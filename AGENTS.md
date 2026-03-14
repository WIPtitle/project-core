# AGENTS.md - Project Core Development Guide

## Project Description

**Project Core** is a self-hosted, multi-platform alarm system with GPIO sensors, IP cameras, motion detection, and push notifications. Deployable on Raspberry Pi or any server running Docker.

## Architecture

Multi-service microservices architecture with Docker Compose:

**Core Services:**
- `frontend` (Next.js 14 + React 18, TypeScript, Tailwind CSS)
- `devices-manager` (FastAPI, Python 3)
- `auth` (FastAPI)
- `local-audio-manager` (FastAPI) - manages MP3 playback
- `notifications-manager` (FastAPI) - ntfy integration
- `database` (PostgreSQL 16.4)
- `ntfy` (push notification broker)
- `nginx` (reverse proxy, SSL)

**External Dependencies:**
- `gpio-monitor` - Raspberry Pi GPIO monitoring (submodule)
- `mp3-player-server` - Remote audio playback (submodule)

## Build & Run Commands

```bash
# Production
docker compose up -d

# Development
./dev-run.sh    # starts GPIO/MP3 locally, then docker compose
./dev-stop.sh   # cleanup
```

## Code Conventions

- **Python**: FastAPI with SQLModel ORM
- **Frontend**: Next.js App Router, TypeScript, Radix UI components
- **Database**: PostgreSQL with SQLModel models
- **Credentials**: Stored in shared volume, consumed via env vars

## Things to Know

1. **Submodules**: GPIO Monitor and MP3 Player are separate repos.
2. **YOLO Integration**: `ultralytics` for person detection on always-recording cameras.
3. **Detection**: Motion via OpenCV frame diff; optional person detection with YOLO.
4. **No .env needed**: All configuration via web UI after first startup.
5. **Always-recording**: Cameras record continuously with hourly rotation; frame buffer shared with motion detection workers.
