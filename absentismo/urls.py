# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('gestionar_absentismo/', views.gestionar_absentismo),
    path('ajax_absentismo/', views.ajax_absentismo),
]