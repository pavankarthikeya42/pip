# PDF ↔ KARI UI Validation Tool

A Python 3.12 starter implementation for validating KARI comparison data against PIP PDFs and Excel metadata for large medicine batches.

## Current design

- Playwright: KARI browser automation
- Docling: primary PDF extraction
- PyMuPDF: fallback PDF extraction and page/table evidence
- openpyxl: Excel import
- SQLite: checkpoints/results
- Meta-prompt: semantic ambiguity only
- No embeddings/vector DB/RAG

## Important

The supplied KARI HTML reference was used to ground the initial selectors:
- `.dl-row`
- `.dl-pdf-btn[title="View PIP PDF"]`
- `.cmp-section-group`
- `.cmp-sec-row`
- `.cmp-sec-content`
- `[data-section-key]`
- `.cmp-content-inner`

The live KARI environment was not available to execute browser actions here. Therefore the login URL, search behavior, and exact live Compare button must be verified before production use.

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
```

Configure `.env` with the real KARI URL and permitted LLM endpoint.

## Excel

Create an Excel with at least `Medicine_Name`. Prefer `PIP_Number` when available. Supported aliases are implemented in `app/worker/queue.py`.

## Import and run

```powershell
python run.py --import-excel data/input/person1.xlsx --owner USER_1
python run.py --run --owner USER_1
```

For the three operators, use `USER_1`, `USER_2`, and `USER_3` with separate input batches or owner-assigned rows.

## CAPTCHA

The tool pauses when a CAPTCHA is detected and waits for a human to complete it. It does not bypass or solve CAPTCHA.

## Validation model

Three comparisons are planned:

1. Excel ↔ UI metadata
2. Excel ↔ PDF metadata
3. PDF ↔ UI content/sections/tables

Sections are page-independent. Tables are order-independent. UI dropdown sections are expanded before extraction. Semantic mapping is delegated only to the meta-prompt when deterministic matching cannot resolve it.

## Current MVP limitation

PDF semantic section/table conversion is intentionally conservative in this first build: Docling markdown and PyMuPDF page/table extraction are preserved as raw structured evidence. The next implementation pass should add the medicine-specific canonical PDF section parser and richer PDF metadata mapping after validating several real PDFs.
