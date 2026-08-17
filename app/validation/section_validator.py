from .normalizer import norm

def section_index(sections):
    return {norm(s.get("label") or s.get("key")):s for s in sections}

def validate_sections(pdf_sections, ui_sections):
    # First use exact/normalized label/key matching; unresolved mappings go to semantic validator.
    ui_idx=section_index(ui_sections)
    matched=[]; missing=[]; unresolved=[]
    for p in pdf_sections:
        keys=[norm(p.get("label")), norm(p.get("key"))]
        found=None
        for k in keys:
            if k and k in ui_idx:
                found=ui_idx[k]; break
        if found:
            matched.append({"pdf":p,"ui":found})
        else:
            unresolved.append(p)
    return {"matched":matched,"missing_candidates":unresolved,"extra_ui":[u for k,u in ui_idx.items() if not any(k in (norm(m["pdf"].get("label")),norm(m["pdf"].get("key"))) for m in matched)]}
