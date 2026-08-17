from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

class Settings(BaseModel):
    kari_base_url: str = os.getenv("KARI_BASE_URL", "")
    kari_search_url: str = os.getenv("KARI_SEARCH_URL", "")
    kari_username: str = os.getenv("KARI_USERNAME", "")
    kari_password: str = os.getenv("KARI_PASSWORD", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    headless: bool = os.getenv("HEADLESS", "false").lower() == "true"
    playwright_slow_mo_ms: int = int(os.getenv("PLAYWRIGHT_SLOW_MO_MS", "100"))
    min_action_delay: float = float(os.getenv("MIN_ACTION_DELAY", "0.5"))
    max_wait_seconds: int = int(os.getenv("MAX_WAIT_SECONDS", "30"))
    retry_count: int = int(os.getenv("RETRY_COUNT", "2"))
    owner: str = os.getenv("OWNER", "USER_1")
    kari_sources: list[str] = [x.strip() for x in os.getenv("KARI_SOURCES", "USPI,PIP").split(",") if x.strip()]
    kari_meta_prompt_template: str = os.getenv(
        "KARI_META_PROMPT_TEMPLATE",
        'Find the regulatory PIP information for the medicine "{medicine_name}". '
        'Use the selected USPI and PIP sources. Return the relevant PIP result and its comparison option. '
        'Do not infer or invent data.'
    )

settings = Settings()
PDF_DIR = ROOT / "data" / "pdf"
EXTRACTED_DIR = ROOT / "data" / "extracted"
RESULTS_DIR = ROOT / "data" / "results"
REFERENCE_DIR = ROOT / "data" / "reference"
for p in (PDF_DIR, EXTRACTED_DIR, RESULTS_DIR):
    p.mkdir(parents=True, exist_ok=True)
