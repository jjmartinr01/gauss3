# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('cupo/', views.cupo),
    path('ajax_cupo/', views.ajax_cupo),
    path('edit_cupo/<int:cupo_id>/', views.edit_cupo),
    path('plantilla_organica/', views.plantilla_organica),
    path('comprueba_dnis/', views.comprueba_dnis),
    path('arregla_duplicados/', views.arregla_duplicados),
    # path('select_po/', views.select_po),
    path('rrhh_cupos/', views.rrhh_cupos),
]
