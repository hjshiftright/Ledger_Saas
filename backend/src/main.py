"""Ledger 3.0 — FastAPI application entry point.

Start the server:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Or use the built-in runner (reads host/port/debug from settings / .env):
    python main.py
    python main.py --store-dir /data/ledger_store
    python main.py --port 9000

CLI import tool (no server required):
    python cli.py import path/to/statement.csv
    python cli.py import path/to/statement.pdf --account-id my-hdfc --user-id alice
    python cli.py info
"""

from __future__ import annotations

import logging
import mimetypes
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings

# ── User-facing routers ───────────────────────────────────────────────────────
from api.routers.imports          import router as imports_router
from api.routers.llm              import router as llm_router
from api.routers.pipeline         import router as pipeline_router
from api.routers.accounts         import router as coa_accounts_router
from api.routers.proposals        import router as proposals_router
from api.routers.transactions     import router as transactions_router
from api.routers.goals            import router as goals_router
from api.routers.budgets          import router as budgets_router
from api.routers.reports          import router as reports_router
from api.routers.auth             import router as auth_router
from api.routers.chat             import router as chat_router

# ── Onboarding routers (profile, coa, institution, account, ob, networth) ─────
from onboarding.router import router as onboarding_router

# ── Domain error types ────────────────────────────────────────────────────────
from common.exceptions import PFMSError
from common.schemas import ErrorResponse

logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.app_debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    logger.info(
        "Ledger 3.0 starting — env=%s, host=%s, port=%s",
        settings.app_env, settings.app_host, settings.app_port,
    )
    yield
    logger.info("Ledger 3.0 shutting down.")


# ── App factory ───────────────────────────────────────────────────────────────

_OPENAPI_TAGS = [
    {"name": "System",         "description": "Health check and server info."},
    {"name": "profile",        "description": "User profile setup and preferences."},
    {"name": "institutions",   "description": "Financial institutions (banks, brokerages, etc.)."},
    {"name": "accounts",       "description": "Chart of Accounts — onboarding accounts."},
    {"name": "coa",            "description": "Chart of Accounts — full COA tree."},
    {"name": "opening_balances", "description": "Set opening balances during onboarding."},
    {"name": "net_worth",      "description": "Net-worth snapshots."},
    {"name": "orchestrator",   "description": "Onboarding step progress."},
    {"name": "Imports",          "description": "Upload and detect statement files."},
    {"name": "Import Pipeline",  "description": "Parse then smart-process a batch (normalize → dedup → categorize → score → propose)."},
    {"name": "Proposals",        "description": "Review, approve, and commit proposed journal entries."},
    {"name": "LLM",              "description": "Manage LLM providers."},
    {"name": "Import Accounts",  "description": "Chart of Accounts CRUD."},
    {"name": "Transactions",     "description": "List committed (posted) transactions."},
    {"name": "Goals",            "description": "Financial goals CRUD with progress tracking."},
    {"name": "Budgets",          "description": "Budget plans with per-category spending limits."},
]


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Ledger 3.0 API",
        description=(
            "AI-powered personal finance ledger with double-entry accounting, "
            "onboarding wizard, statement import pipeline, and reporting."
        ),
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=_OPENAPI_TAGS,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request timing middleware ─────────────────────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        logger.info(
            "%s %s → %s (%.0fms)",
            request.method,
            request.url.path + (f"?{request.url.query}" if request.url.query else ""),
            response.status_code,
            (time.time() - start) * 1000,
        )
        return response

    # ── Exception handlers ────────────────────────────────────────────────────

    @app.exception_handler(PFMSError)
    async def pfms_error_handler(request: Request, exc: PFMSError):
        _STATUS_MAP = {
            "VALIDATION_ERROR": 422,
            "NOT_FOUND": 404,
            "DUPLICATE": 409,
            "SYSTEM_ACCOUNT": 403,
            "BUSINESS_RULE": 400,
            "ONBOARDING_SEQUENCE": 409,
        }
        status_code = _STATUS_MAP.get(exc.error_code, 400)
        logger.warning("PFMSError [%s] %s → %s", exc.error_code, request.url.path, exc.message)
        return JSONResponse(
            status_code=status_code,
            content=ErrorResponse(error_code=exc.error_code, message=exc.message).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": jsonable_encoder(exc.errors()),
            },
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={"error": "NOT_FOUND", "message": f"Path '{request.url.path}' not found."},
        )

    @app.exception_handler(500)
    async def server_error_handler(request: Request, exc):
        logger.exception("Unhandled server error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
        )

    # ── Health check ──────────────────────────────────────────────────────────

    @app.get("/health", tags=["System"], summary="Health check")
    def health():
        s = get_settings()
        return {
            "status": "ok",
            "version": "3.0.0",
            "env": s.app_env,
            "database": s.database_url,
            "llm_providers": {
                "gemini": s.has_gemini(),
                "openai": s.has_openai(),
                "anthropic": s.has_anthropic(),
            },
        }

    # Root redirection (optional, but since we mount at root, this is redundant if html=True)
    # However, keeping it doesn't hurt if we want a specific behavior.
    # Let's just remove it and let StaticFiles handle it.

    # ── Mount routers ─────────────────────────────────────────────────────────
    PREFIX = "/api/v1"

    # Onboarding (profile, coa, institution, account, opening_balance, networth, orchestrator)
    app.include_router(onboarding_router)

    # Import pipeline (user-facing)
    app.include_router(coa_accounts_router,     prefix=PREFIX)
    app.include_router(imports_router,          prefix=PREFIX)
    app.include_router(llm_router,              prefix=PREFIX)
    app.include_router(pipeline_router,         prefix=PREFIX)
    app.include_router(proposals_router,        prefix=PREFIX)

    # Committed transactions, goals, budgets, reports
    app.include_router(transactions_router, prefix=PREFIX)
    app.include_router(goals_router,        prefix=PREFIX)
    app.include_router(budgets_router,      prefix=PREFIX)
    app.include_router(reports_router,      prefix=PREFIX)
    app.include_router(chat_router,         prefix=PREFIX)
    app.include_router(auth_router)  # Auth routes (already have /api/v1/auth prefix)

    # ── Serve compiled frontend ───────────────────────────────────────────────
    import os
    from pathlib import Path
    
    # On Windows, mimetypes.guess_type() often returns 'text/plain' for .js files
    # if the registry is messed up. Explicitly add them to ensure correct headers.
    mimetypes.add_type('application/javascript', '.js')
    mimetypes.add_type('text/css', '.css')
    
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
        logger.info("Frontend served from root %s", frontend_dist)

    return app


app = create_app()


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Ledger 3.0 API server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host",      default=None, help="Bind host (overrides APP_HOST)")
    parser.add_argument("--port",      type=int, default=None, help="Bind port (overrides APP_PORT)")
    parser.add_argument("--reload",    action="store_true", help="Enable auto-reload (dev)")
    parser.add_argument("--store-dir", default=None, dest="store_dir",
                        help="Path for the JSON persistence store (overrides LEDGER_STORE_DIR)")
    args = parser.parse_args()

    settings = get_settings()

    if args.store_dir:
        import os
        os.environ["LEDGER_STORE_DIR"] = args.store_dir

    uvicorn.run(
        "main:app",
        host=args.host or settings.app_host,
        port=args.port or settings.app_port,
        reload=args.reload,
        log_level="debug" if settings.app_debug else "info",
    )
