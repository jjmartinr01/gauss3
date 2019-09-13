# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^moscosos/$$', views.moscosos, name='moscosos'),
    url(r'^ajax_moscosos/$', views.ajax_moscosos, name='ajax_moscosos'),
]
