"""
URL configuration for mycolegiofavorito project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import include
from django.shortcuts import redirect
from django.conf.urls import handler404



urlpatterns = [

    path('admin/', admin.site.urls),
    path('docentes/', include('docentes.urls')),
    path('', include(('core.urls', 'core'), namespace='core')),
    path('estudiantes/', include('estudiantes.urls')),
    path('academico/', include('academico.urls')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),  # aquí
    path('administracion/', include('administracion.urls', namespace='administracion')),
     path('ia/', include('ia.urls')),
    path('nomina/', include('nomina.urls', namespace='nomina')),
    path('asistencia/', include('asistencia.urls', namespace='asistencia')),
    path('caja/', include('caja.urls', namespace='caja')),

]

handler404 = 'core.views.custom_404_view'