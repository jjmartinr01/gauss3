# -*- coding: utf-8 -*-
# from django.conf.urls import url
from django.urls import path
from . import views

urlpatterns = [
    path('viviendas/', views.viviendas),
    path('ajax_viviendas/', views.ajax_viviendas),
    path('reservas_vut/', views.reservas_vut),
    path('ajax_reservas_vut/', views.ajax_reservas_vut),
    path('viajeros/', views.viajeros),
    path('contabilidad_vut/', views.contabilidad_vut),
    path('ajax_contabilidad_vut/', views.ajax_contabilidad_vut),
    path('domotica_vut/', views.domotica_vut),
    path('ajax_domotica_vut/', views.ajax_domotica_vut),
    path('viviendas_registradas_vut/', views.viviendas_registradas_vut),
    path('registro_viajero_manual/', views.registro_viajero_manual),
    path('web_vut/', views.web_vut),
    path('web_vut_id/<int:vivienda_id>/', views.web_vut_id),
    path('reserva_vut_crea_recibo/<int:reserva_id>/', views.reserva_vut_crea_recibo),
    # path('web_vut_id/', views.web_vut_id),
]

# urlpatterns = [
#     url(r'^viviendas/$', views.viviendas, name='viviendas'),
#     url(r'^ajax_viviendas/$', views.ajax_viviendas, name='ajax_viviendas'),
#     url(r'^reservas_vut/$', views.reservas_vut, name='reservas_vut'),
#     url(r'^ajax_reservas_vut/$', views.ajax_reservas_vut, name='ajax_reservas_vut'),
#     url(r'^viajeros/$', views.viajeros, name='viajeros'),
#     url(r'^contabilidad_vut/$', views.contabilidad_vut, name='contabilidad_vut'),
#     url(r'^ajax_contabilidad_vut/$', views.ajax_contabilidad_vut, name='ajax_contabilidad_vut'),
#     url(r'^domotica_vut/$', views.domotica_vut, name='domotica_vut'),
#     url(r'^ajax_domotica_vut/$', views.ajax_domotica_vut, name='ajax_domotica_vut'),
#     url(r'^viviendas_registradas_vut/$', views.viviendas_registradas_vut, name='viviendas_registradas_vut'),
#     url(r'^registro_viajero_manual/$', views.registro_viajero_manual, name='registro_viajero_manual'),
#     url(r'^web_vut/$', views.web_vut, name='web_vut'),
#     url(r'^web_vut_id/<int:vivienda_id>/$', views.web_vut_id, name='web_vut_id'),
#     # url(r'^web_vut_id/$', views.web_vut_id, name='web_vut_id'),
# ]
