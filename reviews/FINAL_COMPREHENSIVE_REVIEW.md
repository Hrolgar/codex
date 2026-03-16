# Codex — Final Comprehensive Review

**Date:** 2026-03-16
**Reviewer:** reviewer (Code Review Worker)
**Scope:** All phases — full codebase audit before testing

---

## VERDICT: REQUEST CHANGES

**6 Critical, 8 High, 10 Medium, 7 Low** issues identified.

---

## CRITICAL ISSUES

### C1. Frontend calls `/libraries` endpoints that don't exist
**Files:** `frontend/src/api/client.ts` lines 242-263
**Impact:** BLOCKING — Library management UI is completely broken

Frontend defines and calls:
- `GET /api/libraries`
- `POST /api/libraries`
- `DELETE /api/libraries/{id}`
- `POST /api/libraries/{id}/scan`

Backend has NO `/libraries` router. The equivalent functionality is at `/api/root-folders`. The frontend `Library` type (line 134-144) doesn't match `RootFolderResponse` schema either.

**Fix:** Update `client.ts` to use `/root-folders` endpoints and align the `Library` type with `RootFolderResponse`, OR add `/libraries` as an alias in `router.py`.

---

### C2. Settings key mismatch in download client service
**File:** `backend/app/services/download_client_service.py` lines 76, 83
**Impact:** Download category assignment silently fails

Code fetches:
- `'downloadclient.qbittorrent.category'` — does NOT exist in schema
- `'downloadclient.sabnzbd.category'` — does NOT exist in schema

Schema defines per-media-type keys:
- `'downloadclient.qbittorrent.category.ebook'`
- `'downloadclient.qbittorrent.category.audiobook'`
- `'downloadclient.qbittorrent.category.comic'`
- (same pattern for sabnzbd)

**Fix:** Update `get_client_from_settings()` to accept a `media_type` parameter and fetch the correct per-type category key.

---

### C3. Fire-and-forget async tasks in authors.py
**File:** `backend/app/api/authors.py` lines 378, 424
**Impact:** Background catalog refresh tasks can be garbage-collected before completion

```python
asyncio.create_task(_refresh_catalog(author.id))  # Line 378 — no reference stored
asyncio.create_task(_refresh(author_id))           # Line 424 — no reference stored
```

Other endpoints in the same file correctly use `_background_tasks.add(task)` (line 509-511).

**Fix:** Store task references in `_background_tasks` set with `add_done_callback` for discard.

---

### C4. No authentication or authorization on any endpoint
**Files:** All API routes, `backend/app/main.py` lines 163-169
**Impact:** Any network-accessible client can browse filesystem, trigger downloads, modify settings, clear database

- Zero auth middleware
- CORS allows all origins with credentials: `allow_origins=["*"], allow_credentials=True`
- WebSocket has no auth check (`backend/app/api/downloads.py` line 61)
- Dev endpoints guarded only by env var, not auth

**Note:** Acceptable for v1 local-only deployment, but must be addressed before any network exposure.

---

### C5. SQL injection risk in migration helper
**File:** `backend/app/main.py` line 42
**Impact:** `default_clause` is interpolated into raw SQL without validation

```python
await conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}'))
```

While table/column names are validated with `_validate_identifier()`, the default value clause is not. Currently only called with hardcoded values from lifespan, but the function is generic and reusable.

**Fix:** Validate `default` parameter or use SQLAlchemy DDL operations instead of raw text.

---

### C6. Path traversal in Calibre import
**File:** `backend/app/api/importexport.py` line 165
**Impact:** Malicious Calibre library can create LibraryItems pointing outside intended directory

```python
file_path = str(library_path / book_dir / f"{file_name}.{fmt}")
```

`book_dir` comes directly from Calibre's `metadata.db` (`row["book_path"]`) without path traversal validation. Combined with no auth (C4), attacker can point to arbitrary filesystem paths.

**Fix:** Resolve and validate that final path is within `library_path`:
```python
resolved = (library_path / book_dir).resolve()
resolved.relative_to(library_path.resolve())  # raises ValueError if outside
```

---

## HIGH ISSUES

### H1. Download path validation uses string prefix (anti-pattern)
**File:** `backend/app/services/download_service.py` line 489
```python
if not str(final_path.resolve()).startswith(str(download_dir.resolve())):
```
`/data/downloads-evil/file` passes this check. Use `Path.relative_to()` instead.

### H2. Hardlink destination not validated against root
**File:** `backend/app/services/hardlink_service.py` line 43
Book metadata containing `../../` in title could write files outside destination root.

### H3. Calibre import path not restricted to allowed directories
**File:** `backend/app/api/importexport.py` lines 72-77
User-supplied `body.path` can point to any directory on the filesystem. No allowlist.

