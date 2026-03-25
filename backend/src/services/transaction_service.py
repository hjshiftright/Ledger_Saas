from repositories.sqla_transaction_repo import TransactionRepository
from db.models.transactions import Transaction, TransactionLine
from schemas.transaction import TransactionCreateDTO
from sqlalchemy.orm import Session


class TransactionService:
    def __init__(self, session: Session):
        self.txn_repo = TransactionRepository(session)

    def record_expense(self, dto: TransactionCreateDTO) -> Transaction:
        txn = Transaction(
            transaction_date=dto.date,
            transaction_type="EXPENSE",
            description=dto.description,
        )
        txn.lines.append(TransactionLine(
            account_id=dto.expense_account_id,
            line_type="DEBIT",
            amount=dto.amount,
        ))
        txn.lines.append(TransactionLine(
            account_id=dto.payment_account_id,
            line_type="CREDIT",
            amount=dto.amount,
        ))

        return self.txn_repo.create_with_children(txn)
