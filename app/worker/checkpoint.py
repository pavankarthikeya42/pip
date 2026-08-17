def checkpoint(db, job_id, status, error=None):
    db.set_status(job_id, status, error)
