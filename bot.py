"""ربات کاریابی همراکار - بله (نسخه کامل async)"""
import asyncio, json, logging, os, re
import aiohttp
import bale_api as api
import database as db
from database import (INDUSTRIES, CATEGORIES, PROVINCES, EMP_TYPES,
                      GENDERS, EXPERIENCES, RELOCATE, fmt_salary)
from bale_api import inline, reply_kb, remove_kb, paginate, msg_text, msg_doc, msg_uid, msg_cid, cb_uid, cb_cid, cb_mid
from config import TOKEN, ADMIN_IDS

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO,
                    handlers=[logging.StreamHandler(), logging.FileHandler("hamrakar.log", encoding="utf-8")])
log = logging.getLogger(__name__)

# ── وضعیت‌های مکالمه ──────────────────────────
IDLE = "IDLE"
ER_NAME, ER_COMPANY, ER_INDUSTRY, ER_PHONE, ER_POSITION = "ER_NAME", "ER_COMPANY", "ER_INDUSTRY", "ER_PHONE", "ER_POSITION"
ER_ADDRESS, ER_EMAIL, ER_WEBSITE, ER_GEND, ER_AGE = "ER_ADDRESS", "ER_EMAIL", "ER_WEBSITE", "ER_GEND", "ER_AGE"
JS_NAME, JS_PHONE, JS_PROV, JS_JOBTITLE, JS_EXP = "JS_NAME", "JS_PHONE", "JS_PROV", "JS_JOBTITLE", "JS_EXP"
JS_SALARY, JS_DOB, JS_GENDER, JS_RELOCATE, JS_CITIES = "JS_SALARY", "JS_DOB", "JS_GENDER", "JS_RELOCATE", "JS_CITIES"
JS_CATS, JS_SKILLS, JS_LANGS = "JS_CATS", "JS_SKILLS", "JS_LANGS"
JOB_TITLE, JOB_TYPE, JOB_LOC, JOB_SAL, JOB_CAT, JOB_GEND, JOB_AGE = "JOB_TITLE", "JOB_TYPE", "JOB_LOC", "JOB_SAL", "JOB_CAT", "JOB_GEND", "JOB_AGE"
SEARCH_CAT, SEARCH_PROV, SEARCH_TYPE, SEARCH_UB = "SEARCH_CAT", "SEARCH_PROV", "SEARCH_TYPE", "SEARCH_UB"
RESUME_JOB, RESUME_AGREE = "RESUME_JOB", "RESUME_AGREE"
ADM_REJECT_JOB, ADM_REJECT_APP, ADM_REJECT_REQ = "ADM_REJECT_JOB", "ADM_REJECT_APP", "ADM_REJECT_REQ"

_state = {}
_data = {}

def st(uid): return _state.get(uid, IDLE)
def dt(uid): return _data.setdefault(uid, {})
def set_st(uid, s, **kw):
    _state[uid] = s
    if kw: dt(uid).update(kw)
def clear(uid):
    _state[uid] = IDLE
    _data[uid] = {}

# ── منو ها ────────────────────────────
def emp_menu():
    return reply_kb([
        ["📝 ثبت آگهی جدید", "📋 آگهی‌های من"],
        ["🔎 جستجوی کارجو", "📬 درخواست‌های رزومه"],
        ["👤 پروفایل من", "⚙️ تنظیمات"],
        ["🔄 تغییر نقش", "🔄 شروع مجدد"],
        ["❓ راهنما"],
    ])

def js_menu():
    return reply_kb([
        ["🔍 جستجوی آگهی", "📄 ارسال رزومه"],
        ["📊 درخواست‌های من", "👤 پروفایل من"],
        ["⚙️ تنظیمات", "🔄 تغییر نقش"],
        ["🔄 شروع مجدد", "❓ راهنما"],
    ])

def adm_menu():
    return reply_kb([
        ["📋 تأیید آگهی", "📬 تأیید رزومه"],
        ["📩 درخواست‌های رزومه", "📊 آمار"],
        ["🔙 منو اصلی", "🔄 شروع مجدد"],
    ])

def menu_for(user):
    if not user or not user["role"]: return remove_kb()
    if user["chat_id"] in ADMIN_IDS: return adm_menu()
    return emp_menu() if user["role"] == "employer" else js_menu()

