# -*- coding: utf-8 -*-

from django.urls import path
from . import views

# from django.conf.urls import url
# from . import views

urlpatterns = [
    path('formularios/', views.formularios),
    path('mis_formularios/', views.mis_formularios),
    path('rellena_gform/<int:id>/<str:identificador>/', views.rellena_gform),
    path('rellena_gform/<int:id>/<str:identificador>/<str:gfr_identificador>/', views.rellena_gform),
    path('ver_gform/<int:id>/<str:identificador>/', views.ver_gform),
    path('ver_resultados/<int:id>/<str:identificador>/', views.ver_resultados),
]
