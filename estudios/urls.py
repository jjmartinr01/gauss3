# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('configura_cursos/', views.configura_cursos),
    path('departamentos_didacticos/', views.departamentos_didacticos),
    path('configura_grupos/', views.configura_grupos),
    path('evaluar_materias/', views.evaluar_materias),
    path('configura_materias_pendientes/', views.configura_materias_pendientes),
    path('configura_competencias/', views.configura_competencias),
    path('asignaturas_centro/', views.asignaturas_centro),
]