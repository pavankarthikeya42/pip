#!/usr/bin/env python3
"""Convenience script to aggregate all document validation JSON results into a single CSV file."""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from app.validation.csv_exporter import export_all_to_csv
from app.config import RESULTS_DIR

if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else RESULTS_DIR / "all_validation_results.csv"
    res_path = export_all_to_csv(out_path)
    print(f"Successfully generated single CSV file at: {res_path}")
