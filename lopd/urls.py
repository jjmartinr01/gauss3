# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^responsables_lopd/$', views.responsables_lopd, name='responsables_lopd'),
    url(r'^documento_seguridad/$', views.documento_seguridad, name='documento_seguridad'),
    url(r'^derechos_arco/$', views.derechos_arco, name='derechos_arco'),
    url(r'^incidencias_lopd/$', views.incidencias_lopd, name='incidencias_lopd'),
    url(r'^inventario_soportes/$', views.inventario_soportes, name='inventario_soportes'),
    url(r'^confidencialidad/$', views.confidencialidad, name='confidencialidad'),
]
