import asyncio, json, re
from pathlib import Path
from ..config import settings, EXTRACTED_DIR, RESULTS_DIR
from ..database.database import Database
from ..browser.kari_browser import KARIClient
from ..pdf.docling_extractor import extract_with_docling
from ..pdf.pymupdf_fallback import extract_with_pymupdf
from ..ui.metadata_extractor import normalize_metadata_keys
from ..validation.metadata_validator import compare_metadata
from ..validation.section_validator import validate_sections
from ..validation.semantic_validator import SemanticValidator
from ..worker.queue import stream_jobs_from_excel

from ..validation.ui_pdf_validator import compare_ui_vs_pdf
from ..validation.report_formatter import generate_reports
from ..validation.csv_exporter import export_all_to_csv

def get_report_key(job: dict) -> str:
    pip = job.get('pip_number') or job.get('medicine_name', 'PIP')
    status = (job.get('status') or '').strip()
    if status and status.lower() not in {'unknown', 'none'}:
        safe_status = re.sub(r'[^a-zA-Z0-9_-]', '_', status)
        return f"{pip}_{safe_status}"
    return pip

def cleanup_temp_files(pip: str, pdf_path: Path = None):
    """Delete intermediate PDF and extracted JSON files after result reports are saved."""
    to_delete = [
        pdf_path,
        EXTRACTED_DIR / f"{pip}_pdf.json",
        EXTRACTED_DIR / f"{pip}_ui.json",
    ]
    for file_path in to_delete:
        try:
            if file_path and Path(file_path).exists():
                Path(file_path).unlink()
                print(f"[CLEANUP] Deleted temp file: {file_path}")
        except Exception as ex:
            print(f"[CLEANUP] Could not remove {file_path}: {ex}")

