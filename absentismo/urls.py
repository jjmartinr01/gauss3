# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^gestionar_absentismo/$', views.gestionar_absentismo, name='gestionar_absentismo'),
    url(r'^ajax_absentismo/$', views.ajax_absentismo, name='ajax_absentismo'),
]
