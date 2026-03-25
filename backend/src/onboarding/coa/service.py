from typing import List
from repositories.protocols import AccountRepository
from common.events import event_bus
from common.exceptions import SystemAccountError, ValidationError, NotFoundError, BusinessRuleError
from .schemas import AccountNodeResponse, COATreeResponse
from .default_tree import DEFAULT_COA


def _attr(node, key, default=None):
    """Access a field from either an ORM model or a dict."""
    if hasattr(node, key):
        return getattr(node, key)
    return node.get(key, default) if isinstance(node, dict) else default


class COASetupService:
    def __init__(self, account_repo: AccountRepository):
        self._accounts = account_repo

    def create_default_coa(self, user_id: int | None = None) -> List[AccountNodeResponse]:
        created_accounts = []

        def _walk_and_create(node, parent_id=None):
            data = {
                "parent_id": parent_id,
                "code": node["code"],
                "name": node["name"],
                "type": node["type"],
                "subtype": node.get("subtype"),
                "normal_balance": node["normal_balance"],
                "is_placeholder": node.get("is_placeholder", False),
                "is_system": node.get("is_system", False),
                "is_active": True,
            }
            if user_id is not None:
                data["user_id"] = user_id
            created = self._accounts.create(data)
            created_accounts.append(created)

            for child in node.get("children", []):
                _walk_and_create(child, _attr(created, "id"))

        for root_node in DEFAULT_COA:
            _walk_and_create(root_node)

        event_bus.publish("coa.initialized", {})
        return [self._to_response(acc) for acc in created_accounts]

    def get_coa_tree(self) -> COATreeResponse:
        all_accounts = self._accounts.get_tree()
        # Build a map and nested structure
        nodes: dict[int, AccountNodeResponse] = {}
        for acc in all_accounts:
            nodes[_attr(acc, "id")] = self._to_response(acc)
        roots: list[AccountNodeResponse] = []
        for acc in all_accounts:
            pid = _attr(acc, "parent_id")
            node = nodes[_attr(acc, "id")]
            if pid and pid in nodes:
                nodes[pid].children.append(node)
            else:
                roots.append(node)
        return COATreeResponse(items=roots)

    def rename_account(self, account_id: int, new_name: str) -> AccountNodeResponse:
        if not new_name.strip():
            raise ValidationError("Account name cannot be empty")
        account = self._accounts.get(account_id)
        if not account:
            raise NotFoundError("Account", account_id)
        if _attr(account, "is_system"):
            raise SystemAccountError(_attr(account, "name"))
        updated = self._accounts.update(account_id, {"name": new_name})
        return self._to_response(updated)

    def add_custom_category(self, parent_id: int, name: str) -> AccountNodeResponse:
        if not name.strip():
            raise ValidationError("Category name cannot be empty")
        parent = self._accounts.get(parent_id)
        if not parent:
            raise NotFoundError("Parent Account", parent_id)
        if not _attr(parent, "is_placeholder"):
            raise BusinessRuleError("Cannot add category under a non-placeholder account")

        children = self._accounts.get_children(parent_id)
        if children:
            max_code = max(int(_attr(c, "code")) for c in children)
            new_code = str(max_code + 1)
        else:
            base = int(_attr(parent, "code"))
            new_code = str(base + 1)

        # Skip any codes already in use (could be occupied by grandchildren)
        while self._accounts.find_by_code(new_code):
            new_code = str(int(new_code) + 1)

        data = {
            "parent_id": parent_id,
            "code": new_code,
            "name": name,
            "type": _attr(parent, "account_type"),
            "subtype": _attr(parent, "account_subtype"),
            "normal_balance": _attr(parent, "normal_balance"),
            "is_placeholder": False,
            "is_system": False,
            "is_active": True,
        }
        created = self._accounts.create(data)
        return self._to_response(created)

    def deactivate_category(self, account_id: int) -> None:
        account = self._accounts.get(account_id)
        if not account:
            raise NotFoundError("Account", account_id)
        if _attr(account, "is_system"):
            raise SystemAccountError(_attr(account, "name"))
        if self._accounts.has_transactions(account_id):
            raise BusinessRuleError("Cannot deactivate an account with transactions")
        self._accounts.update(account_id, {"is_active": False})
        event_bus.publish("coa.category_deactivated", {"account_id": account_id})

    def is_coa_ready(self) -> bool:
        tree = self._accounts.get_tree()
        return len(tree) > 0

    def _to_response(self, node) -> AccountNodeResponse:
        return AccountNodeResponse(
            id=_attr(node, "id"),
            code=_attr(node, "code"),
            name=_attr(node, "name"),
            type=_attr(node, "account_type") or _attr(node, "type"),
            subtype=_attr(node, "account_subtype") or _attr(node, "subtype"),
            normal_balance=_attr(node, "normal_balance"),
            is_placeholder=_attr(node, "is_placeholder", False),
            is_system=_attr(node, "is_system", False),
            is_active=_attr(node, "is_active", True),
            parent_id=_attr(node, "parent_id"),
            children=[],
        )
