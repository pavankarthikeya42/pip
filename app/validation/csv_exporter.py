import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..config import RESULTS_DIR, EXTRACTED_DIR

CSV_HEADERS = [
    "file_name",
    "generic_name",
    "brand_name",
    "sponsor",
    "pip_number",
    "decision_number",
    "decision_date",
    "decision_type",
    "status",
    "condition_indication",
    "overall_status",
]


def extract_row_from_json(filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract standard row fields from a validation result JSON dictionary."""
    file_name = filename

    generic_name = data.get("generic_name", "")
    brand_name = data.get("brand_name") or data.get("medicine", "")
    sponsor = data.get("sponsor", "")
    pip_number = data.get("pip_number", "")
    decision_number = data.get("decision_number", "")
    decision_date = data.get("decision_date", "")
    decision_type = data.get("decision_type", "")
    status = data.get("status", "")
    condition_indication = (
        data.get("condition_indication")
        or data.get("therapeutic_areas")
        or data.get("therapeutic_area")
        or ""
    )
    overall_status = data.get("overall_status", "")

    # Fallback to nested ui_vs_pdf_validation / metadata_validation if top-level fields are empty
    meta_val = data.get("ui_vs_pdf_validation", {}).get("metadata", {})
    matched_fields = meta_val.get("matched_fields", []) + meta_val.get("mismatches", [])
    field_map = {}
    for item in matched_fields:
        f_name = item.get("field")
        val = item.get("pdf_value") or item.get("ui_value")
        if f_name and val and f_name not in field_map:
            field_map[f_name] = val

    if not generic_name:
        generic_name = field_map.get("generic_name", "")
    if not brand_name:
        brand_name = field_map.get("brand_name", "")
    if not sponsor:
        sponsor = field_map.get("sponsor", "")
    if not pip_number:
        pip_number = field_map.get("pip_number", "")
    if not decision_number:
        decision_number = field_map.get("decision_number", "")
    if not decision_date:
        decision_date = field_map.get("decision_date", "")
    if not decision_type:
        decision_type = field_map.get("decision_type", "")
    if not status:
        status = field_map.get("status", "")
    if not condition_indication:
        condition_indication = field_map.get("condition_indication", "") or field_map.get("therapeutic_area", "")

    return {
        "file_name": file_name,
        "generic_name": generic_name,
        "brand_name": brand_name,
        "sponsor": sponsor,
        "pip_number": pip_number,
        "decision_number": decision_number,
        "decision_date": decision_date,
        "decision_type": decision_type,
        "status": status,
        "condition_indication": condition_indication,
        "overall_status": overall_status,
    }


def export_all_to_csv(output_path: Optional[Path | str] = None) -> Path:
    """Scan all validation JSON results and export to a single CSV file (one row per document)."""
    if output_path is None:
        output_path = RESULTS_DIR / "all_validation_results.csv"
    else:
        output_path = Path(output_path)

    json_files: Dict[str, Path] = {}
    for d in (RESULTS_DIR, EXTRACTED_DIR):
        if d.exists():
            for p in d.glob("*_validation.json"):
                json_files[p.name] = p

    rows: List[Dict[str, Any]] = []
    for filename in sorted(json_files.keys()):
        filepath = json_files[filename]
        try:
            content = filepath.read_text(encoding="utf-8")
            data = json.loads(content)
            rows.append(extract_row_from_json(filename, data))
        except Exception as ex:
            print(f"[CSV EXPORT] Warning: Error reading {filename}: {ex}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[CSV EXPORT] Exported {len(rows)} record(s) to single CSV file: {output_path}")
    return output_path
