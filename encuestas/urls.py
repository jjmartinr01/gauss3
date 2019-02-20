# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^configurar_encuestas/$', views.configurar_encuestas, name='configurar_encuestas'),
    # url(r'^ajax_cupo/$', views.ajax_cupo, name='ajax_cupo'),
    # url(r'^edit_cupo/(?P<cupo_id>[0-9]+)/$', views.edit_cupo, name='edit_cupo'),
]
