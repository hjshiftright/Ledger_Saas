from decimal import Decimal
from datetime import date
from sqlalchemy.orm import joinedload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.transactions import Transaction, TransactionLine
from repositories.base import BaseRepository

class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, session: AsyncSession):
        super().__init__(Transaction, session)

    async def create_with_children(self, transaction: Transaction) -> Transaction:
        """Atomically persist a Transaction + all Lines. Leverages SQLAlchemy cascade."""
        self._validate_balanced(transaction)
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def create_transaction(self, tx_data: dict, lines_data: list[dict]) -> Transaction:
        """Protocol-compatible method used by onboarding services."""
        data = tx_data.copy()
        # Map legacy dict keys to ORM column names
        if "tx_type" in data and "transaction_type" not in data:
            data["transaction_type"] = data.pop("tx_type")
        if "date" in data and "transaction_date" not in data:
            data["transaction_date"] = data.pop("date")
        if "notes" in data and "description" not in data:
            data["description"] = data.pop("notes") or "Opening Balance"
        data.setdefault("description", "Opening Balance")
        # Coerce date strings → Python date objects (SQLite rejects strings)
        for date_field in ("transaction_date", "effective_date"):
            val = data.get(date_field)
            if isinstance(val, str):
                from datetime import date as _date
                data[date_field] = _date.fromisoformat(val)

        tx = Transaction(**data)
        for line_data in lines_data:
            ld = line_data.copy()
            # Map "action" → "line_type" (legacy protocol used "action")
            if "action" in ld and "line_type" not in ld:
                ld["line_type"] = ld.pop("action")
            line = TransactionLine(**ld)
            tx.lines.append(line)
        return self.create_with_children(tx)

    async def get_opening_balance_for_account(self, account_id: int) -> Transaction | None:
        """Find the opening balance transaction for a specific account."""
        stmt = (
            select(Transaction)
            .options(joinedload(Transaction.lines))
            .join(TransactionLine)
            .where(TransactionLine.account_id == account_id)
            .where(Transaction.transaction_type == "OPENING_BALANCE")
            .where(Transaction.is_void.is_(False))
        )
        return await self.session.scalar(stmt)

    async def void_transaction(self, tx_id: int) -> None:
        tx = self.get_by_id(tx_id)
        if tx:
            tx.is_void = True
            await self.session.flush()

    async def find_by_hash(self, txn_hash: str) -> Transaction | None:
        """Return a committed Transaction by its dedup hash, or None."""
        stmt = select(Transaction).where(Transaction.txn_hash == txn_hash)
        return await self.session.scalar(stmt)

    async def get_committed_hashes_for_account(self, account_id: int, user_id: int | None = None) -> set[str]:
        """Return all non-null txn_hash values for transactions touching *account_id*.

        Used by the dedup router to seed the seen-hashes set from the DB, providing
        a safety net when the JSON dedup-hash file is absent or stale.
        """
        stmt = (
            select(Transaction.txn_hash)
            .join(TransactionLine)
            .where(TransactionLine.account_id == account_id)
            .where(Transaction.txn_hash.is_not(None))
            .where(Transaction.is_void.is_(False))
        )
        if user_id is not None:
            stmt = stmt.where(Transaction.user_id == user_id)
        return set(self.session.scalars(stmt).all())

    async def get_with_lines(self, transaction_id: int) -> Transaction | None:
        """Eager-load lines to avoid N+1 queries."""
        stmt = (
            select(Transaction)
            .options(joinedload(Transaction.lines))
            .where(Transaction.id == transaction_id)
        )
        return await self.session.scalar(stmt)

    def get_by_date_range(
        self, start_date: date, end_date: date, status: str | None = None,
        user_id: int | None = None,
    ) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .options(joinedload(Transaction.lines))
            .where(Transaction.transaction_date.between(start_date, end_date))
        )
        if status:
            stmt = stmt.where(Transaction.status == status)
        if user_id is not None:
            stmt = stmt.where(Transaction.user_id == user_id)
        stmt = stmt.order_by(Transaction.transaction_date.desc())
        return list(self.session.scalars(stmt).unique().all())

    @staticmethod
    def _validate_balanced(transaction: Transaction) -> None:
        """Enforce double-entry invariant before persistence."""
        if len(transaction.lines) < 2:
            raise ValueError("Transaction must have at least 2 lines (double-entry)")
        total_debit = sum(
            line.amount for line in transaction.lines if line.line_type == "DEBIT"
        )
        total_credit = sum(
            line.amount for line in transaction.lines if line.line_type == "CREDIT"
        )
        if total_debit != total_credit:
            raise ValueError(
                f"Transaction is unbalanced: debits={total_debit}, credits={total_credit}"
            )
