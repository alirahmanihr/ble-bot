import aiosqlite
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "hamrakar.db"


# =========================================================
# CONSTANTS (FULL COMPATIBLE WITH BOT)
# =========================================================
INDUSTRIES = [
    "فناوری اطلاعات", "صنعت", "ساختمان", "بازرگانی",
    "آموزش", "پزشکی", "مالی", "لجستیک", "خدمات"
]

CATEGORIES = [
    "IT", "HR", "Marketing", "Sales", "Engineering",
    "Accounting", "Design", "Content", "Management"
]

PROVINCES = [
    "تهران", "اصفهان", "مشهد", "شیراز", "تبریز",
    "اهواز", "کرج", "قم", "یزد", "رشت"
]

EMP_TYPES = ["تمام وقت", "پاره وقت", "دورکاری", "پروژه‌ای"]

GENDERS = ["مرد", "زن", "ترجیحی ندارد"]

EXPERIENCES = ["کمتر از 1 سال", "1-3 سال", "3-5 سال", "5+ سال"]

RELOCATE = ["بله", "خیر", "بستگی دارد"]


# =========================================================
# INIT DATABASE
# =========================================================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:

        # USERS
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            role TEXT,
            emp_name TEXT,
            emp_company TEXT,
            emp_industry TEXT,
            emp_phone TEXT,
            emp_position TEXT,

            js_name TEXT,
            js_phone TEXT,
            js_province TEXT,
            js_job_title TEXT,
            js_experience TEXT,
            js_salary INTEGER,

            rating REAL DEFAULT 5.0,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # JOBS
        await db.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_cid INTEGER,
            title TEXT,
            emp_type TEXT,
            location TEXT,
            salary INTEGER,
            category TEXT,
            status TEXT DEFAULT 'pending',
            admin_approved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # APPLICATIONS
        await db.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            app_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            seeker_cid INTEGER,
            employer_id INTEGER,
            resume_file TEXT,
            resume_text TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        # STATE MACHINE STORAGE
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            uid INTEGER PRIMARY KEY,
            state TEXT,
            data TEXT
        )
        """)

        await db.commit()


# =========================================================
# USERS
# =========================================================
async def get_user(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE chat_id=?",
            (chat_id,)
        )
        return await cur.fetchone()


async def upsert_user(chat_id, **data):
    async with aiosqlite.connect(DB_PATH) as db:
        user = await get_user(chat_id)

        if user:
            keys = ",".join([f"{k}=?" for k in data])
            values = list(data.values()) + [chat_id]
            await db.execute(
                f"UPDATE users SET {keys} WHERE chat_id=?",
                values
            )
        else:
            cols = ",".join(["chat_id"] + list(data.keys()))
            vals = [chat_id] + list(data.values())
            qs = ",".join(["?"] * len(vals))
            await db.execute(
                f"INSERT INTO users ({cols}) VALUES ({qs})",
                vals
            )

        await db.commit()


# =========================================================
# JOBS
# =========================================================
async def create_job(emp_cid, title, emp_type, location, salary, category):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        INSERT INTO jobs
        (emp_cid, title, emp_type, location, salary, category, status, admin_approved)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', 0)
        """, (emp_cid, title, emp_type, location, salary, category))

        await db.commit()
        return cur.lastrowid


async def get_job(job_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM jobs WHERE job_id=?",
            (job_id,)
        )
        return await cur.fetchone()


async def get_jobs(category=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if category:
            cur = await db.execute("""
            SELECT * FROM jobs
            WHERE category=? AND status='active' AND admin_approved=1
            """, (category,))
        else:
            cur = await db.execute("""
            SELECT * FROM jobs
            WHERE status='active' AND admin_approved=1
            """)

        return await cur.fetchall()


async def get_employer_jobs(emp_cid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM jobs WHERE emp_cid=?",
            (emp_cid,)
        )
        return await cur.fetchall()


async def get_pending_jobs():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM jobs WHERE admin_approved=0"
        )
        return await cur.fetchall()


async def approve_job(job_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE jobs
        SET admin_approved=1, status='active'
        WHERE job_id=?
        """, (job_id,))
        await db.commit()


async def reject_job(job_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE jobs
        SET status='rejected'
        WHERE job_id=?
        """, (job_id,))
        await db.commit()


# =========================================================
# APPLICATIONS
# =========================================================
async def create_application(job_id, seeker_cid, employer_id, resume_file="", resume_text=""):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        INSERT INTO applications
        (job_id, seeker_cid, employer_id, resume_file, resume_text, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
        """, (job_id, seeker_cid, employer_id, resume_file, resume_text))

        await db.commit()
        return cur.lastrowid


async def get_pending_applications():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
        SELECT a.*, j.title
        FROM applications a
        JOIN jobs j ON a.job_id=j.job_id
        WHERE a.status='pending'
        """)
        return await cur.fetchall()


async def approve_application(app_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE applications
        SET status='approved'
        WHERE app_id=?
        """, (app_id,))
        await db.commit()


async def reject_application(app_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE applications
        SET status='rejected'
        WHERE app_id=?
        """, (app_id,))
        await db.commit()


# =========================================================
# STATE SYSTEM
# =========================================================
async def get_state(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT state, data FROM user_state WHERE uid=?",
            (uid,)
        )
        row = await cur.fetchone()
        if not row:
            return "IDLE", {}
        import json
        return row["state"], json.loads(row["data"] or "{}")


async def set_state(uid, state, data=None):
    import json
    data = data or {}
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO user_state (uid, state, data)
        VALUES (?, ?, ?)
        ON CONFLICT(uid) DO UPDATE SET
        state=excluded.state,
        data=excluded.data
        """, (uid, state, json.dumps(data, ensure_ascii=False)))
        await db.commit()


async def clear_state(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_state WHERE uid=?",
            (uid,)
        )
        await db.commit()


# =========================================================
# STATS
# =========================================================
async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM users WHERE role='employer'")
        employers = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM users WHERE role='job_seeker'")
        seekers = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM jobs WHERE status='active' AND admin_approved=1")
        active = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM jobs WHERE admin_approved=0")
        pending = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM applications WHERE status='pending'")
        pending_apps = (await cur.fetchone())[0]

        return {
            "total": total,
            "employers": employers,
            "seekers": seekers,
            "active": active,
            "pending": pending,
            "pending_apps": pending_apps
        }
def fmt_salary(value):
    if not value:
        return "توافقی"
    try:
        return f"{int(value):,} تومان"
    except:
        return str(value)