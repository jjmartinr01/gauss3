# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^viviendas/$', views.viviendas, name='viviendas'),
    url(r'^ajax_viviendas/$', views.ajax_viviendas, name='ajax_viviendas'),
    url(r'^reservas_vut/$', views.reservas_vut, name='reservas_vut'),
    url(r'^ajax_reservas_vut/$', views.ajax_reservas_vut, name='ajax_reservas_vut'),
    url(r'^viajeros/$', views.viajeros, name='viajeros'),
    url(r'^contabilidad_vut/$', views.contabilidad_vut, name='contabilidad_vut'),
    url(r'^ajax_contabilidad_vut/$', views.ajax_contabilidad_vut, name='ajax_contabilidad_vut'),
    url(r'^domotica_vut/$', views.domotica_vut, name='domotica_vut'),
    url(r'^ajax_domotica_vut/$', views.ajax_domotica_vut, name='ajax_domotica_vut'),
    url(r'^viviendas_registradas_vut/$', views.viviendas_registradas_vut, name='viviendas_registradas_vut'),
    url(r'^registro_viajero_manual/$', views.registro_viajero_manual, name='registro_viajero_manual'),
]
