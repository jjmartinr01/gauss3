# -*- coding: utf-8 -*-
from django.urls import path
from . import views

urlpatterns = [
    path('gestionar_actividades/', views.gestionar_actividades),
    path('ajax_actividades/', views.ajax_actividades),
    path('actividades_xml/', views.actividades_xml),
    path('actividades_json/', views.actividades_json),
    path('actividades2slides/', views.actividades2slides),
    # path('create_vevents/', views.create_vevents),
]
