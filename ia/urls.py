from django.urls import path
from .views import prueba_ia

urlpatterns = [
    path('prueba/', prueba_ia),
]