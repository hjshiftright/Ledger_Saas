from sqlalchemy import String, Integer, Boolean, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base
from decimal import Decimal
from datetime import date

class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    template_name: Mapped[str] = mapped_column(String)
    transaction_type: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    payee_id: Mapped[int | None] = mapped_column(ForeignKey("payees.id"), nullable=True)
    estimated_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    is_amount_fixed: Mapped[bool] = mapped_column(Boolean, default=True)
    frequency: Mapped[str] = mapped_column(String)
    interval_value: Mapped[int] = mapped_column(Integer, default=1)
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    month_of_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_occurrence_date: Mapped[date] = mapped_column(Date)
    last_generated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_occurrences: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_occurrences: Mapped[int] = mapped_column(Integer, default=0)
    auto_confirm: Mapped[bool] = mapped_column(Boolean, default=False)
    security_id: Mapped[int | None] = mapped_column(ForeignKey("securities.id"), nullable=True)
    sip_units: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    lines: Mapped[list["RecurringTransactionLine"]] = relationship(
        back_populates="recurring_transaction", cascade="all, delete-orphan", lazy="selectin"
    )

class RecurringTransactionLine(Base):
    __tablename__ = "recurring_transaction_lines"
    recurring_transaction_id: Mapped[int] = mapped_column(ForeignKey("recurring_transactions.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    line_type: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    recurring_transaction: Mapped["RecurringTransaction"] = relationship(back_populates="lines")
