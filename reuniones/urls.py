# -*- coding: utf-8 -*-

from django.conf.urls import url
from reuniones import views

urlpatterns = [
    url(r'^conv_template/$', views.conv_template, name='conv_template'),
    url(r'^conv_template_ajax/$', views.conv_template_ajax, name='conv_template_ajax'),
    url(r'^conv_reunion/$', views.conv_reunion, name='conv_reunion'),
    url(r'^conv_reunion_ajax/$', views.conv_reunion_ajax, name='conv_reunion_ajax'),
    url(r'^redactar_actas_reunion/$', views.redactar_actas_reunion, name='redactar_actas_reunion'),
    url(r'^redactar_actas_reunion_ajax/$', views.redactar_actas_reunion_ajax, name='redactar_actas_reunion_ajax'),
    url(r'^lectura_actas_reunion/$', views.lectura_actas_reunion, name='lectura_actas_reunion'),
    url(r'^control_asistencia_reunion/$', views.control_asistencia_reunion, name='control_asistencia_reunion'),
    url(r'^firmar_acta_reunion/$', views.firmar_acta_reunion, name='firmar_acta_reunion'),
]
