import asyncio
import json
import logging
import os
import re
import aiohttp
import bale_api as api
import database as db
from database import (INDUSTRIES, CATEGORIES, PROVINCES, EMP_TYPES,
                      GENDERS, EXPERIENCES, RELOCATE, fmt_salary)
from bale_api import inline, reply_kb, remove_kb, paginate, msg_text, msg_doc, msg_uid, msg_cid, cb_uid, cb_cid, cb_mid
from config import TOKEN, ADMIN_IDS
from logging.handlers import RotatingFileHandler

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
handler = RotatingFileHandler("hamrakar.log", encoding="utf-8", maxBytes=5*1024*1024, backupCount=3)
handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
log.addHandler(handler)
log.addHandler(logging.StreamHandler())

# وضعیت‌های مکالمه
IDLE = "IDLE"

# کارفرما - ثبت‌نام
ER_NAME, ER_COMPANY, ER_INDUSTRY, ER_PHONE, ER_POSITION = "ER_NAME", "ER_COMPANY", "ER_INDUSTRY", "ER_PHONE", "ER_POSITION"
# کارفرما - تکمیل پروفایل
ER_ADDRESS, ER_EMAIL, ER_WEBSITE, ER_GEND, ER_AGE = "ER_ADDRESS", "ER_EMAIL", "ER_WEBSITE", "ER_GEND", "ER_AGE"

# کارجو - ثبت‌نام
JS_NAME, JS_PHONE, JS_PROV, JS_JOB, JS_EXP, JS_SAL = "JS_NAME", "JS_PHONE", "JS_PROV", "JS_JOB", "JS_EXP", "JS_SAL"
JS_DOB, JS_GEND, JS_RELOC, JS_CITIES, JS_CATS, JS_SKILLS = "JS_DOB", "JS_GEND", "JS_RELOC", "JS_CITIES", "JS_CATS", "JS_SKILLS"

# آگهی
JOB_TITLE, JOB_TYPE, JOB_LOC, JOB_SAL, JOB_CAT = "JOB_TITLE", "JOB_TYPE", "JOB_LOC", "JOB_SAL", "JOB_CAT"

# جستجو
SEARCH_CAT = "SEARCH_CAT"

# ارسال رزومه
RES_JOB, RES_UPLOAD = "RES_JOB", "RES_UPLOAD"

# ادمین
ADM_REJ_JOB, ADM_REJ_APP = "ADM_REJ_JOB", "ADM_REJ_APP"


async def st(uid):
    s, _ = await db.get_state(uid)
    return s

async def dt(uid):
    _, d = await db.get_state(uid)
    return d

async def set_st(uid, s, **kw):
    _, d = await db.get_state(uid)
    if kw: d.update(kw)
    await db.set_state(uid, s, d)

async def clear(uid):
    await db.clear_state(uid)

def emp_menu():
    return reply_kb([
        ["📝 ثبت آگهی", "📋 آگهی‌های من"],
        ["🔎 جستجوی کارجو", "📬 درخواست‌های رزومه"],
        ["👤 پروفایل", "⚙️ تنظیمات"],
        ["🔄 تغییر نقش", "❓ راهنما"],
    ])

def js_menu():
    return reply_kb([
        ["🔍 جستجوی آگهی", "📄 ارسال رزومه"],
        ["📊 درخواست‌های من", "👤 پروفایل"],
        ["⚙️ تنظیمات", "🔄 تغییر نقش"],
        ["❓ راهنما"],
    ])

def adm_menu():
    return reply_kb([
        ["📋 تأیید آگهی", "📬 تأیید رزومه"],
        ["📊 آمار", "🔙 منو"],
    ])

def menu_for(user):
    if not user or not user["role"]: return remove_kb()
    if user["chat_id"] in ADMIN_IDS: return adm_menu()
    return emp_menu() if user["role"] == "employer" else js_menu()

async def show_menu(s, cid, user, msg=""):
    role_map = {"employer": "کارفرما", "job_seeker": "کارجو"}
    role_fa = "ادمین" if cid in ADMIN_IDS else role_map.get(user["role"], "—")
    text = f"🏠 *منوی اصلی — {role_fa}*"
    if msg: text += "\n\n" + msg
    await api.send_message(s, cid, text, menu_for(user))

async def notify_admins(s, text, kb=None):
    for aid in ADMIN_IDS:
        try: await api.send_message(s, aid, text, kb)
        except: pass

async def process(s, upd):
    if "message" in upd: await on_msg(s, upd["message"])
    elif "callback_query" in upd: await on_cb(s, upd["callback_query"])

