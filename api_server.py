from fastapi import FastAPI
import asyncio

app = FastAPI()

# -----------------------
# MOCK DB CONNECTION (later real DB)
# -----------------------
import database as db


@app.on_event("startup")
async def startup():
    await db.init_db()


# -----------------------
# DASHBOARD STATS
# -----------------------
@app.get("/stats")
async def stats():
    data = await db.get_stats()
    return data


# -----------------------
# USERS LIST
# -----------------------
@app.get("/users")
async def users():
    # ساده شده برای MVP
    return {"ok": True, "message": "users endpoint ready"}


# -----------------------
# JOBS LIST
# -----------------------
@app.get("/jobs")
async def jobs():
    jobs = await db.get_jobs()
    return {"jobs": jobs}


# -----------------------
# APPROVE JOB (ADMIN PANEL)
# -----------------------
@app.post("/approve-job/{job_id}")
async def approve_job(job_id: int):
    await db.approve_job(job_id)
    return {"ok": True, "job_id": job_id}


# -----------------------
# SEND MESSAGE TO BOT (BRIDGE)
# -----------------------
@app.post("/send")
async def send(data: dict):
    # این بعداً به bot وصل می‌شود
    return {
        "ok": True,
        "sent": data
    }
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)