from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .services import get_recommendations
from .services import _resolve_external_id


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

def pick(request):
    title = request.GET.get('title', '').strip()
    media_type = request.GET.get('media_type', '').strip()
    external_id = _resolve_external_id(title, media_type)

    if external_id is None:
        return render(request, 'recommendations/not_found.html', {
            'title': title
        })
    return redirect('catalog:select_work',
                    media_type=media_type, external_id=external_id)