from django.urls import path
from django.shortcuts import render
from . import views

app_name = 'dashboard'

# Minimal dashboard view for root
def index(request):
    return render(request, 'dashboard_index.html')

urlpatterns = [
    path('', views.index, name='dashboard'),
    path('full/', views.index, name='full_dashboard'),
]
