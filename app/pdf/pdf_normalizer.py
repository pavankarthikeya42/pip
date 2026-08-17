import re, unicodedata

def normalize_text(value: str) -> str:
    if value is None: return ""
    value = unicodedata.normalize("NFKC", str(value))
    value = re.sub(r"\s+", " ", value).strip().casefold()
    return value

def normalize_identifier(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or "")).casefold())
