from django.urls import path

from core import views
from .views import home,  seleccionar_centro, dashboard, centro_list, centro_create, centro_update, centro_delete
app_name = 'core'
urlpatterns = [
    path('', home, name='home'),
        path('seleccionar-centro/', seleccionar_centro, name='seleccionar_centro'),
path('dashboard/', dashboard, name='dashboard'),


    # =========================
    # CRUD CENTROS EDUCATIVOS
    # =========================

    path(
        'centros/',
        centro_list,
        name='centro_list'
    ),

    path(
        'centros/crear/',
        centro_create,
        name='centro_create'
    ),

    path(
        'centros/<int:pk>/editar/',
        centro_update,
        name='centro_update'
    ),

    path(
        'centros/<int:pk>/eliminar/',
        centro_delete,
        name='centro_delete'
    ),
path(
    'configuracion-centro/',
    views.configuracion_centro,
    name='configuracion_centro'
),
]





#from django.urls import path
#from .views import home, seleccionar_centro, dashboard_docente, dashboard_admin, estudiante_inicio

#urlpatterns = [
  #  path('', home, name='home'),                        # Home router
  #  path('seleccionar-centro/', seleccionar_centro, name='seleccionar_centro'),
   # path('dashboard-docente/', dashboard_docente, name='dashboard_docente'),
  #  path('dashboard-admin/', dashboard_admin, name='dashboard_admin'),
  #  path('estudiante/', estudiante_inicio, name='estudiante_inicio'),
#]
