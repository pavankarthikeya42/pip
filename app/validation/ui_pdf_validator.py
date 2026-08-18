from .normalizer import norm, norm_id
import re

ID_FIELDS = {"pip_number", "decision_number"}


def _compare_section_content(pdf_txt: str, ui_txt: str) -> bool:
    """Compare section content with tolerance for UI noise (e.g. injected page headers).

    Strategy:
    1. If either text is empty, treat as match (no content to compare).
    2. Simple substring check (fast path).
    3. Chunk-based: split PDF text into meaningful segments and verify each
       segment exists somewhere in the UI text. This handles cases where
       the UI injects page headers/footers in the middle of section content.
    """
    if not pdf_txt or not ui_txt:
        return True

    norm_pdf = norm(pdf_txt)
    norm_ui = norm(ui_txt)

    # Fast path: simple containment
    if norm_pdf in norm_ui or norm_ui in norm_pdf:
        return True

    # Chunk-based comparison: split PDF content by tab-separated entries
    # (for table-like sections) or by sentences, and check each chunk exists in UI.
    # Split on tab or newline boundaries to get meaningful content chunks.
    chunks = re.split(r'[\t\n]+', pdf_txt)
    chunks = [c.strip() for c in chunks if c.strip()]

    if not chunks:
        return True

    matched_chunks = 0
    for chunk in chunks:
        norm_chunk = norm(chunk)
        # Skip very short chunks (headers like "Area", "Description")
        if len(norm_chunk) < 4:
            matched_chunks += 1
            continue
        if norm_chunk in norm_ui:
            matched_chunks += 1

    # Consider it a match if at least 80% of meaningful chunks are found in the UI
    ratio = matched_chunks / len(chunks) if chunks else 1.0
    return ratio >= 0.8

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
            
            content_match = _compare_section_content(pdf_txt, ui_txt)
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
