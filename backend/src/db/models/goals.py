from datetime import date
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, TenantScopedMixin


class Goal(TenantScopedMixin, Base):
    __tablename__ = "goals"

    name: Mapped[str] = mapped_column(String, nullable=False)
    goal_type: Mapped[str] = mapped_column(String, nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sip_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    expected_return_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    currency_code: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    milestones: Mapped[list["GoalMilestone"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )
    contributions: Mapped[list["GoalContribution"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )
    account_mappings: Mapped[list["GoalAccountMapping"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )


class GoalMilestone(TenantScopedMixin, Base):
    __tablename__ = "goal_milestones"

    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_achieved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    goal: Mapped["Goal"] = relationship(back_populates="milestones")


class GoalContribution(TenantScopedMixin, Base):
    __tablename__ = "goal_contributions"

    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    contribution_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    goal: Mapped["Goal"] = relationship(back_populates="contributions")


class GoalAccountMapping(TenantScopedMixin, Base):
    __tablename__ = "goal_account_mappings"

    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    goal: Mapped["Goal"] = relationship(back_populates="account_mappings")
