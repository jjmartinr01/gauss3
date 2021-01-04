# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('ge2ge/', views.ge2ge),
]
