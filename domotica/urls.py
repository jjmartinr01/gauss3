# -*- coding: utf-8 -*-
from django.urls import path
from . import views

urlpatterns = [
    path('grupos_domotica/', views.grupos_domotica),
    path('ajax_grupos_domotica/', views.ajax_grupos_domotica),
    path('configura_domotica/', views.configura_domotica),
    path('ajax_configura_domotica/', views.ajax_configura_domotica),
    path('lnk/', views.lnk),
    path('dispositivos/', views.dispositivos),
]