from django.urls import path
from .api_views import (
    CatalogDetailAPI, CatalogReviewsAPI,
    CatalogPopularMovieAPI, CatalogPopularTVAPI, CatalogSearchAPI,
    CatalogSelectAPI, ArtistDetailAPI
)

urlpatterns = [
    path('popular/movie/', CatalogPopularMovieAPI.as_view(), name='api_catalog_popular_movie'),
    path('popular/tv/', CatalogPopularTVAPI.as_view(), name='api_catalog_popular_tv'),
    path('search/', CatalogSearchAPI.as_view(), name='api_catalog_search'),
    path('select/', CatalogSelectAPI.as_view(), name='api_catalog_select'),
    path('artists/<int:pk>/', ArtistDetailAPI.as_view(), name='api_artist_detail'),
    path('<int:pk>/', CatalogDetailAPI.as_view(), name='api_catalog_detail'),
    path('<int:pk>/reviews/', CatalogReviewsAPI.as_view(), name='api_catalog_reviews'),
]