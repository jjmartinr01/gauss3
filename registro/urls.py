# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro),
    path('ajax_registros/', views.ajax_registros),
]
