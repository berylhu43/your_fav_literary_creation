from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from .forms import AddEntryForm
from .services import get_or_create_work
from .models import Catalog
from review.models import Review

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
    reviews = work.reviews.all()
    average = reviews.aggregate(Avg('rating'))['rating__avg']

    context = {
        'work': work,
        'reviews': reviews,
        'average': average,
    }

    return render(request, 'catalog/detail.html', context)
