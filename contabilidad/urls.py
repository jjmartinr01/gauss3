# -*- coding: utf-8 -*-

# from django.conf.urls import url
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
    path('firmar_ordenes_adeudo/', views.firmar_ordenes_adeudo),
    path('mis_ordenes_adeudo/', views.mis_ordenes_adeudo),
    path('orden_adeudo_directo_sepa/<int:id>/', views.orden_adeudo_directo_sepa)
]

# urlpatterns = [
#     url(r'^presupuesto/$', views.presupuesto, name='presupuesto'),
#     url(r'^presupuesto_ajax/$', views.presupuesto_ajax, name='presupuesto_ajax'),
#     url(r'^presupuesto/(?P<id>\d+)/$', views.presupuesto, name='presupuesto'),
#     url(r'^presupuestos/$', views.presupuestos, name='presupuestos'),
# url(r'^add_partida/$', views.add_partida,  name='add_partida'),
# url(r'^save_partida/$', views.save_partida,  name='save_partida'),
# url(r'^mod_partida/$', views.mod_partida,  name='mod_partida'),
# url(r'^del_partida/$', views.del_partida,  name='del_partida'),
# url(r'^update_partida/$', views.update_partida,  name='update_partida'),
# url(r'^mod_describir/$', views.mod_describir,  name='mod_describir'),
# url(r'^gastos_ingresos/$', views.gastos_ingresos, name='gastos_ingresos'),
# url(r'^gastos_ingresos_ajax/$', views.gastos_ingresos_ajax, name='gastos_ingresos_ajax'),
# url(r'^add_gasto_ingreso/$', views.add_gasto_ingreso,  name='add_gasto_ingreso'),
# url(r'^save_gasto_ingreso/$', views.save_gasto_ingreso,  name='save_gasto_ingreso'),
# url(r'^del_gasto_ingreso/$', views.del_gasto_ingreso,  name='del_gasto_ingreso'),
# url(r'^mod_politica/$', views.mod_politica,  name='mod_politica'),
# url(r'^mod_asiento/$', views.mod_asiento,  name='mod_asiento'),
# url(r'^politica_cuotas/$', views.politica_cuotas, name='politica_cuotas'),
# url(r'^crear_politica_cuota/$', views.crear_politica_cuota,  name='crear_politica_cuota'),
# url(r'^ajax_politica_cuotas/$', views.ajax_politica_cuotas, name='ajax_politica_cuotas'),
# url(r'^crea_asientos/$', views.crea_asientos,  name='crea_asientos'),
# url(r'^orden_adeudo_directo_sepa/$', views.orden_adeudo_directo_sepa, name='orden_adeudo_directo_sepa'),
# ]