class Runner:
    def __init__(self, db=None):
        self.db = db

    def _set_status(self, jid, status, error=None):
        if self.db and jid is not None:
            self.db.set_status(jid, status, error)

    def _save_result(self, mid, overall, result_json):
        if self.db and mid is not None:
            self.db.save_result(mid, overall, result_json)

    async def run_one(self, job, client):
        jid = job.get('id') if isinstance(job, dict) else (job['id'] if 'id' in job.keys() else None)
        mid = job.get('medicine_id') if isinstance(job, dict) else (job['medicine_id'] if 'medicine_id' in job.keys() else None)
        pip = job.get('pip_number') or job.get('medicine_name', 'PIP')
        report_key = get_report_key(job)
        self._set_status(jid, 'SEARCHING')
        try:
            await client.search(job['medicine_name'])
            row = await client.select_pip(
                pip_number=job.get('pip_number', ''),
                generic_name=job.get('generic_name', ''),
                brand_name=job.get('brand_name', ''),
                decision_date=job.get('decision_date', ''),
                status=job.get('status', '')
            )
            self._set_status(jid, 'PIP_FOUND')
            # 1. Open comparison view & extract UI comparison table data (includes 3x expand/collapse)
            ui = await client.compare(row)
            (EXTRACTED_DIR / f"{report_key}_ui.json").write_text(json.dumps(ui, ensure_ascii=False, indent=2), encoding='utf-8')
            self._set_status(jid, 'UI_EXTRACTED')

            # 2. Download the PDF directly from the comparison table header button
            pdf_path = Path(EXTRACTED_DIR).parent / 'pdf' / f"{report_key}.pdf"
            pdf_path = await client.retrieve_pdf_from_comparison(pip)
            self._set_status(jid, 'PDF_RETRIEVED')

            # 3. Extract data from the downloaded PDF
            pdf = extract_with_docling(pdf_path)
            if not pdf.get('available'):
                pdf = extract_with_pymupdf(pdf_path)
            (EXTRACTED_DIR / f"{report_key}_pdf.json").write_text(json.dumps(pdf, ensure_ascii=False, indent=2), encoding='utf-8')
            self._set_status(jid, 'PDF_EXTRACTED')

            # 4. Perform direct UI vs PDF Validation
            ui_vs_pdf = compare_ui_vs_pdf(ui, pdf)

            # 5. Excel Metadata Comparison
            excel_meta=normalize_metadata_keys({
                'generic_name':job.get('generic_name',''),'brand_name':job.get('brand_name',''),'sponsor':job.get('sponsor',''),
                'pip_number':job.get('pip_number',''),'decision_number':job.get('decision_number',''),'decision_date':job.get('decision_date',''),
                'decision_type':job.get('decision_type',''),'status':job.get('status',''),'therapeutic_area':job.get('therapeutic_area',''),
                'condition_indication':job.get('condition_indication','')})
            ui_meta = normalize_metadata_keys(ui.get('metadata', {}))
            metadata = compare_metadata(excel_meta, ui_meta)

            sections=validate_sections(pdf.get('sections',[]),ui.get('sections',[]))
            semantic=[]
            sv=SemanticValidator(settings.llm_base_url,settings.llm_api_key,settings.llm_model)
            for item in sections['missing_candidates']:
                semantic.append(await sv.compare(item, {'sections':ui.get('sections',[])}, 'Find an equivalent UI section for this PDF section.'))
            missing=[x for x,r in zip(sections['missing_candidates'],semantic) if r.get('decision')!='MATCH']
            
            has_ui_pdf_mismatches = bool(ui_vs_pdf['metadata']['mismatches']) or bool(ui_vs_pdf['sections']['missing_sections_in_ui'])
            overall='PASS' if not metadata['mismatches'] and not missing and not has_ui_pdf_mismatches else 'FAIL'
            
            result = {
                'medicine': job['medicine_name'],
                'generic_name': job.get('generic_name', ''),
                'brand_name': job.get('brand_name') or job.get('medicine_name', ''),
                'sponsor': job.get('sponsor', ''),
                'pip_number': pip,
                'decision_number': job.get('decision_number', ''),
                'decision_date': job.get('decision_date', ''),
                'decision_type': job.get('decision_type', ''),
                'status': job.get('status', ''),
                'condition_indication': job.get('condition_indication', '') or job.get('therapeutic_areas', '') or job.get('therapeutic_area', ''),
                'overall_status': overall,
                'ui_vs_pdf_validation': ui_vs_pdf,
                'metadata_validation': metadata,
                'section_validation': {
                    'exact_matches': len(sections['matched']),
                    'missing_in_ui': len(missing),
                    'uncertain': sum(1 for r in semantic if r.get('decision')=='UNCERTAIN')
                },
                'missing_sections_in_ui': [x.get('label') or x.get('key') for x in missing],
                'semantic_checks': semantic
            }
            (RESULTS_DIR / f"{report_key}_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            generate_reports(result, report_key)
            self._save_result(mid, overall, json.dumps(result, ensure_ascii=False))
            self._set_status(jid, 'COMPLETED')
            cleanup_temp_files(report_key, pdf_path)
            return result
        except Exception as e:
            self._set_status(jid, 'ERROR', str(e)); raise

    MAX_RETRIES = 3
    RESET_INTERVAL = 25  # Refresh workspace every 25 drugs to maintain peak browser performance

    async def run_stream(self, excel_path: str | Path, limit: int | None = None, medicine: str | None = None, skip_existing: bool = True):
        """Stream jobs directly from Excel without using a database."""
        jobs = stream_jobs_from_excel(excel_path, limit=limit, medicine=medicine)
        print(f"[STREAM RUNNER] Streamed {len(jobs)} drug record(s) from {Path(excel_path).name}", flush=True)

        client = KARIClient()
        processed_count = 0
        skipped_count = 0
        failed_count = 0
        batch_count = 0

        try:
            await client.start()
            for idx, job in enumerate(jobs, 1):
                report_key = get_report_key(job)
                report_file = RESULTS_DIR / f"{report_key}_report.md"
                val_file = RESULTS_DIR / f"{report_key}_validation.json"

                if skip_existing and (report_file.exists() or val_file.exists()):
                    print(f"[STREAM RUNNER] [{idx}/{len(jobs)}] Skipping already completed drug: {job['medicine_name']} ({report_key})", flush=True)
                    skipped_count += 1
                    if not val_file.exists():
                        skipped_result = {
                            'medicine': job['medicine_name'],
                            'generic_name': job.get('generic_name', ''),
                            'brand_name': job.get('brand_name') or job.get('medicine_name', ''),
                            'sponsor': job.get('sponsor', ''),
                            'pip_number': job.get('pip_number') or job.get('medicine_name', 'PIP'),
                            'decision_number': job.get('decision_number', ''),
                            'decision_date': job.get('decision_date', ''),
                            'decision_type': job.get('decision_type', ''),
                            'status': job.get('status', ''),
                            'condition_indication': job.get('condition_indication', '') or job.get('therapeutic_area', ''),
                            'overall_status': 'SKIPPED',
                        }
                        val_file.write_text(json.dumps(skipped_result, ensure_ascii=False, indent=2), encoding='utf-8')
                    continue

                if batch_count > 0 and batch_count % self.RESET_INTERVAL == 0:
                    print(f"[STREAM RUNNER] Processed {batch_count} drugs in current workspace. Resetting chat thread to keep DOM fast...", flush=True)
                    try:
                        await client.reset_workspace()
                    except Exception as ex:
                        print(f"[STREAM RUNNER] Workspace reset notice: {ex}", flush=True)

                print(f"[STREAM RUNNER] [{idx}/{len(jobs)}] Processing drug: {job['medicine_name']} ({report_key})", flush=True)
                try:
                    await self.run_one(job, client)
                    processed_count += 1
                    batch_count += 1
                except Exception as e:
                    failed_count += 1
                    print(f"[STREAM RUNNER] Error processing {job['medicine_name']}: {e}", flush=True)
                    if not val_file.exists():
                        failed_result = {
                            'medicine': job['medicine_name'],
                            'generic_name': job.get('generic_name', ''),
                            'brand_name': job.get('brand_name') or job.get('medicine_name', ''),
                            'sponsor': job.get('sponsor', ''),
                            'pip_number': job.get('pip_number') or job.get('medicine_name', 'PIP'),
                            'decision_number': job.get('decision_number', ''),
                            'decision_date': job.get('decision_date', ''),
                            'decision_type': job.get('decision_type', ''),
                            'status': job.get('status', ''),
                            'condition_indication': job.get('condition_indication', '') or job.get('therapeutic_area', ''),
                            'overall_status': 'FAIL',
                            'error_message': str(e),
                        }
                        val_file.write_text(json.dumps(failed_result, ensure_ascii=False, indent=2), encoding='utf-8')
                    try:
                        page = await client.ensure_active_page()
                        await page.goto(settings.kari_base_url, wait_until="domcontentloaded")
                        await page.wait_for_timeout(1000)
                    except Exception:
                        pass
        finally:
            await client.close()
            export_all_to_csv()

        print(f"\n[STREAM RUNNER SUMMARY] Completed: {processed_count} | Skipped: {skipped_count} | Failed: {failed_count} | Total: {len(jobs)}")

    async def run(self, owner=None):
        if not self.db:
            self.db = Database()
        # Create one browser session for the entire batch — login once.
        client = KARIClient()
        try:
            await client.start()
            while True:
                job = self.db.next_job(owner)
                if not job:
                    print(f"[RUNNER] No pending jobs found in database for owner: {owner or 'ALL'}", flush=True)
                    break
                retry = job['retry_count'] or 0
                if retry >= self.MAX_RETRIES:
                    print(f"[RUNNER] Job {job['id']} exceeded max retries ({self.MAX_RETRIES}), skipping.", flush=True)
                    self.db.set_status(job['id'], 'FAILED_PERMANENT', 'Max retries exceeded')
                    continue
                print(f"[RUNNER] Processing job {job['id']}: {job['medicine_name']} ({job['pip_number']}) [attempt {retry+1}/{self.MAX_RETRIES}]", flush=True)
                try:
                    await self.run_one(job, client)
                    self.db.increment_retry(job['id'], reset=True)
                except Exception as e:
                    self.db.increment_retry(job['id'])
                    print(f"Job {job['id']} failed: {e}", flush=True)
                    # Navigate back to home for the next job/retry
                    try:
                        page = await client.ensure_active_page()
                        await page.goto(settings.kari_base_url, wait_until="domcontentloaded")
                        await page.wait_for_timeout(1000)
                    except Exception:
                        pass
        finally:
            await client.close()
            export_all_to_csv()

