from datetime import date
from decimal import Decimal
from sqlalchemy import String, Numeric, Date, Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base, TenantScopedMixin


class MonthlySnapshot(TenantScopedMixin, Base):
    __tablename__ = "monthly_snapshots"

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    snapshot_year: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_month: Mapped[int] = mapped_column(Integer, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_debits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "account_id", "snapshot_year", "snapshot_month",
            name="uq_snapshot_tenant_account_period",
        ),
    )


class NetWorthHistory(TenantScopedMixin, Base):
    __tablename__ = "net_worth_history"

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    net_worth: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)


class SavedReport(TenantScopedMixin, Base):
    __tablename__ = "saved_reports"

    name: Mapped[str] = mapped_column(String, nullable=False)
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    parameters_json: Mapped[str | None] = mapped_column(String, nullable=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
