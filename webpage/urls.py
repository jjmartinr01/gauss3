# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^inicioweb/$', views.inicioweb, name='inicioweb'),
    # url(r'^inicioweb/$', views.inicioweb, name='inicioweb'),
]
