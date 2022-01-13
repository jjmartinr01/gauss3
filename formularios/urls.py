# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('formularios/', views.formularios),
    path('mis_formularios/', views.mis_formularios),
    path('rellena_gform/<int:id>/<str:identificador>/', views.rellena_gform),
    path('rellena_gform/<int:id>/<str:identificador>/<str:gfr_identificador>/', views.rellena_gform),
    path('ver_gform/<int:id>/<str:identificador>/', views.ver_gform),
    path('ver_resultados/<int:id>/<str:identificador>/', views.ver_resultados),
    path('formularios_disponibles/', views.formularios_disponibles),
    path('carga_cuestionarios_funcionario_practicas/', views.carga_cuestionarios_funcionario_practicas),
    path('procesos_evaluacion_funcpract/', views.procesos_evaluacion_funcpract),
    path('recufunprac/<int:id>/<str:actor>/', views.recufunprac),
    path('mis_evalpract/', views.mis_evalpract),
    path('mis_respuestas/<int:id>/<str:identificador>/<str:gfr_identificador>/', views.mis_respuestas),
]
