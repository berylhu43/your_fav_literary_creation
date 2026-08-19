from django.utils.html import strip_tags
from .models import Catalog, Genre, Artist, Credit
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
        'description': strip_tags(data.get('overview', '')),
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
    created_by = data.get('created_by', [])

    return {
        'title': data.get('name', ''),                    
        'release_year': release_year,
        'description': strip_tags(data.get('overview', '')),
        'episodes': data.get('number_of_episodes'),       
        'cover_url': cover_url,
        'genre_names': [g['name'] for g in data.get('genres', [])],
        'created_by': created_by
    }


def _map_book(volume_id):
    data = clients.get_book_details(volume_id)
    if data is None:
        return None

    info = data.get('volumeInfo', {})

    published = info.get('publishedDate') or ''
    release_year = int(published[:4]) if published[:4].isdigit() else None
    image_links = info.get('imageLinks', {})
    cover_url = image_links.get('thumbnail', '')

    # google books api returns categories as a list of strings
    # each string may contain multiple genres separated by "/"
    genre_names = []
    categories = info.get('categories', [])
    if categories:
        for part in categories[0].split('/'):   
            name = part.strip()
            if name:
                genre_names.append(name)

    return {
        'title': info.get('title', ''),
        'release_year': release_year,
        'description': strip_tags(info.get('description', '')),
        'pages': info.get('pageCount'),
        'cover_url': cover_url,
        'genre_names': genre_names,
        'author_names': info.get('authors', []),
    }


def _get_or_create_artists(person):
    profile_path = person.get('profile_path')
    profile_url = f'https://image.tmdb.org/t/p/w185{profile_path}' if profile_path else ''
    artist,_ = Artist.objects.get_or_create(
        source = Catalog.Source.TMDB,
        external_id = str(person['id']),
        defaults = {
            'name': person.get('name', ''),
            'profile_url': profile_url,
        },
    )
    return artist


def _add_movie_credits(work, external_id):
    cast, crew = clients.get_movie_credits(external_id)

    # find directors
    directors = [c for c in crew if c.get('job') == 'Director']

    for person in directors:
        artist = _get_or_create_artists(person)
        Credit.objects.get_or_create(catalog=work, artist=artist, role='director')

    for person in cast[:10]:
        artist = _get_or_create_artists(person)
        Credit.objects.get_or_create(catalog=work, artist=artist, role='actor')

def _add_tv_credits(work, external_id, created_by):
    cast = clients.get_tv_credits(external_id)

    for person in created_by:
        artist = _get_or_create_artists(person)
        Credit.objects.get_or_create(catalog=work, artist=artist, role='director')

    for person in cast[:10]:
        artist = _get_or_create_artists(person)
        Credit.objects.get_or_create(catalog=work, artist=artist, role='actor')


def _add_book_credits(work, author_names):
    for name in author_names:
        artist, _ = Artist.objects.get_or_create(
            name=name,
            defaults={'source': Catalog.Source.GOOGLE_BOOKS}
        )
        Credit.objects.get_or_create(catalog=work, artist=artist, role='author')

def get_or_create_work(*, media_type, external_id):
    """
    Stage 2: given a media_type and a TMDB id, return the matching Catalog
    row — reusing it if it already exists, otherwise fetching from TMDB,
    mapping the fields, and creating it.

    Search tv and movie available on current stage.
    """
    # check source by media types
    if media_type == Catalog.MediaType.BOOK:
        source = Catalog.Source.GOOGLE_BOOKS
    elif media_type in (Catalog.MediaType.MOVIE, Catalog.MediaType.TV):
        source = Catalog.Source.TMDB
    else:
        return None   

    # check if the subject existed in the catalog
    existing = Catalog.objects.filter(
        media_type=media_type,
        source=source,
        external_id=str(external_id),
    ).first()
    if existing:
        return existing

    # if not existed, get by media type
    if media_type == Catalog.MediaType.MOVIE:
        fields = _map_movie(external_id)
    elif media_type == Catalog.MediaType.TV:
        fields = _map_tv(external_id)
    elif media_type == Catalog.MediaType.BOOK:
        fields = _map_book(external_id)

    if fields is None:
        return None

    genre_names = fields.pop('genre_names')
    created_by = fields.pop('created_by', [])
    author_names = fields.pop('author_names', [])
    
    work = Catalog.objects.create(
        media_type = media_type,
        source=source,
        external_id=str(external_id),
        **fields,
    )

    # genre reflection from TMDB api
    genre_objects = []
    for g in genre_names:
        genre,_=Genre.objects.get_or_create(name=g)
        genre_objects.append(genre)
    work.genres.set(genre_objects)

    # credits reflection from TMDB api
    if media_type == Catalog.MediaType.MOVIE:
        _add_movie_credits(work, external_id)
    elif media_type == Catalog.MediaType.TV:
        _add_tv_credits(work, external_id, created_by)
    elif media_type == Catalog.MediaType.BOOK:
        _add_book_credits(work, author_names)

    return work