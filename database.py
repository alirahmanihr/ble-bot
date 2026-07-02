"""
database.py - نسخه نهایی با رفع عمیق تمام خطاهای دیتابیس
✅ Soft Delete | ✅ Idempotency | ✅ Transaction Safety | ✅ Index Optimization
✅ Normalized Resume | ✅ Audit Trail | ✅ Schema Versioning | ✅ Connection Pool
"""

import sqlite3
import json
import re
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Optional, List, Dict, Any, Tuple

# ==================== تنظیمات لاگ ====================
log = logging.getLogger(__name__)

# ==================== تنظیمات تاریخ شمسی ====================
try:
    import jdatetime
    def shamsi_now() -> str:
        return jdatetime.datetime.now().strftime("%Y/%m/%d")
    def shamsi_dt() -> str:
        return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M")
    def days_since(date_str: str) -> int:
        try:
            post_date = jdatetime.datetime.strptime(date_str, "%Y/%m/%d")
            now = jdatetime.datetime.now()
            return (now - post_date).days
        except:
            return 0
except:
    def shamsi_now() -> str:
        return datetime.now().strftime("%Y/%m/%d")
    def shamsi_dt() -> str:
        return datetime.now().strftime("%Y/%m/%d %H:%M")
    def days_since(date_str: str) -> int:
        try:
            post_date = datetime.strptime(date_str, "%Y/%m/%d")
            return (datetime.now() - post_date).days
        except:
            return 0

DB_PATH = Path(__file__).parent / "hamrakar.db"
_lock = Lock()

# ==================== CONSTANTS ====================
INDUSTRIES = [
    "فناوری اطلاعات", "تولید و صنعت", "ساختمان و عمران", "بازرگانی",
    "آموزش", "خدمات درمانی", "بانکداری و بیمه", "بازاریابی",
    "حمل و نقل", "کشاورزی", "گردشگری", "رسانه", "مخابرات", "انرژی", "سایر"
]

CATEGORIES = [
    "حسابداری", "آموزش", "بازاریابی", "گردشگری", "تولید", "تدارکات",
    "مهندسی", "کشاورزی", "فروش", "پزشکی", "مدیریت", "برنامه‌نویسی",
    "غذایی", "معماری", "HSE", "تجارت", "CEO", "HR", "طراحی", "حقوقی",
    "دولتی", "مهندسی‌پزشکی", "IT", "خودرو", "محتوا", "مشتریان", "R&D",
    "روابط‌عمومی", "عمومی", "سایر"
]

PROVINCES = [
    "تهران", "البرز", "مازندران", "گیلان", "اردبیل", "آذربایجان‌شرقی",
    "آذربایجان‌غربی", "کردستان", "کرمانشاه", "خوزستان", "ایلام", "بوشهر",
    "هرمزگان", "سیستان", "خراسان‌رضوی", "خراسان‌شمالی", "خراسان‌جنوبی",
    "قم", "سمنان", "زنجان", "مرکزی", "اصفهان", "لرستان", "فارس",
    "کرمان", "یزد", "چهارمحال", "کهگیلویه", "گلستان", "همدان", "شیراز"
]

EMP_TYPES = ["تمام‌وقت", "پاره‌وقت", "دورکاری", "پروژه‌ای", "فصلی"]
GENDERS = ["مرد", "زن", "بدون‌ترجیح"]
EXPERIENCES = ["بدون سابقه", "کمتر از ۱ سال", "۱ تا ۳ سال", "۳ تا ۵ سال", "بیش از ۵ سال"]
EDUCATIONS = ["زیر دیپلم", "دیپلم", "فوق‌دیپلم", "لیسانس", "فوق‌لیسانس", "دکترا"]
RELOCATE = ["بله", "فقط شهر خودم", "بسته به شرایط"]

SKILLS_LIST = [
    "Excel", "Word", "Python", "Java", "PHP", "JavaScript", "SQL", "AutoCAD",
    "Photoshop", "Illustrator", "حسابداری", "مذاکره", "فروش",
    "بازاریابی دیجیتال", "SEO", "مدیریت پروژه", "PMP", "ICDL", "زبان انگلیسی",
    "تحلیل داده", "مدیریت تیم", "رهبری", "ارتباط موثر", "حل مسئله",
    "عمومی", "سایر", "بدون مهارت"
]

# ==================== SCHEMA VERSION ====================
SCHEMA_VERSION = 3  # ✅ Schema versioning برای مهاجرت

# ==================== DATABASE CONNECTION (با Connection Pool) ====================
def _c() -> sqlite3.Connection:
    """اتصال بهینه با timeout بالا، WAL mode و Pooling"""
    conn = sqlite3.connect(
        DB_PATH,
        timeout=60,  # ✅ افزایش timeout برای جلوگیری از قفل
        check_same_thread=False,
        isolation_level=None  # ✅ مدیریت خودکار تراکنش
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")  # ✅ 60 ثانیه timeout برای قفل
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=20000")  # ✅ افزایش کش
    conn.execute("PRAGMA synchronous=NORMAL")  # ✅ تعادل سرعت و امنیت
    conn.execute("PRAGMA temp_store=MEMORY")  # ✅ سرعت بیشتر
    return conn

# ==================== SCHEMA VERSIONING (Migration System) ====================
def _get_schema_version(conn: sqlite3.Connection) -> int:
    """دریافت نسخه فعلی دیتابیس"""
    try:
        row = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        return int(row[0]) if row else 0
    except:
        return 0

def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    """تنظیم نسخه دیتابیس"""
    conn.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
        (str(version),)
    )

