from datetime import date
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, TenantScopedMixin


class Budget(TenantScopedMixin, Base):
    __tablename__ = "budgets"

    name: Mapped[str] = mapped_column(String, nullable=False)
    period_type: Mapped[str] = mapped_column(String, nullable=False, default="MONTHLY")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "period_type IN ('MONTHLY','QUARTERLY','ANNUAL','CUSTOM')",
            name="ck_budget_period_type",
        ),
    )

    items: Mapped[list["BudgetItem"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )


class BudgetItem(TenantScopedMixin, Base):
    __tablename__ = "budget_items"

    budget_id: Mapped[int] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    planned_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    budget: Mapped["Budget"] = relationship(back_populates="items")
