# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build

WORKDIR /build
COPY frontend/ .
RUN npm install && npm run build

# Stage 2: Backend + serve frontend
FROM python:3.13-slim

WORKDIR /app

# Install system deps for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (use requirements style to avoid hatchling package discovery)
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir \
    "fastapi>=0.115" "uvicorn[standard]" "sqlalchemy[asyncio]>=2.0" \
    asyncpg alembic pydantic-settings httpx python-multipart isbnlib rapidfuzz \
    ebooklib mutagen

# Copy backend application
COPY backend/app app/
COPY backend/alembic alembic/
COPY backend/alembic.ini .

# Copy frontend build output to serve as static files
COPY --from=frontend-build /build/dist /app/static

# Persistent data directory (settings DB, cover cache)
VOLUME /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
