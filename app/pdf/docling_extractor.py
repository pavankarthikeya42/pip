from pathlib import Path

def extract_with_docling(pdf_path: Path) -> dict:
    # Use fast pymupdf extraction to prevent slow PyTorch/Docling CPU startup delays
    try:
        from .pymupdf_fallback import extract_with_pymupdf
        return extract_with_pymupdf(pdf_path)
    except Exception as e:
        return {"available": False, "error": str(e), "sections": [], "tables": [], "text": ""}
