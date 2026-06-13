"""
دیتابیس کامل ربات همراکار — بله
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager

try:
    import jdatetime
    def shamsi_now():
        return jdatetime.datetime.now().strftime("%Y/%m/%d")
    def shamsi_datetime():
        return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M")
except:
    def shamsi_now():
        return datetime.now().strftime("%Y/%m/%d")
    def shamsi_datetime():
        return datetime.now().strftime("%Y/%m/%d %H:%M")

DB_PATH = Path(__file__).parent / "hamrakar.db"

# ── ثابت‌ها ────────────────────────────────────────
INDUSTRIES = [
    "فناوری اطلاعات و نرم‌افزار", "تولید و صنعت", "ساختمان و عمران",
    "بازرگانی و واردات", "خدمات آموزشی", "خدمات درمانی و پزشکی",
    "بانکداری و بیمه", "بازاریابی و تبلیغات", "حمل و نقل و لجستیک",
    "کشاورزی و دامپروری", "گردشگری و هتلداری", "رسانه و نشر",
    "مخابرات و ارتباطات", "انرژی و نفت و گاز", "سایر صنایع",
]

CATEGORIES = [
    "حسابداری و امور مالی", "آموزش و تدریس", "بازاریابی و فروش",
    "گردشگری و هتلداری", "تولید و عملیات", "تدارکات و لجستیک",
    "فنی و مهندسی", "کشاورزی و دامپروری", "فروشگاه‌داری و خرده فروشی",
    "پزشکی و پرستاری", "مدیریت اجرایی", "WEB و برنامه‌نویسی",
    "صنایع غذایی و آشپزی", "معماری و عمران", "بهداشت و ایمنی (HSE)",
    "واردات و صادرات", "مدیریت ارشد (CEO)", "منابع انسانی (HR)",
    "طراحی و هنر", "قوانین و قراردادها (حقوقی)", "دولتی",
    "مهندسی پزشکی", "IT و شبکه", "خودرو", "تولید محتوا",
    "خدمات مشتریان و پشتیبانی", "پژوهش و توسعه (R&D)", "رسانه و روابط عمومی",
]

PROVINCES = [
    "آذربایجان شرقی", "آذربایجان غربی", "اردبیل", "اصفهان", "البرز",
    "ایلام", "بوشهر", "تهران", "چهارمحال و بختیاری", "خراسان جنوبی",
    "خراسان رضوی", "خراسان شمالی", "خوزستان", "زنجان", "سمنان",
    "سیستان و بلوچستان", "فارس", "قزوین", "قم", "کردستان",
    "کرمان", "کرمانشاه", "کهگیلویه و بویراحمد", "گلستان", "گیلان",
    "لرستان", "مازندران", "مرکزی", "هرمزگان", "همدان", "یزد",
]

EMP_TYPES = ["تمام وقت", "پاره وقت", "دورکاری", "پروژه‌ای", "فصلی"]
GENDERS = ["مرد", "زن", "بدون ترجیح"]
EXPERIENCES = ["بدون سابقه", "کمتر از ۱ سال", "۱ تا ۳ سال", "۳ تا ۵ سال", "بیش از ۵ سال"]
RELOCATE = ["بله", "فقط شهر خودم", "بسته به شرایط"]

@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except:
        con.rollback()
        raise
    finally:
        con.close()

def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            role TEXT CHECK(role IN ('employer','job_seeker')),
            
            -- کارفرما
            emp_name TEXT, emp_company TEXT, emp_industry TEXT,
            emp_phone TEXT, emp_position TEXT,
            emp_address TEXT, emp_email TEXT, emp_website TEXT,
            emp_gender_need TEXT, emp_age_min INTEGER, emp_age_max INTEGER,
            
            -- کارجو
            js_name TEXT, js_phone TEXT, js_province TEXT,
            js_job_title TEXT, js_experience TEXT,
            js_salary_expect INTEGER, js_dob TEXT, js_age INTEGER,
            js_gender TEXT, js_relocate TEXT,
            js_categories TEXT DEFAULT '[]',
            js_cities TEXT DEFAULT '[]',
            js_skills TEXT DEFAULT '[]',
            js_languages TEXT DEFAULT '[]',
            js_resume_text TEXT, js_resume_file_id TEXT,
            js_rating REAL DEFAULT 0.0,
            js_private INTEGER DEFAULT 0,
            
            -- مشترک
            rating REAL DEFAULT 0.0,
            reg_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_cid INTEGER NOT NULL,
            title TEXT NOT NULL,
            emp_type TEXT,
            location TEXT,
            salary INTEGER,
            priority_urgent INTEGER DEFAULT 0,
            priority_confidential INTEGER DEFAULT 0,
            category TEXT,
            gender_need TEXT,
            age_min INTEGER, age_max INTEGER,
            status TEXT DEFAULT 'pending',
            admin_approved INTEGER DEFAULT 0,
            post_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(emp_cid) REFERENCES users(chat_id)
        );

        CREATE TABLE IF NOT EXISTS applications (
            app_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            seeker_cid INTEGER NOT NULL,
            status TEXT DEFAULT 'pending_admin',
            sent_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_id, seeker_cid),
            FOREIGN KEY(job_id) REFERENCES jobs(job_id),
            FOREIGN KEY(seeker_cid) REFERENCES users(chat_id)
        );

        CREATE TABLE IF NOT EXISTS resume_requests (
            req_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            emp_cid INTEGER NOT NULL,
            seeker_cid INTEGER NOT NULL,
            status TEXT DEFAULT 'pending_seeker',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_id, emp_cid, seeker_cid),
            FOREIGN KEY(job_id) REFERENCES jobs(job_id),
            FOREIGN KEY(emp_cid) REFERENCES users(chat_id),
            FOREIGN KEY(seeker_cid) REFERENCES users(chat_id)
        );

        CREATE TABLE IF NOT EXISTS ratings (
            rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_cid INTEGER NOT NULL,
            to_cid INTEGER NOT NULL,
            job_id INTEGER,
            score REAL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_cid, to_cid, job_id),
            FOREIGN KEY(from_cid) REFERENCES users(chat_id),
            FOREIGN KEY(to_cid) REFERENCES users(chat_id)
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_cat ON jobs(category);
        CREATE INDEX IF NOT EXISTS idx_jobs_st ON jobs(status, admin_approved);
        CREATE INDEX IF NOT EXISTS idx_apps_job ON applications(job_id);
        """)

