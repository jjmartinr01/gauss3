# -*- coding: utf-8 -*-

from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^configurar_convocatorias/$', views.configurar_convocatorias, name='configurar_convocatorias'),
    re_path(r'^configurar_convocatorias_ajax/$', views.configurar_convocatorias_ajax, name='configurar_convocatorias_ajax'),
    re_path(r'^convocatorias/$', views.convocatorias, name='convocatorias'),
    re_path(r'^convocatorias_ajax/$', views.convocatorias_ajax, name='convocatorias_ajax'),
    re_path(r'^redactar_actas/$', views.redactar_actas, name='redactar_actas'),
    re_path(r'^redactar_actas_ajax/$', views.redactar_actas_ajax, name='redactar_actas_ajax'),
    re_path(r'^ver_actas/$', views.ver_actas, name='ver_actas'),
    re_path(r'^ver_actas_ajax/$', views.ver_actas_ajax, name='ver_actas_ajax'),
    # url(r'^actualiza_texto_acta/$', views.actualiza_texto_acta, name='actualiza_texto_acta'),
    re_path(r'^ajax_actas/$', views.ajax_actas, name='ajax_actas'),
]
