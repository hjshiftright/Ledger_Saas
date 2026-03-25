"""import command — full one-shot pipeline: detect → parse → normalize → dedup → categorize → propose."""
from __future__ import annotations

import argparse
import getpass
import sys
import uuid
from pathlib import Path

from commands._helpers import (
    _bold, _dim, _green, _yellow, _red,
    _band_colour, _fmt_amount, _truncate,
    _get_db_session, _load_profile, _store_stats_line,
    _resolve_llm_provider,
)


def cmd_import(args: argparse.Namespace) -> int:
    """Full pipeline: detect → parse → normalize → dedup → categorize → propose."""
    path = Path(args.file)
    if not path.is_file():
        print(_red(f"  Error: file not found: {path}"), file=sys.stderr)
        return 1

    file_bytes = path.read_bytes()
    user_id    = args.user_id
    account_id = args.account_id or f"CLI-{path.stem.upper()[:20]}"
    batch_id   = str(uuid.uuid4())

    from modules.store import get_store_dir
    store_dir    = Path(args.store_dir) if args.store_dir else get_store_dir()
    display_name, base_currency = _load_profile(store_dir, user_id)

    from core.models.source_map import get_source_account as _get_src_acct
    _src_info_early = _get_src_acct(account_type_override=args.account_type or None)
    source_account_code  = _src_info_early.account_code
    source_account_name  = _src_info_early.account_name
    source_account_class = _src_info_early.account_class

    # ── PDF password / decryption ──────────────────────────────────────────
    if path.suffix.lower() == ".pdf":
        from core.utils.pdf_utils import is_pdf_encrypted, decrypt_pdf_bytes
        if is_pdf_encrypted(file_bytes):
            pwd = args.password
            if not pwd:
                try:
                    pwd = getpass.getpass(f"  Password for {path.name}: ")
                except (EOFError, KeyboardInterrupt):
                    print(_yellow("\n  Aborted."))
                    return 1
            try:
                file_bytes = decrypt_pdf_bytes(file_bytes, pwd)
                print(_green(f"  PDF decrypted successfully."))
            except ValueError as exc:
                if "WRONG_PASSWORD" in str(exc):
                    print(_red("  Error: incorrect PDF password."), file=sys.stderr)
                else:
                    print(_red(f"  Error: {exc}"), file=sys.stderr)
                return 1

    print()
    print(_bold("  Ledger 3.0 — Import Pipeline"))
    print(f"  {'File:':<16} {path.name}")
    print(f"  {'Size:':<16} {len(file_bytes):,} bytes")
    if display_name != user_id:
        print(f"  {'User:':<16} {display_name}  {_dim(f'({user_id})')}")
    else:
        print(f"  {'User:':<16} {user_id}")
    print(f"  {'Currency:':<16} {base_currency}")
    print(f"  {'Account:':<16} {account_id}")
    print(f"  {'Account type:':<16} {args.account_type or 'auto'}  ({source_account_code} {source_account_name})")
    print(f"  {'Batch:':<16} {batch_id}")

    # ── Step 1: Detect source type ─────────────────────────────────────────
    print()
    print(_bold("  [1/3] Detecting source type…"))
    from modules.parser.detector import SourceDetector
    from core.models.enums import SourceType

    if args.source_type:
        try:
            forced_st = SourceType(args.source_type)
        except ValueError:
            print(_red(f"  Error: unknown source type '{args.source_type}'"), file=sys.stderr)
            print(f"  Valid values: {', '.join(st.value for st in SourceType)}", file=sys.stderr)
            return 1
        print(f"  {'Source:':<16} {forced_st.value}  {_yellow('(forced)')}")
        detection_confidence = 1.0
        detected_source      = forced_st
    else:
        detector             = SourceDetector()
        det                  = detector.detect(filename=path.name, file_bytes=file_bytes)
        detected_source      = det.source_type
        detection_confidence = det.confidence
        conf_tag = _green(f"{detection_confidence:.0%}") if detection_confidence >= 0.70 \
                   else _yellow(f"{detection_confidence:.0%}")
        print(f"  {'Source:':<16} {detected_source.value}  (confidence {conf_tag})")
        if detection_confidence < 0.70:
            print(_yellow("  ⚠  Low detection confidence — consider passing --source-type"))

    # ── Step 2: Parse ──────────────────────────────────────────────────────
    print()
    print(_bold("  [2/3] Parsing…"))
    from modules.parser.registry import ParserRegistry
    from modules.parser.chain import ExtractionChain
    from core.models.enums import ParseStatus

    registry = ParserRegistry.default()
    parser   = registry.get(detected_source)

    if parser is None:
        print(_red(f"  Error: no parser registered for {detected_source.value}"))
        print(f"  Supported: {', '.join(st.value for st in registry.registered_types())}")
        return 1

    # Resolve LLM provider for parse-time fallback (scanned/image PDFs where text extraction fails)
    _parse_llm = None
    if getattr(args, "use_llm", False) or getattr(args, "llm_all", False):
        try:
            _p_sess = _get_db_session()
            _parse_llm = _resolve_llm_provider(
                _p_sess, user_id, getattr(args, "provider_id", None) or None
            )
            _p_sess.close()
            if _parse_llm:
                print(f"  {'LLM fallback:':<16} {_parse_llm.PROVIDER_NAME}  {_dim('(vision mode — for scanned PDFs)')}")
            else:
                print(_yellow("  ⚠  --llm requested but no provider configured — parse will use text/table methods only"))
        except Exception:
            pass

    chain  = ExtractionChain(parser, batch_id, file_bytes)
    result = chain.run(llm_provider=_parse_llm)

    parse_conf_tag = _green(f"{result.metadata.overall_confidence:.0%}") \
        if result.metadata.overall_confidence >= 0.75 \
        else _yellow(f"{result.metadata.overall_confidence:.0%}")
    print(f"  {'Status:':<16} {result.status.value}")
    print(f"  {'Rows found:':<16} {len(result.rows)}")
    print(f"  {'Confidence:':<16} {parse_conf_tag}")
    print(f"  {'Method:':<16} {result.metadata.extraction_method.value}")

    if result.status == ParseStatus.FAILED or not result.rows:
        print(_red("  Parse failed — no rows extracted."))
        if result.error_message:
            print(f"  {result.error_message}")
        return 1

    # ── Steps 3–5: Normalize → Dedup → Categorize → Score → Propose ───────
    print()
    print(_bold("  [3/3] Processing (normalize → dedup → categorize → score → propose)…"))
    from services.smart_service import SmartProcessor, SmartProcessingOptions
    from repositories.sqla_account_repo import AccountRepository
    from repositories.sqla_transaction_repo import TransactionRepository

    db_hashes: set[str] = set()
    llm_provider = None
    _session = None
    try:
        _session = _get_db_session()
        acc = AccountRepository(_session).find_by_code(account_id)
        if acc:
            db_hashes = TransactionRepository(_session).get_committed_hashes_for_account(acc.id)
        if getattr(args, "use_llm", False) or getattr(args, "llm_all", False):
            llm_provider = _resolve_llm_provider(
                _session, user_id, getattr(args, "provider_id", None) or None
            )
            if llm_provider:
                print(f"  {'LLM provider:':<16} {llm_provider.PROVIDER_NAME}"
                      f"  {_dim('(all rows)' if getattr(args, 'llm_all', False) else '(low-confidence rows)')}")
            else:
                print(_yellow("  ⚠  --llm requested but no provider configured — skipping LLM stage"))
    except Exception:
        pass

    # Refine source account from detected SourceType if no explicit --account-type
    if not args.account_type:
        from core.models.source_map import get_source_account as _get_src_acct2
        _src_info = _get_src_acct2(source_type=detected_source)
        source_account_code  = _src_info.account_code
        source_account_name  = _src_info.account_name
        source_account_class = _src_info.account_class

    opts  = SmartProcessingOptions(
        use_llm=llm_provider is not None,
        llm_provider=llm_provider,
        llm_for_red_band_only=not getattr(args, "llm_all", False),
        bank_account_id=source_account_code,
        source_account_code=source_account_code,
        source_account_name=source_account_name,
        source_account_class=source_account_class,
        account_id=account_id,
        db_hashes=db_hashes,
        session=_session,
    )
    smart = SmartProcessor().process_batch(
        user_id=user_id, batch_id=batch_id, raw_rows=result.rows, options=opts,
    )
    for w in smart.warnings[:5]:
        print(_yellow(f"  ⚠  {w}"))

    dup_tag = _green("0") if smart.duplicate_count == 0 else _yellow(str(smart.duplicate_count))
    print(f"  {'Normalized:':<16} {smart.normalized_count}")
    print(f"  {'New:':<16} {_green(str(smart.new_count))}")
    print(f"  {'Duplicates:':<16} {dup_tag}")
    print(f"  {'Confidence bands:':<16} "
          f"{_green(str(smart.green_count))} green / "
          f"{_yellow(str(smart.yellow_count))} yellow / "
          f"{_red(str(smart.red_count))} red")

    if smart.new_count == 0:
        print(_yellow("\n  All rows are duplicates — nothing new to import."))
        print()
        return 0

    proposals = smart.proposals
    print(f"  {'Proposals:':<16} {len(proposals.proposals)}")
    print(f"  {'Unproposable:':<16} {len(proposals.unproposable)}")

    # ── Results table ──────────────────────────────────────────────────────
    print()
    print(_bold("  ─── Transaction Summary ──────────────────────────────────────"))
    print(f"  {'#':<4} {'Date':<12} {'Narration':<43} {'Dr/Cr':<5} {'Amount':>14}  {'Category':<22}  Band")
    print("  " + "─" * 112)

    for i, row in enumerate(smart.normalized_rows, 1):
        dr_cr  = "DR" if row.is_debit else "CR"
        amount = _fmt_amount(row.amount, base_currency)
        cat    = row.extra_fields.get("category", "EXPENSE_OTHER")
        band   = row.extra_fields.get("confidence_band", "RED")
        date   = str(row.txn_date or row.raw_date or "")[:10]
        narr   = _truncate(row.narration or row.raw_narration or "", 42)
        print(f"  {i:<4} {date:<12} {narr:<43} {dr_cr:<5} {amount:>14}  {cat:<22}  {_band_colour(band)}")

    print()

    # ── Proposals table ────────────────────────────────────────────────────
    if proposals.proposals:
        print(_bold("  ─── Proposed Journal Entries ─────────────────────────────────"))
        for p in proposals.proposals:
            bal = _green("✓ balanced") if p.is_balanced else _red("✗ UNBALANCED")
            print(f"\n  {p.txn_date}  {_truncate(p.narration, 50)}  [{bal}]")
            for line in p.lines:
                dr = f"DR {_fmt_amount(line.debit,  base_currency)}" if line.debit  else ""
                cr = f"CR {_fmt_amount(line.credit, base_currency)}" if line.credit else ""
                print(f"    {line.account_code:<6}  {line.account_name:<30}  {dr or cr}")
        print()

    print(_bold(f"  Done. {smart.new_count} new transaction(s) imported.  Store: {_store_stats_line()}"))
    print()
    return 0
