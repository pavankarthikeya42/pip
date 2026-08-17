from .normalizer import norm, norm_id

ID_FIELDS = {"pip_number", "decision_number"}

KEY_ALIASES = {
    "generic": "generic_name",
    "generic_name": "generic_name",
    "sponsor": "sponsor",
    "pip_number": "pip_number",
    "pip_number": "pip_number",
    "decision_number": "decision_number",
    "decision_number": "decision_number",
    "decision_date": "decision_date",
    "decision_date": "decision_date",
    "decision_type": "decision_type",
    "decision_type": "decision_type",
    "status": "status",
    "therapeutic_areas": "therapeutic_area",
    "therapeutic_area": "therapeutic_area",
    "condition___indication": "condition_indication",
    "condition_indication": "condition_indication"
}

def canonical_key(k: str) -> str:
    n = norm(k).replace(" / ", "_").replace("/", "_").replace(" ", "_")
    return KEY_ALIASES.get(n, n)

def compare_ui_vs_pdf(ui: dict, pdf: dict) -> dict:
    ui_meta = ui.get("metadata", {})
    pdf_meta = pdf.get("metadata", {})
    
    ui_meta_map = {canonical_key(k): (k, v) for k, v in ui_meta.items()}
    pdf_meta_map = {canonical_key(k): (k, v) for k, v in pdf_meta.items()}
    
    matched_fields = []
    metadata_mismatches = []
    missing_in_ui_meta = []
    extra_in_ui_meta = []
    
    all_keys = set(ui_meta_map.keys()) | set(pdf_meta_map.keys())
    
    for ck in all_keys:
        in_ui = ck in ui_meta_map
        in_pdf = ck in pdf_meta_map
        
        if in_ui and in_pdf:
            orig_ui_k, ui_val = ui_meta_map[ck]
            orig_pdf_k, pdf_val = pdf_meta_map[ck]
            
            is_id = any(id_f in ck for id_f in ID_FIELDS)
            same = (norm_id(ui_val) == norm_id(pdf_val)) if is_id else (norm(ui_val) == norm(pdf_val))
            
            if same:
                matched_fields.append({
                    "field": ck,
                    "pdf_label": orig_pdf_k,
                    "ui_label": orig_ui_k,
                    "pdf_value": pdf_val,
                    "ui_value": ui_val,
                    "status": "MATCH"
                })
            else:
                metadata_mismatches.append({
                    "field": ck,
                    "pdf_label": orig_pdf_k,
                    "ui_label": orig_ui_k,
                    "pdf_value": pdf_val,
                    "ui_value": ui_val,
                    "status": "MISMATCH"
                })
        elif in_pdf and not in_ui:
            orig_pdf_k, pdf_val = pdf_meta_map[ck]
            missing_in_ui_meta.append({
                "field": ck,
                "pdf_label": orig_pdf_k,
                "pdf_value": pdf_val,
                "status": "MISSING_IN_UI"
            })
        elif in_ui and not in_pdf:
            orig_ui_k, ui_val = ui_meta_map[ck]
            extra_in_ui_meta.append({
                "field": ck,
                "ui_label": orig_ui_k,
                "ui_value": ui_val,
                "status": "EXTRA_IN_UI"
            })
            
    # Section comparison
    pdf_sections = pdf.get("sections", [])
    ui_sections = ui.get("sections", [])
    
    ui_sec_map = {norm(s.get("label") or s.get("key")): s for s in ui_sections}
    pdf_sec_map = {norm(s.get("label") or s.get("key")): s for s in pdf_sections}
    
    matched_sections = []
    missing_sections_in_ui = []
    extra_sections_in_ui = []
    
    for pdf_nk, pdf_sec in pdf_sec_map.items():
        if pdf_nk in ui_sec_map:
            ui_sec = ui_sec_map[pdf_nk]
            pdf_txt = pdf_sec.get("text", "")
            ui_txt = ui_sec.get("text", "")
            
            content_match = (norm(pdf_txt) in norm(ui_txt) or norm(ui_txt) in norm(pdf_txt)) if (pdf_txt and ui_txt) else True
            matched_sections.append({
                "label": pdf_sec.get("label") or pdf_sec.get("key"),
                "pdf_text": pdf_txt,
                "ui_text": ui_txt,
                "content_status": "MATCH" if content_match else "CONTENT_MISMATCH"
            })
        else:
            missing_sections_in_ui.append({
                "label": pdf_sec.get("label") or pdf_sec.get("key"),
                "pdf_text": pdf_sec.get("text", "")
            })
            
    for ui_nk, ui_sec in ui_sec_map.items():
        if ui_nk not in pdf_sec_map:
            extra_sections_in_ui.append({
                "label": ui_sec.get("label") or ui_sec.get("key"),
                "ui_text": ui_sec.get("text", "")
            })
            
    return {
        "metadata": {
            "matched_fields": matched_fields,
            "mismatches": metadata_mismatches,
            "missing_in_ui": missing_in_ui_meta,
            "extra_in_ui": extra_in_ui_meta
        },
        "sections": {
            "matched_sections": matched_sections,
            "missing_sections_in_ui": missing_sections_in_ui,
            "extra_sections_in_ui": extra_sections_in_ui
        }
    }
