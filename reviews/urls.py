from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('', views.my_records, name='my_records'),
    path('add/<int:pk>/', views.add_record, name='add_record'),
    path('<int:pk>/edit/', views.change_record, name='change_record'),
    path('<int:pk>/delete/', views.delete_record, name='delete_record'),
]