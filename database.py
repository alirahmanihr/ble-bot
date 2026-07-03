"""
database.py - نسخه async کامل
✅ asyncio.Lock | ✅ asyncio.to_thread | ✅ Transaction Safety | ✅ Soft Delete
"""

import sqlite3
import json
import re
import time
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

log = logging.getLogger(__name__)

# ==================== Rate Limiting ====================
# In-memory rate limiter: max 5 resume submissions per 60s per user
_rate_limit: Dict[int, list] = {}
_rate_limit_lock = asyncio.Lock()

# ==================== تاریخ شمسی ====================
try:
    import jdatetime

    def shamsi_now() -> str:
        return jdatetime.datetime.now().strftime("%Y/%m/%d")

    def shamsi_dt() -> str:
        return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M")
except:

    def shamsi_now() -> str:
        return datetime.now().strftime("%Y/%m/%d")

    def shamsi_dt() -> str:
        return datetime.now().strftime("%Y/%m/%d %H:%M")


DB_PATH = Path(__file__).parent / "hamrakar.db"
_db_lock = asyncio.Lock()
SCHEMA_VERSION = 3

# ==================== CONSTANTS ====================
INDUSTRIES = [
    "فناوری اطلاعات",
    "تولید و صنعت",
    "ساختمان و عمران",
    "بازرگانی",
    "آموزش",
    "خدمات درمانی",
    "بانکداری و بیمه",
    "بازاریابی",
    "حمل و نقل",
    "کشاورزی",
    "گردشگری",
    "رسانه",
    "مخابرات",
    "انرژی",
    "سایر",
]
CATEGORIES = [
    "حسابداری",
    "آموزش",
    "بازاریابی",
    "گردشگری",
    "تولید",
    "تدارکات",
    "مهندسی",
    "کشاورزی",
    "فروش",
    "پزشکی",
    "مدیریت",
    "برنامه‌نویسی",
    "غذایی",
    "معماری",
    "HSE",
    "تجارت",
    "CEO",
    "HR",
    "طراحی",
    "حقوقی",
    "دولتی",
    "مهندسی‌پزشکی",
    "IT",
    "خودرو",
    "محتوا",
    "مشتریان",
    "R&D",
    "روابط‌عمومی",
    "عمومی",
    "سایر",
]
PROVINCES = [
    "تهران",
    "البرز",
    "مازندران",
    "گیلان",
    "اردبیل",
    "آذربایجان‌شرقی",
    "آذربایجان‌غربی",
    "کردستان",
    "کرمانشاه",
    "خوزستان",
    "ایلام",
    "بوشهر",
    "هرمزگان",
    "سیستان",
    "خراسان‌رضوی",
    "خراسان‌شمالی",
    "خراسان‌جنوبی",
    "قم",
    "سمنان",
    "زنجان",
    "مرکزی",
    "اصفهان",
    "لرستان",
    "فارس",
    "کرمان",
    "یزد",
    "چهارمحال",
    "کهگیلویه",
    "گلستان",
    "همدان",
    "شیراز",
]
EMP_TYPES = ["تمام‌وقت", "پاره‌وقت", "دورکاری", "پروژه‌ای", "فصلی"]
GENDERS = ["مرد", "زن", "بدون‌ترجیح"]
EXPERIENCES = [
    "بدون سابقه",
    "کمتر از ۱ سال",
    "۱ تا ۳ سال",
    "۳ تا ۵ سال",
    "بیش از ۵ سال",
]
EDUCATIONS = ["زیر دیپلم", "دیپلم", "فوق‌دیپلم", "لیسانس", "فوق‌لیسانس", "دکترا"]
RELOCATE = ["بله", "فقط شهر خودم", "بسته به شرایط"]
SKILLS_LIST = [
    "Excel",
    "Word",
    "Python",
    "Java",
    "PHP",
    "JavaScript",
    "SQL",
    "AutoCAD",
    "Photoshop",
    "Illustrator",
    "حسابداری",
    "مذاکره",
    "فروش",
    "بازاریابی دیجیتال",
    "SEO",
    "مدیریت پروژه",
    "PMP",
    "ICDL",
    "زبان انگلیسی",
    "تحلیل داده",
    "مدیریت تیم",
    "رهبری",
    "ارتباط موثر",
    "حل مسئله",
    "عمومی",
    "سایر",
    "بدون مهارت",
]


# ==================== CONNECTION ====================
def _c() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=60, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=20000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


# ==================== SAFETY: Row → dict converters ====================
def to_dict(row) -> Optional[Dict]:
    """Convert sqlite3.Row → dict. Returns None for None input."""
    if row is None:
        return None
    return dict(row)


def to_dict_list(rows) -> List[Dict]:
    """Convert list of sqlite3.Row → list of dict. Always returns list."""
    if not rows:
        return []
    return [dict(r) for r in rows]


def _get_schema_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute(
            "SELECT value FROM metadata WHERE key='schema_version'"
        ).fetchone()
        return int(row[0]) if row else 0
    except:
        return 0


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
        (str(version),),
    )


