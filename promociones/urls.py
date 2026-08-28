from django.urls import path

from .views import (
    promociones_dashboard,
    promociones_recuperacion,
    promociones_extraordinario,
)

app_name = 'promociones'

urlpatterns = [
    path('', promociones_dashboard, name='dashboard'),
    path('recuperacion/', promociones_recuperacion, name='recuperacion'),
    path('extraordinario/', promociones_extraordinario, name='extraordinario'),
]
