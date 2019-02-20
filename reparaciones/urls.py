# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^gestionar_reparaciones/$', views.gestionar_reparaciones, name='gestionar_reparaciones'),
url(r'^gestionar_reparaciones_ajax/$', views.gestionar_reparaciones_ajax, name='gestionar_reparaciones_ajax'),
]