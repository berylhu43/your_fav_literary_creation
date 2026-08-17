from .models import Catalog, Genre
from . import clients

def _map_movie(tmdb_id):
    data = clients.get_movie_details(tmdb_id)
    if data is None:
        return None
    
    # reflect each queries
    release_date = data.get('release_date') or ''
    release_year = int(release_date[:4]) if release_date[:4].isdigit() else None
    poster_path = data.get('poster_path')
    cover_url = f'https://image.tmdb.org/t/p/w500{poster_path}' if poster_path else ''

    return {
        'title': data.get('title', ''),
        'release_year': release_year,
        'description': data.get('overview', ''),
        'runtime': data.get('runtime'),
        'cover_url': cover_url,
        'genre_names': [g['name'] for g in data.get('genres', [])],
    }

def _map_tv(tmdb_id):
    data = clients.get_tv_details(tmdb_id)
    if data is None:
        return None

    first_air = data.get('first_air_date') or ''
    release_year = int(first_air[:4]) if first_air[:4].isdigit() else None
    poster_path = data.get('poster_path')
    cover_url = f'https://image.tmdb.org/t/p/w500{poster_path}' if poster_path else ''

    return {
        'title': data.get('name', ''),                    
        'release_year': release_year,
        'description': data.get('overview', ''),
        'episodes': data.get('number_of_episodes'),       
        'cover_url': cover_url,
        'genre_names': [g['name'] for g in data.get('genres', [])],
    }


def get_or_create_work(*, media_type, tmdb_id):
    """
    Stage 2: given a media_type and a TMDB id, return the matching Catalog
    row — reusing it if it already exists, otherwise fetching from TMDB,
    mapping the fields, and creating it.

    Search tv and movie available on current stage.
    """

    # check if the subject existed in the catalog
    existing = Catalog.objects.filter(
        source=Catalog.Source.TMDB,
        external_id=str(tmdb_id),
    ).first()
    if existing:
        return existing

    # if not existed, get by media type
    if media_type == Catalog.MediaType.MOVIE:
        fields = _map_movie(tmdb_id)
    elif media_type == Catalog.MediaType.TV:
        fields = _map_tv(tmdb_id)
    else:
        return None

    if fields is None:
        return None

    genre_names = fields.pop('genre_names')
    
    work = Catalog.objects.create(
        media_type = media_type,
        source=Catalog.Source.TMDB,
        external_id=str(tmdb_id),
        **fields,
    )

    # genre reflection from TMDB api
    genre_objects = []
    for g in genre_names:
        genre,_=Genre.objects.get_or_create(name=g)
        genre_objects.append(genre)
    work.genres.set(genre_objects)

    return work