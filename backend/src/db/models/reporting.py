from sqlalchemy import String, Integer, Boolean, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.models.base import Base
from decimal import Decimal
from datetime import date, datetime

class MonthlySnapshot(Base):
    __tablename__ = "monthly_snapshots"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    snapshot_year: Mapped[int] = mapped_column(Integer)
    snapshot_month: Mapped[int] = mapped_column(Integer)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_debits: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    total_credits: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)

class NetWorthHistory(Base):
    __tablename__ = "net_worth_history"
    snapshot_date: Mapped[date] = mapped_column(Date)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    net_worth: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    liquid_assets: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    investment_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

class SavedReport(Base):
    __tablename__ = "saved_reports"
    name: Mapped[str] = mapped_column(String)
    report_type: Mapped[str] = mapped_column(String)
    parameters_json: Mapped[str] = mapped_column(String)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
