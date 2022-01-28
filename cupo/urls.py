# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('cupo/', views.cupo),
    path('ajax_cupo/', views.ajax_cupo),
    path('edit_cupo/<int:cupo_id>/', views.edit_cupo),
    path('plantilla_organica/', views.plantilla_organica),
path('comprueba_dnis/', views.comprueba_dnis),
]