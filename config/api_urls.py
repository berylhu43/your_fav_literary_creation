from rest_framework.routers import DefaultRouter
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from reviews.api_views import ReviewViewSet
from catalog.api_views import CatalogDetailAPI, CatalogReviewsAPI

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('token/', obtain_auth_token, name='api_token'),
    path('', include(router.urls)),
    path('catalog/<int:pk>/', CatalogDetailAPI.as_view(), name='api_catalog-detail'),
    path('catalog/<int:pk>/reviews/', CatalogReviewsAPI.as_view(), name='api_catalog-reviews'),
]