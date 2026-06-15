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

# وضعیت‌های ثبت‌نام
IDLE = "IDLE"
ER_NAME, ER_COMPANY, ER_INDUSTRY, ER_PHONE, ER_POSITION = "ER_NAME", "ER_COMPANY", "ER_INDUSTRY", "ER_PHONE", "ER_POSITION"
ER_ADDRESS, ER_EMAIL, ER_WEBSITE, ER_GEND, ER_AGE = "ER_ADDRESS", "ER_EMAIL", "ER_WEBSITE", "ER_GEND", "ER_AGE"
JS_NAME, JS_PHONE, JS_PROV, JS_JOB, JS_EXP, JS_SAL = "JS_NAME", "JS_PHONE", "JS_PROV", "JS_JOB", "JS_EXP", "JS_SAL"
JS_DOB, JS_GEND, JS_RELOC, JS_CITIES, JS_CATS, JS_SKILLS = "JS_DOB", "JS_GEND", "JS_RELOC", "JS_CITIES", "JS_CATS", "JS_SKILLS"
JOB_TITLE, JOB_TYPE, JOB_LOC, JOB_SAL, JOB_CAT, JOB_GEND, JOB_AGE = "JOB_TITLE", "JOB_TYPE", "JOB_LOC", "JOB_SAL", "JOB_CAT", "JOB_GEND", "JOB_AGE"
JOB_PRIORITY = "JOB_PRIORITY"
SEARCH_CAT, SEARCH_PROV = "SEARCH_CAT", "SEARCH_PROV"
RES_JOB, RES_UPLOAD = "RES_JOB", "RES_UPLOAD"
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

async def on_msg(s, msg):
    cid, uid, text = msg_cid(msg), msg_uid(msg), msg_text(msg)
    doc = msg_doc(msg)
    state = await st(uid)

    if text in ("🔙 بازگشت", "🔙 بازگشت به منو", "🔙 منو"):
        await clear(uid)
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
        
    elif state == JS_NAME:
        await set_st(uid, JS_PHONE, js_name=text)
        await api.send_message(s, cid, "📞 شماره تماس:", reply_kb([["🔙 بازگشت"]]))
    elif state == JS_PHONE:
        await set_st(uid, JS_PROV, js_phone=text)
        await api.send_message(s, cid, "🗺 استان محل سکونت خود را تعیین کنید:", paginate(PROVINCES, [], "prov", 0, cols=2))
        
    elif state == JOB_TITLE:
        await set_st(uid, JOB_TYPE, job_title=text)
        kb = inline([[(t, "jtype:"+t)] for t in EMP_TYPES])
        await api.send_message(s, cid, "🤝 نوع همکاری:", kb)
    elif state == JOB_LOC:
        await set_st(uid, JOB_SAL, job_location=text)
        await api.send_message(s, cid, "💰 حقوق پیشنهادی (عدد به تومان):", reply_kb([["🔙 بازگشت"]]))
    elif state == JOB_SAL:
        try:
            val = int(re.sub(r'\D', '', text))
        except:
            val = 0
        await set_st(uid, JOB_CAT, job_salary=val)
        await api.send_message(s, cid, "🏷 دسته شغلی مربوطه:", paginate(CATEGORIES, [], "cat", 0))

    elif state == RES_JOB:
        try:
            job_id = int(text)
            job = await db.get_job(job_id)
            if job and job["status"] == "active":
                await set_st(uid, RES_UPLOAD, target_job_id=job_id, target_job_title=job['title'])
                await api.send_message(s, cid, f"📤 لطفا فایل رزومه (PDF یا عکس) خود را ارسال کنید:", reply_kb([["🔙 بازگشت"]]))
            else:
                await api.send_message(s, cid, "❌ آگهی مورد نظر یافت نشد یا غیرفعال است.")
        except:
            await api.send_message(s, cid, "❌ شماره آگهی باید عددی باشد.")
    elif state == RES_UPLOAD:
        file_id = doc.get("file_id") if doc else None
        if file_id or text:
            await finalize_application(s, cid, uid, file_id, text)
        else:
            await api.send_message(s, cid, "📤 لطفا فایل رزومه را برای ارسال آپلود کنید یا متن رزومه را بفرستید:")
            
    else:
        user = await db.get_user(cid)
        if user and user["role"]: await show_menu(s, cid, user)
        else: await welcome(s, cid, uid)

