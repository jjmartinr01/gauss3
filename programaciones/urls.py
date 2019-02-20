# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^titulos/$', views.titulos, name='titulos'),
    url(r'^editar_programacion/$', views.editar_programacion, name='editar_programacion'),
    url(r'^programaciones/$', views.programaciones, name='programaciones'),
    url(r'^ajax_programaciones/$', views.ajax_programaciones, name='ajax_programaciones'),
    url(r'^objetivos_criterios/$', views.objetivos_criterios, name='objetivos_criterios'),
    url(r'^copiar_programacion/$', views.copiar_programacion, name='copiar_programacion'),
    url(r'^departamentos_centro_educativo/$', views.departamentos_centro_educativo,
        name='departamentos_centro_educativo'),
    url(r'^departamentos_centro_educativo_ajax/$', views.departamentos_centro_educativo_ajax,
        name='departamentos_centro_educativo_ajax'),
    url(r'^generar_datos/$', views.generar_datos, name='generar_datos'),
    url(r'^ajax_objetivos_criterios/$', views.ajax_objetivos_criterios, name='ajax_objetivos_criterios'),
    # url(r'^configura_cursos/$', views.configura_cursos, name='configura_cursos'),
    # url(r'^departamentos_didacticos/$', views.departamentos_didacticos, name='departamentos_didacticos'),
    url(r'^resultados_aprendizaje/$', views.resultados_aprendizaje, name='resultados_aprendizaje'),
    url(r'^cuerpos_funcionarios_entidad/$', views.cuerpos_funcionarios_entidad, name='cuerpos_funcionarios_entidad'),
    url(r'^cargar_programaciones/$', views.cargar_programaciones, name='cargar_programaciones'),
    url(r'^cargar_programaciones_ajax/$', views.cargar_programaciones_ajax, name='cargar_programaciones_ajax'),
    url(r'^profesores_centro_educativo/$', views.profesores_centro_educativo, name='profesores_centro_educativo'),
]
