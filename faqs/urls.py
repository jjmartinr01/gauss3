# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^configura_faqs/$', views.configura_faqs, name='configura_faqs'),
    url(r'^faqs_gauss/$', views.faqs_gauss, name='faqs_gauss'),
    url(r'^faqs_entidad/$', views.faqs_entidad, name='faqs_entidad'),
]
