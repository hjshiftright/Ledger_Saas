from datetime import date as datetime_date
from typing import Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.accounts import (
    BankAccount, FixedDeposit, CreditCard, Loan, BrokerageAccount
)


class SqlAlchemyAccountDetailRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_model_for_type(self, detail_type: str) -> Type:
        mapping = {
            "BANK_ACCOUNT": BankAccount,
            "FIXED_DEPOSIT": FixedDeposit,
            "CREDIT_CARD": CreditCard,
            "LOAN": Loan,
            "BROKERAGE": BrokerageAccount,
        }
        model = mapping.get(detail_type.upper())
        if not model:
            raise ValueError(f"Unknown account detail type: {detail_type}")
        return model

    async def create_detail(self, detail_type: str, data: dict) -> Any:
        model_class = self._get_model_for_type(detail_type)
        mapped_data = self._map_data(detail_type, data)
        detail = model_class(**mapped_data)
        self.session.add(detail)
        await self.session.flush()
        return detail

    async def _map_data(self, detail_type: str, data: dict) -> dict:
        mapped = data.copy()
        for k in list(mapped.keys()):
            if k in ("start_date", "maturity_date", "deposit_date", "disbursement_date", "opening_date"):
                if isinstance(mapped[k], str) and mapped[k]:
                    mapped[k] = datetime_date.fromisoformat(mapped[k])

        t = detail_type.upper()
        if t == "BANK_ACCOUNT":
            if "branch" in mapped:
                mapped["branch_name"] = mapped.pop("branch")
        elif t == "FIXED_DEPOSIT":
            if "start_date" in mapped:
                mapped["deposit_date"] = mapped.pop("start_date")
            if "deposit_type" not in mapped:
                mapped["deposit_type"] = "CUMULATIVE"
            if "maturity_amount" not in mapped:
                mapped["maturity_amount"] = mapped.get("principal_amount")
        elif t == "LOAN":
            if "start_date" in mapped:
                mapped["disbursement_date"] = mapped.pop("start_date")
        elif t == "CREDIT_CARD":
            if "last_four_digits" in mapped:
                mapped["card_number_masked"] = mapped.pop("last_four_digits")
            mapped.pop("interest_rate_annual", None)
        elif t == "BROKERAGE":
            if "demat_id" in mapped:
                mapped["account_identifier"] = mapped.pop("demat_id")
            if "brokerage_account_type" not in mapped:
                mapped["brokerage_account_type"] = "CASH"
            mapped.pop("default_cost_basis_method", None)
        return mapped
