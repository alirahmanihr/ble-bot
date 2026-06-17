import aiosqlite
import json
from pathlib import Path
from datetime import datetime

try:
    import jdatetime
except ImportError:
    jdatetime = None

DB_PATH = Path(__file__).parent / "hamrakar.db"

# =========================================================
# CONSTANTS - کاملاً فارسی و کامل
# =========================================================
INDUSTRIES = [
    "فناوری اطلاعات و نرم‌افزار",
    "صنعت و تولید",
    "ساختمان و عمران",
    "بازرگانی و فروش",
    "آموزش و پژوهش",
    "پزشکی و سلامت",
    "مالی و بانکی",
    "حمل و نقل و لجستیک",
    "خدمات و گردشگری",
    "کشاورزی",
    "رسانه و تبلیغات",
    "انرژی و نفت",
    "حقوقی و قراردادها",
    "تولید محتوا",
    "منابع انسانی",
]

CATEGORIES = [
    "برنامه‌نویسی و توسعه",
    "طراحی و گرافیک",
    "مدیریت و منابع انسانی",
    "بازاریابی و فروش",
    "مالی و حسابداری",
    "مهندسی و فنی",
    "آموزش و تدریس",
    "پشتیبانی و خدمات",
    "پزشکی و پیراپزشکی",
    "حقوقی و امور قراردادها",
    "حمل و نقل",
    "تولید و صنعت",
    "فروش و بازرگانی",
    "مدیریت پروژه",
    "امور اداری و دفتری",
    "رسانه و تولید محتوا",
    "امنیت و نظامی",
    "انرژی و نفت و گاز",
    "گردشگری و هتلداری",
    "سایر موارد",
]

PROVINCES = [
    "تهران", "اصفهان", "مشهد (خراسان رضوی)", "شیراز (فارس)", "تبریز (آذربایجان شرقی)",
    "اهواز (خوزستان)", "کرج (البرز)", "قم", "یزد", "رشت (گیلان)",
    "کرمان", "ارومیه (آذربایجان غربی)", "زاهدان (سیستان و بلوچستان)", "بندرعباس (هرمزگان)",
    "اردبیل", "اراک (مرکزی)", "ساری (مازندران)", "همدان", "سنندج (کردستان)",
    "قزوین", "گرگان (گلستان)", "بوشهر", "خرم‌آباد (لرستان)", "شهرکرد (چهارمحال)",
    "ایلام", "بیرجند (خراسان جنوبی)", "بجنورد (خراسان شمالی)", "زنجان",
    "سمنان", "دزفول", "کاشان", "آمل", "لنگرود", "مراغه", "ساوه",
]

EMP_TYPES = ["تمام وقت", "پاره وقت", "دورکاری", "پروژه‌ای", "کارآموزی"]
GENDERS = ["مرد", "زن", "فرقی نمی‌کند"]
EXPERIENCES = ["کمتر از 1 سال", "1 تا 3 سال", "3 تا 5 سال", "5 تا 10 سال", "بیشتر از 10 سال"]
RELOCATE = ["بله", "خیر", "بستگی دارد"]


# =========================================================
# HELPERS
# =========================================================
def fmt_salary(value):
    if not value:
        return "توافقی"
    try:
        return f"{int(value):,} تومان"
    except:
        return str(value)


