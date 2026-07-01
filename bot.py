"""
ربات کاریابی همراکار - نسخه تولیدی نهایی (کامل)
"""

import asyncio
import json
import logging
import re
import aiohttp
from logging.handlers import RotatingFileHandler

import bale_api as api
import database as db
from config import TOKEN, ADMIN_IDS, CHANNEL_1, CHANNEL_2, BOT_NAME, SLOGAN, SLOGAN_EMP, THANKS
from database import (
    INDUSTRIES, CATEGORIES, PROVINCES, EMP_TYPES,
    GENDERS, EXPERIENCES, EDUCATIONS, RELOCATE, SKILLS_LIST,
    fmt_salary, parse_int, stars, jlist, shamsi_dt,
    add_activity_log, get_activity_log, get_matching_seekers_for_job,
    get_matching_employers_for_seeker
)
from bale_api import (
    inline, reply_kb, remove_kb, paginate,
    msg_text, msg_doc, msg_photo, msg_uid, msg_cid,
    cb_uid, cb_cid, cb_mid
)

# ==================== تنظیمات لاگ ====================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler("hamrakar.log", maxBytes=5*1024*1024,
                            backupCount=3, encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# ==================== STATE CONSTANTS ====================
IDLE = "IDLE"
ER_NAME, ER_COMPANY, ER_INDUSTRY, ER_PHONE, ER_POSITION = "ER_NAME","ER_COMPANY","ER_INDUSTRY","ER_PHONE","ER_POSITION"
ER_ADDRESS, ER_EMAIL, ER_WEBSITE = "ER_ADDRESS","ER_EMAIL","ER_WEBSITE"
JS_NAME, JS_PHONE = "JS_NAME","JS_PHONE"
JS_PROV, JS_JOB, JS_EXP, JS_EDU = "JS_PROV","JS_JOB","JS_EXP","JS_EDU"
JS_SAL, JS_DOB, JS_GEND, JS_RELOC = "JS_SAL","JS_DOB","JS_GEND","JS_RELOC"
JS_CITIES, JS_CATS, JS_SKILLS, JS_ABOUT = "JS_CITIES","JS_CATS","JS_SKILLS","JS_ABOUT"
JS_ALLOW_NOTIFY = "JS_ALLOW_NOTIFY"
JOB_TITLE, JOB_TYPE, JOB_PROV, JOB_CITY = "JOB_TITLE","JOB_TYPE","JOB_PROV","JOB_CITY"
JOB_SAL, JOB_CAT, JOB_GEND, JOB_EDU, JOB_EXP, JOB_DESC = "JOB_SAL","JOB_CAT","JOB_GEND","JOB_EDU","JOB_EXP","JOB_DESC"
SRCH_CAT, SRCH_PROV = "SRCH_CAT","SRCH_PROV"
SRCH_SK_CAT, SRCH_SK_PROV = "SRCH_SK_CAT","SRCH_SK_PROV"
RES_JOB, RES_LETTER = "RES_JOB","RES_LETTER"
RES_EXP_Q, RES_EXP_PLACE, RES_EXP_DURATION, RES_EXP_ROLE, RES_EXP_AGAIN = "RES_EXP_Q","RES_EXP_PLACE","RES_EXP_DURATION","RES_EXP_ROLE","RES_EXP_AGAIN"
ADM_REJ_JOB, ADM_REJ_APP = "ADM_REJ_JOB","ADM_REJ_APP"
ADM_EDIT_JOB, ADM_EDIT_APP = "ADM_EDIT_JOB","ADM_EDIT_APP"
ADM_BROADCAST, ADM_BAN_ID = "ADM_BROADCAST","ADM_BAN_ID"
DM_STATE = "DM_WRITE"
EDIT_EMP_FIELD = "EDIT_EMP_FIELD"
EDIT_JS_FIELD = "EDIT_JS_FIELD"
EDIT_JOB_FIELD = "EDIT_JOB_FIELD"
BROADCAST_TARGET = "BROADCAST_TARGET"
JS_PROFILE_DONE = "JS_PROFILE_DONE"
EMP_PROFILE_DONE = "EMP_PROFILE_DONE"

# ==================== MENU TEXTS ====================
MENU_TEXTS = {
    "📝 ثبت آگهی", "📋 آگهی‌های من", "🔎 جستجوی کارجو", "📬 درخواست‌های رزومه",
    "✏️ ویرایش پروفایل", "👤 پروفایل", "🔄 تغییر نقش", "❓ راهنما",
    "🔍 جستجوی آگهی", "📄 ارسال رزومه", "📊 درخواست‌های من",
    "🔖 آگهی‌های ذخیره‌شده", "📋 تاریخچه فعالیت", "🔔 اعلان‌ها",
    "📋 تأیید آگهی", "📬 تأیید رزومه", "📊 آمار کامل",
    "📢 پیام همگانی", "🚫 مدیریت کاربران", "📑 لاگ ادمین", "🔙 منو",
    "🔙 بازگشت", "🔙 بازگشت به منو",
}

# ==================== MENUS ====================
def emp_menu():
    return reply_kb([
        ["📝 ثبت آگهی", "📋 آگهی‌های من"],
        ["🔎 جستجوی کارجو", "📬 درخواست‌های رزومه"],
        ["✏️ ویرایش پروفایل", "👤 پروفایل"],
        ["🔄 تغییر نقش", "❓ راهنما"],
    ])

def js_menu():
    return reply_kb([
        ["🔍 جستجوی آگهی", "📊 درخواست‌های من"],
        ["🔖 آگهی‌های ذخیره‌شده", "🔔 اعلان‌ها"],
        ["📋 تاریخچه فعالیت", "✏️ ویرایش پروفایل"],
        ["👤 پروفایل", "🔄 تغییر نقش"],
        ["❓ راهنما"],
    ])

def adm_menu():
    return reply_kb([
        ["📋 تأیید آگهی", "📬 تأیید رزومه"],
        ["📊 آمار کامل", "🔔 اعلان‌ها"],
        ["📢 پیام همگانی", "🚫 مدیریت کاربران"],
        ["📑 لاگ ادمین", "🔙 منو"],
    ])

def menu_for(user):
    if not user or not user["role"]:
        return remove_kb()
    if user["chat_id"] in ADMIN_IDS:
        return adm_menu()
    return emp_menu() if user["role"] == "employer" else js_menu()

async def show_menu(s, cid, user, msg=""):
    if not user:
        await do_welcome(s, cid)
        return
    notifs = db.get_unread_count(cid)
    role_map = {"employer": "کارفرما", "job_seeker": "کارجو"}
    r = "ادمین" if cid in ADMIN_IDS else role_map.get(user["role"], "—")
    t = f"🏠 *{BOT_NAME}*\n👤 {r}"
    if notifs:
        t += f" | 🔔 {notifs} اعلان"
    if msg:
        t += f"\n\n{msg}"
    await api.send_message(s, cid, t, menu_for(user))

async def notify_admins(s, text, kb=None):
    for aid in ADMIN_IDS:
        try:
            await api.send_message(s, aid, text, kb)
            await asyncio.sleep(0.05)
        except Exception as e:
            log.warning(f"notify_admin {aid}: {e}")

# ==================== DISPATCH ====================
async def process(s, upd):
    if "message" in upd:
        await on_msg(s, upd["message"])
    elif "callback_query" in upd:
        await on_cb(s, upd["callback_query"])

# ==================== MESSAGE HANDLER ====================
async def on_msg(s, msg):
    cid = msg_cid(msg)
    text = msg_text(msg)
    doc = msg_doc(msg)
    photos = msg_photo(msg)

    if db.is_banned(cid):
        await api.send_message(s, cid, "🚫 حساب شما مسدود است.")
        return

    state, data = db.get_state(cid)

    if text in ("🔙 بازگشت", "🔙 بازگشت به منو", "🔙 منو"):
        db.clear_state(cid)
        user = db.get_user(cid)
        if user and user["role"]:
            await show_menu(s, cid, user)
        else:
            await do_welcome(s, cid)
        return

    if text.startswith("/"):
        await handle_cmd(s, cid, text, data)
        return

    if text in MENU_TEXTS:
        db.clear_state(cid)
        await handle_menu_btn(s, cid, text)
        return

    await handle_state(s, cid, state, data, text, doc, photos)

async def handle_cmd(s, cid, text, data):
    cmd = text.split()[0].lower()
    args = text.split()[1:] if len(text.split()) > 1 else []

    if cmd == "/start":
        await cmd_start(s, cid)
        return
    if cmd == "/menu":
        await cmd_menu(s, cid)
        return
    if cmd == "/profile":
        await cmd_profile(s, cid)
        return
    if cmd == "/help":
        await cmd_help(s, cid)
        return

    if cid not in ADMIN_IDS:
        return

    if cmd == "/stats":
        await cmd_stats(s, cid)
        return
    if cmd == "/ban" and args:
        uid = int(args[0]) if args[0].isdigit() else 0
        reason = " ".join(args[1:]) if len(args) > 1 else ""
        if uid:
            db.ban_user(uid, reason)
            await api.send_message(s, cid, f"🚫 {uid} بن شد")
    if cmd == "/unban" and args:
        uid = int(args[0]) if args[0].isdigit() else 0
        if uid:
            db.unban_user(uid)
            await api.send_message(s, cid, f"✅ {uid} آزاد شد")
    if cmd == "/info" and args:
        uid = int(args[0]) if args[0].isdigit() else 0
        if uid:
            u = db.get_user(uid)
            if u:
                await api.send_message(s, cid,
                    f"👤 *اطلاعات کاربر {uid}*\n\n"
                    f"نقش: {u['role']}\n"
                    f"بن: {'بله' if u['is_banned'] else 'خیر'}\n"
                    f"عضویت: {u['reg_date']}\n"
                    f"آخرین فعالیت: {str(u['last_active'])[:16]}")
            else:
                await api.send_message(s, cid, "❌ یافت نشد")

async def handle_menu_btn(s, cid, text):
    m = {
        "📝 ثبت آگهی": lambda: start_job(s, cid),
        "📋 آگهی‌های من": lambda: my_jobs(s, cid),
        "🔎 جستجوی کارجو": lambda: start_search_seeker(s, cid),
        "📬 درخواست‌های رزومه": lambda: emp_received(s, cid),
        "✏️ ویرایش پروفایل": lambda: (
            edit_emp_menu(s, cid) if db.get_user(cid) and db.get_user(cid)["role"] == "employer"
            else edit_js_menu(s, cid)
        ),
        "👤 پروفایل": lambda: cmd_profile(s, cid),
        "🔄 تغییر نقش": lambda: start_changerole(s, cid),
        "❓ راهنما": lambda: cmd_help(s, cid),
        "🔍 جستجوی آگهی": lambda: start_search(s, cid),
        "📄 ارسال رزومه": lambda: start_resume(s, cid),
        "📊 درخواست‌های من": lambda: my_apps(s, cid),
        "🔖 آگهی‌های ذخیره‌شده": lambda: my_bookmarks(s, cid),
        "🔔 اعلان‌ها": lambda: my_notifs(s, cid),
        "📋 تاریخچه فعالیت": lambda: activity_log(s, cid),
        "📋 تأیید آگهی": lambda: adm_jobs(s, cid),
        "📬 تأیید رزومه": lambda: adm_apps(s, cid),
        "📊 آمار کامل": lambda: cmd_stats(s, cid),
        "📢 پیام همگانی": lambda: start_broadcast(s, cid),
        "🚫 مدیریت کاربران": lambda: adm_users(s, cid),
        "📑 لاگ ادمین": lambda: adm_logs(s, cid),
        "🔙 منو": lambda: cmd_menu(s, cid),
    }
    if text in m:
        await m[text]()
    else:
        await api.send_message(s, cid, "❌ این دکمه هنوز فعال نشده است.")

