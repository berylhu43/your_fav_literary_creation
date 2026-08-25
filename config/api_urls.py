from rest_framework.authtoken.views import obtain_auth_token
from reviews.api_views import ReviewListAPI
from django.urls import path

urlpatterns = [
    path('token/', obtain_auth_token, name='api_token'),
    path('reviews/', ReviewListAPI.as_view(), name='api_reviews'),
]