from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from .api_views import RegisterAPI, LogoutAPI

urlpatterns = [
    path('token/', obtain_auth_token, name='api_token'),
    path('register/', RegisterAPI.as_view(), name='api_register'),
    path('logout/', LogoutAPI.as_view(), name='api_logout'),
]