async def handle_state(s, cid, state, data, text, doc, photos):
    if state == ER_NAME:
        if len(text) < 2:
            await api.send_message(s, cid, "❌ حداقل ۲ کاراکتر")
            return
        data["emp_name"] = text
        db.set_state(cid, ER_COMPANY, data)
        await api.send_message(s, cid, "🏢 نام شرکت:", reply_kb([["🔙 بازگشت"]]))

    elif state == ER_COMPANY:
        data["emp_company"] = text
        db.set_state(cid, ER_INDUSTRY, data)
        await api.send_message(s, cid, "🏭 صنعت شرکت:", paginate(INDUSTRIES, [], "ind", 0, cols=1))

    elif state == ER_PHONE:
        phone = text.replace(" ", "")
        if not re.search(r'09\d{9}', phone):
            await api.send_message(s, cid, "❌ شماره موبایل معتبر وارد کنید (مثال: 09123456789)")
            return
        existing = db.get_user_by_phone(phone, role="employer")
        if existing and existing["chat_id"] != cid:
            await api.send_message(s, cid, "❌ این شماره تماس قبلاً برای یک کارفرمای دیگر ثبت شده است.")
            return
        data["emp_phone"] = phone
        db.set_state(cid, ER_POSITION, data)
        await api.send_message(s, cid, "💼 سمت شغلی خود را وارد کنید:", reply_kb([["🔙 بازگشت"]]))

    elif state == ER_POSITION:
        await save_emp_basic(s, cid, text)

    elif state == ER_ADDRESS:
        data["emp_address"] = "" if text == "0" else text
        db.set_state(cid, ER_EMAIL, data)
        await api.send_message(s, cid, "📧 ایمیل (اختیاری - 0 برای رد):", reply_kb([["🔙 بازگشت"]]))

    elif state == ER_EMAIL:
        data["emp_email"] = "" if text == "0" else text
        db.set_state(cid, ER_WEBSITE, data)
        await api.send_message(s, cid, "🌐 وب‌سایت (اختیاری - 0 برای رد):", reply_kb([["🔙 بازگشت"]]))

    elif state == ER_WEBSITE:
        data["emp_website"] = "" if text == "0" else text
        db.set_state(cid, EMP_PROFILE_DONE, data)
        await api.send_message(s, cid,
            "✅ اطلاعات شما ثبت شد.\nبرای تکمیل پروفایل دکمه زیر را بزنید:",
            inline([[("✅ تکمیل پروفایل", "emp_profile_done")]]))

    elif state == JS_NAME:
        if len(text) < 2:
            await api.send_message(s, cid, "❌ حداقل ۲ کاراکتر")
            return
        data["js_name"] = text
        db.set_state(cid, JS_PHONE, data)
        await api.send_message(s, cid, "📞 شماره موبایل:", reply_kb([["🔙 بازگشت"]]))

    elif state == JS_PHONE:
        phone = text.replace(" ", "")
        if not re.search(r'09\d{9}', phone):
            await api.send_message(s, cid, "❌ شماره موبایل معتبر وارد کنید")
            return
        existing = db.get_user_by_phone(phone, role="job_seeker")
        if existing and existing["chat_id"] != cid:
            await api.send_message(s, cid, "❌ این شماره تماس قبلاً برای یک کارجوی دیگر ثبت شده است.")
            return
        db.upsert_user(cid, role="job_seeker", js_name=data.get("js_name"), js_phone=phone)
        db.clear_state(cid)
        user = db.get_user(cid)
        add_activity_log(cid, "ثبت‌نام", "ثبت‌نام به‌عنوان کارجو")
        await api.send_message(s, cid,
            f"🎉 *ثبت‌نام با موفقیت انجام شد!*\n\n{SLOGAN}\n\n"
            f"⏱ ثبت اطلاعات شما کمتر از 1 دقیقه زمان می‌برد.\n\n"
            f"برای تکمیل پروفایل مراحل بعدی را طی کنید:")
        db.set_state(cid, JS_PROV)
        await api.send_message(s, cid, "🗺 استان:", paginate(PROVINCES, [], "prov", 0, cols=2))
        return

    elif state == JS_JOB:
        data["js_job_title"] = text
        db.set_state(cid, JS_EXP, data)
        await api.send_message(s, cid, "📆 سطح تجربه:", inline([[(e, f"jsexp:{e}")] for e in EXPERIENCES]))

    elif state == JS_SAL:
        data["js_salary_min"] = parse_int(text)
        db.set_state(cid, JS_DOB, data)
        await api.send_message(s, cid, "📅 تاریخ تولد (مثال: ۱۳۷۵/۰۳/۱۵ یا سن ۲۵):", reply_kb([["🔙 بازگشت"]]))

    elif state == JS_DOB:
        data["js_dob"] = text
        db.set_state(cid, JS_GEND, data)
        await api.send_message(s, cid, "👥 جنسیت:", inline([[(g, f"jsgend:{g}")] for g in GENDERS]))

    elif state == JS_ABOUT:
        data["js_about"] = "" if text == "0" else text
        db.set_state(cid, JS_PROFILE_DONE, data)
        await api.send_message(s, cid,
            "✅ اطلاعات شما ثبت شد.\nبرای تکمیل پروفایل دکمه زیر را بزنید:",
            inline([[("✅ تکمیل پروفایل", "js_profile_done")]]))

    elif state == JOB_TITLE:
        if len(text) < 2:
            await api.send_message(s, cid, "❌ حداقل ۲ کاراکتر")
            return
        data["job_title"] = text
        db.set_state(cid, JOB_TYPE, data)
        await api.send_message(s, cid, "🤝 نوع همکاری:", inline([[(t, f"jtype:{t}")] for t in EMP_TYPES]))

    elif state == JOB_CITY:
        data["job_city"] = "" if text == "0" else text
        db.set_state(cid, JOB_SAL, data)
        await api.send_message(s, cid,
            "💰 حقوق پیشنهادی:\n"
            "• بازه: 5000000-8000000\n"
            "• ثابت: 5000000\n"
            "• 0 برای توافقی:",
            reply_kb([["🔙 بازگشت"]]))

    elif state == JOB_SAL:
        parts = re.findall(r'\d+', text.replace(",", ""))
        if len(parts) >= 2:
            data["job_salary_min"] = int(parts[0])
            data["job_salary_max"] = int(parts[1])
        elif len(parts) == 1:
            data["job_salary_min"] = int(parts[0])
            data["job_salary_max"] = 0
        else:
            data["job_salary_min"] = 0
            data["job_salary_max"] = 0
        db.set_state(cid, JOB_CAT, data)
        await api.send_message(s, cid, "🏷 دسته شغلی:", paginate(CATEGORIES, [], "cat", 0))

    elif state == JOB_DESC:
        data["job_desc"] = "" if text == "0" else text
        await finalize_job(s, cid, data)

    elif state == SRCH_PROV:
        await do_search(s, cid, data)

    elif state == SRCH_SK_PROV:
        await do_search_seeker(s, cid, data)

    elif state == RES_JOB:
        try:
            jid = int(text)
            job = db.get_job(jid)
            if job and job["status"] == "active" and job["admin_approved"]:
                if db.has_applied(jid, cid):
                    await api.send_message(s, cid, "⚠️ قبلاً برای این آگهی رزومه ارسال کرده‌اید")
                    return
                db.increment_views(jid)
                data["target_job_id"] = jid
                db.set_state(cid, RES_LETTER, data)
                await api.send_message(s, cid,
                    f"💼 *{job['title']}*\n"
                    f"🏷 {job['category']} | 🗺 {job['province'] or '—'}\n"
                    f"💰 {fmt_salary(job['salary_min'], job['salary_max'])}\n\n"
                    f"📝 معرفی کوتاه بنویسید (یا 0 برای رد):",
                    reply_kb([["🔙 بازگشت"]]))
            else:
                await api.send_message(s, cid, "❌ آگهی یافت نشد یا فعال نیست")
        except:
            await api.send_message(s, cid, "❌ شماره صحیح وارد کنید")

    elif state == RES_LETTER:
        data["cover_letter"] = "" if text == "0" else text
        db.set_state(cid, RES_EXP_Q, data)
        await api.send_message(s, cid,
            "📋 *سابقه کاری*\n\nآیا سابقه‌کاری دارید؟",
            inline([[("✅ بله", "exp_yes"), ("❌ خیر", "exp_no")]]))

    elif state == RES_EXP_PLACE:
        data["exp_place"] = text
        db.set_state(cid, RES_EXP_DURATION, data)
        await api.send_message(s, cid, "⏱ مدت زمان (مثلاً: ۲ سال):", reply_kb([["🔙 بازگشت"]]))

    elif state == RES_EXP_DURATION:
        data["exp_duration"] = text
        db.set_state(cid, RES_EXP_ROLE, data)
        await api.send_message(s, cid, "💼 سمت شغلی خود را وارد کنید:", reply_kb([["🔙 بازگشت"]]))

    elif state == RES_EXP_ROLE:
        data["exp_role"] = text
        exp_list = data.get("exp_list", [])
        exp_list.append({
            "place": data.get("exp_place"),
            "duration": data.get("exp_duration"),
            "role": text
        })
        data["exp_list"] = exp_list
        db.set_state(cid, RES_EXP_AGAIN, data)
        await api.send_message(s, cid,
            "✅ سابقه کاری اضافه شد.\nآیا سابقه‌ی دیگری دارید؟",
            inline([[("✅ بله، اضافه کن", "exp_again_yes"), ("❌ خیر، تمام شد", "exp_again_no")]]))

    elif state == ADM_REJ_JOB:
        jid = data.get("reject_job_id")
        if jid:
            db.reject_job(jid, cid, text)
            job = db.get_job(jid)
            add_activity_log(job["emp_cid"], "نتیجه آگهی", job["title"], "رد شد")
            try:
                await api.send_message(s, job["emp_cid"],
                    f"❌ *آگهی رد شد*\n\n💼 {job['title']}\n\n📝 دلیل: {text}")
            except:
                pass
        db.clear_state(cid)
        await api.send_message(s, cid, "✅ آگهی رد شد")
        await adm_jobs(s, cid)

    elif state == ADM_REJ_APP:
        aid = data.get("reject_app_id")
        if aid:
            app = db.get_application(aid)
            db.reject_application(aid, cid, text)
            add_activity_log(app["seeker_cid"], "نتیجه رزومه", app["title"], f"رد شد: {text}")
            try:
                await api.send_message(s, app["seeker_cid"],
                    f"❌ *رزومه رد شد*\n\n💼 {app['title']}\n\n📝 دلیل: {text}")
            except:
                pass
        db.clear_state(cid)
        await api.send_message(s, cid, "✅ رزومه رد شد")
        await adm_apps(s, cid)

    elif state == ADM_EDIT_JOB:
        jid = data.get("edit_job_id")
        field = data.get("edit_field")
        if jid and field:
            db.update_job_by_admin(jid, cid, **{field: text})
            add_activity_log(cid, "ویرایش آگهی توسط ادمین", f"آگهی {jid}", f"تغییر {field}")
            db.clear_state(cid)
            await api.send_message(s, cid, f"✅ آگهی بروزرسانی شد")
            await adm_jobs(s, cid)

    elif state == ADM_EDIT_APP:
        aid = data.get("edit_app_id")
        field = data.get("edit_field")
        if aid and field:
            db.update_application_by_admin(aid, cid, **{field: text})
            add_activity_log(cid, "ویرایش رزومه توسط ادمین", f"رزومه {aid}", f"تغییر {field}")
            db.clear_state(cid)
            await api.send_message(s, cid, f"✅ رزومه بروزرسانی شد")
            await adm_apps(s, cid)

    elif state == ADM_BROADCAST:
        if cid not in ADMIN_IDS:
            return
        target = data.get("broadcast_target", "all")
        if target == "employer":
            users = db.get_all_users(role="employer")
        elif target == "job_seeker":
            users = db.get_all_users(role="job_seeker")
        else:
            users = db.get_all_users()
        await api.send_message(s, cid, f"📢 ارسال به {len(users)} کاربر...")
        ok = 0
        fail = 0
        for row in users:
            try:
                await api.send_message(s, row["chat_id"], text)
                db.add_notification(row["chat_id"], f"📢 پیام همگانی: {text}")
                ok += 1
                await asyncio.sleep(0.05)
            except:
                fail += 1
        db.clear_state(cid)
        await api.send_message(s, cid, f"✅ ارسال شد: {ok}\n❌ خطا: {fail}")

    elif state == ADM_BAN_ID:
        if cid not in ADMIN_IDS:
            return
        if text.isdigit():
            db.ban_user(int(text))
            await api.send_message(s, cid, f"🚫 کاربر {text} بن شد")
        db.clear_state(cid)

    else:
        handled = await handle_extended_state(s, cid, state, data, text)
        if not handled:
            user = db.get_user(cid)
            if user and user["role"]:
                await show_menu(s, cid, user)
            else:
                await do_welcome(s, cid)

