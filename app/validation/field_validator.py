from .normalizer import norm

def compare_values(pdf_value, ui_value):
    if norm(pdf_value)==norm(ui_value): return "MATCH"
    return "MISMATCH"
