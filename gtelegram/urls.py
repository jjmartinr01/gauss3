# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^166888701:AAFMSZgh9GEL59mmOH_Gv91aibU5b-Eg13Q/$', views.telegram_webhook, name='telegram_webhook'),
    url(r'^gtelegram_ajax/$', views.gtelegram_ajax, name='gtelegram_ajax'),
]
