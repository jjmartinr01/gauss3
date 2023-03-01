# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('documentos/', views.documentos),
    path('contrato_gauss/', views.contrato_gauss),
    path('presentaciones/', views.presentaciones),
    path('normativa/', views.normativa),
]