def _run_migrations(conn: sqlite3.Connection, current_version: int) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)"
    )

    # === v1: base tables ===
    if current_version < 1:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            role TEXT CHECK(role IN ('employer','job_seeker')),
            emp_name TEXT, emp_company TEXT, emp_industry TEXT, emp_phone TEXT UNIQUE,
            emp_position TEXT, emp_address TEXT, emp_email TEXT, emp_website TEXT,
            emp_gender_need TEXT, emp_age_min INTEGER, emp_age_max INTEGER,
            js_name TEXT, js_phone TEXT UNIQUE, js_province TEXT, js_job_title TEXT,
            js_experience TEXT, js_education TEXT, js_salary_min INTEGER DEFAULT 0,
            js_salary_max INTEGER DEFAULT 0, js_dob TEXT, js_gender TEXT,
            js_relocate TEXT, js_cities TEXT DEFAULT '[]', js_categories TEXT DEFAULT '[]',
            js_skills TEXT DEFAULT '[]', js_about TEXT,
            work_experience TEXT DEFAULT '[]', allow_employer_notify INTEGER DEFAULT 0,
            resume_complete INTEGER DEFAULT 0, rating REAL DEFAULT 0.0,
            rating_count INTEGER DEFAULT 0, private_mode INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0, ban_reason TEXT, reg_date TEXT,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_states (
            chat_id INTEGER PRIMARY KEY, state TEXT DEFAULT 'IDLE',
            data TEXT DEFAULT '{}', updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT, emp_cid INTEGER NOT NULL,
            title TEXT NOT NULL, emp_type TEXT, province TEXT, city TEXT,
            salary_min INTEGER DEFAULT 0, salary_max INTEGER DEFAULT 0,
            category TEXT NOT NULL, gender_need TEXT, age_min INTEGER, age_max INTEGER,
            education_need TEXT, experience_need TEXT, description TEXT, benefits TEXT,
            contact_phone TEXT, contact_email TEXT, contact_address TEXT,
            status TEXT DEFAULT 'pending', admin_approved INTEGER DEFAULT 0,
            approved_date TEXT, expiry_date TEXT, views INTEGER DEFAULT 0,
            app_count INTEGER DEFAULT 0, post_date TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(emp_cid) REFERENCES users(chat_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS applications (
            app_id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL,
            seeker_cid INTEGER NOT NULL, cover_letter TEXT, resume_file TEXT,
            resume_type TEXT, file_size INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending_admin', admin_note TEXT, employer_note TEXT,
            sent_date TEXT, seen_date TEXT, idempotency_key TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
            FOREIGN KEY(seeker_cid) REFERENCES users(chat_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS ratings (
            rating_id INTEGER PRIMARY KEY AUTOINCREMENT, from_cid INTEGER NOT NULL,
            to_cid INTEGER NOT NULL, job_id INTEGER, score INTEGER, comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_cid, to_cid, job_id)
        );
        CREATE TABLE IF NOT EXISTS bookmarks (
            bm_id INTEGER PRIMARY KEY AUTOINCREMENT, user_cid INTEGER NOT NULL,
            job_id INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_cid, job_id),
            FOREIGN KEY(user_cid) REFERENCES users(chat_id) ON DELETE CASCADE,
            FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS notifications (
            notif_id INTEGER PRIMARY KEY AUTOINCREMENT, user_cid INTEGER NOT NULL,
            text TEXT NOT NULL, is_read INTEGER DEFAULT 0, message_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_cid) REFERENCES users(chat_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS admin_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT, admin_cid INTEGER NOT NULL,
            action TEXT NOT NULL, target_id INTEGER, note TEXT, ip_address TEXT,
            user_agent TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS activity_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT, user_cid INTEGER NOT NULL,
            action TEXT NOT NULL, detail TEXT, result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_cid) REFERENCES users(chat_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS direct_messages (
            msg_id INTEGER PRIMARY KEY AUTOINCREMENT, from_cid INTEGER NOT NULL,
            to_cid INTEGER NOT NULL, job_id INTEGER, text TEXT NOT NULL,
            is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        _set_schema_version(conn, 1)

    if current_version < 2:
        for table in [
            "users",
            "jobs",
            "applications",
            "bookmarks",
            "notifications",
            "activity_logs",
            "direct_messages",
            "ratings",
        ]:
            try:
                cols = [
                    c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()
                ]
                if "deleted_at" not in cols:
                    conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL"
                    )
                    log.info(f"  ✅ added deleted_at to {table}")
            except Exception as e:
                log.warning(f"  ⚠️ could not add deleted_at to {table}: {e}")
        _set_schema_version(conn, 2)

    if current_version < 3:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS work_experiences (
                exp_id INTEGER PRIMARY KEY AUTOINCREMENT, user_chat_id INTEGER NOT NULL,
                place TEXT NOT NULL, duration TEXT NOT NULL, role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, deleted_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY(user_chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_work_user ON work_experiences(user_chat_id)"
        )
        for idx in [
            "CREATE INDEX IF NOT EXISTS idx_jobs_cat ON jobs(category, status, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_prov ON jobs(province, status, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_emp ON jobs(emp_cid, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_expiry ON jobs(expiry_date, status, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_cat_prov ON jobs(category, province, status, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_apps_job ON applications(job_id, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_apps_seeker ON applications(seeker_cid, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status, deleted_at)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_apps_unique ON applications(job_id, seeker_cid, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_ratings_to ON ratings(to_cid, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_cid, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_cid, is_read, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_admin_logs_action ON admin_logs(action, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_admin_logs_admin ON admin_logs(admin_cid, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_logs(user_cid, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_dm_from ON direct_messages(from_cid, deleted_at)",
            "CREATE INDEX IF NOT EXISTS idx_dm_to ON direct_messages(to_cid, deleted_at)",
        ]:
            conn.execute(idx)
        _set_schema_version(conn, 3)


# ==================== ASYNC DB WRAPPER ====================
async def _run_db(fn, *args, **kwargs):
    """Run a sync function in thread pool under async lock."""
    async with _db_lock:
        return await asyncio.to_thread(fn, *args, **kwargs)


def _repair_schema(conn: sqlite3.Connection):
    """Ensure required columns exist on all tables (belt-and-suspenders repair)."""
    # deleted_at on all tables
    tables = [
        "users",
        "jobs",
        "applications",
        "bookmarks",
        "notifications",
        "activity_logs",
        "direct_messages",
        "ratings",
        "user_states",
        "work_experiences",
    ]
    for table in tables:
        try:
            cols = [
                c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()
            ]
            if "deleted_at" not in cols:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL"
                )
                log.info(f"  🔧 repaired: added deleted_at to {table}")
        except Exception:
            pass  # table might not exist yet — ignore

    # Repair missing columns on users table (old DBs may lack these)
    try:
        cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
        needed = {
            "allow_employer_notify": "INTEGER DEFAULT 0",
            "resume_complete": "INTEGER DEFAULT 0",
            "js_about": "TEXT",
            "js_cities": "TEXT DEFAULT '[]'",
            "js_categories": "TEXT DEFAULT '[]'",
            "js_skills": "TEXT DEFAULT '[]'",
            "work_experience": "TEXT DEFAULT '[]'",
        }
        for col_name, col_def in needed.items():
            if col_name not in cols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                log.info(f"  🔧 repaired: added {col_name} to users")
    except Exception as e:
        log.warning(f"  ⚠️ schema repair on users: {e}")


# ==================== INIT ====================
def _init_db_sync():
    conn = _c()
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)"
        )
        current_version = _get_schema_version(conn)
        if current_version < SCHEMA_VERSION:
            _run_migrations(conn, current_version)
            log.info(f"✅ دیتابیس به نسخه {SCHEMA_VERSION} مهاجرت داده شد")
        else:
            log.info(f"✅ دیتابیس در نسخه {SCHEMA_VERSION} است")
        # Always repair missing columns (belt-and-suspenders)
        _repair_schema(conn)
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.error(f"❌ خطا در راه‌اندازی دیتابیس: {e}")
        raise
    finally:
        conn.close()


async def init_db():
    await _run_db(_init_db_sync)


# ==================== STATE ====================
def _get_state_sync(cid: int):
    conn = _c()
    try:
        row = conn.execute(
            "SELECT state, data FROM user_states WHERE chat_id=? AND deleted_at IS NULL",
            (cid,),
        ).fetchone()
        if row:
            try:
                return row[0], json.loads(row[1])
            except:
                return row[0], {}
    finally:
        conn.close()
    return "IDLE", {}


async def get_state(cid: int) -> Tuple[str, Dict]:
    return await _run_db(_get_state_sync, cid)


def _set_state_sync(cid: int, state: str, data: Optional[Dict] = None):
    if data is None:
        data = {}
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (cid,))
        conn.execute(
            "INSERT OR REPLACE INTO user_states(chat_id, state, data, updated_at) VALUES(?, ?, ?, CURRENT_TIMESTAMP)",
            (cid, state, json.dumps(data, ensure_ascii=False)),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def set_state(cid: int, state: str, data: Optional[Dict] = None) -> bool:
    return await _run_db(_set_state_sync, cid, state, data)


def _clear_state_sync(cid: int):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "UPDATE user_states SET deleted_at=CURRENT_TIMESTAMP WHERE chat_id=?",
            (cid,),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def clear_state(cid: int) -> bool:
    return await _run_db(_clear_state_sync, cid)


def _is_state_stale_sync(cid: int, ttl_minutes: int = 30) -> bool:
    """Check if user's state is older than ttl_minutes. Returns True if stale."""
    conn = _c()
    try:
        row = conn.execute(
            "SELECT updated_at FROM user_states WHERE chat_id=? AND deleted_at IS NULL AND state != ?",
            (cid, "IDLE"),
        ).fetchone()
        if not row or not row[0]:
            return False
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz

        try:
            updated = _dt.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            return _dt.utcnow() - updated > _td(minutes=ttl_minutes)
        except Exception:
            return False
    finally:
        conn.close()


async def is_state_stale(cid: int, ttl_minutes: int = 30) -> bool:
    return await _run_db(_is_state_stale_sync, cid, ttl_minutes)


# ==================== USERS ====================
def _get_user_sync(cid: int):
    conn = _c()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE chat_id=? AND deleted_at IS NULL", (cid,)
        ).fetchone()
        return to_dict(row)
    finally:
        conn.close()


async def get_user(cid: int):
    return await _run_db(_get_user_sync, cid)


def _get_user_by_phone_sync(phone: str, role: Optional[str] = None):
    if not phone:
        return None
    conn = _c()
    try:
        if role == "employer":
            row = conn.execute(
                "SELECT * FROM users WHERE emp_phone=? AND role='employer' AND deleted_at IS NULL",
                (phone,),
            ).fetchone()
        elif role == "job_seeker":
            row = conn.execute(
                "SELECT * FROM users WHERE js_phone=? AND role='job_seeker' AND deleted_at IS NULL",
                (phone,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM users WHERE (emp_phone=? OR js_phone=?) AND deleted_at IS NULL",
                (phone, phone),
            ).fetchone()
        return to_dict(row)
    finally:
        conn.close()


async def get_user_by_phone(phone: str, role: Optional[str] = None):
    return await _run_db(_get_user_by_phone_sync, phone, role)


def _upsert_user_sync(cid: int, **fields):
    if not fields:
        return False
    fields["last_active"] = datetime.now().isoformat()
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
        valid = {k: v for k, v in fields.items() if k in cols}
        existing = conn.execute(
            "SELECT 1 FROM users WHERE chat_id=? AND deleted_at IS NULL", (cid,)
        ).fetchone()
        if existing:
            if valid:
                set_clause = ", ".join(f"{k}=?" for k in valid)
                conn.execute(
                    f"UPDATE users SET {set_clause} WHERE chat_id=?",
                    list(valid.values()) + [cid],
                )
        else:
            valid["chat_id"] = cid
            valid.setdefault("reg_date", shamsi_now())
            conn.execute(
                f"INSERT INTO users ({', '.join(valid.keys())}) VALUES ({', '.join('?' * len(valid))})",
                list(valid.values()),
            )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def upsert_user(cid: int, **fields) -> bool:
    return await _run_db(_upsert_user_sync, cid, **fields)


async def is_banned(cid: int) -> bool:
    user = await get_user(cid)
    return bool(user and user["is_banned"])


async def ban_user(cid: int, reason: str = "") -> bool:
    return await upsert_user(cid, is_banned=1, ban_reason=reason)


async def unban_user(cid: int) -> bool:
    return await upsert_user(cid, is_banned=0, ban_reason=None)


def _get_all_users_sync(role: Optional[str] = None):
    conn = _c()
    try:
        if role:
            rows = conn.execute(
                "SELECT chat_id FROM users WHERE role=? AND is_banned=0 AND deleted_at IS NULL",
                (role,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT chat_id FROM users WHERE is_banned=0 AND deleted_at IS NULL"
            ).fetchall()
        return to_dict_list(rows)
    finally:
        conn.close()


async def get_all_users(role: Optional[str] = None):
    return await _run_db(_get_all_users_sync, role)


def _get_users_by_category_sync(category: str):
    conn = _c()
    try:
        rows = conn.execute(
            "SELECT chat_id FROM users WHERE role='job_seeker' AND is_banned=0 AND private_mode=0 AND allow_employer_notify=1 AND js_categories LIKE ? AND deleted_at IS NULL",
            (f'%"{category}"%',),
        ).fetchall()
        return to_dict_list(rows)
    finally:
        conn.close()


async def get_users_by_category(category: str):
    return await _run_db(_get_users_by_category_sync, category)


# ==================== WORK EXPERIENCE ====================
def _add_work_experience_sync(user_chat_id: int, place: str, duration: str, role: str):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        existing = conn.execute(
            "SELECT exp_id FROM work_experiences WHERE user_chat_id=? AND place=? AND duration=? AND role=? AND deleted_at IS NULL",
            (user_chat_id, place, duration, role),
        ).fetchone()
        if existing:
            conn.commit()
            return True
        conn.execute(
            "INSERT INTO work_experiences(user_chat_id, place, duration, role) VALUES(?,?,?,?)",
            (user_chat_id, place, duration, role),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def add_work_experience(
    user_chat_id: int, place: str, duration: str, role: str
) -> bool:
    return await _run_db(_add_work_experience_sync, user_chat_id, place, duration, role)


def _get_work_experiences_sync(user_chat_id: int):
    conn = _c()
    try:
        rows = conn.execute(
            "SELECT place, duration, role FROM work_experiences WHERE user_chat_id=? AND deleted_at IS NULL ORDER BY created_at DESC",
            (user_chat_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


async def get_work_experiences(user_chat_id: int):
    return await _run_db(_get_work_experiences_sync, user_chat_id)


# ==================== JOBS ====================
def _create_job_sync(emp_cid: int, **fields):
    fields.update(
        emp_cid=emp_cid,
        post_date=shamsi_now(),
        status="pending",
        admin_approved=0,
        expiry_date=(datetime.now() + timedelta(days=30)).isoformat(),
    )
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        cols = [c[1] for c in conn.execute("PRAGMA table_info(jobs)").fetchall()]
        valid = {k: v for k, v in fields.items() if k in cols}
        cursor = conn.execute(
            f"INSERT INTO jobs ({', '.join(valid.keys())}) VALUES ({', '.join('?' * len(valid))})",
            list(valid.values()),
        )
        jid = cursor.lastrowid
        conn.commit()
        return jid
    except:
        conn.rollback()
        return None
    finally:
        conn.close()


async def create_job(emp_cid: int, **fields):
    return await _run_db(_create_job_sync, emp_cid, **fields)


def _get_job_sync(jid: int):
    conn = _c()
    try:
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id=? AND deleted_at IS NULL", (jid,)
        ).fetchone()
        return to_dict(row)
    finally:
        conn.close()


async def get_job(jid: int):
    return await _run_db(_get_job_sync, jid)


def _get_employer_jobs_sync(emp_cid: int, page: int = 0, per: int = 10):
    conn = _c()
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE emp_cid=? AND deleted_at IS NULL",
            (emp_cid,),
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM jobs WHERE emp_cid=? AND deleted_at IS NULL ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (emp_cid, per, page * per),
        ).fetchall()
        return to_dict_list(rows), total
    finally:
        conn.close()


async def get_employer_jobs(emp_cid: int, page: int = 0, per: int = 10):
    return await _run_db(_get_employer_jobs_sync, emp_cid, page, per)


def _get_pending_jobs_sync(category: Optional[str] = None):
    conn = _c()
    try:
        sql = """SELECT j.*, u.emp_company, u.emp_name FROM jobs j
                 JOIN users u ON j.emp_cid=u.chat_id
                 WHERE j.status='pending' AND j.admin_approved=0
                 AND j.deleted_at IS NULL AND u.deleted_at IS NULL"""
        params = []
        if category:
            sql += " AND j.category=?"
            params.append(category)
        sql += " ORDER BY j.created_at LIMIT 50"
        rows = conn.execute(sql, params).fetchall()
        return to_dict_list(rows)
    finally:
        conn.close()


async def get_pending_jobs(category: Optional[str] = None):
    return await _run_db(_get_pending_jobs_sync, category)


def _approve_job_sync(jid: int, admin_cid: int):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "UPDATE jobs SET admin_approved=1, status='active', approved_date=? WHERE job_id=? AND deleted_at IS NULL",
            (shamsi_dt(), jid),
        )
        conn.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id) VALUES(?,?,?)",
            (admin_cid, "approve_job", jid),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def approve_job(jid: int, admin_cid: int) -> bool:
    return await _run_db(_approve_job_sync, jid, admin_cid)


def _reject_job_sync(jid: int, admin_cid: int, reason: str = ""):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "UPDATE jobs SET status='rejected' WHERE job_id=? AND deleted_at IS NULL",
            (jid,),
        )
        conn.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id, note) VALUES(?,?,?,?)",
            (admin_cid, "reject_job", jid, reason),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def reject_job(jid: int, admin_cid: int, reason: str = "") -> bool:
    return await _run_db(_reject_job_sync, jid, admin_cid, reason)


