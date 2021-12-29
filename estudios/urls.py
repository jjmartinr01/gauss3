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
]

# url(r'^titulos/$', views.titulos, name='titulos'),
# url(r'^editar_programacion/$', views.editar_programacion, name='editar_programacion'),
# url(r'^programaciones/$', views.programaciones, name='programaciones'),
# url(r'^ajax_programaciones/$', views.ajax_programaciones, name='ajax_programaciones'),
# url(r'^objetivos_criterios/$', views.objetivos_criterios, name='objetivos_criterios'),
# url(r'^copiar_programacion/$', views.copiar_programacion, name='copiar_programacion'),
# url(r'^resultados_aprendizaje/$', views.resultados_aprendizaje, name='resultados_aprendizaje'),
# url(r'^generar_datos/$', views.generar_datos, name='generar_datos'),
# url(r'^ajax_objetivos_criterios/$', views.ajax_objetivos_criterios, name='ajax_objetivos_criterios'),
# url(r'^resultados_aprendizaje/$', views.resultados_aprendizaje, name='resultados_aprendizaje'),
# url(r'^define_curso/$', views.define_curso, name='define_curso'),
# url(r'^define_materia/$', views.define_materia, name='define_materia'),
