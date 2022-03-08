# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('titulos/', views.titulos),
    path('editar_programacion/', views.editar_programacion),
    path('programaciones/', views.programaciones),
    path('ajax_programaciones/', views.ajax_programaciones),
    path('objetivos_criterios/', views.objetivos_criterios),
    path('copiar_programacion/', views.copiar_programacion),
    path('departamentos_centro_educativo/', views.departamentos_centro_educativo),
    path('departamentos_centro_educativo_ajax/', views.departamentos_centro_educativo_ajax),
    path('generar_datos/', views.generar_datos),
    path('ajax_objetivos_criterios/', views.ajax_objetivos_criterios),
    path('resultados_aprendizaje/', views.resultados_aprendizaje),
    path('cuerpos_funcionarios_entidad/', views.cuerpos_funcionarios_entidad),
    path('cargar_programaciones/', views.cargar_programaciones),
    path('cargar_programaciones_ajax/', views.cargar_programaciones_ajax),
    path('profesores_centro_educativo/', views.profesores_centro_educativo),
    path('aspectos_pga/', views.aspectos_pga),
    path('proyecto_educativo_centro/', views.proyecto_educativo_centro),
    path('pecjson/<int:code>/', views.pecjson),
    path('pgajson/<int:code>/', views.pgajson),
    path('progsecundaria/', views.progsecundaria),
path('progsecundaria_sb/<int:id>/', views.progsecundaria_sb),
path('cuadernodocente/', views.cuadernodocente),
# path('cuaderno_full_screen/<int:id>/', views.cuaderno_full_screen),
]
