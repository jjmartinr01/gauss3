# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('informes_seguimiento/', views.informes_seguimiento),
    path('ajax_informe_seguimiento/', views.ajax_informe_seguimiento),
    path('informes_tareas/', views.informes_tareas),
    path('ajax_informe_tareas/', views.ajax_informe_tareas),
]
