## SYSTEM ARCHITECTURE

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   API Layer  │────────▶│ Redis Queue  │◀────────│   Worker     │
│   (FastAPI)  │         │  (Job Store) │         │  (Executor)  │
└──────────────┘         └──────────────┘         └──────────────┘
       │                                                   │
       │                                                   │
       ▼                                                   ▼
┌──────────────┐                               ┌──────────────────┐
│    Client    │                               │ Browser Session  │
│  (HTTP/MP4)  │                               │   (Playwright)   │
└──────────────┘                               └──────────────────┘
```

## MODULE RESPONSIBILITIES

### API Layer (`/api/main.py`)
- Accept job requests via POST /demo/run
- Return job_id immediately
- Store job metadata in Redis with TTL
- Push job_id to queue
- Expose status endpoint
- Stream MP4 on export
- Delete artifacts after stream

### Job Orchestration (Redis)
- Queue: `demo:queue` (list)
- Job metadata: `job:{job_id}` (string, JSON)
- Video storage: `video:{job_id}` (binary)
- TTL: 3600s default
- No payload larger than video binary

### Worker (`/worker/runner.py`)
- Poll Redis queue (BRPOP)
- Update job status: pending → processing → completed/failed
- Orchestrate execution pipeline
- Store video in Redis
- Cleanup temp files

### Browser Automation (`/worker/browser.py`)
- Launch Chromium via Playwright
- Fixed viewport: 1280×720
- Enable video recording
- Navigate with networkidle wait
- Scroll page for content reveal
- Click elements by selector
- Return video path on stop

### Interaction Discovery (`/worker/discovery.py`)
- Scan DOM for interactable elements
- Extract: buttons, links, role=button
- Filter by visibility and enabled state
- Generate fingerprints (MD5 of tag:text:role:href)
- Track visited fingerprints
- Return unvisited elements

### LLM Planner (`/worker/planner.py`)
- Accept element list + current URL
- Apply blacklist (delete, pay, checkout, etc.)
- Call GPT-4o-mini for ranking (optional)
- Fallback to keyword scoring
- Return ActionPlan array with selector + priority
- Max 5 actions per scan

### Execution Controller (`/worker/executor.py`)
- State machine: initial → navigating → discovering → planning → executing → complete
- Enforce limits:
  - max_clicks: 10
  - max_depth: 3
  - max_runtime: 300s
- Track visited URLs
- Abort on domain change
- Abort on auth pages
- Break on no unvisited elements
- Raise SafetyViolation on timeout

### Video Pipeline (`/worker/recorder.py`)
- Accept raw video from Playwright
- Use ffmpeg for processing:
  - Trim start/end idle time
  - Normalize framerate (30 fps)
  - Encode as H.264 MP4
  - Apply faststart flag
- Delete raw video after processing
- Return final MP4 path

## EXECUTION FLOW

1. Client sends POST /demo/run with URL
2. API generates job_id, stores metadata in Redis, pushes to queue
3. Worker pops job_id from queue
4. Worker updates status to "processing"
5. Worker starts browser session with recording
6. Worker navigates to URL
7. Worker scrolls page
8. Loop (until limits reached):
   a. Scan DOM for elements
   b. Filter unvisited elements
   c. Rank interactions via LLM
   d. Execute top-ranked action
   e. Wait for idle
   f. Check runtime/depth/click limits
9. Worker stops browser, retrieves raw video
10. Worker processes video with ffmpeg
11. Worker stores video binary in Redis
12. Worker updates status to "completed"
13. Client polls GET /demo/status/{job_id}
14. Client requests GET /demo/export/{job_id}
15. API streams video, deletes artifacts

## GUARDRAILS

### Safety Blacklist
- delete, remove, unsubscribe, deactivate
- pay, checkout, purchase, buy
- cancel, close account, sign out, log out

### Runtime Limits
- Max clicks: 10
- Max depth: 3 navigations
- Max runtime: 300s
- Video processing timeout: 120s

### Domain Restriction
- Only interact within initial domain
- Abort if domain changes

### Auth Detection
- URL patterns: /login, /signin, /register, /auth
- Abort if detected

### Resource Limits (Docker)
- CPU: 2 cores max
- Memory: 2GB max
- Ephemeral storage only

## FAILURE MODES

### Job Not Found
- Return 404 on status/export

### Job Not Completed
- Return 400 with current status

### Video Not Found
- Return 404 after completion

### Browser Crash
- Catch exception, mark job failed
- Store error message in Redis

### FFmpeg Failure
- Catch exception, mark job failed
- Cleanup partial files

### Runtime Timeout
- SafetyViolation raised
- Mark job failed
- Force browser stop

### Redis Unavailable
- API returns 503
- Worker retries connection

## DEPLOYMENT

### Build
```bash
docker-compose build
```

### Run
```bash
docker-compose up -d
```

### Scale Workers
```bash
docker-compose up -d --scale worker=3
```

### Logs
```bash
docker-compose logs -f worker
```

### Cleanup
```bash
docker-compose down -v
```

## ENVIRONMENT VARIABLES

### API
- REDIS_HOST: Redis hostname
- REDIS_PORT: Redis port
- JOB_TTL: Job expiration (seconds)

### Worker
- REDIS_HOST: Redis hostname
- REDIS_PORT: Redis port
- POLL_INTERVAL: Queue polling interval (seconds)
- MAX_CLICKS: Maximum interactions per job
- MAX_DEPTH: Maximum navigation depth
- MAX_RUNTIME: Maximum execution time (seconds)
- OPENAI_API_KEY: Optional LLM key

## DATA FLOW

### Job Metadata (Redis)
```json
{
  "job_id": "uuid",
  "url": "https://example.com",
  "status": "pending|processing|completed|failed",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "error": "string|null"
}
```

### Action Plan
```json
{
  "selector": "button:nth-of-type(1)",
  "action": "click",
  "priority": 1,
  "reason": "Primary CTA"
}
```

### Execution Metrics
```json
{
  "state": "complete",
  "clicks": 8,
  "depth": 2,
  "visited_urls": 3,
  "runtime": 45.2
}
```

## SECURITY

- No credential storage
- No cookie persistence
- No localStorage reuse
- Sandboxed browser context
- Network egress unrestricted (required for target sites)
- No file system mounts
- Ephemeral containers
- TTL-enforced cleanup

## STATELESS DESIGN

- No persistent databases
- No file storage beyond TTL
- No session management
- No user accounts
- No analytics
- Redis as ephemeral store only
- All state deleted post-export
