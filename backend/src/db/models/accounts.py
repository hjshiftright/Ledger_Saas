from sqlalchemy import String, Integer, Boolean, Numeric, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.models.base import Base
from decimal import Decimal
from datetime import date, datetime
from db.models.base import TenantScopedMixin

class Currency(Base):
    __tablename__ = "currencies"
    code: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String)
    decimal_places: Mapped[int] = mapped_column(Integer, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Account(TenantScopedMixin, Base):
    __tablename__ = "accounts"

    parent_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    account_type: Mapped[str] = mapped_column(String, nullable=False)
    account_subtype: Mapped[str | None] = mapped_column(String, nullable=True)
    currency_code: Mapped[str] = mapped_column(String, default="INR")
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    normal_balance: Mapped[str] = mapped_column(String, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        # Account codes are unique within a tenant, not globally
        UniqueConstraint("tenant_id", "code", name="uq_account_tenant_code"),
    )

    # Self-referential hierarchy
    parent: Mapped["Account | None"] = relationship(
        remote_side="Account.id", back_populates="children"
    )
    children: Mapped[list["Account"]] = relationship(back_populates="parent")

class FinancialInstitution(TenantScopedMixin, Base):
    __tablename__ = "financial_institutions"
    name: Mapped[str] = mapped_column(String)
    institution_type: Mapped[str] = mapped_column(String)
    logo_path: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    bank_accounts: Mapped[list["BankAccount"]] = relationship(back_populates="institution")
    fixed_deposits: Mapped[list["FixedDeposit"]] = relationship(back_populates="institution")
    credit_cards: Mapped[list["CreditCard"]] = relationship(back_populates="institution")
    loans: Mapped[list["Loan"]] = relationship(back_populates="institution")
    brokerage_accounts: Mapped[list["BrokerageAccount"]] = relationship(back_populates="institution")

class BankAccount(TenantScopedMixin, Base):
    __tablename__ = "bank_accounts"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("financial_institutions.id"))
    account_number_masked: Mapped[str | None] = mapped_column(String, nullable=True)
    bank_account_type: Mapped[str] = mapped_column(String)
    ifsc_code: Mapped[str | None] = mapped_column(String, nullable=True)
    branch_name: Mapped[str | None] = mapped_column(String, nullable=True)
    nominee_name: Mapped[str | None] = mapped_column(String, nullable=True)
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped["FinancialInstitution"] = relationship(back_populates="bank_accounts")
    account: Mapped["Account"] = relationship()

class FixedDeposit(TenantScopedMixin, Base):
    __tablename__ = "fixed_deposits"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("financial_institutions.id"))
    fd_number: Mapped[str | None] = mapped_column(String, nullable=True)
    deposit_type: Mapped[str] = mapped_column(String)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    compounding_frequency: Mapped[str] = mapped_column(String, default="QUARTERLY")
    deposit_date: Mapped[date] = mapped_column(Date)
    maturity_date: Mapped[date] = mapped_column(Date)
    maturity_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped["FinancialInstitution"] = relationship(back_populates="fixed_deposits")
    account: Mapped["Account"] = relationship()

class CreditCard(TenantScopedMixin, Base):
    __tablename__ = "credit_cards"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("financial_institutions.id"))
    card_number_masked: Mapped[str | None] = mapped_column(String, nullable=True)
    card_network: Mapped[str | None] = mapped_column(String, nullable=True)
    card_variant: Mapped[str | None] = mapped_column(String, nullable=True)
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    billing_cycle_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_due_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    reward_program_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped["FinancialInstitution"] = relationship(back_populates="credit_cards")
    account: Mapped["Account"] = relationship()

class Loan(TenantScopedMixin, Base):
    __tablename__ = "loans"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("financial_institutions.id"))
    loan_account_number: Mapped[str | None] = mapped_column(String, nullable=True)
    loan_type: Mapped[str] = mapped_column(String)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    current_outstanding: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    interest_type: Mapped[str] = mapped_column(String, default="FLOATING")
    tenure_months: Mapped[int] = mapped_column(Integer)
    emi_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    disbursement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    emi_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    linked_asset_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    prepayment_charges_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped["FinancialInstitution"] = relationship(back_populates="loans")
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])

class BrokerageAccount(TenantScopedMixin, Base):
    __tablename__ = "brokerage_accounts"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("financial_institutions.id"))
    account_identifier: Mapped[str | None] = mapped_column(String, nullable=True)
    brokerage_account_type: Mapped[str] = mapped_column(String)
    depository: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    institution: Mapped["FinancialInstitution"] = relationship(back_populates="brokerage_accounts")
    account: Mapped["Account"] = relationship()

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    # Using String for currency_code to avoid FK issues with base class ID vs code.
    from_currency_code: Mapped[str] = mapped_column(String)
    to_currency_code: Mapped[str] = mapped_column(String)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    rate_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
