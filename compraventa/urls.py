# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('comprar_y_vender/', views.comprar_y_vender),
    path('crea_categorias/', views.crea_categorias),
    path('ajax_compraventa/', views.ajax_compraventa),
    path('estado_articulo/', views.estado_articulo),
]
