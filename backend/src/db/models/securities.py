from sqlalchemy import String, Integer, Boolean, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base
from decimal import Decimal
from datetime import date, datetime

class Security(Base):
    __tablename__ = "securities"
    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    isin: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String)
    security_type: Mapped[str] = mapped_column(String)
    exchange: Mapped[str | None] = mapped_column(String, nullable=True)
    sector: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_category: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_amc: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_plan: Mapped[str | None] = mapped_column(String, nullable=True)
    mf_option: Mapped[str | None] = mapped_column(String, nullable=True)
    face_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    prices: Mapped[list["SecurityPrice"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="selectin"
    )
    tax_lots: Mapped[list["TaxLot"]] = relationship(
        back_populates="security", cascade="all, delete-orphan", lazy="selectin"
    )

class SecurityPrice(Base):
    __tablename__ = "security_prices"
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    price_date: Mapped[date] = mapped_column(Date)
    close_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)

    security: Mapped["Security"] = relationship(back_populates="prices")

class TaxLot(Base):
    __tablename__ = "tax_lots"
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"))
    buy_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    acquisition_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    acquisition_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    status: Mapped[str] = mapped_column(String, default="OPEN")

    security: Mapped["Security"] = relationship(back_populates="tax_lots")
    disposals: Mapped[list["TaxLotDisposal"]] = relationship(
        back_populates="tax_lot", cascade="all, delete-orphan", lazy="selectin"
    )

class TaxLotDisposal(Base):
    __tablename__ = "tax_lot_disposals"
    tax_lot_id: Mapped[int] = mapped_column(ForeignKey("tax_lots.id"))
    sell_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    disposal_date: Mapped[date] = mapped_column(Date)
    quantity_disposed: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    sale_price_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    sale_proceeds: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost_of_acquisition: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    realized_gain_loss: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    holding_period_days: Mapped[int] = mapped_column(Integer)
    gain_type: Mapped[str] = mapped_column(String)
    grandfathering_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    grandfathered_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    tax_lot: Mapped["TaxLot"] = relationship(back_populates="disposals")

class FoContract(Base):
    __tablename__ = "fo_contracts"
    underlying_security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    contract_type: Mapped[str] = mapped_column(String)
    expiry_date: Mapped[date] = mapped_column(Date)
    strike_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    lot_size: Mapped[int] = mapped_column(Integer)
    exchange: Mapped[str] = mapped_column(String, default="NSE")
    contract_symbol: Mapped[str] = mapped_column(String, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class FoPosition(Base):
    __tablename__ = "fo_positions"
    fo_contract_id: Mapped[int] = mapped_column(ForeignKey("fo_contracts.id"))
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"))
    position_type: Mapped[str] = mapped_column(String)
    quantity_lots: Mapped[int] = mapped_column(Integer)
    quantity_units: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    entry_date: Mapped[date] = mapped_column(Date)
    entry_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    exit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exit_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    margin_blocked: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    premium_paid: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    premium_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    settlement_type: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="OPEN")

class HoldingsSummary(Base):
    __tablename__ = "holdings_summary"
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"))
    brokerage_account_id: Mapped[int] = mapped_column(ForeignKey("brokerage_accounts.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    average_cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_invested_value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    latest_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    latest_price_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_market_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unrealized_pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    absolute_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    day_change: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    day_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    last_recomputed_at: Mapped[datetime] = mapped_column(DateTime)