async def show_menu(s, cid, user, msg=""):
    role_map = {"employer": "کارفرما", "job_seeker": "کارجو"}
    role_fa = "ادمین" if cid in ADMIN_IDS else role_map.get(user["role"], "—")
    text = f"🏠 *منوی اصلی — {role_fa}*"
    if msg: text += f"\n\n{msg}"
    await api.send_message(s, cid, text, menu_for(user))

async def notify_admins(s, text, kb=None):
    for aid in ADMIN_IDS:
        try: await api.send_message(s, aid, text, kb)
        except: pass

# ── dispatch ──────────────────────────────
async def process(s, upd):
    if "message" in upd: await on_msg(s, upd["message"])
    elif "callback_query" in upd: await on_cb(s, upd["callback_query"])

# ── پیام‌ها ──────────────────────────────────
async def on_msg(s, msg):
    cid, uid, text = msg_cid(msg), msg_uid(msg), msg_text(msg)
    state = st(uid)

    if text in ("🔙 بازگشت به منو", "🏠 منو اصلی", "🔙 منو"):
        clear(uid)
        user = await db.get_user(cid)
        if user and user["role"]: await show_menu(s, cid, user)
        else: await welcome(s, cid, uid)
        return

    if text.startswith("/"):
        cmd = text.split()[0].lower()
        if cmd == "/start": await cmd_start(s, cid, uid); return
        if cmd == "/menu": await cmd_menu(s, cid); return
        if cmd == "/profile": await cmd_profile(s, cid); return
        if cmd == "/help": await cmd_help(s, cid); return
        if cmd == "/stats" and cid in ADMIN_IDS: await cmd_stats(s, cid); return
        return

    menu_map = {
        "📝 ثبت آگهی جدید": lambda: start_job(s, cid, uid),
        "📋 آگهی‌های من": lambda: my_jobs(s, cid),
        "🔎 جستجوی کارجو": lambda: search_seeker(s, cid),
        "📬 درخواست‌های رزومه": lambda: requests_resume(s, cid),
        "👤 پروفایل من": lambda: cmd_profile(s, cid),
        "⚙️ تنظیمات": lambda: settings(s, cid),
        "🔄 تغییر نقش": lambda: start_changerole(s, cid, uid),
        "❓ راهنما": lambda: cmd_help(s, cid),
        "🔍 جستجوی آگهی": lambda: start_search(s, cid, uid),
        "📄 ارسال رزومه": lambda: start_resume(s, cid, uid),
        "📊 درخواست‌های من": lambda: my_requests(s, cid),
        "📋 تأیید آگهی": lambda: adm_jobs(s, cid),
        "📬 تأیید رزومه": lambda: adm_apps(s, cid),
        "📩 درخواست‌های رزومه": lambda: adm_reqs(s, cid),
        "📊 آمار": lambda: cmd_stats(s, cid),
        "🔙 منو اصلی": lambda: cmd_menu(s, cid),
        "🔄 شروع مجدد": lambda: cmd_restart(s, cid, uid),
    }
    if text in menu_map:
        await menu_map[text]()
        return

    if state == ER_NAME:
        dt(uid)["emp_name"] = text
        set_st(uid, ER_COMPANY)
        await api.send_message(s, cid, "🏢 نام شرکت:", reply_kb([["🔙 بازگشت به منو"]]))
    elif state == ER_COMPANY:
        dt(uid)["emp_company"] = text
        set_st(uid, ER_INDUSTRY)
        await api.send_message(s, cid, "🏭 صنعت شرکت:", paginate(INDUSTRIES, [], "ind", 0, cols=1))
    elif state == ER_PHONE:
        dt(uid)["emp_phone"] = text
        set_st(uid, ER_POSITION)
        await api.send_message(s, cid, "💼 سمت شغلی شما:", reply_kb([["🔙 بازگشت به منو"]]))
    elif state == ER_POSITION:
        await save_emp(s, cid, uid, text)
    elif state == ER_ADDRESS:
        dt(uid)["emp_address"] = text if text != "0" else ""
        set_st(uid, ER_EMAIL)
        await api.send_message(s, cid, "📧 ایمیل (اختیاری - 0 برای رد):", reply_kb([["🔙 بازگشت به منو"]]))
    elif state == ER_EMAIL:
        dt(uid)["emp_email"] = text if text != "0" else ""
        set_st(uid, ER_WEBSITE)
        await api.send_message(s, cid, "🌐 وب‌سایت (اختیاری - 0 برای رد):", reply_kb([["🔙 بازگشت به منو"]]))
    elif state == ER_WEBSITE:
        dt(uid)["emp_website"] = text if text != "0" else ""
        set_st(uid, ER_GEND)
        kb = inline([[(g, f"egend:{g}")] for g in GENDERS])
        await api.send_message(s, cid, "👥 جنسیت مورد نیاز:", kb)
    elif state == JS_NAME:
        dt(uid)["js_name"] = text
        set_st(uid, JS_PHONE)
        await api.send_message(s, cid, "📞 شماره تماس:", reply_kb([["🔙 بازگشت به منو"]]))
    elif state == JS_PHONE:
        dt(uid)["js_phone"] = text
        set_st(uid, JS_PROV)
        await api.send_message(s, cid, "🗺 استان:", paginate(PROVINCES, [], "prov", 0, cols=2))
    elif state == JOB_TITLE:
        dt(uid)["job_title"] = text
        set_st(uid, JOB_TYPE)
        kb = inline([[(t, f"jtype:{t}")] for t in EMP_TYPES])
        await api.send_message(s, cid, "🤝 نوع همکاری:", kb)
    elif state == JOB_LOC:
        dt(uid)["job_location"] = text
        set_st(uid, JOB_SAL)
        await api.send_message(s, cid, "💰 حقوق (عدد بدون علامت):", reply_kb([["🔙 بازگشت به منو"]]))
    elif state == JOB_SAL:
        try:
            dt(uid)["job_salary"] = int(re.sub(r'\D', '', text)) if text else 0
        except:
            dt(uid)["job_salary"] = 0
        set_st(uid, JOB_CAT)
        await api.send_message(s, cid, "🏷 دسته شغلی:", paginate(CATEGORIES, [], "cat", 0))
    elif state == SEARCH_CAT:
        await do_search(s, cid, uid)
    elif state == RESUME_JOB:
        await handle_job_code(s, cid, uid, text)
    elif state == ADM_REJECT_JOB:
        job_id = dt(uid).get("reject_job_id")
        if job_id: await db.reject_job(job_id)
        clear(uid)
        await api.send_message(s, cid, "✅ آگهی رد شد.")
        await adm_jobs(s, cid)
    elif state == ADM_REJECT_APP:
        app_id = dt(uid).get("reject_app_id")
        if app_id: await db.reject_application(app_id)
        clear(uid)
        await api.send_message(s, cid, "✅ رزومه رد شد.")
        await adm_apps(s, cid)
    else:
        user = await db.get_user(cid)
        if user and user["role"]: await show_menu(s, cid, user)
        else: await welcome(s, cid, uid)

