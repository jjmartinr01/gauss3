# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^define_horario/$', views.define_horario, name='define_horario'),
    # url(r'^define_curso/$', views.define_curso, name='define_curso'),
    # url(r'^define_grupo/$', views.define_grupo, name='define_grupo'),
    # url(r'^define_materia/$', views.define_materia, name='define_materia'),
    url(r'^horario_ge/$', views.horario_ge, name='horario_ge'),
    url(r'^horario_subentidad/$', views.horario_subentidad, name='horario_subentidad'),
    url(r'^horario_aulas/$', views.horario_aulas, name='horario_aulas'),
    url(r'^horarios_ajax/$', views.horarios_ajax, name='horarios_ajax'),
    url(r'^carga_masiva_horarios/$', views.carga_masiva_horarios, name='carga_masiva_horarios'),
    url(r'^actividades_horarios/$', views.actividades_horarios, name='actividades_horarios'),
    url(r'^guardias_horario/$', views.guardias_horario, name='guardias_horario'),
    url(r'^guardias_ajax/$', views.guardias_ajax, name='guardias_ajax'),
    url(r'^actillas/$', views.actillas, name='actillas'),
    url(r'^alumnos_horarios/$', views.alumnos_horarios, name='alumnos_horarios'),
    url(r'^alumnos_horarios_ajax/$', views.alumnos_horarios_ajax, name='alumnos_horarios_ajax'),
]