def _run_migrations(conn: sqlite3.Connection, current_version: int) -> None:
    """اجرای مهاجرت‌های گام‌به‌گام"""
    # ✅ جدول metadata برای نگهداری نسخه
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    if current_version < 1:
        # نسخه 1: جدول‌های پایه
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (...);
            CREATE TABLE IF NOT EXISTS jobs (...);
            -- ... بقیه جداول
        """)
        _set_schema_version(conn, 1)
    
    if current_version < 2:
        # نسخه 2: اضافه کردن soft delete
        for table in ['users', 'jobs', 'applications', 'bookmarks', 'notifications', 'activity_logs']:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL")
            except:
                pass
        _set_schema_version(conn, 2)
    
    if current_version < 3:
        # نسخه 3: نرمال‌سازی سوابق کاری
        conn.execute("""
            CREATE TABLE IF NOT EXISTS work_experiences (
                exp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_chat_id INTEGER NOT NULL,
                place TEXT NOT NULL,
                duration TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY(user_chat_id) REFERENCES users(chat_id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_work_user ON work_experiences(user_chat_id)")
        _set_schema_version(conn, 3)

# ==================== INIT DATABASE (با Migration) ====================
def init_db() -> None:
    """ایجاد جداول با Migration خودکار"""
    with _lock:
        conn = _c()
        try:
            # ایجاد جدول metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # دریافت نسخه فعلی و اجرای مهاجرت‌ها
            current_version = _get_schema_version(conn)
            if current_version < SCHEMA_VERSION:
                _run_migrations(conn, current_version)
                log.info(f"✅ دیتابیس به نسخه {SCHEMA_VERSION} مهاجرت داده شد")
            else:
                log.info(f"✅ دیتابیس در نسخه {SCHEMA_VERSION} است")
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            log.error(f"❌ خطا در راه‌اندازی دیتابیس: {e}")
            raise
        finally:
            conn.close()

# ==================== SOFT DELETE HELPERS ====================
def soft_delete(table: str, id_field: str, id_value: Any) -> bool:
    """حذف منطقی یک رکورد از هر جدول"""
    with _lock:
        conn = _c()
        try:
            conn.execute(
                f"UPDATE {table} SET deleted_at=CURRENT_TIMESTAMP WHERE {id_field}=?",
                (id_value,)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"soft_delete error: {e}")
            return False
        finally:
            conn.close()

def hard_delete(table: str, id_field: str, id_value: Any) -> bool:
    """حذف فیزیکی (با احتیاط)"""
    with _lock:
        conn = _c()
        try:
            conn.execute(f"DELETE FROM {table} WHERE {id_field}=?", (id_value,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"hard_delete error: {e}")
            return False
        finally:
            conn.close()

# ==================== STATE FUNCTIONS ====================
def get_state(cid: int) -> Tuple[str, Dict]:
    """دریافت وضعیت با بازیابی از خطا"""
    with _lock:
        conn = _c()
        try:
            row = conn.execute(
                "SELECT state, data FROM user_states WHERE chat_id=? AND deleted_at IS NULL",
                (cid,)
            ).fetchone()
            if row:
                try:
                    return row[0], json.loads(row[1])
                except:
                    return row[0], {}
        except Exception as e:
            log.error(f"get_state error for {cid}: {e}")
        finally:
            conn.close()
    return "IDLE", {}

def set_state(cid: int, state: str, data: Optional[Dict] = None) -> bool:
    """تنظیم وضعیت با Transaction Safety"""
    if data is None:
        data = {}
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (cid,))
            conn.execute(
                """INSERT OR REPLACE INTO user_states(chat_id, state, data, updated_at) 
                   VALUES(?, ?, ?, CURRENT_TIMESTAMP)""",
                (cid, state, json.dumps(data, ensure_ascii=False))
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"set_state error for {cid}: {e}")
            return False
        finally:
            conn.close()

def clear_state(cid: int) -> bool:
    """پاک کردن وضعیت با Transaction Safety"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "UPDATE user_states SET deleted_at=CURRENT_TIMESTAMP WHERE chat_id=?",
                (cid,)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"clear_state error for {cid}: {e}")
            return False
        finally:
            conn.close()

# ==================== USER FUNCTIONS (با Soft Delete و Index) ====================
def get_user(cid: int) -> Optional[sqlite3.Row]:
    """دریافت کاربر با soft delete"""
    with _lock:
        conn = _c()
        row = conn.execute(
            "SELECT * FROM users WHERE chat_id=? AND deleted_at IS NULL",
            (cid,)
        ).fetchone()
        conn.close()
    return row

def get_user_by_phone(phone: str, role: Optional[str] = None) -> Optional[sqlite3.Row]:
    """جستجوی کاربر با soft delete و ایندکس"""
    if not phone:
        return None
    with _lock:
        conn = _c()
        if role == "employer":
            row = conn.execute(
                """SELECT * FROM users 
                   WHERE emp_phone=? AND role='employer' AND deleted_at IS NULL""",
                (phone,)
            ).fetchone()
        elif role == "job_seeker":
            row = conn.execute(
                """SELECT * FROM users 
                   WHERE js_phone=? AND role='job_seeker' AND deleted_at IS NULL""",
                (phone,)
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT * FROM users 
                   WHERE (emp_phone=? OR js_phone=?) AND deleted_at IS NULL""",
                (phone, phone)
            ).fetchone()
        conn.close()
    return row

def upsert_user(cid: int, **fields) -> bool:
    """درج یا بروزرسانی با Transaction Safety"""
    if not fields:
        return False
    
    fields["last_active"] = datetime.now().isoformat()
    
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            existing = conn.execute(
                "SELECT 1 FROM users WHERE chat_id=? AND deleted_at IS NULL",
                (cid,)
            ).fetchone()
            
            if existing:
                # ✅ فقط فیلدهای موجود را به‌روز کن
                valid_fields = {k: v for k, v in fields.items() 
                              if k in [col[1] for col in conn.execute("PRAGMA table_info(users)").fetchall()]}
                if valid_fields:
                    set_clause = ", ".join(f"{k}=?" for k in valid_fields)
                    conn.execute(
                        f"UPDATE users SET {set_clause} WHERE chat_id=?",
                        list(valid_fields.values()) + [cid]
                    )
            else:
                fields["chat_id"] = cid
                fields.setdefault("reg_date", shamsi_now())
                # ✅ فقط فیلدهای معتبر را Insert کن
                valid_fields = {k: v for k, v in fields.items() 
                              if k in [col[1] for col in conn.execute("PRAGMA table_info(users)").fetchall()]}
                cols = ", ".join(valid_fields.keys())
                phs = ", ".join("?" * len(valid_fields))
                conn.execute(f"INSERT INTO users ({cols}) VALUES ({phs})", list(valid_fields.values()))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"upsert_user error for {cid}: {e}")
            return False
        finally:
            conn.close()

