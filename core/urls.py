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

path(
    'configuracion-centro/test-correo/',
    views.test_correo,
    name='test_correo'
),

    # =========================
    # PERMISOS POR PAGINA
    # =========================

    path(
        'permisos/',
        views.permiso_pagina_list,
        name='permiso_pagina_list'
    ),
    path(
        'permisos/crear/',
        views.permiso_pagina_create,
        name='permiso_pagina_create'
    ),
    path(
        'permisos/<int:pk>/editar/',
        views.permiso_pagina_update,
        name='permiso_pagina_update'
    ),
    path(
        'permisos/<int:pk>/eliminar/',
        views.permiso_pagina_delete,
        name='permiso_pagina_delete'
    ),

    # =========================
    # TEMA / APARIENCIA
    # =========================

    path(
        'tema/',
        views.tema_centro,
        name='tema_centro'
    ),
    path(
        'tema/preview/',
        views.tema_centro_preview,
        name='tema_centro_preview'
    ),

    # =========================
    # LOGO DEL CENTRO
    # =========================

path(
    'logo/',
    views.logo_centro,
    name='logo_centro'
),

    # =========================
    # MINI TARJETA DE PERSONA (popover al pasar el mouse)
    # =========================

    path(
        'ajax/persona-card/',
        views.persona_card_ajax,
        name='persona_card_ajax'
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
