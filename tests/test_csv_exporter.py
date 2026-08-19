import csv
import json
from pathlib import Path
from app.validation.csv_exporter import export_all_to_csv, extract_row_from_json, CSV_HEADERS

def test_extract_row_from_json():
    filename = "EMEA-002341-PIP01-18-M03_Modified_validation.json"
    data = {
        "generic_name": "ganaxolone",
        "brand_name": "Ztalmy",
        "sponsor": "Marinus Pharmaceuticals Inc.",
        "pip_number": "EMEA-002341-PIP01-18-M03",
        "decision_number": "P/0350/2024",
        "decision_date": "2024-09-27",
        "decision_type": "PM: decision...",
        "status": "Modified",
        "condition_indication": "Treatment of...",
        "overall_status": "PASS"
    }

    row = extract_row_from_json(filename, data)
    assert row["file_name"] == filename
    assert row["generic_name"] == "ganaxolone"
    assert row["brand_name"] == "Ztalmy"
    assert row["sponsor"] == "Marinus Pharmaceuticals Inc."
    assert row["pip_number"] == "EMEA-002341-PIP01-18-M03"
    assert row["decision_number"] == "P/0350/2024"
    assert row["decision_date"] == "2024-09-27"
    assert row["decision_type"] == "PM: decision..."
    assert row["status"] == "Modified"
    assert row["condition_indication"] == "Treatment of..."
    assert row["overall_status"] == "PASS"

def test_export_all_to_csv(tmp_path, monkeypatch):
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    file1_name = "EMEA-002341-PIP01-18-M03_Modified_validation.json"
    file1_data = {
        "generic_name": "ganaxolone",
        "brand_name": "Ztalmy",
        "sponsor": "Marinus Pharmaceuticals Inc.",
        "pip_number": "EMEA-002341-PIP01-18-M03",
        "decision_number": "P/0350/2024",
        "decision_date": "2024-09-27",
        "decision_type": "PM: decision...",
        "status": "Modified",
        "condition_indication": "Treatment of...",
        "overall_status": "PASS"
    }
    (results_dir / file1_name).write_text(json.dumps(file1_data), encoding="utf-8")

    file2_name = "EMEA-002341-PIP02-23_Original_validation.json"
    file2_data = {
        "generic_name": "ganaxolone",
        "brand_name": "Ztalmy",
        "sponsor": "Marinus Pharmaceuticals Inc.",
        "pip_number": "EMEA-002341-PIP02-23",
        "decision_number": "P/0100/2023",
        "decision_date": "2023-01-15",
        "decision_type": "Original",
        "status": "Original",
        "condition_indication": "Treatment of CDKL5 deficiency disorder",
        "overall_status": "PASS"
    }
    (results_dir / file2_name).write_text(json.dumps(file2_data), encoding="utf-8")

    monkeypatch.setattr("app.validation.csv_exporter.RESULTS_DIR", results_dir)
    monkeypatch.setattr("app.validation.csv_exporter.EXTRACTED_DIR", tmp_path / "non_existent")

    out_csv = tmp_path / "output.csv"
    res = export_all_to_csv(out_csv)
    assert res.exists()

    with open(res, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert list(reader[0].keys()) == CSV_HEADERS
        assert reader[0]["file_name"] == file1_name
        assert reader[0]["generic_name"] == "ganaxolone"
        assert reader[0]["pip_number"] == "EMEA-002341-PIP01-18-M03"
        assert reader[1]["file_name"] == file2_name
        assert reader[1]["pip_number"] == "EMEA-002341-PIP02-23"