async def on_cb(s, cb):
    cid, uid, data, mid, cbid = cb_cid(cb), cb_uid(cb), cb.get("data",""), cb_mid(cb), cb["id"]
    await api.answer_cb(s, cbid)

    user = await db.get_user(cid)
    d = await dt(uid)

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

    if data.startswith("jtype:"):
        val = data.replace("jtype:", "")
        await set_st(uid, JOB_LOC, job_emp_type=val)
        await api.send_message(s, cid, "📍 آدرس حدودی یا لوکیشن محل کار را تایپ کنید:", reply_kb([["🔙 بازگشت"]]))
        return

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

    if data.startswith("admjob:"):
        job_id = int(data.split(":")[1])
        await db.approve_job(job_id)
        job = await db.get_job(job_id)
        await api.send_message(s, cid, f"✅ آگهی {job_id} بنام '{job['title']}' تایید و فعال شد.")
        try:
            await api.send_message(s, job['employer_id'], f"🎉 کارفرمای گرامی، آگهی استخدامی شما بنام '{job['title']}' تایید و در کانال‌ها منتشر شد.\n\n🏢 شریکِ مسیرِ رشدِ سازمان‌ها")
        except: pass
        await adm_jobs(s, cid)
        return

    if data.startswith("admapp:"):
        app_id = int(data.split(":")[1])
        await db.approve_application(app_id)
        await api.send_message(s, cid, f"✅ رزومه ملحق به درخواست {app_id} تایید شد.")
        await adm_apps(s, cid)
        return

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
        text = ("«اگر دوست دارید عضو کانال‌های ما شوید و ما را خوشحال کنید، می‌توانید عضو شوید. "
                "در غیر این صورت، می‌توانید از این مرحله عبور کنید.»")
        await api.send_message(s, cid, text,
            inline([[("✅ عضو شدم", "joined:ok"), ("⏭ بعداً", "skip_channel")]])
        )

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
        text = (f"👔 *پروفایل کارفرما سازمان*\n\n"
                f"👤 نام: {user['emp_name'] or '—'}\n"
                f"🏢 شرکت: {user['emp_company'] or '—'}\n"
                f"🏭 صنعت: {user['emp_industry'] or '—'}\n"
                f"📞 تلفن: {user['emp_phone'] or '—'}\n"
                f"💼 سمت: {user['emp_position'] or '—'}\n"
                f"📅 تاریخ ثبت: {user['created_at']}")
    else:
        text = (f"👤 *پروفایل تخصصی کارجو*\n\n"
                f"👤 نام کامل: {user['js_name'] or '—'}\n"
                f"📞 تلفن تماس: {user['js_phone'] or '—'}\n"
                f"🗺 استان: {user['js_province'] or '—'}\n"
                f"💼 شغل انتخابی: {user['js_job_title'] or '—'}\n"
                f"⭐ امتیاز کنونی: {user['rating'] or 5.0}")
    await api.send_message(s, cid, text, menu_for(user))

async def cmd_help(s, cid):
    user = await db.get_user(cid)
    await api.send_message(s, cid,
        "📖 *راهنمای بخش‌های ربات همراکار*\n\n"
        "👔 بخش کارفرمایان: ثبت آگهی‌های مدرن سازمانی و شکار هوشمند کارجویان.\n"
        "🔍 بخش کارجویان: یافتن برترین فرصت‌های کسب‌وکار ایران و ارسال آنی رزومه.\n\n"
        "🙏 با تشکر از اعتماد شما",
        menu_for(user) if user else remove_kb())

async def cmd_stats(s, cid):
    if cid not in ADMIN_IDS: return
    stats = await db.get_stats()
    await api.send_message(s, cid,
        f"📊 *آمار کلی ربات همراکار*\n\n"
        f"👥 کل کاربران فعال: {stats['total']}\n"
        f"👔 کارفرمایان ثبت‌شده: {stats['employers']}\n"
        f"🔍 کارجویان فعال: {stats['seekers']}\n"
        f"📋 آگهی‌های زنده تایید شده: {stats['active']}\n"
        f"📬 رزومه‌های تایید شده نهایی: {stats['pending_apps']}")

async def cmd_settings(s, cid):
    user = await db.get_user(cid)
    if not user: return
    await api.send_message(s, cid, "⚙️ *تنظیمات حساب کاربری*\n\nامکان پیکربندی اعلان‌ها و وضعیت حریم خصوصی شما.", menu_for(user))

