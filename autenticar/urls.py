# -*- coding: utf-8 -*-

from django.urls import path
# import django_cas_ng.views
from . import views

urlpatterns = [
    path('', views.index),
    path('accounts/login/', views.no_login),
    path('enlazar/', views.enlazar),
    path('perfiles_permisos/', views.perfiles_permisos),
    path('politica_privacidad/', views.politica_privacidad),
    path('aviso_legal/', views.aviso_legal),
    path('carga_masiva/', views.carga_masiva),
    path('del_entidad_gausers/', views.del_entidad_gausers),
    path('recupera_password/', views.recupera_password),
    path('recarga_captcha/', views.recarga_captcha),
    path('asignar_menus_entidad/', views.asignar_menus_entidad),
    path('actualizar_menus_permisos/', views.actualizar_menus_permisos),
    path('borrar_entidades/', views.borrar_entidades),
    path('execute_migrations/', views.execute_migrations),
    path('ejecutar_query/', views.ejecutar_query),
    path('acceso_from_racima/<str:token>/', views.acceso_from_racima),
    # URLs para el login a través del CAS del Gobierno
    path('logincas/', views.logincas),
    # path('accounts/login', django_cas_ng.views.LoginView.as_view(), name='cas_ng_login'),
    # path('accounts/logout', django_cas_ng.views.LogoutView.as_view(), name='cas_ng_logout'),
]
