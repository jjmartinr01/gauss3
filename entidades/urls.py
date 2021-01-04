# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('datos_entidad/', views.datos_entidad),
    path('voluntarios/', views.usuarios_entidad),
    path('madres_padres/', views.usuarios_entidad),
    path('usuarios_entidad/', views.usuarios_entidad),
    path('usuarios_entidad_ajax/', views.usuarios_entidad_ajax),
    path('listados_usuarios/', views.listados_usuarios),
    path('ajax_filtro/', views.ajax_filtro),
    path('ajax_entidades/', views.ajax_entidades),
    path('mis_datos/', views.mis_datos),
    path('mis_datos_ajax/', views.mis_datos_ajax),
    path('add_usuario/', views.add_usuario),
    path('reserva_plazas/', views.reserva_plazas),
    path('bajas_usuarios/', views.bajas_usuarios),
    path('organigrama/', views.organigrama),
    path('subentidades/', views.subentidades),
    path('subentidades_ajax/', views.subentidades_ajax),
    path('buscar_asociados/', views.buscar_asociados),
    path('buscar_usuarios/', views.buscar_usuarios),
    path('crea_entidad/', views.crea_entidad),
    path('listados_usuarios_entidad/', views.listados_usuarios_entidad),
    path('dependencias_entidad/', views.dependencias_entidad),
    path('rondas_entidad/', views.rondas_entidad),
    path('tutores_entidad/', views.tutores_entidad),
    path('configura_rondas/', views.configura_rondas),
    path('formulario_ext_reserva_plaza/', views.formulario_ext_reserva_plaza),
    path('configura_auto_id/', views.configura_auto_id),
    path('linkge/<str:code>/', views.linkge),
    path('crealinkge/', views.crealinkge),
    path('selectgcs/', views.selectgcs),
    path('selectgcs_organization/', views.selectgcs_organization),
    path('doc_configuration/', views.doc_configuration),
]
