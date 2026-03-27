from datetime import date
from decimal import Decimal
from sqlalchemy import String, Boolean, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base, TenantScopedMixin


class TaxSection(Base):
    """Global reference table for Indian IT Act sections — not tenant-scoped."""
    __tablename__ = "tax_sections"

    section_code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    max_deduction_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    applicable_regime: Mapped[str] = mapped_column(String, nullable=False, default="OLD")
    financial_year: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TaxLot(TenantScopedMixin, Base):
    __tablename__ = "tax_lots"

    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"), nullable=False)
    brokerage_account_id: Mapped[int] = mapped_column(
        ForeignKey("brokerage_accounts.id"), nullable=False
    )
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)


class TaxLotDisposal(TenantScopedMixin, Base):
    __tablename__ = "tax_lot_disposals"

    tax_lot_id: Mapped[int] = mapped_column(
        ForeignKey("tax_lots.id"), nullable=False, index=True
    )
    disposal_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_disposed: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    sale_price_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)


class TaxSectionMapping(TenantScopedMixin, Base):
    """Per-tenant overrides for Indian IT Act section assignments on accounts."""
    __tablename__ = "tax_section_mappings"

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    tax_section_id: Mapped[int] = mapped_column(ForeignKey("tax_sections.id"), nullable=False)
    override_notes: Mapped[str | None] = mapped_column(String, nullable=True)
