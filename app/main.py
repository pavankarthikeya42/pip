import argparse, asyncio
from .database.database import Database
from .worker.queue import load_jobs_from_excel
from .worker.runner import Runner
from .config import settings, RESULTS_DIR
from .validation.csv_exporter import export_all_to_csv


def main():
    p = argparse.ArgumentParser(description="PDF <-> KARI validation tool")
    p.add_argument('--import-excel', help='Path to the PIP Excel export')
    p.add_argument('--stream-excel', help='Path to PIP Excel export for Direct DB-less Stream validation')
    p.add_argument('--owner', default=settings.owner, help='Owner/user name')
    p.add_argument('--medicine', help='Import/test only one medicine by Brand Name')
    p.add_argument('--limit', type=int, help='Import at most N medicine rows')
    p.add_argument('--no-skip', action='store_true', help='Do not skip already completed drugs in stream mode')
    p.add_argument('--run', action='store_true', help='Run the validation worker')
    p.add_argument('--export-csv', nargs='?', const=str(RESULTS_DIR / "all_validation_results.csv"), help='Export all validation results to a single CSV file')
    args = p.parse_args()

    if args.export_csv:
        csv_path = export_all_to_csv(args.export_csv)
        print(f"Exported validation results CSV to: {csv_path}")
        return

    if args.stream_excel:
        asyncio.run(
            Runner().run_stream(
                excel_path=args.stream_excel,
                limit=args.limit,
                medicine=args.medicine,
                skip_existing=not args.no_skip,
            )
        )
        return

    db = Database()
    if args.import_excel:
        count = load_jobs_from_excel(
            db, args.import_excel, args.owner,
            limit=args.limit, medicine=args.medicine
        )
        print(f"Imported {count} medicine record(s) for {args.owner}")
        if args.medicine:
            row = db.get_medicine(args.medicine, args.owner)
            if row:
                print("\nImported metadata:")
                print(f"  Brand Name: {row['brand_name']}")
                print(f"  Generic Name: {row['generic_name']}")
                print(f"  Sponsor: {row['sponsor']}")
                print(f"  PIP Number: {row['pip_number']}")
                print(f"  Decision Type: {row['decision_type']}")
                print(f"  Decision Date: {row['decision_date']}")
                print(f"  Status: {row['status']}")
                print(f"  Therapeutic Areas: {row['therapeutic_area']}")
                print(f"  Decision Number: {row['decision_number']}")
                print(f"  Source: {row['source_file']} row {row['source_row']}")
    if args.run:
        asyncio.run(Runner(db).run(args.owner))


if __name__=='__main__':
    main()

