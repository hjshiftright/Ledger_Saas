# Import all model modules so that Base.metadata is fully populated.
# Alembic env.py and tests/conftest.py rely on this.
from db.models import (  # noqa: F401
    users,
    tenants,
    accounts,
    transactions,
    goals,
    budgets,
    imports,
    recurring,
    reporting,
    categories,
    system,
    tax,
    securities,
)
