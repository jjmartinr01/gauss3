# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^crea_bancos/$', views.crea_bancos, name='crea_bancos'),
    url(r'^asocia_bancos/$', views.asocia_bancos, name='asocia_bancos'),
    url(r'^calc_iban/$', views.calc_iban, name='calc_iban'),
    url(r'^bancos_sin_bic/$', views.bancos_sin_bic, name='bancos_sin_bic'),
    url(r'^download_bancos/$', views.download_bancos, name='download_bancos'),
]
