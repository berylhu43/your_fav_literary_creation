from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from reviews.models import Review
from .forms import AddEntryForm
from .services import get_or_create_work
from .models import Catalog
from .clients import search_movies, search_tv

@login_required
def add_entry(request):
    if request.method == 'POST':
        form = AddEntryForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            work = get_or_create_work(
                media_type=data['media_type'],
                title=data['title']
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

    context = {
        'work': work,
        'reviews': other_reviews,
        'average': average,
        'my_review': my_review,
    }

    return render(request, 'catalog/detail.html', context)


def catalog_list(request):
    works = Catalog.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews'),
    )

    query = request.GET.get('q', '')
    if query:
        works = works.filter(title__icontains=query)

    return render(request, 'catalog/list.html', {'works': works, 'query':query})

def search_works(request):
    query = request.GET.get('q', '')
    media_type = request.GET.get('media_type', 'movie')
    results = []
    if query:
        if media_type == 'tv':
            results = search_tv(query)
        else:
            results = search_movies(query)
    return render(request, 'catalog/search.html', {
        'query': query, 
        'media_type': media_type,
        'results':results
        })


def select_work(request, tmdb_id, media_type):
    work = get_or_create_work(media_type=media_type, tmdb_id=tmdb_id)
    if work is None:
        return render(request, 'catalog/search.html', {
            'error': 'Could not fetch this movie. Try another one.',
        })
    return redirect('catalog:detail', pk=work.pk)