from pathlib import Path

from app.database.database import Database
from app.worker.queue import detect_header_row, load_jobs_from_excel


EXCEL = Path(__file__).parents[1] / "data" / "input" / "PIP_list_all_PIP_labels_20260812_163732.xlsx"


def test_pip_export_header_row():
    import openpyxl
    wb = openpyxl.load_workbook(EXCEL, data_only=True)
    row, cols = detect_header_row(wb.active)
    assert row == 5
    assert len(cols) == 19
    assert cols["brand_name"] == 1
    assert cols["pip_number"] == 4
    assert cols["last_updated"] == 19


def test_import_zynlonta(tmp_path):
    db = Database(tmp_path / "test.db")
    count = load_jobs_from_excel(db, EXCEL, "USER_1", medicine="Zynlonta", limit=1)
    assert count == 1
    row = db.get_medicine("Zynlonta", "USER_1")
    assert row is not None
    assert row["generic_name"] == "Loncastuximab tesirine"
    assert row["pip_number"] == "EMEA-002665-PIP02-20-M01"
    assert row["decision_date"] == "2024-05-06"
    assert row["source_row"] == 6