# ── callbacks ──────────────────────────────
async def on_cb(s, cb):
    cid, uid, data, mid, cbid = cb_cid(cb), cb_uid(cb), cb.get("data", ""), cb_mid(cb), cb["id"]
    await api.answer_cb(s, cbid)

    if data.startswith("role:"):
        role = data.replace("role:", "")
        await db.upsert_user(cid, role=role)
        if role == "employer":
            set_st(uid, ER_NAME)
            await api.send_message(s, cid, "✅ *کارفرما*\n\nنام و نام خانوادگی:", reply_kb([["🔙 بازگشت به منو"]]))
        else:
            set_st(uid, JS_NAME)
            await api.send_message(s, cid, "✅ *کارجو*\n\nنام و نام خانوادگی:", reply_kb([["🔙 بازگشت به منو"]]))
        return

    if data == "joined:ok":
        user = await db.get_user(cid)
        if user and user["role"]: await show_menu(s, cid, user, "✅ خوش آمدید!")
        else: await welcome(s, cid, uid)
        return

    if data.startswith("ind:"):
        val = data.replace("ind:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(INDUSTRIES, [], "ind", p, cols=1))
            return
        if val == "DONE":
            if not dt(uid).get("emp_industry"):
                await api.send_message(s, cid, "⚠️ یک صنعت انتخاب کنید!")
                return
            set_st(uid, ER_PHONE)
            await api.send_message(s, cid, "📞 شماره تماس:", reply_kb([["🔙 بازگشت به منو"]]))
            return
        dt(uid)["emp_industry"] = val
        await api.edit_reply_markup(s, cid, mid, paginate(INDUSTRIES, [val], "ind", dt(uid).get("_ip", 0), cols=1))
        return

    if data.startswith("prov:"):
        val = data.replace("prov:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [], "prov", p, cols=2))
            return
        if val == "DONE":
            if not dt(uid).get("js_province"):
                await api.send_message(s, cid, "⚠️ یک استان انتخاب کنید!")
                return
            set_st(uid, JS_JOBTITLE)
            await api.send_message(s, cid, "💼 شغل مورد نظر (متن آزاد):", reply_kb([["🔙 بازگشت به منو"]]))
            return
        dt(uid)["js_province"] = val
        await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [val], "prov", dt(uid).get("_pp", 0), cols=2))
        return

    if data.startswith("prov2:"):
        val = data.replace("prov2:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            sel = dt(uid).get("js_cities", [])
            await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, sel, "prov2", p, cols=2))
            return
        if val == "DONE":
            set_st(uid, JS_CATS)
            await api.send_message(s, cid, "🏷 دسته شغلی (حداکثر 3):", paginate(CATEGORIES, [], "jscat", 0))
            return
        sel = dt(uid).setdefault("js_cities", [])
        if val in sel: sel.remove(val)
        else: sel.append(val)
        await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, sel, "prov2", dt(uid).get("_pp2", 0), cols=2))
        return

    if data.startswith("egend:"):
        dt(uid)["emp_gender"] = data.replace("egend:", "")
        set_st(uid, ER_AGE)
        await api.send_message(s, cid, "📅 محدوده سنی (مثال: 25-40 یا 0 برای رد):", reply_kb([["🔙 بازگشت به منو"]]))
        return

    if data.startswith("jtype:"):
        dt(uid)["job_emp_type"] = data.replace("jtype:", "")
        set_st(uid, JOB_LOC)
        await api.send_message(s, cid, "📍 آدرس محل کار:", reply_kb([["🔙 بازگشت به منو"]]))
        return

    if data.startswith("cat:"):
        val = data.replace("cat:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [], "cat", p))
            return
        if val == "DONE":
            if not dt(uid).get("job_category"):
                await api.send_message(s, cid, "⚠️ یک دسته انتخاب کنید!")
                return
            await finalize_job(s, cid, uid)
            return
        dt(uid)["job_category"] = val
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [val], "cat", dt(uid).get("_jc", 0)))
        return

    if data.startswith("jscat:"):
        val = data.replace("jscat:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            sel = dt(uid).get("js_categories", [])
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, sel, "jscat", p))
            return
        if val == "DONE":
            set_st(uid, JS_EXP)
            kb = inline([[(e, f"jsexp:{e}")] for e in EXPERIENCES])
            await api.send_message(s, cid, "📆 سطح تجربه:", kb)
            return
        sel = dt(uid).setdefault("js_categories", [])
        if val in sel: sel.remove(val)
        elif len(sel) < 3: sel.append(val)
        else:
            await api.send_message(s, cid, "⚠️ حداکثر 3 دسته!", keyboard=None)
            return
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, sel, "jscat", dt(uid).get("_jsc", 0)))
        return

    if data.startswith("jsexp:"):
        dt(uid)["js_experience"] = data.replace("jsexp:", "")
        set_st(uid, JS_SALARY)
        await api.send_message(s, cid, "💰 حقوق مورد انتظار (عدد - 0 برای توافقی):", reply_kb([["🔙 بازگشت به منو"]]))
        return

    if data.startswith("scat:"):
        val = data.replace("scat:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [], "scat", p))
            return
        if val == "DONE":
            dt(uid)["search_cat"] = dt(uid).get("search_cat")
            await do_search(s, cid, uid)
            return
        dt(uid)["search_cat"] = val
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [val], "scat", dt(uid).get("_sc", 0)))
        return

    if data.startswith("admjob:"):
        job_id = int(data.split(":")[1])
        await db.approve_job(job_id)
        job = await db.get_job(job_id)
        if job:
            emp = await db.get_user(job["emp_cid"])
            await api.send_message(s, cid, f"✅ آگهی {job_id} تأیید شد.")
            try:
                await api.send_message(s, job["emp_cid"],
                    f"✅ آگهی *{job['title']}* تأیید شد!\n\n🏢 شریکِ مسیرِ رشدِ سازمان‌ها")
            except: pass
        await adm_jobs(s, cid)
        return

    if data.startswith("admreject:"):
        job_id = int(data.split(":")[1])
        await db.reject_job(job_id)
        await api.send_message(s, cid, f"❌ آگهی {job_id} رد شد.")
        await adm_jobs(s, cid)
        return

    if data.startswith("admapp:"):
        app_id = int(data.split(":")[1])
        await db.approve_application(app_id)
        await api.send_message(s, cid, f"✅ رزومه {app_id} تأیید شد.")
        await adm_apps(s, cid)
        return

    if data.startswith("admrejectapp:"):
        app_id = int(data.split(":")[1])
        await db.reject_application(app_id)
        await api.send_message(s, cid, f"❌ رزومه {app_id} رد شد.")
        await adm_apps(s, cid)
        return

    if data.startswith("admreq:"):
        req_id = int(data.split(":")[1])
        await db.approve_resume_request(req_id)
        await api.send_message(s, cid, f"✅ درخواست {req_id} تأیید شد.")
        await adm_reqs(s, cid)
        return

    if data == "cr:yes":
        user = await db.get_user(cid)
        old = user["role"] if user else None
        new = "job_seeker" if old == "employer" else "employer"
        await db.upsert_user(cid, role=new, emp_name=None, emp_company=None)
        clear(uid)
        if new == "employer":
            set_st(uid, ER_NAME)
            await api.send_message(s, cid, "✅ *کارفرما*\n\nنام و نام خانوادگی:", reply_kb([["🔙 بازگشت به منو"]]))
        else:
            set_st(uid, JS_NAME)
            await api.send_message(s, cid, "✅ *کارجو*\n\nنام و نام خانوادگی:", reply_kb([["🔙 بازگشت به منو"]]))
        return

    if data == "cr:no":
        clear(uid)
        user = await db.get_user(cid)
        if user: await show_menu(s, cid, user)
        return

