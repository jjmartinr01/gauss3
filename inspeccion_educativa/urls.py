# -*- coding: utf-8 -*-

# from django.conf.urls import url
from django.urls import path
from . import views

urlpatterns = [
    path('tareas_ie/', views.tareas_ie),
    path('cargar_centros_mdb/', views.cargar_centros_mdb),
]