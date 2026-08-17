import requests
from django.conf import settings

TMDB_BASE_URL = 'https://api.themoviedb.org/3'

def search_movies(query):
    """
    Search by film name from TMDB api and return candidates.
    """
    try:
        response = requests.get(
            f'{TMDB_BASE_URL}/search/movie',
            params={
                'api_key': settings.TMDB_API_KEY,
                'query': query,
            },
            timeout=5,
        )
        response.raise_for_status()
        return response.json().get('results', [])[:10]
    except requests.RequestException:
        return []

def get_movie_details(tmdb_id):
    """
    Fetch full details for one movie from TMDB by its id.
    Returns the movie dict, or None on failure.
    """
    try:
        response = requests.get(
            f'{TMDB_BASE_URL}/movie/{tmdb_id}',
            params={'api_key': settings.TMDB_API_KEY},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None
    