import json
import logging

import httpx

from app.metadata.base import MetadataResult

logger = logging.getLogger(__name__)

HARDCOVER_URL = 'https://api.hardcover.app/v1/graphql'

# Map Hardcover's full language names to 2-letter ISO codes
_HC_LANG_TO_ISO: dict[str, str] = {
    'English': 'en', 'Norwegian': 'no', 'German': 'de', 'French': 'fr',
    'Spanish; Castilian': 'es', 'Italian': 'it', 'Portuguese': 'pt',
    'Dutch': 'nl', 'Swedish': 'sv', 'Danish': 'da', 'Finnish': 'fi',
    'Russian': 'ru', 'Polish': 'pl', 'Japanese': 'ja', 'Chinese': 'zh',
    'Korean': 'ko', 'Arabic': 'ar', 'Hebrew': 'he', 'Hindi': 'hi',
    'Czech': 'cs',
}

# Normalize Hardcover edition_format to common format names
_HC_FORMAT_MAP: dict[str, str] = {
    'Audio': 'audio', 'Paperback': 'paperback', 'Hardcover': 'hardcover',
    'ebook': 'ebook', 'Kindle': 'ebook',
}


def _normalize_editions(editions: list[dict]) -> list[dict]:
    """Normalize Hardcover edition data to provider-agnostic format."""
    for ed in editions:
        # Normalize language: {language: "English"} -> "en"
        lang = ed.get('language')
        if isinstance(lang, dict):
            lang_name = lang.get('language', '')
            ed['language'] = _HC_LANG_TO_ISO.get(lang_name, lang_name)
        elif isinstance(lang, str):
            ed['language'] = _HC_LANG_TO_ISO.get(lang, lang)
        # Normalize edition_format to common format
        fmt = ed.get('edition_format')
        if fmt:
            ed['format'] = _HC_FORMAT_MAP.get(fmt, fmt.lower() if fmt else '')
        else:
            ed['format'] = ''
    return editions


