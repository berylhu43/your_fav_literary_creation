import requests
from django.conf import settings

TMDB_BASE_URL = 'https://api.themoviedb.org/3'

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

def search_book(query):
    pass


def get_movie_details(tmdb_id):
    """
    Fetch full details for one movie from TMDB by its id.
    Returns the movie dict, or None on failure.
    """
    return _tmdb_get(f'/movie/{tmdb_id}')

def get_tv_details(tmdb_id):
    """
    Fetch full details for one movie from TMDB by its id.
    Returns the movie dict, or None on failure.
    """
    return _tmdb_get(f'/tv/{tmdb_id}')

def get_book_details():
    pass
    