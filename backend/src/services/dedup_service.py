"""SM-F Deduplication Engine.

Spec reference: R2.5 — Unique Transaction ID Generation
Each transaction gets a deterministic SHA-256 based ID. Re-importing the same
statement produces identical hashes, so duplicates are silently skipped.

Also supports cross-account transfer-pair detection (R2.6) with three scenarios:

  1. SAME-BATCH: both account statements uploaded in one import run.
     Both the debit side and the credit side land in result.new and are matched
     in a single pass (new × new).

  2. CROSS-BATCH (prospective): one account was already imported; the counterpart
     account is now being imported.  The caller passes the prior account's rows
     as ``existing_rows``.  A second pass (new × historical) matches the incoming
     rows against those historical rows and creates retroactive transfer-pair links.
     The historical row receives ``dedup_status = TRANSFER_PAIR`` and
     ``transfer_pair_retroactive = True`` in its extra_fields.

  3. ONE-SIDED (deferred): only one account has been imported so far and no
     counterpart row is available.  The row stays NEW.  When the counterpart
     account is imported later, scenario 2 handles the match at that time.

Match criteria (R2.6):
  - Opposite direction  (one is_debit=True, one is_debit=False)
  - Equal amount
  - Date within ±TRANSFER_DATE_TOLERANCE_DAYS (currently 1)
  - At least one of (narration, raw_narration) contains a transfer keyword
    (upi / neft / rtgs / imps / transfer / trf)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal

from core.models.enums import DedupStatus
from services.normalize_service import NormalizedTransaction

# Transfer-pair matching constants
_TRANSFER_DATE_TOLERANCE_DAYS: int = 1
_TRANSFER_KEYWORDS: frozenset[str] = frozenset({"upi", "neft", "rtgs", "imps", "transfer", "trf"})


@dataclass
class DedupResult:
    txn_hash: str
    status: DedupStatus
    matched_hash: str | None = None    # For TRANSFER_PAIR: the other side's hash


@dataclass
class DedupBatchResult:
    batch_id: str
    new: list[NormalizedTransaction] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)             # row_ids
    near_duplicates: list[str] = field(default_factory=list)
    # Same-batch pairs: both row_ids belong to this batch
    transfer_pairs: list[tuple[str, str]] = field(default_factory=list)
    # Cross-batch (retroactive) pairs: (new_row_id, historical_row_id)
    retroactive_transfer_pairs: list[tuple[str, str]] = field(default_factory=list)

    @property
    def txn_new(self) -> int:
        return len(self.new)

    @property
    def txn_duplicate(self) -> int:
        return len(self.duplicates)


class DedupService:
    """SM-F: Detect and remove duplicate transactions."""

    def compute_txn_hash(self, row: NormalizedTransaction, account_id: str) -> str:
        """Deterministic hash per R2.5: hash(account_id + date + narration + amount + balance)."""
        balance_str = str(row.closing_balance) if row.closing_balance else ""
        raw = "|".join([
            account_id,
            str(row.txn_date or ""),
            row.raw_narration.strip().upper(),
            str(row.amount.quantize(Decimal("0.01"))),
            balance_str,
        ])
        return hashlib.sha256(raw.encode()).hexdigest()

    def dedup_batch(
        self,
        user_id: str,
        batch_id: str,
        account_id: str,
        rows: list[NormalizedTransaction],
        existing_rows: list[NormalizedTransaction] | None = None,
        db_hashes: set[str] | None = None,
    ) -> DedupBatchResult:
        """Classify each row as NEW, DUPLICATE, NEAR_DUPLICATE, or TRANSFER_PAIR.

        Args:
            user_id:       Owning user.
            batch_id:      Current import batch identifier.
            account_id:    The account this batch belongs to.
            rows:          Normalized rows from the current import.
            existing_rows: Previously imported rows from *other* accounts owned by
                           the same user.  Used for cross-batch (scenario 2) transfer
                           detection.  Callers should supply a short lookback window
                           (e.g., transactions within ±3 days of any date present in
                           the current batch) to keep the comparison set small.
            db_hashes:     Set of hashes already committed to the SQLite DB (from
                           Transaction.txn_hash).  Merged into the seen-hash set so
                           previously approved transactions are detected as duplicates
                           on re-import.  This is the authoritative cross-session
                           dedup source; the old JSON file store has been removed.
        """
        # Build an intra-request seen set from DB-committed hashes.
        # No module-level cache: each dedup call is self-contained and
        # safe across multiple workers.
        seen: set[str] = set(db_hashes) if db_hashes else set()
        result = DedupBatchResult(batch_id=batch_id)

        for row in rows:
            txn_hash = self.compute_txn_hash(row, account_id)
            row.extra_fields["txn_hash"] = txn_hash

            if txn_hash in seen:
                result.duplicates.append(row.row_id)
                row.extra_fields["dedup_status"] = DedupStatus.DUPLICATE.value
            else:
                seen.add(txn_hash)
                result.new.append(row)
                row.extra_fields["dedup_status"] = DedupStatus.NEW.value

        # Cross-account transfer pair detection (R2.6)
        self._detect_transfer_pairs(result.new, result, historical=existing_rows or [])

        return result

    def _detect_transfer_pairs(
        self,
        new_rows: list[NormalizedTransaction],
        result: DedupBatchResult,
        historical: list[NormalizedTransaction] | None = None,
    ) -> None:
        """Detect inter-account transfer pairs in two passes.

        Pass 1 — Same-batch (new × new):
            Both sides of the transfer arrived in this import (scenario 1).

        Pass 2 — Cross-batch (new × historical):
            One side was already in the system from a prior import of a different
            account (scenario 2).  The historical row is retroactively marked
            TRANSFER_PAIR and added to ``result.retroactive_transfer_pairs``.
        """
        candidates = [r for r in new_rows if r.txn_date is not None]
        hist_candidates = [r for r in (historical or []) if r.txn_date is not None]
        matched: set[str] = set()

        # ── Pass 1: same-batch pairs (new × new) ─────────────────────────────
        for i, a in enumerate(candidates):
            if a.row_id in matched:
                continue
            for b in candidates[i + 1:]:
                if b.row_id in matched:
                    continue
                if _is_transfer_pair(a, b):
                    a.extra_fields["dedup_status"] = DedupStatus.TRANSFER_PAIR.value
                    b.extra_fields["dedup_status"] = DedupStatus.TRANSFER_PAIR.value
                    result.transfer_pairs.append((a.row_id, b.row_id))
                    matched.update([a.row_id, b.row_id])

        # ── Pass 2: cross-batch pairs (new × historical) ─────────────────────
        hist_matched: set[str] = set()
        for a in candidates:
            if a.row_id in matched:
                continue
            for b in hist_candidates:
                if b.row_id in hist_matched:
                    continue
                if _is_transfer_pair(a, b):
                    a.extra_fields["dedup_status"] = DedupStatus.TRANSFER_PAIR.value
                    b.extra_fields["dedup_status"] = DedupStatus.TRANSFER_PAIR.value
                    b.extra_fields["transfer_pair_retroactive"] = True
                    result.retroactive_transfer_pairs.append((a.row_id, b.row_id))
                    matched.add(a.row_id)
                    hist_matched.add(b.row_id)


def _looks_like_transfer(narration: str, raw_narration: str = "") -> bool:
    """Return True if either the cleaned or raw narration contains a transfer keyword."""
    combined = (narration + " " + raw_narration).lower()
    return any(kw in combined for kw in _TRANSFER_KEYWORDS)


def _is_transfer_pair(a: NormalizedTransaction, b: NormalizedTransaction) -> bool:
    """Return True iff a and b look like the two sides of the same inter-account transfer."""
    return (
        a.is_debit != b.is_debit
        and a.amount == b.amount
        and a.txn_date is not None
        and b.txn_date is not None
        and abs((a.txn_date - b.txn_date).days) <= _TRANSFER_DATE_TOLERANCE_DAYS
        and _looks_like_transfer(a.narration, a.raw_narration)
        and _looks_like_transfer(b.narration, b.raw_narration)
    )


# ── Investment-row dedup (keyed by extra_fields["dedup_key"]) ────────────────

def dedup_by_key(
    rows: "list",  # list[RawParsedRow]
    existing_dedup_keys: set[str] | None = None,
) -> tuple["list", "list"]:
    """Filter raw parsed rows using their `extra_fields["dedup_key"]`.

    Used for Zerodha Tax P&L, CAS, and other investment parsers that embed a
    deterministic dedup key in every row.  Rows without a dedup_key pass through
    unchanged (bank rows).

    Args:
        rows:                 Fresh rows from the parser.
        existing_dedup_keys:  Set of dedup_keys already in the database.

    Returns:
        (new_rows, duplicate_rows) — both are lists of RawParsedRow.
    """
    from core.models.enums import DedupStatus  # local import to avoid circulars  # noqa: PLC0415

    seen: set[str] = set(existing_dedup_keys or set())
    new_rows: list = []
    duplicate_rows: list = []

    for row in rows:
        key = (row.extra_fields or {}).get("dedup_key")
        if not key:
            # No dedup_key → treat as new (bank rows handled by txn_hash path)
            new_rows.append(row)
            continue
        if key in seen:
            row.extra_fields["dedup_status"] = DedupStatus.DUPLICATE.value
            duplicate_rows.append(row)
        else:
            seen.add(key)
            new_rows.append(row)

    return new_rows, duplicate_rows