async def _query(api_key: str, query: str, variables: dict | None = None) -> dict:
    # Strip 'Bearer ' prefix if user pasted it with the token
    if api_key.startswith('Bearer '):
        api_key = api_key[7:]
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    body = {'query': query}
    if variables:
        body['variables'] = variables
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(HARDCOVER_URL, json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# search() returns jsonb `results` — no inline fragments allowed.
# We request `results` as a plain scalar and parse the JSON ourselves.
# For books we do a follow-up query to get typed Book objects.
# ---------------------------------------------------------------------------

_SEARCH_IDS_QUERY = '''
query SearchIDs($q: String!, $queryType: String!, $perPage: Int!) {
  search(query: $q, query_type: $queryType, per_page: $perPage) {
    results
  }
}'''

_BOOKS_BY_IDS_QUERY = '''
query BooksByIDs($ids: [Int!]!) {
  books(where: {id: {_in: $ids}}) {
    id title slug release_year
    image { url }
    contributions { author { name } }
    editions {
      edition_format
      language { language }
      isbn_13 isbn_10 asin
      audio_seconds
      pages
      release_year
    }
  }
}'''

_BOOKS_BY_IDS_FULL_QUERY = '''
query BooksByIDsFull($ids: [Int!]!) {
  books(where: {id: {_in: $ids}}) {
    id title subtitle description
    image { url }
    contributions { author { name } }
    editions {
      isbn_13 isbn_10 pages
      language { language }
      release_date
    }
    book_series { series { name } position_in_series }
  }
}'''


async def search_author(api_key: str, name: str) -> dict | None:
    """Search for an author by name. Returns author data from jsonb results."""
    data = await _query(api_key, _SEARCH_IDS_QUERY, {
        'q': name, 'queryType': 'author', 'perPage': 1,
    })
    raw_results = data.get('data', {}).get('search', {}).get('results', [])
    results = _parse_results(raw_results)
    if not results:
        return None
    hit = results[0]
    # Author jsonb results have: name, slug, image, books, books_count, etc.
    # Normalize image to nested dict format callers expect (image.url)
    image_val = hit.get('image')
    if isinstance(image_val, str):
        hit['image'] = {'url': image_val}
    elif not isinstance(image_val, dict):
        hit['image'] = {}
    return hit


async def get_author_books(api_key: str, author_slug: str) -> list[dict]:
    """Fetch all books by an author via contributions (authors → contributions → book)."""
    query = '''
    query AuthorBooks($slug: String!) {
      authors(where: {slug: {_eq: $slug}}) {
        name
        contributions {
          book {
            id title slug
            release_year
            image { url }
            contributions { author { name } }
            editions {
              id
              edition_format
              language { language }
              isbn_13 isbn_10 asin
              audio_seconds
              pages
            }
          }
        }
      }
    }'''
    data = await _query(api_key, query, {'slug': author_slug})
    authors = data.get('data', {}).get('authors', [])
    if not authors:
        return []
    # Extract books from contributions, filter out nulls and deduplicate
    seen_ids = set()
    books = []
    for contrib in authors[0].get('contributions', []):
        book = contrib.get('book')
        if book and book.get('id') not in seen_ids:
            seen_ids.add(book['id'])
            # Normalize editions to provider-agnostic format
            if 'editions' in book:
                book['editions'] = _normalize_editions(book['editions'])
            books.append(book)
    return books


def _parse_results(raw) -> list[dict]:
    """Parse jsonb results from Hardcover search.
    Actual format: {"hits": [{"document": {...}}, ...], "found": N}
    """
    if isinstance(raw, str):
        raw = json.loads(raw)
    # Typesense response is a dict with "hits" array
    if isinstance(raw, dict):
        hits = raw.get('hits', [])
        return [h['document'] for h in hits if isinstance(h, dict) and 'document' in h]
    # Fallback: if it's already a list
    if isinstance(raw, list):
        parsed = []
        for item in raw:
            if isinstance(item, dict):
                parsed.append(item.get('document', item))
        return parsed
    return []


async def search_books(api_key: str, query: str, per_page: int = 20) -> list[dict]:
    """Two-step search: get IDs from jsonb results, then fetch typed Book objects."""
    data = await _query(api_key, _SEARCH_IDS_QUERY, {
        'q': query, 'queryType': 'books', 'perPage': per_page,
    })
    raw_results = data.get('data', {}).get('search', {}).get('results', [])
    results = _parse_results(raw_results)
    if not results:
        return []
    ids = [int(r['id']) for r in results if isinstance(r, dict) and r.get('id')]
    if not ids:
        return []
    books_data = await _query(api_key, _BOOKS_BY_IDS_QUERY, {'ids': ids})
    books = books_data.get('data', {}).get('books', [])
    # Preserve search result ordering
    book_map = {b['id']: b for b in books}
    return [book_map[i] for i in ids if i in book_map]


def classify_media_types(book: dict) -> list[str]:
    """Classify a book's media types using normalized edition data.

    Returns a list like ['ebook'], ['audiobook'], or ['ebook', 'audiobook']
    when a book has editions of both types.
    """
    editions = book.get('editions', [])
    has_audio = any(
        e.get('audio_seconds') or e.get('format') == 'audio'
        for e in editions
    )
    has_ebook = any(
        e.get('format') in ('paperback', 'hardcover', 'ebook') or e.get('pages')
        for e in editions
    )
    types: list[str] = []
    if has_ebook or not has_audio:
        types.append('ebook')
    if has_audio:
        types.append('audiobook')
    return types


# ---------------------------------------------------------------------------
# Provider class used by MetadataService
# ---------------------------------------------------------------------------

ISBN_QUERY = """
query LookupISBN($isbn: String!) {
  books(where: {editions: {isbn_13: {_eq: $isbn}}}, limit: 1) {
    id title subtitle description
    image { url }
    contributions { author { name } }
    editions { isbn_13 isbn_10 pages language { language } release_date }
    book_series { series { name } position_in_series }
  }
}
"""


def _parse_book(book: dict) -> MetadataResult:
    authors = []
    for contrib in book.get("contributions") or []:
        author = contrib.get("author") or {}
        if author.get("name"):
            authors.append(author["name"])

    isbn_13 = isbn_10 = page_count = language = publish_year = None
    for edition in book.get("editions") or []:
        if not isbn_13 and edition.get("isbn_13"):
            isbn_13 = edition["isbn_13"]
        if not isbn_10 and edition.get("isbn_10"):
            isbn_10 = edition["isbn_10"]
        if not page_count and edition.get("pages"):
            page_count = edition["pages"]
        if not language:
            lang = edition.get("language")
            if isinstance(lang, dict):
                language = lang.get("language")
            elif isinstance(lang, str):
                language = lang
        if not publish_year and edition.get("release_date"):
            rd = str(edition["release_date"])
            if rd[:4].isdigit():
                publish_year = int(rd[:4])

    series_name = series_position = None
    for bs in book.get("book_series") or []:
        series = bs.get("series") or {}
        if series.get("name"):
            series_name = series["name"]
            series_position = bs.get("position_in_series")
            break

    image = book.get("image") or {}

    return MetadataResult(
        title=book.get("title"),
        subtitle=book.get("subtitle"),
        authors=authors,
        description=book.get("description"),
        cover_url=image.get("url"),
        publish_year=publish_year,
        page_count=page_count,
        language=language,
        isbn_10=isbn_10,
        isbn_13=isbn_13,
        series_name=series_name,
        series_position=series_position,
        hardcover_slug=book.get("slug"),
        source="hardcover",
    )


class HardcoverProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, title: str, author: str | None = None) -> list[MetadataResult]:
        try:
            query_str = f"{title} {author}" if author else title
            # Step 1: search for IDs via jsonb results
            data = await _query(self.api_key, _SEARCH_IDS_QUERY, {
                'q': query_str, 'queryType': 'books', 'perPage': 10,
            })
            raw_results = data.get("data", {}).get("search", {}).get("results", [])
            results = _parse_results(raw_results)
            if not results:
                return []
            ids = [int(r['id']) for r in results if isinstance(r, dict) and r.get('id')]
            if not ids:
                return []
            # Step 2: fetch typed Book objects by ID
            books_data = await _query(self.api_key, _BOOKS_BY_IDS_FULL_QUERY, {'ids': ids})
            books = books_data.get("data", {}).get("books", [])
            # Preserve search ordering
            book_map = {b['id']: b for b in books}
            ordered = [book_map[i] for i in ids if i in book_map]
            return [_parse_book(b) for b in ordered]
        except Exception:
            logger.warning("Hardcover search failed for %r", title, exc_info=True)
            return []

    async def lookup_isbn(self, isbn: str) -> MetadataResult | None:
        try:
            data = await _query(self.api_key, ISBN_QUERY, {"isbn": isbn})
            books = data.get("data", {}).get("books", [])
            if books:
                return _parse_book(books[0])
            return None
        except Exception:
            logger.warning("Hardcover ISBN lookup failed for %s", isbn, exc_info=True)
            return None
