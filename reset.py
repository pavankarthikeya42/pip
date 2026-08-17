import sqlite3
with sqlite3.connect('validation.db') as c:
    c.execute("UPDATE jobs SET status='PENDING'")
    print(c.execute("SELECT status FROM jobs").fetchall())
