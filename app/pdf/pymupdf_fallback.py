from pathlib import Path
import fitz

import re

def extract_pdf_metadata(full_text: str) -> dict:
    meta = {}
    pip_match = re.search(r'(EMEA-\d{6}-PIP\d{2}-\d{2}(?:-M\d+)?|\bEMEA-\d+-\S+)', full_text)
    if pip_match:
        meta['pip_number'] = pip_match.group(1).strip()

    dec_num_match = re.search(r'\b(P/\d{4}/\d{4})\b', full_text)
    if dec_num_match:
        meta['decision_number'] = dec_num_match.group(1).strip()

    dec_date_match = re.search(r'of\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})', full_text)
    if dec_date_match:
        meta['decision_date'] = dec_date_match.group(1).strip()

    active_match = re.search(r'Active substance\(s\):\s*\n?\s*([^\n]+)', full_text, re.I)
    if active_match:
        meta['generic_name'] = active_match.group(1).strip()

    brand_match = re.search(r'for\s+[a-z\s\(\)]*?\b([A-Z][a-zA-Z0-9]+)\b\s*,\s*\([^)]*PIP', full_text)
    if brand_match:
        meta['brand_name'] = brand_match.group(1).strip()

    sponsor_match = re.search(r'(?:addressed to|Name/corporate name of the PIP applicant:)\s*\n?\s*([^\n,]+)', full_text, re.I)
    if sponsor_match:
        meta['sponsor'] = sponsor_match.group(1).strip()

    condition_match = re.search(r'Condition\(s\):\s*\n?\s*([^\n]+)', full_text, re.I)
    if condition_match:
        meta['condition_indication'] = condition_match.group(1).strip()

    return meta

def extract_pdf_sections(full_text: str) -> list:
    sections = []
    
    member_match = re.search(r'(The Paediatric Committee member of [^\n\.]+)', full_text, re.I)
    if member_match:
        sections.append({
            "key": "paediatric_community_member_state",
            "label": "Paediatric Community Member State",
            "text": member_match.group(1).strip()
        })
        
    waiver_match = re.search(r'The waiver applies to:\s*\n?\s*•?\s*([^\;\n\.]+)', full_text, re.I)
    if waiver_match:
        sections.append({
            "key": "waiver_age",
            "label": "Waiver Age",
            "text": waiver_match.group(1).strip()
        })

    subset_match = re.search(r'Subset\(s\) of the paediatric population concerned[^\n]*\n?\s*([^\n]+)', full_text, re.I)
    if subset_match:
        sections.append({
            "key": "subset_of_population_for_paediatric_development",
            "label": "Subset of Population for Paediatric Development",
            "text": subset_match.group(1).strip()
        })

    if "Clinical studies" in full_text or "Quality-related" in full_text:
        sections.append({
            "key": "studies",
            "label": "Studies",
            "text": "Studies extracted from PDF"
        })

    return sections

def extract_with_pymupdf(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    pages = []
    full_text_list = []
    for i, p in enumerate(doc, 1):
        text = p.get_text("text")
        full_text_list.append(text)
        tables = []
        try:
            tf = p.find_tables()
            for table in tf.tables:
                tables.append({"page": i, "rows": table.extract()})
        except Exception:
            pass
        pages.append({"page": i, "text": text, "tables": tables})
    
    full_text = "\n\n".join(full_text_list)
    meta = extract_pdf_metadata(full_text)
    sections = extract_pdf_sections(full_text)

    return {
        "available": True,
        "pages": pages,
        "text": full_text,
        "metadata": meta,
        "sections": sections
    }