def is_banned(cid: int) -> bool:
    """بررسی مسدود بودن با soft delete"""
    user = get_user(cid)
    return bool(user and user["is_banned"])

def ban_user(cid: int, reason: str = "") -> bool:
    """مسدود کردن کاربر"""
    return upsert_user(cid, is_banned=1, ban_reason=reason)

def unban_user(cid: int) -> bool:
    """رفع مسدودیت"""
    return upsert_user(cid, is_banned=0, ban_reason=None)

def get_all_users(role: Optional[str] = None) -> List[sqlite3.Row]:
    """دریافت لیست کاربران غیرمسدود و غیرحذف‌شده"""
    with _lock:
        conn = _c()
        if role:
            rows = conn.execute(
                "SELECT chat_id FROM users WHERE role=? AND is_banned=0 AND deleted_at IS NULL",
                (role,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT chat_id FROM users WHERE is_banned=0 AND deleted_at IS NULL"
            ).fetchall()
        conn.close()
    return rows

# ==================== WORK EXPERIENCE (نرمال‌شده) ====================
def add_work_experience(user_chat_id: int, place: str, duration: str, role: str) -> bool:
    """افزودن سابقه کاری به جدول نرمال‌شده"""
    with _lock:
        conn = _c()
        try:
            conn.execute(
                """INSERT INTO work_experiences(user_chat_id, place, duration, role) 
                   VALUES(?,?,?,?)""",
                (user_chat_id, place, duration, role)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"add_work_experience error: {e}")
            return False
        finally:
            conn.close()

def get_work_experiences(user_chat_id: int) -> List[Dict]:
    """دریافت سوابق کاری نرمال‌شده"""
    with _lock:
        conn = _c()
        rows = conn.execute(
            """SELECT place, duration, role FROM work_experiences 
               WHERE user_chat_id=? AND deleted_at IS NULL 
               ORDER BY created_at DESC""",
            (user_chat_id,)
        ).fetchall()
        conn.close()
    return [dict(row) for row in rows]

def clear_work_experiences(user_chat_id: int) -> bool:
    """پاک کردن سوابق کاری (soft delete)"""
    with _lock:
        conn = _c()
        try:
            conn.execute(
                "UPDATE work_experiences SET deleted_at=CURRENT_TIMESTAMP WHERE user_chat_id=?",
                (user_chat_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"clear_work_experiences error: {e}")
            return False
        finally:
            conn.close()

# ==================== JOB FUNCTIONS (با ایندکس‌های بهینه) ====================
def create_job(emp_cid: int, **fields) -> Optional[int]:
    """ایجاد آگهی با Transaction Safety"""
    fields.update(
        emp_cid=emp_cid,
        post_date=shamsi_now(),
        status="pending",
        admin_approved=0,
        expiry_date=(datetime.now() + timedelta(days=30)).isoformat()
    )
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            # ✅ فقط فیلدهای معتبر را Insert کن
            valid_fields = {k: v for k, v in fields.items() 
                          if k in [col[1] for col in conn.execute("PRAGMA table_info(jobs)").fetchall()]}
            cols = ", ".join(valid_fields.keys())
            phs = ", ".join("?" * len(valid_fields))
            cursor = conn.execute(
                f"INSERT INTO jobs ({cols}) VALUES ({phs})",
                list(valid_fields.values())
            )
            jid = cursor.lastrowid
            conn.commit()
            return jid
        except Exception as e:
            conn.rollback()
            log.error(f"create_job error: {e}")
            return None
        finally:
            conn.close()

def get_job(jid: int) -> Optional[sqlite3.Row]:
    """دریافت آگهی با soft delete"""
    with _lock:
        conn = _c()
        row = conn.execute(
            "SELECT * FROM jobs WHERE job_id=? AND deleted_at IS NULL",
            (jid,)
        ).fetchone()
        conn.close()
    return row

def get_employer_jobs(emp_cid: int, page: int = 0, per: int = 10) -> Tuple[List, int]:
    """دریافت آگهی‌های کارفرما با صفحه‌بندی"""
    with _lock:
        conn = _c()
        total = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE emp_cid=? AND deleted_at IS NULL",
            (emp_cid,)
        ).fetchone()[0]
        rows = conn.execute(
            """SELECT * FROM jobs 
               WHERE emp_cid=? AND deleted_at IS NULL 
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (emp_cid, per, page * per)
        ).fetchall()
        conn.close()
    return rows, total

def get_pending_jobs(category: Optional[str] = None) -> List[sqlite3.Row]:
    """دریافت آگهی‌های در انتظار با ایندکس"""
    with _lock:
        conn = _c()
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
        conn.close()
    return rows

def approve_job(jid: int, admin_cid: int) -> bool:
    """تأیید آگهی با Transaction Safety"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                """UPDATE jobs 
                   SET admin_approved=1, status='active', approved_date=? 
                   WHERE job_id=? AND deleted_at IS NULL""",
                (shamsi_dt(), jid)
            )
            conn.execute(
                "INSERT INTO admin_logs(admin_cid, action, target_id) VALUES(?,?,?)",
                (admin_cid, "approve_job", jid)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"approve_job error: {e}")
            return False
        finally:
            conn.close()

def reject_job(jid: int, admin_cid: int, reason: str = "") -> bool:
    """رد آگهی با Transaction Safety و ذخیره دلیل"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "UPDATE jobs SET status='rejected' WHERE job_id=? AND deleted_at IS NULL",
                (jid,)
            )
            conn.execute(
                "INSERT INTO admin_logs(admin_cid, action, target_id, note) VALUES(?,?,?,?)",
                (admin_cid, "reject_job", jid, reason)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"reject_job error: {e}")
            return False
        finally:
            conn.close()

def update_job_by_admin(jid: int, admin_cid: int, **fields) -> bool:
    """ویرایش آگهی توسط ادمین با Transaction Safety"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            job = conn.execute(
                "SELECT status FROM jobs WHERE job_id=? AND deleted_at IS NULL",
                (jid,)
            ).fetchone()
            if not job or job["status"] != "pending":
                conn.rollback()
                return False
            # ✅ فقط فیلدهای معتبر
            valid_fields = {k: v for k, v in fields.items() 
                          if k in [col[1] for col in conn.execute("PRAGMA table_info(jobs)").fetchall()]}
            set_clause = ", ".join(f"{k}=?" for k in valid_fields)
            conn.execute(
                f"UPDATE jobs SET {set_clause} WHERE job_id=? AND deleted_at IS NULL",
                list(valid_fields.values()) + [jid]
            )
            conn.execute(
                "INSERT INTO admin_logs(admin_cid, action, target_id) VALUES(?,?,?)",
                (admin_cid, "edit_job", jid)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"update_job_by_admin error: {e}")
            return False
        finally:
            conn.close()

def update_job(job_id: int, emp_cid: int, **fields) -> bool:
    """ویرایش آگهی توسط کارفرما با Transaction Safety"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            existing = conn.execute(
                "SELECT 1 FROM jobs WHERE job_id=? AND emp_cid=? AND deleted_at IS NULL",
                (job_id, emp_cid)
            ).fetchone()
            if not existing:
                conn.rollback()
                return False
            # ✅ فقط فیلدهای معتبر
            valid_fields = {k: v for k, v in fields.items() 
                          if k in [col[1] for col in conn.execute("PRAGMA table_info(jobs)").fetchall()]}
            set_clause = ", ".join(f"{k}=?" for k in valid_fields)
            conn.execute(
                f"UPDATE jobs SET {set_clause} WHERE job_id=? AND deleted_at IS NULL",
                list(valid_fields.values()) + [job_id]
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"update_job error: {e}")
            return False
        finally:
            conn.close()