# ── توابع اصلی ────────────────────────────
async def welcome(s, cid, uid):
    clear(uid)
    welcome_text = await db.get_setting("welcome_text",
        "🌟 *رسانه استخدامی همراکار*\n\n"
        "✨ ما به توان انسان‌ها باور داریم ✨\n\n"
        "👔 کارفرما → آگهی ثبت کنید\n"
        "🔍 کارجو → شغل بیابید\n\n"
        "👇 نقش خود را انتخاب کنید:")
    kb = inline([[("👔 کارفرما", "role:employer"), ("🔍 کارجو", "role:job_seeker")]])
    await api.send_message(s, cid, welcome_text, kb)

async def cmd_start(s, cid, uid):
    clear(uid)
    user = await db.get_user(cid)
    if user and user["role"]:
        await show_menu(s, cid, user)
    else:
        await api.send_message(s, cid,
            "📢 **عضویت در کانال‌های ما**\n\n@hamrakar\n@hamrakarjob\n\n"
            "اگر می‌خواهید عضو شوید دکمه زیر را بزنید:",
            inline([[("✅ عضو شدم", "joined:ok"),
                     ("⏭ بعداً", "skip_channel")]]))
        set_st(uid, IDLE)

async def cmd_restart(s, cid, uid):
    clear(uid)
    user = await db.get_user(cid)
    if user and user["role"]:
        await db.upsert_user(cid, role=None)
    await cmd_start(s, cid, uid)

