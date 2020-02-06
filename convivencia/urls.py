# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.urls import path
from . import views

urlpatterns = [
    path('gestionar_conductas/', views.gestionar_conductas),
    path('gestionar_conductas_ajax/', views.gestionar_conductas_ajax),
    path('sancionar_conductas/', views.sancionar_conductas),
    path('sancionar_conductas_ajax/', views.sancionar_conductas_ajax),
    path('expediente_sancionador/', views.expediente_sancionador),
]

# urlpatterns = [
#     url(r'^gestionar_conductas/$', views.gestionar_conductas, name='gestionar_conductas'),
#     url(r'^gestionar_conductas_ajax/$', views.gestionar_conductas_ajax, name='gestionar_conductas_ajax'),
#     url(r'^sancionar_conductas/$', views.sancionar_conductas, name='sancionar_conductas'),
#     url(r'^sancionar_conductas_ajax/$', views.sancionar_conductas_ajax, name='sancionar_conductas_ajax'),
#     url(r'^expediente_sancionador/$', views.expediente_sancionador, name='expediente_sancionador'),
# ]
