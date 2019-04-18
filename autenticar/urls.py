# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^accounts/login/$', views.no_login, name='no_login'),
    url(r'^enlazar/$', views.enlazar, name='enlazar'),
    url(r'^$', views.index, name='index'),
    url(r'^perfiles_permisos/$', views.perfiles_permisos, name='perfiles_permisos'),
    url(r'^politica_privacidad/$', views.politica_privacidad, name='politica_privacidad'),
    url(r'^aviso_legal/$', views.aviso_legal, name='aviso_legal'),
    url(r'^carga_masiva/$', views.carga_masiva, name='carga_masiva'),
    url(r'^del_entidad_gausers/$', views.del_entidad_gausers, name='del_entidad_gausers'),
    url(r'^recupera_password/$', views.recupera_password, name='recupera_password'),
    url(r'^recarga_captcha/$', views.recarga_captcha, name='recarga_captcha'),
    url(r'^asignar_menus_entidad/$', views.asignar_menus_entidad, name='asignar_menus_entidad'),
    url(r'^actualizar_menus_permisos/$', views.actualizar_menus_permisos, name='actualizar_menus_permisos'),
    url(r'^execute_migrations/$', views.execute_migrations, name='execute_migrations'),
    # url(r'^load_gauser_educa/$', views.load_gauser_educa, name='load_gauser_educa'),
    # url(r'^gestionar_candidatos/$', views.gestionar_candidatos, name='gestionar_candidatos'),
]
