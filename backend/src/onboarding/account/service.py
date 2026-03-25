from repositories.protocols import AccountRepository, InstitutionRepository, AccountDetailRepository
from common.events import event_bus
from common.exceptions import NotFoundError, ValidationError, BusinessRuleError
from .schemas import (
    BankAccountSetupDTO, CreditCardSetupDTO, LoanSetupDTO,
    BrokerageSetupDTO, FixedDepositSetupDTO, CashWalletSetupDTO
)


def _attr(node, key, default=None):
    """Access a field from either an ORM model or a dict."""
    if hasattr(node, key):
        return getattr(node, key)
    return node.get(key, default) if isinstance(node, dict) else default


class AccountSetupService:
    def __init__(self,
                 account_repo: AccountRepository,
                 inst_repo: InstitutionRepository,
                 detail_repo: AccountDetailRepository):
        self._accounts = account_repo
        self._institutions = inst_repo
        self._details = detail_repo

    def _resolve_parent_and_create_coa_leaf(self, parent_code: str, display_name: str):
        tree = self._accounts.get_tree()
        parent = None

        def _find_by_code(nodes, code):
            for n in nodes:
                if _attr(n, "code") == code:
                    return n
                children = _attr(n, "children", []) or []
                res = _find_by_code(children, code)
                if res:
                    return res
            return None

        parent = _find_by_code(tree, parent_code)
        if not parent:
            raise NotFoundError("COA Category Code", parent_code)

        p_id = _attr(parent, "id")
        children = self._accounts.get_children(p_id)
        if children:
            max_code = max(int(_attr(c, "code")) for c in children)
            new_code = str(max_code + 1)
        else:
            base = int(_attr(parent, "code"))
            new_code = str(base + 1)

        data = {
            "parent_id": p_id,
            "code": new_code,
            "name": display_name,
            "type": _attr(parent, "account_type") or _attr(parent, "type"),
            "subtype": _attr(parent, "account_subtype") or _attr(parent, "subtype"),
            "normal_balance": _attr(parent, "normal_balance"),
            "is_placeholder": False,
            "is_system": False,
            "is_active": True,
        }
        return self._accounts.create(data)

    def _validate_institution(self, institution_id: int):
        if not self._institutions.get(institution_id):
            raise NotFoundError("Institution", institution_id)

    def add_bank_account(self, dto: BankAccountSetupDTO):
        self._validate_institution(dto.institution_id)
        coa_node = self._resolve_parent_and_create_coa_leaf("1100", dto.display_name)

        detail = {
            "account_id": _attr(coa_node, "id"),
            "institution_id": dto.institution_id,
            "account_number_masked": dto.account_number_masked,
            "bank_account_type": dto.bank_account_type.value,
            "ifsc_code": dto.ifsc_code,
            "branch": dto.branch,
        }
        detail_record = self._details.create_detail("bank_account", detail)
        event_bus.publish("account.created", {"account_id": _attr(coa_node, "id"), "type": "BANK"})
        return {"coa": coa_node, "detail": detail_record}

    def add_credit_card(self, dto: CreditCardSetupDTO):
        self._validate_institution(dto.institution_id)
        coa_node = self._resolve_parent_and_create_coa_leaf("2100", dto.display_name)

        detail = {
            "account_id": _attr(coa_node, "id"),
            "institution_id": dto.institution_id,
            "last_four_digits": dto.last_four_digits,
            "credit_limit": dto.credit_limit,
            "billing_cycle_day": dto.billing_cycle_day,
            "interest_rate_annual": dto.interest_rate_annual,
        }
        detail_record = self._details.create_detail("credit_card", detail)
        event_bus.publish("account.created", {"account_id": _attr(coa_node, "id"), "type": "CREDIT_CARD"})
        return {"coa": coa_node, "detail": detail_record}

    def add_loan(self, dto: LoanSetupDTO):
        self._validate_institution(dto.institution_id)
        coa_node = self._resolve_parent_and_create_coa_leaf("2200", dto.display_name)

        detail = {
            "account_id": _attr(coa_node, "id"),
            "institution_id": dto.institution_id,
            "loan_type": dto.loan_type.value,
            "principal_amount": dto.principal_amount,
            "interest_rate": dto.interest_rate,
            "tenure_months": dto.tenure_months,
            "emi_amount": dto.emi_amount,
            "start_date": dto.start_date,
            "linked_asset_account_id": dto.linked_asset_account_id,
        }
        detail_record = self._details.create_detail("loan", detail)
        event_bus.publish("account.created", {"account_id": _attr(coa_node, "id"), "type": "LOAN"})
        return {"coa": coa_node, "detail": detail_record}

    def add_brokerage_account(self, dto: BrokerageSetupDTO):
        self._validate_institution(dto.institution_id)
        coa_node = self._resolve_parent_and_create_coa_leaf("1200", dto.display_name)

        detail = {
            "account_id": _attr(coa_node, "id"),
            "institution_id": dto.institution_id,
            "demat_id": dto.demat_id,
            "default_cost_basis_method": dto.default_cost_basis_method,
        }
        detail_record = self._details.create_detail("brokerage", detail)
        event_bus.publish("account.created", {"account_id": _attr(coa_node, "id"), "type": "BROKERAGE"})
        return {"coa": coa_node, "detail": detail_record}

    def add_fixed_deposit(self, dto: FixedDepositSetupDTO):
        self._validate_institution(dto.institution_id)
        coa_node = self._resolve_parent_and_create_coa_leaf("1200", dto.display_name)

        detail = {
            "account_id": _attr(coa_node, "id"),
            "institution_id": dto.institution_id,
            "principal_amount": dto.principal_amount,
            "interest_rate": dto.interest_rate,
            "start_date": dto.start_date,
            "maturity_date": dto.maturity_date,
            "compounding_frequency": dto.compounding_frequency,
            "auto_renew": dto.auto_renew,
        }
        detail_record = self._details.create_detail("fixed_deposit", detail)
        event_bus.publish("account.created", {"account_id": _attr(coa_node, "id"), "type": "FIXED_DEPOSIT"})
        return {"coa": coa_node, "detail": detail_record}

    def add_cash_wallet(self, dto: CashWalletSetupDTO):
        coa_node = self._resolve_parent_and_create_coa_leaf("1100", dto.display_name)
        return {"coa": coa_node, "detail": None}
