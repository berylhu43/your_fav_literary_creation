from django.core.cache import cache
from django.db.models import Count, Q
from datetime import date
from catalog.clients import _tmdb_get, _google_books_get
from reviews.models import Review
from catalog.models import Genre, Catalog
from .clients import _llm_get
import json
import re
import unicodedata
import hashlib


def get_recommendations(user, query, media_types, force_refresh=False):
    """
    Get personalized recommendations for a user.
    Three steps: llm filter based on user input, ORM get user history, query LLM.
    Query user's human language input.
    Media type mutiple choice form, eg. ['movie', 'tv']
    Can be used for REST API or background tasks.
    """
    # check cache
    key = _recommend_cache_key(user, query, media_types)

    if not force_refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached

    filters = _extract_filters(query, media_types)
    samples = _sample_reviews(user, filters, media_types, per_bucket=12)
    prompt = _build_recommend_prompt(query, media_types, samples, filters)
    raw = _llm_get([{'role': 'user', 'content': prompt}], thinking={'type': 'enabled'}, reasoning_effort='high')
    result = _parse(raw) if raw else []
    result = _filter_seen(user, result, media_types)   
    result = result[:10]
    cache.set(key, result, 60 * 60)
    print(f'>>> final result: {result!r}')
    return result

# get cache
def _recommend_cache_key(user, query, media_types):
    types = ",".join(sorted(media_types))
    q = query.strip().lower()
    digest = hashlib.sha256(q.encode('utf-8')).hexdigest()[:16]
    return f'rec:{user.id}:{types}:{digest}'


# First Step: extract filters from user query using LLM
def _extract_filters(query, media_types):
    """
    Use LLM to extract filters from user query.
    Returns a dict of filters, e.g. {'genre': 'sci-fi', 'year': 2020}
    """
    prompt = _build_extract_prompt(query, media_types)
    raw = _llm_get([{'role': 'user', 'content': prompt}], temperature=0.2, thinking={'type': 'disabled'}, reasoning_effort='low')
    print(f'>>> extract raw: {raw!r}') 
    if raw is None:
        return {}
    try:
        parsed =json.loads(raw)
        print(f'>>> extract parsed: {parsed!r}')
        return parsed
    except (json.JSONDecodeError, TypeError):
        print('>>> extract parse FAILED')
        return {}


def _build_extract_prompt(query, media_types):
    """Build a prompt that turns the user's free-text request into a
    structured filter JSON."""
    genre_names = list(Genre.objects.filter(catalogs__media_type__in=media_types)
                       .distinct().order_by('name').values_list('name', flat=True))
    genre_list = ', '.join(genre_names)
    today = date.today().isoformat()
    return (
        "You are a filter extractor for a media recommendation app. "
        "Given a user's free-text request for what they want to watch or read, "
        "extract structured search filters.\n\n"
        f"Available genres (choose ONLY from these, use the exact spelling): "
        f"{genre_list}\n\n"
        "Rules:\n"
        "- For any field you cannot infer, use null (or [] for genres).\n"
        "- 'genres': a list of genre names implied by the request. "
        "Return 2-3 genres — pick the ones most central to the request. "
        "Do not return just one unless the request names a single genre explicitly. "
        "For mood or occasion requests (e.g. 'first date at home', 'something to watch with "
        "family'), infer suitable genres yourself (e.g. Romance, Comedy, Family).\n"
        "- 'rating_min' / 'rating_max': a 0-5 scale. Only set these if the "
        "request implies a quality bar (e.g. 'hidden gems', 'only the best'). "
        "For casual requests leave them null.\n"
        "- 'artist': a person's name if the request names one (actor, director, "
        "author), else null. Return the person's full name in English/Latin script\n"
        "- 'year_min' / 'year_max': set these if the request implies a time "
        "period (e.g. '90s movies' -> 1990 to 1999), else null.\n\n"
        "Return this exact json shape:\n"
        '{"genres": [], "rating_min": null, "rating_max": null, '
        '"artist": null, "year_min": null, "year_max": null}\n\n'
        f"Today's date: {today}\n\n"
        f"User request: \"{query}\""         
    )

# Second Step: sample reviews from user history using ORM
DIRECTOR_ROLE = 'director'      
DIRECTOR_LIMIT = 2

def _director_key(catalog):
    """
    Artist id of the director, for de-duplication.
    None when there's no director credit (books, some tv, incomplete data).
    Reads from prefetched credits — no extra query.
    """
    for credit in catalog.credits.all():
        if credit.role == DIRECTOR_ROLE:
            return credit.artist_id
    return None

