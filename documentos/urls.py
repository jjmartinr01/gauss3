# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^documentos/$', views.documentos, name='documentos'),
    url(r'^documentos_ajax/$', views.documentos_ajax, name='documentos_ajax'),
    url(r'^contrato_gauss/$', views.contrato_gauss, name='contrato_gauss'),
]
