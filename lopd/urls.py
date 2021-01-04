# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('responsables_lopd/', views.responsables_lopd),
    path('documento_seguridad/', views.documento_seguridad),
path('derechos_arco/', views.derechos_arco),
path('incidencias_lopd/', views.incidencias_lopd),
path('inventario_soportes/', views.inventario_soportes),
path('confidencialidad/', views.confidencialidad),
]