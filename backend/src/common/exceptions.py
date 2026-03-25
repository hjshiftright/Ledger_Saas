class PFMSError(Exception):
    """Base exception for all ledger errors."""
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class ValidationError(PFMSError):
    """Input validation failure."""
    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")

class NotFoundError(PFMSError):
    """Requested entity does not exist."""
    def __init__(self, entity: str, identifier: str | int):
        super().__init__(f"{entity} '{identifier}' not found", "NOT_FOUND")

class DuplicateError(PFMSError):
    """Entity with same unique key already exists."""
    def __init__(self, entity: str, key: str):
        super().__init__(f"{entity} with '{key}' already exists", "DUPLICATE")

class SystemAccountError(PFMSError):
    """Attempt to modify a system-managed account."""
    def __init__(self, account_name: str):
        super().__init__(
            f"Cannot modify system account '{account_name}'",
            "SYSTEM_ACCOUNT"
        )

class BusinessRuleError(PFMSError):
    """Domain/business rule violation."""
    def __init__(self, message: str):
        super().__init__(message, "BUSINESS_RULE")

class OnboardingSequenceError(PFMSError):
    """Onboarding steps accessed out of order."""
    def __init__(self, message: str):
        super().__init__(message, "ONBOARDING_SEQUENCE")