# ==================== CALLBACK HANDLER ====================
async def on_cb(s, cb):
    cid = cb_cid(cb)
    d = cb.get("data", "")
    mid = cb_mid(cb)
    cbid = cb["id"]
    await api.answer_cb(s, cbid)

    if db.is_banned(cid):
        return

    state, data = db.get_state(cid)

    if d.startswith("role:"):
        role = d.replace("role:", "")
        db.upsert_user(cid, role=role)
        if role == "employer":
            db.set_state(cid, ER_NAME)
            await api.send_message(s, cid,
                "✅ *کارفرما انتخاب شد*\n\n"
                "👤 نام و نام خانوادگی خود را وارد کنید:\n"
                "⏱ ثبت اطلاعات شما کمتر از 1 دقیقه زمان می‌برد.",
                reply_kb([["🔙 بازگشت"]]))
        else:
            db.set_state(cid, JS_NAME)
            await api.send_message(s, cid,
                "✅ *کارجو انتخاب شد*\n\n"
                "👤 نام و نام خانوادگی خود را وارد کنید:\n"
                "⏱ ثبت اطلاعات شما کمتر از 1 دقیقه زمان می‌برد.",
                reply_kb([["🔙 بازگشت"]]))
        return

    if d == "joined:ok":
        user = db.get_user(cid)
        if user and user["role"]:
            await show_menu(s, cid, user, "✅ خوش آمدید!")
        else:
            await do_welcome(s, cid)
        return

    if d == "skip_channel":
        db.clear_state(cid)
        user = db.get_user(cid)
        if user and user["role"]:
            await show_menu(s, cid, user)
        else:
            await do_welcome(s, cid)
        return

    if d.startswith("ind:"):
        val = d.replace("ind:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_ip"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(INDUSTRIES, [], "ind", p, cols=1))
            return
        if val == "DONE":
            if not data.get("emp_industry"):
                await api.answer_cb(s, cbid, "یک صنعت انتخاب کنید!", True)
                return
            db.set_state(cid, ER_PHONE, data)
            await api.send_message(s, cid, "📞 شماره موبایل:", reply_kb([["🔙 بازگشت"]]))
            return
        data["emp_industry"] = val
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(INDUSTRIES, [val], "ind", data.get("_ip", 0), cols=1))
        return

    if d == "emp_profile_done":
        _, data = db.get_state(cid)
        await save_emp_profile(s, cid, data)
        return

    if d == "js_profile_done":
        _, data = db.get_state(cid)
        await save_seeker_profile(s, cid, data)
        return

    if d.startswith("prov:"):
        val = d.replace("prov:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_pp"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [], "prov", p, cols=2))
            return
        if val == "DONE":
            if not data.get("js_province"):
                await api.answer_cb(s, cbid, "یک استان انتخاب کنید!", True)
                return
            db.set_state(cid, JS_JOB, data)
            await api.send_message(s, cid, "💼 شغل مورد نظر:", reply_kb([["🔙 بازگشت"]]))
            return
        data["js_province"] = val
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [val], "prov", data.get("_pp", 0), cols=2))
        return

    if d.startswith("jscity:"):
        val = d.replace("jscity:", "")
        sel = data.get("js_cities", [])
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_jcity"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, sel, "jscity", p, cols=2))
            return
        if val == "DONE":
            db.set_state(cid, JS_CATS, data)
            await api.send_message(s, cid, "🏷 دسته‌های شغلی (حداکثر ۳):", paginate(CATEGORIES, [], "jscat", 0))
            return
        if val in sel:
            sel.remove(val)
        else:
            sel.append(val)
        data["js_cities"] = sel
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, sel, "jscity", data.get("_jcity", 0), cols=2))
        return

    if d.startswith("jscat:"):
        val = d.replace("jscat:", "")
        sel = data.get("js_categories", [])
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_jsc"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, sel, "jscat", p))
            return
        if val == "DONE":
            if not sel:
                await api.answer_cb(s, cbid, "حداقل ۱ دسته!", True)
                return
            db.set_state(cid, JS_SKILLS, data)
            await api.send_message(s, cid, "🛠 مهارت‌ها (حداکثر ۱۰):", paginate(SKILLS_LIST, [], "skill", 0))
            return
        if val in sel:
            sel.remove(val)
        elif len(sel) < 3:
            sel.append(val)
        else:
            await api.answer_cb(s, cbid, "حداکثر ۳ دسته!", True)
            return
        data["js_categories"] = sel
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, sel, "jscat", data.get("_jsc", 0)))
        return

    if d.startswith("skill:"):
        val = d.replace("skill:", "")
        sel = data.get("js_skills", [])
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_sk"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(SKILLS_LIST, sel, "skill", p))
            return
        if val.startswith("ADD:"):
            new_skill = val.replace("ADD:", "").strip()
            if new_skill and new_skill not in sel and len(sel) < 10:
                sel.append(new_skill)
                if new_skill not in SKILLS_LIST:
                    SKILLS_LIST.append(new_skill)
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(SKILLS_LIST, sel, "skill", data.get("_sk", 0)))
            return
        if val == "DONE":
            db.set_state(cid, JS_ALLOW_NOTIFY, data)
            await api.send_message(s, cid,
                "📢 *اجازه ارسال به کارفرماها*\n\n"
                "آیا موافقید اطلاعات شما برای کارفرماهایی که در حوزه‌ی شغلی شما فعال هستند، ارسال شود؟",
                inline([[("✅ بله، موافقم", "allow_notify_yes"), ("❌ خیر، مخالفم", "allow_notify_no")]]))
            return
        if val in sel:
            sel.remove(val)
        elif len(sel) < 10:
            sel.append(val)
        else:
            await api.answer_cb(s, cbid, "حداکثر ۱۰ مهارت!", True)
            return
        data["js_skills"] = sel
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(SKILLS_LIST, sel, "skill", data.get("_sk", 0)))
        return

    if d == "allow_notify_yes":
        data["allow_employer_notify"] = 1
        db.set_state(cid, JS_ABOUT, data)
        await api.send_message(s, cid, "📝 درباره خودتان بنویسید (اختیاری - 0 برای رد):", reply_kb([["🔙 بازگشت"]]))
        return

    if d == "allow_notify_no":
        data["allow_employer_notify"] = 0
        db.set_state(cid, JS_ABOUT, data)
        await api.send_message(s, cid, "📝 درباره خودتان بنویسید (اختیاری - 0 برای رد):", reply_kb([["🔙 بازگشت"]]))
        return

    if d.startswith("jsgend:"):
        data["js_gender"] = d.replace("jsgend:", "")
        db.set_state(cid, JS_RELOC, data)
        await api.send_message(s, cid, "✈️ آمادگی جابجایی:", inline([[(r, f"jsreloc:{r}")] for r in RELOCATE]))
        return

    if d.startswith("jsreloc:"):
        data["js_relocate"] = d.replace("jsreloc:", "")
        db.set_state(cid, JS_CITIES, data)
        await api.send_message(s, cid, "🗺 شهرهای کاری:", paginate(PROVINCES, data.get("js_cities", []), "jscity", 0, cols=2))
        return

    if d.startswith("jsexp:"):
        data["js_experience"] = d.replace("jsexp:", "")
        db.set_state(cid, JS_EDU, data)
        await api.send_message(s, cid, "🎓 تحصیلات:", inline([[(e, f"jsedu:{e}")] for e in EDUCATIONS]))
        return

    if d.startswith("jsedu:"):
        data["js_education"] = d.replace("jsedu:", "")
        db.set_state(cid, JS_SAL, data)
        await api.send_message(s, cid, "💰 حقوق مورد انتظار (یا 0 برای توافقی):", reply_kb([["🔙 بازگشت"]]))
        return

    if d.startswith("jtype:"):
        data["job_emp_type"] = d.replace("jtype:", "")
        db.set_state(cid, JOB_PROV, data)
        await api.send_message(s, cid, "🗺 استان:", paginate(PROVINCES, [], "jprov", 0, cols=2))
        return

    if d.startswith("jprov:"):
        val = d.replace("jprov:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_jp"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [], "jprov", p, cols=2))
            return
        if val == "DONE":
            if not data.get("job_province"):
                await api.answer_cb(s, cbid, "یک استان انتخاب کنید!", True)
                return
            db.set_state(cid, JOB_CITY, data)
            await api.send_message(s, cid, "🏙 شهر (یا 0):", reply_kb([["🔙 بازگشت"]]))
            return
        data["job_province"] = val
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [val], "jprov", data.get("_jp", 0), cols=2))
        return

    if d.startswith("cat:"):
        val = d.replace("cat:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_jc"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [], "cat", p))
            return
        if val == "DONE":
            if not data.get("job_category"):
                await api.answer_cb(s, cbid, "یک دسته انتخاب کنید!", True)
                return
            db.set_state(cid, JOB_GEND, data)
            await api.send_message(s, cid, "👥 جنسیت مورد نیاز:", inline([[(g, f"jgend:{g}")] for g in GENDERS]))
            return
        data["job_category"] = val
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [val], "cat", data.get("_jc", 0)))
        return

    if d.startswith("jgend:"):
        data["job_gender"] = d.replace("jgend:", "")
        db.set_state(cid, JOB_EDU, data)
        await api.send_message(s, cid, "🎓 تحصیلات مورد نیاز:", inline([[(e, f"jedu:{e}")] for e in EDUCATIONS] + [[("بدون شرط", "jedu:none")]]))
        return

    if d.startswith("jedu:"):
        data["job_education"] = d.replace("jedu:", "")
        db.set_state(cid, JOB_EXP, data)
        await api.send_message(s, cid, "📆 تجربه مورد نیاز:", inline([[(e, f"jexp:{e}")] for e in EXPERIENCES] + [[("بدون شرط", "jexp:none")]]))
        return

    if d.startswith("jexp:"):
        data["job_experience"] = d.replace("jexp:", "")
        db.set_state(cid, JOB_DESC, data)
        await api.send_message(s, cid, "📝 توضیحات آگهی (یا 0 برای رد):", reply_kb([["🔙 بازگشت"]]))
        return

    if d.startswith("scat:"):
        val = d.replace("scat:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_sc"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [], "scat", p))
            return
        if val == "DONE":
            db.set_state(cid, SRCH_PROV, data)
            await api.send_message(s, cid, "🗺 استان:", paginate(PROVINCES, [], "sprov", 0, cols=2))
            return
        data["search_category"] = val
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [val], "scat", data.get("_sc", 0)))
        return

    if d.startswith("sprov:"):
        val = d.replace("sprov:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_sp"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [], "sprov", p, cols=2))
            return
        if val == "DONE":
            await do_search(s, cid, data)
            return
        data["search_province"] = val
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [val], "sprov", data.get("_sp", 0), cols=2))
        return

    if d.startswith("skcat:"):
        val = d.replace("skcat:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_skc"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [], "skcat", p))
            return
        if val == "DONE":
            db.set_state(cid, SRCH_SK_PROV, data)
            await api.send_message(s, cid, "🗺 استان:", paginate(PROVINCES, [], "skprov", 0, cols=2))
            return
        data["sk_category"] = val
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [val], "skcat", data.get("_skc", 0)))
        return

    if d.startswith("skprov:"):
        val = d.replace("skprov:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            data["_skp"] = p
            db.set_state(cid, state, data)
            await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [], "skprov", p, cols=2))
            return
        if val == "DONE":
            await do_search_seeker(s, cid, data)
            return
        data["sk_province"] = val
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [val], "skprov", data.get("_skp", 0), cols=2))
        return

    if d.startswith("applyjob:"):
        jid = int(d.split(":")[1])
        job = db.get_job(jid)
        user = db.get_user(cid)
        if not job or job["status"] != "active":
            await api.send_message(s, cid, "❌ آگهی نامعتبر")
            return
        if not user or user["role"] != "job_seeker":
            await api.send_message(s, cid, "⛔ فقط کارجو می‌تواند رزومه ارسال کند")
            return
        if db.has_applied(jid, cid):
            await api.send_message(s, cid, "⚠️ قبلاً برای این آگهی رزومه ارسال کرده‌اید")
            return
        db.increment_views(jid)
        db.set_state(cid, RES_LETTER, {"target_job_id": jid})
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n\n📝 معرفی کوتاه (یا 0 برای رد):",
            reply_kb([["🔙 بازگشت"]]))
        return

    if d == "exp_yes":
        db.set_state(cid, RES_EXP_PLACE, data)
        await api.send_message(s, cid, "🏢 محل کار:", reply_kb([["🔙 بازگشت"]]))
        return

    if d == "exp_no":
        await finalize_application(s, cid, data)
        return

    if d == "exp_again_yes":
        db.set_state(cid, RES_EXP_PLACE, data)
        await api.send_message(s, cid, "🏢 محل کار بعدی:", reply_kb([["🔙 بازگشت"]]))
        return

    if d == "exp_again_no":
        await finalize_application(s, cid, data)
        return

    if d.startswith("bookmark:"):
        jid = int(d.split(":")[1])
        if db.is_bookmarked(cid, jid):
            db.remove_bookmark(cid, jid)
            await api.answer_cb(s, cbid, "🔖 از ذخیره‌ها حذف شد")
        else:
            db.add_bookmark(cid, jid)
            add_activity_log(cid, "ذخیره آگهی", f"ذخیره آگهی {jid}")
            await api.answer_cb(s, cbid, "🔖 ذخیره شد!")
        return

    if d.startswith("viewseeker:"):
        sk_cid = int(d.split(":")[1])
        seeker = db.get_user(sk_cid)
        if not seeker:
            await api.send_message(s, cid, "❌ یافت نشد")
            return
        cats = jlist(seeker["js_categories"])
        skills = jlist(seeker["js_skills"])
        cities = jlist(seeker["js_cities"])
        exp_list = jlist(seeker.get("work_experience", "[]"))
        exp_text = ""
        if exp_list:
            exp_text = "\n📋 *سوابق کاری:*\n"
            for i, exp in enumerate(exp_list, 1):
                exp_text += f"{i}. {exp.get('place', '—')} | {exp.get('duration', '—')} | {exp.get('role', '—')}\n"
        await api.send_message(s, cid,
            f"👤 *{seeker['js_name']}*\n"
            f"📞 {seeker['js_phone']}\n"
            f"🗺 {seeker['js_province'] or '—'}\n"
            f"💼 {seeker['js_job_title'] or '—'}\n"
            f"📆 {seeker['js_experience'] or '—'}\n"
            f"🎓 {seeker['js_education'] or '—'}\n"
            f"💰 {fmt_salary(seeker['js_salary_min'])}\n"
            f"✈️ {seeker['js_relocate'] or '—'}\n"
            f"🏷 {', '.join(cats) or '—'}\n"
            f"🛠 {', '.join(skills[:8]) or '—'}\n"
            f"🗺 {', '.join(cities[:3]) or '—'}\n"
            f"📝 {seeker['js_about'] or '—'}\n"
            f"{exp_text}"
            f"⭐ {stars(seeker['rating'], seeker['rating_count'])}")
        return

    if d.startswith("admjob:"):
        jid = int(d.split(":")[1])
        db.approve_job(jid, cid)
        job = db.get_job(jid)
        add_activity_log(job["emp_cid"], "نتیجه آگهی", job["title"], "تأیید شد")
        await api.send_message(s, cid, f"✅ آگهی *{job['title']}* تأیید شد")
        try:
            hashtag = f"#{job['category'].replace(' ', '')}"
            msg_to_emp = f"✅ *آگهی تأیید شد!*\n\n💼 {job['title']}\n\n{SLOGAN_EMP}\n\n{hashtag}"
            await api.send_message(s, job["emp_cid"], msg_to_emp)
            channel_text = (
                f"📢 *آگهی جدید*\n\n"
                f"💼 {job['title']}\n"
                f"🏷 {job['category']}\n"
                f"💰 {fmt_salary(job['salary_min'], job['salary_max'])}\n"
                f"🗺 {job['province'] or '—'}\n"
                f"🤝 {job['emp_type'] or '—'}\n"
                f"📅 {job['post_date']}\n\n"
                f"{hashtag}"
            )
            await api.send_message(s, CHANNEL_1, channel_text)
            await api.send_message(s, CHANNEL_2, channel_text)
        except Exception as e:
            log.error(f"انتشار در کانال: {e}")
        asyncio.create_task(_notify_seekers_job(s, dict(job)))
        await adm_jobs(s, cid)
        return

    if d.startswith("admreject:"):
        jid = int(d.split(":")[1])
        db.set_state(cid, ADM_REJ_JOB, {"reject_job_id": jid})
        await api.send_message(s, cid, "✍️ دلیل رد آگهی:", reply_kb([["🔙 بازگشت"]]))
        return

    if d.startswith("adm_edit_job:"):
        parts = d.split(":")
        jid = int(parts[1])
        field = parts[2]
        db.set_state(cid, ADM_EDIT_JOB, {"edit_job_id": jid, "edit_field": field})
        labels = {
            "title": "عنوان جدید",
            "category": "دسته جدید",
            "province": "استان جدید",
            "city": "شهر جدید",
            "salary_min": "حقوق پایه",
            "salary_max": "حقوق حداکثر"
        }
        await api.send_message(s, cid, f"✏️ {labels.get(field, field)} را وارد کنید:", reply_kb([["🔙 بازگشت"]]))
        return

    if d.startswith("admapp:"):
        parts = d.split(":")
        aid = int(parts[1])
        note = parts[2] if len(parts) > 2 else ""
        db.approve_application(aid, cid, note)
        app = db.get_application(aid)
        add_activity_log(app["seeker_cid"], "نتیجه رزومه", app["title"], "تأیید شد")
        await api.send_message(s, cid, f"✅ رزومه تأیید شد")
        try:
            await api.send_message(s, app["seeker_cid"],
                f"✅ *{THANKS}*\n\n"
                f"رزومه شما برای آگهی *{app['title']}* تأیید شد!\n"
                f"📝 نظر ادمین: {note if note else 'بدون نظر'}")
            seeker = db.get_user(app["seeker_cid"])
            cats = jlist(seeker["js_categories"])
            skills = jlist(seeker["js_skills"])
            exp_list = jlist(seeker.get("work_experience", "[]"))
            exp_text = ""
            if exp_list:
                exp_text = "\n📋 سوابق کاری:\n"
                for exp in exp_list[:3]:
                    exp_text += f"• {exp.get('place', '—')} ({exp.get('duration', '—')}) - {exp.get('role', '—')}\n"
            emp_text = (
                f"📬 *رزومه جدید دریافت شد!*\n\n"
                f"💼 آگهی: {app['title']}\n\n"
                f"👤 {seeker['js_name']}\n"
                f"📞 {seeker['js_phone']}\n"
                f"🗺 {seeker['js_province'] or '—'}\n"
                f"📆 {seeker['js_experience'] or '—'}\n"
                f"🎓 {seeker['js_education'] or '—'}\n"
                f"💰 {fmt_salary(seeker['js_salary_min'])}\n"
                f"🏷 {', '.join(cats) or '—'}\n"
                f"🛠 {', '.join(skills[:5]) or '—'}\n"
                f"{exp_text}"
                f"⭐ {stars(seeker['rating'], seeker['rating_count'])}"
            )
            if app.get("cover_letter"):
                emp_text += f"\n\n📝 معرفی: {app['cover_letter']}"
            await api.send_message(s, app["emp_cid"], emp_text,
                inline([
                    [("👤 پروفایل کامل", f"viewseeker:{app['seeker_cid']}")],
                    [("⭐ امتیاز دهید", f"rate_seeker:{app['seeker_cid']}:{app['job_id']}")]
                ]))
        except Exception as e:
            log.error(f"admapp send: {e}")
        await adm_apps(s, cid)
        return

    if d.startswith("admrejectapp:"):
        aid = int(d.split(":")[1])
        db.set_state(cid, ADM_REJ_APP, {"reject_app_id": aid})
        await api.send_message(s, cid, "✍️ دلیل رد رزومه:", reply_kb([["🔙 بازگشت"]]))
        return

    if d.startswith("adm_edit_app:"):
        parts = d.split(":")
        aid = int(parts[1])
        field = parts[2]
        db.set_state(cid, ADM_EDIT_APP, {"edit_app_id": aid, "edit_field": field})
        labels = {
            "cover_letter": "معرفی جدید",
            "resume_file": "فایل جدید (file_id)"
        }
        await api.send_message(s, cid, f"✏️ {labels.get(field, field)} را وارد کنید:", reply_kb([["🔙 بازگشت"]]))
        return

    if d.startswith("myjobs:"):
        page = int(d.split(":")[1])
        await my_jobs(s, cid, page)
        return

    if d == "cr:yes":
        user = db.get_user(cid)
        if not user:
            await api.send_message(s, cid, "❌ ابتدا ثبت‌نام کنید: /start")
            return
        old = user["role"]
        new = "job_seeker" if old == "employer" else "employer"
        if new == "employer" and user["emp_name"] and user["emp_phone"]:
            db.upsert_user(cid, role=new)
            db.clear_state(cid)
            add_activity_log(cid, "تغییر نقش", f"تغییر به کارفرما")
            await show_menu(s, cid, user, "✅ نقش شما با موفقیت به کارفرما تغییر کرد!")
            return
        elif new == "job_seeker" and user["js_name"] and user["js_phone"]:
            db.upsert_user(cid, role=new)
            db.clear_state(cid)
            add_activity_log(cid, "تغییر نقش", f"تغییر به کارجو")
            await show_menu(s, cid, user, "✅ نقش شما با موفقیت به کارجو تغییر کرد!")
            return
        else:
            db.upsert_user(cid, role=new)
            db.clear_state(cid)
            if new == "employer":
                db.set_state(cid, ER_NAME)
                await api.send_message(s, cid,
                    "✅ *کارفرما انتخاب شد*\n\n"
                    "👤 نام و نام خانوادگی خود را وارد کنید:\n"
                    "⏱ ثبت اطلاعات شما کمتر از 1 دقیقه زمان می‌برد.",
                    reply_kb([["🔙 بازگشت"]]))
            else:
                db.set_state(cid, JS_NAME)
                await api.send_message(s, cid,
                    "✅ *کارجو انتخاب شد*\n\n"
                    "👤 نام و نام خانوادگی خود را وارد کنید:\n"
                    "⏱ ثبت اطلاعات شما کمتر از 1 دقیقه زمان می‌برد.",
                    reply_kb([["🔙 بازگشت"]]))
        return

    if d == "cr:no":
        db.clear_state(cid)
        user = db.get_user(cid)
        if user:
            await show_menu(s, cid, user)
        return

    if d.startswith("broadcast_target:"):
        target = d.replace("broadcast_target:", "")
        data["broadcast_target"] = target
        db.set_state(cid, ADM_BROADCAST, data)
        await api.send_message(s, cid,
            f"📢 *متن پیام همگانی را بنویسید:*\n\n"
            f"🎯 مخاطبان: {target}",
            reply_kb([["🔙 بازگشت"]]))
        return

    if d.startswith("rate_seeker:"):
        parts = d.split(":")
        to_cid = int(parts[1])
        job_id = int(parts[2])
        await api.send_message(s, cid,
            f"⭐ به این کارجو امتیاز دهید:",
            inline([
                [(f"⭐ ۱", f"rate_do:{to_cid}:{job_id}:1"), (f"⭐ ۲", f"rate_do:{to_cid}:{job_id}:2")],
                [(f"⭐ ۳", f"rate_do:{to_cid}:{job_id}:3"), (f"⭐ ۴", f"rate_do:{to_cid}:{job_id}:4")],
                [(f"⭐ ۵", f"rate_do:{to_cid}:{job_id}:5")],
            ]))
        return

    if d.startswith("rate_do:"):
        parts = d.split(":")
        to_cid = int(parts[1])
        job_id = int(parts[2])
        score = int(parts[3])
        if db.add_rating(cid, to_cid, job_id, score):
            add_activity_log(cid, "امتیازدهی", f"امتیاز {score} به کاربر {to_cid}")
            await api.send_message(s, cid, f"⭐ امتیاز {score}/5 با موفقیت ثبت شد! ممنون.")
        else:
            await api.send_message(s, cid, "❌ خطا در ثبت امتیاز")
        return

    if d == "privacy:toggle":
        user = db.get_user(cid)
        if user:
            new_p = 0 if user["private_mode"] else 1
            db.upsert_user(cid, private_mode=new_p)
            status = "🔓 عمومی" if not new_p else "🔒 خصوصی"
            await api.send_message(s, cid, f"✅ وضعیت نمایش شما به *{status}* تغییر کرد.")
            await show_menu(s, cid, user)
        return

    if d == "empprofile:start":
        db.set_state(cid, ER_ADDRESS)
        await api.send_message(s, cid, "📍 آدرس محل کار (یا 0):", reply_kb([["🔙 بازگشت"]]))
        return

    if d == "jsprofile:start":
        db.set_state(cid, JS_PROV)
        await api.send_message(s, cid, "🗺 استان:", paginate(PROVINCES, [], "prov", 0, cols=2))
        return

    if d.startswith("share_job:"):
        jid = int(d.split(":")[1])
        job = db.get_job(jid)
        if job and job["status"] == "active" and job["admin_approved"]:
            share_link = f"https://t.me/{BOT_NAME.replace(' ', '_')}?start=job_{jid}"
            await api.send_message(s, cid,
                f"🔗 *لینک اشتراک‌گذاری آگهی*\n\n"
                f"💼 {job['title']}\n"
                f"🏷 {job['category']}\n\n"
                f"{share_link}\n\n"
                f"📋 این لینک را کپی کرده و برای دیگران ارسال کنید.")
        else:
            await api.send_message(s, cid, "❌ آگهی برای اشتراک‌گذاری فعال نیست")
        return

    if d.startswith("dmseeker:"):
        await api.send_message(s, cid, "⛔ این قابلیت موقتاً غیرفعال است.")
        return

    handled = await handle_extended_cb(s, cid, d, mid, cbid, state, data)
    if handled:
        return

    if d.startswith("searchmore:"):
        page = int(d.split(":")[1])
        _, search_data = db.get_state(cid)
        search_data["search_page"] = page
        db.set_state(cid, state, search_data)
        await do_search(s, cid, search_data, page)
        return

