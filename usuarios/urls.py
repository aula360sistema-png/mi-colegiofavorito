from django.urls import path
from .views import login_view, logout_view, crear_miembro
from django.contrib.auth.views import LogoutView

app_name = 'usuarios'

urlpatterns = [
   path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('crear/', crear_miembro, name='crear_miembro'),


]
