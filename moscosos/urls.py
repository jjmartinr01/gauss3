# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('moscosos/', views.moscosos),
    path('ajax_moscosos/', views.ajax_moscosos),
]