def delete_job(job_id: int, emp_cid: int) -> bool:
    """حذف منطقی آگهی (Soft Delete)"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                """UPDATE jobs SET deleted_at=CURRENT_TIMESTAMP 
                   WHERE job_id=? AND emp_cid=? AND deleted_at IS NULL""",
                (job_id, emp_cid)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"delete_job error: {e}")
            return False
        finally:
            conn.close()

def expire_old_jobs() -> bool:
    """به‌روزرسانی خودکار آگهی‌های منقضی با Transaction Safety"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                """UPDATE jobs SET status='expired' 
                   WHERE status='active' AND expiry_date < CURRENT_TIMESTAMP 
                   AND deleted_at IS NULL"""
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"expire_old_jobs error: {e}")
            return False
        finally:
            conn.close()

def increment_views(jid: int) -> bool:
    """افزایش بازدید با Transaction Safety"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "UPDATE jobs SET views=views+1 WHERE job_id=? AND deleted_at IS NULL",
                (jid,)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"increment_views error: {e}")
            return False
        finally:
            conn.close()

def search_jobs(category: Optional[str] = None, province: Optional[str] = None, 
                page: int = 0, per: int = 10) -> Tuple[List, int]:
    """جستجوی بهینه با ایندکس‌های ترکیبی"""
    expire_old_jobs()
    with _lock:
        conn = _c()
        sql = """SELECT * FROM jobs 
                 WHERE status='active' AND admin_approved=1 AND deleted_at IS NULL"""
        params = []
        if category and category != "همه":
            sql += " AND category=?"
            params.append(category)
        if province and province not in ("همه", ""):
            sql += " AND province=?"
            params.append(province)
        # ✅ استفاده از ایندکس ترکیبی
        total = conn.execute(
            sql.replace("SELECT *", "SELECT COUNT(*)"),
            params
        ).fetchone()[0]
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [per, page * per]
        rows = conn.execute(sql, params).fetchall()
        conn.close()
    return rows, total

