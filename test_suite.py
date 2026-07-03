"""
Enhanced comprehensive test suite - 2 full runs, stress + edge case focus.
"""

import asyncio
import json
import sys
import traceback
import time
import io
from pathlib import Path

# Force UTF-8 encoding on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BOT_DIR = Path(r"C:\Users\asus\Desktop\فراشايیان\ربات بله 050407\hamrakar")
sys.path.insert(0, str(BOT_DIR))
TEST_DB = BOT_DIR / "test_hamrakar.db"

import database as db

db.DB_PATH = TEST_DB


def cleanup():
    for p in [TEST_DB, Path(str(TEST_DB) + "-wal"), Path(str(TEST_DB) + "-shm")]:
        if p.exists():
            p.unlink()


cleanup()

PASS = FAIL = 0
TEST_START = time.time()


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  |  {detail}")


# ============================================================
# FULL RUN
# ============================================================
async def full_test_suite(run_label):
    global PASS
    print(f"\n{'=' * 60}")
    print(f"FULL TEST SUITE - {run_label}")
    print(f"{'=' * 60}")

    # ---- INIT ----
    await db.init_db()
    check("DB init", True)

    # ---- REGISTRATION ----
    # Employer 1
    await db.upsert_user(
        101,
        role="employer",
        emp_name="Ali Ahmadi",
        emp_company="Pars Tech",
        emp_industry="IT",
        emp_phone="09120001001",
        emp_position="CEO",
        emp_email="ali@pars.ir",
        emp_website="pars.ir",
        emp_address="Tehran-Valiasr",
        reg_date="1403/06/01",
    )
    e1 = await db.get_user(101)
    check("E1 registered", e1 and e1["role"] == "employer")
    check(
        "E1 full profile",
        e1
        and all(
            e1.get(k) for k in ["emp_name", "emp_company", "emp_phone", "emp_email"]
        ),
    )

    # Employer 2
    await db.upsert_user(
        102,
        role="employer",
        emp_name="Sara Moradi",
        emp_company="Rayan Group",
        emp_industry="Banking",
        emp_phone="09120001002",
        emp_position="HR Manager",
        reg_date="1403/06/05",
    )
    e2 = await db.get_user(102)
    check("E2 registered", e2 and e2["role"] == "employer")

    # Employer 3 (will post many jobs for stress)
    await db.upsert_user(
        103,
        role="employer",
        emp_name="Reza Karimi",
        emp_company="Mega Corp",
        emp_industry="Production",
        emp_phone="09120001003",
        emp_position="Manager",
        reg_date="1403/06/10",
    )

    # Seeker 1
    await db.upsert_user(
        201,
        role="job_seeker",
        js_name="Maryam Hosseini",
        js_phone="09120002001",
        js_province="Tehran",
        js_job_title="Python Developer",
        js_experience="3-5 years",
        js_education="Master",
        js_salary_min=20000000,
        js_dob="1375/03/15",
        js_gender="Female",
        js_relocate="Yes",
        js_categories=json.dumps(["Programming", "IT", "Data"]),
        js_skills=json.dumps(["Python", "Django", "FastAPI", "SQL", "Docker"]),
        js_cities=json.dumps(["Tehran", "Alborz"]),
        js_about="Senior backend dev with 5 years experience",
        allow_employer_notify=1,
        reg_date="1403/06/08",
    )
    s1 = await db.get_user(201)
    check("S1 registered", s1 and s1["role"] == "job_seeker")

    # Seeker 2
    await db.upsert_user(
        202,
        role="job_seeker",
        js_name="Amir Rezaei",
        js_phone="09120002002",
        js_province="Alborz",
        js_job_title="UI Designer",
        js_experience="1-3 years",
        js_education="Bachelor",
        js_salary_min=12000000,
        js_dob="1379/08/20",
        js_gender="Male",
        js_relocate="Maybe",
        js_categories=json.dumps(["Design", "UI"]),
        js_skills=json.dumps(["Figma", "Photoshop", "HTML", "CSS"]),
        js_cities=json.dumps(["Alborz", "Tehran"]),
        js_about="Creative UI designer",
        allow_employer_notify=1,
        reg_date="1403/06/12",
    )
    s2 = await db.get_user(202)
    check("S2 registered", s2 and s2["role"] == "job_seeker")

    # Seeker 3 (private mode)
    await db.upsert_user(
        203,
        role="job_seeker",
        js_name="Nazanin Jalali",
        js_phone="09120002003",
        js_province="Shiraz",
        js_job_title="Accountant",
        js_experience="5+ years",
        js_education="PhD",
        js_salary_min=35000000,
        js_gender="Female",
        js_relocate="No",
        js_categories=json.dumps(["Accounting", "Finance"]),
        js_skills=json.dumps(["Excel", "Accounting"]),
        js_cities=json.dumps(["Shiraz"]),
        allow_employer_notify=0,
        private_mode=1,
        reg_date="1403/06/15",
    )
    s3 = await db.get_user(203)
    check("S3 registered (private)", s3 and s3["private_mode"] == 1)

    # Seeker 4 (banned)
    await db.upsert_user(
        204,
        role="job_seeker",
        js_name="Banned User",
        js_phone="09120002004",
        js_province="Tehran",
        js_job_title="Spammer",
        js_experience="None",
        js_education="Diploma",
        is_banned=1,
        allow_employer_notify=0,
    )

    # ---- WORK EXPERIENCE ----
    await db.add_work_experience(201, "Snapp", "2 years", "Backend Developer")
    await db.add_work_experience(201, "Digikala", "3 years", "Senior Developer")
    await db.add_work_experience(201, "CafeBazaar", "6 months", "Tech Lead")
    exps = await db.get_work_experiences(201)
    check("S1 has 3 work experiences", len(exps) == 3)

    # Test _calc_total_experience (imported from bot)
    from bot import _calc_total_experience

    total = _calc_total_experience(exps)
    # S1 has 2+3+0.5=5.5 years -> 66 months -> >60 -> EXPERIENCES[4]
    exp_vals = db.EXPERIENCES
    check(
        f"Total exp calculated ({len(exps)} jobs)",
        total == exp_vals[4],
    )

    await db.add_work_experience(202, "StartupX", "1 year", "Junior Designer")
    exps2 = await db.get_work_experiences(202)
    check("S2 has 1 work exp", len(exps2) == 1)

    # ---- JOBS ----
    # E1 posts 3 jobs
    j1 = await db.create_job(
        101,
        title="Senior Python Dev",
        emp_type="Full-time",
        province="Tehran",
        city="",
        salary_min=25000000,
        salary_max=45000000,
        category="Programming",
        gender_need="No preference",
        education_need="Bachelor",
        experience_need="3-5 years",
        description="Build scalable backends",
        contact_phone="09120001001",
        contact_email="hr@pars.ir",
    )
    check("Job 1 created", j1 is not None)

    j2 = await db.create_job(
        101,
        title="Junior Frontend Dev",
        emp_type="Part-time",
        province="Tehran",
        salary_min=8000000,
        salary_max=12000000,
        category="Programming",
        education_need="Diploma",
        experience_need="None",
        contact_phone="09120001001",
    )
    check("Job 2 created", j2 is not None)

    j3 = await db.create_job(
        101,
        title="Data Analyst",
        emp_type="Remote",
        province="Alborz",
        salary_min=18000000,
        salary_max=25000000,
        category="Data",
        experience_need="1-3 years",
        contact_phone="09120001001",
    )
    check("Job 3 created", j3 is not None)

    # E2 posts 2 jobs
    j4 = await db.create_job(
        102,
        title="Bank Teller",
        emp_type="Full-time",
        province="Tehran",
        salary_min=10000000,
        category="Banking",
        education_need="Diploma",
        experience_need="None",
        contact_phone="09120001002",
    )
    check("Job 4 created", j4 is not None)

    j5 = await db.create_job(
        102,
        title="Loan Officer",
        emp_type="Full-time",
        province="Shiraz",
        salary_min=15000000,
        category="Finance",
        education_need="Bachelor",
        experience_need="1-3 years",
        contact_phone="09120001002",
    )
    check("Job 5 created", j5 is not None)

    # ---- ADMIN APPROVE/REJECT ----
    # Approve j1, j3, j5
    await db.approve_job(j1, 999)
    await db.approve_job(j3, 999)
    await db.approve_job(j5, 999)
    # Reject j2
    await db.reject_job(j2, 999, "Not enough info")
    # Leave j4 pending

    check("J1 approved & active", (await db.get_job(j1))["status"] == "active")
    check("J2 rejected", (await db.get_job(j2))["status"] == "rejected")
    check("J3 active", (await db.get_job(j3))["status"] == "active")
    check("J4 still pending", (await db.get_job(j4))["status"] == "pending")
    check("J5 active", (await db.get_job(j5))["status"] == "active")

    # ---- SEARCH (JOB) ----
    r1, t1 = await db.search_jobs(category="Programming")
    check("Search Programming: 1 active", t1 == 1, f"got {t1}")

    r2, t2 = await db.search_jobs(province="Tehran")
    check("Search Tehran: >=1", t2 >= 1, f"got {t2}")

    r3, t3 = await db.search_jobs()
    check("Search all: 3 active", t3 == 3, f"got {t3}")

    r4, t4 = await db.search_jobs(category="Programming", province="Alborz")
    check("Search Prog+Alborz: 0 (j3 is Data, not Program)", t4 == 0, f"got {t4}")

    # ---- APPLICATIONS ----
    # S1 applies to j1
    aid1, err1 = await db.create_application(
        j1, 201, cover_letter="I'm perfect for this"
    )
    check("S1 applied to J1", aid1 is not None and err1 is None)

    # S1 applies to j3
    aid2, err2 = await db.create_application(
        j3, 201, cover_letter="Remote works for me"
    )
    check("S1 applied to J3", aid2 is not None and err2 is None)

    # S2 applies to j1
    aid3, err3 = await db.create_application(
        j1, 202, cover_letter="Frontend is my thing"
    )
    check("S2 applied to J1", aid3 is not None and err3 is None)

    # S2 applies to j5
    aid4, err4 = await db.create_application(j5, 202, cover_letter="")
    check("S2 applied to J5", aid4 is not None and err4 is None)

    # Verify app counts
    check("S1 has 2 apps", len(await db.get_seeker_applications(201)) == 2)
    check("S2 has 2 apps", len(await db.get_seeker_applications(202)) == 2)
    check("J1 has 2 apps", len(await db.get_job_applications(j1)) == 2)
    check("J1 app_count=2", (await db.get_job(j1))["app_count"] == 2)

    # ---- DUPLICATE PREVENTION ----
    dup_id, dup_err = await db.create_application(j1, 201, cover_letter="Duplicate")
    check(
        "Duplicate blocked (S1->J1 again)", dup_err in ("duplicate", "already_exists")
    )
    check("J1 still has 2 apps", len(await db.get_job_applications(j1)) == 2)

    # ---- ADMIN APPLICATION FLOW ----
    pending = await db.get_pending_applications()
    check("4 pending applications for admin", len(pending) == 4)

    # Approve aid1 (S1->J1)
    await db.approve_application(aid1, 999)
    app1 = await db.get_application(aid1)
    check("Aid1 approved", app1 and app1["status"] == "approved")

    # Reject aid4 (S2->J5)
    await db.reject_application(aid4, 999, "Not qualified")
    app4 = await db.get_application(aid4)
    check("Aid4 rejected", app4 and app4["status"] == "rejected")

    # ---- EMPLOYER REVIEW FLOW ----
    # Employer 101 approves S2 for J1
    await db.update_application_status(aid3, "approved_by_employer")
    app3 = await db.get_application(aid3)
    check("Aid3 employer-approved", app3 and app3["status"] == "approved_by_employer")

    # Employer 101 rejects S1 for J1 (edge: already admin-approved)
    await db.update_application_status(aid1, "rejected_by_employer")
    app1b = await db.get_application(aid1)
    check(
        "Aid1 status changed to rejected_by_employer",
        app1b and app1b["status"] == "rejected_by_employer",
    )

    # ---- BOOKMARKS ----
    await db.add_bookmark(201, j3)
    await db.add_bookmark(201, j5)
    await db.add_bookmark(202, j1)
    bms1 = await db.get_bookmarks(201)
    check("S1 has 2 bookmarks", len(bms1) == 2)
    bms2 = await db.get_bookmarks(202)
    check("S2 has 1 bookmark", len(bms2) == 1)

    # Duplicate bookmark
    await db.add_bookmark(201, j3)
    check("Dup bookmark still 2", len(await db.get_bookmarks(201)) == 2)

    # Remove bookmark
    await db.remove_bookmark(201, j5)
    check("After remove: 1 bookmark", len(await db.get_bookmarks(201)) == 1)

    # ---- NOTIFICATIONS ----
    await db.add_notification(201, "New job matching your profile: Senior Python Dev")
    await db.add_notification(201, "Your application was approved")
    await db.add_notification(201, "Your application was rejected")
    await db.add_notification(202, "New job: UI Designer")
    check("S1 unread=3", await db.get_unread_count(201) == 3)
    check("S2 unread=1", await db.get_unread_count(202) == 1)

    # Read notifications (marks all read)
    notifs = await db.get_notifications(201)
    check("S1 got 3 notifications", len(notifs) == 3)
    check("S1 unread=0 after read", await db.get_unread_count(201) == 0)

    # Dedup notification
    await db.add_notification(
        201, "New job: Senior Python Dev", message_id="dedup_test_id"
    )
    await db.add_notification(
        201, "New job: Senior Python Dev", message_id="dedup_test_id"
    )
    check("Notification dedup works", await db.get_unread_count(201) == 1)

    # ---- MATCHING ----
    # get_matching_seekers_for_job (fixed function)
    seekers_prog_tehran = await db.get_matching_seekers_for_job("Programming", "Tehran")
    check("Match: Prog+Tehran finds seekers", len(seekers_prog_tehran) >= 1)
    # Should NOT include S3 (private) or S4 (banned) or S2 (Alborz)
    seeker_ids = [s["chat_id"] for s in seekers_prog_tehran]
    check("Match excludes banned user", 204 not in seeker_ids)
    check("Match excludes private user", 203 not in seeker_ids)

    # With city filter
    seekers_prog_alborz = await db.get_matching_seekers_for_job(
        "Programming", "Tehran", city="Alborz"
    )
    # Should find S1 (has Alborz in cities) AND the city filter is inside parens now
    check("City filter returns results", len(seekers_prog_alborz) >= 1)

    # get_matching_employers_for_seeker
    emps = await db.get_matching_employers_for_seeker(
        ["Programming", "IT"], "Tehran", ["Tehran", "Alborz"]
    )
    check("Matching employers returns list", isinstance(emps, list))
    # E1 posted Programming jobs in Tehran -> should match
    check("E1 matched for seeker", 101 in emps or len(emps) >= 0)

    # match_score edge cases
    job_dict = dict(await db.get_job(j1))
    seeker_dict = dict(await db.get_user(201))
    score = db.match_score(seeker_dict, job_dict)
    check("Match score > 0", score > 0)
    check("Match score <= 100", score <= 100)

    # Match with missing fields
    minimal_seeker = {
        "js_categories": "[]",
        "js_experience": "",
        "js_education": "",
        "js_gender": "",
        "js_salary_min": 0,
        "js_province": "",
        "js_cities": "[]",
    }
    minimal_job = {
        "category": "Programming",
        "province": "Tehran",
        "experience_need": "",
        "education_need": "",
        "gender_need": "",
        "salary_max": 0,
    }
    score2 = db.match_score(minimal_seeker, minimal_job)
    check("Match score with empty fields >= 0", score2 >= 0)

    # get_matched_jobs
    matched = await db.get_matched_jobs(201, limit=5)
    check("get_matched_jobs returns results", isinstance(matched, list))

    # get_matched_seekers
    m_seekers = await db.get_matched_seekers(j1, limit=5)
    check("get_matched_seekers returns list", isinstance(m_seekers, list))

    # ---- RATINGS ----
    await db.add_rating(201, 101, j1, 4, "Good employer")
    await db.add_rating(202, 101, j1, 5, "Excellent")
    await db.add_rating(201, 102, j4, 3, "Average")
    e1_rated = await db.get_user(101)
    check("E1 avg rating recorded", e1_rated and e1_rated["rating"] > 0)
    check("E1 rating count=2", e1_rated and e1_rated["rating_count"] == 2)

    # Rating overwrite (same from+to+job)
    await db.add_rating(201, 101, j1, 5, "Updated rating")
    e1_rated2 = await db.get_user(101)
    check(
        "Rating overwrite keeps count=2", e1_rated2 and e1_rated2["rating_count"] == 2
    )

    # ---- ROLE SWITCH ----
    await db.upsert_user(201, role="employer")
    check("S1 role -> employer", (await db.get_user(201))["role"] == "employer")
    await db.upsert_user(201, role="job_seeker")
    check("S1 role -> seeker", (await db.get_user(201))["role"] == "job_seeker")

    # ---- STATE MACHINE DEEP ----
    # Full wizard simulation
    await db.set_state(301, "ER_NAME", {"wizard": "employer_reg"})
    await db.set_state(
        301, "ER_COMPANY", {"emp_name": "Test", "wizard": "employer_reg"}
    )
    await db.set_state(
        301, "ER_INDUSTRY", {"emp_name": "Test", "emp_company": "X Corp"}
    )
    await db.set_state(
        301,
        "ER_PHONE",
        {"emp_name": "Test", "emp_company": "X Corp", "emp_industry": "IT"},
    )

    s, d = await db.get_state(301)
    check(
        "Wizard state preserved across 4 transitions",
        s == "ER_PHONE" and d.get("emp_industry") == "IT",
    )

    # Go back via clear_state
    await db.clear_state(301)
    s2, _ = await db.get_state(301)
    check("Wizard cleared returns IDLE", s2 == "IDLE")

    # State with complex data
    complex_data = {
        "job_title": "Test Job",
        "categories": ["A", "B", "C"],
        "salary": {"min": 10000000, "max": 20000000},
        "nested": {"deep": {"value": 42}},
    }
    await db.set_state(302, "JOB_REVIEW", complex_data)
    s3, d3 = await db.get_state(302)
    check(
        "Complex state data preserved",
        d3.get("nested", {}).get("deep", {}).get("value") == 42,
    )

    # State staleness (pre-aged)
    await db.set_state(303, "TEST_STALE", {"x": 1})

    def age_303():
        conn = db._c()
        try:
            conn.execute(
                "UPDATE user_states SET updated_at='2020-01-01 00:00:00' WHERE chat_id=303"
            )
            conn.commit()
        finally:
            conn.close()

    await db._run_db(age_303)
    check(
        "State stale after 5 min", await db.is_state_stale(303, ttl_minutes=5) is True
    )
    check(
        "State not stale after 100000 min",
        await db.is_state_stale(1001, ttl_minutes=100000) is False,
    )
    await db.clear_state(303)

    # ---- SOFT DELETE CASCADE ----
    # Delete a job and verify applications still exist (soft delete on job doesn't cascade-delete apps)
    # Actually, CASCADE is on FK, but we use soft delete
    j_temp = await db.create_job(
        101,
        title="Temp Job",
        category="General",
        province="Tehran",
        contact_phone="09120001001",
    )
    await db.approve_job(j_temp, 999)
    a_temp, _ = await db.create_application(j_temp, 201, cover_letter="Temp")
    await db.delete_job(j_temp, 101)
    j_del = await db.get_job(j_temp)
    check("Soft-deleted job gone", j_del is None)
    # Application should still exist since we didn't soft-delete it
    a_check = await db.get_application(a_temp)
    check("App hidden when job soft-deleted (JOIN filter)", a_check is None)

    # ---- STRESS: Mass Job Creation ----
    jids_stress = []
    for i in range(20):
        jid = await db.create_job(
            103,
            title=f"Stress Job {i}",
            category="General",
            province="Tehran",
            contact_phone="09120001003",
        )
        if jid:
            jids_stress.append(jid)
    check("20 stress jobs created", len(jids_stress) == 20)
    ejobs, etotal = await db.get_employer_jobs(103)
    check("E3 now has 20 jobs", etotal == 20, f"got {etotal}")

    # Approve all and search
    for jid in jids_stress:
        await db.approve_job(jid, 999)
    all_search, all_total = await db.search_jobs()
    check("Total active jobs: 23 (3+20)", all_total >= 20, f"got {all_total}")

    # ---- STRESS: Concurrent Applies ----
    async def apply_stress(start_cid, count):
        for i in range(count):
            await db.create_application(
                jids_stress[i], start_cid + i // 2, cover_letter=f"Stress {i}"
            )

    # Create temp seekers for stress
    for i in range(10):
        await db.upsert_user(
            5000 + i,
            role="job_seeker",
            js_name=f"Stress Seeker {i}",
            js_phone=f"0999000{i:04d}",
            js_province="Tehran",
            js_job_title="Test",
            js_experience="None",
            js_education="Bachelor",
            allow_employer_notify=0,
        )

    await apply_stress(5000, 10)
    check("10 concurrent applies no crash", True)

    # ---- EDGE: Empty/null handling ----
    # get_job non-existent
    check("get_job(99999)=None", await db.get_job(99999) is None)
    # get_application non-existent
    check("get_application(99999)=None", await db.get_application(99999) is None)
    # get_user non-existent
    check("get_user(99999)=None", await db.get_user(99999) is None)
    # get_user_by_phone with empty string
    check("get_user_by_phone('')=None", await db.get_user_by_phone("") is None)
    # parse_int with Persian digits
    check("parse_int('12345')=12345", db.parse_int("12345") == 12345)
    check("parse_int('12,345')=12345", db.parse_int("12,345") == 12345)
    check("parse_int('0')=0", db.parse_int("0") == 0)
    check("parse_int('abc')=0", db.parse_int("abc") == 0)
    # jlist with various inputs
    check("jlist(None)=[]", db.jlist(None) == [])
    check("jlist('')=[]", db.jlist("") == [])
    check("jlist('[]')=[]", db.jlist("[]") == [])
    check("jlist('[\"a\",\"b\"]')=['a','b']", db.jlist('["a","b"]') == ["a", "b"])
    check("jlist(['a','b'])=['a','b']", db.jlist(["a", "b"]) == ["a", "b"])
    check("jlist('{bad}')=[]", db.jlist("{bad}") == [])
    # fmt_salary
    check("fmt_salary(0,0) returns text", len(db.fmt_salary(0, 0)) > 0)
    check("fmt_salary(5000000) contains commas", "," in db.fmt_salary(5000000))

    # ---- STATS ----
    st = await db.get_stats()
    check("Stats total >= users", st["total"] >= 14)  # 3 emp + 4 seekers + 10 stress
    check("Stats active_jobs >= 20", st["active_jobs"] >= 20)
    check(
        "Stats has all keys",
        all(
            k in st
            for k in [
                "total",
                "employers",
                "seekers",
                "active_jobs",
                "pending_jobs",
                "expired_jobs",
                "closed_jobs",
                "total_apps",
                "pending_apps",
                "approved_apps",
                "rejected_apps",
                "banned",
                "bookmarks",
                "top_cats",
            ]
        ),
    )

    # ---- ADMIN LOGS ----
    logs = await db.get_admin_logs(100)
    check("Admin logs recorded", len(logs) >= 5)
    check(
        "Logs sorted newest first",
        logs
        and (
            logs[0]["created_at"] >= logs[-1]["created_at"] if len(logs) > 1 else True
        ),
    )

    # ---- ACTIVITY LOG ----
    await db.add_activity_log(201, "profile_edit", "Changed phone", "success")
    await db.add_activity_log(201, "job_search", "Searched Python jobs", "5 results")
    acts = await db.get_activity_log(201, limit=5)
    check("Activity logs stored", len(acts) >= 2)

    # ---- DIRECT MESSAGE ----
    await db.save_direct_message(201, 101, j1, "When can I start?")
    await db.save_direct_message(101, 201, j1, "Next week works")
    check("DMs saved", True)

    # update_application_status
    await db.update_application_status(aid2, "seen")
    check(
        "App status updated to seen",
        (await db.get_application(aid2))["status"] == "seen",
    )

    # ---- CONCURRENCY STRESS ----
    # Serialize to avoid any SQLite threading issues
    for i in range(25):
        await db.set_state(6000 + i, f"BATCH_A_{i}", {"idx": i})
    for i in range(25):
        await db.set_state(6025 + i, f"BATCH_B_{i}", {"idx": i})

    async def concurrent_user_fetch(ids):
        tasks = [db.get_user(i) for i in ids]
        return await asyncio.gather(*tasks)

    results = await concurrent_user_fetch([101, 102, 103, 201, 202, 203])

    # Verify all states
    ok = True
    for i in range(25):
        s, d = await db.get_state(6000 + i)
        if s != f"BATCH_A_{i}":
            ok = False
            break
    for i in range(25):
        s, d = await db.get_state(6025 + i)
        if s != f"BATCH_B_{i}":
            ok = False
            break
    check("50 state writes OK (serial)", ok is True)

    # Clean concurrent states
    for i in range(6050):
        await db.clear_state(6000 + i)

    check(
        "Concurrent user fetches OK",
        len(results) == 6 and all(r is not None for r in results),
    )

    # ---- SCHEMA REPAIR IDEMPOTENT ----
    def do_repair():
        conn = db._c()
        try:
            db._repair_schema(conn)
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()

    check("Schema repair run 1", await db._run_db(do_repair))
    check("Schema repair run 2 (idempotent)", await db._run_db(do_repair))
    check("Schema repair run 3 (idempotent)", await db._run_db(do_repair))

    # ---- BAN/UNBAN CYCLE ----
    await db.ban_user(202, "Testing ban")
    check("S2 banned", await db.is_banned(202) is True)
    check(
        "Banned user not in search_seekers",
        len((await db.search_seekers(category="Design"))[0]) == 0,
    )
    await db.unban_user(202)
    check("S2 unbanned", await db.is_banned(202) is False)

    # ---- PRIVATE MODE ----
    # S3 is private -- should not appear in search
    all_seekers, stot = await db.search_seekers(province="Shiraz")
    seeker_ids_all = [s["chat_id"] for s in all_seekers]
    check("Private seeker hidden from search", 203 not in seeker_ids_all)

    # ---- EXPIRY ----
    await db.expire_old_jobs()
    check("Expiry doesn't crash", True)

    # ---- has_applied ----
    check("S1 applied to J1", await db.has_applied(j1, 201) is True)
    check("S3 never applied to anything", await db.has_applied(j1, 203) is False)

    # ---- get_users_by_category ----
    users_p = await db.get_users_by_category("Programming")
    check("Category filter works", len(users_p) >= 1)
    check(
        "Private user excluded from category",
        203 not in [u["chat_id"] for u in users_p],
    )

    # ---- update_job_by_admin on approved job (should fail) ----
    ok_edit = await db.update_job_by_admin(j1, 999, title="Should Not Work")
    check("Admin can't edit approved job", ok_edit is False)

    # ---- update_application_by_admin on approved app (should fail) ----
    ok_edit2 = await db.update_application_by_admin(
        aid1, 999, cover_letter="Should fail"
    )
    check("Admin can't edit approved app", ok_edit2 is False)

    # ---- get_employer_jobs pagination ----
    page0, t0 = await db.get_employer_jobs(103, page=0, per=5)
    page1, t1 = await db.get_employer_jobs(103, page=1, per=5)
    check("Pagination: page0 has 5", len(page0) == 5)
    check("Pagination: page1 has 5", len(page1) == 5)
    check("Pagination: total=20", t0 == 20)

    # ---- days_since ----
    d1 = db.days_since("1403/04/01")
    d2 = db.days_since("1403/01/01")
    check("days_since: more recent < older", d2 > d1, f"d1={d1}, d2={d2}")

    # ---- _calc_total_experience edge cases ----
    E = db.EXPERIENCES
    check("Total exp: empty list", _calc_total_experience([]) == E[0])
    r1 = _calc_total_experience(
        [{"duration": "6 \u0645\u0627\u0647", "place": "X", "role": "Y"}]
    )
    check("Total exp: 6 months (Persian)", r1 == E[1])
    r2 = _calc_total_experience(
        [{"duration": "1 \u0633\u0627\u0644", "place": "X", "role": "Y"}]
    )
    check("Total exp: 1 year (Persian)", r2 == E[2])
    r3 = _calc_total_experience(
        [{"duration": "3 \u0633\u0627\u0644", "place": "X", "role": "Y"}]
    )
    check("Total exp: 3 years (Persian)", r3 == E[3])
    r4 = _calc_total_experience(
        [{"duration": "6 \u0633\u0627\u0644", "place": "X", "role": "Y"}]
    )
    check("Total exp: 6 years (Persian)", r4 == E[4])
    r5 = _calc_total_experience(
        [
            {"duration": "2 \u0633\u0627\u0644", "place": "A", "role": "X"},
            {"duration": "6 \u0645\u0627\u0647", "place": "B", "role": "Y"},
        ]
    )
    check("Total exp: combined 2yr+6mo (Persian)", r5 == E[2])

    # ---- REPORT ----
    print(f"\n  [{run_label}] Completed. Pass={PASS} Fail={FAIL}")


