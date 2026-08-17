from dataclasses import dataclass
from typing import Optional

@dataclass
class Medicine:
    medicine_name: str
    generic_name: str = ""
    brand_name: str = ""
    sponsor: str = ""
    pip_number: str = ""
    decision_number: str = ""
    decision_date: str = ""
    decision_type: str = ""
    status: str = ""
    therapeutic_area: str = ""
    condition_indication: str = ""
    owner: str = "USER_1"

@dataclass
class Job:
    medicine_name: str
    pip_number: str = ""
    owner: str = "USER_1"
    status: str = "PENDING"
    error: Optional[str] = None
