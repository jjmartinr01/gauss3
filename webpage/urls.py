# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^inicioweb/$', views.inicioweb, name='inicioweb'),
    url(r'^avisolegal/$', views.avisolegal, name='avisolegal'),
    url(r'^privacidad/$', views.privacidad, name='privacidad'),
    url(r'^condiciones/$', views.condiciones, name='condiciones'),
]