def get_user(cid):
    with _conn() as c:
        return c.execute("SELECT * FROM users WHERE chat_id=?", (cid,)).fetchone()

def upsert_user(cid, **fields):
    if not fields: return
    existing = get_user(cid)
    if existing:
        sets = ", ".join(f"{k}=?" for k in fields)
        with _conn() as c:
            c.execute(f"UPDATE users SET {sets} WHERE chat_id=?",
                      list(fields.values()) + [cid])
    else:
        fields["chat_id"] = cid
        fields.setdefault("reg_date", shamsi_now())
        cols = ", ".join(fields.keys())
        phs = ", ".join("?" * len(fields))
        with _conn() as c:
            c.execute(f"INSERT INTO users ({cols}) VALUES ({phs})",
                      list(fields.values()))

def create_job(emp_cid, **fields):
    fields.update(emp_cid=emp_cid, post_date=shamsi_now(),
                  status="pending", admin_approved=0)
    cols = ", ".join(fields.keys())
    phs = ", ".join("?" * len(fields))
    with _conn() as c:
        cur = c.execute(f"INSERT INTO jobs ({cols}) VALUES ({phs})",
                        list(fields.values()))
        return cur.lastrowid

def get_job(job_id):
    with _conn() as c:
        return c.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()

def get_employer_jobs(emp_cid, status=None):
    sql = "SELECT * FROM jobs WHERE emp_cid=?"
    params = [emp_cid]
    if status:
        sql += " AND status=?"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    with _conn() as c:
        return c.execute(sql, params).fetchall()

def get_pending_jobs():
    with _conn() as c:
        return c.execute(
            "SELECT j.*, u.emp_name, u.emp_company FROM jobs j "
            "JOIN users u ON j.emp_cid=u.chat_id "
            "WHERE j.status='pending' AND j.admin_approved=0 "
            "ORDER BY j.created_at"
        ).fetchall()

def approve_job(job_id):
    with _conn() as c:
        c.execute("UPDATE jobs SET admin_approved=1, status='active' WHERE job_id=?",
                  (job_id,))

