# Ledger 3.0 — Implementation Tasks

> Update this file as tasks are completed. Mark `[x]` when done.
> Reference spec files in `docs/specs/` for acceptance criteria.

---

## Phase 1 — Core Infrastructure *(shared across all modules)*

| # | Task | File | Status |
|---|---|---|---|
| 1.1 | Shared enumerations (SourceType, ExtractionMethod, TxnTypeHint, BatchStatus, …) | `core/models/enums.py` | [x] Done |
| 1.2 | RawParsedRow + ParseMetadata + ParseResult models | `core/models/raw_parsed_row.py` | [x] Done |
| 1.3 | ImportBatch model | `core/models/import_batch.py` | [x] Done |
| 1.4 | ColumnMapping model | `core/models/column_mapping.py` | [x] Done |
| 1.5 | Confidence scoring utility | `core/utils/confidence.py` | [x] Done |
| 1.6 | PDF utility helpers (hash, text extract, page render) | `core/utils/pdf_utils.py` | [x] Done |

---

## Phase 2 — Parser Engine (SM-C)

| # | Task | File | Status |
|---|---|---|---|
| 2.1 | BaseParser abstract class | `modules/parser/base.py` | [x] Done |
| 2.2 | ExtractionChain (fallback orchestration) | `modules/parser/chain.py` | [x] Done |
| 2.3 | ParserRegistry (source_type → parser dispatch) | `modules/parser/registry.py` | [x] Done |
| 2.4 | SourceDetector (filename + content fingerprint) | `modules/parser/detector.py` | [x] Done |
| 2.5 | Text layer extractor (pdfplumber) | `modules/parser/extraction/text_layer.py` | [x] Done |
| 2.6 | Table extractor (Camelot / pdfplumber stream) | `modules/parser/extraction/table_extract.py` | [x] Done |
| 2.7 | OCR extractor (Tesseract via pytesseract) | `modules/parser/extraction/ocr.py` | [x] Done |
| 2.8 | HDFC Bank PDF parser | `modules/parser/parsers/hdfc_pdf.py` | [x] Done |
| 2.9 | SBI Bank PDF parser | `modules/parser/parsers/sbi_pdf.py` | [x] Done |
| 2.10 | ICICI Bank PDF parser | `modules/parser/parsers/icici_pdf.py` | [x] Done |
| 2.10a | Axis Bank PDF parser | `modules/parser/parsers/axis_pdf.py` | [x] Done |
| 2.10b | Kotak Bank PDF parser | `modules/parser/parsers/kotak_pdf.py` | [x] Done |
| 2.10c | IndusInd Bank PDF parser | `modules/parser/parsers/indusind_pdf.py` | [x] Done |
| 2.10d | IDFC Bank PDF parser | `modules/parser/parsers/idfc_pdf.py` | [x] Done |
| 2.11 | Generic CSV / XLS parser + column mapper | `modules/parser/parsers/generic_csv.py` | [x] Done |
| 2.12 | CAS (CAMS) parser | `modules/parser/parsers/cas_cams.py` | [x] Done |
| 2.13 | Zerodha CSV parsers | `modules/parser/parsers/zerodha_csv.py` | [x] Done |

---

## Phase 3 — LLM Module (SM-D)

| # | Task | File | Status |
|---|---|---|---|
| 3.1 | BaseLLMProvider + request/response contracts | `modules/llm/base.py` | [x] Done |
| 3.2 | LLM data models (LLMProvider, PromptTemplate, etc.) | `modules/llm/models.py` | [x] Done |
| 3.3 | LLMProviderRegistry | `modules/llm/registry.py` | [x] Done |
| 3.4 | Google Gemini provider (primary) | `modules/llm/providers/gemini.py` | [x] Done |
| 3.5 | OpenAI provider | `modules/llm/providers/openai_provider.py` | [ ] Stub |
| 3.6 | Anthropic provider | `modules/llm/providers/anthropic_provider.py` | [ ] Stub |
| 3.7 | LLM extraction coordinator | `modules/llm/extractor.py` | [x] Done |

---

## Phase 4 — Tests

