# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('inicioweb/', views.inicioweb),
    path('avisolegal/', views.avisolegal),
    path('privacidad/', views.privacidad),
    path('condiciones/', views.condiciones),
]