def shamsi_datetime():
    if jdatetime:
        try:
            return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M")
        except:
            pass
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# =========================================================
# INIT DATABASE
# =========================================================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.execute("PRAGMA journal_mode=WAL")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            role TEXT,
            reg_date TEXT DEFAULT (datetime('now')),

            emp_name TEXT,
            emp_company TEXT,
            emp_industry TEXT,
            emp_phone TEXT,
            emp_position TEXT,
            emp_address TEXT,
            emp_email TEXT,
            emp_website TEXT,
            emp_gender TEXT,
            emp_age TEXT,

            js_name TEXT,
            js_phone TEXT,
            js_province TEXT,
            js_job_title TEXT,
            js_experience TEXT,
            js_salary INTEGER DEFAULT 0,
            js_dob TEXT,
            js_gender TEXT,
            js_relocate TEXT,
            js_cities TEXT,
            js_categories TEXT,
            js_skills TEXT,
            js_langs TEXT,
            js_rating REAL DEFAULT 5.0,

            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_cid INTEGER,
            title TEXT,
            emp_type TEXT,
            location TEXT,
            salary INTEGER DEFAULT 0,
            category TEXT,
            gender_req TEXT,
            age_req TEXT,
            status TEXT DEFAULT 'pending',
            admin_approved INTEGER DEFAULT 0,
            reject_reason TEXT,
            post_date TEXT DEFAULT (datetime('now')),
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            app_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            seeker_cid INTEGER,
            employer_id INTEGER,
            resume_file TEXT DEFAULT '',
            resume_text TEXT DEFAULT '',
            status TEXT DEFAULT 'pending_admin',
            reject_reason TEXT,
            sent_date TEXT DEFAULT (datetime('now')),
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            uid INTEGER PRIMARY KEY,
            state TEXT DEFAULT 'IDLE',
            data TEXT DEFAULT '{}'
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS resume_requests (
            req_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            employer_id INTEGER,
            seeker_id INTEGER,
            seeker_name TEXT DEFAULT '',
            employer_company TEXT DEFAULT '',
            seeker_status TEXT DEFAULT 'pending',
            admin_status TEXT DEFAULT 'pending_admin',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)

        await db.commit()


# =========================================================
# USERS
# =========================================================
async def get_user(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,))
        return await cur.fetchone()


async def upsert_user(chat_id, **data):
    async with aiosqlite.connect(DB_PATH) as db:
        user = await get_user(chat_id)
        if user:
            keys = ",".join([f"{k}=?" for k in data])
            values = list(data.values()) + [chat_id]
            await db.execute(f"UPDATE users SET {keys} WHERE chat_id=?", values)
        else:
            cols = ",".join(["chat_id"] + list(data.keys()))
            vals = [chat_id] + list(data.values())
            qs = ",".join(["?"] * len(vals))
            await db.execute(f"INSERT INTO users ({cols}) VALUES ({qs})", vals)
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users ORDER BY created_at DESC")
        return await cur.fetchall()


# =========================================================
# JOBS
# =========================================================
async def create_job(emp_cid, title, emp_type, location, salary, category,
                     gender_req="", age_req=""):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        INSERT INTO jobs (emp_cid, title, emp_type, location, salary, category,
                          gender_req, age_req, status, admin_approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0)
        """, (emp_cid, title, emp_type, location, salary, category, gender_req, age_req))
        await db.commit()
        return cur.lastrowid


async def get_job(job_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        return await cur.fetchone()


async def get_jobs(category=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT j.*, u.emp_name AS employer_name, u.emp_company AS employer_company
            FROM jobs j
            LEFT JOIN users u ON j.emp_cid = u.chat_id
            WHERE j.status='active' AND j.admin_approved=1
        """
        params = []
        if category:
            query += " AND j.category=?"
            params.append(category)
        cur = await db.execute(query, params)
        return await cur.fetchall()


async def get_all_jobs():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT j.*, u.emp_name AS employer_name, u.emp_company AS employer_company
            FROM jobs j
            LEFT JOIN users u ON j.emp_cid = u.chat_id
            ORDER BY j.created_at DESC
        """)
        return await cur.fetchall()


async def get_employer_jobs(emp_cid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM jobs WHERE emp_cid=?", (emp_cid,))
        return await cur.fetchall()


async def get_pending_jobs():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
        SELECT j.*, u.emp_company
        FROM jobs j
        LEFT JOIN users u ON j.emp_cid = u.chat_id
        WHERE j.admin_approved=0 AND j.status='pending'
        """)
        return await cur.fetchall()


