# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^cc_valorar_mis_alumnos/$', views.cc_valorar_mis_alumnos, name='cc_valorar_mis_alumnos'),
    url(r'^cc_valorar_cualquier_alumno/$', views.cc_valorar_cualquier_alumno, name='cc_valorar_cualquier_alumno'),
    url(r'^cc_configuracion/$', views.cc_configuracion, name='cc_configuracion'),
]
