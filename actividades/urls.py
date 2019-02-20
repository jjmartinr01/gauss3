# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^gestionar_actividades/$', views.gestionar_actividades, name='gestionar_actividades'),
    url(r'^ajax_actividades/$', views.ajax_actividades, name='ajax_actividades'),
    url(r'^actividades_xml/$', views.actividades_xml, name='actividades_xml'),
    url(r'^actividades_json/$', views.actividades_json, name='actividades_json'),
    url(r'^actividades2slides/$', views.actividades2slides, name='actividades2slides'),
    # url(r'^create_vevents/$', views.create_vevents, name='create_vevents'),
]