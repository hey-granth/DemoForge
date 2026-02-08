import os
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
import redis.asyncio as redis
import json
from datetime import datetime

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
JOB_TTL = int(os.getenv("JOB_TTL", "3600"))

redis_client: Optional[redis.Redis] = None


class DemoRequest(BaseModel):
    url: HttpUrl


class JobResponse(BaseModel):
    job_id: str
    status: str
    created_at: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    created_at: str
    updated_at: str
    error: Optional[str] = None


@app.on_event("startup")
async def startup():
    global redis_client
    try:
        redis_client = await redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=False
        )
        await redis_client.ping()
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        redis_client = None


@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()


@app.post("/demo/run", response_model=JobResponse)
async def create_demo(request: DemoRequest):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    job_data = {
        "job_id": job_id,
        "url": str(request.url),
        "status": "pending",
        "created_at": now,
        "updated_at": now
    }
    
    await redis_client.setex(
        f"job:{job_id}",
        JOB_TTL,
        json.dumps(job_data)
    )
    
    await redis_client.lpush("demo:queue", job_id)
    
    return JobResponse(
        job_id=job_id,
        status="pending",
        created_at=now
    )


@app.get("/demo/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    job_data = await redis_client.get(f"job:{job_id}")
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    data = json.loads(job_data)
    
    return JobStatus(
        job_id=data["job_id"],
        status=data["status"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        error=data.get("error")
    )


@app.get("/demo/export/{job_id}")
async def export_video(job_id: str):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    job_data = await redis_client.get(f"job:{job_id}")
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    data = json.loads(job_data)
    
    if data["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job status is {data['status']}, not completed"
        )
    
    video_key = f"video:{job_id}"
    video_data = await redis_client.get(video_key)
    
    if not video_data:
        raise HTTPException(status_code=404, detail="Video not found")
    
    async def stream_and_cleanup():
        yield video_data
        try:
            await redis_client.delete(video_key)
            await redis_client.delete(f"job:{job_id}")
        except:
            pass
    
    return StreamingResponse(
        stream_and_cleanup(),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f"attachment; filename=demo-{job_id}.mp4"
        }
    )


@app.delete("/demo/cleanup/{job_id}")
async def cleanup_job(job_id: str):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    deleted = await redis_client.delete(
        f"job:{job_id}",
        f"video:{job_id}"
    )
    
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"status": "deleted", "job_id": job_id}


@app.get("/health")
async def health():
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")
    try:
        await redis_client.ping()
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
