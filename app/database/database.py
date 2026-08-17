import json
import sqlite3
from pathlib import Path
from typing import Iterable
from ..config import ROOT

DB_PATH = ROOT / "validation.db"


class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.init()

    def connect(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def init(self):
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS medicines(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              medicine_name TEXT NOT NULL,
              generic_name TEXT, brand_name TEXT, sponsor TEXT,
              pip_number TEXT, decision_number TEXT, decision_date TEXT,
              decision_type TEXT, status TEXT, therapeutic_area TEXT,
              condition_indication TEXT, owner TEXT,
              metadata_json TEXT,
              source_file TEXT,
              source_row INTEGER,
              UNIQUE(medicine_name,pip_number)
            );
            CREATE TABLE IF NOT EXISTS jobs(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              medicine_id INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'PENDING',
              error TEXT, retry_count INTEGER DEFAULT 0,
              updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(medicine_id) REFERENCES medicines(id)
            );
            CREATE TABLE IF NOT EXISTS validation_results(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              medicine_id INTEGER NOT NULL,
              overall_status TEXT, result_json TEXT NOT NULL,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(medicine_id) REFERENCES medicines(id)
            );
            CREATE TABLE IF NOT EXISTS validation_items(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              medicine_id INTEGER NOT NULL,
              category TEXT, item_key TEXT, status TEXT,
              pdf_value TEXT, ui_value TEXT, excel_value TEXT, reason TEXT,
              source_page TEXT
            );
            CREATE TABLE IF NOT EXISTS errors(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              medicine_id INTEGER, stage TEXT, message TEXT,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            ''')
            # Safe migration for databases created by the earlier MVP.
            existing = {r[1] for r in c.execute("PRAGMA table_info(medicines)").fetchall()}
            for name, sql in {
                "metadata_json": "ALTER TABLE medicines ADD COLUMN metadata_json TEXT",
                "source_file": "ALTER TABLE medicines ADD COLUMN source_file TEXT",
                "source_row": "ALTER TABLE medicines ADD COLUMN source_row INTEGER",
            }.items():
                if name not in existing:
                    c.execute(sql)
            c.commit()

    def upsert_medicines(self, rows: Iterable[dict]):
        with self.connect() as c:
            for r in rows:
                metadata = {k: v for k, v in r.items() if k not in {"owner", "source_file", "source_row"}}
                c.execute('''INSERT INTO medicines
                (medicine_name,generic_name,brand_name,sponsor,pip_number,decision_number,
                 decision_date,decision_type,status,therapeutic_area,condition_indication,owner,
                 metadata_json,source_file,source_row)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(medicine_name,pip_number) DO UPDATE SET
                generic_name=excluded.generic_name,brand_name=excluded.brand_name,
                sponsor=excluded.sponsor,decision_number=excluded.decision_number,
                decision_date=excluded.decision_date,decision_type=excluded.decision_type,
                status=excluded.status,therapeutic_area=excluded.therapeutic_area,
                condition_indication=excluded.condition_indication,owner=excluded.owner,
                metadata_json=excluded.metadata_json,source_file=excluded.source_file,
                source_row=excluded.source_row''',
                (
                    r.get("medicine_name", ""), r.get("generic_name", ""),
                    r.get("brand_name", ""), r.get("sponsor", ""), r.get("pip_number", ""),
                    r.get("decision_number", ""), r.get("decision_date", ""),
                    r.get("decision_type", ""), r.get("status", ""),
                    r.get("therapeutic_areas", ""), r.get("condition_indication", ""),
                    r.get("owner", "USER_1"), json.dumps(metadata, ensure_ascii=False),
                    r.get("source_file", ""), int(r.get("source_row") or 0),
                ))
            c.commit()

    def create_jobs(self, owner=None):
        with self.connect() as c:
            if owner:
                c.execute("""INSERT INTO jobs(medicine_id)
                    SELECT id FROM medicines m
                    WHERE m.owner=? AND NOT EXISTS
                    (SELECT 1 FROM jobs j WHERE j.medicine_id=m.id)""", (owner,))
            else:
                c.execute("""INSERT INTO jobs(medicine_id)
                    SELECT id FROM medicines m
                    WHERE NOT EXISTS
                    (SELECT 1 FROM jobs j WHERE j.medicine_id=m.id)""")
            c.commit()

    def get_medicine(self, medicine_name: str, owner: str | None = None):
        with self.connect() as c:
            q = "SELECT * FROM medicines WHERE lower(medicine_name)=lower(?)"
            args = [medicine_name]
            if owner:
                q += " AND owner=?"
                args.append(owner)
            q += " ORDER BY id LIMIT 1"
            return c.execute(q, args).fetchone()

    def next_job(self, owner=None):
        with self.connect() as c:
            q = '''SELECT j.*,m.* FROM jobs j JOIN medicines m ON m.id=j.medicine_id
                   WHERE j.status IN ('PENDING','ERROR','REVIEW_REQUIRED',
                                      'SEARCHING','PIP_FOUND','PDF_RETRIEVED',
                                      'PDF_EXTRACTED','UI_EXTRACTED')'''
            args=[]
            if owner:
                q += ' AND m.owner=?'; args.append(owner)
            q += ' ORDER BY j.id LIMIT 1'
            return c.execute(q,args).fetchone()

    def set_status(self, job_id, status, error=None):
        with self.connect() as c:
            c.execute("UPDATE jobs SET status=?,error=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(status,error,job_id)); c.commit()

    def increment_retry(self, job_id, reset=False):
        with self.connect() as c:
            if reset:
                c.execute("UPDATE jobs SET retry_count=0 WHERE id=?", (job_id,))
            else:
                c.execute("UPDATE jobs SET retry_count=COALESCE(retry_count,0)+1 WHERE id=?", (job_id,))
            c.commit()

    def save_result(self, medicine_id, overall_status, result_json):
        with self.connect() as c:
            c.execute("INSERT INTO validation_results(medicine_id,overall_status,result_json) VALUES(?,?,?);",(medicine_id,overall_status,result_json)); c.commit()
