import re, unicodedata

def norm(v):
    v = unicodedata.normalize("NFKC", str(v or ""))
    v = v.replace("\u2013","-").replace("\u2014","-")
    return re.sub(r"\s+", " ", v).strip().casefold()

def norm_id(v):
    return re.sub(r"\s+", "", norm(v))
