from pathlib import Path

def extract_with_docling(pdf_path: Path) -> dict:
    try:
        from docling.document_converter import DocumentConverter
    except Exception:
        return {"available": False, "error": "Docling is not installed", "sections": [], "tables": [], "text": ""}
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document
    # Export markdown is a robust baseline; structured traversal is kept optional because
    # Docling versions expose slightly different APIs.
    markdown = doc.export_to_markdown()
    return {"available": True, "text": markdown, "sections": [], "tables": [], "provenance": {}}