async def approve_job(job_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE jobs SET admin_approved=1, status='active' WHERE job_id=?
        """, (job_id,))
        await db.commit()


async def reject_job(job_id, reason=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE jobs SET status='rejected', reject_reason=? WHERE job_id=?
        """, (reason, job_id))
        await db.commit()


# =========================================================
# APPLICATIONS
# =========================================================
async def create_application(job_id, seeker_cid, employer_id,
                             resume_file="", resume_text=""):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        INSERT INTO applications (job_id, seeker_cid, employer_id,
                                  resume_file, resume_text, status)
        VALUES (?, ?, ?, ?, ?, 'pending_admin')
        """, (job_id, seeker_cid, employer_id, resume_file, resume_text))
        await db.commit()
        return cur.lastrowid


async def get_pending_applications():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
        SELECT a.*, j.title AS job_title, u.js_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        LEFT JOIN users u ON a.seeker_cid = u.chat_id
        WHERE a.status = 'pending_admin'
        """)
        return await cur.fetchall()


async def approve_application(app_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE applications SET status='approved' WHERE app_id=?
        """, (app_id,))
        await db.commit()


async def reject_application(app_id, reason=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE applications SET status='rejected', reject_reason=? WHERE app_id=?
        """, (reason, app_id))
        await db.commit()


async def get_all_applications():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT a.*, j.title AS job_title, j.emp_cid AS employer_id,
                   u.emp_company AS employer_company, u2.js_name AS seeker_name
            FROM applications a
            JOIN jobs j ON a.job_id = j.job_id
            LEFT JOIN users u ON j.emp_cid = u.chat_id
            LEFT JOIN users u2 ON a.seeker_cid = u2.chat_id
            ORDER BY a.created_at DESC
        """)
        return await cur.fetchall()


async def get_seeker_applications(seeker_cid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
        SELECT a.*, j.title
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.seeker_cid=?
        ORDER BY a.created_at DESC
        """, (seeker_cid,))
        return await cur.fetchall()


# =========================================================
# RESUME REQUESTS
# =========================================================
async def create_resume_request(job_id, employer_id, seeker_id,
                                seeker_name="", employer_company=""):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        INSERT INTO resume_requests (job_id, employer_id, seeker_id,
                                     seeker_name, employer_company)
        VALUES (?, ?, ?, ?, ?)
        """, (job_id, employer_id, seeker_id, seeker_name, employer_company))
        await db.commit()
        return cur.lastrowid


async def get_pending_resume_requests():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
        SELECT r.*, u.emp_company
        FROM resume_requests r
        LEFT JOIN users u ON r.employer_id = u.chat_id
        WHERE r.admin_status = 'pending_admin'
        """)
        return await cur.fetchall()


async def approve_resume_request(req_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE resume_requests SET admin_status='approved' WHERE req_id=?
        """, (req_id,))
        await db.commit()


async def reject_resume_request(req_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        UPDATE resume_requests SET admin_status='rejected' WHERE req_id=?
        """, (req_id,))
        await db.commit()


# =========================================================
# STATE SYSTEM
# =========================================================
async def get_state(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT state, data FROM user_state WHERE uid=?", (uid,))
        row = await cur.fetchone()
        if not row:
            return "IDLE", {}
        return row["state"], json.loads(row["data"] or "{}")


async def set_state(uid, state, data=None):
    data = data or {}
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO user_state (uid, state, data)
        VALUES (?, ?, ?)
        ON CONFLICT(uid) DO UPDATE SET
        state=excluded.state, data=excluded.data
        """, (uid, state, json.dumps(data, ensure_ascii=False)))
        await db.commit()


async def clear_state(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM user_state WHERE uid=?", (uid,))
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

        cur = await db.execute("SELECT COUNT(*) FROM applications WHERE status='pending_admin'")
        pending_apps = (await cur.fetchone())[0]

        return {
            "total": total,
            "employers": employers,
            "seekers": seekers,
            "active": active,
            "pending": pending,
            "pending_apps": pending_apps
        }
