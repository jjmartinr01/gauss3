# -*- coding: utf-8 -*-
# from django.conf.urls import url
from django.urls import path
from . import views

urlpatterns = [
    path('cupo/', views.cupo),
    path('ajax_cupo/', views.ajax_cupo),
    path('edit_cupo/<int:cupo_id>/', views.edit_cupo),
    path('plantilla_organica/', views.plantilla_organica),
]

# urlpatterns = [
#     url(r'^cupo/$', views.cupo, name='cupo'),
#     url(r'^ajax_cupo/$', views.ajax_cupo, name='ajax_cupo'),
#     url(r'^edit_cupo/(?P<cupo_id>[0-9]+)/$', views.edit_cupo, name='edit_cupo'),
# url(r'^carga_masiva_plantilla/$', views.carga_masiva_plantilla, name='carga_masiva_plantilla'),
# ]
