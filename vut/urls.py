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
    path('rvpd/<str:secret_id>/', views.rvpd),
    path('contratos_vut/', views.contratos_vut),
    path('firconvut/<str:secret_id>/<str:n>/', views.firconvut),
    # path('web_vut_id/', views.web_vut_id),
]
