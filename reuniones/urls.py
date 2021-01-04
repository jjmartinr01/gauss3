# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('conv_template/', views.conv_template),
    path('conv_template_ajax/', views.conv_template_ajax),
    path('conv_reunion/', views.conv_reunion),
    path('conv_reunion_ajax/', views.conv_reunion_ajax),
    path('redactar_actas_reunion/', views.redactar_actas_reunion),
    path('redactar_actas_reunion_ajax/', views.redactar_actas_reunion_ajax),
    path('lectura_actas_reunion/', views.lectura_actas_reunion),
    path('control_asistencia_reunion/', views.control_asistencia_reunion),
    path('firmar_acta_reunion/', views.firmar_acta_reunion),
]