# ──────────────────────────────────────────────
# پیام‌ها
# ──────────────────────────────────────────────
async def on_msg(s, msg):
    cid, uid, text = msg_cid(msg), msg_uid(msg), msg_text(msg)
    doc = msg_doc(msg)
    state = await st(uid)

    # دکمه بازگشت
    if text in ("🔙 بازگشت", "🔙 بازگشت به منو", "🔙 منو", "🏠 منو اصلی"):
        await clear(uid)
        user = await db.get_user(cid)
        if user and user["role"]: await show_menu(s, cid, user)
        else: await welcome(s, cid, uid)
        return

    # دستورات
    if text.startswith("/"):
        cmd = text.split()[0].lower()
        if cmd == "/start": await cmd_start(s, cid, uid); return
        if cmd == "/menu": await cmd_menu(s, cid); return
        if cmd == "/profile": await cmd_profile(s, cid); return
        if cmd == "/help": await cmd_help(s, cid); return
        if cmd == "/stats" and cid in ADMIN_IDS: await cmd_stats(s, cid); return
        return

    # منوی متنی
    menu_map = {
        "📝 ثبت آگهی": lambda: start_job(s, cid, uid),
        "📋 آگهی‌های من": lambda: my_jobs(s, cid),
        "🔎 جستجوی کارجو": lambda: cmd_search(s, cid),
        "📬 درخواست‌های رزومه": lambda: cmd_requests(s, cid),
        "👤 پروفایل": lambda: cmd_profile(s, cid),
        "⚙️ تنظیمات": lambda: cmd_settings(s, cid),
        "🔄 تغییر نقش": lambda: start_changerole(s, cid, uid),
        "❓ راهنما": lambda: cmd_help(s, cid),
        "🔍 جستجوی آگهی": lambda: start_search(s, cid, uid),
        "📄 ارسال رزومه": lambda: start_resume(s, cid, uid),
        "📊 درخواست‌های من": lambda: my_apps(s, cid),
        "📋 تأیید آگهی": lambda: adm_jobs(s, cid),
        "📬 تأیید رزومه": lambda: adm_apps(s, cid),
        "📊 آمار": lambda: cmd_stats(s, cid),
        "🔙 منو": lambda: cmd_menu(s, cid),
    }
    if text in menu_map:
        await menu_map[text]()
        return

    d = await dt(uid)

    # ── کارفرما: ثبت‌نام ──
    if state == ER_NAME:
        await set_st(uid, ER_COMPANY, emp_name=text)
        await api.send_message(s, cid, "🏢 نام شرکت:", reply_kb([["🔙 بازگشت"]]))
    elif state == ER_COMPANY:
        await set_st(uid, ER_INDUSTRY, emp_company=text)
        await api.send_message(s, cid, "🏭 صنعت شرکت خود را انتخاب کنید:", paginate(INDUSTRIES, [], "ind", 0, cols=1))
    elif state == ER_PHONE:
        await set_st(uid, ER_POSITION, emp_phone=text)
        await api.send_message(s, cid, "💼 سمت شغلی شما در سازمان:", reply_kb([["🔙 بازگشت"]]))
    elif state == ER_POSITION:
        await save_emp(s, cid, uid, text)

    # ── کارفرما: تکمیل پروفایل ──
    elif state == ER_ADDRESS:
        await set_st(uid, ER_EMAIL, emp_address=text if text != "0" else "")
        await api.send_message(s, cid, "📧 ایمیل (اختیاری - 0 برای رد):", reply_kb([["🔙 بازگشت"]]))
    elif state == ER_EMAIL:
        await set_st(uid, ER_WEBSITE, emp_email=text if text != "0" else "")
        await api.send_message(s, cid, "🌐 وب‌سایت (اختیاری - 0 برای رد):", reply_kb([["🔙 بازگشت"]]))
    elif state == ER_WEBSITE:
        await set_st(uid, ER_GEND, emp_website=text if text != "0" else "")
        kb = inline([[(g, f"egend:{g}")] for g in GENDERS])
        await api.send_message(s, cid, "👥 جنسیت مورد نیاز:", kb)
    elif state == ER_AGE:
        await set_st(uid, IDLE, emp_age=text)
        await api.send_message(s, cid, "✅ پروفایل کارفرما با موفقیت تکمیل شد.")
        user = await db.get_user(cid)
        if user: await show_menu(s, cid, user)

    # ── کارجو: ثبت‌نام ──
    elif state == JS_NAME:
        await set_st(uid, JS_PHONE, js_name=text)
        await api.send_message(s, cid, "📞 شماره تماس:", reply_kb([["🔙 بازگشت"]]))
    elif state == JS_PHONE:
        await set_st(uid, JS_PROV, js_phone=text)
        await api.send_message(s, cid, "🗺 استان محل سکونت خود را تعیین کنید:", paginate(PROVINCES, [], "prov", 0, cols=2))
    elif state == JS_JOB:
        await set_st(uid, JS_EXP, js_job_title=text)
        kb = inline([[(e, f"jsexp:{e}")] for e in EXPERIENCES])
        await api.send_message(s, cid, "📆 سطح تجربه:", kb)
    elif state == JS_SAL:
        try:
            val = int(re.sub(r'\D', '', text))
        except:
            val = 0
        await set_st(uid, JS_DOB, js_salary=val)
        await api.send_message(s, cid, "📅 تاریخ تولد یا سن (مثال: 1375/03/15 یا 25):", reply_kb([["🔙 بازگشت"]]))
    elif state == JS_DOB:
        await set_st(uid, JS_GEND, js_dob=text)
        kb = inline([[(g, f"jsgend:{g}")] for g in GENDERS])
        await api.send_message(s, cid, "👤 جنسیت:", kb)

    # ── آگهی ──
    elif state == JOB_TITLE:
        await set_st(uid, JOB_TYPE, job_title=text)
        kb = inline([[(t, "jtype:"+t)] for t in EMP_TYPES])
        await api.send_message(s, cid, "🤝 نوع همکاری:", kb)
    elif state == JOB_LOC:
        await set_st(uid, JOB_SAL, job_location=text)
        await api.send_message(s, cid, "💰 حقوق پیشنهادی (عدد به تومان - 0 برای توافقی):", reply_kb([["🔙 بازگشت"]]))
    elif state == JOB_SAL:
        try:
            val = int(re.sub(r'\D', '', text))
        except:
            val = 0
        await set_st(uid, JOB_CAT, job_salary=val)
        await api.send_message(s, cid, "🏷 دسته شغلی مربوطه:", paginate(CATEGORIES, [], "cat", 0))

    # ── ارسال رزومه ──
    elif state == RES_JOB:
        try:
            job_id = int(text)
            job = await db.get_job(job_id)
            if job and job["status"] == "active":
                await set_st(uid, RES_UPLOAD, target_job_id=job_id, target_job_title=job['title'])
                await api.send_message(s, cid, "📤 فایل رزومه (PDF یا عکس) را ارسال کنید\nیا متن رزومه را تایپ کنید:", reply_kb([["🔙 بازگشت"]]))
            else:
                await api.send_message(s, cid, "❌ آگهی مورد نظر یافت نشد یا غیرفعال است.")
        except:
            await api.send_message(s, cid, "❌ شماره آگهی باید عددی باشد.")
    elif state == RES_UPLOAD:
        file_id = doc.get("file_id") if doc else None
        if file_id or text:
            await finalize_application(s, cid, uid, file_id, text)
        else:
            await api.send_message(s, cid, "📤 لطفا فایل رزومه را آپلود کنید یا متن رزومه را بفرستید:")

    # ── حالت ناشناخته ──
    else:
        user = await db.get_user(cid)
        if user and user["role"]: await show_menu(s, cid, user)
        else: await welcome(s, cid, uid)


