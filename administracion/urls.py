from django import views
from django.urls import path
from .views import administrativo_create, imprimir_boletin_acta, cerrar_completivo, cerrar_extraordinario, dashboard_admin, generar_boletines, lista_boletines, listado_personal, mantenimiento_home, reportes, seguimiento_estudiante, seguimiento_estudiantes, ver_boletin_estudiante, promociones_dashboard, promociones_recuperacion, promociones_extraordinario

app_name = 'administracion'

urlpatterns = [
    path('dashboard/', dashboard_admin, name='dashboard_admin'),
    path('crear-administrativo/', administrativo_create, name='administrativo_create'),
    path('personal/', listado_personal, name='listado_personal'),
    path('mantenimiento/', mantenimiento_home, name='mantenimiento'),
    path('reportes/', reportes, name='reportes'),
        path(
        'boletines/generar/',
        generar_boletines,
        name='generar_boletines'
    ),
    path(
        'boletines/cerrar-completivo/',
        cerrar_completivo,
        name='cerrar_completivo'
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

    path(
        'promociones/',
        promociones_dashboard,
        name='promociones_dashboard'
    ),
    path(
        'promociones/recuperacion/',
        promociones_recuperacion,
        name='promociones_recuperacion'
    ),
    path(
        'promociones/extraordinario/',
        promociones_extraordinario,
        name='promociones_extraordinario'
    ),
    path(
        'boletines/cerrar-extraordinario/',
        cerrar_extraordinario,
        name='cerrar_extraordinario'
    ),
]
