from .normalizer import norm, norm_id, norm_date

ID_FIELDS = {"pip_number", "decision_number"}
DATE_FIELDS = {"decision_date", "first_published", "last_updated", "discontinue_date"}

def compare_metadata(excel: dict, ui: dict, pdf: dict):
    out = {"excel_ui": {}, "excel_pdf": {}, "mismatches": []}
    for key, expected in excel.items():
        if not expected: continue
        for name, actuals in (("ui", ui), ("pdf", pdf)):
            actual = actuals.get(key, "")
            if key in ID_FIELDS:
                same = norm_id(expected) == norm_id(actual)
            elif "date" in key or key in DATE_FIELDS:
                same = norm_date(expected) == norm_date(actual)
            else:
                same = norm(expected) == norm(actual)
            out[f"excel_{name}"][key] = "PASS" if same else "MISMATCH"
            if not same:
                out["mismatches"].append({"field": key, "source": name, "excel": expected, "actual": actual})
    return out
