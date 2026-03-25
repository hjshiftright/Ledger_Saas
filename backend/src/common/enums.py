from enum import Enum

class Currency(str, Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

class TaxRegime(str, Enum):
    OLD = "OLD"
    NEW = "NEW"

class InstitutionType(str, Enum):
    BANK = "BANK"
    NBFC = "NBFC"
    BROKERAGE = "BROKERAGE"
    AMC = "AMC"
    INSURANCE = "INSURANCE"
    GOVERNMENT = "GOVERNMENT"
    OTHER = "OTHER"

class BankAccountType(str, Enum):
    SAVINGS = "SAVINGS"
    CURRENT = "CURRENT"
    SALARY = "SALARY"

class LoanType(str, Enum):
    HOME = "HOME"
    VEHICLE = "VEHICLE"
    PERSONAL = "PERSONAL"
    EDUCATION = "EDUCATION"
    GOLD = "GOLD"
    OTHER = "OTHER"

class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    EQUITY = "EQUITY"

class NormalBalance(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class OnboardingStep(str, Enum):
    PROFILE = "PROFILE"
    COA_SETUP = "COA_SETUP"
    INSTITUTION_SETUP = "INSTITUTION_SETUP"
    ACCOUNT_SETUP = "ACCOUNT_SETUP"
    OPENING_BALANCES = "OPENING_BALANCES"
    GOAL_PLANNING = "GOAL_PLANNING"
    BUDGET_SETUP = "BUDGET_SETUP"
    RECURRING_SETUP = "RECURRING_SETUP"
    NETWORTH_REVIEW = "NETWORTH_REVIEW"

class OnboardingStepStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
