from rest_framework.authtoken.views import obtain_auth_token
from reviews.api_views import ReviewViewSet
from rest_framework.routers import DefaultRouter
from django.urls import path, include

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('token/', obtain_auth_token, name='api_token'),
    path('', include(router.urls)),
]