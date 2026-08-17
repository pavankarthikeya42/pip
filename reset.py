import sqlite3
with sqlite3.connect('validation.db') as c:
    c.execute("UPDATE jobs SET status='PENDING', retry_count=0")
    print(c.execute("SELECT id, status, retry_count FROM jobs").fetchall())
