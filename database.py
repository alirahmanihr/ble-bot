"""
دیتابیس همراکار - نسخه نهایی با پشتیبانی از اجازه ارسال به کارفرما
"""
import sqlite3, json, re
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

try:
    import jdatetime
    def shamsi_now(): return jdatetime.datetime.now().strftime("%Y/%m/%d")
    def shamsi_dt():  return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M")
except:
    def shamsi_now(): return datetime.now().strftime("%Y/%m/%d")
    def shamsi_dt():  return datetime.now().strftime("%Y/%m/%d %H:%M")

DB_PATH = Path(__file__).parent / "hamrakar.db"
_lock   = Lock()

# ══════════════════════════════════════════════════════════════════════════
# ثابت‌ها
# ══════════════════════════════════════════════════════════════════════════
INDUSTRIES = [
    "فناوری اطلاعات","تولید و صنعت","ساختمان و عمران","بازرگانی",
    "آموزش","خدمات درمانی","بانکداری و بیمه","بازاریابی",
    "حمل و نقل","کشاورزی","گردشگری","رسانه","مخابرات","انرژی","سایر"
]

CATEGORIES = [
    "حسابداری","آموزش","بازاریابی","گردشگری","تولید","تدارکات",
    "مهندسی","کشاورزی","فروش","پزشکی","مدیریت","برنامه‌نویسی",
    "غذایی","معماری","HSE","تجارت","CEO","HR","طراحی","حقوقی",
    "دولتی","مهندسی‌پزشکی","IT","خودرو","محتوا","مشتریان","R&D","روابط‌عمومی",
    "عمومی", "سایر"
]

PROVINCES = [
    "تهران","البرز","مازندران","گیلان","اردبیل","آذربایجان‌شرقی",
    "آذربایجان‌غربی","کردستان","کرمانشاه","خوزستان","ایلام","بوشهر",
    "هرمزگان","سیستان","خراسان‌رضوی","خراسان‌شمالی","خراسان‌جنوبی",
    "قم","سمنان","زنجان","مرکزی","اصفهان","لرستان","فارس",
    "کرمان","یزد","چهارمحال","کهگیلویه","گلستان","همدان","شیراز"
]

EMP_TYPES   = ["تمام‌وقت","پاره‌وقت","دورکاری","پروژه‌ای","فصلی"]
GENDERS     = ["مرد","زن","بدون‌ترجیح"]
EXPERIENCES = ["بدون سابقه","کمتر از ۱ سال","۱ تا ۳ سال","۳ تا ۵ سال","بیش از ۵ سال"]
EDUCATIONS  = ["زیر دیپلم","دیپلم","فوق‌دیپلم","لیسانس","فوق‌لیسانس","دکترا"]
RELOCATE    = ["بله","فقط شهر خودم","بسته به شرایط"]
SKILLS_LIST = [
    "Excel","Word","Python","Java","PHP","JavaScript","SQL","AutoCAD",
    "Photoshop","Illustrator","حسابداری","مذاکره","فروش",
    "بازاریابی دیجیتال","SEO","مدیریت پروژه","PMP","ICDL","زبان انگلیسی",
    "تحلیل داده","مدیریت تیم","رهبری","ارتباط موثر","حل مسئله",
    "عمومی", "سایر", "بدون مهارت"
]

# ══════════════════════════════════════════════════════════════════════════
# اتصال به دیتابیس
# ══════════════════════════════════════════════════════════════════════════
def _c():
    c = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=10000")
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA cache_size=10000")
    return c

