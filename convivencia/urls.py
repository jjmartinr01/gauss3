# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('gestionar_conductas/', views.gestionar_conductas),
    path('gestionar_conductas_ajax/', views.gestionar_conductas_ajax),
    path('sancionar_conductas/', views.sancionar_conductas),
    path('sancionar_conductas_ajax/', views.sancionar_conductas_ajax),
    path('expediente_sancionador/', views.expediente_sancionador),
]