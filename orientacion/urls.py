from django.urls import path

from . import views

app_name = 'orientacion'

urlpatterns = [
    path('', views.inicio, name='inicio'),
]
