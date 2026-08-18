import requests
from django.conf import settings

TMDB_BASE_URL = 'https://api.themoviedb.org/3'
GOOGLE_BOOKS_URL = 'https://www.googleapis.com/books/v1/volumes'

def _tmdb_get(path, params=None):
    """
    Low-level: make one GET request to TMDB, handling timeout/errors.
    Returns parsed JSON dict, or None on failure.
    """
    try: 
        response = requests.get(
            f'{TMDB_BASE_URL}{path}',
            params={'api_key':settings.TMDB_API_KEY, **(params or {})},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None

def _google_books_get(path, params=None):
    """
    Low-level: query Google Books API, handling timeout/errors.
    Returns parsed JSON dict, or None on failure.
    """
    try:
        response = requests.get(
            f'{GOOGLE_BOOKS_URL}{path}',
            params={'key':settings.GOOGLE_BOOKS_API_KEY, **(params or {})},
            timeout = 5,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def search_movies(query):
    """
    Search by film name from TMDB api and return candidates.
    """
    data = _tmdb_get('/search/movie', {'query': query})
    return data.get('results', [])[:20] if data else []


def search_tv(query):
    """
    Search by tv series name from TMDB api and return candidates.
    """
    data = _tmdb_get('/search/tv', {'query': query})
    return data.get('results', [])[:20] if data else []

def search_books(query):
    """
    Search by books name from google books api and return candidates.
    """
    data = _google_books_get('', {'q':query, 'orderBy': 'relevance'})
    return data.get('items', [])[:20] if data else []

def get_movie_details(tmdb_id):
    """
    Fetch full details for one movie from TMDB by its id.
    Returns the movie dict, or None on failure.
    """
    return _tmdb_get(f'/movie/{tmdb_id}')

def get_tv_details(tmdb_id):
    """
    Fetch full details for one tv from TMDB by its id.
    Returns the tv dict, or None on failure.
    """
    return _tmdb_get(f'/tv/{tmdb_id}')

def get_book_details(volume_id):
    """
    Fetch full details for one book from GOOGLE books by its id.
    Returns the book dict, or None on failure.
    """
    return _google_books_get(f'/{volume_id}')
    