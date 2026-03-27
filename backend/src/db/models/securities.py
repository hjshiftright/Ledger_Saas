from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Boolean, Numeric, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, TenantScopedMixin


class Security(Base):
    """Global reference table — not tenant-scoped."""
    __tablename__ = "securities"

    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    isin: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    security_type: Mapped[str] = mapped_column(String, nullable=False)
    exchange: Mapped[str | None] = mapped_column(String, nullable=True)
    sector: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_category: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_amc: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_plan: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_option: Mapped[str | None] = mapped_column(String, nullable=True)
    face_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    prices: Mapped[list["SecurityPrice"]] = relationship(
        back_populates="security", cascade="all, delete-orphan"
    )


class SecurityPrice(Base):
    """Global reference table — not tenant-scoped."""
    __tablename__ = "security_prices"

    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"), nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)

    security: Mapped["Security"] = relationship(back_populates="prices")


class FoContract(Base):
    """Global reference table — not tenant-scoped."""
    __tablename__ = "fo_contracts"

    underlying_security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"), nullable=False)
    contract_type: Mapped[str] = mapped_column(String, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    strike_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False)
    exchange: Mapped[str] = mapped_column(String, nullable=False, default="NSE")
    contract_symbol: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FoPosition(TenantScopedMixin, Base):
    __tablename__ = "fo_positions"

    brokerage_account_id: Mapped[int] = mapped_column(
        ForeignKey("brokerage_accounts.id"), nullable=False, index=True
    )
    fo_contract_id: Mapped[int] = mapped_column(ForeignKey("fo_contracts.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    avg_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    position_date: Mapped[date] = mapped_column(Date, nullable=False)


class HoldingsSummary(TenantScopedMixin, Base):
    __tablename__ = "holdings_summary"

    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"), nullable=False)
    brokerage_account_id: Mapped[int] = mapped_column(
        ForeignKey("brokerage_accounts.id"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "security_id", "brokerage_account_id",
            name="uq_holdings_tenant_sec_brok",
        ),
    )
