# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# import urlparse
import urllib  # .parse import parse_qs # Sirve para leer los forms serializados y pasados por ajax
from datetime import datetime

import simplejson as json
from django.contrib.auth.decorators import login_required
from django.core.files.base import File
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.text import slugify

from actas.models import *
from autenticar.control_acceso import permiso_required
# from calendario.models import Acontecimiento
# from calendario.models import Evento, Calendario
from calendario.models import Vevent
from entidades.models import Subentidad, Gauser_extra
from gauss.funciones import html_to_pdf, human_readable_list
from gauss.rutas import MEDIA_ANAGRAMAS, MEDIA_ACTAS, RUTA_BASE
from mensajes.models import Aviso
from mensajes.views import crear_aviso, encolar_mensaje


# from lxml import etree
# from BeautifulSoup import BeautifulStoneSoup
# from bs4 import BeautifulSoup
# from actas.models import Convocatoria, Acta  # , Punto_convocatoria, Acuerdo_acta


# import locale
# locale.setlocale(locale.LC_ALL, "")


# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
# FUNCIONES RELACIONADAS CON LA CONFIGURACIÓN DE CONVOCATORIAS DE REUNIÓN
# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#

@permiso_required('acceso_configurar_convocatorias')
def configurar_convocatorias(request):
    g_e = request.session['gauser_extra']
    if g_e.has_permiso('edita_configuraciones_convocatorias'):
        configuraciones = Convocatoria.objects.filter(entidad=g_e.ronda.entidad, plantilla=True)
    else:
        configuraciones = Convocatoria.objects.filter(entidad=g_e.ronda.entidad, creador=g_e.gauser, plantilla=True)

    return render(request, "configurar_convocatorias.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'title': 'Crear una nueva configuración de convocatoria',
                            'permiso': 'crea_configuraciones_convocatorias'},
                           ),
                      'configura': True,
                      'formname': 'configura_convocatorias',
                      'configuraciones': configuraciones,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def configurar_convocatorias_ajax(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'update_texto_configura_convocatoria':
            try:
                configuracion = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
                if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
                    configuracion.texto_convocatoria = request.POST['texto']
                    configuracion.save()
                    puntos = request.POST.getlist('puntos[]')
                    Punto_convocatoria.objects.filter(convocatoria=configuracion).delete()
                    for punto in puntos:
                        Punto_convocatoria.objects.create(convocatoria=configuracion, punto=punto)
                    html = render_to_string('convocatoria_texto.html', {'c': configuracion})
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_nombre_configura_convocatoria':
            try:
                configuracion = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
                if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
                    configuracion.nombre = request.POST['nombre'].strip()
                    configuracion.save()
                    try:
                        acta = Acta.objects.get(convocatoria=configuracion)
                        acta.nombre = 'Acta de la reunión: %s' % configuracion.nombre
                        acta.save()
                    except:
                        pass
                return JsonResponse({'ok': True, 'nombre': configuracion.nombre})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_lugar_configura_convocatoria':
            try:
                configuracion = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
                if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
                    configuracion.lugar = request.POST['lugar']
                    configuracion.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_convoca_configura_convocatoria':
            try:
                configuracion = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
                if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
                    ge = Gauser_extra.objects.get(id=request.POST['convoca'], ronda=g_e.ronda)
                    configuracion.convoca = ge.gauser
                    configuracion.save()
                    cargos = {c[0]: c[1] for c in ge.cargos.all().values_list('id', 'cargo')}
                    return JsonResponse({'ok': True, 'cargos': cargos, 'convocante': ge.gauser.get_full_name()})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_cargo_configura_convocatoria':
            try:
                configuracion = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
                if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
                    cargo_convocante = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
                    configuracion.cargo_convocante = cargo_convocante
                    configuracion.save()
                return JsonResponse({'ok': True, 'cargo': cargo_convocante.cargo})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_subentidades_convocadas_configura_convocatoria':
            try:
                configuracion = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
                if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
                    subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad,
                                                             id__in=request.POST.getlist('subentidades[]'))
                    configuracion.convocados.clear()
                    configuracion.convocados.add(*subentidades)
                    configuracion.save()
                    texto = human_readable_list(configuracion.convocados.all().values_list('nombre', flat=True))
                    if not texto:
                        texto = '<<convocados>>'
                return JsonResponse({'ok': True, 'texto': texto})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_cargos_convocados_configura_convocatoria':
            try:
                configuracion = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
                if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
                    cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad,
                                                  id__in=request.POST.getlist('cargos[]'))
                    configuracion.cargos_convocados.clear()
                    configuracion.cargos_convocados.add(*cargos)
                    configuracion.save()
                    texto = human_readable_list(configuracion.convocados.all().values_list('nombre', flat=True))
                    if not texto:
                        texto = '<<convocados>>'
                return JsonResponse({'ok': True, 'texto': texto})
            except:
                return JsonResponse({'ok': False})
        elif action == 'sub_convocadas_texto':
            try:
                configuracion = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
                texto = human_readable_list(configuracion.convocados.all().values_list('nombre', flat=True))
                if not texto:
                    texto = '<<convocados>>'
                return JsonResponse({'ok': True, 'texto': texto})
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            conf = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
            plantillas = [] if conf.plantilla else Convocatoria.objects.filter(entidad=g_e.ronda.entidad,
                                                                               plantilla=True)
            if g_e.has_permiso('edita_configuraciones_convocatorias') or conf.creador == g_e.gauser:
                if conf.convoca:
                    cargos = Gauser_extra.objects.get(gauser=conf.convoca, ronda=g_e.ronda).cargos.all()
                else:
                    cargos = []
                ok = True
                html = render_to_string('configurar_convocatoria_accordion_content.html',
                                        {'configura_convocatoria': conf, 'g_e': g_e, 'cargos': cargos,
                                         'plantillas': plantillas})
            else:
                ok = False
                html = ''
            return JsonResponse({'ok': ok, 'html': html})
        elif action == 'nueva_configuracion' and g_e.has_permiso('crea_configuraciones_convocatorias'):
            try:
                conv = Convocatoria.objects.create(creador=g_e.gauser, entidad=g_e.ronda.entidad, plantilla=True,
                                                   nombre='Convocatoria ...', fecha_hora=datetime.now())
                html_conv = render_to_string('convocatoria_texto.html', {'c': conv})
                conv.texto_convocatoria = html_conv
                conv.save()
                html = render_to_string('configurar_convocatoria_accordion.html', {'c': conv})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif action == 'delete_configura_convocatoria':
            configuracion = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
            if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
                ok = True
                if request.POST['is_plantilla'] == 'False':
                    Acta.objects.get(convocatoria=configuracion).delete()
                configuracion.delete()
            else:
                ok = False
            return JsonResponse({'ok': ok})

        elif action == 'nueva_convocatoria' and g_e.has_permiso('crea_convocatorias'):
            try:
                conv = Convocatoria.objects.create(creador=g_e.gauser, entidad=g_e.ronda.entidad, plantilla=False,
                                                   nombre='Convocatoria ...', fecha_hora=datetime.now())
                Acta.objects.create(convocatoria=conv, nombre='Acta de la reunión: %s' % conv.nombre)
                html_conv = render_to_string('convocatoria_texto.html', {'c': conv})
                conv.texto_convocatoria = html_conv
                conv.save()
                html = render_to_string('configurar_convocatoria_accordion.html', {'c': conv})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif action == 'update_plantilla':
            conv = Convocatoria.objects.get(id=request.POST['convocatoria'], entidad=g_e.ronda.entidad, plantilla=False)
            if g_e.has_permiso('crea_convocatorias') or conv.creador == g_e.gauser:
                try:
                    conf = Convocatoria.objects.get(id=request.POST['plantilla'], entidad=g_e.ronda.entidad,
                                                    plantilla=True)
                    conv.texto_convocatoria = conf.texto_convocatoria
                    conv.convoca = conf.convoca
                    conv.lugar = conf.lugar
                    if conf.fecha_hora < timezone.now():
                        conv.fecha_hora = timezone.now()
                    else:
                        conv.fecha_hora = conf.fecha_hora
                    conv.nombre = conf.nombre
                    conv.cargo_convocante = conf.cargo_convocante
                    conv.convocados.add(*conf.convocados.all())
                    conv.save()
                    if conv.convoca:
                        cargos = Gauser_extra.objects.get(gauser=conv.convoca, ronda=g_e.ronda).cargos.all()
                    else:
                        cargos = []
                    day_name = conv.fecha_hora.strftime('%A').lower()
                    day_num = conv.fecha_hora.day
                    month_name = conv.fecha_hora.strftime('%B').lower()
                    year = conv.fecha_hora.year
                    datetime_time = conv.fecha_hora.strftime("%H:%M")
                    html = render_to_string('configurar_convocatoria_accordion_content.html',
                                            {'configura_convocatoria': conv, 'g_e': g_e, 'cargos': cargos})
                    return JsonResponse(
                        {'ok': True, 'html': html, 'day_name': day_name, 'day_num': day_num, 'month_name': month_name,
                         'year': year, 'datetime_time': datetime_time})
                except:
                    return JsonResponse({'ok': False})
        elif action == 'update_fecha_hora':
            convocatoria = Convocatoria.objects.get(id=request.POST['convocatoria'], entidad=g_e.ronda.entidad)
            fecha_hora = datetime.strptime(request.POST['fecha_hora'], "%d/%m/%Y %H:%M")
            convocatoria.fecha_hora = fecha_hora
            convocatoria.save()
            day_name = fecha_hora.strftime('%A').lower()
            day_num = fecha_hora.day
            month_name = fecha_hora.strftime('%B').lower()
            year = fecha_hora.year
            datetime_time = fecha_hora.strftime("%H:%M")
            return JsonResponse(
                {'ok': True, 'day_name': day_name, 'day_num': day_num, 'month_name': month_name, 'year': year,
                 'datetime_time': datetime_time})
        elif action == 'update_redacta_acta':
            try:
                configuracion = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
                acta = Acta.objects.get(convocatoria=configuracion)
                if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
                    ge = Gauser_extra.objects.get(id=request.POST['redacta'], ronda=g_e.ronda)
                    acta.redacta = ge.gauser
                    acta.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos'})
            except:
                return JsonResponse({'ok': False})


# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
# FUNCIONES RELACIONADAS CON LA CREACIÓN DE CONVOCATORIAS DE REUNIÓN
# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#

@permiso_required('acceso_convocatorias')
def convocatorias(request):
    g_e = request.session['gauser_extra']
    if g_e.has_permiso('crea_convocatorias'):
        convs = Convocatoria.objects.filter(entidad=g_e.ronda.entidad, plantilla=False)
    else:
        convs = Convocatoria.objects.filter(entidad=g_e.ronda.entidad, creador=g_e.gauser, plantilla=False)
    if request.method == 'POST':
        if request.POST['action'] == 'pdf_convocatoria':
            try:
                convocatoria = Convocatoria.objects.get(id=request.POST['id_convocatoria'], entidad=g_e.ronda.entidad)
                fichero = 'convocatoria_%s_%s' % (g_e.ronda.entidad.code, convocatoria.id)
                c = render_to_string('convocatoria2pdf.html', {
                    'convocatoria': convocatoria,
                    'MA': MEDIA_ANAGRAMAS,
                }, request=request)
                fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_ACTAS, title=u'Convocatoria de reunión')
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
                return response
            except:
                crear_aviso(request, False, 'No es posible generar el pdf de la convocatoria solicitada')

    return render(request, "convocatorias.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'title': 'Crear una nueva convocatoria',
                            'permiso': 'crea_convocatorias'},
                           ),
                      'configura': False,
                      'formname': 'convocatorias',
                      'convocatorias': convs,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def convocatorias_ajax(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'nueva_convocatoria' and g_e.has_permiso('crea_convocatorias'):
            try:
                conv = Convocatoria.objects.create(creador=g_e.gauser, entidad=g_e.ronda.entidad, plantilla=False,
                                                   nombre='Convocatoria ...', fecha_hora=datetime.now())
                Acta.objects.create(convocatoria=conv, nombre='Acta: %s' % conv.nombre)
                html_conv = render_to_string('convocatoria_texto.html', {'c': conv})
                conv.texto_convocatoria = html_conv
                conv.save()
                html = render_to_string('convocatoria_accordion.html', {'c': conv})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            conv = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'], plantilla=False)
            plantillas = Convocatoria.objects.filter(entidad=g_e.ronda.entidad, plantilla=True)
            if g_e.has_permiso('edita_convocatorias') or conv.creador == g_e.gauser:
                if conv.convoca:
                    cargos = Gauser_extra.objects.get(gauser=conv.convoca, ronda=g_e.ronda).cargos.all()
                else:
                    cargos = []
                html = render_to_string('convocatoria_accordion_content.html',
                                        {'convocatoria': conv, 'g_e': g_e, 'cargos': cargos, 'plantillas': plantillas})
                return JsonResponse({'ok': True, 'html': html})
            else:
                return JsonResponse({'ok': False})
        elif action == 'delete_convocatoria':
            mensaje = ''
            try:
                convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'])
                if g_e.has_permiso('borra_convocatorias') or convocatoria.creador == g_e.gauser:
                    try:
                        acta = Acta.objects.get(convocatoria=convocatoria)
                    except:
                        acta = None
                    if acta.fecha_aprobacion:
                        mensaje = '<p>La convocatoria tiene asociada un acta que ya ha sido aprobada. No puede borrarse.</p>'
                        return JsonResponse({'ok': False, 'mensaje': mensaje})
                    elif acta.publicada:
                        mensaje = '<p>La convocatoria tiene asociada un acta que ya ha sido publicada. No puede borrarse.</p>'
                        return JsonResponse({'ok': False, 'mensaje': mensaje})
                    else:
                        try:
                            e = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='convocatoria' + str(convocatoria.id))
                            e.delete()
                        except:
                            pass
                        try:
                            Acta.objects.get(convocatoria=convocatoria).delete()
                            mensaje += '<p>Se ha borrado el acta asociada a esta convocatoria.</p>'
                        except:
                            mensaje += '<p>No se ha encontrado un acta asociada a esta convocatoria.</p>'
                        convocatoria.delete()
                        mensaje += '<p>Se ha borrado la convocatoria.</p>'
                        return JsonResponse({'ok': True, 'mensaje': mensaje})
                else:
                    mensaje += '<p>No tienes permisos para borrar esta convocatoria.</p>'
                    return JsonResponse({'ok': False, 'mensaje': mensaje})
            except:
                mensaje += '<p>Error al tratar de borrar esta convocatoria.</p>'
                return JsonResponse({'ok': False, 'mensaje': mensaje})
        elif action == 'update_plantilla':
            conv = Convocatoria.objects.get(id=request.POST['convocatoria'], entidad=g_e.ronda.entidad, plantilla=False)
            if g_e.has_permiso('edita_convocatorias') or conv.creador == g_e.gauser:
                plantillas = Convocatoria.objects.filter(entidad=g_e.ronda.entidad, plantilla=True)
                try:
                    conf = plantillas.get(id=request.POST['plantilla'])
                    conv.basada_en = conf
                    conv.texto_convocatoria = conf.texto_convocatoria
                    conv.convoca = conf.convoca
                    conv.lugar = conf.lugar
                    conv.fecha_hora = timezone.now()
                    conv.nombre = conf.nombre
                    conv.cargo_convocante = conf.cargo_convocante
                    conv.convocados.add(*conf.convocados.all())
                    conv.save()
                    if conv.convoca:
                        cargos = Gauser_extra.objects.get(gauser=conv.convoca, ronda=g_e.ronda).cargos.all()
                    else:
                        cargos = []
                    try:
                        acta = Acta.objects.get(convocatoria=conv)
                        acta.nombre = 'Acta: %s' % conv.nombre
                        acta.save()
                    except:
                        pass
                    day_name = conv.fecha_hora.strftime('%A').lower()
                    day_num = conv.fecha_hora.day
                    month_name = conv.fecha_hora.strftime('%B').lower()
                    year = conv.fecha_hora.year
                    datetime_time = conv.fecha_hora.strftime("%H:%M")
                    plantillas = [{'id': p.id, 'nombre': p.nombre} for p in plantillas]
                    html = render_to_string('convocatoria_accordion_content.html',
                                            {'convocatoria': conv, 'g_e': g_e, 'cargos': cargos, 'nombre': conv.nombre,
                                             'plantillas': plantillas})
                    return JsonResponse(
                        {'ok': True, 'html': html, 'day_name': day_name, 'day_num': day_num, 'month_name': month_name,
                         'year': year, 'datetime_time': datetime_time, 'nombre': conv.nombre})
                except:
                    return JsonResponse({'ok': False})
        elif action == 'update_fecha_hora':
            convocatoria = Convocatoria.objects.get(id=request.POST['convocatoria'], entidad=g_e.ronda.entidad)
            fecha_hora = datetime.strptime(request.POST['fecha_hora'], "%d/%m/%Y %H:%M")
            convocatoria.fecha_hora = fecha_hora
            convocatoria.save()
            day_name = fecha_hora.strftime('%A').lower()
            day_num = fecha_hora.day
            month_name = fecha_hora.strftime('%B').lower()
            year = fecha_hora.year
            datetime_time = fecha_hora.strftime("%H:%M")
            return JsonResponse(
                {'ok': True, 'day_name': day_name, 'day_num': day_num, 'month_name': month_name, 'year': year,
                 'datetime_time': datetime_time})
        elif action == 'update_lugar_convocatoria':
            try:
                convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'])
                if g_e.has_permiso('edita_convocatorias') or convocatoria.creador == g_e.gauser:
                    convocatoria.lugar = request.POST['lugar']
                    convocatoria.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_convoca_convocatoria':
            try:
                convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'])
                if g_e.has_permiso('edita_convocatorias') or convocatoria.creador == g_e.gauser:
                    ge = Gauser_extra.objects.get(id=request.POST['convoca'], ronda=g_e.ronda)
                    convocatoria.convoca = ge.gauser
                    convocatoria.save()
                    cargos = {c[0]: c[1] for c in ge.cargos.all().values_list('id', 'cargo')}
                    return JsonResponse({'ok': True, 'cargos': cargos, 'convocante': ge.gauser.get_full_name()})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_cargo_convocatoria':
            try:
                convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'])
                if g_e.has_permiso('edita_convocatorias') or convocatoria.creador == g_e.gauser:
                    cargo_convocante = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
                    convocatoria.cargo_convocante = cargo_convocante
                    convocatoria.save()
                    return JsonResponse({'ok': True, 'cargo': cargo_convocante.cargo})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_redacta_acta':
            try:
                convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'])
                acta = Acta.objects.get(convocatoria=convocatoria)
                if g_e.has_permiso('edita_convocatorias') or convocatoria.creador == g_e.gauser:
                    ge = Gauser_extra.objects.get(id=request.POST['redacta'], ronda=g_e.ronda)
                    acta.redacta = ge.gauser
                    acta.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_subentidades_convocadas_convocatoria':
            try:
                convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'])
                if g_e.has_permiso('edita_convocatorias') or convocatoria.creador == g_e.gauser:
                    subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad,
                                                             id__in=request.POST.getlist('subentidades[]'))
                    convocatoria.convocados.clear()
                    convocatoria.convocados.add(*subentidades)
                    convocatoria.save()
                    texto = human_readable_list(convocatoria.convocados.all().values_list('nombre', flat=True))
                    if not texto:
                        texto = "la %s" % convocatoria.entidad.name
                return JsonResponse({'ok': True, 'texto': texto})
            except:
                return JsonResponse({'ok': False})
        # elif action == 'update_cargos_convocados_convocatoria':
        #     try:
        #         convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'])
        #         if g_e.has_permiso('edita_convocatorias') or convocatoria.creador == g_e.gauser:
        #             cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('cargos[]'))
        #             convocatoria.cargos_convocados.clear()
        #             convocatoria.cargos_convocados.add(*cargos)
        #             convocatoria.save()
        #             texto = human_readable_list(convocatoria.convocados.all().values_list('nombre', flat=True))
        #             if not texto:
        #                 texto = '<<convocados>>'
        #         return JsonResponse({'ok': True, 'texto': texto})
        #     except:
        #         return JsonResponse({'ok': False})
        elif action == 'update_nombre_convocatoria':
            try:
                convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'])
                if g_e.has_permiso('edita_convocatorias') or convocatoria.creador == g_e.gauser:
                    convocatoria.nombre = request.POST['nombre'].strip()
                    convocatoria.save()
                    try:
                        acta = Acta.objects.get(convocatoria=convocatoria)
                        acta.nombre = 'Acta: %s' % convocatoria.nombre
                        acta.save()
                    except:
                        pass
                return JsonResponse({'ok': True, 'nombre': convocatoria.nombre})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_texto_convocatoria':
            try:
                convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'],
                                                        plantilla=False)
                if g_e.has_permiso('edita_convocatorias') or convocatoria.creador == g_e.gauser:
                    convocatoria.texto_convocatoria = request.POST['texto']
                    convocatoria.save()
                    puntos = request.POST.getlist('puntos[]')
                    Punto_convocatoria.objects.filter(convocatoria=convocatoria).delete()
                    for punto in puntos:
                        Punto_convocatoria.objects.create(convocatoria=convocatoria, punto=punto)
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la convocatoria'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'send_email':
            try:
                convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'],
                                                        plantilla=False)
                if g_e.has_permiso('mail_convocatorias') or convocatoria.creador == g_e.gauser:
                    n = convocatoria.nombre
                    t = convocatoria.texto_convocatoria
                    html = '<h2>%s</h2>%s' % (n, t)
                    if convocatoria.convocados.all().count() > 0:
                        rs = [ge.gauser for ge in
                              Gauser_extra.objects.filter(subentidades__in=convocatoria.convocados.all())]
                    else:
                        rs = [ge.gauser for ge in
                              Gauser_extra.objects.filter(ronda__entidad=convocatoria.entidad)]
                    encolar_mensaje(emisor=g_e, receptores=rs, asunto='Convocatoria: %s' % n, html=html,
                                    etiqueta='actas%s' % convocatoria.id)
                    correos = [g.email for g in rs if g.email]
                    mensaje = '<p>Enviado correo a %s personas.</p><p>%s</p>' % (
                        len(correos), human_readable_list(correos, type='lower'))
                    return JsonResponse({'ok': True, 'mensaje': mensaje})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para enviar el correo'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error al tratar de llevar a cabo la acción solicitada'})
        elif action == 'crea_evento':
            try:
                convocatoria = Convocatoria.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'],
                                                        plantilla=False)
                if g_e.has_permiso('evento_convocatorias') or convocatoria.creador == g_e.gauser:
                    try:
                        e = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='convocatoria' + str(convocatoria.id))
                        e.delete()
                    except:
                        pass
                    evento = Vevent.objects.create(entidad=g_e.ronda.entidad, uid='convocatoria' + str(convocatoria.id),
                                                   description=convocatoria.texto_convocatoria,
                                                   dtstart=convocatoria.fecha_hora, summary=convocatoria.nombre)
                    evento.propietarios.add(g_e.gauser)
                    evento.subentidades.add(*convocatoria.convocados.all())
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para enviar el correo'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error al tratar de llevar a cabo la acción solicitada'})


