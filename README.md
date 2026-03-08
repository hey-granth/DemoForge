# DemoForge

DemoForge generates automated demo videos of websites.

It accepts a URL, drives an isolated browser session, records the interaction, converts the capture to MP4, and returns the result. Available as a **single Docker container**, a **CLI tool**, or a **multi-service deployment**.

## Quick Start

### Docker (recommended)

Run the full stack in one command:

```bash
docker run -p 8080:8080 heygranth/demoforge
```

Open `http://localhost:8080` to access the UI.

### CLI

Install with `pipx`:

```bash
pipx install demoforge
demoforge setup          # one-time: install Playwright Chromium
demoforge https://example.com
```

Or with pip:

```bash
pip install demoforge
demoforge setup
demoforge https://example.com --output demo.mp4
```

### CLI Options

```
demoforge <url>                          # record with defaults
demoforge <url> --output demo.mp4        # custom output path
demoforge <url> --viewport 1920x1080     # custom viewport
demoforge <url> --max-clicks 15          # more interactions
demoforge <url> --max-runtime 600        # longer timeout
demoforge setup                          # install browser
demoforge --version                      # print version
```

## Motivation

Creating repeatable product walkthroughs by hand is slow and difficult to operationalize. DemoForge provides a pipeline for generating short demo videos from public websites without persisting browser state or long-lived media artifacts.

## Core Features

- **Single Docker image** with all services bundled (API, worker, Redis, frontend)
- **Standalone CLI** — no Redis or server required
- FastAPI API for job creation, status polling, export, and cleanup
- Redis-backed queue and transient job state storage
- Isolated Playwright Chromium sessions per job
- Automated interaction discovery and ranked action planning
- MP4 post-processing with `ffmpeg`
- Next.js frontend for submission, progress tracking, and download
- Ephemeral artifact handling with one-hour retention
- Worker scaling through container replication

## Architecture Overview

```text
User -> Frontend -> API -> Redis -> Worker -> Browser -> Video -> User
```

The core recording engine lives in `demoforge/core/` and is shared by all interfaces:

```text
demoforge/core/        Shared engine (browser, discovery, planner, executor, recorder, pipeline)
demoforge/cli.py       CLI entry point
api/                   FastAPI service and HTTP endpoints
worker/                Redis-backed async worker
frontend/              Next.js UI
docker/                Container images and orchestration configs
scripts/               Build and publish scripts
tests/                 Pytest-based test suite
```

## Installation Methods

### 1. Docker — All-in-One (recommended for trying DemoForge)

```bash
docker run -p 8080:8080 heygranth/demoforge
```

This single container bundles Redis, the API, the worker, and the frontend behind nginx on port 8080.

Optional environment variables:

```bash
docker run -p 8080:8080 \
  -e GEMINI_API_KEY=your-key \
  -e MAX_CLICKS=15 \
  heygranth/demoforge
```

### 2. Docker Compose — Multi-Container (recommended for development)

```bash
docker compose up --build -d
cd frontend && npm install && npm run dev
```

The Compose stack runs `redis`, `api`, and `worker` as separate services. The frontend runs on the host at `http://localhost:3000`.

### 3. CLI — Standalone Tool

```bash
pipx install demoforge
demoforge setup
demoforge https://example.com
```

Requires `ffmpeg` installed on the host system:
- Ubuntu/Debian: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: `choco install ffmpeg`

### 4. pip — Editable Development Install

```bash
pip install -e ".[dev]"
demoforge setup
```

## Demo Workflow

1. A user submits a website URL (via UI, API, or CLI).
2. A browser session launches in headless Chromium.
3. The engine discovers interactive elements on the page.
4. An interaction planner ranks and selects safe actions.
5. The executor performs interactions while recording video.
6. The raw recording is converted to MP4 with `ffmpeg`.
7. The user receives the generated video.

## Configuration

| Variable | Service | Default | Purpose |
| --- | --- | --- | --- |
| `REDIS_HOST` | API, worker | `localhost` | Redis hostname |
| `REDIS_PORT` | API, worker | `6379` | Redis port |
| `JOB_TTL` | API | `3600` | Job metadata retention in seconds |
| `POLL_INTERVAL` | worker | `2` | Queue polling interval in seconds |
| `MAX_CLICKS` | worker, CLI | `10` | Maximum interactions per job |
| `MAX_DEPTH` | worker, CLI | `3` | Maximum navigation depth |
| `MAX_RUNTIME` | worker, CLI | `300` | Maximum execution time in seconds |
| `GEMINI_API_KEY` | worker, CLI | unset | Optional Gemini API key for LLM-based interaction ranking |

## Usage Examples

### CLI

```bash
# Basic recording
demoforge https://example.com

# Custom output and viewport
demoforge https://example.com --output walkthrough.mp4 --viewport 1920x1080

# With Gemini for smarter interaction planning
GEMINI_API_KEY=your-key demoforge https://example.com
```

### API

```bash
# Submit a job
curl -X POST http://localhost:8080/api/demo/run \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Check status
curl http://localhost:8080/api/demo/status/<job_id>

# Download video
curl http://localhost:8080/api/demo/export/<job_id> -o demo.mp4
```

### Frontend

1. Open `http://localhost:8080` (Docker) or `http://localhost:3000` (dev).
2. Submit a public website URL.
3. Wait for processing to complete.
4. The video downloads automatically.

## Development

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Node.js 18+ and npm
- ffmpeg

### Setup

```bash
pip install -e ".[dev]"
demoforge setup
```

### Testing

```bash
make test               # run all tests
make test-coverage      # with coverage report
make test-verbose       # verbose output
```

### Building the Docker image

```bash
make build-allinone     # build all-in-one image
make run-allinone       # run it locally
make publish-docker     # push to Docker Hub
```

## Design Principles

- Deterministic execution over exploratory breadth
- Isolated and sandboxed browser sessions
- Shared core engine across all interfaces (CLI, worker, API)
- Stateless API and ephemeral workers
- Temporary artifacts with explicit cleanup semantics
- Clear failure states for queueing, execution, and export paths
- Horizontal scaling through independent workers


## Contributing

See `CONTRIBUTING.md` for development workflow, testing expectations, pull request standards, and security reporting guidance.

## License

A repository license file has not been published yet. Do not assume redistribution or production usage rights until a license is added.
