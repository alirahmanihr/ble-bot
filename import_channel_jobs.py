"""
اسکریپت وارد کردن آگهی‌های کانال به دیتابیس
=============================================
آگهی‌هایی که قبلاً در کانال منتشر شده‌اند را مستقیم وارد دیتابیس می‌کند.
- وضعیت: active (نیاز به تأیید ادمین ندارد)
- انقضا: ۳۰ روز
- کارفرما: سیستم (کانال هم‌راه‌کار)

روش استفاده:
  ۱. آگهی‌ها را در لیست JOBS_DATA (پایین همین فایل) به فرمت استاندارد وارد کنید.
  ۲. فایل را اجرا کنید:   python import_channel_jobs.py

فرمت استاندارد هر آگهی:
  {
      "title":       "عنوان شغلی",           # الزامی
      "category":    "دسته‌بندی",            # الزامی — از لیست CATEGORIES
      "province":    "استان",                # اختیاری
      "city":        "شهر",                  # اختیاری
      "emp_type":    "نوع همکاری",           # اختیاری: تمام‌وقت، پاره‌وقت، دورکاری...
      "salary_min":  5000000,               # اختیاری — عدد به تومان
      "salary_max":  10000000,              # اختیاری
      "description": "توضیحات کامل آگهی",    # اختیاری
      "benefits":    "مزایا",                # اختیاری
      "gender_need": "جنسیت",               # اختیاری: مرد، زن، مهم نیست
      "education_need": "تحصیلات",          # اختیاری
      "experience_need": "سابقه",           # اختیاری
      "contact_phone": "0912xxxxxxx",       # اختیاری
      "contact_email": "email@example.com", # اختیاری
  }
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import database as db
from database import CATEGORIES, PROVINCES, EMP_TYPES, GENDERS, EDUCATIONS, EXPERIENCES

# ═══════════════════════════════════════════════════════════════
# 📝 اینجا آگهی‌های کانال را وارد کنید
# ═══════════════════════════════════════════════════════════════
JOBS_DATA = [
    # ── نمونه (برای تست) ──
    # {
    #     "title": "برنامه‌نویس بک‌اند پایتون",
    #     "category": "فناوری اطلاعات",
    #     "province": "تهران",
    #     "city": "تهران",
    #     "emp_type": "تمام‌وقت",
    #     "salary_min": 15000000,
    #     "salary_max": 25000000,
    #     "description": "مسلط به Django و PostgreSQL — حداقل ۲ سال سابقه",
    #     "benefits": "بیمه، ناهار رایگان، دورکاری پنج‌شنبه‌ها",
    #     "education_need": "کارشناسی",
    #     "experience_need": "۲ سال",
    #     "contact_phone": "021-12345678",
    # },
]

# ═══════════════════════════════════════════════════════════════


def validate_job(job: dict, index: int) -> list[str]:
    """Check required fields and valid values. Returns list of warnings."""
    warnings = []

    if not job.get("title"):
        warnings.append(f"آگهی #{index}: عنوان ندارد — رد شد")
    if not job.get("category"):
        warnings.append(f"آگهی #{index}: دسته‌بندی ندارد — رد شد")
    elif job["category"] not in CATEGORIES:
        warnings.append(
            f"آگهی #{index}: دسته‌بندی '{job['category']}' در لیست نیست. "
            f"گزینه‌های معتبر: {', '.join(CATEGORIES[:5])}..."
        )

    if job.get("province") and job["province"] not in PROVINCES:
        warnings.append(f"آگهی #{index}: استان '{job['province']}' معتبر نیست")

    return warnings


async def main():
    print("=" * 60)
    print("📥 IMPORT CHANNEL JOBS")
    print("=" * 60)

    if not JOBS_DATA:
        print("\n⚠️  لیست JOBS_DATA خالی است. آگهی‌ها را اضافه کنید.\n")
        return

    await db.init_db()

    # Validate
    valid_jobs = []
    skipped = 0
    for i, job in enumerate(JOBS_DATA, 1):
        warnings = validate_job(job, i)
        if any("رد شد" in w for w in warnings):
            for w in warnings:
                print(f"  ❌ {w}")
            skipped += 1
        else:
            for w in warnings:
                print(f"  ⚠️  {w}")
            valid_jobs.append(job)

    if not valid_jobs:
        print("\n❌ هیچ آگهی معتبری برای وارد کردن نیست.\n")
        return

    # Import
    print(f"\n📦 در حال وارد کردن {len(valid_jobs)} آگهی...\n")
    imported = []
    failed = 0

    for i, job in enumerate(valid_jobs, 1):
        # Clean None values and empty strings
        clean = {k: v for k, v in job.items() if v is not None and v != ""}
        jid = await db.create_channel_job(**clean)
        if jid:
            imported.append((jid, job["title"]))
            print(f"  ✅ #{i} | id={jid} | {job['title']}")
        else:
            failed += 1
            print(f"  ❌ #{i} | {job['title']} — خطا در ذخیره")

    # Summary
    stats = await db.get_stats()
    print("\n" + "=" * 60)
    print("📊 نتیجه نهایی:")
    print(f"   ✅ وارد شده: {len(imported)}")
    print(f"   ⏭️  رد شده:  {skipped}")
    print(f"   ❌ خطا:     {failed}")
    print(f"   📋 کل آگهی‌های فعال: {stats['active_jobs']}")
    print(f"   ⏰ انقضای خودکار: ۳۰ روز دیگر")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