| # | Task | File | Status |
|---|---|---|---|
| 4.1 | Test fixtures and shared conftest | `tests/conftest.py` | [x] Done |
| 4.2 | Core enums tests | `tests/core/test_enums.py` | [x] Done |
| 4.3 | Core models tests | `tests/core/test_models.py` | [x] Done |
| 4.4 | SourceDetector tests | `tests/parser/test_detector.py` | [x] Done |
| 4.5 | ParserRegistry tests | `tests/parser/test_registry.py` | [x] Done |
| 4.6 | ExtractionChain tests | `tests/parser/test_chain.py` | [x] Done |
| 4.7 | HDFC parser tests | `tests/parser/test_hdfc_parser.py` | [x] Done |
| 4.8 | Generic CSV parser tests | `tests/parser/test_generic_csv.py` | [x] Done |
| 4.9 | Gemini provider tests | `tests/llm/test_gemini_provider.py` | [x] Done |
| 4.10 | LLM registry tests | `tests/llm/test_llm_registry.py` | [x] Done |
| 4.11 | SBI parser tests | `tests/parser/test_sbi_parser.py` | [x] Done |
| 4.12 | ICICI parser tests | `tests/parser/test_icici_parser.py` | [x] Done |
| 4.13 | Axis parser tests | `tests/parser/test_axis_parser.py` | [x] Done |
| 4.14 | Kotak parser tests | `tests/parser/test_kotak_parser.py` | [x] Done |
| 4.15 | IndusInd parser tests | `tests/parser/test_indusind_parser.py` | [x] Done |
| 4.16 | IDFC parser tests | `tests/parser/test_idfc_parser.py` | [x] Done |
| 4.17 | Zerodha parsers tests | `tests/parser/test_zerodha_parsers.py` | [x] Done |
| 4.18 | CAS parser tests | `tests/parser/test_cas_parser.py` | [x] Done |

---

## Phase 5 — Pipeline Orchestration (SM-K) *(future)*

| # | Task | File | Status |
|---|---|---|---|
| 5.1 | POST /pipeline/parse endpoint | `src/api/routers/pipeline.py` | [x] Done |
| 5.2 | POST /pipeline/analyze endpoint | `src/api/routers/pipeline.py` | [x] Done |
| 5.3 | POST /pipeline/import (full) endpoint | `src/api/routers/pipeline.py` | [x] Done |

---

## Phase 6 — Sub-modules (SM-A through SM-K)

| # | Task | File | Status |
|---|---|---|---|
| 6.1 | SM-A Account Registry models | `src/accounts/models.py` | [x] Done |
| 6.2 | SM-A Account Registry service | `src/accounts/service.py` | [x] Done |
| 6.3 | SM-A Account Registry router | `src/api/routers/accounts.py` | [x] Done |
| 6.4 | SM-A Business rule tests BR-A-01..BR-A-11 | `tests/test_api_accounts.py` | [x] Done |
| 6.5 | SM-B Document Ingestion router | `src/api/routers/imports.py` | [x] Done |
| 6.6 | SM-C Parser Engine router | `src/api/routers/parser.py` | [x] Done |
| 6.7 | SM-D LLM Processing router | `src/api/routers/llm.py` | [x] Done |
| 6.8 | SM-E Normalize service | `src/modules/normalize/service.py` | [x] Done |
| 6.9 | SM-E Normalize router | `src/api/routers/normalize.py` | [x] Done |
| 6.10 | SM-F Dedup service | `src/modules/dedup/service.py` | [x] Done |
| 6.11 | SM-F Dedup router | `src/api/routers/dedup.py` | [x] Done |
| 6.12 | SM-G Categorize service | `src/modules/categorize/service.py` | [x] Done |
| 6.13 | SM-G Categorize router | `src/api/routers/categorize.py` | [x] Done |
| 6.14 | SM-H Confidence service | `src/modules/confidence/service.py` | [x] Done |
| 6.15 | SM-H Confidence router | `src/api/routers/confidence.py` | [x] Done |
| 6.16 | SM-I Proposal service | `src/modules/proposal/service.py` | [x] Done |
| 6.17 | SM-I Proposals router | `src/api/routers/proposals.py` | [x] Done |
| 6.18 | SM-J Smart AI processor | `src/modules/smart/service.py` | [x] Done |
| 6.19 | SM-J Smart router | `src/api/routers/smart.py` | [x] Done |
| 6.20 | SM-K Pipeline orchestration router | `src/api/routers/pipeline.py` | [x] Done |
| 6.21 | FastAPI main app | `src/main.py` | [x] Done |

---

## Notes

- LLM is **optional everywhere**. All pipeline stages must produce valid output with `use_llm=False`.
- `password` field for PDF decryption is **never persisted** — used in-memory and discarded.
- All tests use mocks/fixtures for PDF bytes and LLM API calls — no real network calls in unit tests.
- Confidence threshold for extraction: **0.75** (see `CONFIDENCE_THRESHOLD` in `modules/parser/base.py`).
- Run tests: `pytest tests/ -v --cov=core --cov=modules`
