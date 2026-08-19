from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.core.cache import cache
from reviews.models import Review
from .forms import AddEntryForm
from .services import get_or_create_work
from .models import Catalog
from .clients import search_books, search_movies, search_tv, get_popular_movies, get_popular_tv

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
    popular_movies = cache.get('popular_movies')
    if popular_movies is None:
        popular_movies = get_popular_movies()
        cache.set('popular_movies', popular_movies, 60 * 60)  # Cache for 1 hour

    popular_tv = cache.get('popular_tv')
    if popular_tv is None:
        popular_tv = get_popular_tv()
        cache.set('popular_tv', popular_tv, 60 * 60)  # Cache for 1 hour

    return render(request, 'catalog/discovery_home.html', {
        'popular_movies': popular_movies,
        'popular_tv': popular_tv,
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