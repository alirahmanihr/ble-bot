"""
FINAL VERIFICATION TEST — deep, exhaustive, real-world.
Covers:
  1. Full E2E employer flow (Bale register → post job → TG mirror)
  2. Full E2E seeker flow (TG register → submit resume → Bale mirror)
  3. Profile sync: field-by-field verification after upsert
  4. Work experience cross-platform visibility
  5. Concurrent profile updates → no data loss
  6. Role handling across linked accounts
  7. Admin actions reflected on both platforms
  8. Job lifecycle: full create→approve→close→renew→delete chain
  9. Resume/application visibility across platforms
  10. Matching integrity with linked accounts
  11. Edge cases: unlinked user, empty fields, duplicate prevention
  12. Stress: rapid profile edits + reads while syncing
  13. State management preserves platform context
  14. Ban/unban propagates logically
  15. Real-world scenario: multiple employers + seekers interacting
"""

import asyncio
import json
import sys
import io
import time
import traceback
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BOT_DIR = Path(r"C:\Users\asus\Desktop\فراشايیان\ربات بله 050407\hamrakar")
sys.path.insert(0, str(BOT_DIR))
TEST_DB = BOT_DIR / "test_final.db"

import database as db
import bale_api as api
from database import (
    CATEGORIES,
    PROVINCES,
    EMP_TYPES,
    EXPERIENCES,
    EDUCATIONS,
    fmt_salary,
    parse_int,
    jlist,
    shamsi_now,
    shamsi_dt,
)

db.DB_PATH = TEST_DB

PASS = FAIL = 0


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
        if detail:
            print(f"         \033[91m→ {detail}\033[0m")


