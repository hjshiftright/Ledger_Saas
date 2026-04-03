"""Ledger 3.0 — CLI entry point.

All command logic lives in the commands/ package:
  commands/_helpers.py    — shared colour/format helpers, DB session, profile loader
  commands/onboarding.py  — onboarding profile/status/coa/institution commands
  commands/cmd_import.py  — import command (one-shot pipeline)
  commands/pipeline.py    — staged pipeline commands (parse/analyze/propose/commit/status)
  commands/info.py        — info command
  commands/parser.py      — build_parser (argument definitions)

Usage:
  python cli.py <command> [options]
  python cli.py --help
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

logging.basicConfig(format="%(name)s: %(message)s", level=logging.WARNING)
logging.getLogger("modules").setLevel(logging.INFO)
logging.getLogger("core").setLevel(logging.INFO)


async def main() -> None:
    from commands.parser import build_parser
    from commands.onboarding import cmd_onboarding
    from commands.cmd_import import cmd_import
    from commands.pipeline import cmd_pipeline
    from commands.info import cmd_info

    parser = build_parser()
    args   = parser.parse_args()

    if args.store_dir:
        os.environ["LEDGER_STORE_DIR"] = args.store_dir

    from modules.store import configure_store_dir, get_store_dir
    configure_store_dir(get_store_dir())

    # Ensure DB tables exist and seed default Chart of Accounts if the accounts table is empty
    from commands._helpers import _get_async_session
    from sqlalchemy import func, select
    _seed = await _get_async_session()
    try:
        from db.models.accounts import Account
        count = await _seed.scalar(select(func.count()).select_from(Account))
        if count == 0:
            from repositories.sqla_account_repo import AccountRepository
            from onboarding.coa.service import COASetupService
            await COASetupService(AccountRepository(_seed)).create_default_coa()
            await _seed.commit()
    except Exception:
        pass
    finally:
        await _seed.close()

    dispatch = {
        "import":     cmd_import,
        "pipeline":   cmd_pipeline,
        "info":       cmd_info,
        "onboarding": cmd_onboarding,
    }
    sys.exit(await dispatch[args.command](args))


if __name__ == "__main__":
    asyncio.run(main())
