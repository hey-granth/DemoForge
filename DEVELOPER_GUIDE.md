# Developer Operations Guide

Command reference for building, running, and testing the DemoForge system.

---

## 1. Environment Setup

### Backend
```bash
# Clone and enter project
cd DemoForge

# Initialize environment
cp .env.example .env
# Required: Set OPENAI_API_KEY in .env if using LLM planner
```

### Frontend
```bash
cd frontend
# Install dependencies (requires Node 18+)
npm install
```

---

## 2. Running the System

### Full Stack (Recommended)
```bash
# Start backend (API + Redis + Worker)
docker-compose up -d

# Start frontend (Dev mode)
cd frontend
npm run dev
```

### Resource Management
```bash
# View backend logs
docker-compose logs -f

# Scale workers for faster processing
docker-compose up -d --scale worker=3

# Stop all backend services
docker-compose down -v
```

---

## 3. API Testing (Manual)

Use these commands to verify the backend independent of the UI.

### Health Check
```bash
curl http://localhost:8000/health
```

### Submit a Job
```bash
curl -X POST http://localhost:8000/demo/run \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```
*Take note of the `job_id` in the response.*

### Check Job Status
```bash
# Replace {job_id} with your actual ID
curl http://localhost:8000/demo/status/{job_id}
```

### Export/Download Video
```bash
curl http://localhost:8000/demo/export/{job_id} -o demo.mp4
```

### Force Cleanup
```bash
curl -X DELETE http://localhost:8000/demo/cleanup/{job_id}
```

---

## 4. Troubleshooting

### Browser/Worker Issues
If videos are not generating:
```bash
# Check worker logs for Playwright/FFmpeg errors
docker-compose logs -f worker
```

### Redis Inspection
```bash
# Enter Redis CLI inside the container
docker-compose exec redis redis-cli

# Check queue length
LLEN demo:queue

# List all job keys
KEYS job:*
```

### Frontend Debugging
```bash
# Run build to check for production issues
cd frontend
npm run build
```

---

## 5. Development Workflow
1. Start Backend: `docker-compose up -d`
2. Start Frontend: `npm run dev` (in `frontend/`)
3. Open: `http://localhost:3000`
4. Monitor: `docker-compose logs -f worker`