# ──────────────────────────────────────────────
# کالبک‌ها
# ──────────────────────────────────────────────
async def on_cb(s, cb):
    cid, uid, data, mid, cbid = cb_cid(cb), cb_uid(cb), cb.get("data", ""), cb_mid(cb), cb["id"]
    await api.answer_cb(s, cbid)

    user = await db.get_user(cid)
    d = await dt(uid)

    # ── انتخاب نقش ──
    if data.startswith("role:"):
        role = data.replace("role:", "")
        await db.upsert_user(cid, role=role)
        if role == "employer":
            await set_st(uid, ER_NAME)
            await api.send_message(s, cid, "👔 *فرم ثبت‌نام کارفرما*\n\nلطفا نام و نام خانوادگی خود را ارسال کنید:", reply_kb([["🔙 بازگشت"]]))
        else:
            await set_st(uid, JS_NAME)
            await api.send_message(s, cid, "🔍 *فرم ثبت‌نام کارجو*\n\nلطفا نام و نام خانوادگی خود را ارسال کنید:", reply_kb([["🔙 بازگشت"]]))
        return

    # ── عضویت در کانال ──
    if data == "joined:ok":
        user = await db.get_user(cid)
        if user and user["role"]:
            await show_menu(s, cid, user, "✅ عضویت با موفقیت تایید شد!")
        else:
            await welcome(s, cid, uid)
        return
    if data == "skip_channel":
        user = await db.get_user(cid)
        if user and user["role"]: await show_menu(s, cid, user)
        else: await welcome(s, cid, uid)
        return

    # ── صنعت (کارفرما) ──
    if data.startswith("ind:"):
        val = data.replace("ind:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(INDUSTRIES, [], "ind", p, cols=1))
            return
        if val == "DONE":
            ind = d.get("emp_industry")
            if not ind:
                await api.send_message(s, cid, "⚠️ لطفا یک صنعت انتخاب کنید.")
                return
            await set_st(uid, ER_PHONE)
            await api.send_message(s, cid, "📞 شماره تماس (الزامی):", reply_kb([["🔙 بازگشت"]]))
            return
        await set_st(uid, ER_INDUSTRY, emp_industry=val)
        await api.edit_reply_markup(s, cid, mid, paginate(INDUSTRIES, [val], "ind", d.get("_ip", 0), cols=1))
        return

    # ── استان (کارجو) ──
    if data.startswith("prov:"):
        val = data.replace("prov:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [], "prov", p, cols=2))
            return
        if val == "DONE":
            prov = d.get("js_province")
            if not prov:
                await api.send_message(s, cid, "⚠️ لطفا یک استان انتخاب کنید.")
                return
            await set_st(uid, JS_JOB)
            await api.send_message(s, cid, "💼 عنوان شغل مورد نظر شما چیست؟ (متن آزاد):", reply_kb([["🔙 بازگشت"]]))
            return
        await set_st(uid, JS_PROV, js_province=val)
        await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, [val], "prov", d.get("_pp", 0), cols=2))
        return

    # ── استان‌های مورد نظر (چند انتخابی برای کارجو) ──
    if data.startswith("prov2:"):
        val = data.replace("prov2:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            sel = d.get("js_cities", [])
            await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, sel, "prov2", p, cols=2))
            return
        if val == "DONE":
            await set_st(uid, JS_CATS)
            sel = d.get("js_cities", [])
            await api.send_message(s, cid, "🏷 دسته‌های شغلی مورد علاقه (حداکثر ۳ تا):", paginate(CATEGORIES, [], "jscat", 0))
            return
        sel = d.setdefault("js_cities", [])
        if val in sel:
            sel.remove(val)
        else:
            sel.append(val)
        await api.edit_reply_markup(s, cid, mid, paginate(PROVINCES, sel, "prov2", d.get("_pp2", 0), cols=2))
        return

    # ── دسته‌های شغلی کارجو ──
    if data.startswith("jscat:"):
        val = data.replace("jscat:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            sel = d.get("js_categories", [])
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, sel, "jscat", p))
            return
        if val == "DONE":
            await save_js(s, cid, uid)
            return
        sel = d.setdefault("js_categories", [])
        if val in sel:
            sel.remove(val)
        elif len(sel) < 3:
            sel.append(val)
        else:
            await api.send_message(s, cid, "⚠️ حداکثر ۳ دسته می‌توانید انتخاب کنید.")
            return
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, sel, "jscat", d.get("_jsc", 0)))
        return

    # ── جنسیت کارفرما ──
    if data.startswith("egend:"):
        await set_st(uid, ER_AGE, emp_gender=data.replace("egend:", ""))
        await api.send_message(s, cid, "📅 محدوده سنی (مثال: 25-40 یا 0 برای رد):", reply_kb([["🔙 بازگشت"]]))
        return

    # ── نوع همکاری ──
    if data.startswith("jtype:"):
        await set_st(uid, JOB_LOC, job_emp_type=data.replace("jtype:", ""))
        await api.send_message(s, cid, "📍 آدرس محل کار:", reply_kb([["🔙 بازگشت"]]))
        return

    # ── دسته شغلی آگهی ──
    if data.startswith("cat:"):
        val = data.replace("cat:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [], "cat", p))
            return
        if val == "DONE":
            cat = d.get("job_category")
            if not cat:
                await api.send_message(s, cid, "⚠️ لطفا یک دسته‌بندی انتخاب کنید.")
                return
            await finalize_job(s, cid, uid)
            return
        await set_st(uid, JOB_CAT, job_category=val)
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [val], "cat", d.get("_jc", 0)))
        return

    # ── جستجو بر اساس دسته ──
    if data.startswith("scat:"):
        val = data.replace("scat:", "")
        if val.startswith("PAGE:"):
            p = int(val.split(":")[1])
            await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [], "scat", p))
            return
        if val == "DONE":
            cat = d.get("search_cat")
            if not cat:
                await api.send_message(s, cid, "⚠️ لطفا یک دسته انتخاب کنید.")
                return
            await do_search(s, cid, uid)
            return
        await set_st(uid, SEARCH_CAT, search_cat=val)
        await api.edit_reply_markup(s, cid, mid, paginate(CATEGORIES, [val], "scat", d.get("_sc", 0)))
        return

    # ── سطح تجربه ──
    if data.startswith("jsexp:"):
        await set_st(uid, JS_SAL, js_experience=data.replace("jsexp:", ""))
        await api.send_message(s, cid, "💰 حقوق مورد انتظار (عدد به تومان - 0 برای توافقی):", reply_kb([["🔙 بازگشت"]]))
        return

    # ── جنسیت کارجو ──
    if data.startswith("jsgend:"):
        await set_st(uid, JS_RELOC, js_gender=data.replace("jsgend:", ""))
        kb = inline([[(r, f"jsreloc:{r}")] for r in RELOCATE])
        await api.send_message(s, cid, "🚗 آیا آماده نقل مکان هستید؟", kb)
        return

    # ── نقل مکان ──
    if data.startswith("jsreloc:"):
        await set_st(uid, JS_CITIES, js_relocate=data.replace("jsreloc:", ""))
        await api.send_message(s, cid, "🗺 استان‌های مورد نظر برای کار (چند انتخابی):", paginate(PROVINCES, [], "prov2", 0, cols=2))
        return

    # ── تأیید/رد ادمین ──
    if data.startswith("admjob:"):
        job_id = int(data.split(":")[1])
        await db.approve_job(job_id)
        job = await db.get_job(job_id)
        if job:
            await api.send_message(s, cid, f"✅ آگهی {job_id} بنام '{job['title']}' تایید و فعال شد.")
            try:
                await api.send_message(s, job['emp_cid'],
                    f"🎉 کارفرمای گرامی، آگهی استخدامی شما بنام '{job['title']}' تایید و در کانال‌ها منتشر شد.\n\n🏢 شریکِ مسیرِ رشدِ سازمان‌ها")
            except: pass
        else:
            await api.send_message(s, cid, f"✅ آگهی {job_id} تایید شد.")
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
        await api.send_message(s, cid, f"✅ رزومه {app_id} تایید شد.")
        await adm_apps(s, cid)
        return

    if data.startswith("admrejectapp:"):
        app_id = int(data.split(":")[1])
        await db.reject_application(app_id)
        await api.send_message(s, cid, f"❌ رزومه {app_id} رد شد.")
        await adm_apps(s, cid)
        return

    # ── تغییر نقش ──
    if data == "cr:yes":
        user = await db.get_user(cid)
        old = user["role"] if user else None
        new = "job_seeker" if old == "employer" else "employer"
        await db.upsert_user(cid, role=new, emp_name=None, emp_company=None)
        await clear(uid)
        if new == "employer":
            await set_st(uid, ER_NAME)
            await api.send_message(s, cid, "👔 نقش به کارفرما تغییر یافت.\nلطفا نام و نام خانوادگی:", reply_kb([["🔙 بازگشت"]]))
        else:
            await set_st(uid, JS_NAME)
            await api.send_message(s, cid, "🔍 نقش به کارجو تغییر یافت.\nلطفا نام و نام خانوادگی:", reply_kb([["🔙 بازگشت"]]))
        return

    if data == "cr:no":
        await clear(uid)
        user = await db.get_user(cid)
        if user: await show_menu(s, cid, user)
        return


