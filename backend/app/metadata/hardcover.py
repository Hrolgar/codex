import logging
import httpx

logger = logging.getLogger(__name__)

HARDCOVER_URL = 'https://api.hardcover.app/v1/graphql'


async def _query(api_key: str, query: str, variables: dict | None = None) -> dict:
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    body = {'query': query}
    if variables:
        body['variables'] = variables
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(HARDCOVER_URL, json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def search_author(api_key: str, name: str) -> dict | None:
    query = '''
    query SearchAuthor($q: String!) {
      search(query: $q, query_type: "authors", per_page: 1) {
        results { ... on Author { id name slug bio image { url } } }
      }
    }'''
    data = await _query(api_key, query, {'q': name})
    results = data.get('data', {}).get('search', {}).get('results', [])
    return results[0] if results else None


async def get_author_books(api_key: str, author_slug: str) -> list[dict]:
    query = '''
    query AuthorBooks($slug: String!) {
      authors(where: {slug: {_eq: $slug}}) {
        name
        books_aggregate { aggregate { count } }
        books(order_by: {users_read_count: desc}) {
          id title slug
          release_year
          image { url }
          contributions { author { name } }
          editions {
            id
            format
            language { language }
            isbn_13 isbn_10 asin
            audio_seconds
            pages
            release_year
          }
        }
      }
    }'''
    data = await _query(api_key, query, {'slug': author_slug})
    authors = data.get('data', {}).get('authors', [])
    if not authors:
        return []
    return authors[0].get('books', [])


async def search_books(api_key: str, query: str, per_page: int = 20) -> list[dict]:
    gql = '''
    query SearchBooks($q: String!, $perPage: Int!) {
      search(query: $q, query_type: "books", per_page: $perPage) {
        results {
          ... on Book {
            id title slug release_year
            image { url }
            contributions { author { name } }
            editions {
              format language { language }
              isbn_13 isbn_10 asin audio_seconds pages
            }
          }
        }
      }
    }'''
    data = await _query(api_key, gql, {'q': query, 'perPage': per_page})
    return data.get('data', {}).get('search', {}).get('results', [])


def classify_media_type(book: dict) -> str:
    editions = book.get('editions', [])
    has_audio = any(e.get('audio_seconds') or e.get('format') == 'Audio' for e in editions)
    has_ebook = any(e.get('format') in ('Paperback', 'Hardcover', 'ebook', 'Kindle') or e.get('pages') for e in editions)
    if has_audio and not has_ebook:
        return 'audiobook'
    return 'ebook'
