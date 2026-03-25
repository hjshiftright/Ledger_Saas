from sqlalchemy import String, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base
from decimal import Decimal

class TaxSection(Base):
    __tablename__ = "tax_sections"
    section_code: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    max_deduction_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    applicable_regime: Mapped[str] = mapped_column(String, default="OLD")
    financial_year: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    mappings: Mapped[list["TaxSectionMapping"]] = relationship(
        back_populates="tax_section", cascade="all, delete-orphan", lazy="selectin"
    )

class TaxSectionMapping(Base):
    __tablename__ = "tax_section_mappings"
    tax_section_id: Mapped[int] = mapped_column(ForeignKey("tax_sections.id"))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    security_id: Mapped[int | None] = mapped_column(ForeignKey("securities.id"), nullable=True)
    transaction_type: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    tax_section: Mapped["TaxSection"] = relationship(back_populates="mappings")
