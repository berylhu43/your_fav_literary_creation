from django.urls import path
from .api_views import RecommendationAPI, RecommendationPickAPI

urlpatterns = [
    path('', RecommendationAPI.as_view(), name='api_recommendations'),
    path('pick/', RecommendationPickAPI.as_view(), name='api_recommendation_pick'),
]