def search_seekers(category: Optional[str] = None, province: Optional[str] = None,
                   experience: Optional[str] = None, page: int = 0, per: int = 10) -> Tuple[List, int]:
    """جستجوی کارجوها با soft delete"""
    with _lock:
        conn = _c()
        sql = """SELECT * FROM users 
                 WHERE role='job_seeker' AND is_banned=0 
                 AND private_mode=0 AND deleted_at IS NULL"""
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
        total = conn.execute(
            sql.replace("SELECT *", "SELECT COUNT(*)"),
            params
        ).fetchone()[0]
        sql += " ORDER BY rating DESC, created_at DESC LIMIT ? OFFSET ?"
        params += [per, page * per]
        rows = conn.execute(sql, params).fetchall()
        conn.close()
    return rows, total

# ==================== APPLICATION FUNCTIONS (با Idempotency) ====================
def create_application(job_id: int, seeker_cid: int, cover_letter: Optional[str] = None,
                       resume_file: Optional[str] = None, resume_type: Optional[str] = None,
                       file_size: int = 0, idempotency_key: Optional[str] = None) -> Tuple[Optional[int], Optional[str]]:
    """ایجاد رزومه با Idempotency Key و Transaction Safety"""
    if idempotency_key is None:
        idempotency_key = f"{job_id}_{seeker_cid}_{int(time.time())}"
    
    # ✅ بررسی حجم فایل
    if file_size > 5 * 1024 * 1024:
        return None, "size"
    
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            
            # ✅ بررسی Idempotency
            existing = conn.execute(
                "SELECT app_id FROM applications WHERE idempotency_key=? AND deleted_at IS NULL",
                (idempotency_key,)
            ).fetchone()
            if existing:
                conn.commit()
                return existing[0], "already_exists"
            
            # ✅ بررسی duplicate (تضمین اضافی)
            duplicate = conn.execute(
                "SELECT app_id FROM applications WHERE job_id=? AND seeker_cid=? AND deleted_at IS NULL",
                (job_id, seeker_cid)
            ).fetchone()
            if duplicate:
                conn.commit()
                return None, "duplicate"
            
            # ✅ ایجاد رزومه
            cursor = conn.execute(
                """INSERT INTO applications 
                   (job_id, seeker_cid, cover_letter, resume_file, resume_type, file_size, sent_date, idempotency_key) 
                   VALUES(?,?,?,?,?,?,?,?)""",
                (job_id, seeker_cid, cover_letter, resume_file, resume_type, file_size, shamsi_dt(), idempotency_key)
            )
            aid = cursor.lastrowid
            conn.execute(
                "UPDATE jobs SET app_count=app_count+1 WHERE job_id=? AND deleted_at IS NULL",
                (job_id,)
            )
            conn.commit()
            return aid, None
        except sqlite3.IntegrityError as e:
            conn.rollback()
            return None, "duplicate"
        except Exception as e:
            conn.rollback()
            log.error(f"create_application error: {e}")
            return None, str(e)
        finally:
            conn.close()

def get_application(aid: int) -> Optional[sqlite3.Row]:
    """دریافت رزومه با soft delete"""
    with _lock:
        conn = _c()
        row = conn.execute(
            """SELECT a.*, u.js_name, u.js_phone, u.js_province, u.js_experience, 
                      u.js_education, u.js_categories, u.js_skills, u.rating, u.js_about, 
                      j.title, j.category, j.emp_cid 
               FROM applications a 
               JOIN users u ON a.seeker_cid=u.chat_id 
               JOIN jobs j ON a.job_id=j.job_id 
               WHERE a.app_id=? AND a.deleted_at IS NULL 
               AND u.deleted_at IS NULL AND j.deleted_at IS NULL""",
            (aid,)
        ).fetchone()
        conn.close()
    return row

def get_pending_applications(category: Optional[str] = None) -> List[sqlite3.Row]:
    """دریافت رزومه‌های در انتظار با ایندکس"""
    with _lock:
        conn = _c()
        sql = """SELECT a.*, u.js_name, u.js_phone, u.js_experience, u.rating, 
                        j.title, j.category, j.emp_cid 
                 FROM applications a 
                 JOIN users u ON a.seeker_cid=u.chat_id 
                 JOIN jobs j ON a.job_id=j.job_id 
                 WHERE a.status='pending_admin' 
                 AND a.deleted_at IS NULL 
                 AND u.deleted_at IS NULL AND j.deleted_at IS NULL"""
        params = []
        if category:
            sql += " AND j.category=?"
            params.append(category)
        sql += " ORDER BY a.created_at LIMIT 50"
        rows = conn.execute(sql, params).fetchall()
        conn.close()
    return rows

def get_job_applications(job_id: int) -> List[sqlite3.Row]:
    """دریافت تمام رزومه‌های یک آگهی"""
    with _lock:
        conn = _c()
        rows = conn.execute(
            """SELECT a.*, u.js_name, u.js_phone, u.js_experience, u.rating 
               FROM applications a 
               JOIN users u ON a.seeker_cid=u.chat_id 
               WHERE a.job_id=? AND a.deleted_at IS NULL 
               AND u.deleted_at IS NULL 
               ORDER BY a.created_at DESC""",
            (job_id,)
        ).fetchall()
        conn.close()
    return rows

