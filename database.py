# database.py
import sqlite3, json
from threading import Lock

DB_FILE = "hamrakar.db"
_lock = Lock()

def _c():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _lock, _c() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, role TEXT, name TEXT, province TEXT, city TEXT, company_name TEXT, phone TEXT, email TEXT, address TEXT, resume_experiences TEXT, resume_education TEXT, resume_skills TEXT, state TEXT DEFAULT 'START', state_data TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS jobs (job_id INTEGER PRIMARY KEY AUTOINCREMENT, emp_cid INTEGER, title TEXT, category TEXT, province TEXT, city TEXT, salary TEXT, description TEXT, phone TEXT, email TEXT, address TEXT, status TEXT DEFAULT 'active')")
        conn.execute("CREATE TABLE IF NOT EXISTS applications (app_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER, seeker_cid INTEGER, mode TEXT, custom_exp TEXT, custom_edu TEXT)")
        conn.commit()

def upsert_user(cid, **kw):
    with _lock, _c() as conn:
        if not conn.execute("SELECT chat_id FROM users WHERE chat_id=?", (cid,)).fetchone():
            conn.execute("INSERT INTO users (chat_id, state) VALUES (?, 'START')", (cid,))
        if kw:
            sets = ", ".join([f"{k}=?" for k in kw.keys()])
            conn.execute(f"UPDATE users SET {sets} WHERE chat_id=?", list(kw.values()) + [cid])
        conn.commit()

def get_user(cid):
    with _lock, _c() as conn:
        res = conn.execute("SELECT * FROM users WHERE chat_id=?", (cid,)).fetchone()
        return dict(res) if res else None

def set_state(cid, state, data=None):
    upsert_user(cid, state=state, state_data=json.dumps(data) if data else None)

def get_state(cid):
    u = get_user(cid)
    return (u['state'], json.loads(u['state_data'])) if u and u['state_data'] else (u['state'] if u else 'START', None)

init_db()