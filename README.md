# DemoForge

DemoForge generates automated demo videos of websites.

It accepts a URL, enqueues a job, drives an isolated browser session, records the interaction, converts the capture to MP4, and returns the result to the user. The system is designed for deterministic execution, ephemeral artifacts, and horizontal worker scaling.

## Motivation

Creating repeatable product walkthroughs by hand is slow and difficult to operationalize. DemoForge provides a service-oriented pipeline for generating short demo videos from public websites without persisting browser state or long-lived media artifacts.

## Core Features

- FastAPI API for job creation, status polling, export, and cleanup
- Redis-backed queue and transient job state storage
- Isolated Playwright Chromium sessions per job
- Automated interaction discovery and ranked action planning
- MP4 post-processing with `ffmpeg`
- Next.js frontend for submission, progress tracking, and download
- Ephemeral artifact handling with one-hour retention and delete-on-export behavior
- Worker scaling through container replication

## Demo Workflow

1. A user submits a website URL.
2. The API validates the request and creates a queued job in Redis.
3. A worker consumes the job and starts an isolated Playwright browser session.
4. The worker explores safe interactions on the target site.
5. The session is recorded.
6. The raw recording is processed into MP4 with `ffmpeg`.
7. The user polls job status and downloads the generated video.

## Architecture Overview

```text
User -> Frontend -> API -> Redis -> Worker -> Browser -> Video -> User
```

- The frontend submits URLs and polls job state.
- The API is stateless and only coordinates job lifecycle.
- Redis acts as both queue and transient artifact store.
- Workers execute browser sessions, generate recordings, and publish MP4 output.
- Video artifacts are temporary and removed after export or TTL expiry.

## System Components

### Frontend
- Next.js application in `frontend/`
- Accepts a URL, submits jobs, polls status, and downloads MP4 output
- Uses a local rewrite from `/api/*` to `http://localhost:8000/*` during development

### API Service
- FastAPI application in `api/main.py`
- Exposes `POST /demo/run`, `GET /demo/status/{job_id}`, `GET /demo/export/{job_id}`, `DELETE /demo/cleanup/{job_id}`, and `GET /health`
- Stores job metadata in Redis with TTL-based expiry

### Worker Service
- Async Python worker in `worker/runner.py`
- Consumes `demo:queue`, launches Playwright, executes interactions, records video, and stores MP4 output in Redis
- Applies runtime limits and interaction safety filters

### Redis
- Coordinates queued jobs and transient job/video state
- Stores job metadata under `job:{job_id}` and generated video under `video:{job_id}`

## Project Structure

```text
api/        FastAPI service and HTTP endpoints
worker/     Browser automation, planning, execution, and video processing
frontend/   Next.js UI, polling hooks, and browser-side API client
docker/     Container images for the API and worker services
tests/      Pytest-based coverage for API and worker modules
```

The repository does not currently include a `scripts/` directory. Operational commands are kept in `Makefile`, `docker-compose.yml`, and the service-specific dependency manifests.

## Local Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js and npm for the frontend

### Recommended local workflow

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Start Redis, the API, and the worker stack:
   ```bash
   docker compose up --build -d
   ```
3. Start the frontend development server:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. Open `http://localhost:3000`.
5. Verify backend health at `http://localhost:8000/health`.

### Optional service-by-service development

Docker is the reference runtime. If you need to run services directly on the host, use the pinned dependency files in `api/requirements.txt`, `worker/requirements.txt`, and `tests/requirements.txt`, and install Playwright Chromium plus `ffmpeg` locally.

## Running with Docker

The Compose stack includes `redis`, `api`, and `worker`.

```bash
docker compose up --build -d
docker compose logs -f worker
docker compose up -d --scale worker=3
docker compose down -v
```

Notes:
- The frontend is not part of `docker-compose.yml` and is typically run separately from `frontend/`.
- The worker image installs Playwright Chromium and `ffmpeg`.

## Configuration

Configuration is sourced from environment variables.

| Variable | Service | Default | Purpose |
| --- | --- | --- | --- |
| `REDIS_HOST` | API, worker | `localhost` | Redis hostname |
| `REDIS_PORT` | API, worker | `6379` | Redis port |
| `JOB_TTL` | API | `3600` | Initial job metadata retention in seconds |
| `POLL_INTERVAL` | worker | `2` | Queue polling interval in seconds |
| `MAX_CLICKS` | worker | `10` | Maximum interactions per job |
| `MAX_DEPTH` | worker | `3` | Maximum navigation depth |
| `MAX_RUNTIME` | worker | `300` | Maximum execution time in seconds |
| `GEMINI_API_KEY` | worker | unset | Optional ranking model for interaction planning |

Operational notes:
- Generated videos are stored transiently and are not intended for permanent retention.
- Export deletes the video and job state after streaming.
- The current implementation uses a one-hour TTL for transient artifacts.

## Usage Example

### API flow

```bash
curl -X POST http://localhost:8000/demo/run \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

curl http://localhost:8000/demo/status/<job_id>

curl http://localhost:8000/demo/export/<job_id> -o demo.mp4
```

### Frontend flow

1. Open `http://localhost:3000`.
2. Submit a public website URL.
3. Wait for the job to transition from `pending` to `processing` to `completed`.
4. The frontend downloads the MP4 automatically when the job completes.

## Design Principles

- Deterministic execution over exploratory breadth
- Isolated and sandboxed browser sessions
- Stateless API and ephemeral workers
- Temporary artifacts with explicit cleanup semantics
- Clear failure states for queueing, execution, and export paths
- Horizontal scaling through independent workers

## Roadmap / Future Potential

- Smarter interaction discovery and page-state understanding
- Visual step highlighting in the generated video
- Multi-browser execution support beyond Chromium
- Optional voiceover generation for narrated demos
- Customizable demo scripts and per-domain policies
- CI-driven demo generation for release workflows
- Programmatic API access for external automation
- Distributed worker scaling and queue partitioning

## Contributing

See `CONTRIBUTING.md` for development workflow, testing expectations, pull request standards, and security reporting guidance.

## License

A repository license file has not been published yet. Do not assume redistribution or production usage rights until a license is added.
