# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('configura_federacion/', views.configura_federacion),
    path('ajax_configura_federacion/', views.ajax_configura_federacion),
path('cuotas_federacion/', views.cuotas_federacion),
path('ajax_cuotas_federacion/', views.ajax_cuotas_federacion),
path('documentos_federacion/', views.documentos_federacion),
path('ajax_documentos_federacion/', views.ajax_documentos_federacion),
path('inscribir_federacion/', views.inscribir_federacion),
]
