# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('configurar_encuestas/', views.configurar_encuestas),
]
