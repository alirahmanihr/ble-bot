<<<<<<< HEAD
# 📁 file: database.py
import aiosqlite
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "hamrakar.db"

PROVINCES = [
    "تهران", "البرز", "اصفهان", "فارس", "خراسان رضوی", "آذربایجان شرقی", "مازندران",
    "گیلان", "خوزستان", "قم", "کرمان", "هرمزگان", "یزد", "قزوین", "مرکزی", "بوشهر",
    "لرستان", "کرمانشاه", "کردستان", "همدان", "گلستان", "سیستان و بلوچستان",
    "اردبیل", "آذربایجان غربی", "زنجان", "چهارمحال و بختیاری", "خراسان جنوبی",
    "خراسان شمالی", "سمنان", "ایلام", "کهگیلویه و بویراحمد"
]

CATEGORIES = [
    "حسابداری و امور مالی", "آموزش و تدریس", "بازاریابی و فروش", "گردشگری و هتلداری",
    "تولید و عملیات", "تدارکات و لجستیک", "فنی و مهندسی", "کشاورزی و دامپروری",
    "فروشگاه‌داری و خرده فروشی", "پزشکی و پرستاری", "مدیریت اجرایی", "WEB و برنامه‌نویسی",
    "صنایع غذایی و آشپزی", "معماری و عمران", "بهداشت و ایمنی (HSE)", "واردات و صادرات",
    "مدیریت ارشد (CEO)", "منابع انسانی (HR)", "طراحی و هنر", "قوانین و قراردادها",
    "دولتی", "مهندسی پزشکی", "IT و شبکه", "خودرو", "تولید محتوا",
    "خدمات مشتریان", "پژوهش و توسعه", "رسانه و روابط عمومی"
]

INDUSTRIES = [
    "فناوری اطلاعات و نرم‌افزار", "تولید و صنعت", "ساختمان و عمران", "بازرگانی و واردات",
    "خدمات آموزشی", "خدمات درمانی و پزشکی", "بانکداری و بیمه", "بازاریابی و تبلیغات",
    "حمل و نقل و لجستیک", "کشاورزی و دامپروری", "گردشگری و هتلداری", "رسانه و نشر",
    "مخابرات و ارتباطات", "انرژی و نفت و گاز", "سایر صنایع"
=======
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
>>>>>>> b5b8e6b86e8330ffa1cb6ebdffd753fca440247f
]

EMP_TYPES = ["تمام وقت", "پاره وقت", "دورکاری", "پروژه‌ای", "فصلی"]
GENDERS = ["مرد", "زن", "بدون ترجیح"]
<<<<<<< HEAD
EXPERIENCES = ["کمتر از ۱ سال", "۱ تا ۳ سال", "۳ تا ۵ سال", "بیش از ۵ سال"]
RELOCATE = ["بله", "فقط شهر خودم", "بسته به شرایط"]

def fmt_salary(val):
    if not val or val in ("0", 0):
        return "توافقی"
    try:
        val = int(val)
        if val >= 1000000:
            return f"{val/1000000:g} میلیون تومان"
        return f"{val:,} تومان"
    except:
        return str(val)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                role TEXT,
                username TEXT,
                reg_date TEXT,
                rating REAL DEFAULT 5.0,
                rating_count INTEGER DEFAULT 0,
                
                emp_name TEXT,
                emp_company TEXT,
                emp_industry TEXT,
                emp_phone TEXT,
                emp_position TEXT,
                emp_address TEXT,
                emp_email TEXT,
                emp_website TEXT,
                emp_gender_pref TEXT,
                emp_age_pref TEXT,

                js_name TEXT,
                js_phone TEXT,
                js_province TEXT,
                js_job_title TEXT,
                js_categories TEXT,
                js_experience TEXT,
                js_salary INTEGER,
                js_dob TEXT,
                js_gender TEXT,
                js_relocate TEXT,
                js_cities TEXT,
                js_skills TEXT,
                js_languages TEXT,
                js_resume_text TEXT,
                js_resume_file TEXT,
                js_show_in_search INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employer_id INTEGER,
                employer_name TEXT,
                employer_company TEXT,
                title TEXT,
                type TEXT,
                priority TEXT,
                location TEXT,
                salary INTEGER,
                category TEXT,
                gender_req TEXT,
                age_req TEXT,
                status TEXT DEFAULT 'pending_admin',
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                app_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                job_title TEXT,
                employer_id INTEGER,
                employer_company TEXT,
                seeker_id INTEGER,
                seeker_name TEXT,
                resume_file TEXT,
                resume_text TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS resume_requests (
                req_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employer_id INTEGER,
                employer_company TEXT,
                job_id INTEGER,
                job_title TEXT,
                seeker_id INTEGER,
                seeker_name TEXT,
                seeker_status TEXT DEFAULT 'pending_seeker',
                admin_status TEXT DEFAULT 'pending_admin',
                created_at TEXT
            )
        """)
        await db.commit()

async def get_user(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,)) as cur:
            return await cur.fetchone()

async def upsert_user(chat_id, **kwargs):
    async with aiosqlite.connect(DB_PATH) as db:
        user = await get_user(chat_id)
        if not user:
            cols = ["chat_id"] + list(kwargs.keys())
            vals = [chat_id] + list(kwargs.values())
            query = f"INSERT INTO users ({', '.join(cols)}) VALUES ({', '.join(['?']*len(vals))})"
            await db.execute(query, vals)
        else:
            updates = []
            vals = []
            for k, v in kwargs.items():
                updates.append(f"{k}=?")
                vals.append(v)
            vals.append(chat_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE chat_id=?"
            await db.execute(query, vals)
        await db.commit()

async def add_job(employer_id, employer_name, employer_company, title, jtype, location, salary, category, priority, gender_req, age_req, created_at):
    async with aiosqlite.connect(DB_PATH) as db:
        q = """
            INSERT INTO jobs (employer_id, employer_name, employer_company, title, type, location, salary, category, priority, gender_req, age_req, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        async with db.execute(q, (employer_id, employer_name, employer_company, title, jtype, location, salary, category, json.dumps(priority), gender_req, age_req, created_at)) as cur:
            row_id = cur.lastrowid
        await db.commit()
        return row_id

async def get_job(job_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)) as cur:
            res = await cur.fetchone()
            if res:
                res = dict(res)
                try: res["priority"] = json.loads(res["priority"])
                except: res["priority"] = []
            return res

