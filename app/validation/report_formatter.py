import json
from ..config import RESULTS_DIR

def generate_reports(result: dict, pip_number: str):
    """Generate human-readable Markdown and formatted JSON reports in the results directory."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    ui_pdf = result.get("ui_vs_pdf_validation", {})
    meta = ui_pdf.get("metadata", {})
    sec = ui_pdf.get("sections", {})

    medicine = result.get("medicine", "")
    overall = result.get("overall_status", "UNKNOWN")

    # Generate Markdown Report
    md_lines = [
        f"# PIP Validation Report: {medicine} ({pip_number})",
        f"**Overall Validation Status:** `{overall}`\n",
        "## 1. UI vs PDF Metadata Comparison\n",
        "### Matched Fields",
        "| Field | PDF Value | UI Value | Status |",
        "| :--- | :--- | :--- | :--- |"
    ]

    for m in meta.get("matched_fields", []):
        md_lines.append(f"| {m['field']} | {m['pdf_value']} | {m['ui_value']} | `{m['status']}` |")

    if not meta.get("matched_fields"):
        md_lines.append("*No matched metadata fields found.*")

    md_lines.extend([
        "\n### Field Value Mismatches",
        "| Field | PDF Value | UI Value | Status |",
        "| :--- | :--- | :--- | :--- |"
    ])
    for mm in meta.get("mismatches", []):
        md_lines.append(f"| {mm['field']} | {mm['pdf_value']} | {mm['ui_value']} | `{mm['status']}` |")

    if not meta.get("mismatches"):
        md_lines.append("*No field value mismatches found.*")

    md_lines.extend([
        "\n### Missing Fields in UI",
        "| Field | PDF Value | Status |",
        "| :--- | :--- | :--- |"
    ])
    for mis in meta.get("missing_in_ui", []):
        md_lines.append(f"| {mis['field']} | {mis['pdf_value']} | `{mis['status']}` |")

    if not meta.get("missing_in_ui"):
        md_lines.append("*No PDF metadata fields are missing in the UI.*")

    md_lines.extend([
        "\n### Extra Fields in UI",
        "| Field Label | UI Value | Status |",
        "| :--- | :--- | :--- |"
    ])
    for ext in meta.get("extra_in_ui", []):
        md_lines.append(f"| {ext['ui_label']} | {ext['ui_value']} | `{ext['status']}` |")

    if not meta.get("extra_in_ui"):
        md_lines.append("*No extra metadata fields in UI.*")

    md_lines.extend([
        "\n## 2. UI vs PDF Section Comparison\n",
        "### Matched Sections",
        "| Section Label | Content Status |",
        "| :--- | :--- |"
    ])
    for s in sec.get("matched_sections", []):
        md_lines.append(f"| {s['label']} | `{s['content_status']}` |")

    if not sec.get("matched_sections"):
        md_lines.append("*No matched sections.*")

    md_lines.extend([
        "\n### Missing Sections in UI",
        "| Section Label | PDF Content |",
        "| :--- | :--- |"
    ])
    for ms in sec.get("missing_sections_in_ui", []):
        md_lines.append(f"| {ms['label']} | {ms['pdf_text']} |")

    if not sec.get("missing_sections_in_ui"):
        md_lines.append("*No PDF sections are missing in the UI.*")

    md_lines.extend([
        "\n### Extra Sections in UI",
        "| Section Label | UI Content |",
        "| :--- | :--- |"
    ])
    for es in sec.get("extra_sections_in_ui", []):
        md_lines.append(f"| {es['label']} | {es['ui_text']} |")

    if not sec.get("extra_sections_in_ui"):
        md_lines.append("*No extra sections in UI.*")

    md_content = "\n".join(md_lines)

    (RESULTS_DIR / f"{pip_number}_report.md").write_text(md_content, encoding="utf-8")
    (RESULTS_DIR / f"{pip_number}_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[REPORTS] Saved validation report -> {RESULTS_DIR / f'{pip_number}_report.md'}")
