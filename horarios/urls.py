# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('define_horario/', views.define_horario),
    path('horario_ge/', views.horario_ge),
    path('horario_subentidad/', views.horario_subentidad),
    path('horario_aulas/', views.horario_aulas),
    path('horarios_ajax/', views.horarios_ajax),
    path('carga_masiva_horarios/', views.carga_masiva_horarios),
    path('actividades_horarios/', views.actividades_horarios),
    path('guardias_horario/', views.guardias_horario),
    path('guardias_ajax/', views.guardias_ajax),
    path('actillas/', views.actillas),
    path('alumnos_horarios/', views.alumnos_horarios),
    path('alumnos_horarios_ajax/', views.alumnos_horarios_ajax),
    path('seguimiento_educativo/', views.seguimiento_educativo),
]