### H4. Unhandled HTTP errors in author search endpoint
**File:** `backend/app/api/authors.py` lines 72-78
`resp.raise_for_status()` for OpenLibrary call has no try/except — returns 500 instead of meaningful error.

### H5. Partial download cleanup incomplete
**File:** `backend/app/services/download_service.py` lines 553-557
Error path uses bare `except Exception: pass` which swallows cleanup failures silently.

### H6. AuthorBookListItem `editions` field not in frontend type
**Backend:** `backend/app/api/authors.py` line 282 returns `editions: list[dict]`
**Frontend:** `AuthorBookListItem` type (client.ts lines 29-32) has no `editions` field.

### H7. Metadata provider errors crash enrichment
**File:** `backend/app/services/metadata_service.py` lines 42-50
No per-provider try/except — one provider exception kills the whole enrichment loop.

### H8. Catalog refresh doesn't update author status on failure
**File:** `backend/app/main.py` lines 106-118
When periodic refresh fails, `author.catalog_status` stays as previous value instead of being set to `"error"`.

---

## MEDIUM ISSUES

### M1. 30+ settings defined in schema but never referenced in code
**File:** `backend/app/services/settings_service.py`
Includes: `audiobookshelf.url/api_key`, `prowlarr.enabled`, `general.theme`, `general.library_url`, `scan.interval_hours`, `notifications.on_new_books`, all `metadata.*.enabled` toggles.

### M2. Frontend `SearchResult` type missing 4 backend fields
`magnet_url`, `protocol`, `publish_date`, `grabs` — returned by backend but not typed in frontend.

### M3. Frontend `DownloadResponse` missing `root_folder_id` and `is_upgrade`
These fields were added in recent commits but frontend type wasn't updated.

### M4. `any` types in AuthorDetailPage break type safety
**File:** `frontend/src/pages/AuthorDetailPage.tsx` lines 102, 299
`Record<string, any[]>` and `book: any` — should use proper types.

### M5. Non-null assertions in SearchPage without validation
**File:** `frontend/src/pages/SearchPage.tsx` lines 87, 91, 98
`result.download_url!` and `result.source!` — will crash if nullish.

### M6. Hardcoded database credentials in config
**File:** `backend/app/config.py` line 9 — `postgresql+asyncpg://codex:codex@db:5432/codex`

### M7. WebSocket has no authentication
**File:** `backend/app/api/downloads.py` line 61

### M8. Dev endpoints use runtime env var, not build-time guard
**File:** `backend/app/api/dev.py` lines 20-22

### M9. Notification type not enum-constrained on backend
**Backend:** `notification_type: str` — Frontend expects `"info"|"success"|"warning"|"error"` literal union.

### M10. Google Books API key inconsistency
Schema has both `metadata.google.api_key` and `metadata.google_books.api_key`. Code only checks one.

---

## LOW ISSUES

### L1. Orphaned `/app/sources/` directory — empty, never imported
### L2. Prowlarr search returns 500 instead of 503 when Prowlarr is down (`backend/app/api/search.py`)
### L3. Error messages expose internal file paths (`importexport.py` line 77)
### L4. Inconsistent `exc_info` usage in background task logging
### L5. `position` type: backend uses `float`, frontend expects `number` (JS has no distinction, but intent is unclear)
### L6. Frontend doesn't call `/notifications/count` endpoint (exists but unused)
### L7. TODO: Google Books catalog provider not implemented (`catalog_service.py` line 3)

---

## WHAT'S WORKING WELL

- **Import structure is excellent** — zero circular imports, clean dependency graph
- **Models are consistent** — all ForeignKeys use string references, all models properly exported
- **Router registration complete** — all 11 route modules registered in `router.py`
- **Background tasks in main.py lifespan** are properly tracked and cancelled on shutdown
- **Root folder scan tasks** correctly use `_background_tasks` set with done callbacks
- **Database sessions** properly managed via `Depends(get_db)` with async context managers
- **SSRF validation** exists in download service (lines 46-62)
- **Filename sanitization** exists in download service (lines 65-79)
- **Rate limiter** properly implemented for metadata provider calls
- **Schema inheritance** is clean — schemas compose via Pydantic without circular deps

---

## PRIORITY ORDER FOR FIXES

### Before Testing (Blockers)
1. **C1** — Fix `/libraries` → `/root-folders` endpoint mismatch (UI is broken)
2. **C2** — Fix download client category settings keys
3. **C3** — Store async task references in `authors.py`

### Before Any Network Exposure
4. **C4** — Add authentication system
5. **C5** — Fix SQL injection in migration helper
6. **C6** — Add path traversal validation to Calibre import
7. **H1-H3** — Fix all path validation issues

### Before Release
8. **H4-H8** — Error handling improvements
9. **M1-M10** — Type alignment and dead settings cleanup
10. **L1-L7** — Polish items
