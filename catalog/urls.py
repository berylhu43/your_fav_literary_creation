from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.catalog_list, name='list'),
    path('add/', views.add_entry, name='add_entry'),
    path('<int:pk>/', views.detail, name='detail'),
]