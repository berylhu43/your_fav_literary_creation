from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Review
from .forms import ReviewForm

@login_required
def my_records(request):
    reviews = (
        request.user.reviews
        .select_related('catalog')
        .all()
    )

    query = request.GET.get('q', '')
    if query:
        reviews = reviews.filter(catalog__title__icontains=query)

        return render(request, 'reviews/my_records.html',{
            'reviews': reviews,
            'query': query,
        })
    return render(request, 'reviews/my_records.html', {'reviews': reviews})

@login_required
def delete_record(request, pk):
    review = get_object_or_404(Review, pk=pk, user=request.user)

    if request.method == 'POST':
        review.delete()
        return redirect('reviews:my_records')

    return render(request, 'reviews/delete_record.html', {'review': review})


def change_record(request, pk):
    review = get_object_or_404(Review, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            return redirect('reviews:my_records')
    else:
        form = ReviewForm(instance=review)

    return render(request, 'reviews/change_record.html', {'form':form, 'review': review})