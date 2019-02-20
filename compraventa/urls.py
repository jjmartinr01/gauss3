# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^comprar_y_vender/$', views.comprar_y_vender, name='comprar_y_vender'),
    url(r'^crea_categorias/$', views.crea_categorias, name='crea_categorias'),
    url(r'^ajax_compraventa/$', views.ajax_compraventa, name='ajax_compraventa'),
    url(r'^estado_articulo/$', views.estado_articulo, name='estado_articulo'),
]