async def cmd_search(s, cid):
    user = await db.get_user(cid)
    if not user: return
    await api.send_message(s, cid, "🔎 *جستجوی رزومه کارجویان*\n\nبرای دستیابی به قابلیت‌های پیشرفته، پروفایل خود را تکمیل کنید.", menu_for(user))

async def cmd_requests(s, cid):
    user = await db.get_user(cid)
    if not user or user["role"] != "employer": return
    await api.send_message(s, cid, "📬 *درخواست‌های مشاهده رزومه*\n\nمجموعه تقاضاهای شما در انتظار پاسخ کارجو در این بخش نمایان خواهد شد.", menu_for(user))

async def start_job(s, cid, uid):
    user = await db.get_user(cid)
    if not user or user["role"] != "employer":
        await api.send_message(s, cid, "⛔ دسترسی غیرمجاز. این بخش برای کارفرمایان است."); return
    await clear(uid)
    await set_st(uid, JOB_TITLE)
    await api.send_message(s, cid, "📝 *ثبت فرصت شغلی جدید*\n\nلطفا عنوان آگهی را تایپ کنید (مثال: کارمند امور اداری):", reply_kb([["🔙 بازگشت"]]))

async def finalize_job(s, cid, uid):
    d = await dt(uid)
    if not d.get("job_title") or not d.get("job_category"):
        await api.send_message(s, cid, "❌ خطا! اطلاعات ثبت آگهی ناقص است."); return
    
    user = await db.get_user(cid)
    job_id = await db.create_job(
        employer_id=cid,
        title=d["job_title"],
        type=d.get("job_emp_type", "تمام وقت"),
        priority="🔵 عادی",
        location=d.get("job_location", "نامشخص"),
        salary=d.get("job_salary", 0),
        category=d["job_category"],
        gender_req="بدون ترجیح",
        age_req="بدون ترجیح"
    )
    await clear(uid)
    await api.send_message(s, cid, f"✅ آگهی کارسپاری شما با موفقیت به سیستم ارسال شد.\n⏳ این آگهی پس از بازنگری ادمین تایید و منتشر خواهد شد.")
    await notify_admins(s, f"🔔 *یک آگهی جدید استخدام جهت بازنگری ثبت شد:*\n\n💼 عنوان: {d['job_title']}\n🏢 کارفرما: {user['emp_company'] if user else 'نامعلوم'}\n\nموافقت با انتشار؟",
        inline([[("✅ تایید آگهی", f"admjob:{job_id}"), ("❌ رد آگهی", f"admreject:{job_id}")]])
    )
    user = await db.get_user(cid)
    await show_menu(s, cid, user)

async def my_jobs(s, cid):
    user = await db.get_user(cid)
    if not user or user["role"] != "employer": return
    jobs = await db.get_employer_jobs(cid)
    if not jobs: 
        await api.send_message(s, cid, "📭 لیست آگهی‌های شما خالی است.", menu_for(user))
        return
    for job in jobs[:10]:
        st_map = {"active": "✅ فعال", "pending_admin": "⏳ در انتظار تایید", "rejected": "❌ رد شده"}
        await api.send_message(s, cid,
            f"💼 *{job['title']}*\n"
            f"🏷 دسته: {job['category']}\n"
            f"💰 حقوق پیشنهادی: {fmt_salary(job['salary'])}\n"
            f"⚙️ وضعیت: {st_map.get(job['status'], job['status'])}")
    await show_menu(s, cid, user)

async def start_search(s, cid, uid):
    user = await db.get_user(cid)
    if not user or user["role"] != "job_seeker": return
    await clear(uid)
    await set_st(uid, SEARCH_PROV)
    await api.send_message(s, cid, "🗺 لطفا استان محل کار مدنظر خود را انتخاب کنید:", paginate(PROVINCES, [], "sprov", 0, cols=2))

async def start_resume(s, cid, uid):
    user = await db.get_user(cid)
    if not user or user["role"] != "job_seeker": return
    await clear(uid)
    await set_st(uid, RES_JOB)
    await api.send_message(s, cid, "🔍 لطفا شماره شناسایی (ID) آگهی دریافتی را تایپ کنید:", reply_kb([["🔙 بازگشت"]]))