async def cmd_menu(s, cid):
    user = await db.get_user(cid)
    if user and user["role"]: await show_menu(s, cid, user)
    else: await welcome(s, cid, 0)

async def cmd_profile(s, cid):
    user = await db.get_user(cid)
    if not user:
        await api.send_message(s, cid, "ابتدا ثبت‌نام کنید: /start")
        return
    if user["role"] == "employer":
        text = (f"👔 *پروفایل کارفرما*\n\n"
                f"نام: {user['emp_name'] or '—'}\n"
                f"شرکت: {user['emp_company'] or '—'}\n"
                f"صنعت: {user['emp_industry'] or '—'}\n"
                f"تلفن: {user['emp_phone'] or '—'}\n"
                f"سمت: {user['emp_position'] or '—'}\n"
                f"📅 {user['reg_date'] or user['created_at'] or '—'}")
    else:
        text = (f"👤 *پروفایل کارجو*\n\n"
                f"نام: {user['js_name'] or '—'}\n"
                f"تلفن: {user['js_phone'] or '—'}\n"
                f"استان: {user['js_province'] or '—'}\n"
                f"شغل مورد نظر: {user['js_job_title'] or '—'}\n"
                f"تجربه: {user['js_experience'] or '—'}\n"
                f"⭐ امتیاز: {user.get('js_rating', 5.0)}\n"
                f"📅 {user['reg_date'] or user['created_at'] or '—'}")
    await api.send_message(s, cid, text, menu_for(user))