# ==================== EXTENDED CALLBACKS ====================
async def handle_extended_cb(s, cid, d, mid, cbid, state, data):
    if d.startswith("edit_emp:"):
        field = d.replace("edit_emp:", "")
        labels = {
            "emp_name": "نام",
            "emp_company": "نام شرکت",
            "emp_industry": "صنعت",
            "emp_phone": "شماره موبایل",
            "emp_position": "سمت",
            "emp_address": "آدرس",
            "emp_email": "ایمیل",
            "emp_website": "وب‌سایت"
        }
        if field == "emp_industry":
            db.set_state(cid, "EDIT_EMP_INDUSTRY", {"edit_field": field})
            await api.send_message(s, cid, "🏭 صنعت جدید:", paginate(INDUSTRIES, [], "ind_edit", 0, cols=1))
        else:
            db.set_state(cid, EDIT_EMP_FIELD, {"edit_field": field})
            await api.send_message(s, cid, f"✏️ {labels.get(field, 'فیلد')} جدید را وارد کنید:", reply_kb([["🔙 بازگشت"]]))
        return True

    if d.startswith("ind_edit:"):
        val = d.replace("ind_edit:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(INDUSTRIES, [], "ind_edit", p, cols=1))
            return True
        if val == "DONE":
            if data.get("edit_industry"):
                db.upsert_user(cid, emp_industry=data["edit_industry"])
                add_activity_log(cid, "ویرایش پروفایل", "تغییر صنعت")
                db.clear_state(cid)
                await api.send_message(s, cid, "✅ صنعت بروزرسانی شد")
            return True
        data["edit_industry"] = val
        db.set_state(cid, "EDIT_EMP_INDUSTRY", data)
        await api.edit_reply_markup(s, cid, mid, paginate(INDUSTRIES, [val], "ind_edit", 0, cols=1))
        return True

    if d.startswith("edit_js:"):
        field = d.replace("edit_js:", "")
        labels = {
            "js_name": "نام",
            "js_phone": "شماره موبایل",
            "js_job_title": "شغل مورد نظر",
            "js_province": "استان",
            "js_experience": "تجربه",
            "js_education": "تحصیلات",
            "js_salary_min": "حقوق",
            "js_about": "درباره من",
            "js_categories": "دسته‌ها",
            "js_skills": "مهارت‌ها"
        }
        if field == "js_experience":
            db.set_state(cid, EDIT_JS_FIELD, {"edit_field": field})
            await api.send_message(s, cid, "📆 تجربه جدید:", inline([[(e, f"edit_exp_val:{e}")] for e in EXPERIENCES]))
        elif field == "js_education":
            db.set_state(cid, EDIT_JS_FIELD, {"edit_field": field})
            await api.send_message(s, cid, "🎓 تحصیلات جدید:", inline([[(e, f"edit_edu_val:{e}")] for e in EDUCATIONS]))
        elif field == "js_province":
            db.set_state(cid, EDIT_JS_FIELD, {"edit_field": field})
            await api.send_message(s, cid, "🗺 استان جدید:", paginate(PROVINCES, [], "edit_prov_val", 0, cols=2))
        elif field == "js_categories":
            user = db.get_user(cid)
            cur = jlist(user["js_categories"])
            db.set_state(cid, EDIT_JS_FIELD, {"edit_field": field, "edit_list": cur})
            await api.send_message(s, cid, "🏷 دسته‌های جدید (حداکثر ۳):", paginate(CATEGORIES, cur, "edit_cat_val", 0))
        elif field == "js_skills":
            user = db.get_user(cid)
            cur = jlist(user["js_skills"])
            db.set_state(cid, EDIT_JS_FIELD, {"edit_field": field, "edit_list": cur})
            await api.send_message(s, cid, "🛠 مهارت‌های جدید:", paginate(SKILLS_LIST, cur, "edit_skill_val", 0))
        else:
            db.set_state(cid, EDIT_JS_FIELD, {"edit_field": field})
            await api.send_message(s, cid, f"✏️ {labels.get(field, 'فیلد')} جدید را وارد کنید:", reply_kb([["🔙 بازگشت"]]))
        return True

    if d.startswith("edit_exp_val:"):
        val = d.replace("edit_exp_val:", "")
        db.upsert_user(cid, js_experience=val)
        add_activity_log(cid, "ویرایش پروفایل", f"تغییر تجربه به {val}")
        db.clear_state(cid)
        await api.send_message(s, cid, f"✅ تجربه بروزرسانی شد: {val}")
        return True

    if d.startswith("edit_edu_val:"):
        val = d.replace("edit_edu_val:", "")
        db.upsert_user(cid, js_education=val)
        add_activity_log(cid, "ویرایش پروفایل", f"تغییر تحصیلات به {val}")
        db.clear_state(cid)
        await api.send_message(s, cid, f"✅ تحصیلات بروزرسانی شد: {val}")
        return True

    if d.startswith("edit_prov_val:"):
        val = d.replace("edit_prov_val:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [], "edit_prov_val", p, cols=2))
            return True
        if val == "DONE":
            if data.get("edit_prov"):
                db.upsert_user(cid, js_province=data["edit_prov"])
                add_activity_log(cid, "ویرایش پروفایل", f"تغییر استان به {data['edit_prov']}")
                db.clear_state(cid)
                await api.send_message(s, cid, f"✅ استان بروزرسانی شد")
            return True
        data["edit_prov"] = val
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [val], "edit_prov_val", 0, cols=2))
        return True

    if d.startswith("edit_cat_val:"):
        val = d.replace("edit_cat_val:", "")
        sel = data.get("edit_list", [])
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, sel, "edit_cat_val", p))
            return True
        if val == "DONE":
            db.upsert_user(cid, js_categories=json.dumps(sel, ensure_ascii=False))
            add_activity_log(cid, "ویرایش پروفایل", "تغییر دسته‌ها")
            db.clear_state(cid)
            await api.send_message(s, cid, f"✅ دسته‌ها بروزرسانی شدند")
            return True
        if val in sel:
            sel.remove(val)
        elif len(sel) < 3:
            sel.append(val)
        else:
            await api.answer_cb(s, cbid, "حداکثر ۳!", True)
            return True
        data["edit_list"] = sel
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, sel, "edit_cat_val", 0))
        return True

    if d.startswith("edit_skill_val:"):
        val = d.replace("edit_skill_val:", "")
        sel = data.get("edit_list", [])
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(SKILLS_LIST, sel, "edit_skill_val", p))
            return True
        if val == "DONE":
            db.upsert_user(cid, js_skills=json.dumps(sel, ensure_ascii=False))
            add_activity_log(cid, "ویرایش پروفایل", "تغییر مهارت‌ها")
            db.clear_state(cid)
            await api.send_message(s, cid, f"✅ مهارت‌ها بروزرسانی شدند")
            return True
        if val in sel:
            sel.remove(val)
        elif len(sel) < 10:
            sel.append(val)
        else:
            await api.answer_cb(s, cbid, "حداکثر ۱۰!", True)
            return True
        data["edit_list"] = sel
        db.set_state(cid, state, data)
        await api.edit_reply_markup(s, cid, mid, paginate(SKILLS_LIST, sel, "edit_skill_val", 0))
        return True

    if d.startswith("edit_job:"):
        parts = d.split(":")
        if len(parts) == 3:
            job_id = int(parts[1])
            field = parts[2]
            labels = {
                "title": "عنوان",
                "emp_type": "نوع همکاری",
                "salary": "حقوق",
                "description": "توضیحات"
            }
            if field == "emp_type":
                db.set_state(cid, EDIT_JOB_FIELD, {"edit_job_id": job_id, "edit_field": field})
                await api.send_message(s, cid, "🤝 نوع همکاری جدید:", inline([[(t, f"edit_jobtype_val:{job_id}:{t}")] for t in EMP_TYPES]))
            else:
                db.set_state(cid, EDIT_JOB_FIELD, {"edit_job_id": job_id, "edit_field": field})
                await api.send_message(s, cid, f"✏️ {labels.get(field, 'فیلد')} جدید:", reply_kb([["🔙 بازگشت"]]))
        return True

    if d.startswith("edit_jobtype_val:"):
        parts = d.split(":")
        if len(parts) == 3:
            job_id = int(parts[1])
            val = parts[2]
            db.update_job(job_id, cid, emp_type=val)
            db.clear_state(cid)
            await api.send_message(s, cid, f"✅ نوع همکاری بروز شد: {val}")
        return True

    if d.startswith("delete_job:"):
        job_id = int(d.split(":")[1])
        await api.send_message(s, cid,
            "⚠️ *آیا مطمئنید؟*\n\nآگهی و تمام رزومه‌های آن حذف می‌شود.",
            inline([[("✅ بله حذف کن", f"confirm_del_job:{job_id}"), ("❌ خیر", "ignore")]]))
        return True

    if d.startswith("confirm_del_job:"):
        job_id = int(d.split(":")[1])
        db.delete_job(job_id, cid)
        add_activity_log(cid, "حذف آگهی", f"حذف آگهی {job_id}")
        await api.send_message(s, cid, "✅ آگهی حذف شد")
        await my_jobs(s, cid)
        return True

    if d == "ignore":
        return True

    if d.startswith("jobreqs:"):
        job_id = int(d.split(":")[1])
        apps = db.get_job_applications(job_id)
        job = db.get_job(job_id)
        if not apps:
            await api.send_message(s, cid, f"📭 هنوز رزومه‌ای برای *{job['title']}* دریافت نشده")
            return True
        await api.send_message(s, cid, f"📬 *{len(apps)} رزومه* برای {job['title']}:")
        st_map = {
            "pending_admin": "⏳ در انتظار",
            "approved": "✅ تأیید شده",
            "rejected": "❌ رد شده",
            "seen": "👁 دیده شده"
        }
        for app in apps:
            exp_list = jlist(app.get("work_experience", "[]"))
            exp_text = f"\n📋 {len(exp_list)} سابقه کاری" if exp_list else ""
            await api.send_message(s, cid,
                f"👤 *{app['js_name']}*\n"
                f"📞 {app['js_phone']}\n"
                f"📆 {app['js_experience'] or '—'}\n"
                f"⭐ {stars(app['rating'])}{exp_text}\n"
                f"وضعیت: {st_map.get(app['status'], '—')}",
                inline([[("👁 مشاهده", f"viewseeker:{app['seeker_cid']}")]]))
        return True

    return False

