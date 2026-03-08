# Contributing to DemoForge

## Introduction

Thank you for contributing to DemoForge.

This project accepts improvements to the API, worker pipeline, browser automation, frontend, tests, and documentation. Contributions should be small in scope, technically justified, and consistent with the system's core goals: deterministic execution, isolation, and operational simplicity.

## Code of Conduct Reference

This repository does not currently publish a standalone `CODE_OF_CONDUCT.md`.

Until one is added, all contributors are expected to participate professionally and respectfully. Harassment, abusive behavior, and bad-faith collaboration are not acceptable in issues, pull requests, code review, or project discussions.

## Development Environment Setup

### Prerequisites

- Docker and Docker Compose
- Node.js and npm
- Python tooling if you plan to run services directly outside containers

### Recommended setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Start the backend stack:
   ```bash
   docker compose up --build -d
   ```
3. Start the frontend in development mode:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. Verify the API is healthy:
   ```bash
   curl http://localhost:8000/health
   ```

### Local service development

Docker is the reference environment for Redis, Playwright, and `ffmpeg` compatibility.

If you need to run services directly on your host machine:
- install API dependencies from `api/requirements.txt`
- install worker dependencies from `worker/requirements.txt`
- install test dependencies from `tests/requirements.txt`
- install Playwright Chromium
- ensure `ffmpeg` is available on `PATH`

## Project Architecture Overview

DemoForge is composed of four runtime services:

- `frontend/`: Next.js interface for URL submission, status polling, and download
- `api/`: FastAPI service that validates requests, creates jobs, reports status, and streams MP4 exports
- `worker/`: async job consumer that launches Playwright, explores interactions, records the session, and converts video to MP4
- Redis: queue and transient state store for jobs and video artifacts

Important implementation boundaries:
- The API is stateless and should remain lightweight.
- Workers own browser execution and media processing.
- Job and artifact data are temporary by design.
- Browser sessions must remain isolated and bounded by execution limits.

## Branching Strategy

- Branch from the main development branch for all changes.
- Use short-lived topic branches.
- Prefer descriptive names such as `feat/worker-timeout-guard`, `fix/api-export-cleanup`, or `docs/readme-refresh`.
- Rebase or merge the latest main branch before opening a pull request if your branch has drifted.

## Pull Request Guidelines

Submit pull requests that are focused, reviewable, and complete.

Include:
- a clear summary of the change
- the problem being solved
- any relevant issue references
- test coverage or verification steps
- screenshots or recordings for frontend changes when helpful

Before opening a pull request:
- remove unrelated edits
- update documentation when behavior or configuration changes
- keep public interfaces and file structure stable unless the change requires otherwise
- ensure new dependencies are necessary and justified

PRs may be asked to split if they combine unrelated refactors, behavior changes, and documentation updates.

## Code Style Guidelines

### General

- Preserve the existing repository structure and naming conventions.
- Prefer explicit, readable code over clever abstractions.
- Keep functions and modules narrowly scoped.
- Avoid drive-by refactors in unrelated areas.

### Python

- Follow existing async patterns in the API and worker services.
- Keep Redis, Playwright, and filesystem error handling explicit.
- Preserve deterministic behavior and safety guards in interaction planning and execution.
- Use type hints where the surrounding module already relies on them.

### Frontend

- Follow existing Next.js and TypeScript conventions in `frontend/src/`.
- Keep UI state transitions explicit and predictable.
- Treat API errors as user-facing states, not silent failures.

### Formatting and linting

- Run repository tests before submitting.
- Run frontend linting when you touch frontend code:
  ```bash
  cd frontend
  npm run lint
  ```

## Testing Expectations

All behavioral changes should include or update tests.

### Python tests

Use the existing test suite in `tests/`:

```bash
make test
```

Additional useful commands:

```bash
make test-coverage
pytest tests/ -vv
```

### Frontend verification

When modifying frontend code, run:

```bash
cd frontend
npm run lint
npm run build
```

### Test quality expectations

- Add tests for the happy path and at least one failure or boundary case.
- Prefer deterministic unit tests over brittle end-to-end flows.
- Do not rely on external websites in automated tests unless the test is explicitly marked and isolated.
- Document any required manual verification for browser or media-processing changes.

## Issue Reporting Guidelines

Use issues for reproducible bugs, feature proposals, and documentation gaps.

A good issue report includes:
- a concise description of the problem
- steps to reproduce
- expected behavior
- actual behavior
- logs or trace output where relevant
- environment details such as OS, Docker version, Python version, Node version, and browser/runtime context

For feature requests, describe the operational need, the expected behavior, and any constraints around determinism, safety, or scalability.

## Security Disclosure Policy

Do not report security vulnerabilities in public issues.

If repository private reporting is available, use the platform's security reporting workflow. Otherwise, contact the maintainers directly and share only the minimum information required to reproduce and assess the issue.

Security reports should include:
- affected component or endpoint
- impact assessment
- reproduction steps
- any required configuration or environment details
- suggested mitigations, if known

Please avoid publishing proof-of-concept exploits or sensitive details until maintainers have had a reasonable opportunity to investigate and respond.

