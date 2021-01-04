# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('apariencia/', views.apariencia),
    path('actualizar_apariencias/', views.actualizar_apariencias),
]