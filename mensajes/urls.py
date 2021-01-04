# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('correo/', views.correo),
    path('responder_mensaje/', views.responder_mensaje),
    path('mensaje_importante/', views.mensaje_importante),
    path('enviados/', views.enviados),
    path('recibidos/', views.recibidos),
    path('ajax_mensajes/', views.ajax_mensajes),
    path('borrar_avisos/', views.borrar_avisos),
    path('get_avisos/', views.get_avisos),
    path('redactar_mensaje/', views.redactar_mensaje),
]