# ==================== EXTENDED STATE HANDLERS ====================
async def handle_extended_state(s, cid, state, data, text) -> bool:
    if state == DM_STATE:
        to_cid = data.get("dm_to")
        job_id = data.get("dm_job")
        if to_cid and job_id:
            user = db.get_user(cid)
            job = db.get_job(job_id)
            db.save_direct_message(cid, to_cid, job_id, text)
            add_activity_log(cid, "پیام مستقیم", f"به کاربر {to_cid} درباره آگهی {job_id}")
            try:
                await api.send_message(s, to_cid,
                    f"💬 *پیام از کارجو*\n\n"
                    f"درباره آگهی: *{job['title']}*\n\n"
                    f"{text}\n\n"
                    f"👤 {user['js_name']} | 📞 {user['js_phone']}")
            except:
                pass
            db.clear_state(cid)
            await api.send_message(s, cid, "✅ پیام ارسال شد!")
            u = db.get_user(cid)
            if u:
                await show_menu(s, cid, u)
        return True

    if state == EDIT_EMP_FIELD:
        field = data.get("edit_field")
        if field:
            val = "" if text == "0" else text
            if field == "emp_phone":
                phone = val.replace(" ", "")
                if not re.search(r'09\d{9}', phone):
                    await api.send_message(s, cid, "❌ شماره موبایل معتبر وارد کنید")
                    return True
                existing = db.get_user_by_phone(phone, role="employer")
                if existing and existing["chat_id"] != cid:
                    await api.send_message(s, cid, "❌ این شماره تماس قبلاً برای یک کارفرمای دیگر ثبت شده است.")
                    return True
                db.upsert_user(cid, emp_phone=phone)
                add_activity_log(cid, "ویرایش پروفایل", f"تغییر شماره تماس به {phone}")
            else:
                db.upsert_user(cid, **{field: val})
                add_activity_log(cid, "ویرایش پروفایل", f"تغییر {field} به {val}")
            db.clear_state(cid)
            await api.send_message(s, cid, f"✅ بروزرسانی شد!")
            u = db.get_user(cid)
            if u:
                await show_menu(s, cid, u)
        return True

    if state == EDIT_JS_FIELD:
        field = data.get("edit_field")
        if field and field not in ("js_experience", "js_education", "js_province", "js_categories", "js_skills"):
            val = "" if text == "0" else text
            if field == "js_salary_min":
                val = parse_int(text)
            elif field == "js_phone":
                phone = val.replace(" ", "")
                if not re.search(r'09\d{9}', phone):
                    await api.send_message(s, cid, "❌ شماره موبایل معتبر وارد کنید")
                    return True
                existing = db.get_user_by_phone(phone, role="job_seeker")
                if existing and existing["chat_id"] != cid:
                    await api.send_message(s, cid, "❌ این شماره تماس قبلاً برای یک کارجوی دیگر ثبت شده است.")
                    return True
                db.upsert_user(cid, js_phone=phone)
                add_activity_log(cid, "ویرایش پروفایل", f"تغییر شماره تماس به {phone}")
                db.clear_state(cid)
                await api.send_message(s, cid, "✅ شماره موبایل بروزرسانی شد!")
                u = db.get_user(cid)
                if u:
                    await show_menu(s, cid, u)
                return True
            else:
                db.upsert_user(cid, **{field: val})
                add_activity_log(cid, "ویرایش پروفایل", f"تغییر {field} به {val}")
            db.clear_state(cid)
            await api.send_message(s, cid, "✅ بروزرسانی شد!")
            u = db.get_user(cid)
            if u:
                await show_menu(s, cid, u)
        return True

    if state == EDIT_JOB_FIELD:
        job_id = data.get("edit_job_id")
        field = data.get("edit_field")
        if job_id and field:
            val = "" if text == "0" else text
            if field == "salary":
                parts = re.findall(r'\d+', text.replace(",", ""))
                if len(parts) >= 2:
                    db.update_job(job_id, cid, salary_min=int(parts[0]), salary_max=int(parts[1]))
                elif len(parts) == 1:
                    db.update_job(job_id, cid, salary_min=int(parts[0]))
            else:
                db.update_job(job_id, cid, **{field: val})
            add_activity_log(cid, "ویرایش آگهی", f"تغییر {field} آگهی {job_id}")
            db.clear_state(cid)
            await api.send_message(s, cid, "✅ آگهی بروزرسانی شد!")
            u = db.get_user(cid)
            if u:
                await show_menu(s, cid, u)
        return True

    return False

