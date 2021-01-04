# -*- coding: utf-8 -*-

from django.urls import path, re_path
from . import views

urlpatterns = [
    path('noticias_web', views.noticias_web),
    path('noticias_web_ajax/', views.noticias_web_ajax),
    path('upload_file_noticia_web/', views.upload_file_noticia_web),
    path('noticias_web_json/', views.noticias_web_json),
    path('web_design/', views.web_design),
    path('ajax_webs/', views.ajax_webs),
    path('edita_web/', views.edita_web),
    path('enlaces_web/', views.enlaces_web),
    path('sube_archivos_web/', views.sube_archivos_web),
    re_path(r'^.*/$', views.pagina_web_entidad),
]
