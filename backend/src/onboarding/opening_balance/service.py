from typing import List, Optional, Any
from datetime import date
from repositories.protocols import TransactionRepository, AccountRepository
from common.events import event_bus
from common.exceptions import NotFoundError, ValidationError, BusinessRuleError
from .schemas import OpeningBalanceDTO


def _attr(node, key, default=None):
    """Access a field from either an ORM model or a dict."""
    if hasattr(node, key):
        return getattr(node, key)
    return node.get(key, default) if isinstance(node, dict) else default


class OpeningBalanceService:
    def __init__(self, tx_repo: TransactionRepository, account_repo: AccountRepository):
        self._transactions = tx_repo
        self._accounts = account_repo

    def _get_system_equity_account(self) -> Any:
        tree = self._accounts.get_tree()

        def _find_by_code(nodes, code):
            for n in nodes:
                if _attr(n, "code") == code:
                    return n
                children = _attr(n, "children", []) or []
                res = _find_by_code(children, code)
                if res:
                    return res
            return None

        sys_acc = _find_by_code(tree, "5100")
        if not sys_acc:
            raise BusinessRuleError("System Equity account 5100 not found")
        return sys_acc

    def set_opening_balance(self, dto: OpeningBalanceDTO, user_id: int) -> Optional[Any]:
        balance = dto.balance_amount
        if balance < 0:
            raise ValidationError("Balance must be >= 0")

        account = self._accounts.get(dto.account_id)
        if not account:
            raise NotFoundError("Account", dto.account_id)

        existing_tx = self._transactions.get_opening_balance_for_account(dto.account_id)
        if existing_tx:
            self._transactions.void_transaction(_attr(existing_tx, "id"))

        if balance == 0:
            return None

        sys_equity = self._get_system_equity_account()

        tx_data = {
            "transaction_date": date.fromisoformat(dto.balance_date) if isinstance(dto.balance_date, str) else dto.balance_date,
            "transaction_type": "OPENING_BALANCE",
            "description": dto.notes or "Opening Balance",
            "status": "POSTED",
            "user_id": user_id,
        }

        acc_id = _attr(account, "id")
        sys_id = _attr(sys_equity, "id")
        is_asset_like = _attr(account, "normal_balance") == "DEBIT"

        if is_asset_like:
            lines = [
                {"account_id": acc_id, "amount": balance, "line_type": "DEBIT"},
                {"account_id": sys_id, "amount": balance, "line_type": "CREDIT"},
            ]
        else:
            lines = [
                {"account_id": acc_id, "amount": balance, "line_type": "CREDIT"},
                {"account_id": sys_id, "amount": balance, "line_type": "DEBIT"},
            ]

        result = self._transactions.create_transaction(tx_data, lines)
        event_bus.publish("opening_balance.set", {"account_id": acc_id})
        return result

    def set_opening_balances_bulk(self, entries: List[OpeningBalanceDTO], user_id: int) -> List[Any]:
        results = []
        for entry in entries:
            res = self.set_opening_balance(entry, user_id)
            if res:
                results.append(res)
        return results

