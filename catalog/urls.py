from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.discovery_home, name='discovery'),
    path('add/', views.add_entry, name='add_entry'),
    path('<int:pk>/', views.detail, name='detail'),
    path('search/', views.search_works, name='search'),
    path('select/<str:media_type>/<str:external_id>/', views.select_work, name='select_work'),
    path('artist/<int:pk>/', views.artist_detail, name='artist_detail'),
]