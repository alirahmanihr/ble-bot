# bot.py
import asyncio, aiohttp, json
import bale_api as api
import database as db
from config import TOKEN, FOOTER, BOT_NAME, SLOGAN

async def handle_update(s, cid, text, cb=None):
    state, sdata = db.get_state(cid)
    
    if text in ["/start", "🔙 بازگشت"]:
        db.set_state(cid, "START")
        await api.send_message(s, cid, f"سلام به {BOT_NAME} خوش آمدید.", api.reply_kb([["👤 کارجو", "🏢 کارفرما"]]))
        return

    # مسیر کارجو
    if state == "START" and text == "👤 کارجو":
        db.upsert_user(cid, role="job_seeker")
        db.set_state(cid, "SEEKER_MAIN")
        await api.send_message(s, cid, "منوی کارجو:", api.reply_kb([["📝 ساخت رزومه", "🔍 جستجوی شغل"]]))
        return

    if state == "SEEKER_MAIN":
        if text == "📝 ساخت رزومه":
            db.set_state(cid, "RES_EXP")
            await api.send_message(s, cid, "سوابق کاری خود را بنویسید:", api.remove_kb())
        elif text == "🔍 جستجوی شغل":
            db.set_state(cid, "SEARCH_CAT")
            await api.send_message(s, cid, "دسته شغلی را وارد کنید:", api.remove_kb())
        return

    if state == "RES_EXP":
        db.upsert_user(cid, resume_experiences=text)
        db.set_state(cid, "SEEKER_MAIN")
        await api.send_message(s, cid, "رزومه ذخیره شد.", api.reply_kb([["📝 ساخت رزومه", "🔍 جستجوی شغل"]]))
        return

    # جستجوی شغل (نمایش با دکمه شیشه‌ای - قانون اصلی)
    if state == "SEARCH_CAT":
        # فرض بر این است که جستجو انجام شده
        # نمایش کارت شغل:
        card = f"💼 عنوان شغل: برنامه نویس\n📍 شهر: یزد\n💰 حقوق: توافقی{FOOTER}"
        kb = api.inline([[("📄 ارسال رزومه", "apply:123")]])
        await api.send_message(s, cid, card, kb)
        db.set_state(cid, "SEEKER_MAIN")
        return

    # پردازش دکمه‌های شیشه‌ای
    if cb and cb.startswith("apply:"):
        jid = cb.split(":")[1]
        kb = api.inline([[("✔️ ارسال رزومه اصلی", f"quick:{jid}")], [("📝 رزومه جدید", f"custom:{jid}")]])
        await api.send_message(s, cid, "نحوه ارسال رزومه را انتخاب کنید:", kb)
        return

async def main():
    api.set_token(TOKEN)
    async with aiohttp.ClientSession() as s:
        offset = 0
        while True:
            resp = await api.get_updates(s, offset=offset)
            for upd in resp.get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    await handle_update(s, upd["message"]["chat"]["id"], upd["message"].get("text"))
                elif "callback_query" in upd:
                    await handle_update(s, upd["callback_query"]["from"]["id"], "", cb=upd["callback_query"]["data"])
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())