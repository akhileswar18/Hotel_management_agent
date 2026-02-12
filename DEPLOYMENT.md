# HMS Deployment Guide

Complete guide to deploying the Hotel Management System. Three methods available depending on your environment.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Method 1: Python (Development)](#method-1-python-development)
3. [Method 2: Windows Executable](#method-2-windows-executable)
4. [Method 3: Docker](#method-3-docker)
5. [Configuration](#configuration)
6. [Database Management](#database-management)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

| Method | Best For | Command |
|---|---|---|
| **Python** | Developers, testing | `python -m src` + `python -m src.ui.app` |
| **Windows .exe** | End users, deployment | `.\dist\HMS.exe` |
| **Docker** | Servers, cloud | `docker compose up` |

---

## Method 1: Python (Development)

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)
- Git (for cloning)

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/Hotel_management_agent.git
cd Hotel_management_agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Windows (cmd):
venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Install dev dependencies for testing
pip install -r requirements-dev.txt
```

### Run

The app has two components that run separately:

```bash
# Terminal 1: Start the API server
python -m src
# → API running at http://127.0.0.1:8000

# Terminal 2: Start the Flet UI
python -m src.ui.app
# → UI opens at http://127.0.0.1:8080
```

Or use the unified launcher:

```bash
python -m src.launcher
# → Starts both API (port 8000) and UI (port 8080)
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src --cov-report=html

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v
```

### Default Credentials

| Username | PIN | Role |
|---|---|---|
| manager | 1234 | MANAGER |
| waiter1 | 1111 | WAITER |
| cashier1 | 2222 | CASHIER |
| clerk1 | 3333 | CLERK |

> Run `python scripts/seed_data.py` to create these users and sample products.

---

## Method 2: Windows Executable

### Prerequisites
- Windows 10 or Windows 11
- No Python installation required (everything is bundled)

### Build the Executable

If building from source:

```powershell
# Activate virtual environment
venv\Scripts\Activate.ps1

# Install PyInstaller
pip install pyinstaller

# Build using the provided script
.\scripts\build_exe.ps1

# Or build manually
pyinstaller hms.spec --noconfirm
```

Output: `dist\HMS.exe` (~80-150 MB)

### Run

```powershell
# Double-click or run from terminal:
.\dist\HMS.exe
```

The executable:
1. Initializes the SQLite database (creates `hms.db` in the current directory)
2. Starts the FastAPI backend on port 8000
3. Starts the Flet UI on port 8080 (opens in default browser)

### Distribution

To distribute to end users:
1. Copy `dist\HMS.exe` to the target machine
2. (Optional) Create a desktop shortcut
3. Run — the database will be created automatically on first launch

### Notes
- The database file (`hms.db`) is created in the same directory as the executable
- Logs are written to a `logs/` folder in the same directory
- To reset the database, delete `hms.db` and restart

---

## Method 3: Docker

### Prerequisites
- Docker Engine 20.10+
- Docker Compose v2+

### Quick Start

```bash
# Build and start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

### Access Points

| Service | URL | Description |
|---|---|---|
| API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger documentation |
| UI | http://localhost:8080 | Flet web interface |

### Custom Ports

```bash
# Use custom ports
API_PORT=9000 UI_PORT=9080 docker compose up -d
```

### Data Persistence

Data is stored in Docker named volumes:

| Volume | Purpose | Path in Container |
|---|---|---|
| `hms-data` | SQLite database | `/app/data/hms.db` |
| `hms-logs` | Application logs | `/app/logs/` |

```bash
# List volumes
docker volume ls | grep hms

# Backup database
docker cp hms-api:/app/data/hms.db ./backup_hms.db

# Restore database
docker cp ./backup_hms.db hms-api:/app/data/hms.db
docker compose restart
```

### Single Container Mode

If you prefer running both API and UI in a single container:

```bash
# Build the image
docker build -t hms:latest .

# Run with both services
docker run -d \
  --name hms \
  -p 8000:8000 \
  -p 8080:8080 \
  -v hms-data:/app/data \
  hms:latest
```

### Environment Variables

Override defaults in `docker-compose.yml` or via `.env`:

```bash
# Create .env file for Docker Compose
cp .env.example .env

# Edit as needed
DATABASE_URL=sqlite:///./data/hms.db
LOG_LEVEL=INFO
API_PORT=8000
UI_PORT=8080
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./hms.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_DIR` | `./logs` | Directory for log files |
| `API_HOST` | `127.0.0.1` | API server bind address |
| `API_PORT` | `8000` | API server port |
| `PRINTER_ENABLED` | `false` | Enable thermal printer (Phase 2+) |
| `OFFLINE_MODE` | `true` | Offline-first mode (always true for v1.0) |
| `TAX_RATE` | `0.18` | Tax rate (18% default) |
| `CURRENCY` | `INR` | Currency code |

### Setting Environment Variables

**Python / Windows:**
```powershell
# Create .env file from template
Copy-Item .env.example .env

# Edit .env to customize
notepad .env
```

**Docker:**
```bash
# Via docker-compose.yml environment section
# Or via .env file in the project root
```

---

## Database Management

### Location

| Method | Database Path |
|---|---|
| Python | `./hms.db` (project root) |
| Windows .exe | Same directory as `HMS.exe` |
| Docker | `/app/data/hms.db` (inside volume `hms-data`) |

### Backup

```bash
# Python / Windows — just copy the file
cp hms.db hms_backup_$(date +%Y%m%d).db

# Docker
docker cp hms-api:/app/data/hms.db ./hms_backup.db
```

### Reset Database

```bash
# Delete the database file and restart
# Python:
rm hms.db hms.db-shm hms.db-wal
python -m src

# Docker:
docker compose down
docker volume rm hotel_management_agent_hms-data
docker compose up -d
```

### Migrations

Migrations run automatically on startup. To run manually:

```bash
python -m migrations.runner apply
python -m migrations.runner status
```

---

## Troubleshooting

### Port Already in Use

```powershell
# Windows — find process using port 8000
netstat -ano | Select-String ":8000.*LISTENING"
# Kill it
taskkill /PID <pid> /T /F
```

```bash
# Linux/macOS
lsof -i :8000
kill -9 <pid>
```

### Database Locked

```bash
# Remove WAL files and restart
rm hms.db-shm hms.db-wal
# Then restart the application
```

### Docker Build Fails

```bash
# Clean rebuild
docker compose build --no-cache
docker compose up -d
```

### PyInstaller Build Fails

```powershell
# Clean and rebuild
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
.\scripts\build_exe.ps1 -Clean
```

### Tests Failing After Update

```bash
# Reset test environment
rm -f test_*.db
pytest tests/ -v --tb=long
```

### Cannot Connect to API from UI

1. Verify API is running: `curl http://localhost:8000/health`
2. Check if ports match between API and UI configuration
3. For Docker: ensure `hms-ui` depends on `hms-api` (already configured)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   Flet UI (:8080)                │
│  ┌──────┐  ┌──────────┐  ┌────────┐  ┌───────┐ │
│  │ Auth │  │   POS    │  │Products│  │Reports│ │
│  └──┬───┘  └────┬─────┘  └───┬────┘  └───┬───┘ │
│     └───────────┴────────────┴────────────┘     │
│                      │ HTTP                      │
├─────────────────────────────────────────────────┤
│              FastAPI Backend (:8000)              │
│  ┌──────────────────────────────────────────┐   │
│  │          Application Services            │   │
│  │  Auth │ Sales │ Inventory │ Reporting    │   │
│  └──────────────────┬───────────────────────┘   │
│                     │                            │
│  ┌──────────────────┴───────────────────────┐   │
│  │            SQLite Database                │   │
│  │  Orders │ Items │ Users │ Stock Ledger    │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## Support

- **README**: [README.md](README.md) — Quick start and overview
- **Release Notes**: [RELEASE_NOTES_v1.0.md](RELEASE_NOTES_v1.0.md) — Features and known issues
- **API Docs**: http://localhost:8000/docs (when running)
- **Tests**: `pytest tests/ -v` — Verify everything works
