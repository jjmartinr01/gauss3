# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^ge2ge/$', views.ge2ge,  name='ge2ge'),
]