def _update_job_by_admin_sync(jid: int, admin_cid: int, **fields):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        job = conn.execute(
            "SELECT status FROM jobs WHERE job_id=? AND deleted_at IS NULL", (jid,)
        ).fetchone()
        if not job or job["status"] != "pending":
            conn.rollback()
            return False
        cols = [c[1] for c in conn.execute("PRAGMA table_info(jobs)").fetchall()]
        valid = {k: v for k, v in fields.items() if k in cols}
        set_clause = ", ".join(f"{k}=?" for k in valid)
        conn.execute(
            f"UPDATE jobs SET {set_clause} WHERE job_id=? AND deleted_at IS NULL",
            list(valid.values()) + [jid],
        )
        conn.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id) VALUES(?,?,?)",
            (admin_cid, "edit_job", jid),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def update_job_by_admin(jid: int, admin_cid: int, **fields) -> bool:
    return await _run_db(_update_job_by_admin_sync, jid, admin_cid, **fields)


def _update_job_sync(job_id: int, emp_cid: int, **fields):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        existing = conn.execute(
            "SELECT 1 FROM jobs WHERE job_id=? AND emp_cid=? AND deleted_at IS NULL",
            (job_id, emp_cid),
        ).fetchone()
        if not existing:
            conn.rollback()
            return False
        cols = [c[1] for c in conn.execute("PRAGMA table_info(jobs)").fetchall()]
        valid = {k: v for k, v in fields.items() if k in cols}
        set_clause = ", ".join(f"{k}=?" for k in valid)
        conn.execute(
            f"UPDATE jobs SET {set_clause} WHERE job_id=? AND deleted_at IS NULL",
            list(valid.values()) + [job_id],
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def update_job(job_id: int, emp_cid: int, **fields) -> bool:
    return await _run_db(_update_job_sync, job_id, emp_cid, **fields)


def _delete_job_sync(job_id: int, emp_cid: int):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "UPDATE jobs SET deleted_at=CURRENT_TIMESTAMP WHERE job_id=? AND emp_cid=? AND deleted_at IS NULL",
            (job_id, emp_cid),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def delete_job(job_id: int, emp_cid: int) -> bool:
    return await _run_db(_delete_job_sync, job_id, emp_cid)


def _expire_old_jobs_sync():
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "UPDATE jobs SET status='expired' WHERE status='active' AND expiry_date < CURRENT_TIMESTAMP AND deleted_at IS NULL"
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def expire_old_jobs() -> bool:
    return await _run_db(_expire_old_jobs_sync)


def _increment_views_sync(jid: int):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "UPDATE jobs SET views=views+1 WHERE job_id=? AND deleted_at IS NULL",
            (jid,),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def increment_views(jid: int) -> bool:
    return await _run_db(_increment_views_sync, jid)


def _search_jobs_sync(
    category: Optional[str] = None,
    province: Optional[str] = None,
    page: int = 0,
    per: int = 10,
):
    _expire_old_jobs_sync()
    conn = _c()
    try:
        sql = "SELECT * FROM jobs WHERE status='active' AND admin_approved=1 AND deleted_at IS NULL"
        params = []
        if category and category != "همه":
            sql += " AND category=?"
            params.append(category)
        if province and province not in ("همه", ""):
            sql += " AND province=?"
            params.append(province)
        total = conn.execute(
            sql.replace("SELECT *", "SELECT COUNT(*)"), params
        ).fetchone()[0]
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [per, page * per]
        rows = conn.execute(sql, params).fetchall()
        return to_dict_list(rows), total
    finally:
        conn.close()


async def search_jobs(
    category: Optional[str] = None,
    province: Optional[str] = None,
    page: int = 0,
    per: int = 10,
):
    return await _run_db(_search_jobs_sync, category, province, page, per)


def _search_seekers_sync(
    category: Optional[str] = None,
    province: Optional[str] = None,
    city: Optional[str] = None,
    experience: Optional[str] = None,
    salary_min: Optional[int] = None,
    page: int = 0,
    per: int = 10,
):
    conn = _c()
    try:
        sql = "SELECT * FROM users WHERE role='job_seeker' AND is_banned=0 AND private_mode=0 AND deleted_at IS NULL"
        params = []
        if category and category != "همه":
            sql += " AND js_categories LIKE ?"
            params.append(f'%"{category}"%')
        if province and province not in ("همه", ""):
            sql += " AND (js_province=? OR js_cities LIKE ?)"
            params += [province, f"%{province}%"]
        if city and city not in ("همه", ""):
            sql += " AND (js_cities LIKE ?)"
            params.append(f"%{city}%")
        if experience and experience != "همه":
            sql += " AND js_experience=?"
            params.append(experience)
        if salary_min and salary_min > 0:
            sql += " AND js_salary_min >= ?"
            params.append(salary_min)
        total = conn.execute(
            sql.replace("SELECT *", "SELECT COUNT(*)"), params
        ).fetchone()[0]
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [per, page * per]
        rows = conn.execute(sql, params).fetchall()
        return to_dict_list(rows), total
    finally:
        conn.close()


async def search_seekers(
    category: Optional[str] = None,
    province: Optional[str] = None,
    city: Optional[str] = None,
    experience: Optional[str] = None,
    salary_min: Optional[int] = None,
    page: int = 0,
    per: int = 10,
):
    return await _run_db(
        _search_seekers_sync,
        category,
        province,
        city,
        experience,
        salary_min,
        page,
        per,
    )


# ==================== APPLICATIONS ====================
def _create_application_sync(
    job_id: int,
    seeker_cid: int,
    cover_letter: Optional[str] = None,
    resume_file: Optional[str] = None,
    resume_type: Optional[str] = None,
    file_size: int = 0,
    idempotency_key: Optional[str] = None,
):
    if idempotency_key is None:
        idempotency_key = f"{job_id}_{seeker_cid}_{int(time.time())}"
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        existing = conn.execute(
            "SELECT app_id FROM applications WHERE idempotency_key=? AND deleted_at IS NULL",
            (idempotency_key,),
        ).fetchone()
        if existing:
            conn.commit()
            return existing[0], "already_exists"
        dup = conn.execute(
            "SELECT app_id FROM applications WHERE job_id=? AND seeker_cid=? AND deleted_at IS NULL",
            (job_id, seeker_cid),
        ).fetchone()
        if dup:
            conn.commit()
            return None, "duplicate"
        cursor = conn.execute(
            "INSERT INTO applications (job_id, seeker_cid, cover_letter, resume_file, resume_type, file_size, sent_date, idempotency_key) VALUES(?,?,?,?,?,?,?,?)",
            (
                job_id,
                seeker_cid,
                cover_letter,
                resume_file,
                resume_type,
                file_size,
                shamsi_dt(),
                idempotency_key,
            ),
        )
        aid = cursor.lastrowid
        conn.execute(
            "UPDATE jobs SET app_count=app_count+1 WHERE job_id=? AND deleted_at IS NULL",
            (job_id,),
        )
        conn.commit()
        return aid, None
    except:
        conn.rollback()
        return None, "duplicate"
    finally:
        conn.close()


async def create_application(
    job_id: int,
    seeker_cid: int,
    cover_letter: Optional[str] = None,
    resume_file: Optional[str] = None,
    resume_type: Optional[str] = None,
    file_size: int = 0,
    idempotency_key: Optional[str] = None,
):
    # Rate limit: max 5 applications per 60 seconds per user
    async with _rate_limit_lock:
        now = time.time()
        times = _rate_limit.get(seeker_cid, [])
        times = [t for t in times if now - t < 60]
        if len(times) >= 5:
            return None, "rate_limit"
        times.append(now)
        _rate_limit[seeker_cid] = times
    return await _run_db(
        _create_application_sync,
        job_id,
        seeker_cid,
        cover_letter,
        resume_file,
        resume_type,
        file_size,
        idempotency_key,
    )


def _get_application_sync(aid: int):
    conn = _c()
    try:
        row = conn.execute(
            "SELECT a.*, u.js_name, u.js_phone, u.js_province, u.js_experience, u.js_education, "
            "u.js_categories, u.js_skills, u.rating AS seeker_rating, u.js_about, "
            "j.title, j.category, j.emp_cid "
            "FROM applications a "
            "JOIN users u ON a.seeker_cid=u.chat_id "
            "JOIN jobs j ON a.job_id=j.job_id "
            "WHERE a.app_id=? AND a.deleted_at IS NULL AND u.deleted_at IS NULL AND j.deleted_at IS NULL",
            (aid,),
        ).fetchone()
        return to_dict(row)
    finally:
        conn.close()


async def get_application(aid: int):
    return await _run_db(_get_application_sync, aid)


def _get_pending_applications_sync(category: Optional[str] = None):
    conn = _c()
    try:
        sql = """SELECT a.*, u.js_name, u.js_phone, u.js_experience, u.rating AS seeker_rating, j.title, j.category, j.emp_cid
                 FROM applications a JOIN users u ON a.seeker_cid=u.chat_id JOIN jobs j ON a.job_id=j.job_id
                 WHERE a.status='pending_admin' AND a.deleted_at IS NULL AND u.deleted_at IS NULL AND j.deleted_at IS NULL"""
        params = []
        if category:
            sql += " AND j.category=?"
            params.append(category)
        sql += " ORDER BY a.created_at LIMIT 50"
        rows = conn.execute(sql, params).fetchall()
        return to_dict_list(rows)
    finally:
        conn.close()


async def get_pending_applications(category: Optional[str] = None):
    return await _run_db(_get_pending_applications_sync, category)


def _get_job_applications_sync(job_id: int):
    conn = _c()
    try:
        rows = conn.execute(
            "SELECT a.*, u.js_name, u.js_phone, u.js_experience, u.rating AS seeker_rating FROM applications a "
            "JOIN users u ON a.seeker_cid=u.chat_id WHERE a.job_id=? AND a.deleted_at IS NULL AND u.deleted_at IS NULL "
            "ORDER BY a.created_at DESC",
            (job_id,),
        ).fetchall()
        return to_dict_list(rows)
    finally:
        conn.close()


async def get_job_applications(job_id: int):
    return await _run_db(_get_job_applications_sync, job_id)


def _get_seeker_applications_sync(seeker_cid: int):
    conn = _c()
    try:
        rows = conn.execute(
            "SELECT a.*, j.title, j.category, j.province FROM applications a JOIN jobs j ON a.job_id=j.job_id "
            "WHERE a.seeker_cid=? AND a.deleted_at IS NULL AND j.deleted_at IS NULL ORDER BY a.created_at DESC LIMIT 50",
            (seeker_cid,),
        ).fetchall()
        return to_dict_list(rows)
    finally:
        conn.close()


async def get_seeker_applications(seeker_cid: int):
    return await _run_db(_get_seeker_applications_sync, seeker_cid)


def _approve_application_sync(aid: int, admin_cid: int, note: str = ""):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "UPDATE applications SET status='approved', admin_note=? WHERE app_id=? AND deleted_at IS NULL",
            (note, aid),
        )
        conn.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id, note) VALUES(?,?,?,?)",
            (admin_cid, "approve_app", aid, note),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def approve_application(aid: int, admin_cid: int, note: str = "") -> bool:
    return await _run_db(_approve_application_sync, aid, admin_cid, note)


