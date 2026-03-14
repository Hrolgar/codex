# Codex

Self-hosted book and audiobook library manager. Knows your library, prevents duplicates, tracks series.

## Features

- **Library indexing** — Audiobookshelf, filesystem scanning, Calibre import
- **Duplicate detection** — fuzzy matching by title, author, and ISBN
- **Series tracking** — automatic series detection and ordering
- **Source search** — search multiple sources with ownership badges so you know what you already have
- **Wishlist** — track books you want to read or listen to

## Quick Start

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD and point BOOKS_DIR to your library
docker compose up -d
```

Open [http://localhost:8000](http://localhost:8000).

## Tech Stack

| Layer    | Technology                   |
|----------|------------------------------|
| Frontend | React, TypeScript, Vite      |
| Backend  | FastAPI, SQLAlchemy 2, async |
| Database | PostgreSQL 16                |
| Search   | Prowlarr (optional)          |

## Development Setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,scanners]"
alembic upgrade head
uvicorn app:create_app --factory --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Screenshots

<!-- TODO: Add screenshots -->