# def puntos_convocatoria(convocatoria):
#     p_conv = []
#     text = unicode(BeautifulStoneSoup(convocatoria.texto_convocatoria, convertEntities=BeautifulStoneSoup.ALL_ENTITIES))
#     xml_conv = etree.XML('<div>' + text + '</div>')
#     ol = xml_conv.find('.//ol[@id="puntos_convocatoria"]')
#     for li in ol.findall('.//li'):
#         try:
#             p_conv.append({'id': li.attrib['id'], 'text': li.text})
#         except:
#             p_conv.append({'id': 'sin_id', 'text': li.text})
#     return p_conv


# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
# FUNCIONES RELACIONADAS CON LA LECTURA DE ACTAS
# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
def ver_actas_ajax(request):
    pass


# @permiso_required('acceso_ver_actas')
def ver_actas(request):
    g_e = request.session['gauser_extra']

    if request.method == 'POST':
        action = request.POST['action']
        if request.POST['action'] == 'pdf_acta':
            try:
                acta = Acta.objects.get(id=request.POST['id_acta'], convocatoria__entidad=g_e.ronda.entidad)
                fichero = 'acta_%s_%s' % (g_e.ronda.entidad.code, acta.id)
                fich = open(MEDIA_ACTAS + fichero)
                crear_aviso(request, True, u"Descarga pdf: %s" % (acta.convocatoria.nombre))
                response = HttpResponse(fich, content_type='application/pdf')
                filename = acta.convocatoria.nombre.replace(' ', '_') + '.pdf'
                response['Content-Disposition'] = 'attachment; filename=' + filename
                return response
            except:
                try:
                    acta = Acta.objects.get(id=request.POST['id_acta'], convocatoria__entidad=g_e.ronda.entidad)
                    fichero = 'acta_%s_%s' % (g_e.ronda.entidad.code, acta.id)
                    c = render_to_string('acta2pdf.html', {
                        'acta': acta,
                        'MA': MEDIA_ANAGRAMAS,
                    }, request=request)
                    fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_ACTAS, title=u'Acta de reunión')
                    response = HttpResponse(fich, content_type='application/pdf')
                    response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
                    return response
                except:
                    crear_aviso(request, False, 'No es posible generar el pdf del acta solicitada')

    if g_e.has_permiso('ve_todas_actas'):
        actas = Acta.objects.filter(convocatoria__entidad=g_e.ronda.entidad, publicada=True)
    else:
        subentidades = g_e.subentidades.all()
        actas = Acta.objects.filter(convocatoria__convocados__in=subentidades, publicada=True).distinct()
    return render(request, "ver_actas.html",
                  {
                      'formname': 'actas',
                      'actas': actas,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def ajax_actas(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        if request.POST['action'] == 'actualiza_convocatoria' and g_e.has_permiso('m40i20'):
            form = urllib.parse.parse_qs(request.POST['form'])
            nombre = form['nombre'][0]
            fecha_hora = form['fecha_hora'][0]
            convocados = Subentidad.objects.filter(id__in=form['convocados'], entidad=g_e.ronda.entidad,
                                                   fecha_expira__gt=datetime.today())
            fecha = datetime.strptime(fecha_hora, "%d/%m/%Y %H:%M")
            data = render_to_string('convocatoria_texto.html',
                                    {'convocados': convocados, 'fecha': fecha, 'nombre': nombre},
                                    request=request)
            return HttpResponse(data)
        if request.POST['action'] == 'contenido_acta':
            acta = Acta.objects.get(id=json.loads(request.POST['id']))
            return HttpResponse('<h2>' + acta.convocatoria.nombre + '</h2>' + acta.contenido_html)


# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
# FUNCIONES RELACIONADAS CON LA REDACCIÓN DE ACTAS
# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#

# @permiso_required('acceso_redactar_actas')
def redactar_actas(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        if request.POST['action'] == 'pdf_acta':
            try:
                acta = Acta.objects.get(id=request.POST['id_acta'], convocatoria__entidad=g_e.ronda.entidad)
                fecha = acta.convocatoria.fecha_hora.strftime('%Y%m%d')
                nombre_fichero = slugify('%s-%s' % (acta.nombre, fecha)) + '.pdf'
                if acta.fecha_aprobacion or acta.publicada:
                    fichero = acta.pdf.read()
                    response = HttpResponse(fichero, content_type='application/pdf')
                    response['Content-Disposition'] = 'attachment; filename=' + nombre_fichero
                    return response
                else:
                    fichero = '%s/borradores/acta' % (g_e.ronda.entidad.code)
                    c = render_to_string('acta2pdf.html', {
                        'acta': acta,
                        'MA': MEDIA_ANAGRAMAS,
                    }, request=request)
                    fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_ACTAS, title=u'Acta de reunión')
                    response = HttpResponse(fich, content_type='application/pdf')
                    response['Content-Disposition'] = 'attachment; filename=' + nombre_fichero
                    return response

                #     fich_name = 'parte_temporal%s.txt' % (vivienda.propietario.id)
                #     ruta = os.path.join("%svut/" % (RUTA_MEDIA), fich_name)
                #     f = open(ruta, "w+")
                #     contenido = render_to_string('fichero_registro_policia.txt', {'v': vivienda, 'vs': registro.viajeros.all()})
                #     f.write(contenido.encode('utf-8'))
                #     registro.parte = File(f)
                #     registro.save()
                #     f.close()


            except:
                crear_aviso(request, False, 'No es posible generar el pdf del acta solicitada')

    subentidades = g_e.subentidades.all()
    if g_e.has_permiso('redacta_cualquier_acta'):
        actas_publicadas = Acta.objects.filter(convocatoria__entidad=g_e.ronda.entidad, publicada=True).distinct()
        actas_sin_publicar = Acta.objects.filter(convocatoria__entidad=g_e.ronda.entidad, publicada=False).distinct()
    elif g_e.has_permiso('redacta_actas_subentidades'):
        actas_publicadas = Acta.objects.filter(convocatoria__convocados__in=subentidades, publicada=True).distinct()
        actas_sin_publicar = Acta.objects.filter(convocatoria__convocados__in=subentidades, publicada=False).distinct()
    elif g_e.has_permiso('redacta_sus_actas'):
        actas_publicadas = Acta.objects.filter(convocatoria__convoca=g_e.gauser,
                                               convocatoria__entidad=g_e.ronda.entidad,
                                               publicada=True).distinct()
        actas_sin_publicar = Acta.objects.filter(convocatoria__convoca=g_e.gauser,
                                                 convocatoria__entidad=g_e.ronda.entidad,
                                                 publicada=False).distinct()
    else:
        actas_publicadas = []
        actas_sin_publicar = []

    return render(request, "redactar_actas.html",
                  {
                      'formname': 'actas',
                      'actas_publicadas': actas_publicadas,
                      'actas_sin_publicar': actas_sin_publicar,
                      'subentidades': subentidades,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def redactar_actas_ajax(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'open_accordion':
            acta = Acta.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
            if not acta.contenido_html:
                try:
                    redacta_ge = Gauser_extra.objects.get(ronda=g_e.ronda, gauser=acta.redacta)
                    cargo_redacta = redacta_ge.cargos.order_by('nivel')[0]
                except:
                    cargo_redacta = None
                p_conv = Punto_convocatoria.objects.filter(convocatoria=acta.convocatoria)
                html = render_to_string('texto_acta.html',
                                        {'convocatoria': acta.convocatoria, 'p_conv': p_conv, 'redacta': acta.redacta,
                                         'cargo_redacta': cargo_redacta})
                acta.contenido_html = html
                acta.save()
            g_es = acta.asistentes.all().values_list('id', 'gauser__last_name', 'gauser__first_name')
            keys = ('id', 'text')
            asistentes = json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in g_es])
            html_accordion = render_to_string('acta_accordion_content.html', {'acta': acta, 'asistentes': asistentes,
                                                                              'g_e': g_e})
            return JsonResponse({'html': html_accordion, 'ok': True})
        elif action == 'update_nombre_acta':
            try:
                acta = Acta.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if acta.publicada or acta.fecha_aprobacion:
                    return JsonResponse({'ok': False})
                if g_e.has_permiso('redacta_cualquier_acta') or acta.redacta == g_e.gauser:
                    acta.nombre = request.POST['nombre'].strip()
                    acta.save()
                return JsonResponse({'ok': True, 'nombre': acta.nombre})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_fecha_aprobacion':
            try:
                acta = Acta.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if request.POST['fecha_aprobacion'] == 'borrar':
                    acta.fecha_aprobacion = None
                    acta.save()
                    return JsonResponse({'ok': True})
                if acta.publicada or acta.fecha_aprobacion:
                    return JsonResponse({'ok': False})
                fecha_aprobacion = datetime.strptime(request.POST['fecha_aprobacion'], "%d/%m/%Y")
                acta.fecha_aprobacion = fecha_aprobacion
                acta.publicada = True
                try:
                    os.remove(RUTA_BASE + acta.pdf.url)
                except:
                    pass
                fichero = '%s/borradores/acta' % (g_e.ronda.entidad.code)
                c = render_to_string('acta2pdf.html', {
                    'acta': acta,
                    'MA': MEDIA_ANAGRAMAS,
                }, request=request)
                fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_ACTAS, title=u'Acta de reunión')
                acta.pdf = File(fich)
                acta.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_usuarios_asistentes':
            acta = Acta.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
            if acta.publicada or acta.fecha_aprobacion:
                return JsonResponse({'ok': False})
            if 'added[]' in request.POST:
                ges = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('added[]'))
                acta.asistentes.add(*ges)
            if 'removed[]' in request.POST:
                ges = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('removed[]'))
                acta.asistentes.remove(*ges)
            asistentes = acta.asistentes.all().values_list('gauser__first_name', 'gauser__last_name')
            ns = human_readable_list([u'{0} {1}'.format(first_name, last_name) for first_name, last_name in asistentes])
            if not asistentes:
                ns = '...'
            return JsonResponse({'ok': True, 'ns': ns})
        elif action == 'update_texto_acta':
            acta = Acta.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
            if acta.publicada or acta.fecha_aprobacion:
                return JsonResponse({'ok': False})
            texto = request.POST['texto']
            acta.contenido_html = texto
            acta.save()
            return JsonResponse({'ok': True})
        elif action == 'update_publicada':
            try:
                acta = Acta.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if acta.fecha_aprobacion:
                    return JsonResponse({'ok': False})
                acta.publicada = not acta.publicada
                if acta.publicada:
                    fichero = '%s/borradores/acta' % (g_e.ronda.entidad.code)
                    c = render_to_string('acta2pdf.html', {
                        'acta': acta,
                        'MA': MEDIA_ANAGRAMAS,
                    }, request=request)
                    fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_ACTAS, title=u'Acta de reunión')
                    acta.pdf = File(fich)
                else:
                    os.remove(RUTA_BASE + acta.pdf.url)
                acta.save()
                return JsonResponse({'ok': True, 'publicada': acta.publicada})
            except:
                return JsonResponse({'ok': False})
        elif action == 'send_email':
            try:
                acta = Acta.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if g_e.has_permiso('mail_actas') or acta.redacta == g_e.gauser:
                    n = acta.nombre
                    t = acta.contenido_html
                    html = '<h2>%s</h2>%s' % (n, t)
                    if acta.convocatoria.convocados.all().count() > 0:
                        rs = [ge.gauser for ge in
                              Gauser_extra.objects.filter(subentidades__in=acta.convocatoria.convocados.all())]
                    else:
                        rs = [ge.gauser for ge in
                              Gauser_extra.objects.filter(ronda__entidad=acta.convocatoria.entidad)]
                    encolar_mensaje(emisor=g_e, receptores=rs, asunto='%s' % n, html=html,
                                    etiqueta='actas%s' % acta.convocatoria.id)
                    correos = [g.email for g in rs if g.email]
                    mensaje = '<p>Enviado correo a %s personas.</p><p>%s</p>' % (
                        len(correos), human_readable_list(correos, type='lower'))
                    return JsonResponse({'ok': True, 'mensaje': mensaje})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para enviar el correo'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error al tratar de llevar a cabo la acción solicitada'})

