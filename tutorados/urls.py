# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^informes_seguimiento/$', views.informes_seguimiento, name='informes_seguimiento'),
    url(r'^ajax_informe_seguimiento/$', views.ajax_informe_seguimiento, name='ajax_informe_seguimiento'),
    url(r'^informes_tareas/$', views.informes_tareas, name='informes_tareas'),
    url(r'^ajax_informe_tareas/$', views.ajax_informe_tareas, name='ajax_informe_tareas'),
]
