from fastapi import APIRouter
from .profile.router import router as profile_router
from .coa.router import router as coa_router
from .institution.router import router as institution_router
from .account.router import router as account_router
from .opening_balance.router import router as ob_router
from .networth.router import router as networth_router
from .orchestrator.router import router as orchestrator_router
from .dashboard.router import router as dashboard_router

# Aggregate all onboarding sub-routers
router = APIRouter()

router.include_router(profile_router)
router.include_router(coa_router)
router.include_router(institution_router)
router.include_router(account_router)
router.include_router(ob_router)
router.include_router(networth_router)
router.include_router(orchestrator_router)
router.include_router(dashboard_router)

# Typically, you would include this `router` in `src/ledger/main.py`.