def reject_job(job_id):
    with _conn() as c:
        c.execute("UPDATE jobs SET status='rejected' WHERE job_id=?", (job_id,))

def search_jobs(category=None, province=None, emp_type=None, urgent=False):
    sql = "SELECT * FROM jobs WHERE status='active' AND admin_approved=1"
    params = []
    if category:
        sql += " AND category=?"
        params.append(category)
    if province:
        sql += " AND location LIKE ?"
        params.append(f"%{province}%")
    if emp_type:
        sql += " AND emp_type=?"
        params.append(emp_type)
    if urgent:
        sql += " AND priority_urgent=1"
    sql += " ORDER BY priority_urgent DESC, created_at DESC LIMIT 50"
    with _conn() as c:
        return c.execute(sql, params).fetchall()

def create_application(job_id, seeker_cid):
    with _conn() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO applications (job_id, seeker_cid, sent_date) "
            "VALUES (?,?,?)", (job_id, seeker_cid, shamsi_datetime()))
        return cur.lastrowid

def get_job_applications(job_id):
    with _conn() as c:
        return c.execute(
            "SELECT a.*, u.js_name, u.js_phone FROM applications a "
            "JOIN users u ON a.seeker_cid=u.chat_id "
            "WHERE a.job_id=?", (job_id,)
        ).fetchall()

def get_pending_applications():
    with _conn() as c:
        return c.execute(
            "SELECT a.*, u.js_name, u.js_phone, j.title FROM applications a "
            "JOIN users u ON a.seeker_cid=u.chat_id "
            "JOIN jobs j ON a.job_id=j.job_id "
            "WHERE a.status='pending_admin' ORDER BY a.created_at"
        ).fetchall()

def approve_application(app_id):
    with _conn() as c:
        c.execute("UPDATE applications SET status='approved' WHERE app_id=?", (app_id,))

def reject_application(app_id):
    with _conn() as c:
        c.execute("UPDATE applications SET status='rejected' WHERE app_id=?", (app_id,))

def create_resume_request(job_id, emp_cid, seeker_cid):
    with _conn() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO resume_requests (job_id, emp_cid, seeker_cid) "
            "VALUES (?,?,?)", (job_id, emp_cid, seeker_cid))
        return cur.lastrowid

def get_pending_resume_requests():
    with _conn() as c:
        return c.execute(
            "SELECT r.*, j.title, u.js_name FROM resume_requests r "
            "JOIN jobs j ON r.job_id=j.job_id "
            "JOIN users u ON r.seeker_cid=u.chat_id "
            "WHERE r.status='pending_seeker' ORDER BY r.created_at"
        ).fetchall()

def approve_resume_request(req_id):
    with _conn() as c:
        c.execute("UPDATE resume_requests SET status='approved' WHERE req_id=?", (req_id,))

def reject_resume_request(req_id):
    with _conn() as c:
        c.execute("UPDATE resume_requests SET status='rejected' WHERE req_id=?", (req_id,))

def set_rating(from_cid, to_cid, job_id, score):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO ratings (from_cid, to_cid, job_id, score) "
            "VALUES (?,?,?,?)", (from_cid, to_cid, job_id, score))
    update_avg_rating(to_cid)

def get_avg_rating(user_cid):
    with _conn() as c:
        row = c.execute("SELECT AVG(score) FROM ratings WHERE to_cid=?",
                        (user_cid,)).fetchone()
    return row[0] or 0.0

def update_avg_rating(user_cid):
    avg = get_avg_rating(user_cid)
    with _conn() as c:
        c.execute("UPDATE users SET rating=? WHERE chat_id=?", (avg, user_cid))

def get_stats():
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        employers = c.execute("SELECT COUNT(*) FROM users WHERE role='employer'").fetchone()[0]
        seekers = c.execute("SELECT COUNT(*) FROM users WHERE role='job_seeker'").fetchone()[0]
        active_jobs = c.execute("SELECT COUNT(*) FROM jobs WHERE status='active'").fetchone()[0]
        pending_jobs = c.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
        pending_apps = c.execute("SELECT COUNT(*) FROM applications WHERE status='pending_admin'").fetchone()[0]
    return {"total": total, "employers": employers, "seekers": seekers,
            "active": active_jobs, "pending": pending_jobs, "pending_apps": pending_apps}