# ──────────────────────────────────────────────
# توابع اصلی
# ──────────────────────────────────────────────

async def welcome(s, cid, uid):
    await clear(uid)
    kb = inline([[("👔 کارفرما", "role:employer"), ("🔍 کارجو", "role:job_seeker")]])
    await api.send_message(s, cid,
        "🌟 *به رسانه استخدامی همراکار خوش آمدید*\n\n"
        "✨ ما به توان انسان‌ها باور داریم ✨\n\n"
        "لطفا نقش خود را گزینش کنید:", kb)

async def cmd_start(s, cid, uid):
    user = await db.get_user(cid)
    if user and user["role"]:
        await show_menu(s, cid, user)
    else:
        text = "«اگر دوست دارید عضو کانال‌های ما شوید و ما را خوشحال کنید، می‌توانید عضو شوید. در غیر این صورت، می‌توانید از این مرحله عبور کنید.»"
        await api.send_message(s, cid, text,
            inline([[("✅ عضو شدم", "joined:ok"), ("⏭ بعداً", "skip_channel")]]))

async def cmd_menu(s, cid):
    user = await db.get_user(cid)
    if user and user["role"]: await show_menu(s, cid, user)
    else: await welcome(s, cid, 0)

async def cmd_profile(s, cid):
    user = await db.get_user(cid)
    if not user:
        await api.send_message(s, cid, "⚠️ کاربری با شناسه شما ثبت نشده است.")
        return
    if user["role"] == "employer":
        text = (f"👔 *پروفایل کارفرما*\n\n"
                f"👤 نام: {user['emp_name'] or '—'}\n"
                f"🏢 شرکت: {user['emp_company'] or '—'}\n"
                f"🏭 صنعت: {user['emp_industry'] or '—'}\n"
                f"📞 تلفن: {user['emp_phone'] or '—'}\n"
                f"💼 سمت: {user['emp_position'] or '—'}\n"
                f"📍 آدرس: {user['emp_address'] or '—'}\n"
                f"📅 تاریخ ثبت: {user['created_at']}")
    else:
        text = (f"👤 *پروفایل کارجو*\n\n"
                f"👤 نام: {user['js_name'] or '—'}\n"
                f"📞 تلفن: {user['js_phone'] or '—'}\n"
                f"🗺 استان: {user['js_province'] or '—'}\n"
                f"💼 شغل: {user['js_job_title'] or '—'}\n"
                f"📆 تجربه: {user['js_experience'] or '—'}\n"
                f"💰 حقوق: {fmt_salary(user['js_salary'])}\n"
                f"⭐ امتیاز: {user['js_rating'] or 5.0}")
    await api.send_message(s, cid, text, menu_for(user))

