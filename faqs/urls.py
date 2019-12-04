# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^configura_federacion/$', views.configura_federacion, name='configura_federacion'),
    url(r'^ajax_configura_federacion/$', views.ajax_configura_federacion, name='ajax_configura_federacion'),
    url(r'^cuotas_federacion/$', views.cuotas_federacion, name='cuotas_federacion'),
    url(r'^ajax_cuotas_federacion/$', views.ajax_cuotas_federacion, name='ajax_cuotas_federacion'),
    url(r'^documentos_federacion/$', views.documentos_federacion, name='documentos_federacion'),
    url(r'^ajax_documentos_federacion/$', views.ajax_documentos_federacion, name='ajax_documentos_federacion'),
    url(r'^inscribir_federacion/$', views.inscribir_federacion, name='inscribir_federacion'),
]
