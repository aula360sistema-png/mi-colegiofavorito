from django.urls import path
from .views import (
    login_view,
    logout_view,
    crear_miembro,
    cambiar_contrasena,
    verificar_2fa,
    configurar_2fa,
    gestionar_2fa,
    mi_perfil,
)

app_name = 'usuarios'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('crear/', crear_miembro, name='crear_miembro'),
    path('password/', cambiar_contrasena, name='cambiar_contrasena'),
    path('perfil/', mi_perfil, name='mi_perfil'),
    path('verificar-2fa/', verificar_2fa, name='verificar_2fa'),
    path('configurar-2fa/', configurar_2fa, name='configurar_2fa'),
    path('gestionar-2fa/', gestionar_2fa, name='gestionar_2fa'),

]