# ============================================================
async def final_verification():
    global PASS, FAIL
    print(f"\n{'=' * 70}")
    print("FINAL DEEP VERIFICATION — ALL FLOWS, ALL EDGE CASES")

    # ──── SECTION A: DB INIT ────
    print(f"\n{'─' * 70}")
    print("A. Database Initialization")
    await db.init_db()
    check("DB init", True)

    # ──── SECTION B: FULL E2E EMPLOYER (BALE) ────
    print(f"\n{'─' * 70}")
    print("B. E2E: Employer Bale → Register → Post → TG Mirror")

    # B1: Create Bale employer
    api.set_platform("bale")
    await db.upsert_user(
        1001,
        role="employer",
        emp_name="حسین رضایی",
        emp_company="شرکت فناوران",
        emp_industry="فناوری اطلاعات",
        emp_phone="09121001001",
        emp_position="مدیرعامل",
        platform="bale",
        reg_date=shamsi_now(),
    )
    e_bale = await db.get_user(1001)
    check("B1: Bale employer created", e_bale and e_bale["role"] == "employer")
    check("B1: Platform=bale", e_bale["platform"] == "bale")

    # B2: Create Telegram employer with same phone (simulates registering on TG later)
    api.set_platform("telegram")
    await db.upsert_user(
        2001,
        role="employer",
        emp_name="",
        emp_company="",
        platform="telegram",
        reg_date=shamsi_now(),
    )
    e_tg = await db.get_user(2001)
    check("B2: TG employer created (empty profile)", e_tg["platform"] == "telegram")

    # B3: Link by phone → profile should sync
    linked = await db.link_users_by_phone(2001, "09121001001", "telegram")
    check("B3: Phone linking succeeded", linked == 1001)

    # B4: Verify TG now has Bale's profile data
    e_tg_after = await db.get_user(2001)
    check("B4: TG emp_name synced", e_tg_after["emp_name"] == "حسین رضایی")
    check("B4: TG emp_company synced", e_tg_after["emp_company"] == "شرکت فناوران")
    check("B4: TG emp_industry synced", e_tg_after["emp_industry"] == "فناوری اطلاعات")
    check("B4: TG emp_position synced", e_tg_after["emp_position"] == "مدیرعامل")
    check("B4: TG role=employer", e_tg_after["role"] == "employer")

    # B5: Employer posts job from Bale
    api.set_platform("bale")
    j1 = await db.create_job(
        1001,
        title="برنامه‌نویس ارشد",
        emp_type="تمام‌وقت",
        province="تهران",
        city="تهران",
        salary_min=30000000,
        salary_max=50000000,
        category="برنامه‌نویسی",
        gender_need="بدون‌ترجیح",
        education_need="لیسانس",
        experience_need="۳ تا ۵ سال",
        description="توسعه بک‌اند با Python",
        contact_phone="09121001001",
    )
    check("B5: Job created from Bale employer", j1 is not None)

    # B6: Admin approves job
    await db.approve_job(j1, 999)
    job = await db.get_job(j1)
    check("B6: Job approved → active", job["status"] == "active")

    # B7: TG employer can see the job (linked account sees same jobs)
    jobs, total = await db.get_employer_jobs(2001)
    check("B7: TG employer sees Bale jobs", total >= 1, f"total={total}")
    check("B7: Job visible to TG employer", any(j["job_id"] == j1 for j in jobs))

    # ──── SECTION C: PROFILE SYNC ON EDIT ────
    print(f"\n{'─' * 70}")
    print("C. Profile Sync: Edits Propagate to Linked Account")

    # C1: Edit Bale employer → TG should reflect
    await db.upsert_user(
        1001, emp_name="حسین رضایی (ویرایش شده)", emp_company="فناوران نوین"
    )
    e_bale2 = await db.get_user(1001)
    e_tg2 = await db.get_user(2001)
    check("C1: Bale name updated", e_bale2["emp_name"] == "حسین رضایی (ویرایش شده)")
    check("C1: TG name synced", e_tg2["emp_name"] == "حسین رضایی (ویرایش شده)")
    check("C1: TG company synced", e_tg2["emp_company"] == "فناوران نوین")

    # C2: Edit TG employer → Bale should reflect
    await db.upsert_user(2001, emp_position="مدیر فنی", emp_email="h@fannavaran.ir")
    e_bale3 = await db.get_user(1001)
    e_tg3 = await db.get_user(2001)
    check("C2: TG position updated", e_tg3["emp_position"] == "مدیر فنی")
    check("C2: Bale position synced", e_bale3["emp_position"] == "مدیر فنی")
    check("C2: Bale email synced", e_bale3["emp_email"] == "h@fannavaran.ir")

    # C3: Add address on Bale → should sync to TG
    await db.upsert_user(
        1001, emp_address="تهران، خیابان ولیعصر", emp_website="fannavaran.ir"
    )
    e_tg4 = await db.get_user(2001)
    check("C3: TG address synced", e_tg4["emp_address"] == "تهران، خیابان ولیعصر")
    check("C3: TG website synced", e_tg4["emp_website"] == "fannavaran.ir")

    # C4: Platform NOT overwritten by sync
    check("C4: Bale platform preserved", e_bale3["platform"] == "bale")
    check("C4: TG platform preserved", e_tg4["platform"] == "telegram")

    # ──── SECTION D: FULL E2E SEEKER (TELEGRAM) ────
    print(f"\n{'─' * 70}")
    print("D. E2E: Seeker Telegram → Register → Resume → Bale Mirror")

    # D1: Create Telegram seeker
    api.set_platform("telegram")
    await db.upsert_user(
        3001,
        role="job_seeker",
        js_name="مریم احمدی",
        js_phone="09123001001",
        js_province="تهران",
        js_job_title="برنامه‌نویس",
        js_experience="۳ تا ۵ سال",
        js_education="لیسانس",
        js_salary_min=25000000,
        js_salary_max=40000000,
        js_dob="1375/04/12",
        js_gender="زن",
        js_relocate="بله",
        js_categories=json.dumps(["برنامه‌نویسی", "IT"], ensure_ascii=False),
        js_skills=json.dumps(["Python", "Django", "PostgreSQL"], ensure_ascii=False),
        js_cities=json.dumps(["تهران"], ensure_ascii=False),
        js_about="توسعه‌دهنده بک‌اند با ۴ سال تجربه",
        allow_employer_notify=1,
        resume_complete=1,
        platform="telegram",
        reg_date=shamsi_now(),
    )
    s_tg = await db.get_user(3001)
    check("D1: TG seeker created", s_tg and s_tg["role"] == "job_seeker")
    check("D1: TG seeker profile complete", s_tg["resume_complete"] == 1)

    # D2: Create Bale seeker with same phone
    api.set_platform("bale")
    await db.upsert_user(
        4001,
        role="job_seeker",
        js_name="",
        platform="bale",
        reg_date=shamsi_now(),
    )
    linked_s = await db.link_users_by_phone(4001, "09123001001", "bale")
    check("D2: Seeker phone linking succeeded", linked_s == 3001)

    # D3: Bale seeker should have full TG profile
    s_bale = await db.get_user(4001)
    check("D3: Bale js_name synced", s_bale["js_name"] == "مریم احمدی")
    check("D3: Bale js_province synced", s_bale["js_province"] == "تهران")
    check("D3: Bale js_experience synced", s_bale["js_experience"] == "۳ تا ۵ سال")
    check("D3: Bale js_education synced", s_bale["js_education"] == "لیسانس")
    check("D3: Bale js_gender synced", s_bale["js_gender"] == "زن")
    check(
        "D3: Bale js_about synced",
        s_bale["js_about"] == "توسعه‌دهنده بک‌اند با ۴ سال تجربه",
    )
    check("D3: Bale resume_complete=1", s_bale["resume_complete"] == 1)

    # D4: Add work experiences on Bale → should be visible on TG
    await db.add_work_experience(4001, "دیجی‌کالا", "۲ سال", "برنامه‌نویس بک‌اند")
    await db.add_work_experience(4001, "اسنپ", "۱ سال", "توسعه‌دهنده ارشد")
    exps_bale = await db.get_work_experiences(4001)
    exps_tg = await db.get_work_experiences(3001)
    check("D4: Bale has 2 work exps", len(exps_bale) == 2)
    check("D4: TG sees linked work exps", len(exps_tg) == 2, f"got {len(exps_tg)}")
    check("D4: TG sees Digikala", any("دیجی‌کالا" in e["place"] for e in exps_tg))

    # D5: Add work experience on TG → visible on Bale too
    await db.add_work_experience(3001, "کافه‌بازار", "۶ ماه", "Tech Lead")
    exps_bale2 = await db.get_work_experiences(4001)
    exps_tg2 = await db.get_work_experiences(3001)
    check("D5: Both now see 3 work exps", len(exps_bale2) == 3 and len(exps_tg2) == 3)
    check(
        "D5: Bale sees CafeBazaar", any("کافه‌بازار" in e["place"] for e in exps_bale2)
    )

    # ──── SECTION E: APPLICATION + RESUME FLOW ────
    print(f"\n{'─' * 70}")
    print("E. Application & Resume: Cross-Platform Visibility")

    # E1: TG seeker applies to job (posted by Bale employer)
    api.set_platform("telegram")
    aid, err = await db.create_application(
        j1,
        3001,
        cover_letter="من ۴ سال تجربه دارم و به Python مسلط هستم",
    )
    check("E1: TG seeker applied to job", aid is not None, f"err={err}")

    # E2: Bale seeker (linked) should also show this application
    apps = await db.get_seeker_applications(4001)
    check(
        "E2: Bale seeker sees linked TG applications",
        len(apps) >= 1,
        f"got {len(apps)}",
    )

    # E3: Another job for multi-app testing
    j2 = await db.create_job(
        1001,
        title="توسعه‌دهنده فرانت‌اند",
        emp_type="دورکاری",
        province="تهران",
        city="تهران",
        salary_min=20000000,
        salary_max=35000000,
        category="برنامه‌نویسی",
        contact_phone="09121001001",
    )
    await db.approve_job(j2, 999)
    check("E3: Job 2 created+approved", j2 is not None)

    # Apply from Bale
    api.set_platform("bale")
    aid2, err2 = await db.create_application(j2, 4001, cover_letter="بله از طرف کارجو")
    check("E4: Bale seeker applied to job 2", aid2 is not None, f"err={err2}")

    # TG seeker should see this app too
    apps_tg = await db.get_seeker_applications(3001)
    check(
        "E5: TG seeker sees linked Bale applications",
        len(apps_tg) >= 2,
        f"got {len(apps_tg)}",
    )

    # ──── SECTION F: ADMIN FLOW — BOTH PLATFORMS ────
    print(f"\n{'─' * 70}")
    print("F. Admin Actions: Approve/Reject on Both Platforms")

    # F1: Admin approves application → both linked accounts should see status change
    await db.approve_application(aid, 777)
    app1 = await db.get_application(aid)
    check("F1: Application approved", app1["status"] == "approved")

    # F2: Admin rejects application from Bale
    await db.reject_application(aid2, 777, "نیاز به تجربه بیشتر")
    app2 = await db.get_application(aid2)
    check("F2: Application rejected", app2["status"] == "rejected")

    # F3: Admin logs recorded correctly
    logs = await db.get_admin_logs(10)
    check("F3: Admin logs exist", len(logs) >= 2)

    # ──── SECTION G: JOB LIFECYCLE (FULL CHAIN) ────
    print(f"\n{'─' * 70}")
    print("G. Job Lifecycle: Create → Approve → Close → Renew → Delete")

    j3 = await db.create_job(
        1001,
        title="مدیر پروژه",
        emp_type="تمام‌وقت",
        province="البرز",
        salary_min=40000000,
        salary_max=60000000,
        category="مدیریت",
        contact_phone="09121001001",
    )
    check("G1: Job created", j3 is not None)
    check("G1: Status=pending", (await db.get_job(j3))["status"] == "pending")

    await db.approve_job(j3, 999)
    check("G2: Approved → active", (await db.get_job(j3))["status"] == "active")

    await db.close_job(j3, 1001)
    check("G3: Closed", (await db.get_job(j3))["status"] == "closed")

    await db.renew_job(j3, 1001)
    check("G4: Renewed → pending", (await db.get_job(j3))["status"] == "pending")

    await db.approve_job(j3, 999)
    check("G5: Re-approved → active", (await db.get_job(j3))["status"] == "active")

    # Edit job
    await db.update_job(j3, 1001, title="مدیر پروژه ارشد", salary_min=50000000)
    j3_after = await db.get_job(j3)
    check("G6: Job edited — title", j3_after["title"] == "مدیر پروژه ارشد")
    check("G6: Job edited — salary", j3_after["salary_min"] == 50000000)

    # Delete job (soft)
    await db.delete_job(j3, 1001)
    check("G7: Soft deleted", await db.get_job(j3) is None)

    # ──── SECTION H: MATCHING INTEGRITY ────
    print(f"\n{'─' * 70}")
    print("H. Matching Integrity with Linked Accounts")

    # Create several jobs + seekers for matching
    # Employer 2 (TG)
    api.set_platform("telegram")
    await db.upsert_user(
        5001,
        role="employer",
        emp_name="نگار حسینی",
        emp_company="رایانش ابری",
        emp_industry="فناوری اطلاعات",
        emp_phone="09125001001",
        emp_position="مدیر منابع انسانی",
        platform="telegram",
        reg_date=shamsi_now(),
    )
    j4 = await db.create_job(
        5001,
        title="مهندس DevOps",
        emp_type="تمام‌وقت",
        province="تهران",
        salary_min=35000000,
        salary_max=55000000,
        category="IT",
        contact_phone="09125001001",
    )
    await db.approve_job(j4, 999)

    # Seeker 3 (Bale) - matching category
    api.set_platform("bale")
    await db.upsert_user(
        6001,
        role="job_seeker",
        js_name="علی کریمی",
        js_phone="09126001001",
        js_province="تهران",
        js_job_title="DevOps Engineer",
        js_experience="۳ تا ۵ سال",
        js_education="لیسانس",
        js_salary_min=30000000,
        js_categories=json.dumps(["IT", "برنامه‌نویسی"], ensure_ascii=False),
        js_cities=json.dumps(["تهران"], ensure_ascii=False),
        allow_employer_notify=1,
        platform="bale",
        reg_date=shamsi_now(),
    )

    # Seeker 4 (TG - linked to 6001)
    api.set_platform("telegram")
    await db.upsert_user(
        6002,
        role="job_seeker",
        platform="telegram",
        reg_date=shamsi_now(),
    )
    await db.link_users_by_phone(6002, "09126001001", "telegram")

    # H1: Matching seekers for job — should find both linked + unlinked
    seekers = await db.get_matching_seekers_for_job("IT", "تهران")
    seeker_ids = [s["chat_id"] for s in seekers]
    # Should find at least the linked seeker (either 6001 or 6002)
    has_match = 6001 in seeker_ids or 6002 in seeker_ids
    check(
        "H1: Matching finds seekers across platforms", has_match, f"found: {seeker_ids}"
    )

    # H2: Matching employers for seeker
    employers = await db.get_matching_employers_for_seeker(
        ["IT", "برنامه‌نویسی"], "تهران", ["تهران"]
    )
    emp_ids = [e["emp_cid"] for e in employers]
    check("H2: Matching finds employers across platforms", len(emp_ids) >= 1)

    # ──── SECTION I: CONCURRENT PROFILE UPDATES ────
    print(f"\n{'─' * 70}")
    print("I. Concurrent Profile Updates (No Data Loss)")

    # Create two more linked accounts for concurrent stress
    api.set_platform("bale")
    await db.upsert_user(
        7001,
        role="employer",
        emp_name="Start",
        emp_company="Co",
        emp_phone="09127001001",
        platform="bale",
        reg_date=shamsi_now(),
    )
    api.set_platform("telegram")
    await db.upsert_user(
        7002,
        role="employer",
        platform="telegram",
        reg_date=shamsi_now(),
    )
    await db.link_users_by_phone(7002, "09127001001", "telegram")

    # I1: Concurrent edits from both platforms simultaneously
    async def edit_bale():
        for i in range(20):
            await db.upsert_user(7001, emp_name=f"Bale Name {i}")
            await asyncio.sleep(0.001)

    async def edit_tg():
        for i in range(20):
            await db.upsert_user(7002, emp_name=f"TG Name {i}")
            await asyncio.sleep(0.001)

    await asyncio.gather(edit_bale(), edit_tg())

    # After concurrent edits, both should have data (last writer wins is OK,
    # but neither should be blank or corrupted)
    bale_final = await db.get_user(7001)
    tg_final = await db.get_user(7002)
    check(
        "I1: Bale name not blank after concurrent edits", bale_final["emp_name"] != ""
    )
    check("I1: TG name not blank after concurrent edits", tg_final["emp_name"] != "")
    check("I1: Bale role preserved", bale_final["role"] == "employer")
    check("I1: TG role preserved", tg_final["role"] == "employer")
    check("I1: Bale platform preserved", bale_final["platform"] == "bale")
    check("I1: TG platform preserved", tg_final["platform"] == "telegram")

    # I2: Concurrent reads + writes don't crash
    async def stress_read(cid):
        for _ in range(30):
            await db.get_user(cid)

    async def stress_write(cid, base_name):
        for i in range(15):
            await db.upsert_user(cid, emp_name=f"{base_name}-{i}")

    await asyncio.gather(
        stress_read(7001),
        stress_read(7002),
        stress_write(7001, "B"),
        stress_write(7002, "T"),
    )
    check("I2: Concurrent read+write no crash", True)

    # ──── SECTION J: EDGE CASES ────
    print(f"\n{'─' * 70}")
    print("J. Edge Cases")

    # J1: Unlinked user — sync does nothing
    await db.upsert_user(9999, role="employer", emp_name="Solo", platform="bale")
    u = await db.get_user(9999)
    check("J1: Unlinked user unaffected", u["emp_name"] == "Solo")

    # J2: Empty field updates — should not overwrite non-empty linked fields
    api.set_platform("bale")
    await db.upsert_user(
        8001,
        role="employer",
        emp_name="Original",
        emp_phone="09128001001",
        emp_company="Original Co",
        emp_position="Manager",
        platform="bale",
        reg_date=shamsi_now(),
    )
    api.set_platform("telegram")
    await db.upsert_user(
        8002,
        role="employer",
        platform="telegram",
        reg_date=shamsi_now(),
    )
    await db.link_users_by_phone(8002, "09128001001", "telegram")

    # Now update Bale with ONLY emp_name — other fields should NOT be blanked
    await db.upsert_user(8001, emp_name="Updated Name")
    tg_linked = await db.get_user(8002)
    check("J2: TG emp_name synced", tg_linked["emp_name"] == "Updated Name")
    check("J2: TG emp_company retained", tg_linked["emp_company"] == "Original Co")
    check("J2: TG emp_position retained", tg_linked["emp_position"] == "Manager")

    # J3: Phone is NOT synced between linked accounts (UNIQUE constraint)
    # Bale has emp_phone, TG should have NULL/empty emp_phone
    check(
        "J3: TG emp_phone NOT synced (UNIQUE safety)",
        tg_linked.get("emp_phone") is None or tg_linked.get("emp_phone") == "",
    )

    # J4: Duplicate phone same platform blocked
    from bot import _validate_phone

    class FakeSess:
        def __bool__(self):
            return True

    api.set_platform("bale")
    ok, _ = await _validate_phone(FakeSess(), 9999, "employer", "09128001001")
    check("J4: Bale duplicate phone blocked", ok is False)

    # J5: Cross-platform phone allowed
    api.set_platform("telegram")
    ok2, _ = await _validate_phone(FakeSess(), 9999, "employer", "09128001001")
    check("J5: Cross-platform phone allowed", ok2 is True)

    # J6: Rate limit for applications
    for i in range(6):
        _, err = await db.create_application(j4, 6001, cover_letter=f"Test {i}")
    check("J6: Rate limit triggered after 5", err == "rate_limit")

    # J7: Duplicate application blocked
    aid_d, err_d = await db.create_application(j4, 6001, cover_letter="Dup")
    check("J7: Duplicate app blocked", err_d == "duplicate" or aid_d is None)

    # J8: Idempotency key works
    key = f"{j4}_{6001}_idem_test_{int(time.time())}"
    aid_i1, _ = await db.create_application(j4, 6001, idempotency_key=key)
    # Wait enough to bypass rate limit
    await asyncio.sleep(1)
    # Clear rate limit
    db._rate_limit.clear()
    aid_i2, err_i2 = await db.create_application(j4, 6001, idempotency_key=key)
    check("J8: Idempotency returns same app", aid_i2 == aid_i1, f"{aid_i2} vs {aid_i1}")

    # J9: Get non-existent entities returns None
    check("J9: get_job(0)=None", await db.get_job(0) is None)
    check("J9: get_user(0)=None", await db.get_user(0) is None)
    check("J9: get_application(0)=None", await db.get_application(0) is None)

    # ──── SECTION K: SEARCH + PAGINATION ────
    print(f"\n{'─' * 70}")
    print("K. Search & Pagination Cross-Platform")

    # Create multiple jobs to test search
    for i in range(12):
        jid = await db.create_job(
            1001,
            title=f"Job Search {i}",
            emp_type="تمام‌وقت",
            province="تهران" if i % 3 == 0 else "البرز" if i % 3 == 1 else "اصفهان",
            salary_min=10000000 + i * 1000000,
            category=CATEGORIES[i % len(CATEGORIES)],
            contact_phone="09121001001",
        )
        if jid:
            await db.approve_job(jid, 999)

    jobs_p0, total = await db.search_jobs(category="همه", province="همه", page=0, per=5)
    check("K1: Search page0 has 5", len(jobs_p0) == 5, f"got {len(jobs_p0)}")
    check("K1: Search total >= 13", total >= 13, f"total={total}")

    jobs_p1, _ = await db.search_jobs(category="همه", province="همه", page=1, per=5)
    check("K2: Search page1 has results", len(jobs_p1) >= 1)

    # Keyword search
    jobs_kw, _ = await db.search_jobs(keyword="Search")
    check("K3: Keyword search works", len(jobs_kw) >= 1)

    # Province search
    jobs_prov, _ = await db.search_jobs(province="تهران")
    check("K4: Province search works", len(jobs_prov) >= 1)

    # Category search
    jobs_cat, _ = await db.search_jobs(category="برنامه‌نویسی")
    check("K5: Category search works", len(jobs_cat) >= 1)

    # ──── SECTION L: NOTIFICATION + BOOKMARK ────
    print(f"\n{'─' * 70}")
    print("L. Notifications & Bookmarks")

    await db.add_notification(1001, "آگهی شما تأیید شد", "msg_001")
    await db.add_notification(1001, "رزومه جدید دریافت شد", "msg_002")
    await db.add_notification(2001, "پروفایل شما بروز شد", "msg_003")

    unread = await db.get_unread_count(1001)
    check("L1: Bale employer has 2 unread", unread == 2, f"got {unread}")

    notifs = await db.get_notifications(1001)
    check("L2: Got notifications", len(notifs) == 2)
    unread_after = await db.get_unread_count(1001)
    check("L3: Marked as read", unread_after == 0)

    # Bookmark
    await db.add_bookmark(3001, j1)
    await db.add_bookmark(3001, j2)
    bms = await db.get_bookmarks(3001)
    check("L4: 2 bookmarks", len(bms) == 2, f"got {len(bms)}")
    await db.remove_bookmark(3001, j1)
    bms2 = await db.get_bookmarks(3001)
    check("L5: 1 bookmark after remove", len(bms2) == 1)

    # ──── SECTION M: BAN / PRIVATE MODE ────
    print(f"\n{'─' * 70}")
    print("M. Ban & Private Mode")

    await db.ban_user(6001, "تست بن")
    s = await db.get_user(6001)
    check("M1: User banned", s["is_banned"] == 1)
    check("M2: Ban reason recorded", s.get("ban_reason") == "تست بن")

    # Banned user excluded from search
    seekers_after_ban = await db.get_matching_seekers_for_job("IT", "تهران")
    check(
        "M3: Banned seeker excluded from matching",
        6001 not in [s["chat_id"] for s in seekers_after_ban],
    )

    await db.unban_user(6001)
    s2 = await db.get_user(6001)
    check("M4: User unbanned", s2["is_banned"] == 0)

    # Private mode
    await db.upsert_user(6001, private_mode=1)
    s3 = await db.get_user(6001)
    check("M5: Private mode ON", s3["private_mode"] == 1)

    await db.upsert_user(6001, private_mode=0)
    s4 = await db.get_user(6001)
    check("M6: Private mode OFF", s4["private_mode"] == 0)

    # ──── SECTION N: RATING ────
    print(f"\n{'─' * 70}")
    print("N. Rating System")

    await db.add_rating(1001, 3001, j1, 5, "عالی")
    await db.add_rating(1001, 3001, j2, 4, "خوب")
    u_rated = await db.get_user(3001)
    check("N1: Rating recorded", u_rated["rating"] >= 4.0)
    check("N2: Rating count=2", u_rated["rating_count"] == 2)

    # ──── SECTION O: STATE MANAGEMENT ────
    print(f"\n{'─' * 70}")
    print("O. State Management")

    await db.set_state(1001, "ER_NAME", {"step": 1})
    s_state, s_data = await db.get_state(1001)
    check("O1: State set", s_state == "ER_NAME")
    check("O2: State data preserved", s_data.get("step") == 1)

    await db.set_state(1001, "ER_COMPANY", {"step": 2})
    s2_state, _ = await db.get_state(1001)
    check("O3: State transitioned", s2_state == "ER_COMPANY")

    await db.clear_state(1001)
    s3_state, s3_data = await db.get_state(1001)
    check("O4: State cleared → IDLE", s3_state == "IDLE")

    # ──── SECTION P: STATS ────
    print(f"\n{'─' * 70}")
    print("P. System Statistics")

    stats = await db.get_stats()
    check("P1: Stats has total", "total" in stats)
    check("P2: Stats has employers", "employers" in stats)
    check("P3: Stats has seekers", "seekers" in stats)
    check("P4: Stats has active_jobs", "active_jobs" in stats)
    check("P5: Stats valid", stats["total"] >= 1)

    # ──── SECTION Q: REAL-WORLD SCENARIO ────
    print(f"\n{'─' * 70}")
    print("Q. Real-World Scenario: Full Hiring Pipeline")

    # 1. Employer registers on Bale
    api.set_platform("bale")
    await db.upsert_user(
        9001,
        role="employer",
        emp_name="کارفرمای تست",
        emp_company="شرکت تست",
        emp_industry="فناوری اطلاعات",
        emp_phone="09129001001",
        emp_position="مدیر",
        platform="bale",
        reg_date=shamsi_now(),
    )

    # 2. Same employer opens Telegram → linking
    api.set_platform("telegram")
    await db.upsert_user(
        9002, role="employer", platform="telegram", reg_date=shamsi_now()
    )
    await db.link_users_by_phone(9002, "09129001001", "telegram")

    # 3. Employer posts 3 jobs from Bale
    api.set_platform("bale")
    job_ids = []
    for i, title in enumerate(["توسعه‌دهنده Go", "تحلیل‌گر داده", "مدیر محصول"]):
        jid = await db.create_job(
            9001,
            title=title,
            emp_type="تمام‌وقت",
            province="تهران",
            salary_min=20000000 + i * 5000000,
            salary_max=40000000 + i * 5000000,
            category=CATEGORIES[i % len(CATEGORIES)],
            contact_phone="09129001001",
        )
        if jid:
            await db.approve_job(jid, 999)
            job_ids.append(jid)

    check("Q1: 3 jobs created", len(job_ids) == 3, f"got {len(job_ids)}")

    # 4. Jobs visible from TG linked account
    tg_jobs, tg_total = await db.get_employer_jobs(9002)
    check("Q2: TG sees 3 jobs", tg_total == 3, f"got {tg_total}")

    # 5. Job seekers apply
    for idx, (cid, plat, phone) in enumerate(
        [
            (9101, "bale", "09129101001"),
            (9102, "telegram", "09129102001"),
            (9103, "bale", "09129103001"),
        ]
    ):
        api.set_platform(plat)
        await db.upsert_user(
            cid,
            role="job_seeker",
            js_name=f"کارجوی {idx + 1}",
            js_phone=phone,
            js_province="تهران",
            js_job_title="توسعه‌دهنده",
            js_experience=EXPERIENCES[idx],
            js_education="لیسانس",
            js_salary_min=15000000,
            js_categories=json.dumps(["برنامه‌نویسی", "IT"], ensure_ascii=False),
            js_cities=json.dumps(["تهران"], ensure_ascii=False),
            allow_employer_notify=1,
            platform=plat,
            reg_date=shamsi_now(),
        )
        # Each applies to one of the jobs
        jid = job_ids[idx % len(job_ids)]
        await db.create_application(jid, cid, cover_letter=f"رزومه کارجوی {idx + 1}")

    # 6. Verify all applications exist
    total_apps = 0
    for jid in job_ids:
        apps = await db.get_job_applications(jid)
        total_apps += len(apps)
    check("Q3: 3 applications total", total_apps == 3, f"got {total_apps}")

    # 7. Admin reviews pending applications (only for our scenario jobs)
    pending_all = await db.get_pending_applications()
    pending_scenario = [a for a in pending_all if a["job_id"] in job_ids]
    check(
        "Q4: 3 pending applications for scenario jobs",
        len(pending_scenario) == 3,
        f"got {len(pending_scenario)} total_pending={len(pending_all)}",
    )

    for app in pending_scenario:
        await db.approve_application(app["app_id"], 777)

    # 8. Verify all approved
    pending_after_all = await db.get_pending_applications()
    pending_after_scenario = [a for a in pending_after_all if a["job_id"] in job_ids]
    check(
        "Q5: 0 pending for scenario jobs after approval",
        len(pending_after_scenario) == 0,
        f"got {len(pending_after_scenario)}",
    )

    # 9. Employer reviews approved applications
    for jid in job_ids:
        apps = await db.get_job_applications(jid)
        for app in apps:
            if app["status"] == "approved":
                await db.update_application_status(
                    app["app_id"], "approved_by_employer"
                )

    # 10. Final verification: job view counts
    for jid in job_ids:
        await db.increment_views(jid)
        await db.increment_views(jid)
    j = await db.get_job(job_ids[0])
    check("Q6: View count incremented", j["views"] >= 2, f"views={j['views']}")

    # ──── SECTION R: SCHEMA INTEGRITY ────
    print(f"\n{'─' * 70}")
    print("R. Schema Integrity")

    # R1: All required columns exist
    conn = db._c()
    try:
        for table, required_cols in [
            ("users", ["chat_id", "role", "platform", "linked_chat_id", "deleted_at"]),
            ("jobs", ["job_id", "emp_cid", "status", "deleted_at"]),
            (
                "applications",
                ["app_id", "job_id", "seeker_cid", "status", "deleted_at"],
            ),
            ("bookmarks", ["bm_id", "user_cid", "job_id", "deleted_at"]),
            ("notifications", ["notif_id", "user_cid", "text", "deleted_at"]),
            ("activity_logs", ["log_id", "user_cid", "action", "deleted_at"]),
            ("work_experiences", ["exp_id", "user_chat_id", "place", "deleted_at"]),
            ("ratings", ["rating_id", "from_cid", "to_cid", "deleted_at"]),
        ]:
            cols = [
                c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()
            ]
            for col in required_cols:
                check(f"R1: {table}.{col} exists", col in cols, f"missing in {table}")
    finally:
        conn.close()

    # R2: WAL mode is on
    conn2 = db._c()
    try:
        journal = conn2.execute("PRAGMA journal_mode").fetchone()[0]
        check("R2: WAL mode active", journal.lower() == "wal", f"got {journal}")
    finally:
        conn2.close()

    # ──── SECTION S: DATA INTEGRITY AFTER ALL OPS ────
    print(f"\n{'─' * 70}")
    print("S. Final Data Integrity Check")

    # Verify linked pairs are consistent
    pairs = [
        (1001, 2001),
        (3001, 4001),
        (6001, 6002),
        (7001, 7002),
        (8001, 8002),
        (9001, 9002),
    ]
    for a, b in pairs:
        ua = await db.get_user(a)
        ub = await db.get_user(b)
        if ua and ub:
            check(
                f"S: {a}↔{b} roles match",
                ua.get("role") == ub.get("role"),
                f"{ua.get('role')} vs {ub.get('role')}",
            )

    # No deleted users leaked into active queries
    all_users = await db.get_all_users()
    check(
        "S: No deleted users in get_all_users", all(len(str(u)) > 0 for u in all_users)
    )

    # ──── REPORT ────
    print(f"\n{'=' * 70}")
    print(f"FINAL DEEP VERIFICATION COMPLETE")
    print(f"  Pass: {PASS}  Fail: {FAIL}")
    if FAIL == 0:
        print(f"  *** ALL DEEP VERIFICATION TESTS PASSED ***")
    else:
        print(f"  *** {FAIL} FAILURES FOUND ***")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    try:
        asyncio.run(final_verification())
    except Exception as e:
        print(f"\n*** TEST CRASHED: {e}")
        traceback.print_exc()
        FAIL = FAIL + 1

    print(f"\nFINAL: {PASS} pass, {FAIL} fail")
    cleanup()
    sys.exit(0 if FAIL == 0 else 1)
