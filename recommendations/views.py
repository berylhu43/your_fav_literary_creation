from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .services import get_recommendations


@login_required
def recommend(request):
    query = request.GET.get('q', '').strip()
    media_types = request.GET.getlist('media_type')   # multiple choices
    recommendations = []
    if query and media_types:                          
        recommendations = get_recommendations(request.user, query, media_types)
    return render(request, 'recommendations/recommend.html', {
        'query': query,
        'media_types': media_types,
        'recommendations': recommendations,
    })