# ==================== NOTIFICATIONS ====================
async def _notify_seekers_job(s, job):
    category = job["category"]
    province = job["province"]
    city = job.get("city")
    seekers = db.get_matching_seekers_for_job(category, province, city)
    for row in seekers:
        try:
            await api.send_message(s, row["chat_id"],
                f"📢 *آگهی جدید متناسب با شما!*\n\n"
                f"💼 {job['title']}\n"
                f"🏷 {category}\n"
                f"💰 {fmt_salary(job.get('salary_min'), job.get('salary_max'))}\n"
                f"🗺 {province or '—'}\n",
                inline([[("📄 ارسال رزومه", f"applyjob:{job['job_id']}"),
                         ("🔖 ذخیره", f"bookmark:{job['job_id']}")]])
            )
            db.add_notification(row["chat_id"], f"📢 آگهی جدید: {job['title']} در دسته {category}")
            await asyncio.sleep(0.05)
        except:
            pass

async def _notify_employers_about_seeker(s, seeker, cities):
    category = seeker.get("js_categories", "[]")
    if category:
        try:
            cats = json.loads(category)
        except:
            cats = []
        for cat in cats:
            employers = db.get_matching_employers_for_seeker(cat, seeker.get("js_province"), cities)
            for emp_cid in employers:
                try:
                    await api.send_message(s, emp_cid,
                        f"👤 *کارجوی جدید متناسب با آگهی شما*\n\n"
                        f"نام: {seeker['js_name']}\n"
                        f"دسته: {cat}\n"
                        f"استان: {seeker.get('js_province', '—')}\n"
                        f"برای مشاهده پروفایل کلیک کنید:",
                        inline([[("👁 مشاهده پروفایل", f"viewseeker:{seeker['chat_id']}")]])
                    )
                    db.add_notification(emp_cid, f"👤 کارجوی جدید در دسته {cat} ثبت نام کرد.")
                    await asyncio.sleep(0.05)
                except:
                    pass

# ==================== CORE FUNCTIONS ====================
async def do_welcome(s, cid):
    db.clear_state(cid)
    await api.send_message(s, cid,
        f"🌟 *{BOT_NAME}*\n\n{SLOGAN}\n\n"
        f"👔 کارفرما ← آگهی ثبت کنید و نیرو بیابید\n"
        f"🔍 کارجو ← شغل مناسب بیابید\n\n"
        f"👇 نقش خود را انتخاب کنید:",
        inline([[("👔 کارفرما", "role:employer"), ("🔍 کارجو", "role:job_seeker")]]))

async def cmd_start(s, cid):
    user = db.get_user(cid)
    if user and user["role"]:
        notifs = db.get_unread_count(cid)
        msg = f"🔔 {notifs} اعلان جدید دارید!" if notifs else ""
        await show_menu(s, cid, user, msg)
    else:
        await api.send_message(s, cid,
            f"📢 *{BOT_NAME}*\n\n"
            f"اگر دوست دارید عضو کانال‌های ما شوید:\n\n"
            f"📣 {CHANNEL_1}\n📣 {CHANNEL_2}\n\n"
            f"می‌توانید از این مرحله عبور کنید:",
            inline([[("✅ عضو شدم", "joined:ok"), ("⏭ بعداً", "skip_channel")]]))

async def cmd_menu(s, cid):
    user = db.get_user(cid)
    if user and user["role"]:
        await show_menu(s, cid, user)
    else:
        await do_welcome(s, cid)

async def cmd_profile(s, cid):
    user = db.get_user(cid)
    if not user:
        await api.send_message(s, cid, "❌ ابتدا ثبت‌نام کنید: /start")
        return

    if user["role"] == "employer":
        jobs, total = db.get_employer_jobs(cid)
        text = (
            f"👔 *پروفایل کارفرما*\n\n"
            f"نام: {user['emp_name'] or '—'}\n"
            f"شماره موبایل: {user['emp_phone'] or '—'}\n"
            f"شرکت: {user['emp_company'] or '—'}\n"
            f"صنعت: {user['emp_industry'] or '—'}\n"
            f"سمت: {user['emp_position'] or '—'}\n"
            f"ایمیل: {user['emp_email'] or '—'}\n"
            f"وب‌سایت: {user['emp_website'] or '—'}\n"
            f"آدرس: {user['emp_address'] or '—'}\n\n"
            f"📋 آگهی‌های ثبت‌شده: {total}\n"
            f"⭐ {stars(user['rating'], user['rating_count'])}\n"
            f"📅 عضویت: {user['reg_date'] or '—'}"
        )
        kb = inline([
            [("✏️ ویرایش پروفایل", "empprofile:start")],
            [("👁 تغییر وضعیت نمایش", "privacy:toggle")]
        ])
    else:
        cats = jlist(user["js_categories"])
        skills = jlist(user["js_skills"])
        cities = jlist(user["js_cities"])
        exp_list = jlist(user.get("work_experience", "[]"))
        prv = "🔓 عمومی" if not user["private_mode"] else "🔒 خصوصی"
        exp_text = ""
        if exp_list:
            exp_text = "\n📋 *سوابق کاری:*\n"
            for i, exp in enumerate(exp_list, 1):
                exp_text += f"{i}. {exp.get('place', '—')} | {exp.get('duration', '—')} | {exp.get('role', '—')}\n"
        text = (
            f"👤 *پروفایل کارجو*\n\n"
            f"نام: {user['js_name'] or '—'}\n"
            f"شماره موبایل: {user['js_phone'] or '—'}\n"
            f"استان: {user['js_province'] or '—'}\n"
            f"شغل: {user['js_job_title'] or '—'}\n"
            f"تجربه: {user['js_experience'] or '—'}\n"
            f"تحصیلات: {user['js_education'] or '—'}\n"
            f"حقوق: {fmt_salary(user['js_salary_min'])}\n"
            f"جابجایی: {user['js_relocate'] or '—'}\n"
            f"جنسیت: {user['js_gender'] or '—'}\n"
            f"دسته‌ها: {', '.join(cats) or '—'}\n"
            f"مهارت‌ها: {', '.join(skills[:5]) or '—'}\n"
            f"شهرهای کاری: {', '.join(cities[:3]) or '—'}\n"
            f"{exp_text}"
            f"\n⭐ {stars(user['rating'], user['rating_count'])}\n"
            f"📅 عضویت: {user['reg_date'] or '—'}\n"
            f"👁 وضعیت نمایش: {prv}"
        )
        kb = inline([
            [("✏️ ویرایش پروفایل", "jsprofile:start")],
            [(f"👁 تغییر وضعیت نمایش", "privacy:toggle")]
        ])
    await api.send_message(s, cid, text, kb)

async def cmd_help(s, cid):
    user = db.get_user(cid)
    await api.send_message(s, cid,
        f"📖 *راهنمای {BOT_NAME}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👔 *کارفرما:*\n"
        f"• 📝 ثبت آگهی شغلی\n"
        f"• 📋 مدیریت آگهی‌ها\n"
        f"• 🔎 جستجوی کارجو\n"
        f"• 📬 مشاهده رزومه‌ها\n\n"
        f"🔍 *کارجو:*\n"
        f"• 🔍 جستجوی پیشرفته آگهی\n"
        f"• 📄 ارسال رزومه\n"
        f"• 🔖 ذخیره آگهی‌ها\n"
        f"• ⭐ امتیازدهی به کارفرما\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 برای شروع: /start\n"
        f"📞 پشتیبانی: {CHANNEL_1}\n\n"
        f"{THANKS}",
        menu_for(user) if user else remove_kb())

async def cmd_stats(s, cid):
    if cid not in ADMIN_IDS:
        return
    st = db.get_stats()
    top = "\n".join([f"  • {c[0]}: {c[1]} آگهی" for c in st["top_cats"]])
    await api.send_message(s, cid,
        f"📊 *آمار کامل {BOT_NAME}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 *کاربران:*\n"
        f"  کل: {st['total']}\n"
        f"  👔 کارفرما: {st['employers']}\n"
        f"  🔍 کارجو: {st['seekers']}\n"
        f"  🚫 بن: {st['banned']}\n\n"
        f"📋 *آگهی‌ها:*\n"
        f"  ✅ فعال: {st['active_jobs']}\n"
        f"  ⏳ انتظار: {st['pending_jobs']}\n"
        f"  ⏰ منقضی: {st['expired_jobs']}\n"
        f"  🔒 بسته: {st['closed_jobs']}\n\n"
        f"📬 *رزومه‌ها:*\n"
        f"  کل: {st['total_apps']}\n"
        f"  ⏳ انتظار: {st['pending_apps']}\n"
        f"  ✅ تأیید: {st['approved_apps']}\n"
        f"  ❌ رد: {st['rejected_apps']}\n\n"
        f"🔖 بوکمارک: {st['bookmarks']}\n\n"
        f"🏆 *پرکاربردترین دسته‌ها:*\n{top}\n\n"
        f"📅 {shamsi_dt()}")

