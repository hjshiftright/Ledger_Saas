from datetime import date
from typing import List, Dict, Any, Optional
from repositories.protocols import (
    AccountRepository, TransactionRepository, ProfileRepository, GoalRepository
)
from common.events import event_bus
from .schemas import DashboardSaveRequest, DashboardDataResponse, AssetItem, GoalItem
from ..profile.schemas import ProfileSetupRequest

# Map the wizard goal id (sent as GoalItem.id) to the DB goal_type enum value
_GOAL_TYPE_MAP: dict[str, str] = {
    "retire":    "RETIREMENT",
    "emergency": "EMERGENCY",
    "home":      "HOME",
    "car":       "VEHICLE",
}

def _goal_type_from_id(goal_id: Any) -> str:
    """Return the goal_type string for a wizard goal id."""
    gid = str(goal_id) if goal_id is not None else ""
    if gid in _GOAL_TYPE_MAP:
        return _GOAL_TYPE_MAP[gid]
    if gid.startswith("edu"):
        return "EDUCATION"
    if gid.startswith("vac"):
        return "VACATION"
    return "OTHERS"


def _attr(node, key, default=None):
    if hasattr(node, key):
        return getattr(node, key)
    return node.get(key, default) if isinstance(node, dict) else default


class DashboardService:
    def __init__(self,
                 account_repo: AccountRepository,
                 tx_repo: TransactionRepository,
                 profile_repo: ProfileRepository,
                 goal_repo: GoalRepository):
        self._accounts = account_repo
        self._txs = tx_repo
        self._profiles = profile_repo
        self._goals = goal_repo

    def save_dashboard(self, data: DashboardSaveRequest, user_id: str) -> DashboardDataResponse:
        uid = int(user_id)
        # 1. Save Profile
        profile_data = {
            "user_id": uid,
            "display_name": data.name,
            "age": data.age,
            "monthly_income": data.monthly_income,
            "monthly_expenses": data.monthly_expenses,
        }
        # Find existing profile for this user
        existing_list = self._profiles.list(limit=1, filters={"user_id": uid})
        existing = existing_list[0] if existing_list else None
        if existing:
            self._profiles.update(existing.id, profile_data)
        else:
            self._profiles.create(profile_data)

        # 2. Save Assets & Liabilities (Simplified: Overwrite per category if match found by name)
        # For this "End to End" we'll just create new ones that don't exist
        # and set their opening balance.
        
        category_map = {
            "banks": "1100",
            "realEstate": "1400",
            "equity": "1202",
            "foreignEquity": "1202",
            "providentFund": "1204",
            "fixedDeposits": "1203",
            "bullion": "1300",
            "others": "1200",
            "creditCards": "2100",
            "homeLoans": "2200",
            "vehicleLoans": "2300",
            "personalLoans": "2400",
            "educationalLoans": "2400",
        }

        # Clear existing non-system accounts in these categories to avoid bloat for this session?
        # No, better to just upsert.
        
        for cat, items in {**data.assets, **data.liabilities}.items():
            parent_code = category_map.get(cat)
            if not parent_code: continue
            
            for item in items:
                if not item.name or item.balance == 0: continue
                
                # Check if account already exists
                # For simplicity, search by name in the category
                existing_acc = self._find_account_by_name_and_parent(item.name, parent_code)
                if not existing_acc:
                    # Create account
                    existing_acc = self._create_coa_leaf(parent_code, item.name)
                
                if not existing_acc:
                    # Parent category not found in COA — skip silently
                    import logging
                    logging.getLogger(__name__).warning(
                        "COA parent code %s not found; skipping account '%s'",
                        parent_code, item.name
                    )
                    continue
                
                # Set opening balance
                self._set_opening_balance(existing_acc.id, item.balance)

        # 3. Save Goals
        today = date.today()
        self._goals.delete_all()
        for goal in data.goals:
            years = max(1, int(goal.years or 1))
            target_year = today.year + years
            self._goals.create({
                "name": goal.name,
                "goal_type": _goal_type_from_id(goal.id),
                "target_amount": goal.target,
                "current_amount": goal.current,
                "start_date": today.isoformat(),
                "target_date": f"{target_year}-{today.month:02d}-01",
            })

        return self.get_dashboard(user_id)

    def get_dashboard(self, user_id: str = None) -> DashboardDataResponse:
        # Load profile scoped to the current user when user_id is provided
        uid = int(user_id) if user_id else None
        filters = {"user_id": uid} if uid else None
        profiles = self._profiles.list(limit=1, sort_by="id", sort_desc=True, filters=filters)
        profile = profiles[0] if profiles else None
        
        # Load assets/liabilities from accounts
        tree = self._accounts.get_tree()
        
        category_map_inv = {
            "1100": "banks",
            "1200": "others",
            "1202": "equity",
            "1203": "fixedDeposits",
            "1204": "providentFund",
            "1300": "bullion",
            "1400": "realEstate",
            "2100": "creditCards",
            "2200": "homeLoans",
            "2300": "vehicleLoans",
            "2400": "personalLoans",
        }
        
        assets = {k: [] for k in ["banks", "realEstate", "equity", "providentFund", "fixedDeposits", "bullion", "others"]}
        liabilities = {k: [] for k in ["creditCards", "homeLoans", "vehicleLoans", "personalLoans"]}
        
        def _walk_and_collect(nodes):
            for n in nodes:
                p_code = _attr(n, "code")
                if p_code in category_map_inv:
                    cat = category_map_inv[p_code]
                    children = _attr(n, "children", []) or []
                    for child in children:
                        bal = self._get_balance(_attr(child, "id"), _attr(child, "normal_balance"))
                        item = AssetItem(id=_attr(child, "id"), name=_attr(child, "name"), balance=bal)
                        if cat in assets: assets[cat].append(item)
                        else: liabilities[cat].append(item)
                else:
                    _walk_and_collect(_attr(n, "children", []) or [])

        _walk_and_collect(tree)

        # Load goals — compute years remaining from target_date
        today = date.today()
        def _years_remaining(g) -> int:
            if g.target_date:
                delta = (g.target_date - today).days
                return max(1, round(delta / 365))
            return 10  # fallback
        goals = [
            GoalItem(
                id=g.id, name=g.name,
                target=float(g.target_amount),
                years=_years_remaining(g),
                current=float(g.current_amount)
            )
            for g in self._goals.list()
        ]

        return DashboardDataResponse(
            name=profile.display_name if profile else "Rahul",
            age=profile.age if profile else 30,
            monthly_income=profile.monthly_income if profile else 150000,
            monthly_expenses=profile.monthly_expenses if profile else 50000,
            assets=assets,
            liabilities=liabilities,
            goals=goals
        )

    def _find_account_by_name_and_parent(self, name, parent_code):
        # Search in the tree
        tree = self._accounts.get_tree()
        def _find(nodes):
            for n in nodes:
                if _attr(n, "code") == parent_code:
                    for c in _attr(n, "children", []) or []:
                        if _attr(c, "name") == name: return c
                res = _find(_attr(n, "children", []) or [])
                if res: return res
            return None
        return _find(tree)

    def _create_coa_leaf(self, parent_code: str, display_name: str):
        tree = self._accounts.get_tree()
        def _find_by_code(nodes, code):
            for n in nodes:
                if _attr(n, "code") == code: return n
                res = _find_by_code(_attr(n, "children", []) or [], code)
                if res: return res
            return None

        parent = _find_by_code(tree, parent_code)
        if not parent:
            return None

        p_id = _attr(parent, "id")
        children = self._accounts.get_children(p_id)

        # Generate a leaf code in the namespace of the parent:
        # parent "1202" → leaf codes "120201", "120202", …
        # This avoids collisions with sibling parent-level codes (e.g. "1203", "1204").
        prefix = parent_code
        if children:
            # Find the highest existing code that starts with our prefix
            suffixed = [
                int(_attr(c, "code"))
                for c in children
                if str(_attr(c, "code", "")).startswith(prefix)
            ]
            if suffixed:
                new_code = str(max(suffixed) + 1)
            else:
                # Children exist but none in our prefix namespace — start fresh
                new_code = prefix + "01"
        else:
            new_code = prefix + "01"

        data = {
            "parent_id": p_id,
            "code": new_code,
            "name": display_name,
            "type": _attr(parent, "account_type") or _attr(parent, "type"),
            "subtype": _attr(parent, "account_subtype") or _attr(parent, "subtype"),
            "normal_balance": _attr(parent, "normal_balance"),
            "is_placeholder": False,
            "is_active": True,
        }
        return self._accounts.create(data)

    def _set_opening_balance(self, account_id, balance):
        # Asset: DEBIT Asset, CREDIT Equity (3000)
        # Liability: DEBIT Equity (3000), CREDIT Liability
        acc = self._accounts.get(account_id)
        if not acc: return
        
        normal = _attr(acc, "normal_balance") # "DEBIT" or "CREDIT"
        
        # Simple opening balance transaction
        ob_equity = self._accounts.find_by_code("5100")
        if not ob_equity: return # Should not happen if COA is initialized
        
        tx_data = {
            "date": date.today().isoformat(),
            "description": f"Opening balance for {acc.name}",
            "transaction_type": "OPENING_BALANCE"
        }
        lines_data = [
            {
                "account_id": account_id,
                "action": normal,
                "amount": balance
            },
            {
                "account_id": ob_equity.id,
                "action": "CREDIT" if normal == "DEBIT" else "DEBIT",
                "amount": balance
            }
        ]
        self._txs.create_transaction(tx_data, lines_data)

    def _get_balance(self, account_id, normal_balance):
        ob = self._txs.get_opening_balance_for_account(account_id)
        if not ob: return 0.0
        
        balance = 0.0
        # Transaction ORM object has lines relationship
        for line in ob.lines:
            if line.account_id == account_id:
                if line.line_type == normal_balance:
                    balance += float(line.amount or 0)
                else:
                    balance -= float(line.amount or 0)
        return balance
