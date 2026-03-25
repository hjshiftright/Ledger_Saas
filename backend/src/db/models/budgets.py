from sqlalchemy import String, Boolean, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base
from decimal import Decimal
from datetime import date


class Budget(Base):
    __tablename__ = "budgets"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    period_type: Mapped[str] = mapped_column(String)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    total_budgeted: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)

    items: Mapped[list["BudgetItem"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan", lazy="selectin"
    )


class BudgetItem(Base):
    __tablename__ = "budget_items"
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    budgeted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    spent_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    rollover_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    rollover_unused: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_threshold_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), default=80)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    budget: Mapped["Budget"] = relationship(back_populates="items")
