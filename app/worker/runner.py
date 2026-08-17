import asyncio, json
from pathlib import Path
from ..config import settings, EXTRACTED_DIR
from ..database.database import Database
from ..browser.kari_browser import KARIClient
from ..pdf.docling_extractor import extract_with_docling
from ..pdf.pymupdf_fallback import extract_with_pymupdf
from ..ui.metadata_extractor import normalize_metadata_keys
from ..validation.metadata_validator import compare_metadata
from ..validation.section_validator import validate_sections
from ..validation.semantic_validator import SemanticValidator

class Runner:
    def __init__(self, db=None): self.db=db or Database()
    async def run_one(self, job, client):
        jid=job['id']; mid=job['medicine_id']; pip=job['pip_number'] or job['medicine_name']
        self.db.set_status(jid,'SEARCHING')
        try:
            await client.search(job['medicine_name'])
            row=await client.select_pip(job['pip_number'],job['generic_name'],job['brand_name'])
            self.db.set_status(jid,'PIP_FOUND')
            pdf_path=Path(EXTRACTED_DIR).parent / 'pdf' / f"{pip}.pdf"
            if not pdf_path.exists(): pdf_path=await client.retrieve_pdf(row,pip)
            self.db.set_status(jid,'PDF_RETRIEVED')
            pdf=extract_with_docling(pdf_path)
            if not pdf.get('available'): pdf=extract_with_pymupdf(pdf_path)
            (EXTRACTED_DIR/f"{pip}_pdf.json").write_text(json.dumps(pdf,ensure_ascii=False,indent=2),encoding='utf-8')
            self.db.set_status(jid,'PDF_EXTRACTED')
            ui=await client.compare(row)
            (EXTRACTED_DIR/f"{pip}_ui.json").write_text(json.dumps(ui,ensure_ascii=False,indent=2),encoding='utf-8')
            self.db.set_status(jid,'UI_EXTRACTED')
            excel_meta=normalize_metadata_keys({
                'generic_name':job['generic_name'],'brand_name':job['brand_name'],'sponsor':job['sponsor'],
                'pip_number':job['pip_number'],'decision_number':job['decision_number'],'decision_date':job['decision_date'],
                'decision_type':job['decision_type'],'status':job['status'],'therapeutic_area':job['therapeutic_area'],
                'condition_indication':job['condition_indication']})
            ui_meta=normalize_metadata_keys(ui.get('metadata',{}))
            pdf_meta={}  # populated by semantic PDF field extraction in next iteration; raw PDF remains traceable.
            metadata=compare_metadata(excel_meta,ui_meta,pdf_meta)
            sections=validate_sections(pdf.get('sections',[]),ui.get('sections',[]))
            semantic=[]
            sv=SemanticValidator(settings.llm_base_url,settings.llm_api_key,settings.llm_model)
            for item in sections['missing_candidates']:
                # Only call LLM for unresolved semantic mappings.
                semantic.append(await sv.compare(item, {'sections':ui.get('sections',[])}, 'Find an equivalent UI section for this PDF section.'))
            missing=[x for x,r in zip(sections['missing_candidates'],semantic) if r.get('decision')!='MATCH']
            overall='PASS' if not metadata['mismatches'] and not missing else 'FAIL'
            result={'medicine':job['medicine_name'],'pip_number':job['pip_number'],'overall_status':overall,
                    'metadata_validation':metadata,'section_validation':{'exact_matches':len(sections['matched']),'missing_in_ui':len(missing),'uncertain':sum(1 for r in semantic if r.get('decision')=='UNCERTAIN')},
                    'missing_sections_in_ui':[x.get('label') or x.get('key') for x in missing], 'semantic_checks':semantic}
            self.db.save_result(mid,overall,json.dumps(result,ensure_ascii=False))
            self.db.set_status(jid,'COMPLETED')
            return result
        except Exception as e:
            self.db.set_status(jid,'ERROR',str(e)); raise

    MAX_RETRIES = 3

    async def run(self, owner=None):
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
                        await client.page.goto(settings.kari_base_url, wait_until="domcontentloaded")
                        await client.page.wait_for_timeout(1000)
                    except Exception:
                        pass
        finally:
            await client.close()
