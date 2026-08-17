from .normalizer import norm, norm_id

ID_FIELDS={"pip_number","decision_number"}

def compare_metadata(excel: dict, ui: dict, pdf: dict):
    out={"excel_ui":{},"excel_pdf":{},"mismatches":[]}
    for key, expected in excel.items():
        if not expected: continue
        for name, actuals in (("ui",ui),("pdf",pdf)):
            actual=actuals.get(key,"")
            same=(norm_id(expected)==norm_id(actual)) if key in ID_FIELDS else (norm(expected)==norm(actual))
            out[f"excel_{name}"][key]="PASS" if same else "MISMATCH"
            if not same:
                out["mismatches"].append({"field":key,"source":name,"excel":expected,"actual":actual})
    return out
