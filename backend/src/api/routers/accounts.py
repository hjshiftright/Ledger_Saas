"""SM-A Account Registry REST API — SQLite-backed.

Endpoints:
    POST   /api/v1/accounts                          — create account
    GET    /api/v1/accounts                          — list accounts (flat)
    GET    /api/v1/accounts/tree                     — full CoA tree
    GET    /api/v1/accounts/{account_id}             — get single account
    PATCH  /api/v1/accounts/{account_id}             — update name / description / code
    DELETE /api/v1/accounts/{account_id}             — delete (leaf, non-system only)
    POST   /api/v1/accounts/{account_id}/move        — move to new parent
    POST   /api/v1/accounts/{account_id}/archive     — soft-delete
    POST   /api/v1/accounts/{account_id}/restore     — un-archive
    GET    /api/v1/accounts/{account_id}/balance     — computed rolled-up balance
    POST   /api/v1/accounts/provision-defaults       — create standard Indian household CoA
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from accounts.models import AccountSubType, AccountType, normal_balance_for
from api.deps import CurrentUser, DBSession
from db.models.accounts import Account as OrmAccount
from onboarding.coa.default_tree import DEFAULT_COA
from repositories.sqla_account_repo import AccountRepository

router = APIRouter(prefix="/accounts", tags=["Account Registry (SM-A)"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateAccountRequest(BaseModel):
    name: str
    account_type: AccountType
    sub_type: AccountSubType = AccountSubType.GENERIC
    parent_id: int | None = None
    code: str | None = None
    description: str = ""
    currency: str = "INR"


class UpdateAccountRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    code: str | None = None
    sub_type: AccountSubType | None = None


class MoveAccountRequest(BaseModel):
    new_parent_id: int | None = None


class AccountResponse(BaseModel):
    account_id: str
    user_id: str
    name: str
    code: str | None
    description: str
    account_type: str
    sub_type: str
    normal_balance: str
    parent_id: str | None
    depth: int
    is_system: bool
    is_leaf: bool
    is_active: bool
    currency: str
    balance: str
    created_at: str
    updated_at: str


class BalanceResponse(BaseModel):
    account_id: str
    balance: str


# ── Internal helpers ──────────────────────────────────────────────────────────

def _br_error(msg: str) -> HTTPException:
    return HTTPException(status_code=422, detail={"error": "BUSINESS_RULE_VIOLATION", "message": msg})


def _depth_of(acc: OrmAccount, repo: AccountRepository) -> int:
    """Walk the parent chain to compute the account's 1-based depth."""
    depth = 1
    current = acc
    while current.parent_id is not None:
        parent = repo.get(current.parent_id)
        if parent is None:
            break
        depth += 1
        current = parent
    return depth


def _sibling_names(parent_id: int | None, repo: AccountRepository) -> list[str]:
    if parent_id is None:
        return [a.name.lower() for a in repo.get_tree() if a.parent_id is None]
    return [a.name.lower() for a in repo.get_children(parent_id)]


def _descendant_ids(acc_id: int, repo: AccountRepository) -> set[int]:
    ids: set[int] = set()
    queue = list(repo.get_children(acc_id))
    while queue:
        node = queue.pop()
        if node.id in ids:
            continue
        ids.add(node.id)
        queue.extend(repo.get_children(node.id))
    return ids


def _to_response(acc: OrmAccount, repo: AccountRepository, user_id: str) -> AccountResponse:
    return AccountResponse(
        account_id=str(acc.id),
        user_id=user_id,
        name=acc.name,
        code=acc.code,
        description=acc.description or "",
        account_type=acc.account_type,
        sub_type=acc.account_subtype or "GENERIC",
        normal_balance=acc.normal_balance,
        parent_id=str(acc.parent_id) if acc.parent_id is not None else None,
        depth=_depth_of(acc, repo),
        is_system=acc.is_system,
        is_leaf=len(repo.get_children(acc.id)) == 0,
        is_active=acc.is_active,
        currency=acc.currency_code,
        balance="0",  # balance is computed from TransactionLines; see GET /balance
        created_at=acc.created_at.isoformat() if acc.created_at else "",
        updated_at=acc.updated_at.isoformat() if acc.updated_at else "",
    )


# ── POST /accounts/provision-defaults ────────────────────────────────────────

