# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^calendario/$', views.calendario, name='calendario'),
    url(r'^edita_evento/$', views.edita_evento, name='edita_evento'),
    url(r'^crea_evento/$', views.crea_evento, name='crea_evento'),
    url(r'^calendario_ajax/$', views.calendario_ajax, name='calendario_ajax'),
    # url(r'^mod_recordatorio/$', views.mod_recordatorio,  name='mod_recordatorio'),
    # url(r'^muestra_calendario/$', views.muestra_calendario,  name='muestra_calendario'),
    # url(r'^mis_eventos/$', views.mis_eventos,  name='mis_eventos'),
    # url(r'^ver_acontecimiento/$', views.ver_acontecimiento,  name='ver_acontecimiento'),
    # url(r'^acontecimiento_importante/$', views.acontecimiento_importante,  name='acontecimiento_importante'),
]
