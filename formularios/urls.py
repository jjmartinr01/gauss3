# -*- coding: utf-8 -*-

from django.urls import path
from . import views

# from django.conf.urls import url
# from . import views

urlpatterns = [
    # path('linkge/<str:code>/', views.linkge),
    path('formularios/', views.formularios),
    path('edita_gform/', views.edita_gform),
    path('rellena_gform/', views.rellena_gform),
    path('resultados_gform/', views.resultados_gform),
    path('ver_gform/', views.ver_gform),
    path('edita_ginput/', views.edita_ginput),
    path('formulario_ajax/', views.formulario_ajax),
    # url(r'^formularios/$', views.formularios, name='formularios'),
    # url(r'^edita_gform/$', views.edita_gform, name='edita_gform'),
    # url(r'^rellena_gform/$', views.rellena_gform, name='rellena_gform'),
    # url(r'^resultados_gform/$', views.resultados_gform, name='resultados_gform'),
    # url(r'^ver_gform/$', views.ver_gform, name='ver_gform'),
    # url(r'^edita_ginput/$', views.edita_ginput, name='edita_ginput'),
    # url(r'^formulario_ajax/$', views.formulario_ajax, name='formulario_ajax'),
]