@router.post(
    "/provision-defaults",
    response_model=list[AccountResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Provision default Indian household Chart of Accounts",
    operation_id="provisionDefaultAccounts",
)
def provision_defaults(user_id: CurrentUser, session: DBSession) -> list[AccountResponse]:
    repo = AccountRepository(session)
    if repo.count() > 0:
        raise HTTPException(
            status_code=409,
            detail={"error": "ALREADY_PROVISIONED", "message": "Accounts already exist. Clear them first."},
        )
    created: list[OrmAccount] = []

    def _walk(nodes: list, parent_id: int | None = None) -> None:
        for node in nodes:
            acc = repo.create({
                "name": node["name"],
                "account_type": node["type"],
                "account_subtype": node.get("subtype", "GENERIC"),
                "normal_balance": node["normal_balance"],
                "parent_id": parent_id,
                "code": node["code"],
                "is_system": node.get("is_system", True),
                "is_placeholder": node.get("is_placeholder", False),
            })
            created.append(acc)
            _walk(node.get("children", []), acc.id)

    for root in DEFAULT_COA:
        _walk([root])

    return [_to_response(a, repo, user_id) for a in created]


# ── POST /accounts ────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
    operation_id="createAccount",
)
def create_account(body: CreateAccountRequest, user_id: CurrentUser, session: DBSession) -> AccountResponse:
    repo = AccountRepository(session)
    # BR-A-02: parent must exist; BR-A-03: max depth 4
    if body.parent_id is not None:
        parent = repo.get(body.parent_id)
        if parent is None:
            raise _br_error(f"Parent account {body.parent_id} does not exist.")
        if _depth_of(parent, repo) + 1 > 4:
            raise _br_error("Maximum account hierarchy depth is 4.")
    # BR-A-07: unique name within same parent
    if body.name.lower() in _sibling_names(body.parent_id, repo):
        raise _br_error(f"An account named '{body.name}' already exists under the same parent.")
    nb = normal_balance_for(body.account_type).value
    acc = repo.create({
        "name": body.name, "account_type": body.account_type.value,
        "account_subtype": body.sub_type.value, "normal_balance": nb,
        "parent_id": body.parent_id, "code": body.code,
        "description": body.description, "currency_code": body.currency,
    })
    return _to_response(acc, repo, user_id)


# ── GET /accounts/bankable ────────────────────────────────────────────────────

@router.get(
    "/bankable",
    response_model=list[AccountResponse],
    summary="List accounts eligible as import source (bank, cash, credit card leaf accounts)",
    operation_id="listBankableAccounts",
)
def list_bankable_accounts(user_id: CurrentUser, session: DBSession) -> list[AccountResponse]:
    """Returns only non-placeholder, active leaf accounts suitable as the
    source account for a bank / CC statement import.

    Includes subtypes: BANK, CASH, CREDIT_CARD.
    This is the filtered list the import wizard shows in its account picker —
    it only contains accounts the user has actually set up, so they can never
    upload a statement against an account that doesn't exist in their CoA.
    """
    _IMPORTABLE_SUBTYPES = {
        AccountSubType.BANK.value,
        AccountSubType.CASH.value,
        AccountSubType.CREDIT_CARD.value,
        AccountSubType.INVESTMENT.value,   # Demat / brokerage accounts
    }
    repo = AccountRepository(session)
    all_accs = repo.get_tree()
    importable = [
        a for a in all_accs
        if a.is_active
        and a.account_subtype in _IMPORTABLE_SUBTYPES
        and not repo.get_children(a.id)   # leaf nodes only (not containers)
    ]
    return [_to_response(a, repo, user_id) for a in importable]


# ── GET /accounts ─────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[AccountResponse],
    summary="List accounts (flat)",
    operation_id="listAccounts",
)
def list_accounts(
    user_id: CurrentUser,
    session: DBSession,
    account_type: AccountType | None = None,
    include_inactive: bool = Query(default=False),
) -> list[AccountResponse]:
    repo = AccountRepository(session)
    all_accs = repo.get_tree()
    if account_type:
        all_accs = [a for a in all_accs if a.account_type == account_type.value]
    if not include_inactive:
        all_accs = [a for a in all_accs if a.is_active]
    return [_to_response(a, repo, user_id) for a in all_accs]


# ── GET /accounts/tree ────────────────────────────────────────────────────────

@router.get(
    "/tree",
    response_model=list[AccountResponse],
    summary="Get full Chart of Accounts tree (sorted by code then name)",
    operation_id="getAccountTree",
)
def get_account_tree(user_id: CurrentUser, session: DBSession, include_inactive: bool = Query(default=False)) -> list[AccountResponse]:
    repo = AccountRepository(session)
    all_accs = repo.get_tree()  # already ordered by code
    if not include_inactive:
        all_accs = [a for a in all_accs if a.is_active]
    return [_to_response(a, repo, user_id) for a in all_accs]


# ── GET /accounts/{account_id} ────────────────────────────────────────────────

@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get a single account",
    operation_id="getAccount",
)
def get_account(account_id: int, user_id: CurrentUser, session: DBSession) -> AccountResponse:
    repo = AccountRepository(session)
    acc = repo.get(account_id)
    if acc is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Account {account_id} not found."})
    return _to_response(acc, repo, user_id)


# ── PATCH /accounts/{account_id} ──────────────────────────────────────────────

@router.patch(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update account name / description / code",
    operation_id="updateAccount",
)
def update_account(account_id: int, body: UpdateAccountRequest, user_id: CurrentUser, session: DBSession) -> AccountResponse:
    repo = AccountRepository(session)
    acc = repo.get(account_id)
    if acc is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Account {account_id} not found."})
    # BR-A-07: unique name within same parent if name is changing
    if body.name and body.name.lower() != acc.name.lower():
        siblings = _sibling_names(acc.parent_id, repo)
        if body.name.lower() in siblings:
            raise _br_error(f"An account named '{body.name}' already exists under the same parent.")
    updates: dict = {}
    if body.name is not None:        updates["name"] = body.name
    if body.description is not None: updates["description"] = body.description
    if body.code is not None:        updates["code"] = body.code
    if body.sub_type is not None:    updates["account_subtype"] = body.sub_type.value
    if updates:
        acc = repo.update(account_id, updates)
    return _to_response(acc, repo, user_id)


