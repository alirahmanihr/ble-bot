from fastapi import FastAPI
import database as db

app = FastAPI(title="Hamrakar API", version="1.0.0")


@app.on_event("startup")
async def startup():
    await db.init_db()


@app.get("/stats")
async def stats():
    data = await db.get_stats()
    return data


@app.get("/users")
async def users():
    users_list = await db.get_all_users()
    return {"count": len(users_list), "users": [dict(u) for u in users_list]}


@app.get("/applications")
async def applications():
    apps_list = await db.get_all_applications()
    return {"count": len(apps_list), "applications": [dict(a) for a in apps_list]}


@app.get("/resume-requests/pending")
async def resume_requests_pending():
    reqs = await db.get_pending_resume_requests()
    return {"count": len(reqs), "resume_requests": [dict(r) for r in reqs]}


@app.post("/approve-application/{app_id}")
async def approve_application(app_id: int):
    await db.approve_application(app_id)
    return {"ok": True, "app_id": app_id}


@app.post("/reject-application/{app_id}")
async def reject_application(app_id: int, reason: str = ""):
    await db.reject_application(app_id, reason)
    return {"ok": True, "app_id": app_id}


@app.post("/approve-resume-request/{req_id}")
async def approve_resume_request(req_id: int):
    await db.approve_resume_request(req_id)
    return {"ok": True, "req_id": req_id}


@app.post("/reject-resume-request/{req_id}")
async def reject_resume_request(req_id: int, reason: str = ""):
    await db.reject_resume_request(req_id)
    return {"ok": True, "req_id": req_id}


@app.get("/jobs")
async def get_jobs_list():
    jobs = await db.get_all_jobs()
    return {"count": len(jobs), "jobs": [dict(j) for j in jobs]}


@app.post("/approve-job/{job_id}")
async def approve_job(job_id: int):
    await db.approve_job(job_id)
    return {"ok": True, "job_id": job_id}


@app.post("/reject-job/{job_id}")
async def reject_job(job_id: int, reason: str = ""):
    await db.reject_job(job_id, reason)
    return {"ok": True, "job_id": job_id}


@app.post("/send")
async def send(data: dict):
    return {"ok": True, "sent": data}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
