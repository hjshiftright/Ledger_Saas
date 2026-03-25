"""info command — show store stats and user profile summary."""
from __future__ import annotations

import argparse
from pathlib import Path

from commands._helpers import (
    _bold, _dim, _green, _yellow,
    _get_db_session, _repos, _load_profile,
)


def cmd_info(args: argparse.Namespace) -> int:
    from modules.store import store_stats, get_store_dir
    store_dir    = Path(args.store_dir) if args.store_dir else get_store_dir()
    stats        = store_stats()
    display_name, base_currency = _load_profile(store_dir, args.user_id)

    print()
    print(_bold("  Ledger 3.0 — Info"))

    print(_bold("\n  User"))
    print(f"  {'User ID:':<22} {args.user_id}")
    if display_name != args.user_id:
        print(f"  {'Display name:':<22} {display_name}")
        print(f"  {'Base currency:':<22} {base_currency}")
    else:
        print(_dim("  No profile found. Run: python cli.py onboarding profile"))

    print(_bold("\n  Store"))
    print(f"  {'Directory:':<22} {stats['store_dir']}")
    print(f"  {'Users with data:':<22} {stats['users']}")
    print(f"  {'Total dedup hashes:':<22} {stats['total_hashes']}")

    if display_name != args.user_id:
        try:
            s_repo, _, _ = _repos(store_dir, args.user_id)
            from onboarding.orchestrator.service import OrchestratorService
            state   = OrchestratorService(s_repo).get_state()
            bar_len = 20
            filled  = int(state.progress_percentage / 100 * bar_len)
            bar     = _green("█" * filled) + _dim("░" * (bar_len - filled))
            done    = _green("complete") if state.is_complete else _yellow("in progress")
            completed = sum(1 for s in state.steps if s.status.value == "COMPLETED")
            print(_bold("\n  Onboarding"))
            print(f"  Progress: [{bar}] {state.progress_percentage}%  — {done}")
            print(f"  Steps:    {completed} / {len(state.steps)} done")
        except Exception:
            pass

    print()
    return 0