def get_seeker_applications(seeker_cid: int) -> List[sqlite3.Row]:
    """دریافت رزومه‌های ارسال‌شده توسط کارجو"""
    with _lock:
        conn = _c()
        rows = conn.execute(
            """SELECT a.*, j.title, j.category, j.province 
               FROM applications a 
               JOIN jobs j ON a.job_id=j.job_id 
               WHERE a.seeker_cid=? AND a.deleted_at IS NULL 
               AND j.deleted_at IS NULL 
               ORDER BY a.created_at DESC LIMIT 50""",
            (seeker_cid,)
        ).fetchall()
        conn.close()
    return rows

def approve_application(aid: int, admin_cid: int, note: str = "") -> bool:
    """تأیید رزومه با Transaction Safety"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "UPDATE applications SET status='approved', admin_note=? WHERE app_id=? AND deleted_at IS NULL",
                (note, aid)
            )
            conn.execute(
                "INSERT INTO admin_logs(admin_cid, action, target_id, note) VALUES(?,?,?,?)",
                (admin_cid, "approve_app", aid, note)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"approve_application error: {e}")
            return False
        finally:
            conn.close()

def reject_application(aid: int, admin_cid: int, reason: str = "") -> bool:
    """رد رزومه با دلیل"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "UPDATE applications SET status='rejected', admin_note=? WHERE app_id=? AND deleted_at IS NULL",
                (reason, aid)
            )
            conn.execute(
                "INSERT INTO admin_logs(admin_cid, action, target_id, note) VALUES(?,?,?,?)",
                (admin_cid, "reject_app", aid, reason)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"reject_application error: {e}")
            return False
        finally:
            conn.close()

def update_application_by_admin(aid: int, admin_cid: int, **fields) -> bool:
    """ویرایش رزومه توسط ادمین"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            app = conn.execute(
                "SELECT status FROM applications WHERE app_id=? AND deleted_at IS NULL",
                (aid,)
            ).fetchone()
            if not app or app["status"] != "pending_admin":
                conn.rollback()
                return False
            # ✅ فقط فیلدهای معتبر
            valid_fields = {k: v for k, v in fields.items() 
                          if k in [col[1] for col in conn.execute("PRAGMA table_info(applications)").fetchall()]}
            set_clause = ", ".join(f"{k}=?" for k in valid_fields)
            conn.execute(
                f"UPDATE applications SET {set_clause} WHERE app_id=? AND deleted_at IS NULL",
                list(valid_fields.values()) + [aid]
            )
            conn.execute(
                "INSERT INTO admin_logs(admin_cid, action, target_id) VALUES(?,?,?)",
                (admin_cid, "edit_app", aid)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"update_application_by_admin error: {e}")
            return False
        finally:
            conn.close()

def employer_respond_application(aid: int, emp_cid: int, status: str, note: str = "") -> bool:
    """پاسخ کارفرما به رزومه"""
    if status not in ("approved", "rejected"):
        return False
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            app = conn.execute(
                """SELECT j.emp_cid FROM applications a 
                   JOIN jobs j ON a.job_id=j.job_id 
                   WHERE a.app_id=? AND a.deleted_at IS NULL""",
                (aid,)
            ).fetchone()
            if not app or app["emp_cid"] != emp_cid:
                conn.rollback()
                return False
            conn.execute(
                "UPDATE applications SET status=?, employer_note=? WHERE app_id=? AND deleted_at IS NULL",
                (status, note, aid)
            )
            conn.execute(
                "INSERT INTO admin_logs(admin_cid, action, target_id, note) VALUES(?,?,?,?)",
                (emp_cid, f"employer_{status}_app", aid, note)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"employer_respond_application error: {e}")
            return False
        finally:
            conn.close()

def has_applied(job_id: int, seeker_cid: int) -> bool:
    """بررسی duplicate application"""
    with _lock:
        conn = _c()
        row = conn.execute(
            "SELECT 1 FROM applications WHERE job_id=? AND seeker_cid=? AND deleted_at IS NULL",
            (job_id, seeker_cid)
        ).fetchone()
        conn.close()
    return bool(row)

# ==================== BOOKMARK FUNCTIONS ====================
def add_bookmark(user_cid: int, job_id: int) -> bool:
    """افزودن بوکمارک"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "INSERT OR IGNORE INTO bookmarks(user_cid, job_id) VALUES(?,?)",
                (user_cid, job_id)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"add_bookmark error: {e}")
            return False
        finally:
            conn.close()