async def cmd_help(s, cid):
    user = await db.get_user(cid)
    await api.send_message(s, cid,
        "📖 *راهنمای ربات همراکار*\n\n"
        "👔 کارفرمایان:\n• ثبت آگهی استخدام\n• جستجوی کارجو\n• درخواست رزومه\n\n"
        "🔍 کارجویان:\n• جستجوی آگهی\n• ارسال رزومه\n• تکمیل پروفایل\n\n"
        "🙏 با تشکر از اعتماد شما",
        menu_for(user) if user else remove_kb())

async def cmd_stats(s, cid):
    if cid not in ADMIN_IDS: return
    stats = await db.get_stats()
    await api.send_message(s, cid,
        f"📊 *آمار ربات همراکار*\n\n"
        f"👥 کل کاربران: {stats['total']}\n"
        f"👔 کارفرمایان: {stats['employers']}\n"
        f"🔍 کارجویان: {stats['seekers']}\n"
        f"📋 آگهی فعال: {stats['active']}\n"
        f"⏳ در انتظار تایید: {stats['pending']}\n"
        f"📬 رزومه جدید: {stats['pending_apps']}")

async def cmd_settings(s, cid):
    user = await db.get_user(cid)
    if not user: return
    await api.send_message(s, cid,
        "⚙️ *تنظیمات*\n\n"
        "برای تکمیل پروفایل از بخش پروفایل استفاده کنید.",
        menu_for(user))

