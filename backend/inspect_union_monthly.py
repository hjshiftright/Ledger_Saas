"""Inspect and parse the Union Bank encrypted monthly PDF statement.

Usage:
    python inspect_union_monthly.py <password>
    python inspect_union_monthly.py          # prompts interactively
"""
import sys
import io
import getpass

sys.path.insert(0, "src")

if len(sys.argv) > 1:
    password = sys.argv[1]
else:
    password = getpass.getpass("Enter Union Bank statement password (usually DDMMYYYY date of birth): ")

import fitz  # noqa: E402  (PyMuPDF)
import pdfplumber  # noqa: E402
from pathlib import Path
from core.utils.pdf_utils import decrypt_pdf_bytes
from modules.parser.parsers.union_pdf import UnionBankPdfParser
from core.models.enums import ExtractionMethod

PDF_PATH = Path("src/samples/union/unionbank-monthly.pdf")
raw = PDF_PATH.read_bytes()

# ── Step 1: Decrypt ───────────────────────────────────────────────────────────
print(f"\nFile: {PDF_PATH.name}  ({len(raw):,} bytes)")
try:
    decrypted = decrypt_pdf_bytes(raw, password)
    print(f"Decrypted successfully  ({len(decrypted):,} bytes)")
except ValueError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# ── Step 2: Peek at text layer ────────────────────────────────────────────────
doc = fitz.open(stream=decrypted, filetype="pdf")
print(f"Pages: {doc.page_count}")
print("\n=== Raw text (page 1, first 2000 chars) ===")
print(doc[0].get_text()[:2000])
doc.close()

# ── Step 3: pdfplumber — tables ───────────────────────────────────────────────
print("\n=== pdfplumber tables (pages 1-2) ===")
with pdfplumber.open(io.BytesIO(decrypted)) as pdf:
    for page in pdf.pages[:2]:
        print(f"\n--- Page {page.page_number} ---")
        tables = page.extract_tables()
        print(f"Tables found: {len(tables)}")
        for ti, tbl in enumerate(tables[:2]):
            print(f"  Table {ti}: {len(tbl)} rows")
            for row in tbl[:5]:
                print("   ", row)

# ── Step 4: Full parse via UnionBankPdfParser ─────────────────────────────────
print("\n=== Full parse via UnionBankPdfParser ===")
parser = UnionBankPdfParser()
for method in [ExtractionMethod.TEXT_LAYER, ExtractionMethod.TABLE_EXTRACTION]:
    result = parser.extract("batch_monthly", decrypted, method)
    print(f"\nMethod: {method.value}  |  rows={len(result.rows)}  |  confidence={result.confidence:.2f}")
    if result.rows:
        r = result.rows[0]
        print(f"  First: date={r.raw_date}  debit={r.raw_debit}  credit={r.raw_credit}  bal={r.raw_balance}")
        print(f"  Narr:  {r.raw_narration[:70]}")
        r2 = result.rows[-1]
        print(f"  Last:  date={r2.raw_date}  debit={r2.raw_debit}  credit={r2.raw_credit}  bal={r2.raw_balance}")
    elif result.metadata.warnings:
        print(f"  Warnings: {result.metadata.warnings[:2]}")