def _sample_reviews(user, filters, media_types, per_bucket=10):
    """
    Sample reviews from user history using ORM.
    Dynamic filtering based on LLM output.
    Returns a list of Review objects.
    """
    qs = Review.objects.filter(
        user=user, 
        catalog__media_type__in=media_types,
        )
    
    genres = filters.get('genres')
    if genres:
        qs = qs.filter(catalog__genres__name__in=genres)

    artist = filters.get('artist')
    if artist:
        qs = qs.filter(catalog__credits__artist__name__icontains=artist)

    year_min = filters.get('year_min')
    if year_min:
        qs = qs.filter(catalog__release_year__gte=year_min)
    year_max = filters.get('year_max')
    if year_max:
        qs = qs.filter(catalog__release_year__lte=year_max)
        
    rating_min = filters.get('rating_min')
    if rating_min is not None:
        qs = qs.filter(rating__gte=rating_min)
    rating_max = filters.get('rating_max')
    if rating_max is not None:
        qs = qs.filter(rating__lte=rating_max)

    # sort by more matching genres
    if genres:
        qs = qs.annotate(
            genre_match=Count(
                'catalog__genres',
                filter=Q(catalog__genres__name__in=genres),
                distinct=True,
            )
        ).order_by('-rating', '-genre_match')
    else:
        qs = qs.order_by('-rating')

    # pull credits + artists in one go so _director_key doesn't cause N+1
    qs = (qs.select_related('catalog')
            .prefetch_related('catalog__credits')
            .distinct())

    # collection de-deup per bucket
    buckets = {}
    collections = set()
    director_count = {}
    for review in qs:
        catalog = review.catalog
        cid = catalog.collection_id
    
        if cid and cid in collections:
            continue

        dkey = _director_key(catalog)
        if dkey and director_count.get(dkey, 0) >= DIRECTOR_LIMIT:
            continue

        key = int(float(review.rating))
        bucket = buckets.setdefault(key, [])
        if len(bucket) < per_bucket:
            bucket.append(review)
            if cid:
                collections.add(cid)
            if dkey:
                director_count[dkey] = director_count.get(dkey, 0) + 1
    result = [review for bucket in buckets.values() for review in bucket]
    print(f'>>> sampled {len(result)} reviews: '
          f'{[r.catalog.title for r in result]}')
    return result

# Third Step: build prompt and query LLM for recommendations
def _build_recommend_prompt(query, media_types, samples, filters):
    """Build the final prompt that asks the LLM to recommend works,
    grounded in the user's rating history when available."""
    today = date.today().isoformat()
    
    if samples:
        history = "\n".join(
            f"- {r.catalog.title} (rated {r.rating}/5)" for r in samples
        )
    else:
        history = "(no rating history for this request)"

    types = ", ".join(media_types)

    constraints = []
    genres = filters.get('genres')
    if genres:
        constraints.append(f"- Genre: every recommendation MUST match at least one of: {', '.join(genres)}.")
    year_min = filters.get('year_min')
    year_max = filters.get('year_max')
    if year_min and year_max:
        constraints.append(f"- Release year: MUST be between {year_min} and {year_max} (inclusive).")
    elif year_min:
        constraints.append(f"- Release year: MUST be {year_min} or later.")
    elif year_max:
        constraints.append(f"- Release year: MUST be {year_max} or earlier.")
    artist = filters.get('artist')
    if artist:
        constraints.append(f"- Prefer works involving {artist} when possible (soft preference, not mandatory).")

    constraint_block = (
        "Hard constraints extracted from the request "
        "(a recommendation that violates a MUST is invalid):\n"
        + "\n".join(constraints) + "\n\n"
    ) if constraints else ""

    return (
        "You are a recommendation engine for a personal media tracker. "
        "Recommend works the user is likely to enjoy but has NOT seen yet.\n\n"
        "Rules:\n"
        "- Recommend 15 works.\n"
        "- Ground your picks in the user's taste.\n"
        "- Every recommendation must satisfy ALL hard constraints listed below.\n"
        "- If the history is empty or has fewer than 5 useful signals, fill the "
        "rest using your own knowledge of well-regarded works that match the "
        "request AND the hard constraints.\n"
        "- Do NOT recommend any title already listed in the history below.\n"
        f"- Every recommendation's media_type must be one of: {types}.\n\n"
        f"What the user is looking for: \"{query}\"\n"
        f"Today's date: {today}\n\n"
        f"Media types to recommend: {types}\n\n"
        f"{constraint_block}"
        "The user's past ratings relevant to this request: \n"
        f"{history}\n\n"
        "Return this exact json shape:\n"
        '{"recommendations": [{"title": "...", "media_type": "...", "year": "...", "reason": "..."}]}\n'
    )

def _parse(raw):
    try:
        data = json.loads(raw)
        return data.get('recommendations', [])
    except (json.JSONDecodeError, TypeError):
        return []


# filter duplicate
def _norm_title(t):
    """Normalize for comparison: strip accents, punctuation, articles, spaces."""
    if not t:
        return ''
    # é -> e, ō -> o
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = t.lower().strip()
    # drop leading articles (en/fr/es) so "The X" == "X" == "La X"
    t = re.sub(r'^(the|a|an|le|la|les|el|los|il)\s+', '', t)
    # drop everything that isn't a letter or digit
    t = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '', t)
    return t


def _filter_seen(user, recommendations, media_types):
    seen = set(
        _norm_title(t) for t in Review.objects.filter(
            user=user,
            catalog__media_type__in=media_types,
        ).values_list('catalog__title', flat=True)
    )
    return [r for r in recommendations
            if _norm_title(r.get('title', '')) not in seen]


def _resolve_external_id(title, media_type):
    """
    Resolve a title and media type to an external ID (e.g. TMDB ID).
    Search in the Catalog DB first, if not found, search external APIs.
    If not found, return None. 
    Send to corresponding external API based on media_type.
    """
    # search in internal db first
    local = Catalog.objects.filter(
        title__iexact=title, 
        media_type=media_type,
    ).first()
    if local and local.external_id:
        return local.external_id

    # if not found, search exteranl APIs
    if media_type in ('movie', 'tv'):
        data = _tmdb_get(f'/search/{media_type}', params={'query': title})
        results = data.get('results', [])
        if results:
            return results[0].get('id')
    elif media_type == 'book':
        data = _google_books_get('', {'q':title})
        items = data.get('items', [])
        if items:
            return items[0].get('id')
    return None