async def save_emp_basic(s, cid, position):
    _, data = db.get_state(cid)
    db.upsert_user(cid,
        role="employer",
        emp_name=data.get("emp_name"),
        emp_company=data.get("emp_company"),
        emp_industry=data.get("emp_industry"),
        emp_phone=data.get("emp_phone"),
        emp_position=position)
    db.clear_state(cid)
    add_activity_log(cid, "ثبت‌نام", "ثبت‌نام به‌عنوان کارفرما")
    user = db.get_user(cid)
    await api.send_message(s, cid,
        f"🎉 *ثبت‌نام کارفرما تکمیل شد!*\n\n{SLOGAN_EMP}\n\n"
        f"برای تکمیل پروفایل (آدرس، ایمیل، وب‌سایت) از دکمه تکمیل در مرحله بعد استفاده کنید.")
    db.set_state(cid, ER_ADDRESS)
    await api.send_message(s, cid, "📍 آدرس محل کار (یا 0):", reply_kb([["🔙 بازگشت"]]))

async def save_emp_profile(s, cid, data):
    db.upsert_user(cid,
        emp_address=data.get("emp_address"),
        emp_email=data.get("emp_email"),
        emp_website=data.get("emp_website"))
    db.clear_state(cid)
    add_activity_log(cid, "تکمیل پروفایل", "تکمیل پروفایل کارفرما")
    user = db.get_user(cid)
    await api.send_message(s, cid,
        f"✅ *پروفایل شما با موفقیت تکمیل شد!*\n\n"
        f"{SLOGAN_EMP}\n\n"
        f"ممنون از اعتماد شما 🙏")
    await show_menu(s, cid, user)

async def save_seeker_profile(s, cid, data):
    db.upsert_user(cid,
        js_province=data.get("js_province"),
        js_job_title=data.get("js_job_title"),
        js_experience=data.get("js_experience"),
        js_education=data.get("js_education"),
        js_salary_min=data.get("js_salary_min", 0),
        js_dob=data.get("js_dob"),
        js_gender=data.get("js_gender"),
        js_relocate=data.get("js_relocate"),
        js_cities=json.dumps(data.get("js_cities", []), ensure_ascii=False),
        js_categories=json.dumps(data.get("js_categories", []), ensure_ascii=False),
        js_skills=json.dumps(data.get("js_skills", []), ensure_ascii=False),
        js_about=data.get("js_about"),
        allow_employer_notify=data.get("allow_employer_notify", 0))
    db.clear_state(cid)
    add_activity_log(cid, "تکمیل پروفایل", "تکمیل پروفایل کارجو")
    user = db.get_user(cid)
    if user and not user["private_mode"] and user["allow_employer_notify"] == 1:
        cities = jlist(user.get("js_cities", []))
        await _notify_employers_about_seeker(s, dict(user), cities)
    await api.send_message(s, cid,
        f"✅ *پروفایل شما با موفقیت تکمیل شد!*\n\n"
        f"{SLOGAN}\n\n"
        f"حالا می‌توانید آگهی‌ها را جستجو کنید.\n"
        f"ممنون از اعتماد شما 🙏")
    await show_menu(s, cid, user)

async def finalize_application(s, cid, data):
    jid = data.get("target_job_id")
    if not jid:
        return
    exp_list = data.get("exp_list", [])
    db.upsert_user(cid, work_experience=json.dumps(exp_list, ensure_ascii=False))
    aid, err = db.create_application(jid, cid,
        cover_letter=data.get("cover_letter"),
        resume_file=None,
        resume_type=None,
        file_size=0)
    if not aid:
        if err == "duplicate":
            await api.send_message(s, cid, "⚠️ قبلاً برای این آگهی رزومه ارسال کرده‌اید")
        else:
            await api.send_message(s, cid, "❌ خطا - دوباره امتحان کنید")
        return
    db.clear_state(cid)
    job = db.get_job(jid)
    user = db.get_user(cid)
    add_activity_log(cid, "ارسال رزومه", f"ارسال رزومه برای آگهی {job['title']}")
    exp_count = len(exp_list)
    exp_msg = f" با {exp_count} سابقه کاری" if exp_count > 0 else " بدون سابقه کاری"
    await api.send_message(s, cid,
        f"✅ *{THANKS}*\n\n"
        f"💼 {job['title']}\n"
        f"📋 رزومه شما{exp_msg} با موفقیت ارسال شد.\n\n"
        f"پس از بررسی توسط کارفرما، نتیجه به شما اطلاع داده می‌شود.")
    await notify_admins(s,
        f"📬 *رزومه جدید*\n\n"
        f"💼 {job['title']}\n"
        f"👤 {user['js_name'] or '—'}\n"
        f"📞 {user['js_phone'] or '—'}\n"
        f"📆 {user['js_experience'] or '—'}\n"
        f"📋 {exp_count} سابقه کاری\n"
        f"⭐ {stars(user['rating'], user['rating_count'])}",
        inline([
            [("✅ تأیید", f"admapp:{aid}"), ("❌ رد", f"admrejectapp:{aid}")],
            [("✏️ ویرایش رزومه", f"adm_edit_app:{aid}:cover_letter")]
        ]))
    await show_menu(s, cid, user)

# ==================== JOB FUNCTIONS ====================
async def start_job(s, cid):
    user = db.get_user(cid)
    if not user or user["role"] != "employer":
        await api.send_message(s, cid, "⛔ فقط کارفرما می‌تواند آگهی ثبت کند")
        return
    db.set_state(cid, JOB_TITLE)
    await api.send_message(s, cid,
        "💼 *ثبت آگهی جدید*\n\nعنوان شغلی را وارد کنید:",
        reply_kb([["🔙 بازگشت"]]))

async def finalize_job(s, cid, data):
    if not data.get("job_title") or not data.get("job_category"):
        await api.send_message(s, cid, "❌ اطلاعات ناقص است")
        return
    jid = db.create_job(cid,
        title=data["job_title"],
        emp_type=data.get("job_emp_type"),
        province=data.get("job_province"),
        city=data.get("job_city"),
        salary_min=data.get("job_salary_min", 0),
        salary_max=data.get("job_salary_max", 0),
        category=data["job_category"],
        gender_need=data.get("job_gender"),
        education_need=data.get("job_education"),
        experience_need=data.get("job_experience"),
        description=data.get("job_desc"))
    db.clear_state(cid)
    add_activity_log(cid, "ثبت آگهی", f"ثبت آگهی {data['job_title']}")
    await api.send_message(s, cid,
        f"✅ *آگهی با موفقیت ثبت شد!*\n\n"
        f"💼 {data['job_title']}\n"
        f"🏷 {data['job_category']}\n"
        f"🗺 {data.get('job_province','—')}\n"
        f"💰 {fmt_salary(data.get('job_salary_min'), data.get('job_salary_max'))}\n\n"
        f"⏳ در انتظار تأیید ادمین\n\n{SLOGAN_EMP}")
    await notify_admins(s,
        f"🔔 *آگهی جدید برای تأیید*\n\n"
        f"💼 {data['job_title']}\n"
        f"🏷 {data['job_category']}\n"
        f"🗺 {data.get('job_province','—')}\n"
        f"💰 {fmt_salary(data.get('job_salary_min'), data.get('job_salary_max'))}",
        inline([
            [("✅ تأیید", f"admjob:{jid}"), ("❌ رد", f"admreject:{jid}")],
            [("✏️ ویرایش آگهی", f"adm_edit_job:{jid}:title"),
             ("✏️ ویرایش دسته", f"adm_edit_job:{jid}:category")]
        ]))
    user = db.get_user(cid)
    await show_menu(s, cid, user)

async def my_jobs(s, cid, page=0):
    user = db.get_user(cid)
    if not user or user["role"] != "employer":
        return
    jobs, total = db.get_employer_jobs(cid, page=page)
    if not jobs:
        await api.send_message(s, cid, "📭 هنوز آگهی ثبت نکرده‌اید", menu_for(user))
        return
    st_map = {
        "active": "✅ فعال",
        "pending": "⏳ انتظار",
        "rejected": "❌ رد",
        "expired": "⏰ منقضی",
        "closed": "🔒 بسته"
    }
    for job in jobs:
        approved_date = job.get("approved_date") or "در انتظار"
        expiry_date = job.get("expiry_date") or "—"
        share_btn = [("🔗 اشتراک‌گذاری", f"share_job:{job['job_id']}")] if job["status"] == "active" and job["admin_approved"] else []
        nav = []
        if not db.is_bookmarked(cid, job["job_id"]):
            nav.append(("🔖 ذخیره", f"bookmark:{job['job_id']}"))
        nav.append(("📬 رزومه‌ها", f"jobreqs:{job['job_id']}"))
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n"
            f"🏷 {job['category']}\n"
            f"💰 {fmt_salary(job['salary_min'], job['salary_max'])}\n"
            f"🗺 {job['province'] or '—'}\n"
            f"👁 {job['views']} | 📄 {job['app_count']} درخواست\n"
            f"{st_map.get(job['status'], '—')}\n"
            f"📅 تاریخ تأیید: {approved_date}\n"
            f"📅 تاریخ انقضا: {expiry_date}",
            inline([nav + share_btn] if share_btn else [nav]))
    nav = []
    if page > 0:
        nav.append((f"◀️ صفحه {page}", f"myjobs:{page-1}"))
    if (page + 1) * 10 < total:
        nav.append((f"▶️ صفحه {page+2}", f"myjobs:{page+1}"))
    if nav:
        await api.send_message(s, cid, "صفحه‌بندی:", inline([nav]))
    await show_menu(s, cid, user)

async def emp_received(s, cid):
    user = db.get_user(cid)
    if not user or user["role"] != "employer":
        return
    jobs, _ = db.get_employer_jobs(cid)
    total_apps = 0
    for job in jobs:
        apps = db.get_job_applications(job["job_id"])
        if apps:
            total_apps += len(apps)
            approved = [a for a in apps if a["status"] == "approved"]
            pending = [a for a in apps if a["status"] == "pending_admin"]
            await api.send_message(s, cid,
                f"💼 *{job['title']}*\n"
                f"📄 کل: {len(apps)} | ✅ تأیید: {len(approved)} | ⏳ انتظار: {len(pending)}",
                inline([[("👁 مشاهده رزومه‌ها", f"jobreqs:{job['job_id']}")]]))
    if total_apps == 0:
        await api.send_message(s, cid, "📭 هنوز رزومه‌ای دریافت نشده")
    await show_menu(s, cid, user)

# ==================== SEARCH FUNCTIONS ====================
async def start_search(s, cid):
    user = db.get_user(cid)
    if not user or user["role"] != "job_seeker":
        return
    db.set_state(cid, SRCH_CAT)
    await api.send_message(s, cid, "🏷 دسته شغلی:", paginate(CATEGORIES, [], "scat", 0))

async def do_search(s, cid, data, page=0):
    jobs, total = db.search_jobs(
        category=data.get("search_category"),
        province=data.get("search_province"),
        page=page)
    db.clear_state(cid)
    user = db.get_user(cid)
    if not jobs:
        await api.send_message(s, cid,
            "❌ *آگهی‌ای با این فیلترها یافت نشد*\n\nسعی کنید فیلترها را تغییر دهید.",
            menu_for(user))
        return
    await api.send_message(s, cid, f"✅ *{total} آگهی یافت شد:*")
    for job in jobs:
        bm = "🔖" if db.is_bookmarked(cid, job["job_id"]) else "🔖 ذخیره"
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n"
            f"🏷 {job['category']}\n"
            f"💰 {fmt_salary(job['salary_min'], job['salary_max'])}\n"
            f"🗺 {job['province'] or '—'}\n"
            f"👁 {job['views']} بازدید | 📅 {job['post_date']}",
            inline([
                [("📄 ارسال رزومه", f"applyjob:{job['job_id']}"),
                 (bm, f"bookmark:{job['job_id']}")],
                [("🔗 اشتراک‌گذاری", f"share_job:{job['job_id']}")]
            ]))
    await show_menu(s, cid, user)

async def start_search_seeker(s, cid):
    user = db.get_user(cid)
    if not user or user["role"] != "employer":
        return
    db.set_state(cid, SRCH_SK_CAT)
    await api.send_message(s, cid, "🏷 دسته شغلی:", paginate(CATEGORIES, [], "skcat", 0))

