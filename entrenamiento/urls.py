from django.urls import path

from . import views

app_name = 'entrenamiento'

urlpatterns = [
    path('', views.inicio, name='inicio'),
]
