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
]

EMP_TYPES = ["تمام وقت", "پاره وقت", "دورکاری", "پروژه‌ای", "فصلی"]
GENDERS = ["مرد", "زن", "بدون ترجیح"]
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