# @login_required()
# def actualiza_texto_acta(request):
#     if request.is_ajax():
#         g_e = request.session['gauser_extra']
#         convocatoria = Convocatoria.objects.get(id=request.POST['id'])
#         sub_convocadas = convocatoria.convocados.all()  # Subentidades convocadas
#         g_es = usuarios_de_gauss(g_e.ronda.entidad, subentidades=sub_convocadas)
#         try:
#             acta = Acta.objects.get(convocatoria=convocatoria)
#             publicar = acta.publicar
#             asistentes = g_es.filter(id__in=acta.asistentes.split(','))
#             contenido = acta.contenido_html
#             con_html = render_to_string('texto_acta.html',
#                                         {'convocatoria': convocatoria, 'existe': True, 'contenido': contenido},
#                                         request=request)
#         except:
#             asistentes = None
#             publicar = False
#             con_html = render_to_string('texto_acta.html', {'convocatoria': convocatoria, 'hoy': datetime.today()},
#                                         request=request)
#         asi_html = render_to_string('asistentes.html',
#                                     {'g_es': g_es, 'asistentes': asistentes, 'sub_convocadas': sub_convocadas},
#                                     request=request)
#         return HttpResponse(json.dumps({'asistentes': asi_html, 'contenido': con_html, 'publicar': publicar}))