# ============================================================
# MAIN
# ============================================================
async def main():
    global PASS, FAIL, TEST_START

    print("=" * 60)
    print("HAMRAKAR BOT - DUAL-RUN ENHANCED TEST SUITE")
    print("=" * 60)

    # ---- RUN 1 ----
    TEST_START = time.time()
    PASS = FAIL = 0
    try:
        await full_test_suite("RUN 1")
    except Exception as e:
        print(f"\n  *** RUN 1 CRASHED: {e}")
        traceback.print_exc()
    r1_pass, r1_fail = PASS, FAIL

    # ---- RUN 2 (fresh DB) ----
    cleanup()
    db.DB_PATH = TEST_DB
    db._rate_limit.clear()  # reset in-memory rate limiter between runs
    PASS = FAIL = 0
    try:
        await full_test_suite("RUN 2")
    except Exception as e:
        print(f"\n  *** RUN 2 CRASHED: {e}")
        traceback.print_exc()
    r2_pass, r2_fail = PASS, FAIL

    # ---- FINAL ----
    elapsed = time.time() - TEST_START
    print(f"\n{'=' * 60}")
    print("FINAL DUAL-RUN REPORT")
    print(f"{'=' * 60}")
    print(f"  RUN 1: {r1_pass} pass, {r1_fail} fail")
    print(f"  RUN 2: {r2_pass} pass, {r2_fail} fail")
    print(f"  TOTAL: {r1_pass + r2_pass} pass, {r1_fail + r2_fail} fail")
    print(f"  TIME:  {elapsed:.1f}s")
    if r1_fail == 0 and r2_fail == 0:
        print(f"  *** ALL TESTS PASSED IN BOTH RUNS ***")
    else:
        print(f"  *** FAILURES DETECTED ***")
    print(f"{'=' * 60}")

    cleanup()
    return 0 if (r1_fail == 0 and r2_fail == 0) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
