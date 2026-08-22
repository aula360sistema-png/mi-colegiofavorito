from django.urls import path

from . import views

app_name = 'seguridad'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('consentimientos/', views.consentimiento_list, name='consentimiento_list'),
    path('consentimientos/nuevo/', views.consentimiento_create, name='consentimiento_create'),
    path('consentimientos/<int:pk>/', views.consentimiento_detail, name='consentimiento_detail'),
    path('consentimientos/<int:pk>/revocar/', views.consentimiento_revocar, name='consentimiento_revocar'),

    path('accesos/', views.registros_acceso, name='registros_acceso'),

    path('anonimizar/', views.anonymize_students, name='anonymize_students'),
]
