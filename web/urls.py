# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^noticias_web/$', views.noticias_web, name='noticias_web'),
    url(r'^noticias_web_ajax/$', views.noticias_web_ajax, name='noticias_web_ajax'),
    url(r'^upload_file_noticia_web/$', views.upload_file_noticia_web, name='upload_file_noticia_web'),
    url(r'^noticias_web_json/$', views.noticias_web_json, name='noticias_web_json'),
    url(r'^web_design/$', views.web_design, name='web_design'),
    url(r'^ajax_webs/$', views.ajax_webs, name='ajax_webs'),
    # url(r'^edita_web/$','views.edita_web,  name='edita_web'),
    # url(r'^template_banded/(?P<id>\d+)/$', views.template_banded,  name='template_banded'),
    url(r'^edita_web/(?P<id>\d+)/$', views.edita_web, name='edita_web'),
    url(r'^enlaces_web/$', views.enlaces_web, name='enlaces_web'),
    url(r'^sube_archivos_web/$', views.sube_archivos_web, name='sube_archivos_web'),
    # url(r'^ajax_enlaces_web/$', views.ajax_enlaces_web,  name='ajax_enlaces_web'),
    url(r'^.*/$', views.pagina_web_entidad, name='pagina_web_entidad'),
]