async def cmd_search(s, cid):
    user = await db.get_user(cid)
    if not user: return
    await api.send_message(s, cid,
        "🔎 *جستجوی کارجو*\n\n"
        "این قابلیت در حال توسعه است.",
        menu_for(user))

async def cmd_requests(s, cid):
    user = await db.get_user(cid)
    if not user or user["role"] != "employer": return
    await api.send_message(s, cid,
        "📬 *درخواست‌های رزومه*\n\n"
        "درخواست‌های شما در انتظار پاسخ کارجو در این بخش نمایش داده می‌شود.",
        menu_for(user))

# ── ثبت‌نام کارفرما ──
async def save_emp(s, cid, uid, position):
    d = await dt(uid)
    await db.upsert_user(cid,
        role="employer",
        emp_name=d.get("emp_name"),
        emp_company=d.get("emp_company"),
        emp_industry=d.get("emp_industry"),
        emp_phone=d.get("emp_phone"),
        emp_position=position)
    await clear(uid)
    user = await db.get_user(cid)
    await api.send_message(s, cid, "🎉 *ثبت‌نام کارفرما تکمیل شد!*\n\n🏢 شریکِ مسیرِ رشدِ سازمان‌ها")
    await show_menu(s, cid, user)

# ── ثبت‌نام کارجو ──
async def save_js(s, cid, uid):
    d = await dt(uid)
    await db.upsert_user(cid,
        role="job_seeker",
        js_name=d.get("js_name"),
        js_phone=d.get("js_phone"),
        js_province=d.get("js_province"),
        js_job_title=d.get("js_job_title"),
        js_experience=d.get("js_experience"),
        js_salary=d.get("js_salary", 0),
        js_dob=d.get("js_dob"),
        js_gender=d.get("js_gender"),
        js_relocate=d.get("js_relocate"),
        js_cities=",".join(d.get("js_cities", [])),
        js_categories=",".join(d.get("js_categories", [])))
    await clear(uid)
    user = await db.get_user(cid)
    await api.send_message(s, cid, "🎉 *ثبت‌نام کارجو تکمیل شد!*\n\n🔍 شریکِ مسیرِ رشدِ شغلی شما")
    await show_menu(s, cid, user)

