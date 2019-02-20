# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^registro/$$', views.registro, name='registro'),
    url(r'^ajax_registros/$', views.ajax_registros, name='ajax_registros'),
]
