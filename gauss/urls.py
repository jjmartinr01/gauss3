# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from django.conf import settings
from django.conf.urls.static import static

# Línea introducida para usar las urls de Foundation
# from django.views.generic import TemplateView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

admin.autodiscover()

urlpatterns = [url(r'^', include('autenticar.urls')),
               url(r'^', include('apariencia.urls')),
               url(r'^', include('entidades.urls')),
               url(r'^', include('mensajes.urls')),
               url(r'^', include('gtelegram.urls')),
               url(r'^', include('calendario.urls')),
               url(r'^', include('contabilidad.urls')),
               url(r'^', include('bancos.urls')),
               url(r'^', include('actas.urls')),
               url(r'^', include('documentos.urls')),
               url(r'^', include('lopd.urls')),
               url(r'^', include('vestuario.urls')),
               url(r'^', include('compraventa.urls')),
               url(r'^', include('gauss_conf.urls')),
               url(r'^', include('formularios.urls')),
               url(r'^', include('horarios.urls')),
               url(r'^', include('cupo.urls')),
               url(r'^', include('convivencia.urls')),
               url(r'^', include('absentismo.urls')),
               url(r'^', include('registro.urls')),
               url(r'^', include('reparaciones.urls')),
               url(r'^', include('actividades.urls')),
               url(r'^', include('tutorados.urls')),
               url(r'^', include('programaciones.urls')),
               url(r'^', include('estudios.urls')),
               url(r'^', include('competencias_clave.urls')),
               url(r'^', include('vut.urls')),
               url(r'^', include('domotica.urls')),
               url(r'^', include('reuniones.urls')),
               url(r'^', include('inspeccion_educativa.urls')),
               url(r'^', include('moscosos.urls')),
               url(r'^', include('federaciones.urls')),
               url(r'^', include('faqs.urls')),
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
               url(r'^admin/', admin.site.urls),
               # Para servir los ficheros de /media/
               # url(r'^media/(?P<path>.*)$', django.views.static,  name='static.serve',
               #     {'document_root': settings.MEDIA_ROOT,}),
               # Línea para capturar cualquier url introducida por un usuario
               # url(r'^.*/$', web.views.pagina_web_entidad,  name='pagina_web_entidad'),
               url(r'^captcha/', include('captcha.urls')),
               # La url de web va la última porque recoge un patrón genérico con el fin de reconocer páginas web
               url(r'^', include('web.urls')),
               ]

# Las siguientes líneas son para visualizar MEDIA cuando corres el servidor de django
# Ayuda obtenida de: https://overiq.com/django-1-10/handling-media-files-in-django/
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

