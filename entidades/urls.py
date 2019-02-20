# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^datos_entidad/$', views.datos_entidad, name='datos_entidad'),
    # url(r'^g_e_To_g_e2/$', views.g_e_To_g_e,  name='g_e_To_g_e2'),
    url(r'^voluntarios/$', views.usuarios_entidad, name='usuarios_entidad'),
    url(r'^madres_padres/$', views.usuarios_entidad, name='usuarios_entidad'),
    url(r'^usuarios_entidad/$', views.usuarios_entidad, name='usuarios_entidad'),
    url(r'^usuarios_entidad_ajax/$', views.usuarios_entidad_ajax, name='usuarios_entidad_ajax'),
    url(r'^listados_usuarios/$', views.listados_usuarios, name='listados_usuarios'),
    url(r'^ajax_filtro/$', views.ajax_filtro, name='ajax_filtro'),
    url(r'^ajax_entidades/$', views.ajax_entidades, name='ajax_entidades'),
    url(r'^mis_datos/$', views.mis_datos, name='mis_datos'),
    url(r'^mis_datos_ajax/$', views.mis_datos_ajax, name='mis_datos_ajax'),
    url(r'^add_usuario/$', views.add_usuario, name='add_usuario'),
    url(r'^reserva_plazas/$', views.reserva_plazas, name='reserva_plazas'),
    url(r'^bajas_usuarios/$', views.bajas_usuarios, name='bajas_usuarios'),
    url(r'^organigrama/$', views.organigrama, name='organigrama'),
    url(r'^subentidades/$', views.subentidades, name='subentidades'),
    url(r'^subentidades_ajax/$', views.subentidades_ajax, name='subentidades_ajax'),
    url(r'^buscar_asociados/$', views.buscar_asociados, name='buscar_asociados'),
    url(r'^buscar_usuarios/$', views.buscar_usuarios, name='buscar_usuarios'),
    url(r'^crea_entidad/$', views.crea_entidad, name='crea_entidad'),
    url(r'^listados_usuarios_entidad/$', views.listados_usuarios_entidad, name='listados_usuarios_entidad'),
    # url(r'^identificadores_entidad/$', views.identificadores_entidad, name='identificadores_entidad'),
    # url(r'^cargos_perfiles_entidad/$', views.cargos_perfiles_entidad, name='cargos_perfiles_entidad'),
    # url(r'^secciones_entidad/$', views.secciones_entidad, name='secciones_entidad'),
    url(r'^dependencias_entidad/$', views.dependencias_entidad, name='dependencias_entidad'),
    url(r'^rondas_entidad/$', views.rondas_entidad, name='rondas_entidad'),
    url(r'^tutores_entidad/$', views.tutores_entidad, name='tutores_entidad'),
    url(r'^configura_rondas/$', views.configura_rondas, name='configura_rondas'),
    url(r'^formulario_ext_reserva_plaza/$', views.formulario_ext_reserva_plaza, name='formulario_ext_reserva_plaza'),
    # url(r'^load_gauser_extra_educa/$', views.load_gauser_extra_educa, name='load_gauser_extra_educa'),
]
