from .normalizer import norm, norm_id, norm_date

ID_FIELDS = {"pip_number", "decision_number"}
DATE_FIELDS = {"decision_date", "first_published", "last_updated", "discontinue_date"}

def is_no_data(val: str) -> bool:
    if not val:
        return True
    n = norm(str(val))
    return not n or "not addressed" in n or "no data" in n or n in {"n/a", "none", "not_addressed", "not addressed"}

def compare_metadata(excel: dict, ui: dict):
    out = {"excel_ui": {}, "mismatches": []}
    for key, expected in excel.items():
        if not expected or is_no_data(expected):
            continue
        actual = ui.get(key, "")
        if is_no_data(actual):
            out["excel_ui"][key] = "NO_DATA_IN_UI"
            continue

        if key in ID_FIELDS:
            same = norm_id(expected) == norm_id(actual)
        elif "date" in key or key in DATE_FIELDS:
            same = norm_date(expected) == norm_date(actual)
        else:
            same = norm(expected) == norm(actual)

        out["excel_ui"][key] = "PASS" if same else "MISMATCH"
        if not same:
            out["mismatches"].append({
                "field": key,
                "source": "ui",
                "excel": expected,
                "actual": actual
            })
    return out
