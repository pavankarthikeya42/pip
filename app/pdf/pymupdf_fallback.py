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

def extract_pdf_sections(full_text: str, page_tables: list = None) -> list:
    """Extract structured sections from the full PDF text.

    Args:
        full_text: Concatenated text of all PDF pages.
        page_tables: List of table dicts [{"page": int, "rows": [[str,...],...]},...] from PyMuPDF.
    """
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

    # The heading can wrap across lines, e.g.:
    #   "Subset(s) of the paediatric population concerned by the paediatric \n"
    #   "development \n"
    #   "From 6 months to less than 18 years of age \n"
    # We need to skip the full multi-line heading and capture the content line after it.
    subset_match = re.search(
        r'Subset\(s\) of the paediatric population concerned'
        r'[^\n]*\n'          # rest of first heading line
        r'(?:[^\n]*?(?:development|investigation)\s*\n)?'  # optional wrapped heading continuation
        r'\s*([^\n]+)',      # capture the actual content line
        full_text, re.I
    )
    if subset_match:
        captured = subset_match.group(1).strip()
        # Guard: if the captured text looks like a section heading, skip it
        if not re.match(r'^\d+\.\d+', captured) and len(captured) > 3:
            sections.append({
                "key": "subset_of_population_for_paediatric_development",
                "label": "Subset of Population for Paediatric Development",
                "text": captured
            })

    # Extract studies from PyMuPDF table data (Area / Description columns).
    # Tables are already extracted by extract_with_pymupdf and passed here.
    studies_rows = _extract_studies_from_tables(page_tables or [])
    if studies_rows:
        # Build a tab-separated text representation matching the UI format:
        #   "Area\tDescription\nQuality-related\nstudies\tNot applicable.\n..."
        lines = ["Area\tDescription"]
        for area, desc in studies_rows:
            lines.append(f"{area}\t{desc}")
        sections.append({
            "key": "studies",
            "label": "Studies",
            "text": "\n".join(lines)
        })
    elif "Clinical studies" in full_text or "Quality-related" in full_text:
        # Fallback: extract studies from raw text using regex
        studies_text = _extract_studies_from_text(full_text)
        sections.append({
            "key": "studies",
            "label": "Studies",
            "text": studies_text
        })

    return sections


# Known study area labels that appear in PIP decision PDFs.
_STUDY_AREAS = [
    "Quality-related studies",
    "Non-clinical studies",
    "Clinical studies",
    "Extrapolation, modelling and simulation studies",
    "Other studies",
    "Other measures",
]

def _extract_studies_from_tables(page_tables: list) -> list:
    """Extract (area, description) pairs from PyMuPDF table data.

    Looks for tables whose first row is [Area, Description] or whose first
    column values match known study area labels.
    """
    rows_out = []
    for tbl in page_tables:
        raw_rows = tbl.get("rows", [])
        if not raw_rows:
            continue
        for row in raw_rows:
            if len(row) < 2:
                continue
            cell0 = (row[0] or "").replace("\n", " ").strip()
            cell1 = (row[1] or "").replace("\n", " ").strip()
            # Skip the header row itself
            if cell0.lower() == "area" and cell1.lower() == "description":
                continue
            # Check if this row is a study area row
            cell0_norm = cell0.lower()
            if any(area.lower() in cell0_norm or cell0_norm in area.lower() for area in _STUDY_AREAS):
                rows_out.append((cell0, cell1))
    return rows_out


def _extract_studies_from_text(full_text: str) -> str:
    """Fallback: extract studies section content from raw text using regex."""
    study_entries = []
    for area in _STUDY_AREAS:
        # Each area label may be split across lines in the PDF text
        # e.g. "Quality-related \nstudies \nNot applicable."
        escaped = re.escape(area).replace(r"\ ", r"\s+").replace(r"\-", r"[-\s]+")
        pattern = escaped + r'\s*\n?\s*(.+?)(?=\n\s*(?:' + '|'.join(
            re.escape(a).replace(r"\ ", r"\s+").replace(r"\-", r"[-\s]+")
            for a in _STUDY_AREAS if a != area
        ) + r'|\d+\.\d+|$))'
        m = re.search(pattern, full_text, re.I | re.DOTALL)
        if m:
            desc = re.sub(r'\s+', ' ', m.group(1)).strip()
            study_entries.append(f"{area}: {desc}")
    return "\n".join(study_entries) if study_entries else "Studies content not extracted"


def extract_with_pymupdf(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    pages = []
    full_text_list = []
    all_tables = []
    for i, p in enumerate(doc, 1):
        text = p.get_text("text")
        full_text_list.append(text)
        tables = []
        try:
            tf = p.find_tables()
            for table in tf.tables:
                tbl_data = {"page": i, "rows": table.extract()}
                tables.append(tbl_data)
                all_tables.append(tbl_data)
        except Exception:
            pass
        pages.append({"page": i, "text": text, "tables": tables})
    
    full_text = "\n\n".join(full_text_list)
    meta = extract_pdf_metadata(full_text)
    sections = extract_pdf_sections(full_text, all_tables)

    return {
        "available": True,
        "pages": pages,
        "text": full_text,
        "metadata": meta,
        "sections": sections
    }

