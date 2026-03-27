from datetime import date
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, TenantScopedMixin


class RecurringTransaction(TenantScopedMixin, Base):
    __tablename__ = "recurring_transactions"

    description: Mapped[str] = mapped_column(String, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "frequency IN ('DAILY','WEEKLY','FORTNIGHTLY','MONTHLY','QUARTERLY','ANNUAL')",
            name="ck_recurring_frequency",
        ),
    )

    lines: Mapped[list["RecurringTransactionLine"]] = relationship(
        back_populates="recurring_transaction", cascade="all, delete-orphan"
    )


class RecurringTransactionLine(TenantScopedMixin, Base):
    __tablename__ = "recurring_transaction_lines"

    recurring_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("recurring_transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    line_type: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    recurring_transaction: Mapped["RecurringTransaction"] = relationship(back_populates="lines")
