# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('tareas_ie/', views.tareas_ie),
    path('cargar_centros_mdb/', views.cargar_centros_mdb),
    path('informes_ie/', views.informes_ie),
    path('plantillas_ie/', views.plantillas_ie),
    path('asignar_centros_inspector/', views.asignar_centros_inspector),
    # path('carga_actuaciones_ie/', views.carga_actuaciones_ie),
    path('carga_masiva_inspeccion/', views.carga_masiva_inspeccion),
]
