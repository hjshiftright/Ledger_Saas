from datetime import date
from typing import List, Dict, Any, Optional
from repositories.protocols import (
    AccountRepository, TransactionRepository, ProfileRepository, GoalRepository
)
from common.events import event_bus
from .schemas import DashboardSaveRequest, DashboardDataResponse, AssetItem, GoalItem
from onboarding.coa.service import COASetupService

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

    async def save_dashboard(self, data: DashboardSaveRequest, user_id: int, tenant_id: str) -> DashboardDataResponse:
        self._tenant_id = tenant_id

        # 0. Ensure the Chart of Accounts is seeded for this tenant
        coa_svc = COASetupService(self._accounts)
        if not await coa_svc.is_coa_ready():
            import logging
            logging.getLogger(__name__).info("COA not found for tenant %s — seeding defaults.", tenant_id)
            await coa_svc.create_default_coa(tenant_id=tenant_id)

        # 1. Save Profile
        profile_data = {
            "user_id": user_id,
            "display_name": data.name,
        }
        existing_list = await self._profiles.list(limit=1, filters={"user_id": user_id})
        existing = existing_list[0] if existing_list else None
        if existing:
            await self._profiles.update(existing.id, profile_data)
        else:
            await self._profiles.create(profile_data)

        # 2. Save Assets & Liabilities
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

        for cat, items in {**data.assets, **data.liabilities}.items():
            parent_code = category_map.get(cat)
            if not parent_code:
                continue

            for item in items:
                if not item.name or item.balance == 0:
                    continue

                existing_acc = await self._find_account_by_name_and_parent(item.name, parent_code)
                if not existing_acc:
                    existing_acc = await self._create_coa_leaf(parent_code, item.name)

                if not existing_acc:
                    import logging
                    logging.getLogger(__name__).warning(
                        "COA parent code %s not found; skipping account '%s'",
                        parent_code, item.name
                    )
                    continue

                await self._set_opening_balance(_attr(existing_acc, "id"), item.balance)

        # 3. Save Goals
        today = date.today()
        await self._goals.delete_all()
        for goal in data.goals:
            years = max(1, int(goal.years or 1))
            target_year = today.year + years
            await self._goals.create({
                "tenant_id": tenant_id,
                "name": goal.name,
                "goal_type": _goal_type_from_id(goal.id),
                "target_amount": goal.target,
                "current_amount": goal.current,
                "target_date": f"{target_year}-{today.month:02d}-01",
            })

        return await self.get_dashboard(user_id)

    async def get_dashboard(self, user_id: int = None) -> DashboardDataResponse:
        filters = {"user_id": user_id} if user_id else None
        profiles = await self._profiles.list(limit=1, sort_by="id", sort_desc=True, filters=filters)
        profile = profiles[0] if profiles else None

        tree = await self._accounts.get_tree()

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

        await self._walk_and_collect(tree, category_map_inv, assets, liabilities)

        today = date.today()
        def _years_remaining(g) -> int:
            if g.target_date:
                delta = (g.target_date - today).days
                return max(1, round(delta / 365))
            return 10

        raw_goals = await self._goals.list()
        goals = [
            GoalItem(
                id=g.id, name=g.name,
                target=float(g.target_amount),
                years=_years_remaining(g),
                current=float(g.current_amount)
            )
            for g in raw_goals
        ]

        return DashboardDataResponse(
            name=profile.display_name if profile else "Rahul",
            age=30,
            monthly_income=150000,
            monthly_expenses=50000,
            assets=assets,
            liabilities=liabilities,
            goals=goals
        )

    async def _walk_and_collect(self, flat_tree, category_map_inv, assets, liabilities):
        # Build parent_id → children index from the flat list to avoid ORM lazy-loading
        by_id = {_attr(n, "id"): n for n in flat_tree}
        children_of: dict = {}
        for n in flat_tree:
            pid = _attr(n, "parent_id")
            if pid is not None:
                children_of.setdefault(pid, []).append(n)

        for n in flat_tree:
            p_code = _attr(n, "code")
            if p_code in category_map_inv:
                cat = category_map_inv[p_code]
                n_id = _attr(n, "id")
                for child in children_of.get(n_id, []):
                    bal = await self._get_balance(_attr(child, "id"), _attr(child, "normal_balance"))
                    item = AssetItem(id=_attr(child, "id"), name=_attr(child, "name"), balance=bal)
                    if cat in assets:
                        assets[cat].append(item)
                    else:
                        liabilities[cat].append(item)

    async def _find_account_by_name_and_parent(self, name, parent_code):
        tree = await self._accounts.get_tree()
        # Flat search: find the parent account, then look for a child with matching name
        parent = next((n for n in tree if _attr(n, "code") == parent_code), None)
        if not parent:
            return None
        p_id = _attr(parent, "id")
        return next((n for n in tree if _attr(n, "parent_id") == p_id and _attr(n, "name") == name), None)

    async def _create_coa_leaf(self, parent_code: str, display_name: str):
        tree = await self._accounts.get_tree()
        # Flat search — get_tree() returns all accounts
        parent = next((n for n in tree if _attr(n, "code") == parent_code), None)
        if not parent:
            return None

        p_id = _attr(parent, "id")
        children = await self._accounts.get_children(p_id)

        prefix = parent_code
        if children:
            suffixed = [
                int(_attr(c, "code"))
                for c in children
                if str(_attr(c, "code", "")).startswith(prefix)
            ]
            if suffixed:
                new_code = str(max(suffixed) + 1)
            else:
                new_code = prefix + "01"
        else:
            new_code = prefix + "01"

        data = {
            "tenant_id": self._tenant_id,
            "parent_id": p_id,
            "code": new_code,
            "name": display_name,
            "type": _attr(parent, "account_type") or _attr(parent, "type"),
            "subtype": _attr(parent, "account_subtype") or _attr(parent, "subtype"),
            "normal_balance": _attr(parent, "normal_balance"),
            "is_placeholder": False,
            "is_active": True,
        }
        return await self._accounts.create(data)

    async def _set_opening_balance(self, account_id, balance):
        acc = await self._accounts.get(account_id)
        if not acc:
            return

        normal = _attr(acc, "normal_balance")

        ob_equity = await self._accounts.find_by_code("3100")
        if not ob_equity:
            return

        tx_data = {
            "tenant_id": self._tenant_id,
            "date": date.today().isoformat(),
            "description": f"Opening balance for {_attr(acc, 'name')}",
            "transaction_type": "OPENING_BALANCE"
        }
        lines_data = [
            {
                "tenant_id": self._tenant_id,
                "account_id": account_id,
                "action": normal,
                "amount": balance
            },
            {
                "tenant_id": self._tenant_id,
                "account_id": _attr(ob_equity, "id"),
                "action": "CREDIT" if normal == "DEBIT" else "DEBIT",
                "amount": balance
            }
        ]
        await self._txs.create_transaction(tx_data, lines_data)

    async def _get_balance(self, account_id, normal_balance):
        ob = await self._txs.get_opening_balance_for_account(account_id)
        if not ob:
            return 0.0

        balance = 0.0
        for line in ob.lines:
            if line.account_id == account_id:
                if line.line_type == normal_balance:
                    balance += float(line.amount or 0)
                else:
                    balance -= float(line.amount or 0)
        return balance
