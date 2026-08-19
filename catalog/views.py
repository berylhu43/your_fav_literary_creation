from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.core.cache import cache
from reviews.models import Review
from .forms import AddEntryForm
from .services import get_or_create_work
from .models import Catalog
from .clients import discover_movies, get_movie_genres, search_books, search_movies, search_tv, discover_tv, get_tv_genres

@login_required
def add_entry(request):
    if request.method == 'POST':
        form = AddEntryForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            work = get_or_create_work(
                media_type=data['media_type'],
                external_id=''
            )
            work.genres.set(data['genres'])

            Review.objects.update_or_create(
                user=request.user,
                catalog=work,
                defaults={
                    'rating': data['rating'],
                    'review_text': data['review_text']
                }
            )

            return redirect('catalog:detail', pk=work.pk)

    else:
        form = AddEntryForm()

    return render(request, 'catalog/add_entry.html', {'form': form})


def detail(request, pk):
    work = get_object_or_404(Catalog, pk=pk)
    all_reviews = work.reviews.all()
    average = all_reviews.aggregate(Avg('rating'))['rating__avg']

    my_review = None
    other_reviews = all_reviews
    if request.user.is_authenticated:
        my_review = all_reviews.filter(user=request.user).first()
        other_reviews = all_reviews.exclude(user=request.user)

    credits = work.credits.select_related('artist')
    directors = [c.artist for c in credits if c.role == 'director']
    actors = [c.artist for c in credits if c.role == 'actor']
    authors = [c.artist for c in credits if c.role == 'author']

    context = {
        'work': work,
        'reviews': other_reviews,
        'average': average,
        'my_review': my_review,
        'directors': directors,
        'actors': actors,
        'authors': authors,
    }

    return render(request, 'catalog/detail.html', context)


def discovery_home(request):
    genre_id_movie = request.GET.get('genre_movie', '')
    genre_id_tv = request.GET.get('genre_tv', '')
    genres_movie = cache.get('movie_genres')
    genres_tv = cache.get('tv_genres')


    if genres_movie is None:
        genres_movie = get_movie_genres()
        cache.set('movie_genres', genres_movie, 60 * 60)  # Cache for 1 hour

    if genre_id_movie:
        movies = discover_movies(genre_id=genre_id_movie)
    else:
        movies = cache.get('popular_movies')
        if movies is None:
            movies = discover_movies()
            cache.set('popular_movies', movies, 60 * 60)  

    if genres_tv is None:
        genres_tv = get_tv_genres()
        cache.set('tv_genres', genres_tv, 60 * 60)  # Cache for 1 hour

    if genre_id_tv:
        tv = discover_tv(genre_id=genre_id_tv)
    else:
        tv = cache.get('popular_tv')
        if tv is None:
            tv = discover_tv()
            cache.set('popular_tv', tv, 60 * 60)  

    return render(request, 'catalog/discovery_home.html', {
        'movies': movies,
        'genres_movie': genres_movie,
        'selected_genre_movie': genre_id_movie,
        'tv': tv,
        'genres_tv': genres_tv,
        'selected_genre_tv': genre_id_tv,
    })

def search_works(request):
    query = request.GET.get('q', '')
    media_type = request.GET.get('media_type', 'movie')
    results = []
    if query:
        if media_type == 'tv':
            results = search_tv(query)
        elif media_type == 'book':
            results = search_books(query)
        else:
            results = search_movies(query)
    return render(request, 'catalog/search.html', {
        'query': query, 
        'media_type': media_type,
        'results':results
        })


def select_work(request, external_id, media_type):
    work = get_or_create_work(media_type=media_type, external_id=external_id)
    if work is None:
        return render(request, 'catalog/search.html', {
            'error': 'Could not fetch this work. Try another one.',
        })
    return redirect('catalog:detail', pk=work.pk)