async def cmd_help(s, cid):
    user = await db.get_user(cid)
    await api.send_message(s, cid,
        "📖 *راهنما*\n\n"
        "👔 *کارفرما:*\n"
        "• ثبت آگهی\n"
        "• جستجوی کارجو\n"
        "• درخواست رزومه\n\n"
        "🔍 *کارجو:*\n"
        "• جستجوی آگهی\n"
        "• ارسال رزومه\n"
        "• تکمیل پروفایل\n\n"
        "🙏 *با تشکر از اعتماد شما*", menu_for(user) if user else remove_kb())

async def cmd_stats(s, cid):
    if cid not in ADMIN_IDS: return
    stats = await db.get_stats()
    await api.send_message(s, cid,
        f"📊 *آمار ربات*\n\n"
        f"👥 کل کاربران: {stats['total']}\n"
        f"👔 کارفرما: {stats['employers']}\n"
        f"🔍 کارجو: {stats['seekers']}\n\n"
        f"📋 آگهی فعال: {stats['active']}\n"
        f"⏳ آگهی در انتظار: {stats['pending']}\n"
        f"📬 رزومه در انتظار: {stats['pending_apps']}")

# ── ثبت‌نام ────────────────────────────
async def save_emp(s, cid, uid, position):
    d = dt(uid)
    await db.upsert_user(cid,
        role="employer", emp_name=d.get("emp_name"),
        emp_company=d.get("emp_company"), emp_industry=d.get("emp_industry"),
        emp_phone=d.get("emp_phone"), emp_position=position)
    clear(uid)
    user = await db.get_user(cid)
    await api.send_message(s, cid,
        "🎉 *ثبت‌نام کارفرما تکمیل شد!*\n\n"
        "🏢 شریکِ مسیرِ رشدِ سازمان‌ها")
    await show_menu(s, cid, user)

# ── آگهی ────────────────────────────────
async def start_job(s, cid, uid):
    user = await db.get_user(cid)
    if not user or user["role"] != "employer":
        await api.send_message(s, cid, "⛔ فقط کارفرما")
        return
    if not (user.get("emp_address") or user.get("emp_email")):
        await api.send_message(s, cid,
            "⚠️ لطفاً ابتدا پروفایل خود را تکمیل کنید.\n\n"
            "📝 در تنظیمات → تکمیل پروفایل")
        return
    clear(uid)
    set_st(uid, JOB_TITLE)
    await api.send_message(s, cid, "💼 *ثبت آگهی*\n\nعنوان شغل:", reply_kb([["🔙 بازگشت به منو"]]))

async def finalize_job(s, cid, uid):
    d = dt(uid)
    job_id = await db.create_job(
        emp_cid=cid,
        title=d.get("job_title"),
        emp_type=d.get("job_emp_type", "تمام وقت"),
        location=d.get("job_location", "نامشخص"),
        salary=d.get("job_salary", 0),
        category=d.get("job_category"))
    clear(uid)
    job = await db.get_job(job_id)
    await api.send_message(s, cid,
        f"✅ *آگهی ثبت شد*\n\n"
        f"عنوان: *{d.get('job_title')}*\n"
        f"دسته: {d.get('job_category')}\n\n"
        f"⏳ در انتظار تأیید ادمین")
    await notify_admins(s,
        f"🔔 *آگهی جدید*\n\n"
        f"عنوان: {d.get('job_title')}\n"
        f"دسته: {d.get('job_category')}\n"
        f"job_id: {job_id}",
        inline([[("✅ تأیید", f"admjob:{job_id}"), ("❌ رد", f"admreject:{job_id}")]]))
    user = await db.get_user(cid)
    await show_menu(s, cid, user)

