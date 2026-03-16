# Codex Comprehensive Code Review
**Date:** 2026-03-16
**Reviewer:** hrolbot-reviewer (agent)
**Scope:** Full codebase — backend (FastAPI + SQLAlchemy) and frontend (React + TypeScript)

---

## Verdict: **Request Changes**

The codebase is well-structured and shows good engineering intent (SSRF protection, path traversal guards, task GC prevention). However, there are several critical security and correctness issues that must be fixed before production deployment. Most importantly: **there is no authentication on any endpoint**, combined with a wildcard CORS + credentials setting, creating a fully open API.

---

## CRITICAL

### C1 — CORS wildcard + `allow_credentials=True` is unsafe
**File:** `backend/app/main.py:165–171`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    ...
)
```

Using `allow_origins=["*"]` with `allow_credentials=True` violates the CORS spec (browsers will reject it) and signals intent to allow credentialed requests from any origin. In practice browsers reject this combination, but it's a misconfiguration that should be corrected regardless. If credentials are needed, enumerate specific allowed origins. If this app has no auth (see C3), drop `allow_credentials=True` entirely.

**Fix:** Either restrict `allow_origins` to specific known origins, or remove `allow_credentials=True`.

---

### C2 — SQL injection in `_add_column_if_missing` via `default` parameter
**File:** `backend/app/main.py:41–42`

```python
default_clause = f" DEFAULT {default}" if default else ""
await conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}'))
```

`default` is interpolated directly into a raw SQL string without parameterization. The callers pass string literals (e.g., `"'idle'"`, `"'false'"`), so this is low exploitability in the current code — but the pattern is inherently dangerous. The `col_type` argument also bypasses parameterization (it's validated via `_validate_identifier` only on the base type before `(`). `DEFAULT` values cannot be parameterized in DDL, but they should be validated against an allowlist of expected SQL literal values.

**Fix:** Validate `default` against an explicit allowlist of safe DDL literals, or restructure to avoid runtime DDL altogether (Alembic handles this properly).

---

### C3 — No authentication on any endpoint
**File:** All API routes (`backend/app/api/`)

No authentication middleware exists. Every endpoint is publicly accessible to anyone who can reach port 8000. This means an attacker can:
- Browse the server filesystem via `GET /api/root-folders/browse`
- Read all stored settings (including Prowlarr/Hardcover API keys) via `GET /api/system/settings`
- Delete all books/authors via `DELETE` endpoints
- Trigger file downloads to arbitrary URLs via `POST /api/downloads`
- Import from arbitrary Audiobookshelf URLs (SSRF, see C5)
- Clear all data via `POST /api/dev/clear` if `CODEX_DEV_MODE=true`

For a self-hosted tool (like Radarr/Sonarr), basic API key authentication is standard. Even a single static token checked on every request would dramatically reduce exposure.

**Fix:** Add an API key header check middleware, or at minimum document that this tool must be placed behind a reverse proxy with auth (e.g., Authelia, nginx basic auth).

---

### C4 — Wrong asyncio task stored for download cancellation
**File:** `backend/app/services/download_service.py:614–615`

```python
task = asyncio.current_task()   # This is process_download_queue's task
_active_tasks[dl.id] = task
```

`asyncio.current_task()` inside `process_download_queue` returns the queue loop task itself, not a task for the individual download. `_process_single` is called directly (not spawned as a new task), so there IS no separate task to cancel. When `cancel()` is called:

```python
task = _active_tasks.get(download_id)
if task and not task.done():
    task.cancel()   # Cancels the ENTIRE queue processor
```

This kills the queue processor on the first cancellation, stopping all future downloads. The actual in-progress HTTP stream (`httpx.AsyncClient`) is not cancelled.

**Fix:** Either spawn `_process_single` as a separate `asyncio.create_task()` and store that reference, or implement cancellation via a per-download `asyncio.Event` / `CancelledError` propagation.

---

### C5 — SSRF in Audiobookshelf import endpoint
**File:** `backend/app/api/importexport.py:206–213`

```python
parsed = urlparse(body.url)
if parsed.scheme not in ("http", "https"):
    raise HTTPException(...)
# No further SSRF check
async with httpx.AsyncClient(timeout=30) as client:
    resp = await client.get(f"{base}/api/libraries", headers=headers)
```

Only the URL scheme is validated. An attacker can supply `http://169.254.169.254/latest/meta-data/` (AWS metadata), `http://localhost:8000/api/dev/clear`, or any internal service URL. The `validate_download_url()` SSRF guard exists in the codebase but is not called here.

**Fix:** Apply `validate_download_url()` (or extract a similar SSRF check) to the Audiobookshelf URL before making requests.

---

### C6 — SSRF bypass in auto-download service
**File:** `backend/app/services/auto_download_service.py:72–76`

```python
await dl_svc.enqueue(
    source_url=best.download_url,   # From Prowlarr search results — unvalidated
    source_type=best.source or "prowlarr",
    book_id=item.book_id,
)
```

`validate_download_url()` is called in the downloads API endpoint (`downloads.py:25`) but NOT in `auto_download_service`. A malicious Prowlarr indexer could return `downloadUrl` values pointing at internal services. The auto-download path bypasses the SSRF guard entirely.

**Fix:** Call `validate_download_url(best.download_url)` before enqueuing in `check_wishlist_for_downloads`.

---

## HIGH

### H1 — SSRF protection bypassed by DNS rebinding
**File:** `backend/app/services/download_service.py:46–62`

`validate_download_url` resolves the hostname at validation time and checks the IP against blocked networks. The actual HTTP request is made seconds later by `httpx`. An attacker using DNS rebinding can have the hostname resolve to a public IP at validation time, then return a private IP when `httpx` opens the TCP connection.

**Fix:** Use `httpx` with a custom transport that performs IP-level SSRF checks at connection time (e.g., intercept `connect()` and validate the resolved IP), or use a library like `ssrf-filter`. Alternatively, run downloads in a network namespace that cannot reach internal services.

---

### H2 — Blocking synchronous I/O inside async context (download writes)
**File:** `backend/app/services/download_service.py:505–515`

```python
with open(temp_path, "wb") as f:
    async for chunk in resp.aiter_bytes(chunk_size=65536):
        f.write(chunk)   # Synchronous file write — blocks event loop
```

`f.write(chunk)` blocks the event loop for the duration of each disk write. For large downloads (hundreds of MB) on slow storage, this stalls all other async operations.

**Fix:** Use `aiofiles` for async writes:
```python
import aiofiles
async with aiofiles.open(temp_path, "wb") as f:
    async for chunk in resp.aiter_bytes(chunk_size=65536):
        await f.write(chunk)
```

---

### H3 — Blocking `os.walk` in async scanner
**File:** `backend/app/scanners/filesystem.py:28`

```python
for dirpath, _, filenames in os.walk(root):
```

`os.walk` is a synchronous, blocking call. For large libraries (tens of thousands of files), this blocks the entire asyncio event loop for seconds. The scanner is called from `run_scan` which is itself launched as a background task, but it still holds the event loop during the walk.

**Fix:** Wrap in `await asyncio.to_thread(list, os.walk(root))` or use `anyio.to_thread.run_sync` to offload to a thread pool. Similarly, `f.stat().st_size` calls in `_build_audiobook_item` and `_build_single_file_item` are synchronous.

---

### H4 — Race condition: scan status check is not atomic
**File:** `backend/app/services/scanner_service.py:30–37`

```python
if root_folder.scan_status == "scanning":
    logger.warning("... already being scanned, skipping")
    return
root_folder.scan_status = "scanning"
await db.commit()
```

Between the read and the write, another concurrent task (e.g., from `trigger_scan_all`) could also read "idle" and proceed. Both scans would run simultaneously, creating duplicate `LibraryItem` and `Book` records.

**Fix:** Use an atomic compare-and-update:
```sql
UPDATE root_folders SET scan_status = 'scanning'
WHERE id = :id AND scan_status != 'scanning'
RETURNING id
```
If the RETURNING result is empty, the scan is already in progress — abort.

---

### H5 — Path traversal in SPA fallback
**File:** `backend/app/main.py:194–200`

```python
@app.get("/{full_path:path}")
async def spa_fallback(request: Request, full_path: str):
    file_path = STATIC_DIR / full_path
    if file_path.is_file():
        return FileResponse(file_path)
```

`STATIC_DIR / full_path` with `pathlib` does NOT normalize `..` components. A request to `/%2e%2e/%2e%2e/etc/passwd` (double URL-encoded) or similar could resolve to a path outside `STATIC_DIR`, and `FileResponse` would serve it. While HTTP clients typically normalize `../` sequences before sending, this is still a defence-in-depth failure.

**Fix:** After computing `file_path`, verify it resolves within `STATIC_DIR`:
```python
try:
    file_path.resolve().relative_to(STATIC_DIR.resolve())
except ValueError:
    return FileResponse(STATIC_DIR / "index.html")
```

---

### H6 — No input validation on setting values
**File:** `backend/app/services/settings_service.py:205–215`

`set_setting` validates only that the key is in the schema, but accepts any string value. For numeric settings like `auto_download.interval_hours`, a value of `"0"` results in `max(0, 0.5) = 0.5` (handled), but `"-999999"` would work. More critically, URL settings like `prowlarr.url` or `downloadclient.qbittorrent.url` accept any value and those values are later used for HTTP requests. An authenticated attacker could set these to SSRF targets.

**Fix:** Add per-key validators to `SETTINGS_SCHEMA` (e.g., regex patterns, type checks, URL validation). At minimum, validate URL settings against the same SSRF guard.

---

### H7 — "In-flight" downloads stuck in `downloading` state after restart
**File:** `backend/app/services/download_service.py:605–624`

When the server restarts, downloads that were `downloading` stay in that state and are never retried (the queue processor only picks up `pending` downloads). Users see a perpetually "downloading" entry with no way to retry it (retry only works on `error` status).

**Fix:** On application startup in `lifespan`, reset all `downloading` downloads back to `pending`:
```python
await conn.execute(
    text("UPDATE downloads SET status='pending', progress=0 WHERE status='downloading'")
)
```

---

## MEDIUM

### M1 — N+1 API calls during OpenLibrary author catalog refresh
**File:** `backend/app/services/catalog_service.py:510–513`

For each of an author's works (up to 500), a separate `GET /works/{id}/editions.json` API call is made:
```python
editions_data = await _ol_get(client, f"/works/{work_key_short}/editions.json", ...)
```

For a prolific author with 200 works, this is 201 HTTP requests (1 for works + 200 for editions). This is slow, hammers the OpenLibrary API, and makes the rate limiter ineffective at preventing long catalog refreshes.

**Fix:** Only fetch editions when actually needed (language filtering or ISBN extraction). Consider batching work metadata requests or using the OpenLibrary search API which returns more data in one call. Apply the title-language heuristic filter _before_ fetching editions to skip obviously excluded works.

---

### M2 — N+1 database queries during filesystem scan
**File:** `backend/app/services/scanner_service.py:82–180`

For each scanned file, `_process_item` issues ~7 separate DB queries: check existing LibraryItem, check duplicate, get-or-create Author, check BookAuthor link, get-or-create Series, check SeriesBook link, create LibraryItem. For a 10,000-file library, that's ~70,000 queries per scan.

**Fix:** Batch the deduplication lookups. Pre-load existing authors and series into in-memory dicts keyed by name at the start of the scan. Use `INSERT ... ON CONFLICT DO NOTHING` for idempotent upserts.

---

### M3 — API keys and credentials stored in plaintext in the database
**File:** `backend/app/services/settings_service.py`

All secrets (Prowlarr API key, Hardcover API key, qBittorrent password, SABnzbd API key) are stored as plaintext strings in the `app_settings` table. Anyone with DB access can extract all credentials.

**Fix:** Encrypt secrets at rest using a key derived from a server-side secret (e.g., `CODEX_SECRET_KEY` env var). Mark `is_secret=True` entries for encrypted storage. Libraries like `cryptography` (Fernet) make this straightforward.

---

### M4 — Schema migrations bypass Alembic (dual-migration system)
**File:** `backend/app/main.py:46–54`

`lifespan` calls `_add_column_if_missing` to add columns that also have Alembic migrations (`002_add_hardcover_slug.py`, etc.). The same schema change exists in two places. If the Alembic version is ahead of the ad-hoc checks, the checks are harmless but confusing. If the Alembic migration is never run, only the ad-hoc check applies. This creates maintenance confusion about the authoritative schema source.

**Fix:** Remove the ad-hoc `_add_column_if_missing` calls and rely exclusively on Alembic. Run `alembic upgrade head` as part of the container entrypoint (it's idempotent).

---

### M5 — `delete_book` associations deleted without transaction isolation
**File:** `backend/app/api/books.py:305–326`

Multiple `DELETE` statements are issued sequentially without being wrapped in a single database transaction. If the process crashes between the `DELETE BookAuthor` and `DELETE SeriesBook` statements, the book is left in a partially deleted state with dangling cross-references.

SQLAlchemy's session is already transactional (all work is flushed atomically on `commit`), but the separate `db.execute(delete(...))` calls within the same session are collected in the same transaction until `await db.commit()`. This is actually safe in this case — but it's not obvious from reading the code, and adding an explicit `async with db.begin():` block would make the intent clear and guard against future refactoring mistakes.

**Fix:** Add an explicit transaction block or a comment explaining that SQLAlchemy sessions are transactional by default.

---

### M6 — Calibre import opens SQLite connection to user-supplied path
**File:** `backend/app/api/importexport.py:90`

```python
conn = sqlite3.connect(str(db_path))
```

While there is a root-folder path check, the check is done _after_ resolving symlinks on the library path but before checking if `db_path` itself is safe. An attacker who can create a symlink inside a root folder pointing to an arbitrary SQLite file could cause the application to open and query it. The SQLite3 library has had vulnerabilities, and opening a maliciously crafted SQLite file could be exploitable.

**Fix:** After resolving `db_path`, ensure it still resolves within the allowed roots. Also open the connection in read-only mode: `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`.

---

### M7 — Unbounded `get_downloads` response
**File:** `backend/app/services/download_service.py:140–146`

```python
stmt = select(Download).order_by(Download.created_at.desc())
# No LIMIT
```

All downloads are returned without pagination. Over time with many completed downloads, this response could become very large.

**Fix:** Add pagination parameters (`limit` / `offset`) or a default limit (e.g., 200 most recent).

---

### M8 — `hardcover_slug` field missing from `BookResponse` schema / API contract
**File:** `backend/app/services/library_service.py:38–60`, `backend/app/api/client.ts:103–125`

`BookDetail` in the frontend includes `hardcover_slug: string | null`, and `library_service.py`'s `get_book` constructs a dict that doesn't include `hardcover_slug`. The `BookResponse` Pydantic model would need to be checked to see if this silently returns `null` or raises a validation error at runtime.

**Fix:** Audit the `BookResponse` schema against the data dict built in `get_book` to ensure all fields are present.

---

### M9 — Download queue processor `_active_tasks` keyed on wrong task (correlated with C4)
**File:** `backend/app/services/download_service.py:614`

Even if C4 is fixed (storing a per-download task), `_active_tasks` is a module-level dict that is never cleaned up on server restart. After a restart, stale IDs could collide with new download UUIDs (unlikely with UUID4 but architecturally risky).

**Fix:** Clear `_active_tasks` on startup and always use `task.add_done_callback` to remove entries.

---

## LOW

### L1 — Default database password is `codex` / `changeme`
**File:** `backend/app/config.py:9`, `docker-compose.yml:6`

The default `DATABASE_URL` uses `codex:codex` as credentials. The `docker-compose.yml` uses `POSTGRES_PASSWORD:-changeme`. Both are trivially guessable.

**Fix:** Generate a random password at first run, or require users to set `POSTGRES_PASSWORD` with no default.

---

### L2 — Dev endpoints exported from frontend API client
**File:** `frontend/src/api/client.ts:353–358`

`seedDemoData()` and `clearDemoData()` are exported. The backend gates these on `CODEX_DEV_MODE=true`, but production builds still include the function calls, and any UI component using them could trigger them if `CODEX_DEV_MODE` is accidentally enabled.

**Fix:** Either gate the export with a build-time environment variable, or simply document that `CODEX_DEV_MODE=true` must never be set in production.

---

### L3 — Frontend `RootFolder` interface has non-nullable disk space fields
**File:** `frontend/src/api/client.ts:437–449`

```typescript
export interface RootFolder {
  free_space: number;   // non-nullable
  total_space: number;  // non-nullable
}
```

But the backend returns `free_space: int | None` / `total_space: int | None`. When the folder path doesn't exist, both are `null`. TypeScript won't catch null-access errors in code that uses `rootFolder.free_space` directly.

**Fix:** Change to `free_space: number | null` and `total_space: number | null`, then add null checks in the components that display disk usage.

---

### L4 — Error response body discarded in API client
**File:** `frontend/src/api/client.ts:8–10`

```typescript
throw new Error(`API error: ${res.status} ${res.statusText}`);
```

The response body (which contains FastAPI's `{"detail": "..."}` error message) is discarded. Users see generic "API error: 422 Unprocessable Entity" messages rather than the actual validation error.

**Fix:** Parse the response body and include `detail` in the thrown error:
```typescript
const body = await res.json().catch(() => ({}));
throw new Error(body.detail || `API error: ${res.status} ${res.statusText}`);
```

---

### L5 — Variable name `l` shadows Python built-in and is a readability issue
**File:** `backend/app/services/catalog_service.py:373, 616`

```python
languages = [l.strip() for l in (languages_raw or 'en').split(',') if l.strip()]
```

`l` is a confusing variable name (looks like `1` in many fonts) and also shadows the Python 2 built-in. Rename to `lang` or `code`.

---

### L6 — `_validate_root_folder_path` is an empty stub
**File:** `backend/app/api/root_folders.py:25–27`

```python
def _validate_root_folder_path(path: str) -> None:
    """Validate that a root folder path is absolute and exists."""
    pass  # Path existence is checked separately in the create endpoint
```

This function does nothing. The validation comment says it validates that the path is absolute and exists, but that logic was moved elsewhere. The stub creates false confidence and should be removed or populated.

---

### L7 — `get_book` in `LibraryService` issues 4 separate queries (minor N+1)
**File:** `backend/app/services/library_service.py:31–60`

```python
book = await self.db.get(Book, book_id)
authors = await self._get_book_authors(book_id)
series = await self._get_book_series(book_id)
library_items = await self._get_book_library_items(book_id)
```

4 sequential queries for a single book detail page. These could be combined into a single query with JOINs, or at minimum run as concurrent coroutines with `asyncio.gather`.

---

### L8 — WebSocket manager doesn't handle `connect` after close
**File:** `backend/app/ws/manager.py:18–22`

```python
if len(self._connections) >= MAX_CONNECTIONS:
    await websocket.close(code=1013, reason="Too many connections")
    return   # websocket not accepted — ws_downloads will still try receive_text()
```

If `connect` returns early (without accepting), the caller in `ws_downloads` continues to call `websocket.receive_text()` on an unaccepted websocket, which will raise an exception. The `WebSocketDisconnect` handler in `ws_downloads` catches this, but the error is swallowed silently and no feedback is given to the caller.

**Fix:** Have `connect` return a bool indicating success, and check it in `ws_downloads`.

---

## Summary Table

| ID  | Severity | Area            | File                              | Issue                                           |
|-----|----------|-----------------|-----------------------------------|-------------------------------------------------|
| C1  | CRITICAL | Security        | main.py:165                       | CORS wildcard + credentials                     |
| C2  | CRITICAL | Security        | main.py:41                        | SQL injection in DDL default clause             |
| C3  | CRITICAL | Security        | All API routes                    | No authentication on any endpoint               |
| C4  | CRITICAL | Asyncio         | download_service.py:614           | Wrong task stored for cancellation              |
| C5  | CRITICAL | Security        | importexport.py:213               | SSRF in Audiobookshelf import                   |
| C6  | CRITICAL | Security        | auto_download_service.py:72       | SSRF bypass in auto-download                    |
| H1  | HIGH     | Security        | download_service.py:46            | DNS rebinding bypasses SSRF check               |
| H2  | HIGH     | Asyncio/Perf    | download_service.py:505           | Blocking file write in async context            |
| H3  | HIGH     | Asyncio/Perf    | filesystem.py:28                  | Blocking os.walk in async scanner               |
| H4  | HIGH     | Data Integrity  | scanner_service.py:30             | Non-atomic scan status check (race condition)   |
| H5  | HIGH     | Security        | main.py:197                       | Path traversal in SPA fallback                  |
| H6  | HIGH     | Security        | settings_service.py:205           | No validation on setting values                 |
| H7  | HIGH     | Correctness     | download_service.py:605           | In-flight downloads stuck after restart         |
| M1  | MEDIUM   | Performance     | catalog_service.py:510            | N+1 API calls (500 requests per author)         |
| M2  | MEDIUM   | Performance     | scanner_service.py:82             | N+1 DB queries during filesystem scan           |
| M3  | MEDIUM   | Security        | settings_service.py               | Secrets stored in plaintext                     |
| M4  | MEDIUM   | Architecture    | main.py:46                        | Dual migration system (Alembic + ad-hoc)        |
| M5  | MEDIUM   | Data Integrity  | books.py:305                      | Multi-statement delete without explicit txn     |
| M6  | MEDIUM   | Security        | importexport.py:90                | SQLite opened from user-supplied path           |
| M7  | MEDIUM   | Performance     | download_service.py:140           | Unbounded downloads list (no pagination)        |
| M8  | MEDIUM   | Correctness     | library_service.py + client.ts    | hardcover_slug missing from API response dict   |
| M9  | MEDIUM   | Asyncio         | download_service.py:614           | Stale _active_tasks entries after restart       |
| L1  | LOW      | Security        | config.py:9, docker-compose.yml   | Default weak credentials                        |
| L2  | LOW      | Frontend        | client.ts:353                     | Dev endpoints exposed in production client      |
| L3  | LOW      | Frontend        | client.ts:437                     | Non-nullable disk space fields (type mismatch)  |
| L4  | LOW      | Frontend        | client.ts:8                       | Error response body discarded                   |
| L5  | LOW      | Style           | catalog_service.py:373            | Variable name `l` (readability)                 |
| L6  | LOW      | Correctness     | root_folders.py:25                | Empty validation stub                           |
| L7  | LOW      | Performance     | library_service.py:31             | 4 sequential queries for one book detail        |
| L8  | LOW      | Correctness     | ws/manager.py:18                  | WebSocket manager doesn't signal connect failure|

---

## What's Done Well

- **SSRF protection exists** — `validate_download_url` with IP blocking is a solid SSRF guard for direct downloads (just needs to be applied consistently).
- **Path traversal in rename is checked** — `_rename_to_template` validates the new path stays within the root folder (`relative_to(root_path)`).
- **`_validate_identifier` for DDL** — table/column names are validated against a regex before being interpolated into SQL.
- **GC prevention for background tasks** — both `_background_tasks` sets (root_folders, scanner_service) and `done_callback` discards are handled correctly.
- **Background task lifecycle** — all background tasks in `lifespan` are properly cancelled on shutdown.
- **defusedxml for XXE** — comic metadata parsing uses `defusedxml.ElementTree` to prevent XML External Entity attacks, with fallback handling.
- **Library pagination** — `get_books` has proper `page`/`per_page` parameters with bounds checking.
- **Upgrade safety** — `_create_library_item` creates the new item before deleting old ones, so a failure never leaves the user with zero copies. Good defensive ordering.
