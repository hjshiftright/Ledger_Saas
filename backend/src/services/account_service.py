from repositories.sqla_account_repo import AccountRepository
from db.models.accounts import Account
from schemas.account import AccountCreateDTO
from sqlalchemy.orm import Session


class AccountService:
    def __init__(self, session: Session):
        self.repo = AccountRepository(session)

    def create_new_account(self, dto: AccountCreateDTO) -> Account:
        if self.repo.find_by_code(dto.code):
            raise ValueError(f"Account code {dto.code} already exists")

        new_account = Account(
            code=dto.code,
            name=dto.name,
            account_type=dto.account_type,
            normal_balance=dto.normal_balance
        )

        return self.repo.create(new_account)
