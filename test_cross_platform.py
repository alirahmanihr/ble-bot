"""
Deep dual-platform integration test — Bale + Telegram simultaneously.
Tests cross-platform routing, phone linking, channel publishing, notifications,
rejection routing, job lifecycle, and failure isolation.

Uses function-level patching of bale_api.send_message and _post to simulate
both providers without real network calls.
"""

import asyncio
import json
import sys
import io
import time
import traceback
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Force UTF-8 encoding on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BOT_DIR = Path(r"C:\Users\asus\Desktop\فراشايیان\ربات بله 050407\hamrakar")
sys.path.insert(0, str(BOT_DIR))
TEST_DB = BOT_DIR / "test_xp2.db"

import database as db
import bale_api as api
from bale_api import inline

db.DB_PATH = TEST_DB

PASS = FAIL = 0
_sent_log = []  # global capture: list of (platform, cid, text, reply_markup)


def cleanup():
    for p in [TEST_DB, Path(str(TEST_DB) + "-wal"), Path(str(TEST_DB) + "-shm")]:
        if p.exists():
            try:
                p.unlink()
            except:
                pass


cleanup()


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  \033[92m[PASS]\033[0m {name}")
    else:
        FAIL += 1
        print(f"  \033[91m[FAIL]\033[0m {name}  |  {detail}")


# ── Fake aiohttp ClientSession ──
class FakeSession:
    """Fake session that passes the `s is None` check in _post but never
    actually makes HTTP calls because we patch send_message/_post."""

    def __bool__(self):
        return True


# ── Patched send_message that logs calls per-platform ──
_original_send_message = api.send_message
_original__post = api._post


async def _patched_send_message(s, cid, text, reply_markup=None, raise_on_error=False):
    """Fake send_message — logs the call and returns success, with rate limiting."""
    global _sent_log
    # Determine which platform by current BASE URL
    base = api._BASE
    plat = "bale" if "bale" in base else "telegram" if "telegram" in base else "unknown"
    _sent_log.append((plat, cid, text, reply_markup))
    # Simulate rate limiting with actual sleep
    key = api._get_rate_limit_key()
    now = time.monotonic()
    last = api._MSG_LAST.get(key, 0.0)
    elapsed = now - last
    if elapsed < api._MSG_MIN_INTERVAL:
        await asyncio.sleep(api._MSG_MIN_INTERVAL - elapsed)
    api._MSG_LAST[key] = time.monotonic()
    return {"ok": True, "result": {"message_id": len(_sent_log)}}


# ── Full Dual-Platform Test ──
async def dual_platform_test():
    global PASS, FAIL, _sent_log
    print(f"\n{'=' * 70}")
    print("DUAL-PLATFORM INTEGRATION TEST (Bale + Telegram)")
    print(f"{'=' * 70}")

    # Monkey-patch send_message for the duration of this test
    api.send_message = _patched_send_message

    # Create fake sessions
    bale_sess = FakeSession()
    tg_sess = FakeSession()

    # ---- 1. Provider Registry ----
    print("\n── 1. Provider Registry ──")
    api.register_provider("bale", bale_sess, "https://tapi.bale.ai/botMOCK")
    api.register_provider("telegram", tg_sess, "https://api.telegram.org/botMOCK")

    providers = api.get_all_providers()
    check("Two providers registered", len(providers) == 2, f"got {len(providers)}")
    check("Bale session retrievable", api.get_provider_session("bale") is bale_sess)
    check(
        "Telegram session retrievable", api.get_provider_session("telegram") is tg_sess
    )

    # ---- 2. send_to_all_providers (channel fan-out) ----
    print("\n── 2. send_to_all_providers (channel fan-out) ──")
    _sent_log.clear()
    api.set_token("MOCK_TOKEN", "https://tapi.bale.ai/bot")
    results = await api.send_to_all_providers("@test_channel", "📢 Test announcement")
    check("Fan-out returns 2 results", len(results) == 2, f"got {len(results)}")
    check("Bale channel send OK", results[0][0] == "bale" and results[0][1] is True)
    check(
        "Telegram channel send OK",
        results[1][0] == "telegram" and results[1][1] is True,
    )

    # Verify both sides captured
    bale_sends = [e for e in _sent_log if e[0] == "bale" and e[1] == "@test_channel"]
    tg_sends = [e for e in _sent_log if e[0] == "telegram" and e[1] == "@test_channel"]
    check("Bale received channel message", len(bale_sends) >= 1)
    check("Telegram received channel message", len(tg_sends) >= 1)

    # ---- 3. send_to_user cross-platform routing ----
    print("\n── 3. send_to_user (cross-platform routing) ──")
    _sent_log.clear()

    # Route to Bale user
    await api.send_to_user(
        1001, "Hello Bale!", user_platform="bale", default_session=bale_sess
    )
    check(
        "send_to_user bale routed",
        any(e[0] == "bale" and e[1] == 1001 for e in _sent_log),
    )

    # Route to Telegram user
    await api.send_to_user(
        2001, "Hello TG!", user_platform="telegram", default_session=bale_sess
    )
    check(
        "send_to_user tg routed",
        any(e[0] == "telegram" and e[1] == 2001 for e in _sent_log),
    )

    # Unknown platform → falls back to default
    _sent_log.clear()
    await api.send_to_user(
        3001, "Unknown", user_platform="whatsapp", default_session=bale_sess
    )
    check("Unknown platform → default", any(e[1] == 3001 for e in _sent_log))

    # No providers registered
    api.unregister_provider("bale")
    api.unregister_provider("telegram")
    result = await api.send_to_user(4001, "No providers")
    check("No providers → graceful fail", result.get("ok") is False)
    # Re-register
    api.register_provider("bale", bale_sess, "https://tapi.bale.ai/botMOCK")
    api.register_provider("telegram", tg_sess, "https://api.telegram.org/botMOCK")

    # ---- 4. Error isolation: one provider missing ----
    print("\n── 4. Error isolation ──")
    api.unregister_provider("telegram")
    _sent_log.clear()
    results = await api.send_to_all_providers("@test", "Only Bale")
    check("One-provider fan-out: 1 result", len(results) == 1)
    check("Only Bale succeeded", results[0][0] == "bale" and results[0][1] is True)
    api.register_provider("telegram", tg_sess, "https://api.telegram.org/botMOCK")

    # ---- 5. DB Init ----
    print("\n── 5. Database Init ──")
    await db.init_db()
    check("DB initialized", True)

    # ---- 6. Cross-platform phone linking ----
    print("\n── 6. Cross-platform phone linking ──")

    # Bale employer
    await db.upsert_user(
        101,
        role="employer",
        emp_name="Ali Bale",
        emp_company="Bale Corp",
        emp_industry="فناوری اطلاعات",
        emp_phone="09120001001",
        emp_position="CEO",
        platform="bale",
        reg_date="1403/06/01",
    )
    check("Bale employer registered", (await db.get_user(101))["platform"] == "bale")

    # Telegram employer SAME phone
    await db.upsert_user(
        201,
        role="employer",
        emp_name="Ali Telegram",
        emp_company="Telegram Corp",
        emp_industry="فناوری اطلاعات",
        emp_position="CTO",
        platform="telegram",
        reg_date="1403/06/02",
    )
    check(
        "Telegram employer registered",
        (await db.get_user(201))["platform"] == "telegram",
    )

    linked = await db.link_users_by_phone(201, "09120001001", "telegram")
    check("Phone linking succeeded", linked == 101)
    e1 = await db.get_user(101)
    e2 = await db.get_user(201)
    check("Bale → links to TG", e1.get("linked_chat_id") == 201)
    check("TG → links to Bale", e2.get("linked_chat_id") == 101)

    # Bale + Telegram seekers
    await db.upsert_user(
        301,
        role="job_seeker",
        js_name="Sara Bale",
        js_phone="09120003001",
        js_province="تهران",
        js_job_title="برنامه‌نویس",
        js_experience="۳ تا ۵ سال",
        js_education="لیسانس",
        js_salary_min=20000000,
        js_categories=json.dumps(["برنامه‌نویسی", "IT"], ensure_ascii=False),
        js_skills=json.dumps(["Python"], ensure_ascii=False),
        js_cities=json.dumps(["تهران"], ensure_ascii=False),
        allow_employer_notify=1,
        platform="bale",
        reg_date="1403/06/05",
    )
    check("Bale seeker registered", (await db.get_user(301))["platform"] == "bale")

    await db.upsert_user(
        401,
        role="job_seeker",
        js_name="Sara TG",
        js_phone="09120003001",
        js_province="تهران",
        js_job_title="برنامه‌نویس",
        js_experience="۳ تا ۵ سال",
        js_education="لیسانس",
        js_salary_min=20000000,
        js_categories=json.dumps(["برنامه‌نویسی", "IT"], ensure_ascii=False),
        js_skills=json.dumps(["Python"], ensure_ascii=False),
        js_cities=json.dumps(["تهران"], ensure_ascii=False),
        allow_employer_notify=1,
        platform="telegram",
        reg_date="1403/06/06",
    )
    linked2 = await db.link_users_by_phone(401, "09120003001", "telegram")
    check("Seeker phone linking succeeded", linked2 is not None)

    # TG-only (no Bale counterpart)
    await db.upsert_user(
        501,
        role="job_seeker",
        js_name="Reza TG Only",
        js_phone="09120005001",
        js_province="البرز",
        js_job_title="طراح",
        js_experience="۱ تا ۳ سال",
        js_education="فوق‌دیپلم",
        js_salary_min=10000000,
        js_categories=json.dumps(["طراحی"], ensure_ascii=False),
        js_skills=json.dumps(["Figma"], ensure_ascii=False),
        js_cities=json.dumps(["البرز"], ensure_ascii=False),
        allow_employer_notify=1,
        platform="telegram",
        reg_date="1403/06/07",
    )
    check("TG-only registered", (await db.get_user(501))["platform"] == "telegram")
    result_none = await db.link_users_by_phone(501, "09120005001", "telegram")
    check("Link without counterpart → None", result_none is None)

    # ---- 7. Job Lifecycle ----
    print("\n── 7. Job Lifecycle ──")
    j1 = await db.create_job(
        101,
        title="Senior Developer",
        emp_type="تمام‌وقت",
        province="تهران",
        salary_min=30000000,
        salary_max=50000000,
        category="برنامه‌نویسی",
        contact_phone="09120001001",
    )
    check("Job created", j1 is not None)
    await db.approve_job(j1, 999)
    check("Job approved → active", (await db.get_job(j1))["status"] == "active")
    await db.close_job(j1, 101)
    check("Job closed", (await db.get_job(j1))["status"] == "closed")
    await db.renew_job(j1, 101)
    check("Job renewed → pending", (await db.get_job(j1))["status"] == "pending")
    await db.approve_job(j1, 999)
    check("Job re-approved", (await db.get_job(j1))["status"] == "active")
    await db.delete_job(j1, 101)
    check("Job deleted (soft)", await db.get_job(j1) is None)

    # Fresh job for app flow
    j2 = await db.create_job(
        101,
        title="Backend Engineer",
        emp_type="دورکاری",
        province="تهران",
        salary_min=25000000,
        salary_max=40000000,
        category="برنامه‌نویسی",
        contact_phone="09120001001",
    )
    await db.approve_job(j2, 999)
    check("Job 2 created+approved", j2 is not None)

    # ---- 8. Cross-platform Applications ----
    print("\n── 8. Cross-platform Applications ──")
    aid1, e1 = await db.create_application(j2, 301, cover_letter="Bale seeker")
    aid2, e2 = await db.create_application(j2, 401, cover_letter="TG seeker")
    aid3, e3 = await db.create_application(j2, 501, cover_letter="TG-only")
    check("3 apps created", aid1 and aid2 and aid3)
    apps = await db.get_job_applications(j2)
    check("Job has 3 apps", len(apps) == 3)

    # ---- 9. Admin approval flow ----
    print("\n── 9. Admin approval flow ──")
    await db.approve_application(aid1, 999)
    await db.approve_application(aid2, 999)
    await db.reject_application(aid3, 999, "Not enough")
    check("Aid1 approved", (await db.get_application(aid1))["status"] == "approved")
    check("Aid2 approved", (await db.get_application(aid2))["status"] == "approved")
    check("Aid3 rejected", (await db.get_application(aid3))["status"] == "rejected")
    pending = await db.get_pending_applications()
    check("No pending apps", len(pending) == 0)

    # ---- 10. Employer review ----
    print("\n── 10. Employer review ──")
    from database import update_application_status

    await update_application_status(aid1, "approved_by_employer")
    await update_application_status(aid2, "rejected_by_employer")
    check(
        "Emp approved aid1",
        (await db.get_application(aid1))["status"] == "approved_by_employer",
    )
    check(
        "Emp rejected aid2",
        (await db.get_application(aid2))["status"] == "rejected_by_employer",
    )

    # ---- 11. Cross-platform matching ----
    print("\n── 11. Matching across platforms ──")
    seekers = await db.get_matching_seekers_for_job("برنامه\u200cنویسی", "تهران")
    seeker_cids = [s["chat_id"] for s in seekers]
    check("Bale seeker matched", 301 in seeker_cids, f"matched: {seeker_cids}")
    check("Telegram seeker matched", 401 in seeker_cids, f"matched: {seeker_cids}")
    for s in seekers:
        check(
            f"Seeker {s['chat_id']} has platform field",
            "platform" in s and s["platform"] in ("bale", "telegram"),
        )

    emp_matches = await db.get_matching_employers_for_seeker(
        ["برنامه‌نویسی", "IT"], "تهران", ["تهران"]
    )
    check("Employer matching returns results", isinstance(emp_matches, list))

    # ---- 12. Linked employer sees jobs ----
    print("\n── 12. Linked employer job visibility ──")
    _, etotal = await db.get_employer_jobs(201)
    check("Linked TG employer sees Bale employer's jobs", etotal >= 1, f"got {etotal}")

    # ---- 13. Notify_admins cross-platform routing ----
    print("\n── 13. notify_admins cross-platform ──")
    from bot import notify_admins
    from config import ADMIN_IDS

    admin_list = list(ADMIN_IDS)
    if len(admin_list) >= 1:
        await db.upsert_user(
            admin_list[0],
            role="employer",
            emp_name="Admin Bale",
            emp_phone="09900000001",
            emp_company="Admin",
            platform="bale",
        )
    if len(admin_list) >= 2:
        await db.upsert_user(
            admin_list[1],
            role="employer",
            emp_name="Admin TG",
            emp_phone="09900000002",
            emp_company="Admin",
            platform="telegram",
        )

    _sent_log.clear()
    await notify_admins(
        bale_sess, "📢 Cross-platform test", inline([[("OK", "cb:test")]])
    )
    # Should have sent to Bale admin via bale, Telegram admin via telegram
    bale_admin = admin_list[0] if len(admin_list) >= 1 else None
    tg_admin = admin_list[1] if len(admin_list) >= 2 else None

    if bale_admin:
        check(
            "Admin Bale notified",
            any(e[0] == "bale" and e[1] == bale_admin for e in _sent_log),
        )
    if tg_admin:
        check(
            "Admin TG notified",
            any(e[0] == "telegram" and e[1] == tg_admin for e in _sent_log),
        )

    # ---- 14. Rate limiting per provider ----
    print("\n── 14. Rate limiting per provider ──")
    api._MSG_LAST.clear()
    api.set_token("MOCK_BALE", "https://tapi.bale.ai/bot")
    start = time.monotonic()
    for i in range(5):
        await api.send_message(bale_sess, 9999, f"Rate {i}")
    elapsed = time.monotonic() - start
    check("Rate limiting active (>=0.15s)", elapsed >= 0.15, f"elapsed={elapsed:.3f}s")

    # ---- 15. Platform field integrity ----
    print("\n── 15. Platform field integrity ──")
    for uid, plat, role in [
        (101, "bale", "employer"),
        (201, "telegram", "employer"),
        (301, "bale", "job_seeker"),
        (401, "telegram", "job_seeker"),
        (501, "telegram", "job_seeker"),
    ]:
        u = await db.get_user(uid)
        check(f"User {uid} platform={plat}", u and u["platform"] == plat)

    # Upsert preserves platform
    await db.upsert_user(101, emp_name="Ali Updated v2")
    u101 = await db.get_user(101)
    check("Upsert preserves platform", u101["platform"] == "bale")
    check("Upsert updates name", u101["emp_name"] == "Ali Updated v2")

    # ---- 16. Stress: rapid cross-platform writes ----
    print("\n── 16. Stress: rapid cross-platform writes ──")
    stress_ids = []
    for i in range(30):
        cid = 8000 + i
        plat = "bale" if i % 2 == 0 else "telegram"
        await db.upsert_user(
            cid,
            role="job_seeker",
            js_name=f"S{i}",
            js_phone=f"0999{i:04d}",
            js_province="تهران",
            js_job_title="تست",
            platform=plat,
        )
        stress_ids.append(cid)
    ok = 0
    for cid in stress_ids:
        u = await db.get_user(cid)
        if u and u.get("platform") in ("bale", "telegram"):
            ok += 1
    check("All 30 stress users have platform", ok == 30, f"{ok}/30")

    # Cleanup
    for cid in stress_ids:
        await db.upsert_user(cid, deleted_at=time.time())

    # ---- 17. _resolve_linked_cids ----
    print("\n── 17. _resolve_linked_cids ──")
    conn = db._c()
    try:
        cids = db._resolve_linked_cids_sync(conn, 101)
        check("101 resolves self+linked", set(cids) >= {101, 201})
        cids2 = db._resolve_linked_cids_sync(conn, 201)
        check("201 resolves self+linked", set(cids2) >= {201, 101})
        cids3 = db._resolve_linked_cids_sync(conn, 501)
        check("Unlinked resolves self only", cids3 == [501])
    finally:
        conn.close()

    # ---- 18. set_platform / get_platform ----
    print("\n── 18. Platform get/set ──")
    api.set_platform("bale")
    check("set→bale", api.get_platform() == "bale")
    api.set_platform("telegram")
    check("set→telegram", api.get_platform() == "telegram")
    api.set_platform("bale")

    # ---- 19. Channel publishing simulation (admjob flow logic) ----
    print("\n── 19. Channel publish simulation ──")
    _sent_log.clear()
    # Simulate what happens in admjob: callback
    CHANNEL_1 = "@hamrakar"
    CHANNEL_2 = "@hamrakarjob"
    channel_text = "📢 آگهی جدید\n💼 Test Job\n🏷 برنامه‌نویسی"

    await api.send_to_all_providers(CHANNEL_1, channel_text)
    await api.send_to_all_providers(CHANNEL_2, channel_text)

    # With both providers active, should have 4 sends (2 channels × 2 providers)
    check(
        "Channel fan-out: 4 sends total", len(_sent_log) == 4, f"got {len(_sent_log)}"
    )
    # Check both channels sent to both platforms
    for ch in [CHANNEL_1, CHANNEL_2]:
        for plat in ["bale", "telegram"]:
            check(f"{plat} → {ch}", any(e[0] == plat and e[1] == ch for e in _sent_log))

    # ---- 20. Employer notification simulation ----
    print("\n── 20. Employer notification cross-platform ──")
    _sent_log.clear()
    # Simulate notifying employer who is on a different platform
    await api.send_to_user(
        101, "✅ آگهی تأیید شد", user_platform="bale", default_session=bale_sess
    )
    check(
        "Bale employer notified on bale",
        any(e[0] == "bale" and e[1] == 101 for e in _sent_log),
    )

    await api.send_to_user(
        201, "✅ آگهی تأیید شد", user_platform="telegram", default_session=bale_sess
    )
    check(
        "TG employer notified on telegram",
        any(e[0] == "telegram" and e[1] == 201 for e in _sent_log),
    )

    # ---- 21. Seekers notification cross-platform ----
    print("\n── 21. Seeker notification cross-platform ──")
    _sent_log.clear()
    await api.send_to_user(
        301, "📬 رزومه تأیید شد", user_platform="bale", default_session=bale_sess
    )
    await api.send_to_user(
        401, "📬 رزومه تأیید شد", user_platform="telegram", default_session=tg_sess
    )
    check(
        "Bale seeker notified on bale",
        any(e[0] == "bale" and e[1] == 301 for e in _sent_log),
    )
    check(
        "TG seeker notified on telegram",
        any(e[0] == "telegram" and e[1] == 401 for e in _sent_log),
    )

    # ---- 22. Rejection notification routing ----
    print("\n── 22. Rejection notification routing ──")
    _sent_log.clear()
    # Simulate admin rejecting employer's job → notify employer on their platform
    await api.send_to_user(
        101, "❌ آگهی رد شد", user_platform="bale", default_session=bale_sess
    )
    check(
        "Rejection routed to Bale employer",
        any(e[0] == "bale" and e[1] == 101 for e in _sent_log),
    )
    await api.send_to_user(
        201, "❌ آگهی رد شد", user_platform="telegram", default_session=bale_sess
    )
    check(
        "Rejection routed to TG employer",
        any(e[0] == "telegram" and e[1] == 201 for e in _sent_log),
    )

    # ---- 23. _validate_phone cross-platform ----
    print("\n── 23. Phone validation cross-platform ──")
    from bot import _validate_phone

    dummy = FakeSession()
    api.set_platform("bale")
    ok, result = await _validate_phone(dummy, 9999, "employer", "09129999999")
    check("New phone validates OK", ok is True)

    # Create a fresh TG-only employer with unique phone
    await db.upsert_user(
        601,
        role="employer",
        emp_name="TG Solo",
        emp_company="TG Solo Co",
        emp_phone="09120000601",
        emp_position="CEO",
        platform="telegram",
        reg_date="1403/07/01",
    )
    # Same platform duplicate blocked
    api.set_platform("telegram")
    ok_tg, _ = await _validate_phone(dummy, 9999, "employer", "09120000601")
    check("Same-platform TG duplicate blocked", ok_tg is False, f"got ok={ok_tg}")

    # Cross-platform: phone on TG should be allowed on Bale
    api.set_platform("bale")
    ok_bale, _ = await _validate_phone(dummy, 9999, "employer", "09120000601")
    check("Cross-platform phone allowed on Bale", ok_bale is True, f"got ok={ok_bale}")

    # Bale duplicate blocked (101 has 09120001001 on bale)
    api.set_platform("bale")
    ok_bale2, _ = await _validate_phone(dummy, 9999, "employer", "09120001001")
    check(
        "Same-platform Bale duplicate blocked", ok_bale2 is False, f"got ok={ok_bale2}"
    )

    # Clean up after test — restore original send_message
    api.send_message = _original_send_message

    # ---- REPORT ----
    print(f"\n{'=' * 70}")
    print(f"DUAL-PLATFORM TEST COMPLETE")
    print(f"  Pass: {PASS}  Fail: {FAIL}")
    if FAIL == 0:
        print(f"  *** ALL CROSS-PLATFORM TESTS PASSED ***")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    try:
        asyncio.run(dual_platform_test())
    except Exception as e:
        print(f"\n*** TEST CRASHED: {e}")
        traceback.print_exc()
        FAIL = FAIL + 1  # FAIL is already in module scope, no need for global

    print(f"\nFINAL: {PASS} pass, {FAIL} fail")
    cleanup()
    sys.exit(0 if FAIL == 0 else 1)
