import re, unicodedata
from datetime import datetime

def norm(v):
    v = unicodedata.normalize("NFKC", str(v or ""))
    v = v.replace("\u2013","-").replace("\u2014","-")
    return re.sub(r"\s+", " ", v).strip().casefold()

def norm_id(v):
    return re.sub(r"\s+", "", norm(v))

def norm_date(v):
    """Normalize date strings (e.g. '27 September 2024' or '2024-09-27') into ISO YYYY-MM-DD."""
    if not v:
        return ""
    v_str = str(v).strip()
    for fmt in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(v_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    try:
        from dateutil import parser
        return parser.parse(v_str).strftime("%Y-%m-%d")
    except Exception:
        pass
    return norm(v)

