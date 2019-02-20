# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^correo/$', views.correo, name='correo'),
    url(r'^responder_mensaje/$', views.responder_mensaje, name='responder_mensaje'),
    url(r'^mensaje_importante/$', views.mensaje_importante, name='mensaje_importante'),
    url(r'^enviados/$', views.enviados, name='enviados'),
    url(r'^recibidos/$', views.recibidos, name='recibidos'),
    url(r'^ajax_mensajes/$', views.ajax_mensajes, name='ajax_mensajes'),
    url(r'^borrar_avisos/$', views.borrar_avisos, name='borrar_avisos'),
    url(r'^get_avisos/$', views.get_avisos, name='get_avisos'),
    url(r'^redactar_mensaje/$', views.redactar_mensaje, name='redactar_mensaje'),
]