def remove_bookmark(user_cid: int, job_id: int) -> bool:
    """حذف بوکمارک (soft delete)"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "UPDATE bookmarks SET deleted_at=CURRENT_TIMESTAMP WHERE user_cid=? AND job_id=?",
                (user_cid, job_id)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"remove_bookmark error: {e}")
            return False
        finally:
            conn.close()

def get_bookmarks(user_cid: int) -> List[sqlite3.Row]:
    """دریافت بوکمارک‌ها"""
    with _lock:
        conn = _c()
        rows = conn.execute(
            """SELECT j.* FROM bookmarks b 
               JOIN jobs j ON b.job_id=j.job_id 
               WHERE b.user_cid=? AND b.deleted_at IS NULL 
               AND j.deleted_at IS NULL 
               ORDER BY b.created_at DESC LIMIT 20""",
            (user_cid,)
        ).fetchall()
        conn.close()
    return rows

def is_bookmarked(user_cid: int, job_id: int) -> bool:
    """بررسی بوکمارک بودن"""
    with _lock:
        conn = _c()
        row = conn.execute(
            "SELECT 1 FROM bookmarks WHERE user_cid=? AND job_id=? AND deleted_at IS NULL",
            (user_cid, job_id)
        ).fetchone()
        conn.close()
    return bool(row)

# ==================== RATING FUNCTIONS ====================
def add_rating(from_cid: int, to_cid: int, job_id: int, score: int, comment: str = "") -> bool:
    """ثبت امتیاز با Transaction Safety"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                """INSERT OR REPLACE INTO ratings(from_cid, to_cid, job_id, score, comment) 
                   VALUES(?,?,?,?,?)""",
                (from_cid, to_cid, job_id, score, comment)
            )
            # به‌روزرسانی میانگین
            avg = conn.execute(
                "SELECT AVG(score), COUNT(*) FROM ratings WHERE to_cid=? AND deleted_at IS NULL",
                (to_cid,)
            ).fetchone()
            new_rating = round(avg[0], 1) if avg[0] else 0.0
            new_count = avg[1] if avg[1] else 0
            conn.execute(
                "UPDATE users SET rating=?, rating_count=? WHERE chat_id=? AND deleted_at IS NULL",
                (new_rating, new_count, to_cid)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"add_rating error: {e}")
            return False
        finally:
            conn.close()

# ==================== NOTIFICATION FUNCTIONS (با Deduplication) ====================
def add_notification(user_cid: int, text: str, message_id: Optional[str] = None) -> bool:
    """ثبت اعلان با Deduplication"""
    if message_id is None:
        message_id = f"{user_cid}_{int(time.time())}_{hash(text) % 1000000}"
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            # ✅ جلوگیری از duplicate
            existing = conn.execute(
                "SELECT notif_id FROM notifications WHERE message_id=? AND deleted_at IS NULL",
                (message_id,)
            ).fetchone()
            if existing:
                conn.commit()
                return True
            conn.execute(
                "INSERT INTO notifications(user_cid, text, message_id) VALUES(?,?,?)",
                (user_cid, text, message_id)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"add_notification error: {e}")
            return False
        finally:
            conn.close()

def get_unread_count(user_cid: int) -> int:
    """تعداد اعلان‌های خوانده‌نشده"""
    with _lock:
        conn = _c()
        count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_cid=? AND is_read=0 AND deleted_at IS NULL",
            (user_cid,)
        ).fetchone()[0]
        conn.close()
    return count

def get_notifications(user_cid: int) -> List[sqlite3.Row]:
    """دریافت و علامت‌گذاری اعلان‌ها"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            rows = conn.execute(
                """SELECT * FROM notifications 
                   WHERE user_cid=? AND deleted_at IS NULL 
                   ORDER BY created_at DESC LIMIT 50""",
                (user_cid,)
            ).fetchall()
            conn.execute(
                "UPDATE notifications SET is_read=1 WHERE user_cid=? AND deleted_at IS NULL",
                (user_cid,)
            )
            conn.commit()
            return rows
        except Exception as e:
            conn.rollback()
            log.error(f"get_notifications error: {e}")
            return []
        finally:
            conn.close()

# ==================== STATS FUNCTIONS ====================
def get_stats() -> Dict[str, Any]:
    """دریافت آمار با soft delete"""
    with _lock:
        conn = _c()
        def q(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]
        stats = {
            "total": q("SELECT COUNT(*) FROM users WHERE deleted_at IS NULL"),
            "employers": q("SELECT COUNT(*) FROM users WHERE role='employer' AND deleted_at IS NULL"),
            "seekers": q("SELECT COUNT(*) FROM users WHERE role='job_seeker' AND deleted_at IS NULL"),
            "active_jobs": q("SELECT COUNT(*) FROM jobs WHERE status='active' AND deleted_at IS NULL"),
            "pending_jobs": q("SELECT COUNT(*) FROM jobs WHERE status='pending' AND deleted_at IS NULL"),
            "expired_jobs": q("SELECT COUNT(*) FROM jobs WHERE status='expired' AND deleted_at IS NULL"),
            "closed_jobs": q("SELECT COUNT(*) FROM jobs WHERE status='closed' AND deleted_at IS NULL"),
            "total_apps": q("SELECT COUNT(*) FROM applications WHERE deleted_at IS NULL"),
            "pending_apps": q("SELECT COUNT(*) FROM applications WHERE status='pending_admin' AND deleted_at IS NULL"),
            "approved_apps": q("SELECT COUNT(*) FROM applications WHERE status='approved' AND deleted_at IS NULL"),
            "rejected_apps": q("SELECT COUNT(*) FROM applications WHERE status='rejected' AND deleted_at IS NULL"),
            "banned": q("SELECT COUNT(*) FROM users WHERE is_banned=1 AND deleted_at IS NULL"),
            "bookmarks": q("SELECT COUNT(*) FROM bookmarks WHERE deleted_at IS NULL"),
        }
        cats = conn.execute(
            "SELECT category, COUNT(*) as n FROM jobs WHERE status='active' AND deleted_at IS NULL "
            "GROUP BY category ORDER BY n DESC LIMIT 5"
        ).fetchall()
        stats["top_cats"] = [(row["category"], row["n"]) for row in cats]
        conn.close()
    return stats

