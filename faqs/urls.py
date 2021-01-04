# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('configura_faqs/', views.configura_faqs),
    path('faqs_gauss/', views.faqs_gauss),
    path('faqs_entidad/', views.faqs_entidad),
    path('faqs_borradas/', views.faqs_borradas),
    path('faqs_sugeridas/', views.faqs_sugeridas),
]
