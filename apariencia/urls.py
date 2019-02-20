# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^apariencia/$', views.apariencia, name='apariencia'),
    url(r'^actualizar_apariencias/$', views.actualizar_apariencias, name='actualizar_apariencias'),
]
