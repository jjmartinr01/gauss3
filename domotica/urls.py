# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^grupos_domotica/$', views.grupos_domotica, name='grupos_domotica'),
    url(r'^ajax_grupos_domotica/$', views.ajax_grupos_domotica, name='ajax_grupos_domotica'),
    url(r'^configura_domotica/$', views.configura_domotica, name='configura_domotica'),
    url(r'^ajax_configura_domotica/$', views.ajax_configura_domotica, name='ajax_configura_domotica'),
]