async def my_jobs(s, cid):
    user = await db.get_user(cid)
    if not user or user["role"] != "employer": return
    jobs = await db.get_employer_jobs(cid)
    if not jobs:
        await api.send_message(s, cid, "هیچ آگهی‌ای ندارید.", menu_for(user))
        return
    st_map = {"active": "✅ فعال", "pending": "⏳ انتظار", "rejected": "❌ رد"}
    for job in jobs:
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n"
            f"دسته: {job['category']}\n"
            f"حقوق: {fmt_salary(job['salary'])}\n"
            f"وضعیت: {st_map.get(job['status'], job['status'])}\n"
            f"📅 {job.get('post_date', job.get('created_at', ''))}")
    await show_menu(s, cid, user)

# ── جستجو ────────────────────────────────────
async def start_search(s, cid, uid):
    user = await db.get_user(cid)
    if not user or user["role"] != "job_seeker": return
    clear(uid)
    set_st(uid, SEARCH_CAT)
    await api.send_message(s, cid, "🏷 دسته شغلی:", paginate(CATEGORIES, [], "scat", 0))

async def do_search(s, cid, uid):
    d = dt(uid)
    jobs = await db.get_jobs(category=d.get("search_cat"))
    clear(uid)
    user = await db.get_user(cid)
    if not jobs:
        await api.send_message(s, cid, "❌ آگهی‌ای یافت نشد.", menu_for(user))
        return
    for job in jobs[:10]:
        emp = await db.get_user(job["emp_cid"])
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n"
            f"شرکت: {emp['emp_company'] if emp else '—'}\n"
            f"حقوق: {fmt_salary(job['salary'])}\n"
            f"🤝 {job['emp_type']}\n"
            f"📍 {job['location']}\n"
            f"🏷 {job['category']}\n"
            f"📅 {job.get('post_date', job.get('created_at', ''))}",
            inline([[("📄 ارسال رزومه", f"applyjob:{job['job_id']}")]]))
    await show_menu(s, cid, user)

# ── ارسال رزومه ──────────────────────────────
async def start_resume(s, cid, uid):
    user = await db.get_user(cid)
    if not user or user["role"] != "job_seeker": return
    if not (user.get("js_name") and user.get("js_phone")):
        await api.send_message(s, cid, "⚠️ لطفاً ابتدا پروفایل را تکمیل کنید.")
        return
    clear(uid)
    set_st(uid, RESUME_JOB)
    await api.send_message(s, cid, "🔍 شماره آگهی را وارد کنید (مثال: 5):", reply_kb([["🔙 بازگشت به منو"]]))

async def handle_job_code(s, cid, uid, code):
    try: job_id = int(code)
    except:
        await api.send_message(s, cid, "❌ شماره آگهی باید عددی باشد.")
        return
    job = await db.get_job(job_id)
    if not job or job["status"] != "active" or not job.get("admin_approved"):
        await api.send_message(s, cid, "❌ آگهی یافت نشد.")
        return
    app = await db.create_application(job_id=job_id, seeker_cid=cid,
                                       employer_id=job["emp_cid"])
    clear(uid)
    user = await db.get_user(cid)
    await api.send_message(s, cid,
        f"✅ *رزومه ارسال شد!*\n\n"
        f"آگهی: *{job['title']}*\n\n"
        f"🙏 با تشکر از اعتماد شما")
    await notify_admins(s,
        f"📬 *رزومه جدید*\n\n"
        f"آگهی: {job['title']}\n"
        f"متقاضی: {user.get('js_name', 'نامشخص')}\n"
        f"app_id: {app}",
        inline([[("✅ تأیید", f"admapp:{app}"), ("❌ رد", f"admrejectapp:{app}")]]))
    await show_menu(s, cid, user)

async def my_requests(s, cid):
    user = await db.get_user(cid)
    if not user or user["role"] != "job_seeker": return
    apps = await db.get_seeker_applications(cid)
    if not apps:
        await api.send_message(s, cid, "📭 درخواست‌ای ندارید.", menu_for(user))
        return
    st_map = {"pending_admin": "⏳ انتظار", "approved": "✅ تأیید", "rejected": "❌ رد"}
    for app in apps:
        await api.send_message(s, cid,
            f"📄 *{app['title']}*\n"
            f"وضعیت: {st_map.get(app['status'], app['status'])}\n"
            f"📅 {app['sent_date']}")
    await show_menu(s, cid, user)