def init_db():
    with _lock:
        c = _c()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id          INTEGER PRIMARY KEY,
            role             TEXT CHECK(role IN ('employer','job_seeker')),
            -- کارفرما
            emp_name         TEXT,
            emp_company      TEXT,
            emp_industry     TEXT,
            emp_phone        TEXT UNIQUE,
            emp_position     TEXT,
            emp_address      TEXT,
            emp_email        TEXT,
            emp_website      TEXT,
            emp_gender_need  TEXT,
            emp_age_min      INTEGER,
            emp_age_max      INTEGER,
            -- کارجو
            js_name          TEXT,
            js_phone         TEXT UNIQUE,
            js_province      TEXT,
            js_job_title     TEXT,
            js_experience    TEXT,
            js_education     TEXT,
            js_salary_min    INTEGER DEFAULT 0,
            js_salary_max    INTEGER DEFAULT 0,
            js_dob           TEXT,
            js_gender        TEXT,
            js_relocate      TEXT,
            js_cities        TEXT DEFAULT '[]',
            js_categories    TEXT DEFAULT '[]',
            js_skills        TEXT DEFAULT '[]',
            js_languages     TEXT DEFAULT '[]',
            js_about         TEXT,
            js_resume_file   TEXT,
            js_resume_type   TEXT,
            work_experience  TEXT DEFAULT '[]',
            allow_employer_notify INTEGER DEFAULT 0,  -- جدید: اجازه ارسال به کارفرما
            -- مشترک
            rating           REAL DEFAULT 0.0,
            rating_count     INTEGER DEFAULT 0,
            private_mode     INTEGER DEFAULT 0,
            is_banned        INTEGER DEFAULT 0,
            ban_reason       TEXT,
            reg_date         TEXT,
            last_active      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_states (
            chat_id     INTEGER PRIMARY KEY,
            state       TEXT DEFAULT 'IDLE',
            data        TEXT DEFAULT '{}',
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS jobs (
            job_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_cid          INTEGER NOT NULL,
            title            TEXT NOT NULL,
            emp_type         TEXT,
            province         TEXT,
            city             TEXT,
            salary_min       INTEGER DEFAULT 0,
            salary_max       INTEGER DEFAULT 0,
            category         TEXT NOT NULL,
            gender_need      TEXT,
            age_min          INTEGER,
            age_max          INTEGER,
            education_need   TEXT,
            experience_need  TEXT,
            description      TEXT,
            benefits         TEXT,
            status           TEXT DEFAULT 'pending'
                             CHECK(status IN ('pending','active','rejected','expired','closed')),
            admin_approved   INTEGER DEFAULT 0,
            approved_date    TEXT,
            expiry_date      TEXT,
            views            INTEGER DEFAULT 0,
            app_count        INTEGER DEFAULT 0,
            post_date        TEXT,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(emp_cid) REFERENCES users(chat_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS applications (
            app_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id        INTEGER NOT NULL,
            seeker_cid    INTEGER NOT NULL,
            cover_letter  TEXT,
            resume_file   TEXT,
            resume_type   TEXT CHECK(resume_type IN ('pdf','docx','photo','audio','voice')),
            file_size     INTEGER DEFAULT 0,
            status        TEXT DEFAULT 'pending_admin'
                          CHECK(status IN ('pending_admin','approved','rejected','seen')),
            admin_note    TEXT,
            sent_date     TEXT,
            seen_date     TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_id, seeker_cid),
            FOREIGN KEY(job_id)     REFERENCES jobs(job_id) ON DELETE CASCADE,
            FOREIGN KEY(seeker_cid) REFERENCES users(chat_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ratings (
            rating_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            from_cid    INTEGER NOT NULL,
            to_cid      INTEGER NOT NULL,
            job_id      INTEGER,
            score       INTEGER CHECK(score BETWEEN 1 AND 5),
            comment     TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_cid, to_cid, job_id)
        );

        CREATE TABLE IF NOT EXISTS bookmarks (
            bm_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_cid    INTEGER NOT NULL,
            job_id      INTEGER NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_cid, job_id),
            FOREIGN KEY(user_cid) REFERENCES users(chat_id) ON DELETE CASCADE,
            FOREIGN KEY(job_id)   REFERENCES jobs(job_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notifications (
            notif_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_cid    INTEGER NOT NULL,
            text        TEXT NOT NULL,
            is_read     INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_cid) REFERENCES users(chat_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS admin_logs (
            log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_cid   INTEGER NOT NULL,
            action      TEXT NOT NULL,
            target_id   INTEGER,
            note        TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activity_logs (
            log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_cid    INTEGER NOT NULL,
            action      TEXT NOT NULL,
            detail      TEXT,
            result      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_cid) REFERENCES users(chat_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS direct_messages (
            msg_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            from_cid    INTEGER NOT NULL,
            to_cid      INTEGER NOT NULL,
            job_id      INTEGER,
            text        TEXT NOT NULL,
            is_read     INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_cat     ON jobs(category, status);
        CREATE INDEX IF NOT EXISTS idx_jobs_prov    ON jobs(province, status);
        CREATE INDEX IF NOT EXISTS idx_jobs_emp     ON jobs(emp_cid);
        CREATE INDEX IF NOT EXISTS idx_jobs_expiry  ON jobs(expiry_date, status);
        CREATE INDEX IF NOT EXISTS idx_apps_job     ON applications(job_id);
        CREATE INDEX IF NOT EXISTS idx_apps_seeker  ON applications(seeker_cid);
        CREATE INDEX IF NOT EXISTS idx_apps_status  ON applications(status);
        CREATE INDEX IF NOT EXISTS idx_users_role   ON users(role);
        CREATE INDEX IF NOT EXISTS idx_states       ON user_states(chat_id);
        CREATE INDEX IF NOT EXISTS idx_notif_user   ON notifications(user_cid, is_read);
        CREATE INDEX IF NOT EXISTS idx_bookmarks    ON bookmarks(user_cid);
        CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_logs(user_cid);
        CREATE INDEX IF NOT EXISTS idx_dm_from      ON direct_messages(from_cid);
        CREATE INDEX IF NOT EXISTS idx_dm_to        ON direct_messages(to_cid);
        """)
        c.commit()
        c.close()

# ══════════════════════════════════════════════════════════════════════════
# State
# ══════════════════════════════════════════════════════════════════════════
def get_state(cid):
    with _lock:
        c = _c()
        row = c.execute("SELECT state, data FROM user_states WHERE chat_id=?", (cid,)).fetchone()
        c.close()
    if row:
        try:    return row[0], json.loads(row[1])
        except: return row[0], {}
    return "IDLE", {}

def set_state(cid, state, data=None):
    if data is None: data = {}
    with _lock:
        c = _c()
        c.execute(
            "INSERT OR REPLACE INTO user_states(chat_id,state,data,updated_at) "
            "VALUES(?,?,?,CURRENT_TIMESTAMP)",
            (cid, state, json.dumps(data, ensure_ascii=False))
        )
        c.commit(); c.close()

def update_data(cid, **kv):
    state, data = get_state(cid)
    data.update(kv)
    set_state(cid, state, data)

def clear_state(cid):
    with _lock:
        c = _c()
        c.execute("DELETE FROM user_states WHERE chat_id=?", (cid,))
        c.commit(); c.close()

# ══════════════════════════════════════════════════════════════════════════
# کاربران
# ══════════════════════════════════════════════════════════════════════════
def get_user(cid):
    with _lock:
        c = _c()
        row = c.execute("SELECT * FROM users WHERE chat_id=?", (cid,)).fetchone()
        c.close()
    return row

def get_user_by_phone(phone, role=None):
    if not phone:
        return None
    with _lock:
        c = _c()
        if role == "employer":
            row = c.execute("SELECT * FROM users WHERE emp_phone=? AND role='employer'", (phone,)).fetchone()
        elif role == "job_seeker":
            row = c.execute("SELECT * FROM users WHERE js_phone=? AND role='job_seeker'", (phone,)).fetchone()
        else:
            row = c.execute("SELECT * FROM users WHERE emp_phone=? OR js_phone=?", (phone, phone)).fetchone()
        c.close()
    return row

def upsert_user(cid, **f):
    if not f: return
    f["last_active"] = datetime.now().isoformat()
    with _lock:
        c = _c()
        ex = c.execute("SELECT 1 FROM users WHERE chat_id=?", (cid,)).fetchone()
        if ex:
            sets = ", ".join(f"{k}=?" for k in f)
            c.execute(f"UPDATE users SET {sets} WHERE chat_id=?", list(f.values()) + [cid])
        else:
            f["chat_id"] = cid
            f.setdefault("reg_date", shamsi_now())
            cols = ", ".join(f.keys())
            phs  = ", ".join("?" * len(f))
            c.execute(f"INSERT INTO users ({cols}) VALUES ({phs})", list(f.values()))
        c.commit()
        c.close()

def is_banned(cid):
    u = get_user(cid)
    return bool(u and u["is_banned"])

def ban_user(cid, reason=""):
    upsert_user(cid, is_banned=1, ban_reason=reason)

def unban_user(cid):
    upsert_user(cid, is_banned=0, ban_reason=None)

def get_all_users(role=None):
    with _lock:
        c = _c()
        if role:
            rows = c.execute("SELECT chat_id FROM users WHERE role=? AND is_banned=0", (role,)).fetchall()
        else:
            rows = c.execute("SELECT chat_id FROM users WHERE is_banned=0").fetchall()
        c.close()
    return rows

def get_users_by_category(category):
    with _lock:
        c = _c()
        rows = c.execute(
            "SELECT chat_id FROM users WHERE role='job_seeker' AND is_banned=0 "
            "AND private_mode=0 AND allow_employer_notify=1 AND js_categories LIKE ?",
            (f'%"{category}"%',)
        ).fetchall()
        c.close()
    return rows

def get_matching_seekers_for_job(category, province, city=None):
    with _lock:
        c = _c()
        sql = """SELECT chat_id FROM users 
                 WHERE role='job_seeker' AND is_banned=0 AND private_mode=0
                 AND allow_employer_notify=1
                 AND js_categories LIKE ?
                 AND (js_province = ? OR js_cities LIKE ?)"""
        params = [f'%"{category}"%', province, f'%"{province}"%']
        if city:
            sql += " OR js_cities LIKE ?"
            params.append(f'%"{city}"%')
        rows = c.execute(sql, params).fetchall()
        c.close()
    return rows

def get_matching_employers_for_seeker(category, province, cities):
    with _lock:
        c = _c()
        sql = """SELECT DISTINCT emp_cid FROM jobs 
                 WHERE status='active' AND admin_approved=1
                 AND category = ?
                 AND (province = ? OR province IN ({}) OR province = ?)"""
        if cities:
            placeholders = ",".join(["?"] * len(cities))
            sql = sql.format(placeholders)
            params = [category, province] + cities + [province]
        else:
            sql = sql.replace(" OR province IN ({})", "")
            params = [category, province]
        rows = c.execute(sql, params).fetchall()
        c.close()
        return [r["emp_cid"] for r in rows]

# ══════════════════════════════════════════════════════════════════════════
# آگهی‌ها
# ══════════════════════════════════════════════════════════════════════════
def create_job(emp_cid, **f):
    f.update(
        emp_cid=emp_cid,
        post_date=shamsi_now(),
        status="pending",
        admin_approved=0,
        expiry_date=(datetime.now() + timedelta(days=30)).isoformat()
    )
    with _lock:
        c = _c()
        cols = ", ".join(f.keys())
        phs  = ", ".join("?" * len(f))
        cur = c.execute(f"INSERT INTO jobs ({cols}) VALUES ({phs})", list(f.values()))
        jid = cur.lastrowid
        c.commit()
        c.close()
    return jid

def get_job(jid):
    with _lock:
        c = _c()
        row = c.execute("SELECT * FROM jobs WHERE job_id=?", (jid,)).fetchone()
        c.close()
    return row

def get_employer_jobs(emp_cid, page=0, per=10):
    with _lock:
        c = _c()
        total = c.execute("SELECT COUNT(*) FROM jobs WHERE emp_cid=?", (emp_cid,)).fetchone()[0]
        rows = c.execute(
            "SELECT * FROM jobs WHERE emp_cid=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (emp_cid, per, page * per)
        ).fetchall()
        c.close()
    return rows, total

def get_pending_jobs(category=None):
    with _lock:
        c = _c()
        sql = ("SELECT j.*, u.emp_company, u.emp_name FROM jobs j "
               "JOIN users u ON j.emp_cid=u.chat_id "
               "WHERE j.status='pending' AND j.admin_approved=0")
        params = []
        if category:
            sql += " AND j.category=?"
            params.append(category)
        sql += " ORDER BY j.created_at LIMIT 50"
        rows = c.execute(sql, params).fetchall()
        c.close()
    return rows

def approve_job(jid, admin_cid):
    with _lock:
        c = _c()
        c.execute(
            "UPDATE jobs SET admin_approved=1, status='active', approved_date=? WHERE job_id=?",
            (shamsi_dt(), jid)
        )
        c.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id) VALUES(?,?,?)",
            (admin_cid, "approve_job", jid)
        )
        c.commit()
        c.close()

def reject_job(jid, admin_cid, reason=""):
    with _lock:
        c = _c()
        c.execute("UPDATE jobs SET status='rejected' WHERE job_id=?", (jid,))
        c.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id, note) VALUES(?,?,?,?)",
            (admin_cid, "reject_job", jid, reason)
        )
        c.commit()
        c.close()

def update_job_by_admin(jid, admin_cid, **fields):
    """ویرایش آگهی توسط ادمین قبل از تأیید"""
    with _lock:
        c = _c()
        # فقط آگهی‌های pending قابل ویرایش هستند
        job = c.execute("SELECT status FROM jobs WHERE job_id=?", (jid,)).fetchone()
        if not job or job["status"] != "pending":
            c.close()
            return False
        sets = ", ".join(f"{k}=?" for k in fields)
        c.execute(f"UPDATE jobs SET {sets} WHERE job_id=?", list(fields.values()) + [jid])
        c.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id) VALUES(?,?,?)",
            (admin_cid, "edit_job", jid)
        )
        c.commit()
        c.close()
        return True

def close_job(jid):
    with _lock:
        c = _c()
        c.execute("UPDATE jobs SET status='closed' WHERE job_id=?", (jid,))
        c.commit()
        c.close()

def expire_old_jobs():
    with _lock:
        c = _c()
        c.execute(
            "UPDATE jobs SET status='expired' WHERE status='active' AND expiry_date < CURRENT_TIMESTAMP"
        )
        c.commit()
        c.close()

def increment_views(jid):
    with _lock:
        c = _c()
        c.execute("UPDATE jobs SET views=views+1 WHERE job_id=?", (jid,))
        c.commit()
        c.close()

def search_jobs(category=None, province=None, page=0, per=10):
    expire_old_jobs()
    with _lock:
        c = _c()
        sql = "SELECT * FROM jobs WHERE status='active' AND admin_approved=1"
        params = []
        if category and category != "همه":
            sql += " AND category=?"
            params.append(category)
        if province and province not in ("همه", ""):
            sql += " AND province=?"
            params.append(province)
        total = c.execute(sql.replace("SELECT *", "SELECT COUNT(*)"), params).fetchone()[0]
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [per, page * per]
        rows = c.execute(sql, params).fetchall()
        c.close()
    return rows, total

def search_seekers(category=None, province=None, experience=None, page=0, per=10):
    with _lock:
        c = _c()
        sql = "SELECT * FROM users WHERE role='job_seeker' AND is_banned=0 AND private_mode=0"
        params = []
        if category and category != "همه":
            sql += " AND js_categories LIKE ?"
            params.append(f'%"{category}"%')
        if province and province not in ("همه", ""):
            sql += " AND (js_province=? OR js_cities LIKE ?)"
            params += [province, f'%{province}%']
        if experience and experience != "همه":
            sql += " AND js_experience=?"
            params.append(experience)
        total = c.execute(sql.replace("SELECT *", "SELECT COUNT(*)"), params).fetchone()[0]
        sql += " ORDER BY rating DESC, created_at DESC LIMIT ? OFFSET ?"
        params += [per, page * per]
        rows = c.execute(sql, params).fetchall()
        c.close()
    return rows, total

# ══════════════════════════════════════════════════════════════════════════
# درخواست‌های رزومه
# ══════════════════════════════════════════════════════════════════════════
def create_application(job_id, seeker_cid, cover_letter=None,
                       resume_file=None, resume_type=None, file_size=0):
    with _lock:
        c = _c()
        try:
            cur = c.execute(
                "INSERT INTO applications "
                "(job_id, seeker_cid, cover_letter, resume_file, resume_type, file_size, sent_date) "
                "VALUES(?,?,?,?,?,?,?)",
                (job_id, seeker_cid, cover_letter, resume_file, resume_type, file_size, shamsi_dt())
            )
            aid = cur.lastrowid
            c.execute("UPDATE jobs SET app_count=app_count+1 WHERE job_id=?", (job_id,))
            c.commit()
            c.close()
            return aid, None
        except sqlite3.IntegrityError:
            c.close()
            return None, "duplicate"
        except Exception as e:
            c.close()
            return None, str(e)

def get_application(aid):
    with _lock:
        c = _c()
        row = c.execute(
            "SELECT a.*, u.js_name, u.js_phone, u.js_province, u.js_experience, "
            "u.js_education, u.js_categories, u.js_skills, u.rating, u.js_about, "
            "u.work_experience, j.title, j.category, j.emp_cid FROM applications a "
            "JOIN users u ON a.seeker_cid=u.chat_id "
            "JOIN jobs j ON a.job_id=j.job_id WHERE a.app_id=?",
            (aid,)
        ).fetchone()
        c.close()
    return row

def get_pending_applications(category=None):
    with _lock:
        c = _c()
        sql = ("SELECT a.*, u.js_name, u.js_phone, u.js_experience, u.rating, "
               "u.work_experience, j.title, j.category, j.emp_cid FROM applications a "
               "JOIN users u ON a.seeker_cid=u.chat_id "
               "JOIN jobs j ON a.job_id=j.job_id "
               "WHERE a.status='pending_admin'")
        params = []
        if category:
            sql += " AND j.category=?"
            params.append(category)
        sql += " ORDER BY a.created_at LIMIT 50"
        rows = c.execute(sql, params).fetchall()
        c.close()
    return rows

def get_job_applications(job_id):
    with _lock:
        c = _c()
        rows = c.execute(
            "SELECT a.*, u.js_name, u.js_phone, u.js_experience, u.rating, u.work_experience "
            "FROM applications a JOIN users u ON a.seeker_cid=u.chat_id "
            "WHERE a.job_id=? ORDER BY a.created_at DESC",
            (job_id,)
        ).fetchall()
        c.close()
    return rows

def get_seeker_applications(seeker_cid):
    with _lock:
        c = _c()
        rows = c.execute(
            "SELECT a.*, j.title, j.category, j.province FROM applications a "
            "JOIN jobs j ON a.job_id=j.job_id "
            "WHERE a.seeker_cid=? ORDER BY a.created_at DESC LIMIT 50",
            (seeker_cid,)
        ).fetchall()
        c.close()
    return rows

def approve_application(aid, admin_cid, note=""):
    with _lock:
        c = _c()
        c.execute("UPDATE applications SET status='approved', admin_note=? WHERE app_id=?", (note, aid))
        c.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id, note) VALUES(?,?,?,?)",
            (admin_cid, "approve_app", aid, note)
        )
        c.commit()
        c.close()

def reject_application(aid, admin_cid, reason=""):
    with _lock:
        c = _c()
        c.execute("UPDATE applications SET status='rejected', admin_note=? WHERE app_id=?", (reason, aid))
        c.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id, note) VALUES(?,?,?,?)",
            (admin_cid, "reject_app", aid, reason)
        )
        c.commit()
        c.close()

def update_application_by_admin(aid, admin_cid, **fields):
    """ویرایش رزومه توسط ادمین قبل از تأیید"""
    with _lock:
        c = _c()
        app = c.execute("SELECT status FROM applications WHERE app_id=?", (aid,)).fetchone()
        if not app or app["status"] != "pending_admin":
            c.close()
            return False
        sets = ", ".join(f"{k}=?" for k in fields)
        c.execute(f"UPDATE applications SET {sets} WHERE app_id=?", list(fields.values()) + [aid])
        c.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id) VALUES(?,?,?)",
            (admin_cid, "edit_app", aid)
        )
        c.commit()
        c.close()
        return True

def has_applied(job_id, seeker_cid):
    with _lock:
        c = _c()
        row = c.execute(
            "SELECT 1 FROM applications WHERE job_id=? AND seeker_cid=?",
            (job_id, seeker_cid)
        ).fetchone()
        c.close()
    return bool(row)

# ══════════════════════════════════════════════════════════════════════════
# بوکمارک
# ══════════════════════════════════════════════════════════════════════════
def add_bookmark(user_cid, job_id):
    with _lock:
        c = _c()
        try:
            c.execute("INSERT OR IGNORE INTO bookmarks(user_cid, job_id) VALUES(?,?)", (user_cid, job_id))
            c.commit()
            c.close()
            return True
        except:
            c.close()
            return False

def remove_bookmark(user_cid, job_id):
    with _lock:
        c = _c()
        c.execute("DELETE FROM bookmarks WHERE user_cid=? AND job_id=?", (user_cid, job_id))
        c.commit()
        c.close()

def get_bookmarks(user_cid):
    with _lock:
        c = _c()
        rows = c.execute(
            "SELECT j.* FROM bookmarks b JOIN jobs j ON b.job_id=j.job_id "
            "WHERE b.user_cid=? ORDER BY b.created_at DESC LIMIT 20",
            (user_cid,)
        ).fetchall()
        c.close()
    return rows

def is_bookmarked(user_cid, job_id):
    with _lock:
        c = _c()
        row = c.execute("SELECT 1 FROM bookmarks WHERE user_cid=? AND job_id=?", (user_cid, job_id)).fetchone()
        c.close()
    return bool(row)

# ══════════════════════════════════════════════════════════════════════════
# امتیاز
# ══════════════════════════════════════════════════════════════════════════
def add_rating(from_cid, to_cid, job_id, score, comment=""):
    with _lock:
        c = _c()
        try:
            c.execute(
                "INSERT OR REPLACE INTO ratings(from_cid, to_cid, job_id, score, comment) "
                "VALUES(?,?,?,?,?)",
                (from_cid, to_cid, job_id, score, comment)
            )
            avg = c.execute("SELECT AVG(score), COUNT(*) FROM ratings WHERE to_cid=?", (to_cid,)).fetchone()
            new_rating = round(avg[0], 1) if avg[0] else 0.0
            new_count = avg[1] if avg[1] else 0
            c.execute("UPDATE users SET rating=?, rating_count=? WHERE chat_id=?", (new_rating, new_count, to_cid))
            c.commit()
            c.close()
            return True
        except:
            c.close()
            return False

# ══════════════════════════════════════════════════════════════════════════
# اعلان
# ══════════════════════════════════════════════════════════════════════════
def add_notification(user_cid, text):
    with _lock:
        c = _c()
        c.execute("INSERT INTO notifications(user_cid, text) VALUES(?,?)", (user_cid, text))
        c.commit()
        c.close()

def get_unread_count(user_cid):
    with _lock:
        c = _c()
        n = c.execute("SELECT COUNT(*) FROM notifications WHERE user_cid=? AND is_read=0", (user_cid,)).fetchone()[0]
        c.close()
    return n

def get_notifications(user_cid):
    with _lock:
        c = _c()
        rows = c.execute(
            "SELECT * FROM notifications WHERE user_cid=? ORDER BY created_at DESC LIMIT 50",
            (user_cid,)
        ).fetchall()
        c.execute("UPDATE notifications SET is_read=1 WHERE user_cid=?", (user_cid,))
        c.commit()
        c.close()
    return rows

# ══════════════════════════════════════════════════════════════════════════
# آمار
# ══════════════════════════════════════════════════════════════════════════
def get_stats():
    with _lock:
        c = _c()
        q = lambda sql: c.execute(sql).fetchone()[0]
        stats = {
            "total": q("SELECT COUNT(*) FROM users"),
            "employers": q("SELECT COUNT(*) FROM users WHERE role='employer'"),
            "seekers": q("SELECT COUNT(*) FROM users WHERE role='job_seeker'"),
            "active_jobs": q("SELECT COUNT(*) FROM jobs WHERE status='active'"),
            "pending_jobs": q("SELECT COUNT(*) FROM jobs WHERE status='pending'"),
            "expired_jobs": q("SELECT COUNT(*) FROM jobs WHERE status='expired'"),
            "closed_jobs": q("SELECT COUNT(*) FROM jobs WHERE status='closed'"),
            "total_apps": q("SELECT COUNT(*) FROM applications"),
            "pending_apps": q("SELECT COUNT(*) FROM applications WHERE status='pending_admin'"),
            "approved_apps": q("SELECT COUNT(*) FROM applications WHERE status='approved'"),
            "rejected_apps": q("SELECT COUNT(*) FROM applications WHERE status='rejected'"),
            "banned": q("SELECT COUNT(*) FROM users WHERE is_banned=1"),
            "bookmarks": q("SELECT COUNT(*) FROM bookmarks"),
        }
        cats = c.execute(
            "SELECT category, COUNT(*) as n FROM jobs WHERE status='active' "
            "GROUP BY category ORDER BY n DESC LIMIT 5"
        ).fetchall()
        stats["top_cats"] = [(r["category"], r["n"]) for r in cats]
        c.close()
    return stats

# ══════════════════════════════════════════════════════════════════════════
# لاگ‌های ادمین
# ══════════════════════════════════════════════════════════════════════════
def get_admin_logs(limit=20):
    with _lock:
        c = _c()
        rows = c.execute("SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        c.close()
    return rows

# ══════════════════════════════════════════════════════════════════════════
# تاریخچه فعالیت (با نتیجه)
# ══════════════════════════════════════════════════════════════════════════
def add_activity_log(user_cid, action, detail="", result=""):
    with _lock:
        c = _c()
        c.execute(
            "INSERT INTO activity_logs(user_cid, action, detail, result) VALUES(?,?,?,?)",
            (user_cid, action, detail, result)
        )
        c.commit()
        c.close()

def get_activity_log(user_cid, limit=30):
    with _lock:
        c = _c()
        rows = c.execute(
            "SELECT * FROM activity_logs WHERE user_cid=? ORDER BY created_at DESC LIMIT ?",
            (user_cid, limit)
        ).fetchall()
        c.close()
    return rows

# ══════════════════════════════════════════════════════════════════════════
# پیام مستقیم
# ══════════════════════════════════════════════════════════════════════════
def save_direct_message(from_cid, to_cid, job_id, text):
    with _lock:
        c = _c()
        c.execute(
            "INSERT INTO direct_messages(from_cid, to_cid, job_id, text) VALUES(?,?,?,?)",
            (from_cid, to_cid, job_id, text)
        )
        c.commit()
        c.close()

# ══════════════════════════════════════════════════════════════════════════
# ویرایش آگهی (توسط کاربر)
# ══════════════════════════════════════════════════════════════════════════
def update_job(job_id, emp_cid, **fields):
    with _lock:
        c = _c()
        ex = c.execute("SELECT 1 FROM jobs WHERE job_id=? AND emp_cid=?", (job_id, emp_cid)).fetchone()
        if not ex:
            c.close()
            return False
        sets = ", ".join(f"{k}=?" for k in fields)
        c.execute(f"UPDATE jobs SET {sets} WHERE job_id=?", list(fields.values()) + [job_id])
        c.commit()
        c.close()
        return True

def delete_job(job_id, emp_cid):
    with _lock:
        c = _c()
        c.execute("DELETE FROM jobs WHERE job_id=? AND emp_cid=?", (job_id, emp_cid))
        c.commit()
        c.close()

# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════
def fmt_salary(mn, mx=None):
    def _f(n):
        if not n or n == 0:
            return None
        try:
            s = str(int(n))
            return ",".join([s[max(0, i-3):i] for i in range(len(s), 0, -3)][::-1])
        except:
            return None
    a = _f(mn)
    b = _f(mx)
    if a and b:
        return f"{a} — {b} تومان"
    if a:
        return f"{a} تومان"
    return "توافقی"

def parse_int(text):
    if not text:
        return 0
    m = re.search(r'\d+', str(text).replace(",", "").replace("،", "").replace("٬", ""))
    return int(m.group()) if m else 0

def stars(rating, count=0):
    if not rating:
        return "بدون امتیاز"
    full = int(rating)
    s = "⭐" * full + "☆" * (5 - full)
    if count:
        return f"{s} ({rating:.1f} از {count} نظر)"
    return f"{s} ({rating:.1f})"

def jlist(text):
    if not text:
        return []
    try:
        return json.loads(text)
    except:
        return []

# ══════════════════════════════════════════════════════════════════════════
# تطابق هوشمند
# ══════════════════════════════════════════════════════════════════════════
def match_score(seeker, job) -> int:
    score = 0
    cats = jlist(seeker["js_categories"])
    if job["category"] in cats:
        score += 40
    cities = jlist(seeker["js_cities"])
    if seeker["js_province"] == job["province"]:
        score += 20
    elif job["province"] in cities:
        score += 15
    exp_order = ["بدون سابقه", "کمتر از ۱ سال", "۱ تا ۳ سال", "۳ تا ۵ سال", "بیش از ۵ سال"]
    s_exp = seeker.get("js_experience", "")
    j_exp = job.get("experience_need", "")
    if j_exp and j_exp != "none" and s_exp:
        try:
            if exp_order.index(s_exp) >= exp_order.index(j_exp):
                score += 15
            else:
                score += 5
        except:
            score += 8
    edu_order = ["زیر دیپلم", "دیپلم", "فوق‌دیپلم", "لیسانس", "فوق‌لیسانس", "دکترا"]
    s_edu = seeker.get("js_education", "")
    j_edu = job.get("education_need", "")
    if j_edu and j_edu != "none" and s_edu:
        try:
            if edu_order.index(s_edu) >= edu_order.index(j_edu):
                score += 10
            else:
                score += 3
        except:
            score += 5
    j_gend = job.get("gender_need", "")
    s_gend = seeker.get("js_gender", "")
    if not j_gend or j_gend == "بدون‌ترجیح":
        score += 10
    elif j_gend == s_gend:
        score += 10
    s_sal = seeker.get("js_salary_min", 0) or 0
    j_sal_max = job.get("salary_max", 0) or 0
    if s_sal == 0 or j_sal_max == 0:
        score += 5
    elif s_sal <= j_sal_max:
        score += 5
    return min(score, 100)

def get_matched_jobs(seeker_cid, limit=10):
    expire_old_jobs()
    seeker = get_user(seeker_cid)
    if not seeker:
        return []
    with _lock:
        c = _c()
        jobs = c.execute(
            "SELECT * FROM jobs WHERE status='active' AND admin_approved=1 "
            "ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
        c.close()
    scored = []
    for job in jobs:
        sc = match_score(seeker, job)
        if sc >= 20:
            scored.append((sc, dict(job)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]

def get_matched_seekers(job_id, limit=10):
    job = get_job(job_id)
    if not job:
        return []
    with _lock:
        c = _c()
        seekers = c.execute(
            "SELECT * FROM users WHERE role='job_seeker' "
            "AND is_banned=0 AND private_mode=0 LIMIT 500"
        ).fetchall()
        c.close()
    scored = []
    for sk in seekers:
        sc = match_score(sk, job)
        if sc >= 20:
            scored.append((sc, dict(sk)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]