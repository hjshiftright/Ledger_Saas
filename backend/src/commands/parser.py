"""build_parser — argument parser for the Ledger 3.0 CLI."""
from __future__ import annotations

import argparse
import textwrap


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="ledger",
        description="Ledger 3.0 — personal finance CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python cli.py onboarding profile --name "Rahul"
              python cli.py onboarding coa init
              python cli.py onboarding institution add --name "HDFC Bank" --type BANK
              python cli.py onboarding status
              python cli.py import statement.csv --account-id HDFC-SAV-1234
              python cli.py pipeline parse statement.pdf
              python cli.py pipeline analyze <batch_id>
              python cli.py pipeline propose <batch_id>
              python cli.py pipeline commit  <batch_id>
              python cli.py info
              python cli.py --user-id alice import statement.csv
        """),
    )
    root.add_argument(
        "--store-dir", default=None, dest="store_dir",
        help="JSON persistence directory (default: ./ledger_store or $LEDGER_STORE_DIR)",
    )
    root.add_argument(
        "--user-id", default="cli-user", dest="user_id",
        help="User identifier — scopes profile, dedup hashes, categorize rules (default: cli-user)",
    )

    sub = root.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── import ────────────────────────────────────────────────────────────
    p_import = sub.add_parser("import", help="Parse and import a statement file (one-shot)")
    p_import.add_argument("file", help="Path to the statement (PDF, CSV, XLS, XLSX)")
    p_import.add_argument("--account-id",   default="", dest="account_id",
                          help="Account identifier used in dedup hash (default: auto from filename)")
    p_import.add_argument("--account-type", default="BANK", dest="account_type",
                          choices=["BANK", "CREDIT_CARD"],
                          help="Statement account type: BANK (default) or CREDIT_CARD")
    p_import.add_argument("--source-type",  default="", dest="source_type",
                          help="Force source type (e.g. HDFC_BANK_CSV, ZERODHA_TRADEBOOK)")
    p_import.add_argument("--password",     default="", dest="password",
                          help="PDF password for encrypted statements (prompted interactively if omitted)")
    p_import.add_argument("--llm",          action="store_true", default=False, dest="use_llm",
                          help="Enable LLM-assisted categorization using the configured provider")
    p_import.add_argument("--provider-id",  default="", dest="provider_id",
                          help="LLM provider ID to use (default: your default provider)")
    p_import.add_argument("--llm-all",      action="store_true", default=False, dest="llm_all",
                          help="Run LLM on ALL rows, not just low-confidence ones (implies --llm)")

    # ── pipeline ──────────────────────────────────────────────────────────
    p_pipe   = sub.add_parser("pipeline", help="Staged import pipeline (parse → analyze → propose → commit)")
    pipe_sub = p_pipe.add_subparsers(dest="pl_command", metavar="STAGE")
    pipe_sub.required = True

    p_pl_parse = pipe_sub.add_parser("parse", help="Stage 1: detect + parse a statement file")
    p_pl_parse.add_argument("file", help="Path to the statement (PDF, CSV, XLS, XLSX)")
    p_pl_parse.add_argument("--account-id",   default="", dest="account_id")
    p_pl_parse.add_argument("--account-type", default="BANK", dest="account_type",
                            choices=["BANK", "CREDIT_CARD"])
    p_pl_parse.add_argument("--source-type",  default="", dest="source_type")
    p_pl_parse.add_argument("--password",     default="", dest="password")
    p_pl_parse.add_argument("--llm",          action="store_true", default=False, dest="use_llm",
                            help="Enable LLM vision fallback for scanned / image-only PDFs")
    p_pl_parse.add_argument("--provider-id",  default="", dest="provider_id",
                            help="LLM provider ID to use (default: your configured default)")

    p_pl_analyze = pipe_sub.add_parser("analyze", help="Stage 2: normalize + dedup + categorize")
    p_pl_analyze.add_argument("batch_id")
    p_pl_analyze.add_argument("--llm",         action="store_true", default=False, dest="use_llm",
                              help="Enable LLM-assisted categorization")
    p_pl_analyze.add_argument("--provider-id", default="", dest="provider_id",
                              help="LLM provider ID to use (default: your default provider)")
    p_pl_analyze.add_argument("--llm-all",     action="store_true", default=False, dest="llm_all",
                              help="Run LLM on ALL rows, not just low-confidence ones")

    p_pl_propose = pipe_sub.add_parser("propose", help="Stage 3: generate + review journal entries")
    p_pl_propose.add_argument("batch_id")

    p_pl_commit = pipe_sub.add_parser("commit", help="Stage 4: commit approved entries to database")
    p_pl_commit.add_argument("batch_id")

    p_pl_status = pipe_sub.add_parser("status", help="List saved batches or show batch detail")
    p_pl_status.add_argument("batch_id", nargs="?", default=None,
                             help="Batch ID to inspect (omit to list all)")

    # ── info ──────────────────────────────────────────────────────────────
    sub.add_parser("info", help="Show store stats and user profile summary")

    # ── onboarding ────────────────────────────────────────────────────────
    p_ob   = sub.add_parser("onboarding", help="Manage user profile and financial setup")
    ob_sub = p_ob.add_subparsers(dest="ob_command", metavar="SUBCOMMAND")
    ob_sub.required = True

    p_prof = ob_sub.add_parser("profile", help="Setup or show the user profile")
    p_prof.add_argument("--name",          default="", dest="profile_name",
                        help="Display name (omit to show current profile or enter wizard mode)")
    p_prof.add_argument("--currency",      default="INR", dest="profile_currency",
                        help="Base currency (default: INR)")
    p_prof.add_argument("--regime",        default="NEW", dest="profile_regime",
                        help="Tax regime: NEW or OLD (default: NEW)")
    p_prof.add_argument("--fy-month",      default=4, type=int, dest="profile_fy_month",
                        help="Financial year start month 1–12 (default: 4 = April)")
    p_prof.add_argument("--date-format",   default="DD/MM/YYYY", dest="profile_date_format",
                        help="Date format (default: DD/MM/YYYY)")
    p_prof.add_argument("--number-format", default="INDIAN", dest="profile_number_format",
                        help="Number format: INDIAN or INTERNATIONAL (default: INDIAN)")

    ob_sub.add_parser("status", help="Show onboarding step completion status")

    p_coa   = ob_sub.add_parser("coa", help="Chart of Accounts management")
    coa_sub = p_coa.add_subparsers(dest="coa_command", metavar="ACTION")
    coa_sub.required = True
    coa_sub.add_parser("init", help="Initialize the default Chart of Accounts tree")
    coa_sub.add_parser("tree", help="Display the Chart of Accounts tree")

    p_inst   = ob_sub.add_parser("institution", help="Manage financial institutions")
    inst_sub = p_inst.add_subparsers(dest="inst_command", metavar="ACTION")
    inst_sub.required = True

    p_inst_add = inst_sub.add_parser("add", help="Register a new institution")
    p_inst_add.add_argument("--name",    required=True, dest="inst_name",
                            help="Institution name (e.g. 'HDFC Bank')")
    p_inst_add.add_argument("--type",    default="BANK", dest="inst_type",
                            choices=["BANK", "NBFC", "BROKERAGE", "AMC",
                                     "INSURANCE", "GOVERNMENT", "OTHER"],
                            help="Institution type (default: BANK)")
    p_inst_add.add_argument("--website", default="", dest="inst_website",
                            help="Website URL (optional)")
    p_inst_add.add_argument("--notes",   default="", dest="inst_notes",
                            help="Free-text notes (optional)")

    inst_sub.add_parser("list", help="List all institutions")

    return root
