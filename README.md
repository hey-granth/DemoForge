# DemoForge

Production-grade web application for automated demo video generation.

## Quick Start

```bash
# Set environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY (optional)

# Build and run
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

## API Endpoints

### POST /demo/run
Submit demo job
```bash
curl -X POST http://localhost:8000/demo/run \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### GET /demo/status/{job_id}
Check job status
```bash
curl http://localhost:8000/demo/status/{job_id}
```

### GET /demo/export/{job_id}
Download video (deletes artifacts)
```bash
curl http://localhost:8000/demo/export/{job_id} -o demo.mp4
```

### DELETE /demo/cleanup/{job_id}
Force cleanup
```bash
curl -X DELETE http://localhost:8000/demo/cleanup/{job_id}
```

## System Requirements

- Docker + Docker Compose
- 2GB RAM minimum per worker
- 2 CPU cores recommended

## Configuration

See `.env.example` for all variables.

Key settings:
- `MAX_CLICKS`: Interaction limit (default: 10)
- `MAX_DEPTH`: Navigation depth (default: 3)
- `MAX_RUNTIME`: Timeout in seconds (default: 300)
- `OPENAI_API_KEY`: Optional LLM enhancement

## Architecture

See `ARCHITECTURE.md` for complete system design.

## Limitations

- No authentication support
- No persistent storage
- Single domain per job
- MP4 output only
- 1 hour TTL on artifacts
