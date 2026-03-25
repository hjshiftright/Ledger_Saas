"""pipeline commands — staged import: parse → analyze → propose → commit."""
from __future__ import annotations

import argparse
import getpass
import json
import sys
import uuid
from decimal import Decimal
from pathlib import Path

from commands._helpers import (
    _bold, _dim, _green, _yellow, _red,
    _band_colour, _fmt_amount, _truncate,
    _get_db_session, _load_profile, _store_stats_line,
    _resolve_llm_provider,
)


# ── Batch state persistence ───────────────────────────────────────────────────

def _batch_dir(store_dir: Path, batch_id: str) -> Path:
    d = store_dir / "batches" / batch_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_batch_meta(store_dir: Path, meta: dict) -> None:
    p = _batch_dir(store_dir, meta["batch_id"]) / "batch.json"
    p.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _load_batch_meta(store_dir: Path, batch_id: str) -> dict | None:
    p = _batch_dir(store_dir, batch_id) / "batch.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _save_raw_rows(store_dir: Path, batch_id: str, rows: list) -> None:
    p = _batch_dir(store_dir, batch_id) / "raw_rows.json"
    p.write_text(json.dumps([r.model_dump(mode="json") for r in rows], indent=2), encoding="utf-8")


def _load_raw_rows(store_dir: Path, batch_id: str) -> list:
    from core.models.raw_parsed_row import RawParsedRow
    p = _batch_dir(store_dir, batch_id) / "raw_rows.json"
    if not p.is_file():
        return []
    return [RawParsedRow(**r) for r in json.loads(p.read_text(encoding="utf-8"))]


def _norm_to_dict(r) -> dict:
    return {
        "row_id": r.row_id, "batch_id": r.batch_id, "source_type": r.source_type,
        "txn_date": str(r.txn_date) if r.txn_date else None,
        "raw_date": r.raw_date, "amount": str(r.amount), "is_debit": r.is_debit,
        "raw_debit": r.raw_debit, "raw_credit": r.raw_credit, "raw_balance": r.raw_balance,
        "closing_balance": str(r.closing_balance) if r.closing_balance is not None else None,
        "narration": r.narration, "raw_narration": r.raw_narration, "reference": r.reference,
        "txn_type": r.txn_type.value, "row_confidence": r.row_confidence,
        "extra_fields": r.extra_fields, "parse_warnings": r.parse_warnings,
    }


def _dict_to_norm(d: dict):
    from datetime import date as _date
    from core.models.enums import TxnTypeHint
    from services.normalize_service import NormalizedTransaction
    return NormalizedTransaction(
        row_id=d["row_id"], batch_id=d["batch_id"], source_type=d["source_type"],
        txn_date=_date.fromisoformat(d["txn_date"]) if d.get("txn_date") else None,
        raw_date=d["raw_date"], amount=Decimal(d["amount"]), is_debit=d["is_debit"],
        raw_debit=d.get("raw_debit"), raw_credit=d.get("raw_credit"),
        raw_balance=d.get("raw_balance"),
        closing_balance=Decimal(d["closing_balance"]) if d.get("closing_balance") else None,
        narration=d["narration"], raw_narration=d["raw_narration"],
        reference=d.get("reference"), txn_type=TxnTypeHint(d["txn_type"]),
        row_confidence=d["row_confidence"],
        extra_fields=d.get("extra_fields", {}), parse_warnings=d.get("parse_warnings", []),
    )


def _save_normalized(store_dir: Path, batch_id: str, rows: list) -> None:
    p = _batch_dir(store_dir, batch_id) / "normalized.json"
    p.write_text(json.dumps([_norm_to_dict(r) for r in rows], indent=2), encoding="utf-8")


def _load_normalized(store_dir: Path, batch_id: str) -> list:
    p = _batch_dir(store_dir, batch_id) / "normalized.json"
    if not p.is_file():
        return []
    return [_dict_to_norm(d) for d in json.loads(p.read_text(encoding="utf-8"))]


