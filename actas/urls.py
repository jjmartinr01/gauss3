# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^configurar_convocatorias/$', views.configurar_convocatorias, name='configurar_convocatorias'),
    url(r'^configurar_convocatorias_ajax/$', views.configurar_convocatorias_ajax, name='configurar_convocatorias_ajax'),
    url(r'^convocatorias/$', views.convocatorias, name='convocatorias'),
    url(r'^convocatorias_ajax/$', views.convocatorias_ajax, name='convocatorias_ajax'),
    url(r'^redactar_actas/$', views.redactar_actas, name='redactar_actas'),
    url(r'^redactar_actas_ajax/$', views.redactar_actas_ajax, name='redactar_actas_ajax'),
    url(r'^ver_actas/$', views.ver_actas, name='ver_actas'),
    url(r'^ver_actas_ajax/$', views.ver_actas_ajax, name='ver_actas_ajax'),
    # url(r'^actualiza_texto_acta/$', views.actualiza_texto_acta, name='actualiza_texto_acta'),
    url(r'^ajax_actas/$', views.ajax_actas, name='ajax_actas'),
]