def _reject_application_sync(aid: int, admin_cid: int, reason: str = ""):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "UPDATE applications SET status='rejected', admin_note=? WHERE app_id=? AND deleted_at IS NULL",
            (reason, aid),
        )
        conn.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id, note) VALUES(?,?,?,?)",
            (admin_cid, "reject_app", aid, reason),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def reject_application(aid: int, admin_cid: int, reason: str = "") -> bool:
    return await _run_db(_reject_application_sync, aid, admin_cid, reason)


def _update_application_by_admin_sync(aid: int, admin_cid: int, **fields):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        app = conn.execute(
            "SELECT status FROM applications WHERE app_id=? AND deleted_at IS NULL",
            (aid,),
        ).fetchone()
        if not app or app["status"] != "pending_admin":
            conn.rollback()
            return False
        cols = [
            c[1] for c in conn.execute("PRAGMA table_info(applications)").fetchall()
        ]
        valid = {k: v for k, v in fields.items() if k in cols}
        set_clause = ", ".join(f"{k}=?" for k in valid)
        conn.execute(
            f"UPDATE applications SET {set_clause} WHERE app_id=? AND deleted_at IS NULL",
            list(valid.values()) + [aid],
        )
        conn.execute(
            "INSERT INTO admin_logs(admin_cid, action, target_id) VALUES(?,?,?)",
            (admin_cid, "edit_app", aid),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def update_application_by_admin(aid: int, admin_cid: int, **fields) -> bool:
    return await _run_db(_update_application_by_admin_sync, aid, admin_cid, **fields)


def _update_application_status_sync(aid: int, status: str):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "UPDATE applications SET status=? WHERE app_id=? AND deleted_at IS NULL",
            (status, aid),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def update_application_status(aid: int, status: str) -> bool:
    return await _run_db(_update_application_status_sync, aid, status)


def _has_applied_sync(job_id: int, seeker_cid: int):
    conn = _c()
    try:
        return bool(
            conn.execute(
                "SELECT 1 FROM applications WHERE job_id=? AND seeker_cid=? AND deleted_at IS NULL",
                (job_id, seeker_cid),
            ).fetchone()
        )
    finally:
        conn.close()


async def has_applied(job_id: int, seeker_cid: int) -> bool:
    return await _run_db(_has_applied_sync, job_id, seeker_cid)


# ==================== BOOKMARKS ====================
def _add_bookmark_sync(user_cid: int, job_id: int):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "INSERT OR IGNORE INTO bookmarks(user_cid, job_id) VALUES(?,?)",
            (user_cid, job_id),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def add_bookmark(user_cid: int, job_id: int) -> bool:
    return await _run_db(_add_bookmark_sync, user_cid, job_id)


def _remove_bookmark_sync(user_cid: int, job_id: int):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "UPDATE bookmarks SET deleted_at=CURRENT_TIMESTAMP WHERE user_cid=? AND job_id=? AND deleted_at IS NULL",
            (user_cid, job_id),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def remove_bookmark(user_cid: int, job_id: int) -> bool:
    return await _run_db(_remove_bookmark_sync, user_cid, job_id)


def _get_bookmarks_sync(user_cid: int):
    conn = _c()
    try:
        rows = conn.execute(
            "SELECT j.* FROM bookmarks b JOIN jobs j ON b.job_id=j.job_id WHERE b.user_cid=? AND b.deleted_at IS NULL AND j.deleted_at IS NULL ORDER BY b.created_at DESC LIMIT 20",
            (user_cid,),
        ).fetchall()
        return to_dict_list(rows)
    finally:
        conn.close()


async def get_bookmarks(user_cid: int):
    return await _run_db(_get_bookmarks_sync, user_cid)


def _is_bookmarked_sync(user_cid: int, job_id: int):
    conn = _c()
    try:
        return bool(
            conn.execute(
                "SELECT 1 FROM bookmarks WHERE user_cid=? AND job_id=? AND deleted_at IS NULL",
                (user_cid, job_id),
            ).fetchone()
        )
    finally:
        conn.close()


async def is_bookmarked(user_cid: int, job_id: int) -> bool:
    return await _run_db(_is_bookmarked_sync, user_cid, job_id)


# ==================== RATINGS ====================
def _add_rating_sync(
    from_cid: int, to_cid: int, job_id: int, score: int, comment: str = ""
):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "INSERT OR REPLACE INTO ratings(from_cid, to_cid, job_id, score, comment) VALUES(?,?,?,?,?)",
            (from_cid, to_cid, job_id, score, comment),
        )
        avg = conn.execute(
            "SELECT AVG(score), COUNT(*) FROM ratings WHERE to_cid=? AND deleted_at IS NULL",
            (to_cid,),
        ).fetchone()
        new_rating = round(avg[0], 1) if avg[0] else 0.0
        new_count = avg[1] if avg[1] else 0
        conn.execute(
            "UPDATE users SET rating=?, rating_count=? WHERE chat_id=? AND deleted_at IS NULL",
            (new_rating, new_count, to_cid),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def add_rating(
    from_cid: int, to_cid: int, job_id: int, score: int, comment: str = ""
) -> bool:
    return await _run_db(_add_rating_sync, from_cid, to_cid, job_id, score, comment)


# ==================== NOTIFICATIONS ====================
def _add_notification_sync(user_cid: int, text: str, message_id: Optional[str] = None):
    if message_id is None:
        message_id = f"{user_cid}_{int(time.time())}_{hash(text) % 1000000}"
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        existing = conn.execute(
            "SELECT notif_id FROM notifications WHERE message_id=? AND deleted_at IS NULL",
            (message_id,),
        ).fetchone()
        if existing:
            conn.commit()
            return True
        conn.execute(
            "INSERT INTO notifications(user_cid, text, message_id) VALUES(?,?,?)",
            (user_cid, text, message_id),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def add_notification(
    user_cid: int, text: str, message_id: Optional[str] = None
) -> bool:
    return await _run_db(_add_notification_sync, user_cid, text, message_id)


def _get_unread_count_sync(user_cid: int):
    conn = _c()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_cid=? AND is_read=0 AND deleted_at IS NULL",
            (user_cid,),
        ).fetchone()[0]
    finally:
        conn.close()


async def get_unread_count(user_cid: int) -> int:
    return await _run_db(_get_unread_count_sync, user_cid)


def _get_notifications_sync(user_cid: int):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        rows = conn.execute(
            "SELECT * FROM notifications WHERE user_cid=? AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 50",
            (user_cid,),
        ).fetchall()
        conn.execute(
            "UPDATE notifications SET is_read=1 WHERE user_cid=? AND deleted_at IS NULL",
            (user_cid,),
        )
        conn.commit()
        return to_dict_list(rows)
    except:
        conn.rollback()
        return []
    finally:
        conn.close()


async def get_notifications(user_cid: int):
    return await _run_db(_get_notifications_sync, user_cid)


# ==================== MATCHING ====================
def _get_matching_seekers_for_job_sync(
    category: str, province: str, city: Optional[str] = None
):
    conn = _c()
    try:
        sql = """SELECT chat_id FROM users WHERE role='job_seeker' AND is_banned=0
                 AND private_mode=0 AND allow_employer_notify=1
                 AND js_categories LIKE ? AND (js_province = ? OR js_cities LIKE ?)"""
        params = [f'%"{category}"%', province, f'%"{province}"%']
        if city:
            sql += " OR js_cities LIKE ?"
            params.append(f'%"{city}"%')
        rows = conn.execute(sql, params).fetchall()
        return to_dict_list(rows)
    finally:
        conn.close()


async def get_matching_seekers_for_job(
    category: str, province: str, city: Optional[str] = None
):
    return await _run_db(_get_matching_seekers_for_job_sync, category, province, city)


def _get_matching_employers_for_seeker_sync(
    categories: List[str], province: str, cities: List[str]
):
    """Get employer chat_ids with active jobs matching any of the seeker's categories + location.
    Uses a single IN query instead of N separate queries."""
    if not categories:
        return []
    conn = _c()
    try:
        placeholders = ",".join(["?"] * len(categories))
        sql = f"""SELECT DISTINCT emp_cid FROM jobs WHERE status='active' AND admin_approved=1
                 AND category IN ({placeholders}) AND (province = ?"""
        params = list(categories) + [province]
        if cities:
            sql += " OR province IN (" + ",".join(["?"] * len(cities)) + ")"
            params += cities
        sql += ")"
        rows = conn.execute(sql, params).fetchall()
        return [r["emp_cid"] for r in rows]
    finally:
        conn.close()


async def get_matching_employers_for_seeker(
    categories: List[str], province: str, cities: List[str]
):
    return await _run_db(
        _get_matching_employers_for_seeker_sync, categories, province, cities
    )


# ==================== MATCH SCORE + MATCHED ====================
def match_score(seeker: Dict, job: Dict) -> int:
    score = 0
    cats = jlist(seeker.get("js_categories", "[]"))
    if job.get("category") in cats:
        score += 40
    cities = jlist(seeker.get("js_cities", "[]"))
    if seeker.get("js_province") == job.get("province"):
        score += 20
    elif job.get("province") in cities:
        score += 15
    exp_order = [
        "بدون سابقه",
        "کمتر از ۱ سال",
        "۱ تا ۳ سال",
        "۳ تا ۵ سال",
        "بیش از ۵ سال",
    ]
    s_exp = seeker.get("js_experience", "")
    j_exp = job.get("experience_need", "")
    if j_exp and j_exp != "none" and s_exp:
        try:
            score += 15 if exp_order.index(s_exp) >= exp_order.index(j_exp) else 5
        except:
            score += 8
    edu_order = ["زیر دیپلم", "دیپلم", "فوق‌دیپلم", "لیسانس", "فوق‌لیسانس", "دکترا"]
    s_edu = seeker.get("js_education", "")
    j_edu = job.get("education_need", "")
    if j_edu and j_edu != "none" and s_edu:
        try:
            score += 10 if edu_order.index(s_edu) >= edu_order.index(j_edu) else 3
        except:
            score += 5
    j_gend = job.get("gender_need", "")
    s_gend = seeker.get("js_gender", "")
    if not j_gend or j_gend == "بدون‌ترجیح" or j_gend == s_gend:
        score += 10
    s_sal = seeker.get("js_salary_min", 0) or 0
    j_sal_max = job.get("salary_max", 0) or 0
    if s_sal == 0 or j_sal_max == 0 or s_sal <= j_sal_max:
        score += 5
    return min(score, 100)


async def get_matched_jobs(seeker_cid: int, limit: int = 10):
    await expire_old_jobs()
    seeker = await get_user(seeker_cid)
    if not seeker:
        return []

    def _run():
        conn = _c()
        try:
            jobs = conn.execute(
                "SELECT * FROM jobs WHERE status='active' AND admin_approved=1 AND deleted_at IS NULL ORDER BY created_at DESC"
            ).fetchall()
            return jobs
        finally:
            conn.close()

    jobs = await _run_db(_run)
    scored = []
    seeker_dict = dict(seeker)
    for job in jobs:
        sc = match_score(seeker_dict, dict(job))
        if sc >= 20:
            scored.append((sc, dict(job)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


async def get_matched_seekers(job_id: int, limit: int = 10):
    job = await get_job(job_id)
    if not job:
        return []

    def _run():
        conn = _c()
        try:
            return conn.execute(
                "SELECT * FROM users WHERE role='job_seeker' AND is_banned=0 AND private_mode=0 AND deleted_at IS NULL LIMIT 500"
            ).fetchall()
        finally:
            conn.close()

    seekers = await _run_db(_run)
    scored = []
    job_dict = dict(job)
    for seeker in seekers:
        sc = match_score(dict(seeker), job_dict)
        if sc >= 20:
            scored.append((sc, dict(seeker)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


# ==================== STATS ====================
def _get_stats_sync():
    conn = _c()
    try:

        def q(sql):
            return conn.execute(sql).fetchone()[0]

        stats = {
            "total": q("SELECT COUNT(*) FROM users WHERE deleted_at IS NULL"),
            "employers": q(
                "SELECT COUNT(*) FROM users WHERE role='employer' AND deleted_at IS NULL"
            ),
            "seekers": q(
                "SELECT COUNT(*) FROM users WHERE role='job_seeker' AND deleted_at IS NULL"
            ),
            "active_jobs": q(
                "SELECT COUNT(*) FROM jobs WHERE status='active' AND deleted_at IS NULL"
            ),
            "pending_jobs": q(
                "SELECT COUNT(*) FROM jobs WHERE status='pending' AND deleted_at IS NULL"
            ),
            "expired_jobs": q(
                "SELECT COUNT(*) FROM jobs WHERE status='expired' AND deleted_at IS NULL"
            ),
            "closed_jobs": q(
                "SELECT COUNT(*) FROM jobs WHERE status='closed' AND deleted_at IS NULL"
            ),
            "total_apps": q(
                "SELECT COUNT(*) FROM applications WHERE deleted_at IS NULL"
            ),
            "pending_apps": q(
                "SELECT COUNT(*) FROM applications WHERE status='pending_admin' AND deleted_at IS NULL"
            ),
            "approved_apps": q(
                "SELECT COUNT(*) FROM applications WHERE status='approved' AND deleted_at IS NULL"
            ),
            "rejected_apps": q(
                "SELECT COUNT(*) FROM applications WHERE status='rejected' AND deleted_at IS NULL"
            ),
            "banned": q(
                "SELECT COUNT(*) FROM users WHERE is_banned=1 AND deleted_at IS NULL"
            ),
            "bookmarks": q("SELECT COUNT(*) FROM bookmarks WHERE deleted_at IS NULL"),
        }
        cats = conn.execute(
            "SELECT category, COUNT(*) as n FROM jobs WHERE status='active' AND deleted_at IS NULL GROUP BY category ORDER BY n DESC LIMIT 5"
        ).fetchall()
        stats["top_cats"] = [(r["category"], r["n"]) for r in cats]
        return stats
    finally:
        conn.close()


async def get_stats():
    return await _run_db(_get_stats_sync)


def _get_admin_logs_sync(limit: int = 20):
    conn = _c()
    try:
        rows = conn.execute(
            "SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return to_dict_list(rows)
    finally:
        conn.close()


async def get_admin_logs(limit: int = 20):
    return await _run_db(_get_admin_logs_sync, limit)


def _add_activity_log_sync(
    user_cid: int, action: str, detail: str = "", result: str = ""
):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "INSERT INTO activity_logs(user_cid, action, detail, result) VALUES(?,?,?,?)",
            (user_cid, action, detail, result),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def add_activity_log(
    user_cid: int, action: str, detail: str = "", result: str = ""
) -> bool:
    return await _run_db(_add_activity_log_sync, user_cid, action, detail, result)


def _get_activity_log_sync(user_cid: int, limit: int = 30):
    conn = _c()
    try:
        rows = conn.execute(
            "SELECT * FROM activity_logs WHERE user_cid=? AND deleted_at IS NULL ORDER BY created_at DESC LIMIT ?",
            (user_cid, limit),
        ).fetchall()
        return to_dict_list(rows)
    finally:
        conn.close()


async def get_activity_log(user_cid: int, limit: int = 30):
    return await _run_db(_get_activity_log_sync, user_cid, limit)


def _save_direct_message_sync(from_cid: int, to_cid: int, job_id: int, text: str):
    conn = _c()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "INSERT INTO direct_messages(from_cid, to_cid, job_id, text) VALUES(?,?,?,?)",
            (from_cid, to_cid, job_id, text),
        )
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()


async def save_direct_message(
    from_cid: int, to_cid: int, job_id: int, text: str
) -> bool:
    return await _run_db(_save_direct_message_sync, from_cid, to_cid, job_id, text)


# ==================== HELPERS (sync, no DB) ====================
def fmt_salary(mn, mx=None) -> str:
    def _f(n):
        if not n or n == 0:
            return None
        try:
            s = str(int(n))
            return ",".join([s[max(0, i - 3) : i] for i in range(len(s), 0, -3)][::-1])
        except:
            return None

    a, b = _f(mn), _f(mx)
    if a and b:
        return f"{a} — {b} تومان"
    if a:
        return f"{a} تومان"
    return "توافقی"


def parse_int(text) -> int:
    if not text:
        return 0
    text = str(text).replace(",", "").replace("،", "").replace("٬", "")
    match = re.search(r"\d+", text)
    return int(match.group()) if match else 0


def stars(rating, count: int = 0) -> str:
    if not rating:
        return "بدون امتیاز"
    full = int(rating)
    s = "⭐" * full + "☆" * (5 - full)
    if count:
        return f"{s} ({rating:.1f} از {count} نظر)"
    return f"{s} ({rating:.1f})"


def jlist(text) -> List:
    """Safely parse JSON string to list. Handles None, str, list/tuple inputs."""
    if text is None:
        return []
    if isinstance(text, (list, tuple)):
        return list(text)
    if isinstance(text, str):
        text = text.strip()
        if not text:
            return []
        try:
            result = json.loads(text)
            return list(result) if isinstance(result, list) else [result]
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def days_since(date_str: str) -> int:
    try:
        from jdatetime import datetime as jdt

        post_date = jdt.strptime(date_str, "%Y/%m/%d")
        return (jdt.now() - post_date).days
    except:
        try:
            post_date = datetime.strptime(date_str, "%Y/%m/%d")
            return (datetime.now() - post_date).days
        except:
            return 0
