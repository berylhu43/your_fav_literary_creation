from .models import Catalog
from . import clients

def get_or_create_work(*, media_type, tmdb_id):
    """
    Stage 2: given a media_type and a TMDB id, return the matching Catalog
    row — reusing it if it already exists, otherwise fetching from TMDB,
    mapping the fields, and creating it.
    """
    # check if the subject existed in the catalog
    existing = Catalog.objects.filter(
        source=Catalog.Source.TMDB,
        external_id=str(tmdb_id),
    ).first()
    if existing:
        return existing

    # if not existed, get from TMDB api
    data = clients.get_movie_details(tmdb_id)
    if data is None:
        return None

    # reflect each queries
    release_date = data.get('release_date') or ''
    release_year = int(release_date[:4]) if release_date[:4].isdigit() else None

    poster_path = data.get('poster_path')
    cover_url = f'https://image.tmdb.org/t/p/w500{poster_path}' if poster_path else ''

    work = Catalog.objects.create(
        media_type = media_type,
        title = data.get('title', ''), 
        release_year=release_year,
        description=data.get('overview',''),
        runtime=data.get('runtime'),
        cover_url=cover_url,
        source=Catalog.Source.TMDB,
        external_id=str(tmdb_id),
    )
    return work