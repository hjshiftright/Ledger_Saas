from sqlalchemy import String, Integer, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base
from decimal import Decimal
from datetime import date


class Goal(Base):
    __tablename__ = "goals"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    goal_type: Mapped[str] = mapped_column(String)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String, default="MEDIUM")
    status: Mapped[str] = mapped_column(String, default="ACTIVE")
    icon: Mapped[str | None] = mapped_column(String, nullable=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    sip_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    expected_return_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    achieved_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    milestones: Mapped[list["GoalMilestone"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )
    contributions: Mapped[list["GoalContribution"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )
    account_mappings: Mapped[list["GoalAccountMapping"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )


class GoalAccountMapping(Base):
    __tablename__ = "goal_account_mappings"
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    allocation_percentage: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=100)

    goal: Mapped["Goal"] = relationship(back_populates="account_mappings")


class GoalMilestone(Base):
    __tablename__ = "goal_milestones"
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"))
    name: Mapped[str] = mapped_column(String)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    achieved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    goal: Mapped["Goal"] = relationship(back_populates="milestones")


class GoalContribution(Base):
    __tablename__ = "goal_contributions"
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"))
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    contribution_date: Mapped[date] = mapped_column(Date)
    contribution_type: Mapped[str] = mapped_column(String, default="MANUAL")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    goal: Mapped["Goal"] = relationship(back_populates="contributions")
