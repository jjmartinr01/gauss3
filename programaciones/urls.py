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
    
    
    path('programaciones_didacticas/', views.programaciones_didacticas),                         # Index get
    path('programacion_didactica/<int:id>/<str:identificador>/', views.programacion_didactica),  # Show get
    
    path('programacion_didactica_ajax/', views.programacion_didactica_ajax),        # Llamadas ajax
    path('progsecundaria_sb/<int:id>/', views.progsecundaria_sb),
    
    path('cuadernosdocentes/', views.cuadernosdocentes),        # Index get
    path('cuadernodocente/', views.cuadernodocente),            # Post ajax
    path('cuadernodocente/<int:id>/', views.cuadernodocente),   # Show get
    
    
    path('verprogramacion/<str:secret>/<int:id>/', views.verprogramacion),
    path('verprogramaciones/<str:secret>/curso/<str:curso>/', views.verprogramaciones),
    path('verprogramaciones/<str:secret>/', views.verprogramaciones),
    path('repositorio_sap/', views.repositorio_sap),
    path('repoescalacp/', views.repoescalacp),
    path('calificacc/', views.calificacc),
    path('crea_calalumce_cev/', views.crea_calalumce_cev),
    path('arregla_instrevals/', views.arregla_instrevals),
    path('estadistica_prog/', views.estadistica_prog),
    path('estadisticas_curso/<str:anno>/', views.estadisticas_curso),
    path('arregla_cuaderno/<int:cuaderno_id>/<int:max_cal>/', views.arregla_cuaderno),
    path('arregla_cuaderno2/<int:cuaderno_id>/<int:max_cal>/', views.arregla_cuaderno2),
    path('arregla_cuaderno3/<int:cuaderno_id>/<int:max_cal>/', views.arregla_cuaderno3),
    path('calificacc_all/<int:grupo_id>/', views.calificacc_all),
]
