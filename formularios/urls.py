# -*- coding: utf-8 -*-

from django.urls import path
from . import views

# from django.conf.urls import url
# from . import views

urlpatterns = [
    path('formularios/', views.formularios),
    path('mis_formularios/', views.mis_formularios),
    # path('edita_gform/', views.edita_gform),
    path('rellena_gform/<int:id>/<str:identificador>/', views.rellena_gform),
    path('resultados_gform/', views.resultados_gform),
    path('ver_gform/<int:id>/<str:identificador>/', views.ver_gform),
    # path('edita_ginput/', views.edita_ginput),
    # path('formulario_ajax/', views.formulario_ajax),
]
