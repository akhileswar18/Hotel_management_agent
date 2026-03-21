# Hotel_management_agent Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-10

## Active Technologies
- Python 3.11+ + Flet 0.80.5, FastAPI, httpx (synchronous), pydantic (001-stabilize-hma-openrouter)
- Existing SQLite database (`hms.db`), no schema changes (001-stabilize-hma-openrouter)
- Python 3.11+ + Flet 0.80.5, FastAPI, httpx (synchronous only), pydantic (001-stabilize-hma-openrouter)
- Python 3.11+ + Flet 0.80.5, FastAPI, httpx (synchronous), pydantic, SQLite (001-stabilize-hma-openrouter)
- Existing SQLite database (`C:\Users\akhil\Hotel_management_agent\hms.db`), no schema changes (001-stabilize-hma-openrouter)

- Python 3.11+ + Flet 0.80.5, FastAPI, httpx, pydantic, existing standard-library threading/timer utilities (001-modernize-hms-ui)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 001-stabilize-hma-openrouter: Added Python 3.11+ + Flet 0.80.5, FastAPI, httpx (synchronous), pydantic, SQLite
- 001-stabilize-hma-openrouter: Added Python 3.11+ + Flet 0.80.5, FastAPI, httpx (synchronous), pydantic, SQLite
- 001-stabilize-hma-openrouter: Added Python 3.11+ + Flet 0.80.5, FastAPI, httpx (synchronous only), pydantic


<!-- MANUAL ADDITIONS START -->
## Workflow Rules

- Whenever a code fix is made, update relevant troubleshooting/knowledge notes in `SKILLS.md` in the same task.
- Keep each `SKILLS.md` update concise: include error, root cause, fix, files touched, and prevention note.
<!-- MANUAL ADDITIONS END -->