async def get_active_jobs_by_category_and_province(category, province):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM jobs WHERE status='active' AND category=? AND location LIKE ?"
        async with db.execute(q, (category, f"%{province}%")) as cur:
            rows = await cur.fetchall()
            res = []
            for r in rows:
                rd = dict(r)
                try: rd["priority"] = json.loads(rd["priority"])
                except: rd["priority"] = []
                res.append(rd)
            return res

async def get_jobs_by_employer(employer_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE employer_id=?", (employer_id,)) as cur:
            rows = await cur.fetchall()
            res = []
            for r in rows:
                rd = dict(r)
                try: rd["priority"] = json.loads(rd["priority"])
                except: rd["priority"] = []
                res.append(rd)
            return res

async def get_pending_jobs():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE status='pending_admin'") as cur:
            rows = await cur.fetchall()
            res = []
            for r in rows:
                rd = dict(r)
                try: rd["priority"] = json.loads(rd["priority"])
                except: rd["priority"] = []
                res.append(rd)
            return res

async def update_job_status(job_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE jobs SET status=? WHERE job_id=?", (status, job_id))
        await db.commit()

async def search_seekers_count(categories, province):
    async with aiosqlite.connect(DB_PATH) as db:
        q = "SELECT COUNT(*) FROM users WHERE role='job_seeker' AND js_show_in_search=1 AND js_province=?"
        params = [province]
        async with db.execute(q, params) as cur:
            return (await cur.fetchone())[0]

async def add_application(job_id, job_title, employer_id, employer_company, seeker_id, seeker_name, resume_file, resume_text, created_at):
    async with aiosqlite.connect(DB_PATH) as db:
        q = """
            INSERT INTO applications (job_id, job_title, employer_id, employer_company, seeker_id, seeker_name, resume_file, resume_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        async with db.execute(q, (job_id, job_title, employer_id, employer_company, seeker_id, seeker_name, resume_file, resume_text, created_at)) as cur:
            row_id = cur.lastrowid
        await db.commit()
        return row_id

async def get_application(app_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM applications WHERE app_id=?", (app_id,)) as cur:
            return await cur.fetchone()

async def update_application_status(app_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE applications SET status=? WHERE app_id=?", (status, app_id))
        await db.commit()

async def add_resume_request(employer_id, employer_company, job_id, job_title, seeker_id, seeker_name, created_at):
    async with aiosqlite.connect(DB_PATH) as db:
        q = """
            INSERT INTO resume_requests (employer_id, employer_company, job_id, job_title, seeker_id, seeker_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        async with db.execute(q, (employer_id, employer_company, job_id, job_title, seeker_id, seeker_name, created_at)) as cur:
            row_id = cur.lastrowid
        await db.commit()
        return row_id

async def get_resume_request(req_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM resume_requests WHERE req_id=?", (req_id,)) as cur:
            return await cur.fetchone()

async def update_resume_request_seeker(req_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE resume_requests SET seeker_status=? WHERE req_id=?", (status, req_id))
        await db.commit()

async def update_resume_request_admin(req_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE resume_requests SET admin_status=? WHERE req_id=?", (status, req_id))
        await db.commit()

async def get_pending_resume_requests():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT r.*, j.title as job_title, u_js.js_name, u_emp.emp_company 
            FROM resume_requests r
            JOIN jobs j ON r.job_id = j.job_id
            JOIN users u_js ON r.seeker_id = u_js.chat_id
            JOIN users u_emp ON r.employer_id = u_emp.chat_id
            WHERE r.seeker_status='agreed' AND r.admin_status='pending_admin'
        """
        async with db.execute(query) as cur:
            return await cur.fetchall()

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE role='employer'") as c1:
            emp_count = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE role='job_seeker'") as c2:
            js_count = (await c2.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM jobs WHERE status='active'") as c3:
            active_jobs = (await c3.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM applications WHERE status='approved'") as c4:
            approved_apps = (await c4.fetchone())[0]
        return {
            "total": emp_count + js_count,
            "employers": emp_count,
            "seekers": js_count,
            "active": active_jobs,
            "pending": 0,
            "pending_apps": approved_apps
        }
=======
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
>>>>>>> b5b8e6b86e8330ffa1cb6ebdffd753fca440247f
