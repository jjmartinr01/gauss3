# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('gestionar_reparaciones/', views.gestionar_reparaciones),
    path('gestionar_reparaciones_ajax/', views.gestionar_reparaciones_ajax),
]
