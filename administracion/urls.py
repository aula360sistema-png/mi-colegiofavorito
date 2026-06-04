from django import views
from django.urls import path
from .views import administrativo_create,  imprimir_boletin_acta, dashboard_admin, generar_boletines, lista_boletines, listado_personal, mantenimiento_home, seguimiento_estudiante, seguimiento_estudiantes, ver_boletin_estudiante

app_name = 'administracion'

urlpatterns = [
    path('dashboard/', dashboard_admin, name='dashboard_admin'),
    path('crear-administrativo/', administrativo_create, name='administrativo_create'),
    path('personal/', listado_personal, name='listado_personal'),
    path('mantenimiento/', mantenimiento_home, name='mantenimiento'),
        path(
        'boletines/generar/',
        generar_boletines,
        name='generar_boletines'
    ),

      path(
        "boletines/",
       lista_boletines,
        name="lista_boletines"
    ),
    path(
        "boletines/<int:acta_id>/",
        ver_boletin_estudiante,
        name="ver_boletin"
    ),




    path(
        "seguimiento/estudiantes/",
        seguimiento_estudiantes,
        name="seguimiento_estudiantes"
    ),

    path(
        "seguimiento/estudiante/<int:estudiante_id>/",
        seguimiento_estudiante,
        name="seguimiento_estudiante"
    ),

     path(
        "boletines/imprimir/<int:acta_id>/",
        imprimir_boletin_acta,
        name="imprimir_boletin_acta"
    ),

    
]