async def finalize_application(s, cid, uid, file_id, text_resume):
    d = await dt(uid)
    job_id = d.get("target_job_id")
    job_title = d.get("target_job_title")
    if not job_id: return
    job = await db.get_job(job_id)
    if not job: return
    
    await db.create_application(
        job_id=job_id,
        seeker_id=cid,
        employer_id=job["employer_id"],
        resume_file=file_id or "",
        resume_text=text_resume or ""
    )
    await clear(uid)
    user = await db.get_user(cid)
    
    await api.send_message(s, cid,
        f"✅ درخواست همکاری شما برای فرصت شغلی *{job_title}* با موفقیت مخابره شد.\n\n🙏 با تشکر از اعتماد شما",
        menu_for(user)
    )
    await notify_admins(s, f"📬 *یک رزومه جدید کارجو برای فرصت شغلی '{job_title}' ثبت شد.*")

async def my_apps(s, cid):
    user = await db.get_user(cid)
    if not user or user["role"] != "job_seeker": return
    await api.send_message(s, cid, "📊 تراکنش‌ها و پرونده‌های ارسالی شما در حال بازخوانی از سرور است...", menu_for(user))

async def adm_jobs(s, cid):
    if cid not in ADMIN_IDS: return
    jobs = await db.get_pending_jobs()
    if not jobs: 
        await api.send_message(s, cid, "✅ هیچ آگهی در صف انتشار ادمین قرار ندارد.", adm_menu())
        return
    for job in jobs[:5]:
        await api.send_message(s, cid,
            f"💼 *آگهی استخدام:* {job['title']}\n"
            f"🏢 کارفرما: {job['emp_company']}\n"
            f"🏷 دسته: {job['category']}",
            inline([[("✅ تایید", f"admjob:{job['job_id']}"), ("❌ رد", f"admreject:{job['job_id']}")]])
        )

async def adm_apps(s, cid):
    if cid not in ADMIN_IDS: return
    apps = await db.get_pending_applications()
    if not apps:
        await api.send_message(s, cid, "✅ رزومه جدیدی جهت بررسی ثبتی وجود ندارد.")
        return
    for app in apps[:5]:
        await api.send_message(s, cid,
            f"👤 کارجو: {app['js_name']}\n"
            f"💼 فرصت: {app['job_title']}",
            inline([[("✅ تایید الحاق", f"admapp:{app['app_id']}")]])
        )

async def save_emp(s, cid, uid, position):
    d = await dt(uid)
    await db.upsert_user(
        cid,
        role="employer",
        emp_name=d.get("emp_name"),
        emp_company=d.get("emp_company"),
        emp_industry=d.get("emp_industry"),
        emp_phone=d.get("emp_phone"),
        emp_position=position
    )
    await clear(uid)
    user = await db.get_user(cid)
    await api.send_message(s, cid, "🎉 *مراحل ثبت‌نام اولیه کارفرمای شما نهایی شد!*\n\n🏢 شریکِ مسیرِ رشدِ سازمان‌ها")
    await show_menu(s, cid, user)

async def start_changerole(s, cid, uid):
    await clear(uid)
    await api.send_message(s, cid,
        "🔄 *تغییر نقش کاربری*\n\nدر صورت تعویض نقش، اطلاعات پایگاه داده شما جهت مراجعات بعدی امن خواهد ماند ولی نقش کاری تغییر می‌کند.\nآیا اطمینان دارید؟",
        inline([[("✅ بله تعویض نقش", "cr:yes"), ("❌ خیر انصراف", "cr:no")]]))

async def main():
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Bot Token is missing from .env configuration.")
        return
    api.set_token(TOKEN)
    await db.init_db()
    log.info("✅ Core process started!")
    offset = 0
    async with aiohttp.ClientSession() as s:
        me = await api.get_me(s)
        if not me.get("ok"):
            log.error("❌ Link connection to Bale API server failed.")
            return
        log.info(f"✅ Bot connected successfully as: {me.get('result', {}).get('username')}")
        while True:
            try:
                resp = await api.get_updates(s, offset=offset)
                if not resp.get("ok"):
                    await asyncio.sleep(5)
                    continue
                for upd in resp.get("result", []):
                    offset = upd["update_id"] + 1
                    try: 
                        await process(s, upd)
                    except Exception as e: 
                        log.error(f"❌ Msg handler exception: {e}")
            except asyncio.CancelledError: break
            except Exception as e:
                log.error(f"❌ Base polling error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())