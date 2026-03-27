from typing import Any
from repositories.protocols import SnapshotRepository, AccountRepository, TransactionRepository
from common.events import event_bus
from .schemas import NetWorthSnapshotDTO


def _attr(node, key, default=None):
    if hasattr(node, key):
        return getattr(node, key)
    return node.get(key, default) if isinstance(node, dict) else default


class NetWorthService:
    def __init__(self,
                 snapshot_repo: SnapshotRepository,
                 account_repo: AccountRepository,
                 tx_repo: TransactionRepository):
        self._snapshots = snapshot_repo
        self._accounts = account_repo
        self._txs = tx_repo

    async def compute_initial_net_worth(self, as_of: str) -> NetWorthSnapshotDTO:
        tree = await self._accounts.get_tree()

        # Flat list from SQLAlchemy — filter non-placeholder leaves directly
        all_leaves = [n for n in tree if not _attr(n, "is_placeholder", False)]

        total_assets = 0.0
        total_liabilities = 0.0
        breakdown = {
            "liquid_assets": 0.0,
            "investments": 0.0,
            "property": 0.0,
            "short_term_liabilities": 0.0,
            "long_term_liabilities": 0.0,
        }

        for leaf in all_leaves:
            l_id = _attr(leaf, "id")
            ob = await self._txs.get_opening_balance_for_account(l_id)
            if not ob:
                continue

            balance = 0.0
            lines = _attr(ob, "lines", []) or ob.get("lines", []) if isinstance(ob, dict) else getattr(ob, "lines", [])
            for line in lines:
                line_acc_id = _attr(line, "account_id")
                if line_acc_id == l_id:
                    l_normal_balance = _attr(leaf, "normal_balance")
                    # SQLAlchemy lines use line_type; legacy dicts use action
                    line_action = _attr(line, "line_type") or _attr(line, "action")
                    if l_normal_balance == line_action:
                        balance += float(_attr(line, "amount", 0))
                    else:
                        balance -= float(_attr(line, "amount", 0))

            if balance <= 0:
                continue

            l_type = _attr(leaf, "account_type") or _attr(leaf, "type")
            l_subtype = _attr(leaf, "account_subtype") or _attr(leaf, "subtype")

            if l_type == "ASSET":
                total_assets += balance
                if l_subtype in ["BANK", "CASH"]:
                    breakdown["liquid_assets"] += balance
                elif l_subtype == "PROPERTY":
                    breakdown["property"] += balance
                else:
                    breakdown["investments"] += balance
            elif l_type == "LIABILITY":
                total_liabilities += balance
                if l_subtype == "CREDIT_CARD":
                    breakdown["short_term_liabilities"] += balance
                else:
                    breakdown["long_term_liabilities"] += balance

        net_worth = total_assets - total_liabilities

        dto = NetWorthSnapshotDTO(
            as_of_date=as_of,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            net_worth=net_worth,
            breakdown=breakdown,
        )

        await self._snapshots.save_net_worth({
            "snapshot_date": as_of,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": net_worth,
        })
        event_bus.publish("networth.computed", {"net_worth": net_worth})

        return dto
