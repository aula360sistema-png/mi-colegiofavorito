from django.urls import path

from . import views

app_name = 'automatizaciones'

urlpatterns = [
    path('alertas/', views.tablero, name='tablero'),
    path('alertas/campania/', views.crear_campania, name='crear_campania'),
]