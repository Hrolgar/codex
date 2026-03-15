# Code Review: Codex — Last 25 Commits on Main (2026-03-15)

**Reviewer:** reviewer (agent-mesh)
**Verdict:** REQUEST CHANGES — 2 critical, 5 major, 8 minor issues found.
**Commits reviewed:** b9e4928..72114df (25 commits)

---

## CRITICAL

### C1. SQL Injection in `_add_column_if_missing`

**File:** `backend/app/main.py:31`

```python
await conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}'))
```

The `table`, `column`, and `col_type` values are interpolated directly into a raw SQL string via f-string. While currently only called with hardcoded literals (`'books'`, `'hardcover_slug'`, `'VARCHAR'`), this is a dangerous pattern. If this helper is ever reused with user-derived input, it becomes a trivial SQL injection vector. The parameterized query on lines 26-28 for the `information_schema` check is done correctly — but the ALTER TABLE is not.

**Fix:** Use `sqlalchemy.sql.quoted_name` or at minimum assert the values are simple identifiers (`re.match(r'^[a-z_]+$', table)`). Better yet, just inline the ALTER TABLE statement since there's only one call site.

### C2. CORS allows all origins with credentials

**File:** `backend/app/main.py:123-129`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    ...
)
```

`allow_origins=["*"]` combined with `allow_credentials=True` is a security misconfiguration. Per the CORS spec, browsers should refuse this combination, but some older clients don't enforce it. This means any website can make authenticated requests to Codex's API if the user has an active session.

**Fix:** Either set `allow_credentials=False` or use a specific origin (configurable via env var).

---

## MAJOR

### M1. Root Folders API: No path traversal or symlink validation

**File:** `backend/app/api/root_folders.py:77-85`

The create endpoint checks `is_absolute()` and `is_dir()`, but doesn't resolve symlinks or check if the path is within allowed Docker volumes. A user could add root folders pointing to sensitive container paths like `/app`, `/proc`, or `/etc`.

**Fix:** Validate that `Path(data.path).resolve()` starts with one of the allowed volume mount points, or at minimum block paths under `/app`, `/proc`, `/sys`, `/etc`.

### M2. Frontend/Backend media type mismatch in RootFoldersSection

**File:** `frontend/src/components/settings/RootFoldersSection.tsx:19`

```typescript
const MEDIA_TYPES = ["book", "audiobook", "ebook", "comic", "magazine"];
```

Backend validates `media_type in ("ebook", "audiobook", "comic")` at `root_folders.py:74`. Frontend default is `"book"` which is always invalid — every first submission fails with 400.

**Fix:** Change to `["ebook", "audiobook", "comic"]` and default to `"ebook"`.

### M3. `addRootFolder` missing required `name` field

**Files:** `frontend/src/api/client.ts:452-461`, `frontend/src/components/settings/RootFoldersSection.tsx:49-57`

`RootFolderCreate` Pydantic model requires `name: str`, but frontend `addRootFolder` has `name` as optional and the form never collects it. Backend returns 422.

**Fix:** Either make `name` optional in backend (default from path) or add name input to form.

### M4. Delete root folder doesn't cascade or warn

**File:** `backend/app/api/root_folders.py:157-163`

Books with `target_path` referencing the deleted folder's path retain stale references. `_get_media_settings` silently falls back to legacy settings.

### M5. Hardcover `queryType` casing inconsistency

**File:** `backend/app/metadata/hardcover.py:111,193`

`search_author` uses `'Author'` (capital A) while `search_books` uses `'books'` (lowercase). May work but inconsistency suggests incomplete testing.

---

## MINOR

### m1. Missing `hardcover_slug` in LibraryService.get_book response

**File:** `backend/app/services/library_service.py:61-83`

The response dict doesn't include `hardcover_slug`, so `BookResponse.hardcover_slug` is always None and the book detail page never shows the Hardcover link.

### m2. NaN when disk usage returns null

**File:** `frontend/src/components/settings/RootFoldersSection.tsx:81`

`folder.total_space - folder.free_space` produces NaN when backend returns null.

**Fix:** `const usedSpace = (folder.total_space ?? 0) - (folder.free_space ?? 0)`

### m3. Dual migration path for hardcover_slug

**Files:** `backend/app/main.py:39`, `backend/alembic/versions/002_add_hardcover_slug.py`

Column added both at startup and via Alembic migration. Alembic version tracking may not reflect reality.

### m4. `_clean_search_query` strips valid words

**File:** `backend/app/search/prowlarr.py:26-40`

Searching for a book titled "Norwegian" strips the word. Overly aggressive heuristic.

### m5. Cancel download kills entire queue

**File:** `backend/app/services/download_service.py:443`

`asyncio.current_task()` returns the queue processor task, not a per-download task. Cancellation kills the background loop.

### m6. `restart.sh` still uses `--no-cache` in default path

**File:** `restart.sh:18`

Default path still uses `--no-cache` despite commit message saying "fast by default."

### m7. Hardcover slug stored in wrong field on Author

**File:** `backend/app/services/catalog_service.py:212`

`author.openlibrary_key = hc_author.get('slug', '')` — semantic mismatch. Latent bug if provider is switched.

### m8. Frontend RootFolder type declares free_space/total_space as non-nullable

**File:** `frontend/src/api/client.ts:444-446`

Backend returns `int | None` but frontend type is `number`. Should be `number | null`.

---

## NOT ISSUES (Verified OK)

- Prowlarr category IDs (7000, 7020, 3030, 7030) are correct per Newznab spec
- Language mapping coverage is reasonable
- SSRF protection in download_service is well-implemented
- Filename sanitization + path traversal check is correct
- Dockerfile multi-stage build is correct and includes all dependencies
- Reading status removal appears complete
- `escape_like` is properly used for ILIKE queries