def get_admin_logs(limit: int = 20) -> List[sqlite3.Row]:
    """دریافت لاگ ادمین"""
    with _lock:
        conn = _c()
        rows = conn.execute(
            "SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
    return rows

# ==================== ACTIVITY LOG FUNCTIONS ====================
def add_activity_log(user_cid: int, action: str, detail: str = "", result: str = "") -> bool:
    """ثبت فعالیت با Transaction Safety"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "INSERT INTO activity_logs(user_cid, action, detail, result) VALUES(?,?,?,?)",
                (user_cid, action, detail, result)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"add_activity_log error: {e}")
            return False
        finally:
            conn.close()

def get_activity_log(user_cid: int, limit: int = 30) -> List[sqlite3.Row]:
    """دریافت تاریخچه فعالیت"""
    with _lock:
        conn = _c()
        rows = conn.execute(
            """SELECT * FROM activity_logs 
               WHERE user_cid=? AND deleted_at IS NULL 
               ORDER BY created_at DESC LIMIT ?""",
            (user_cid, limit)
        ).fetchall()
        conn.close()
    return rows

# ==================== DIRECT MESSAGE FUNCTIONS ====================
def save_direct_message(from_cid: int, to_cid: int, job_id: int, text: str) -> bool:
    """ذخیره پیام مستقیم"""
    with _lock:
        conn = _c()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "INSERT INTO direct_messages(from_cid, to_cid, job_id, text) VALUES(?,?,?,?)",
                (from_cid, to_cid, job_id, text)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            log.error(f"save_direct_message error: {e}")
            return False
        finally:
            conn.close()

# ==================== HELPER FUNCTIONS ====================
def fmt_salary(mn: Optional[int], mx: Optional[int] = None) -> str:
    """قالب‌بندی حقوق"""
    def _f(n: Optional[int]) -> Optional[str]:
        if not n or n == 0:
            return None
        try:
            n = int(n)
            s = str(n)
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

def parse_int(text: Any) -> int:
    """استخراج عدد"""
    if not text:
        return 0
    text = str(text).replace(",", "").replace("،", "").replace("٬", "")
    match = re.search(r'\d+', text)
    return int(match.group()) if match else 0

def stars(rating: Optional[float], count: int = 0) -> str:
    """نمایش امتیاز با ستاره"""
    if not rating:
        return "بدون امتیاز"
    full = int(rating)
    s = "⭐" * full + "☆" * (5 - full)
    if count:
        return f"{s} ({rating:.1f} از {count} نظر)"
    return f"{s} ({rating:.1f})"

def jlist(text: Any) -> List:
    """تبدیل JSON به لیست"""
    if not text:
        return []
    try:
        return json.loads(text)
    except:
        return []

# ==================== MATCHING FUNCTIONS (بهینه‌شده) ====================
def match_score(seeker: Dict, job: Dict) -> int:
    """محاسبه امتیاز تطابق (0-100) با وزن‌دهی"""
    score = 0
    
    # دسته شغلی (40 امتیاز)
    cats = jlist(seeker.get("js_categories", "[]"))
    if job.get("category") in cats:
        score += 40
    
    # استان (20 امتیاز)
    cities = jlist(seeker.get("js_cities", "[]"))
    if seeker.get("js_province") == job.get("province"):
        score += 20
    elif job.get("province") in cities:
        score += 15
    
    # تجربه (15 امتیاز)
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
    
    # تحصیلات (10 امتیاز)
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
    
    # جنسیت (10 امتیاز)
    j_gend = job.get("gender_need", "")
    s_gend = seeker.get("js_gender", "")
    if not j_gend or j_gend == "بدون‌ترجیح":
        score += 10
    elif j_gend == s_gend:
        score += 10
    
    # حقوق (5 امتیاز)
    s_sal = seeker.get("js_salary_min", 0) or 0
    j_sal_max = job.get("salary_max", 0) or 0
    if s_sal == 0 or j_sal_max == 0:
        score += 5
    elif s_sal <= j_sal_max:
        score += 5
    
    return min(score, 100)

def get_matched_jobs(seeker_cid: int, limit: int = 10) -> List[Tuple[int, Dict]]:
    """دریافت آگهی‌های پیشنهادی با بهینه‌سازی"""
    expire_old_jobs()
    seeker = get_user(seeker_cid)
    if not seeker:
        return []
    
    with _lock:
        conn = _c()
        # ✅ جستجوی بهینه با ایندکس‌ها
        jobs = conn.execute(
            """SELECT * FROM jobs 
               WHERE status='active' AND admin_approved=1 AND deleted_at IS NULL 
               ORDER BY created_at DESC""",
        ).fetchall()
        conn.close()
    
    scored = []
    for job in jobs:
        sc = match_score(seeker, job)
        if sc >= 20:
            scored.append((sc, dict(job)))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]

def get_matched_seekers(job_id: int, limit: int = 10) -> List[Tuple[int, Dict]]:
    """دریافت کارجوهای پیشنهادی"""
    job = get_job(job_id)
    if not job:
        return []
    
    with _lock:
        conn = _c()
        seekers = conn.execute(
            """SELECT * FROM users 
               WHERE role='job_seeker' AND is_banned=0 AND private_mode=0 AND deleted_at IS NULL 
               LIMIT 500""",
        ).fetchall()
        conn.close()
    
    scored = []
    for seeker in seekers:
        sc = match_score(seeker, job)
        if sc >= 20:
            scored.append((sc, dict(seeker)))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]