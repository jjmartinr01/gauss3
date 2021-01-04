# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('166888701:AAFMSZgh9GEL59mmOH_Gv91aibU5b-Eg13Q/', views.telegram_webhook),
    path('gtelegram_ajax/', views.gtelegram_ajax),
]