# ── آگهی ──
async def start_job(s, cid, uid):
    user = await db.get_user(cid)
    if not user or user["role"] != "employer":
        await api.send_message(s, cid, "⛔ این بخش فقط برای کارفرمایان است."); return
    await clear(uid)
    await set_st(uid, JOB_TITLE)
    await api.send_message(s, cid, "📝 *ثبت آگهی جدید*\n\nعنوان شغل را وارد کنید:", reply_kb([["🔙 بازگشت"]]))

async def finalize_job(s, cid, uid):
    d = await dt(uid)
    if not d.get("job_title") or not d.get("job_category"):
        await api.send_message(s, cid, "❌ اطلاعات ناقص است."); return
    user = await db.get_user(cid)
    job_id = await db.create_job(
        emp_cid=cid,
        title=d["job_title"],
        emp_type=d.get("job_emp_type", "تمام وقت"),
        location=d.get("job_location", "نامشخص"),
        salary=d.get("job_salary", 0),
        category=d["job_category"])
    await clear(uid)
    await api.send_message(s, cid, f"✅ آگهی شما ثبت شد.\n⏳ در انتظار تأیید ادمین.")
    await notify_admins(s,
        f"🔔 آگهی جدید: {d['job_title']}\nدسته: {d['job_category']}\njob_id: {job_id}",
        inline([[("✅ تأیید", f"admjob:{job_id}"), ("❌ رد", f"admreject:{job_id}")]]))
    user = await db.get_user(cid)
    await show_menu(s, cid, user)

async def my_jobs(s, cid):
    user = await db.get_user(cid)
    if not user or user["role"] != "employer": return
    jobs = await db.get_employer_jobs(cid)
    if not jobs:
        await api.send_message(s, cid, "📭 آگهی‌ای ندارید.", menu_for(user))
        return
    st_map = {"active": "✅ فعال", "pending": "⏳ در انتظار", "rejected": "❌ رد شده"}
    for job in jobs[:10]:
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n"
            f"🏷 {job['category']}\n"
            f"💰 {fmt_salary(job['salary'])}\n"
            f"📌 {st_map.get(job['status'], job['status'])}")
    await show_menu(s, cid, user)

# ── جستجوی آگهی ──
async def start_search(s, cid, uid):
    user = await db.get_user(cid)
    if not user or user["role"] != "job_seeker": return
    await clear(uid)
    await set_st(uid, SEARCH_CAT)
    await api.send_message(s, cid, "🏷 دسته شغلی مورد نظر را انتخاب کنید:", paginate(CATEGORIES, [], "scat", 0))

async def do_search(s, cid, uid):
    d = await dt(uid)
    jobs = await db.get_jobs(category=d.get("search_cat"))
    await clear(uid)
    user = await db.get_user(cid)
    if not jobs:
        await api.send_message(s, cid, "❌ آگهی‌ای یافت نشد.", menu_for(user))
        return
    for job in jobs[:10]:
        emp = await db.get_user(job["emp_cid"])
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n"
            f"🏢 {emp['emp_company'] if emp else '—'}\n"
            f"💰 {fmt_salary(job['salary'])}\n"
            f"🤝 {job['emp_type']}\n"
            f"📍 {job['location']}\n"
            f"🏷 {job['category']}",
            inline([[("📄 ارسال رزومه", f"applyjob:{job['job_id']}")]]))
    await show_menu(s, cid, user)

