from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from db.models.transactions import TransactionLine, Transaction
from db.models.accounts import Account
from db.models.reporting import MonthlySnapshot

class ReportingRepository:
    """Read-only repository for reporting queries. No create/update/delete."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def get_account_balance_at_date(
        self, account_id: int, as_of_date: date
    ) -> Decimal:
        """
        Efficient balance calculation: snapshot + delta.
        """
        # Step 1: Find nearest snapshot
        snapshot_stmt = (
            select(MonthlySnapshot)
            .where(MonthlySnapshot.account_id == account_id)
            .where(
                (MonthlySnapshot.snapshot_year * 100 + MonthlySnapshot.snapshot_month)
                <= (as_of_date.year * 100 + as_of_date.month)
            )
            .order_by(
                MonthlySnapshot.snapshot_year.desc(),
                MonthlySnapshot.snapshot_month.desc(),
            )
            .limit(1)
        )
        snapshot = await self.session.scalar(snapshot_stmt)

        if snapshot:
            base_balance = snapshot.closing_balance
            delta_start = date(snapshot.snapshot_year, snapshot.snapshot_month, 1)
        else:
            base_balance = Decimal("0")
            delta_start = date(2000, 1, 1)

        # Step 2: Sum delta from snapshot end to as_of_date
        delta_stmt = (
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (TransactionLine.line_type == "DEBIT", TransactionLine.amount),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("total_debits"),
                func.coalesce(
                    func.sum(
                        case(
                            (TransactionLine.line_type == "CREDIT", TransactionLine.amount),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("total_credits"),
            )
            .join(Transaction, TransactionLine.transaction_id == Transaction.id)
            .where(
                and_(
                    TransactionLine.account_id == account_id,
                    Transaction.transaction_date > delta_start,
                    Transaction.transaction_date <= as_of_date,
                    Transaction.is_void == False,
                )
            )
        )
        result = await self.session.execute(delta_stmt).one()

        # Step 3: Get account type to determine normal balance direction
        account = self.session.get(Account, account_id)
        if account and account.account_type in ("ASSET", "EXPENSE"):
            return base_balance + result.total_debits - result.total_credits
        else:
            return base_balance + result.total_credits - result.total_debits

    def get_income_expense_summary(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """
        Aggregate income and expense by account for a date range.
        """
        stmt = (
            select(
                Account.id.label("account_id"),
                Account.name.label("account_name"),
                Account.account_type,
                func.sum(TransactionLine.amount).label("total"),
            )
            .join(TransactionLine, TransactionLine.account_id == Account.id)
            .join(Transaction, TransactionLine.transaction_id == Transaction.id)
            .where(
                and_(
                    Account.account_type.in_(["INCOME", "EXPENSE"]),
                    Transaction.transaction_date.between(start_date, end_date),
                    Transaction.is_void == False,
                )
            )
            .group_by(Account.id, Account.name, Account.account_type)
            .order_by(Account.account_type, Account.code)
        )
        rows = await self.session.execute(stmt).all()
        return [
            {
                "account_id": r.account_id,
                "account_name": r.account_name,
                "account_type": r.account_type,
                "total": r.total,
            }
            for r in rows
        ]