# ── جستجوی کارجو ──────────────────────────
async def search_seeker(s, cid):
    user = await db.get_user(cid)
    if not user or user["role"] != "employer": return
    if not (user.get("emp_address") or user.get("emp_email")):
        await api.send_message(s, cid, "⚠️ لطفاً ابتدا پروفایل را تکمیل کنید.")
        return
    await api.send_message(s, cid,
        "🔎 *جستجوی کارجو*\n\n"
        "قابلیت جستجوی پیشرفته در دست توسعه است.\n\n"
        "از بخش درخواست‌های رزومه استفاده کنید.",
        menu_for(user))

async def requests_resume(s, cid):
    user = await db.get_user(cid)
    if not user or user["role"] != "employer": return
    await api.send_message(s, cid, "📩 درخواست‌های رزومه", menu_for(user))

# ── ادمین ────────────────────────────────────
async def adm_jobs(s, cid):
    if cid not in ADMIN_IDS: return
    jobs = await db.get_pending_jobs()
    if not jobs:
        await api.send_message(s, cid, "✅ هیچ آگهی‌ای در انتظار نیست.")
        return
    for job in jobs:
        company = job.get("emp_company") or "نامشخص"
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n"
            f"شرکت: {company}\n"
            f"دسته: {job['category']}\n"
            f"job_id: {job['job_id']}",
            inline([[("✅ تأیید", f"admjob:{job['job_id']}"),
                     ("❌ رد", f"admreject:{job['job_id']}")]]))

async def adm_apps(s, cid):
    if cid not in ADMIN_IDS: return
    apps = await db.get_pending_applications()
    if not apps:
        await api.send_message(s, cid, "✅ هیچ رزومه‌ای در انتظار نیست.")
        return
    for app in apps:
        name = app.get("js_name") or "نامشخص"
        await api.send_message(s, cid,
            f"👤 {name}\n"
            f"آگهی: {app.get('job_title', 'نامشخص')}\n"
            f"app_id: {app['app_id']}",
            inline([[("✅ تأیید", f"admapp:{app['app_id']}"),
                     ("❌ رد", f"admrejectapp:{app['app_id']}")]]))

async def adm_reqs(s, cid):
    if cid not in ADMIN_IDS: return
    reqs = await db.get_pending_resume_requests()
    if not reqs:
        await api.send_message(s, cid, "✅ هیچ درخواست رزومه‌ای در انتظار نیست.", adm_menu())
        return
    for req in reqs[:10]:
        company = req.get("emp_company") or req.get("employer_company") or "نامشخص"
        await api.send_message(s, cid,
            f"📩 *درخواست رزومه*\n"
            f"کارجو: {req.get('seeker_name', 'نامشخص')}\n"
            f"کارفرما: {company}",
            inline([[("✅ تأیید", f"admreq:{req['req_id']}")]]))

# ── تنظیمات ───────────────────────────────────
async def settings(s, cid):
    user = await db.get_user(cid)
    if not user: return
    await api.send_message(s, cid,
        "⚙️ *تنظیمات*\n\n"
        "[ ویژگی‌های اضافی در نسخه‌های بعدی ]",
        menu_for(user))

# ── تغییر نقش ────────────────────────────────
async def start_changerole(s, cid, uid):
    clear(uid)
    kb = inline([[("✅ بله", "cr:yes"), ("❌ خیر", "cr:no")]])
    await api.send_message(s, cid,
        "🔄 *تغییر نقش*\n\n"
        "⚠️ اطلاعات تغییر خواهد کرد.\n"
        "ادامه می‌دهید?", kb)

# ── حلقه اصلی ──────────────────────────────────
async def main():
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n❌ توکن تنظیم نشده!\n")
        return
    api.set_token(TOKEN)
    await db.init_db()
    log.info("ربات همراکار شروع شد...")
    offset = 0
    async with aiohttp.ClientSession() as s:
        me = await api.get_me(s)
        if me.get("ok"):
            log.info(f"متصل: {me['result'].get('first_name')}")
        else:
            log.error("اتصال ناموفق!")
            return
        while True:
            try:
                resp = await api.get_updates(s, offset=offset)
                if not resp.get("ok"):
                    await asyncio.sleep(3)
                    continue
                for upd in resp.get("result", []):
                    offset = upd["update_id"] + 1
                    try: await process(s, upd)
                    except Exception as e: log.exception(f"update: {e}")
            except asyncio.CancelledError: break
            except Exception as e:
                log.error(f"polling: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
