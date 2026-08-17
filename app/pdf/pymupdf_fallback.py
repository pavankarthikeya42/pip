from pathlib import Path
import fitz

def extract_with_pymupdf(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    pages=[]
    for i,p in enumerate(doc,1):
        text=p.get_text("text")
        tables=[]
        try:
            tf=p.find_tables()
            for table in tf.tables:
                tables.append({"page":i,"rows":table.extract()})
        except Exception:
            pass
        pages.append({"page":i,"text":text,"tables":tables})
    return {"available": True, "pages":pages, "text":"\n\n".join(x["text"] for x in pages)}
