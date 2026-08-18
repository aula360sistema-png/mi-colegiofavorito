from django.urls import path
from . import views

app_name = 'tutores'

urlpatterns = [
    path('', views.tutor_list, name='tutor_list'),
    path('inicio/', views.tutor_inicio, name='tutor_inicio'),
    path('inicio/estudiante/<int:estudiante_id>/', views.tutor_estudiante_detalle, name='tutor_estudiante'),
    path('nuevo/', views.tutor_create, name='tutor_create'),
    path('inicio/solicitudes/', views.tutor_solicitudes, name='tutor_solicitudes'),
    path(
        'inicio/historial-clinico/',
        views.tutor_historial_clinico,
        name='tutor_historial_clinico'
    ),
    path('<int:pk>/', views.tutor_detail, name='tutor_detail'),
    path('<int:pk>/editar/', views.tutor_update, name='tutor_update'),
    path('<int:pk>/eliminar/', views.tutor_delete, name='tutor_delete'),
]
