# -*- coding: utf-8 -*-
# from django.conf.urls import include, url
from django.conf.urls import include
from django.urls import re_path
from django.conf import settings
from django.conf.urls.static import static

# Línea introducida para usar las urls de Foundation
# from django.views.generic import TemplateView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

admin.autodiscover()

urlpatterns = [re_path(r'^', include('autenticar.urls')),
               re_path(r'^', include('apariencia.urls')),
               re_path(r'^', include('entidades.urls')),
               re_path(r'^', include('mensajes.urls')),
               re_path(r'^', include('gtelegram.urls')),
               re_path(r'^', include('calendario.urls')),
               re_path(r'^', include('contabilidad.urls')),
               re_path(r'^', include('bancos.urls')),
               re_path(r'^', include('actas.urls')),
               re_path(r'^', include('documentos.urls')),
               re_path(r'^', include('lopd.urls')),
               re_path(r'^', include('vestuario.urls')),
               re_path(r'^', include('compraventa.urls')),
               re_path(r'^', include('gauss_conf.urls')),
               re_path(r'^', include('formularios.urls')),
               re_path(r'^', include('horarios.urls')),
               re_path(r'^', include('cupo.urls')),
               re_path(r'^', include('convivencia.urls')),
               re_path(r'^', include('absentismo.urls')),
               re_path(r'^', include('registro.urls')),
               re_path(r'^', include('reparaciones.urls')),
               re_path(r'^', include('actividades.urls')),
               re_path(r'^', include('tutorados.urls')),
               re_path(r'^', include('programaciones.urls')),
               re_path(r'^', include('estudios.urls')),
               re_path(r'^', include('competencias_clave.urls')),
               re_path(r'^', include('vut.urls')),
               re_path(r'^', include('domotica.urls')),
               re_path(r'^', include('reuniones.urls')),
               re_path(r'^', include('inspeccion_educativa.urls')),
               re_path(r'^', include('moscosos.urls')),
               re_path(r'^', include('federaciones.urls')),
               re_path(r'^', include('faqs.urls')),
               # url(r'^', include('webpage.urls')),
               # url(regex=r'^index_foundation/$',
               #     view=TemplateView.as_view(template_name="foundation/index.html"),
               #     name="foundation_index"),
               # url(regex=r'^icons/$',
               #     view=TemplateView.as_view(template_name="foundation/icons.html"),
               #     name="foundation_icons"),
               # Uncomment the admin/doc line below to enable admin documentation:
               # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
               # Uncomment the next line to enable the admin:
               re_path(r'^admin/', admin.site.urls),
               # Para servir los ficheros de /media/
               # url(r'^media/(?P<path>.*)$', django.views.static,  name='static.serve',
               #     {'document_root': settings.MEDIA_ROOT,}),
               # Línea para capturar cualquier url introducida por un usuario
               # url(r'^.*/$', web.views.pagina_web_entidad,  name='pagina_web_entidad'),
               re_path(r'^captcha/', include('captcha.urls')),
               # La url de web va la última porque recoge un patrón genérico con el fin de reconocer páginas web
               re_path(r'^', include('web.urls')),
               ]

# Las siguientes líneas son para visualizar MEDIA cuando corres el servidor de django
# Ayuda obtenida de: https://overiq.com/django-1-10/handling-media-files-in-django/
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