# ── DELETE /accounts/{account_id} ─────────────────────────────────────────────

@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an account (must be leaf and non-system)",
    operation_id="deleteAccount",
)
def delete_account(account_id: int, user_id: CurrentUser, session: DBSession) -> None:
    repo = AccountRepository(session)
    acc = repo.get(account_id)
    if acc is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Account {account_id} not found."})
    if acc.is_system:
        raise _br_error(f"Account '{acc.name}' is a system account and cannot be deleted.")
    if repo.get_children(account_id):
        raise _br_error(f"Account '{acc.name}' has sub-accounts. Delete or move them first.")
    repo.delete(acc)


# ── POST /accounts/{account_id}/move ─────────────────────────────────────────

@router.post(
    "/{account_id}/move",
    response_model=AccountResponse,
    summary="Move account to a different parent (BR-A-10)",
    operation_id="moveAccount",
)
def move_account(account_id: int, body: MoveAccountRequest, user_id: CurrentUser, session: DBSession) -> AccountResponse:
    repo = AccountRepository(session)
    acc = repo.get(account_id)
    if acc is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Account {account_id} not found."})
    # BR-A-04: no self-parent or ancestor cycles
    if body.new_parent_id == account_id:
        raise _br_error("An account cannot be its own parent.")
    if body.new_parent_id is not None and body.new_parent_id in _descendant_ids(account_id, repo):
        raise _br_error("Cannot move an account to one of its own descendants.")
    # BR-A-03: depth check
    if body.new_parent_id is not None:
        new_parent = repo.get(body.new_parent_id)
        if new_parent is None:
            raise _br_error(f"Target parent account {body.new_parent_id} does not exist.")
        if _depth_of(new_parent, repo) + 1 > 4:
            raise _br_error("Moving here would exceed the maximum hierarchy depth of 4.")
    # BR-A-07: name uniqueness at new location
    if acc.name.lower() in [
        a.name.lower() for a in (
            repo.get_children(body.new_parent_id) if body.new_parent_id
            else [a for a in repo.get_tree() if a.parent_id is None]
        ) if a.id != account_id
    ]:
        raise _br_error(f"An account named '{acc.name}' already exists at the target location.")
    repo.update(account_id, {"parent_id": body.new_parent_id})
    acc = repo.get(account_id)
    return _to_response(acc, repo, user_id)


# ── POST /accounts/{account_id}/archive ───────────────────────────────────────

@router.post(
    "/{account_id}/archive",
    response_model=AccountResponse,
    summary="Archive (soft-delete) an account (BR-A-11)",
    operation_id="archiveAccount",
)
def archive_account(account_id: int, user_id: CurrentUser, session: DBSession) -> AccountResponse:
    repo = AccountRepository(session)
    acc = repo.get(account_id)
    if acc is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Account {account_id} not found."})
    if acc.is_system:
        raise _br_error(f"Cannot archive system account '{acc.name}'.")
    acc = repo.update(account_id, {"is_active": False})
    return _to_response(acc, repo, user_id)


# ── POST /accounts/{account_id}/restore ───────────────────────────────────────

@router.post(
    "/{account_id}/restore",
    response_model=AccountResponse,
    summary="Restore an archived account",
    operation_id="restoreAccount",
)
def restore_account(account_id: int, user_id: CurrentUser, session: DBSession) -> AccountResponse:
    repo = AccountRepository(session)
    acc = repo.get(account_id)
    if acc is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Account {account_id} not found."})
    acc = repo.update(account_id, {"is_active": True})
    return _to_response(acc, repo, user_id)


# ── GET /accounts/{account_id}/balance ───────────────────────────────────────

@router.get(
    "/{account_id}/balance",
    response_model=BalanceResponse,
    summary="Get rolled-up balance for an account and all its descendants (BR-A-09)",
    operation_id="getAccountBalance",
)
def get_account_balance(account_id: int, user_id: CurrentUser, session: DBSession) -> BalanceResponse:
    repo = AccountRepository(session)
    if repo.get(account_id) is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Account {account_id} not found."})
    # Balance is the sum over TransactionLines for this account + all descendants.
    # Computed via raw SQL for efficiency; returns 0 when no transactions exist.
    from decimal import Decimal
    from sqlalchemy import select, func
    from db.models.transactions import TransactionLine
    subtree = {account_id} | _descendant_ids(account_id, repo)
    stmt = (
        select(func.coalesce(func.sum(TransactionLine.amount), 0))
        .where(TransactionLine.account_id.in_(subtree))
    )
    total = session.scalar(stmt) or Decimal("0")
    return BalanceResponse(account_id=str(account_id), balance=str(total))
