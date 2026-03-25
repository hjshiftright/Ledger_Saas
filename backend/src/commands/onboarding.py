"""onboarding sub-commands: profile, status, coa, institution."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from commands._helpers import (
    _bold, _dim, _green, _yellow, _red, _blue,
    _get_db_session, _repos, _load_profile,
)


# ── COA tree renderer (only used by onboarding coa tree) ─────────────────────

def _render_coa_node(node, prefix: str = "", is_last: bool = True) -> None:
    connector = "└─ " if is_last else "├─ "
    code     = node.code if hasattr(node, "code") else node.get("code", "")
    name     = node.name if hasattr(node, "name") else node.get("name", "")
    ntype    = node.type if hasattr(node, "type") else node.get("type", "")
    is_ph    = node.is_placeholder if hasattr(node, "is_placeholder") else node.get("is_placeholder", False)
    children = node.children if hasattr(node, "children") else node.get("children", [])

    line = f"  {prefix}{connector}{_bold(str(code))}  {name}  {_blue(str(ntype))}"
    print(_dim(line) if is_ph else line)

    for i, child in enumerate(children):
        child_prefix = prefix + ("   " if is_last else "│  ")
        _render_coa_node(child, child_prefix, i == len(children) - 1)


# ── onboarding profile ────────────────────────────────────────────────────────

def cmd_onboarding_profile(args: argparse.Namespace) -> int:
    from modules.store import get_store_dir
    store_dir = Path(args.store_dir) if args.store_dir else get_store_dir()

    from repositories.sqla_profile_repo import SqlAlchemyProfileRepository
    from onboarding.profile.service import ProfileService
    from onboarding.profile.schemas import ProfileSetupRequest
    from common.enums import Currency, TaxRegime

    session = _get_db_session()
    ps = ProfileService(SqlAlchemyProfileRepository(session))

    if args.profile_name:
        try:
            req = ProfileSetupRequest(
                display_name=args.profile_name,
                base_currency=Currency(args.profile_currency.upper()),
                financial_year_start_month=int(args.profile_fy_month),
                tax_regime=TaxRegime(args.profile_regime.upper()),
                date_format=args.profile_date_format,
                number_format=args.profile_number_format.upper(),
            )
            profile = ps.setup_profile(req)
        except Exception as exc:
            print(_red(f"  Error: {exc}"), file=sys.stderr)
            return 1
        print()
        print(_green("  Profile saved."))

    elif ps.is_profile_complete():
        profile = ps.get_profile()

    else:
        print()
        print(_bold("  Ledger 3.0 — Profile Setup"))
        print("  No profile found — let's create one.")
        print(_dim("  Press Enter to accept the default shown in [brackets].\n"))
        try:
            name      = input("  Display name: ").strip()
            if not name:
                print(_red("  Display name is required."))
                return 1
            curr_in   = input("  Base currency [INR]: ").strip() or "INR"
            regime_in = input("  Tax regime (NEW / OLD) [NEW]: ").strip().upper() or "NEW"
            fy_in     = input("  Financial year start month (1–12) [4]: ").strip() or "4"
            dfmt_in   = input("  Date format (DD/MM/YYYY | MM/DD/YYYY | YYYY-MM-DD) [DD/MM/YYYY]: ").strip() or "DD/MM/YYYY"
            nfmt_in   = input("  Number format (INDIAN | INTERNATIONAL) [INDIAN]: ").strip().upper() or "INDIAN"
        except (EOFError, KeyboardInterrupt):
            print(_yellow("\n\n  Aborted.\n"))
            return 1
        try:
            req = ProfileSetupRequest(
                display_name=name,
                base_currency=Currency(curr_in.upper()),
                financial_year_start_month=int(fy_in),
                tax_regime=TaxRegime(regime_in),
                date_format=dfmt_in,
                number_format=nfmt_in,
            )
            profile = ps.setup_profile(req)
        except Exception as exc:
            print(_red(f"  Error: {exc}"), file=sys.stderr)
            return 1
        print()
        print(_green("  Profile saved."))

    print()
    print(_bold("  ─── User Profile ────────────────────────────────────────────"))
    print(f"  {'User ID:':<26} {args.user_id}")
    print(f"  {'Display name:':<26} {profile.display_name}")
    print(f"  {'Base currency:':<26} {profile.base_currency}")
    print(f"  {'Tax regime:':<26} {profile.tax_regime}")
    print(f"  {'FY start month:':<26} {profile.financial_year_start_month}")
    print(f"  {'Date format:':<26} {profile.date_format}")
    print(f"  {'Number format:':<26} {profile.number_format}")
    print()
    return 0


# ── onboarding status ─────────────────────────────────────────────────────────

def cmd_onboarding_status(args: argparse.Namespace) -> int:
    from modules.store import get_store_dir
    store_dir = Path(args.store_dir) if args.store_dir else get_store_dir()

    from repositories.sqla_settings_repo import SqlAlchemySettingsRepository
    from onboarding.orchestrator.service import OrchestratorService
    from common.enums import OnboardingStepStatus

    session = _get_db_session()
    s_repo = SqlAlchemySettingsRepository(session)
    orch  = OrchestratorService(s_repo)
    state = orch.get_state()

    _STATUS_ICON = {
        OnboardingStepStatus.COMPLETED:   _green("✓"),
        OnboardingStepStatus.IN_PROGRESS: _yellow("→"),
        OnboardingStepStatus.SKIPPED:     _blue("»"),
        OnboardingStepStatus.PENDING:     _dim("·"),
    }
    _STATUS_LABEL = {
        OnboardingStepStatus.COMPLETED:   _green("COMPLETED"),
        OnboardingStepStatus.IN_PROGRESS: _yellow("IN PROGRESS"),
        OnboardingStepStatus.SKIPPED:     _blue("SKIPPED"),
        OnboardingStepStatus.PENDING:     _dim("PENDING"),
    }

    bar_len  = 28
    filled   = int(state.progress_percentage / 100 * bar_len)
    bar      = _green("█" * filled) + _dim("░" * (bar_len - filled))
    done_tag = _green("COMPLETE ✓") if state.is_complete else _yellow("in progress")

    display_name, _ = _load_profile(store_dir, args.user_id)

    print()
    print(_bold("  ─── Onboarding Status ────────────────────────────────────────"))
    print(f"  User:     {display_name}  ({args.user_id})")
    print(f"  Progress: [{bar}] {state.progress_percentage}%   {done_tag}")
    print()

    for i, step in enumerate(state.steps, 1):
        icon  = _STATUS_ICON.get(step.status, " ")
        label = _STATUS_LABEL.get(step.status, step.status.value)
        name  = step.step.value.replace("_", " ").title()
        print(f"  [{icon}] {i}. {name:<28}  {label}")

    print()
    return 0


# ── onboarding coa ────────────────────────────────────────────────────────────

def cmd_onboarding_coa(args: argparse.Namespace) -> int:
    from modules.store import get_store_dir
    store_dir = Path(args.store_dir) if args.store_dir else get_store_dir()

    from repositories.sqla_account_repo import AccountRepository
    from onboarding.coa.service import COASetupService

    session = _get_db_session()
    svc = COASetupService(AccountRepository(session))

    if args.coa_command == "init":
        if svc.is_coa_ready():
            print(_yellow("\n  COA is already initialized. Use 'coa tree' to view it.\n"))
            return 0
        accounts = svc.create_default_coa()
        print()
        print(_green(f"  COA initialized — {len(accounts)} accounts created."))
        print(_dim("  Tip: run 'onboarding coa tree' to see the full tree."))
        print()

    elif args.coa_command == "tree":
        if not svc.is_coa_ready():
            print(_yellow("\n  COA not initialized yet."))
            print(_dim("  Run: python cli.py onboarding coa init\n"))
            return 0
        tree = svc.get_coa_tree()
        print()
        print(_bold("  ─── Chart of Accounts ────────────────────────────────────────"))
        print(_dim("  (placeholder/group nodes are dimmed)"))
        print()
        for i, root_node in enumerate(tree.items):
            _render_coa_node(root_node, "", i == len(tree.items) - 1)
        print()

    return 0


# ── onboarding institution ────────────────────────────────────────────────────

def cmd_onboarding_institution(args: argparse.Namespace) -> int:
    from modules.store import get_store_dir
    store_dir = Path(args.store_dir) if args.store_dir else get_store_dir()

    from repositories.sqla_institution_repo import SqlAlchemyInstitutionRepository
    from onboarding.institution.service import InstitutionService
    from onboarding.institution.schemas import InstitutionCreateDTO
    from common.enums import InstitutionType

    session = _get_db_session()
    svc = InstitutionService(SqlAlchemyInstitutionRepository(session))

    if args.inst_command == "add":
        try:
            dto = InstitutionCreateDTO(
                name=args.inst_name,
                institution_type=InstitutionType(args.inst_type.upper()),
                website_url=args.inst_website or None,
                notes=args.inst_notes or None,
            )
            created = svc.add_institution(dto)
        except Exception as exc:
            print(_red(f"  Error: {exc}"), file=sys.stderr)
            return 1
        print()
        print(_green(f"  Institution added: [{created.id}] {created.name}  ({created.institution_type.value})"))
        print()

    elif args.inst_command == "list":
        result = svc.list_institutions()
        items  = result.get("items", [])
        print()
        print(_bold("  ─── Institutions ─────────────────────────────────────────────"))
        if not items:
            print(_dim('  (none — add one with: onboarding institution add --name "HDFC Bank" --type BANK)'))
        else:
            print(f"  {'ID':<6} {'Type':<14} Name")
            print("  " + "─" * 52)
            for inst in items:
                iid   = inst["id"]   if isinstance(inst, dict) else inst.id
                itype = inst["institution_type"] if isinstance(inst, dict) else inst.institution_type.value
                iname = inst["name"] if isinstance(inst, dict) else inst.name
                print(f"  {iid:<6} {itype:<14} {iname}")
        print()

    return 0


# ── dispatcher ────────────────────────────────────────────────────────────────

def cmd_onboarding(args: argparse.Namespace) -> int:
    dispatch = {
        "profile":     cmd_onboarding_profile,
        "status":      cmd_onboarding_status,
        "coa":         cmd_onboarding_coa,
        "institution": cmd_onboarding_institution,
    }
    return dispatch[args.ob_command](args)