def _proposal_to_dict(p) -> dict:
    return {
        "proposal_id": p.proposal_id, "batch_id": p.batch_id, "row_id": p.row_id,
        "txn_date": str(p.txn_date) if p.txn_date else None,
        "narration": p.narration, "reference": p.reference,
        "lines": [{"account_id": l.account_id, "account_code": l.account_code,
                   "account_name": l.account_name, "debit": str(l.debit),
                   "credit": str(l.credit), "is_inferred": l.is_inferred}
                  for l in p.lines],
        "overall_confidence": p.overall_confidence,
        "confidence_band": p.confidence_band, "status": p.status,
        "txn_hash": p.txn_hash,
    }


def _dict_to_proposal(d: dict):
    from datetime import date as _date
    from services.proposal_service import ProposedJournalEntry, JournalEntryLine
    lines = [
        JournalEntryLine(
            account_id=l["account_id"], account_code=l["account_code"],
            account_name=l["account_name"], debit=Decimal(l["debit"]),
            credit=Decimal(l["credit"]), is_inferred=l.get("is_inferred", True),
        )
        for l in d["lines"]
    ]
    return ProposedJournalEntry(
        proposal_id=d["proposal_id"], batch_id=d["batch_id"], row_id=d["row_id"],
        txn_date=_date.fromisoformat(d["txn_date"]) if d.get("txn_date") else None,
        narration=d["narration"], reference=d.get("reference"), lines=lines,
        overall_confidence=d["overall_confidence"],
        confidence_band=d["confidence_band"], status=d["status"],
        txn_hash=d.get("txn_hash"),
    )


def _save_proposals(store_dir: Path, batch_id: str, proposals: list) -> None:
    p = _batch_dir(store_dir, batch_id) / "proposals.json"
    p.write_text(json.dumps([_proposal_to_dict(pr) for pr in proposals], indent=2), encoding="utf-8")


def _load_proposals(store_dir: Path, batch_id: str) -> list:
    p = _batch_dir(store_dir, batch_id) / "proposals.json"
    if not p.is_file():
        return []
    return [_dict_to_proposal(d) for d in json.loads(p.read_text(encoding="utf-8"))]


