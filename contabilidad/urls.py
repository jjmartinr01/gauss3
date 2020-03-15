# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('presupuesto/', views.presupuesto),
    path('presupuesto/<int:id>/', views.presupuesto),
    path('presupuesto_ajax/', views.presupuesto_ajax),
    path('presupuestos/', views.presupuestos),
    path('gastos_ingresos/', views.gastos_ingresos),
    path('gastos_ingresos_ajax/', views.gastos_ingresos_ajax),
    path('politica_cuotas/', views.politica_cuotas),
    path('ajax_politica_cuotas/', views.ajax_politica_cuotas),
    path('ordenes_adeudo/', views.ordenes_adeudo),
    path('firmar_orden_adeudo/<int:id_oa>/', views.firmar_orden_adeudo),
    path('mis_ordenes_adeudo/', views.mis_ordenes_adeudo),
]