async def do_search_seeker(s, cid, data):
    seekers, total = db.search_seekers(
        category=data.get("sk_category"),
        province=data.get("sk_province"))
    db.clear_state(cid)
    user = db.get_user(cid)
    if not seekers:
        await api.send_message(s, cid, "❌ کارجویی یافت نشد", menu_for(user))
        return
    await api.send_message(s, cid, f"✅ *{total} کارجو یافت شد:*")
    for sk in seekers:
        cats = jlist(sk["js_categories"])
        skills = jlist(sk["js_skills"])
        name = (sk["js_name"] or "").split()[0] if sk["js_name"] else "—"
        exp_list = jlist(sk.get("work_experience", "[]"))
        exp_text = f" | 📋 {len(exp_list)} سابقه" if exp_list else ""
        await api.send_message(s, cid,
            f"👤 *{name}*\n"
            f"📆 {sk['js_experience'] or '—'}\n"
            f"🎓 {sk['js_education'] or '—'}\n"
            f"🗺 {sk['js_province'] or '—'}\n"
            f"💰 {fmt_salary(sk['js_salary_min'])}\n"
            f"🏷 {', '.join(cats[:2]) or '—'}\n"
            f"🛠 {', '.join(skills[:3]) or '—'}{exp_text}\n"
            f"⭐ {stars(sk['rating'], sk['rating_count'])}",
            inline([[("👁 مشاهده کامل", f"viewseeker:{sk['chat_id']}")]]))
    await show_menu(s, cid, user)

# ==================== RESUME FUNCTIONS ====================
async def start_resume(s, cid):
    user = db.get_user(cid)
    if not user or user["role"] != "job_seeker":
        return
    db.set_state(cid, RES_JOB)
    await api.send_message(s, cid,
        "📄 *ارسال رزومه*\n\nشماره آگهی را وارد کنید:",
        reply_kb([["🔙 بازگشت"]]))

async def my_apps(s, cid):
    user = db.get_user(cid)
    if not user or user["role"] != "job_seeker":
        return
    apps = db.get_seeker_applications(cid)
    if not apps:
        await api.send_message(s, cid, "📭 هنوز رزومه‌ای ارسال نکرده‌اید", menu_for(user))
        return
    st_map = {
        "pending_admin": "⏳ در انتظار",
        "approved": "✅ تأیید شد",
        "rejected": "❌ رد شد",
        "seen": "👁 دیده شد"
    }
    await api.send_message(s, cid, f"📊 *{len(apps)} درخواست شما:*")
    for app in apps:
        await api.send_message(s, cid,
            f"💼 *{app['title']}*\n"
            f"🏷 {app['category']}\n"
            f"{st_map.get(app['status'], '—')}\n"
            f"📅 {app['sent_date']}")
    await show_menu(s, cid, user)

async def my_bookmarks(s, cid):
    user = db.get_user(cid)
    if not user or user["role"] != "job_seeker":
        return
    jobs = db.get_bookmarks(cid)
    if not jobs:
        await api.send_message(s, cid, "🔖 هیچ آگهی ذخیره نشده", menu_for(user))
        return
    await api.send_message(s, cid, f"🔖 *{len(jobs)} آگهی ذخیره‌شده:*")
    for job in jobs:
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n"
            f"🏷 {job['category']}\n"
            f"💰 {fmt_salary(job['salary_min'], job['salary_max'])}\n"
            f"🗺 {job['province'] or '—'}",
            inline([[("📄 ارسال رزومه", f"applyjob:{job['job_id']}"),
                     ("🗑 حذف", f"bookmark:{job['job_id']}")]]))
    await show_menu(s, cid, user)

async def my_notifs(s, cid):
    user = db.get_user(cid)
    if not user:
        return
    notifs = db.get_notifications(cid)
    if not notifs:
        await api.send_message(s, cid, "🔔 اعلان جدیدی ندارید", menu_for(user))
        return
    await api.send_message(s, cid, f"🔔 *{len(notifs)} اعلان:*")
    for n in notifs:
        await api.send_message(s, cid, n["text"])
    await show_menu(s, cid, user)

async def activity_log(s, cid):
    user = db.get_user(cid)
    if not user:
        await api.send_message(s, cid,
            "❌ شما ثبت‌نام کامل ندارید.\nلطفاً با /start ثبت‌نام را کامل کنید.",
            remove_kb())
        return
    notifs = db.get_notifications(cid)
    activities = db.get_activity_log(cid, limit=20)
    all_items = []
    for n in notifs:
        all_items.append({
            "type": "اعلان",
            "detail": n["text"],
            "date": n["created_at"]
        })
    for a in activities:
        all_items.append({
            "type": a["action"],
            "detail": a["detail"],
            "date": a["created_at"]
        })
    all_items.sort(key=lambda x: x["date"], reverse=True)
    if not all_items:
        await api.send_message(s, cid, "📋 هنوز فعالیتی ندارید", menu_for(user))
        return
    lines = ["📋 *تاریخچه فعالیت شما:*\n"]
    for item in all_items[:30]:
        date_str = str(item["date"])[:16] if item["date"] else ""
        lines.append(f"• {item['type']}: *{item['detail']}*\n  📅 {date_str}")
    await api.send_message(s, cid, "\n\n".join(lines), menu_for(user))

# ==================== ADMIN FUNCTIONS ====================
async def adm_jobs(s, cid, category=None):
    if cid not in ADMIN_IDS:
        return
    jobs = db.get_pending_jobs(category)
    if not jobs:
        await api.send_message(s, cid, "✅ هیچ آگهی در انتظار نیست")
        return
    await api.send_message(s, cid, f"📋 *{len(jobs)} آگهی در انتظار:*")
    for job in jobs:
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n"
            f"🏭 {job['emp_company'] or '—'}\n"
            f"🏷 {job['category']}\n"
            f"💰 {fmt_salary(job['salary_min'], job['salary_max'])}\n"
            f"🤝 {job['emp_type'] or '—'}\n"
            f"🗺 {job['province'] or '—'}",
            inline([
                [("✅ تأیید", f"admjob:{job['job_id']}"),
                 ("❌ رد", f"admreject:{job['job_id']}")],
                [("✏️ ویرایش", f"adm_edit_job:{job['job_id']}:title")]
            ]))

async def adm_apps(s, cid, category=None):
    if cid not in ADMIN_IDS:
        return
    apps = db.get_pending_applications(category)
    if not apps:
        await api.send_message(s, cid, "✅ هیچ رزومه در انتظار نیست")
        return
    await api.send_message(s, cid, f"📬 *{len(apps)} رزومه در انتظار:*")
    for app in apps:
        exp_list = jlist(app.get("work_experience", "[]"))
        exp_text = f"📋 {len(exp_list)} سابقه کاری" if exp_list else "بدون سابقه"
        await api.send_message(s, cid,
            f"👤 *{app['js_name']}*\n"
            f"📞 {app['js_phone']}\n"
            f"📆 {app['js_experience'] or '—'}\n"
            f"⭐ {stars(app['rating'])}\n"
            f"{exp_text}\n"
            f"💼 {app['title']} | 🏷 {app['category']}",
            inline([
                [("✅ تأیید", f"admapp:{app['app_id']}"),
                 ("❌ رد", f"admrejectapp:{app['app_id']}")],
                [("✏️ ویرایش", f"adm_edit_app:{app['app_id']}:cover_letter")]
            ]))

async def adm_users(s, cid):
    if cid not in ADMIN_IDS:
        return
    st = db.get_stats()
    await api.send_message(s, cid,
        f"🚫 *مدیریت کاربران*\n\n"
        f"کل: {st['total']} | بن: {st['banned']}\n\n"
        f"*دستورات:*\n"
        f"/ban [user_id] [دلیل]\n"
        f"/unban [user_id]\n"
        f"/info [user_id]")

async def adm_logs(s, cid):
    if cid not in ADMIN_IDS:
        return
    logs = db.get_admin_logs(20)
    if not logs:
        await api.send_message(s, cid, "📑 لاگی ثبت نشده")
        return
    lines = ["📑 *۲۰ عملیات اخیر:*\n"]
    for l in logs:
        lines.append(f"• {l['action']} | target:{l['target_id']} | {str(l['created_at'])[:16]}")
    await api.send_message(s, cid, "\n".join(lines))

async def start_broadcast(s, cid):
    if cid not in ADMIN_IDS:
        return
    await api.send_message(s, cid,
        "📢 *انتخاب مخاطبان برای پیام همگانی:*\n\n"
        "👇 یکی از گزینه‌ها را انتخاب کنید:",
        inline([
            [("👥 همه کاربران", "broadcast_target:all")],
            [("👔 فقط کارفرماها", "broadcast_target:employer")],
            [("🔍 فقط کارجوها", "broadcast_target:job_seeker")],
        ]))

async def start_changerole(s, cid):
    db.clear_state(cid)
    user = db.get_user(cid)
    if not user:
        return
    old = user["role"]
    new = "کارجو" if old == "employer" else "کارفرما"
    await api.send_message(s, cid,
        f"🔄 *تغییر نقش*\n\n"
        f"نقش فعلی: {'کارفرما' if old == 'employer' else 'کارجو'}\n"
        f"نقش جدید: *{new}*\n\n"
        f"⚠️ اطلاعات قبلی محفوظ می‌مانند.",
        inline([[("✅ بله، تغییر بده", "cr:yes"), ("❌ خیر", "cr:no")]]))

# ==================== EDIT PROFILE MENUS ====================
async def edit_emp_menu(s, cid):
    user = db.get_user(cid)
    if not user or user["role"] != "employer":
        return
    await api.send_message(s, cid,
        "✏️ *ویرایش پروفایل کارفرما*\n\nکدام فیلد را ویرایش کنید؟",
        inline([
            [("نام", "edit_emp:emp_name"), ("شماره موبایل", "edit_emp:emp_phone")],
            [("شرکت", "edit_emp:emp_company"), ("صنعت", "edit_emp:emp_industry")],
            [("سمت", "edit_emp:emp_position"), ("آدرس", "edit_emp:emp_address")],
            [("ایمیل", "edit_emp:emp_email"), ("وب‌سایت", "edit_emp:emp_website")],
        ]))

async def edit_js_menu(s, cid):
    user = db.get_user(cid)
    if not user or user["role"] != "job_seeker":
        return
    await api.send_message(s, cid,
        "✏️ *ویرایش پروفایل کارجو*\n\nکدام فیلد را ویرایش کنید؟",
        inline([
            [("نام", "edit_js:js_name"), ("شماره موبایل", "edit_js:js_phone")],
            [("شغل مورد نظر", "edit_js:js_job_title"), ("استان", "edit_js:js_province")],
            [("تجربه", "edit_js:js_experience"), ("تحصیلات", "edit_js:js_education")],
            [("حقوق", "edit_js:js_salary_min"), ("درباره من", "edit_js:js_about")],
            [("دسته‌ها", "edit_js:js_categories"), ("مهارت‌ها", "edit_js:js_skills")],
        ]))

# ==================== MAIN LOOP ====================
async def main():
    if not TOKEN or TOKEN == "YOUR_BALE_BOT_TOKEN_HERE":
        print("\n" + "═" * 50)
        print("❌  فایل .env را باز کنید و BOT_TOKEN را وارد کنید!")
        print("═" * 50 + "\n")
        return

    api.set_token(TOKEN)
    log.info("🔄 در حال راه‌اندازی دیتابیس...")
    try:
        db.init_db()
        log.info("✅ دیتابیس با موفقیت راه‌اندازی شد")
    except Exception as e:
        log.error(f"❌ خطا در راه‌اندازی دیتابیس: {e}", exc_info=True)
        return

    log.info(f"✅ {BOT_NAME} شروع شد")

    offset = 0
    try:
        async with aiohttp.ClientSession() as tmp:
            r = await api.get_updates(tmp, timeout=1, limit=1)
            if r.get("ok") and r.get("result"):
                offset = r["result"][-1]["update_id"] + 1
                log.info(f"✅ skip به offset: {offset}")
    except:
        pass

    async with aiohttp.ClientSession() as s:
        me = await api.get_me(s)
        if not me.get("ok"):
            log.error("❌ اتصال به بله ناموفق! توکن را بررسی کنید.")
            return
        log.info(f"✅ متصل: @{me['result'].get('username')}")

        while True:
            try:
                resp = await api.get_updates(s, offset=offset)
                if not resp.get("ok"):
                    log.warning("get_updates failed, retry in 3s...")
                    await asyncio.sleep(3)
                    continue

                for upd in resp.get("result", []):
                    offset = upd["update_id"] + 1
                    try:
                        await process(s, upd)
                    except Exception as e:
                        log.error(f"update error: {e}", exc_info=True)

            except asyncio.CancelledError:
                log.info("ربات متوقف شد")
                break
            except Exception as e:
                log.error(f"polling error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())