def _confirm(prompt: str = "  Continue? [Y/n]: ") -> bool:
    try:
        ans = input(prompt).strip().lower()
        return ans in ("", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False


# ── Stage 1: parse ────────────────────────────────────────────────────────────

def cmd_pipeline_parse(args: argparse.Namespace) -> int:
    """Stage 1 — detect source type + parse file into raw rows."""
    path = Path(args.file)
    if not path.is_file():
        print(_red(f"  Error: file not found: {path}"), file=sys.stderr)
        return 1

    from modules.store import get_store_dir
    store_dir = Path(args.store_dir) if args.store_dir else get_store_dir()
    _, base_currency = _load_profile(store_dir, args.user_id)

    file_bytes = path.read_bytes()
    batch_id   = str(uuid.uuid4())
    account_id = args.account_id or f"CLI-{path.stem.upper()[:20]}"

    from core.models.source_map import get_source_account as _get_src_acct
    _src_info_early = _get_src_acct(account_type_override=args.account_type or None)
    source_account_code  = _src_info_early.account_code
    source_account_name  = _src_info_early.account_name
    source_account_class = _src_info_early.account_class

    if path.suffix.lower() == ".pdf":
        from core.utils.pdf_utils import is_pdf_encrypted, decrypt_pdf_bytes
        if is_pdf_encrypted(file_bytes):
            pwd = args.password
            if not pwd:
                import re as _re  # noqa: PLC0415
                _cas_re = _re.compile(r"cas.*cams|cams.*cas|camsonline|cas.*kfin|kfin.*cas|kfintech|mf.?central|\bcas\b", _re.I)
                _ubi_re = _re.compile(r"union.?bank|unionbank", _re.I)
                if _cas_re.search(path.name):
                    print(_yellow("  Hint: For CAS statements (CAMS / KFintech) your PAN is the password (e.g. ABCDE1234F)."))
                elif _ubi_re.search(path.name):
                    print(_yellow("  Hint: For Union Bank monthly statements the password is your date of birth (DDMMYYYY, e.g. 15081985)."))
                try:
                    pwd = getpass.getpass(f"  Password for {path.name}: ")
                except (EOFError, KeyboardInterrupt):
                    print(_yellow("\n  Aborted."))
                    return 1
            try:
                file_bytes = decrypt_pdf_bytes(file_bytes, pwd)
            except ValueError as exc:
                print(_red(f"  Error: {exc}"), file=sys.stderr)
                return 1

    elif file_bytes[:4] == b"\xD0\xCF\x11\xE0":
        # OLE2 container — may be an encrypted XLSX (SBI / HDFC new format).
        # Try to detect + decrypt without requiring the .xlsx extension.
        try:
            import io as _io
            import msoffcrypto
            _office = msoffcrypto.OfficeFile(_io.BytesIO(file_bytes))
            if _office.is_encrypted():
                pwd = args.password
                if not pwd:
                    try:
                        pwd = getpass.getpass(f"  Password for {path.name}: ")
                    except (EOFError, KeyboardInterrupt):
                        print(_yellow("\n  Aborted."))
                        return 1
                try:
                    _office.load_key(password=pwd)
                    _dec_buf = _io.BytesIO()
                    _office.decrypt(_dec_buf)
                    file_bytes = _dec_buf.getvalue()
                except Exception as exc:  # noqa: BLE001
                    print(_red(f"  Error: could not decrypt file — {exc}"), file=sys.stderr)
                    return 1
        except ImportError:
            print(_yellow("  Warning: msoffcrypto-tool not installed — cannot decrypt encrypted spreadsheets."))
        except Exception:  # noqa: BLE001
            pass  # not encrypted OLE2 — continue with original bytes

    print()
    print(_bold("  Ledger 3.0 — Stage 1: Parse"))
    print(f"  {'File:':<18} {path.name}  ({len(file_bytes):,} bytes)")
    print(f"  {'Account:':<18} {account_id}  ({args.account_type or 'BANK'})")
    print(f"  {'Batch ID:':<18} {batch_id}")

    from modules.parser.detector import SourceDetector
    from core.models.enums import SourceType
    if args.source_type:
        try:
            detected_source = SourceType(args.source_type)
        except ValueError:
            print(_red(f"  Error: unknown source type '{args.source_type}'"), file=sys.stderr)
            return 1
        print(f"  {'Source type:':<18} {detected_source.value}  {_yellow('(forced)')}")
    else:
        det = SourceDetector().detect(filename=path.name, file_bytes=file_bytes)
        detected_source = det.source_type
        conf_tag = _green(f"{det.confidence:.0%}") if det.confidence >= 0.70 \
                   else _yellow(f"{det.confidence:.0%}")
        print(f"  {'Source type:':<18} {detected_source.value}  (confidence {conf_tag})")

    # Refine source account from detected SourceType if no explicit --account-type
    if not args.account_type:
        from core.models.source_map import get_source_account as _get_src_acct2
        _src_info = _get_src_acct2(source_type=detected_source)
        source_account_code  = _src_info.account_code
        source_account_name  = _src_info.account_name
        source_account_class = _src_info.account_class

    print(f"\n  Parsing…", end="", flush=True)
    from modules.parser.registry import ParserRegistry
    from modules.parser.chain import ExtractionChain
    from core.models.enums import ParseStatus

    parser = ParserRegistry.default().get(detected_source)
    if parser is None:
        print(_red(f"\n  Error: no parser for {detected_source.value}"))
        return 1

    # Resolve LLM provider for parse-time fallback (scanned/image PDFs)
    _parse_llm = None
    if getattr(args, "use_llm", False):
        try:
            _p_sess = _get_db_session()
            _parse_llm = _resolve_llm_provider(
                _p_sess, args.user_id, getattr(args, "provider_id", None) or None
            )
            _p_sess.close()
        except Exception:
            pass

    result = ExtractionChain(parser, batch_id, file_bytes, filename=path.name).run(llm_provider=_parse_llm)
    print(f"  {_green('done')}")

    if result.status == ParseStatus.FAILED or not result.rows:
        print(_red("  Parse failed — no rows extracted."))
        if result.error_message:
            print(f"  {result.error_message}")
        return 1

    conf_tag = _green(f"{result.metadata.overall_confidence:.0%}") \
        if result.metadata.overall_confidence >= 0.75 else _yellow(f"{result.metadata.overall_confidence:.0%}")
    print(f"  {'Rows found:':<18} {len(result.rows)}")
    print(f"  {'Parse confidence:':<18} {conf_tag}")
    print(f"  {'Method:':<18} {result.metadata.extraction_method.value}")

    print()
    print(_bold("  ─── Raw Transactions ─────────────────────────────────────────────"))
    print(f"  {'#':<5} {'Date':<13} {'Narration':<45} {'Debit':>12}  {'Credit':>12}")
    print("  " + "─" * 90)
    for i, row in enumerate(result.rows, 1):
        narr = _truncate(row.raw_narration or "", 44)
        deb  = row.raw_debit  or ""
        cre  = row.raw_credit or ""
        print(f"  {i:<5} {(row.raw_date or ''):<13} {narr:<45} {deb:>12}  {cre:>12}")
    print()

    _save_batch_meta(store_dir, {
        "batch_id": batch_id, "stage": "parsed",
        "source_type": detected_source.value,
        "account_id": account_id, "account_type": args.account_type or "BANK",
        "source_account_code": source_account_code,
        "source_account_name": source_account_name,
        "source_account_class": source_account_class,
        "filename": path.name, "base_currency": base_currency,
        "user_id": args.user_id,
    })
    _save_raw_rows(store_dir, batch_id, result.rows)
    print(_dim(f"  Batch saved → {_batch_dir(store_dir, batch_id)}"))
    print()
    print(_bold(f"  Next: python cli.py pipeline analyze {batch_id}"))

    if _confirm("\n  Continue to Stage 2 — Analyze now? [Y/n]: "):
        args.batch_id = batch_id
        return cmd_pipeline_analyze(args)
    return 0


# ── Stage 2: analyze ──────────────────────────────────────────────────────────

def cmd_pipeline_analyze(args: argparse.Namespace) -> int:
    """Stage 2 — normalize + dedup + categorize + score. Allow category corrections."""
    from modules.store import get_store_dir
    store_dir = Path(args.store_dir) if args.store_dir else get_store_dir()
    batch_id  = args.batch_id

    meta = _load_batch_meta(store_dir, batch_id)
    if meta is None:
        print(_red(f"  Error: batch {batch_id!r} not found. Run 'pipeline parse' first."), file=sys.stderr)
        return 1
    if meta.get("stage") not in ("parsed", "analyzed"):
        print(_yellow(f"  Warning: batch stage is '{meta.get('stage')}' — re-analyzing anyway."))

    raw_rows = _load_raw_rows(store_dir, batch_id)
    if not raw_rows:
        print(_red("  Error: no raw rows found. Re-run 'pipeline parse'."), file=sys.stderr)
        return 1

    user_id       = meta.get("user_id", args.user_id)
    account_id    = meta.get("account_id", batch_id)
    base_currency = meta.get("base_currency", "INR")
    source_acc_c     = meta.get("source_account_code", "1102")
    source_acc_n     = meta.get("source_account_name", "Savings Account")
    source_acc_class = meta.get("source_account_class", "ASSET")

    print()
    print(_bold("  Ledger 3.0 — Stage 2: Analyze"))
    print(f"  {'Batch:':<20} {batch_id}")
    print(f"  {'Source:':<20} {meta.get('source_type', '?')}")
    print(f"  {'Raw rows:':<20} {len(raw_rows)}")
    # ── Optional LLM provider resolution ────────────────────────────────
    llm_provider = None
    _session = None
    use_llm = getattr(args, "use_llm", False) or getattr(args, "llm_all", False)
    if use_llm:
        try:
            _session = _get_db_session()
            llm_provider = _resolve_llm_provider(
                _session, user_id, getattr(args, "provider_id", None) or None
            )
            if llm_provider:
                llm_mode = "all rows" if getattr(args, "llm_all", False) else "low-confidence rows"
                print(f"  {'LLM provider:':<20} {llm_provider.PROVIDER_NAME}  {_dim(f'({llm_mode})')}")
            else:
                print(_yellow("  ⚠  --llm requested but no provider configured — skipping LLM stage"))
        except Exception:
            pass

    print(f"\n  Normalizing… deduplicating… categorizing…", end="", flush=True)

    from services.smart_service import SmartProcessor, SmartProcessingOptions
    opts = SmartProcessingOptions(
        use_llm=llm_provider is not None,
        llm_provider=llm_provider,
        llm_for_red_band_only=not getattr(args, "llm_all", False),
        bank_account_id=source_acc_c,
        source_account_code=source_acc_c,
        source_account_name=source_acc_n,
        source_account_class=source_acc_class,
        account_id=account_id,
        session=_session,
    )
    smart = SmartProcessor().process_batch(
        user_id=user_id, batch_id=batch_id, raw_rows=raw_rows, options=opts,
    )
    print(f"  {_green('done')}")

    dup_tag = _green("0") if smart.duplicate_count == 0 else _yellow(str(smart.duplicate_count))
    print(f"  {'Normalized:':<20} {smart.normalized_count}")
    print(f"  {'New (unique):':<20} {_green(str(smart.new_count))}")
    print(f"  {'Duplicates skipped:':<20} {dup_tag}")
    print(f"  {'Confidence bands:':<20} "
          f"{_green(str(smart.green_count))} green / "
          f"{_yellow(str(smart.yellow_count))} yellow / "
          f"{_red(str(smart.red_count))} red")

    if smart.new_count == 0:
        print(_yellow("\n  All rows are duplicates — nothing new. Batch complete."))
        return 0

    rows = smart.normalized_rows

    print()
    print(_bold("  ─── Categorized Transactions ─────────────────────────────────────"))
    print(f"  {'#':<5} {'Date':<12} {'Narration':<40} {'D/C':<4} {'Amount':>14}  {'Category':<22}  Band")
    print("  " + "─" * 110)
    for i, row in enumerate(rows, 1):
        dr_cr = "DR" if row.is_debit else "CR"
        amt   = _fmt_amount(row.amount, base_currency)
        cat   = row.extra_fields.get("category", "EXPENSE_OTHER")
        band  = row.extra_fields.get("confidence_band", "RED")
        date_ = str(row.txn_date or row.raw_date or "")[:10]
        narr  = _truncate(row.narration or row.raw_narration or "", 39)
        print(f"  {i:<5} {date_:<12} {narr:<40} {dr_cr:<4} {amt:>14}  {cat:<22}  {_band_colour(band)}")
    print()

    print(_dim("  To correct a category enter: <row#> <CATEGORY>  (e.g. '5 INCOME_REFUND')"))
    print(_dim("  Valid categories: INCOME_SALARY INCOME_INTEREST INCOME_REFUND INCOME_CASHBACK"))
    print(_dim("                    EXPENSE_FOOD EXPENSE_TRANSPORT EXPENSE_SHOPPING EXPENSE_HEALTHCARE"))
    print(_dim("                    EXPENSE_UTILITIES EXPENSE_HOUSING EXPENSE_EMI EXPENSE_INSURANCE"))
    print(_dim("                    EXPENSE_ENTERTAINMENT EXPENSE_OTHER TRANSFER INVESTMENT CASH_WITHDRAWAL"))
    print()
    while True:
        try:
            inp = input("  Correction (or Enter to continue): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not inp:
            break
        parts = inp.split(None, 1)
        if len(parts) != 2:
            print(_yellow("  Format: <row#> <CATEGORY>  e.g.  5 INCOME_REFUND"))
            continue
        try:
            idx = int(parts[0]) - 1
            if not (0 <= idx < len(rows)):
                raise ValueError
        except ValueError:
            print(_yellow(f"  Row number must be between 1 and {len(rows)}"))
            continue
        new_cat = parts[1].strip().upper()
        rows[idx].extra_fields["category"] = new_cat
        rows[idx].extra_fields["category_method"] = "user_override"
        print(_green(f"  Row {idx+1}: category set to {new_cat}"))

    _save_normalized(store_dir, batch_id, rows)
    meta["stage"] = "analyzed"
    _save_batch_meta(store_dir, meta)
    print()
    print(_dim(f"  Analysis saved → {_batch_dir(store_dir, batch_id)}"))
    print(_bold(f"  Next: python cli.py pipeline propose {batch_id}"))

    if _confirm("\n  Continue to Stage 3 — Propose journal entries? [Y/n]: "):
        args.batch_id = batch_id
        return cmd_pipeline_propose(args)
    return 0


# ── Stage 3: propose ──────────────────────────────────────────────────────────

def cmd_pipeline_propose(args: argparse.Namespace) -> int:
    """Stage 3 — generate journal entry proposals; allow reject before commit."""
    from modules.store import get_store_dir
    store_dir = Path(args.store_dir) if args.store_dir else get_store_dir()
    batch_id  = args.batch_id

    meta = _load_batch_meta(store_dir, batch_id)
    if meta is None:
        print(_red(f"  Error: batch {batch_id!r} not found."), file=sys.stderr)
        return 1

    rows = _load_normalized(store_dir, batch_id)
    if not rows:
        print(_red("  Error: no analyzed rows — run 'pipeline analyze' first."), file=sys.stderr)
        return 1

    base_currency = meta.get("base_currency", "INR")
    source_acc_c     = meta.get("source_account_code", "1102")
    source_acc_n     = meta.get("source_account_name", "Savings Account")
    source_acc_class = meta.get("source_account_class", "ASSET")

    print()
    print(_bold("  Ledger 3.0 — Stage 3: Propose"))
    print(f"  {'Batch:':<20} {batch_id}")
    print(f"  {'Rows to propose:':<20} {len(rows)}")
    print(f"\n  Generating journal entries…", end="", flush=True)

    from services.proposal_service import ProposalService
    result = ProposalService().propose_batch(
        batch_id=batch_id, bank_account_id=source_acc_c, rows=rows,
        source_account_code=source_acc_c, source_account_name=source_acc_n,
        source_account_class=source_acc_class,
    )
    print(f"  {_green('done')}")
    print(f"  {'Proposals:':<20} {len(result.proposals)}")
    if result.unproposable:
        print(_yellow(f"  {'Unproposable:':<20} {len(result.unproposable)} rows skipped"))
    print()

    print(_bold("  ─── Proposed Journal Entries ─────────────────────────────────────"))
    for i, p in enumerate(result.proposals, 1):
        bal    = _green("✓ balanced") if p.is_balanced else _red("✗ UNBALANCED")
        band_c = _green if p.confidence_band == "GREEN" else (_yellow if p.confidence_band == "YELLOW" else _red)
        print(f"\n  [{i}] {p.txn_date}  {_truncate(p.narration, 52)}  [{bal}]  {band_c(p.confidence_band)}")
        for line in p.lines:
            dr = f"DR {_fmt_amount(line.debit,  base_currency)}" if line.debit  else ""
            cr = f"CR {_fmt_amount(line.credit, base_currency)}" if line.credit else ""
            print(f"       {line.account_code:<6}  {line.account_name:<30}  {dr or cr}")
    print()

    print(_dim("  Enter proposal numbers to REJECT (comma-separated, e.g. 3,7,12)"))
    print(_dim("  or press Enter to approve all:"))
    rejected_indices: set[int] = set()
    try:
        inp = input("  Reject: ").strip()
        if inp:
            for token in inp.split(","):
                token = token.strip()
                if token.isdigit():
                    idx = int(token) - 1
                    if 0 <= idx < len(result.proposals):
                        rejected_indices.add(idx)
                        result.proposals[idx].status = "REJECTED"
                        print(_yellow(f"  Proposal {idx+1} rejected."))
    except (EOFError, KeyboardInterrupt):
        print()

    approved = [p for i, p in enumerate(result.proposals) if i not in rejected_indices]
    print()
    print(f"  {_green(str(len(approved)))} approved   {_yellow(str(len(rejected_indices)))} rejected")

    _save_proposals(store_dir, batch_id, result.proposals)
    meta["stage"] = "proposed"
    _save_batch_meta(store_dir, meta)
    print(_dim(f"  Proposals saved → {_batch_dir(store_dir, batch_id)}"))
    print(_bold(f"  Next: python cli.py pipeline commit {batch_id}"))

    if approved and _confirm("\n  Continue to Stage 4 — Commit to database? [Y/n]: "):
        args.batch_id = batch_id
        return cmd_pipeline_commit(args)
    return 0


# ── Stage 4: commit ───────────────────────────────────────────────────────────

def cmd_pipeline_commit(args: argparse.Namespace) -> int:
    """Stage 4 — write approved proposals to the database as journal entries."""
    from modules.store import get_store_dir
    store_dir = Path(args.store_dir) if args.store_dir else get_store_dir()
    batch_id  = args.batch_id

    meta = _load_batch_meta(store_dir, batch_id)
    if meta is None:
        print(_red(f"  Error: batch {batch_id!r} not found."), file=sys.stderr)
        return 1

    proposals = _load_proposals(store_dir, batch_id)
    if not proposals:
        print(_red("  Error: no proposals found — run 'pipeline propose' first."), file=sys.stderr)
        return 1

    approved      = [p for p in proposals if p.status != "REJECTED"]
    rejected      = [p for p in proposals if p.status == "REJECTED"]
    base_currency = meta.get("base_currency", "INR")

    print()
    print(_bold("  Ledger 3.0 — Stage 4: Commit"))
    print(f"  {'Batch:':<22} {batch_id}")
    print(f"  {'Approved proposals:':<22} {_green(str(len(approved)))}")
    print(f"  {'Rejected (skipped):':<22} {_yellow(str(len(rejected)))}")
    print()

    if not approved:
        print(_yellow("  Nothing to commit."))
        return 0

    # Mark all non-rejected proposals as CONFIRMED for ApprovalService
    for p in approved:
        p.status = "CONFIRMED"

    # Build a minimal PydanticBatch so ApprovalService can create the ORM ImportBatch
    import hashlib as _hashlib  # noqa: PLC0415
    from core.models.import_batch import ImportBatch as PydanticBatch  # noqa: PLC0415
    from core.models.enums import SourceType, FileFormat, BatchStatus  # noqa: PLC0415
    pydantic_batch = PydanticBatch(
        batch_id=batch_id,
        user_id=meta.get("user_id", "cli-user"),
        account_id=meta.get("account_id", batch_id),
        filename=meta.get("filename", "unknown"),
        file_hash=_hashlib.md5(batch_id.encode()).hexdigest(),  # stable placeholder
        source_type=SourceType(meta["source_type"]) if meta.get("source_type") else SourceType.UNKNOWN,
        format=FileFormat.CSV,
        txn_found=len(proposals),
        status=BatchStatus.PROCESSING,
    )

    print("  Writing to database…")
    session = _get_db_session()
    try:
        from services.approval_service import ApprovalService  # noqa: PLC0415
        result = ApprovalService(session).commit_proposals(approved, pydantic_batch)
        session.commit()
    except Exception as exc:
        session.rollback()
        print(_red(f"  Database error: {exc}"), file=sys.stderr)
        return 1
    finally:
        session.close()

    committed     = result["committed"]
    skipped       = result["skipped"]
    already_posted = result["already_posted"]

    print()
    print(_green(f"  ✓  {committed} transaction(s) committed to database"))
    if already_posted:
        print(_dim(f"  {already_posted} already existed (skipped — idempotent)"))
    if skipped:
        print(_yellow(f"  ⚠  {skipped} skipped (accounts not in CoA — run 'onboarding coa init' first)"))
    print()

    meta["stage"] = "committed"
    meta["committed_count"] = committed
    _save_batch_meta(store_dir, meta)

    print(_bold(f"  Done.  Store: {_store_stats_line()}"))
    print()
    return 0


# ── Status: list / inspect batches ────────────────────────────────────────────

def cmd_pipeline_status(args: argparse.Namespace) -> int:
    """List all saved batches or show detail for one batch."""
    from modules.store import get_store_dir
    store_dir   = Path(args.store_dir) if args.store_dir else get_store_dir()
    batches_dir = store_dir / "batches"

    if not batches_dir.is_dir():
        print(_yellow("\n  No batches found.\n"))
        return 0

    batch_id = getattr(args, "batch_id", None)

    if batch_id:
        meta = _load_batch_meta(store_dir, batch_id)
        if meta is None:
            print(_red(f"  Batch {batch_id!r} not found."), file=sys.stderr)
            return 1
        print()
        print(_bold("  ─── Batch Detail ─────────────────────────────────────────────"))
        for k, v in meta.items():
            print(f"  {k:<26} {v}")
        raw   = _load_raw_rows(store_dir, batch_id)
        norm  = _load_normalized(store_dir, batch_id)
        props = _load_proposals(store_dir, batch_id)
        print(f"  {'raw_rows':<26} {len(raw)}")
        print(f"  {'normalized_rows':<26} {len(norm)}")
        print(f"  {'proposals':<26} {len(props)}")
        print()
        return 0

    batch_dirs = sorted(batches_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    print()
    print(_bold("  ─── Saved Batches ────────────────────────────────────────────────"))
    print(f"  {'Batch ID':<38} {'Stage':<12} {'Source':<22} {'File'}")
    print("  " + "─" * 90)
    for bd in batch_dirs[:20]:
        meta_file = bd / "batch.json"
        if not meta_file.is_file():
            continue
        try:
            m = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        stage     = m.get("stage", "?")
        src       = m.get("source_type", "?")
        fname     = m.get("filename", "?")
        colour    = _green if stage == "committed" else (_yellow if stage == "proposed" else _dim)
        stage_col = colour(stage).ljust(12 + len(colour("")) - len(stage))
        print(f"  {m['batch_id']:<38} {stage_col} {src:<22} {fname}")
    print()
    return 0


# ── Dispatcher ────────────────────────────────────────────────────────────────

def cmd_pipeline(args: argparse.Namespace) -> int:
    dispatch = {
        "parse":   cmd_pipeline_parse,
        "analyze": cmd_pipeline_analyze,
        "propose": cmd_pipeline_propose,
        "commit":  cmd_pipeline_commit,
        "status":  cmd_pipeline_status,
    }
    return dispatch[args.pl_command](args)
