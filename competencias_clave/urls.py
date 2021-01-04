# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('cc_valorar_mis_alumnos/', views.cc_valorar_mis_alumnos),
    path('cc_valorar_cualquier_alumno/', views.cc_valorar_cualquier_alumno),
    path('cc_configuracion/', views.cc_configuracion),
]
