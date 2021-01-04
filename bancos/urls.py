# -*- coding: utf-8 -*-

from django.urls import path
from . import views

urlpatterns = [
    path('crea_bancos/', views.crea_bancos),
    path('bancos_sin_bic/', views.bancos_sin_bic),
    path('download_bancos/', views.download_bancos),
    # path('asocia_bancos/', views.asocia_bancos),
    # path('calc_iban/', views.calc_iban),
]