# ── ارسال رزومه ──
async def start_resume(s, cid, uid):
    user = await db.get_user(cid)
    if not user or user["role"] != "job_seeker": return
    if not (user.get("js_name") and user.get("js_phone")):
        await api.send_message(s, cid, "⚠️ ابتدا پروفایل خود را تکمیل کنید.")
        return
    await clear(uid)
    await set_st(uid, RES_JOB)
    await api.send_message(s, cid, "🔍 شماره (ID) آگهی را وارد کنید:", reply_kb([["🔙 بازگشت"]]))

async def finalize_application(s, cid, uid, file_id, text_resume):
    d = await dt(uid)
    job_id = d.get("target_job_id")
    job_title = d.get("target_job_title")
    if not job_id: return
    job = await db.get_job(job_id)
    if not job: return
    await db.create_application(
        job_id=job_id,
        seeker_cid=cid,
        employer_id=job["emp_cid"],
        resume_file=file_id or "",
        resume_text=text_resume or "")
    await clear(uid)
    user = await db.get_user(cid)
    await api.send_message(s, cid,
        f"✅ رزومه شما برای *{job_title}* ارسال شد.\n🙏 با تشکر از اعتماد شما", menu_for(user))
    await notify_admins(s, f"📬 رزومه جدید برای '{job_title}' ارسال شد.")

async def my_apps(s, cid):
    user = await db.get_user(cid)
    if not user or user["role"] != "job_seeker": return
    apps = await db.get_seeker_applications(cid)
    if not apps:
        await api.send_message(s, cid, "📭 درخواستی ارسال نکرده‌اید.", menu_for(user))
        return
    st_map = {"pending_admin": "⏳ در انتظار", "approved": "✅ تأیید شده", "rejected": "❌ رد شده"}
    for app in apps[:10]:
        await api.send_message(s, cid,
            f"📄 *{app['title']}*\n"
            f"وضعیت: {st_map.get(app['status'], app['status'])}\n"
            f"📅 {app['sent_date']}")
    await show_menu(s, cid, user)

# ── پنل ادمین ──
async def adm_jobs(s, cid):
    if cid not in ADMIN_IDS: return
    jobs = await db.get_pending_jobs()
    if not jobs:
        await api.send_message(s, cid, "✅ آگهی در انتظار وجود ندارد.", adm_menu())
        return
    for job in jobs[:5]:
        company = job.get("emp_company") or "نامشخص"
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n🏢 {company}\n🏷 {job['category']}",
            inline([[("✅ تأیید", f"admjob:{job['job_id']}"), ("❌ رد", f"admreject:{job['job_id']}")]]))

async def adm_apps(s, cid):
    if cid not in ADMIN_IDS: return
    apps = await db.get_pending_applications()
    if not apps:
        await api.send_message(s, cid, "✅ رزومه جدیدی وجود ندارد.")
        return
    for app in apps[:5]:
        name = app.get("js_name") or "نامشخص"
        await api.send_message(s, cid,
            f"👤 {name}\n💼 {app.get('job_title', '')}",
            inline([[("✅ تأیید", f"admapp:{app['app_id']}"), ("❌ رد", f"admrejectapp:{app['app_id']}")]]))

# ── تغییر نقش ──
async def start_changerole(s, cid, uid):
    await clear(uid)
    await api.send_message(s, cid,
        "🔄 *تغییر نقش*\n\nآیا مطمئن هستید؟",
        inline([[("✅ بله", "cr:yes"), ("❌ خیر", "cr:no")]]))


# ── حلقه اصلی ──
async def main():
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ توکن تنظیم نشده!")
        return
    api.set_token(TOKEN)
    await db.init_db()
    log.info("✅ ربات همراکار شروع شد...")
    offset = 0
    async with aiohttp.ClientSession() as s:
        me = await api.get_me(s)
        if not me.get("ok"):
            log.error("❌ اتصال به بله برقرار نشد.")
            return
        log.info(f"✅ متصل شد: {me.get('result', {}).get('username')}")
        while True:
            try:
                resp = await api.get_updates(s, offset=offset)
                if not resp.get("ok"):
                    await asyncio.sleep(5)
                    continue
                for upd in resp.get("result", []):
                    offset = upd["update_id"] + 1
                    try: await process(s, upd)
                    except Exception as e: log.error(f"❌ خطا: {e}")
            except asyncio.CancelledError: break
            except Exception as e:
                log.error(f"❌ خطای polling: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
