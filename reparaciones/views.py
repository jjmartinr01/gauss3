# -*- coding: utf-8 -*-
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
# from django.template import RequestContext
# from django.db import models
from django.db.models import Q
from django import forms
from django.forms import ModelForm
from entidades.models import Gauser_extra, Cargo
from autenticar.control_acceso import permiso_required
from gauss.funciones import html_to_pdf
from reparaciones.models import Reparacion
from datetime import datetime, date
from django.core.mail import EmailMessage
from mensajes.views import crear_aviso
from mensajes.models import Aviso
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
import simplejson as json
from gauss.rutas import *
from mensajes.views import encolar_mensaje

logger = logging.getLogger('django')


@permiso_required('acceso_reparaciones')
def gestionar_reparaciones(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST':
        if request.POST['action'] == 'genera_informe' and g_e.has_permiso('genera_informe_reparaciones'):
            try:
                inicio = datetime.strptime(request.POST['id_fecha_inicio'], '%d-%m-%Y')
            except:
                inicio = datetime.strptime('01-01-2000', '%d-%m-%Y')
            try:
                fin = datetime.strptime(request.POST['id_fecha_fin'], '%d-%m-%Y')
            except:
                fin = datetime.strptime('01-01-3000', '%d-%m-%Y')
            texto = request.POST['busca_reparaciones'] if request.POST['busca_reparaciones'] else ' '
            tipos = ['inf', 'ele', 'fon', 'alb', 'gen', 'car']
            tipo = [request.POST['tipo_busqueda']] if request.POST['tipo_busqueda'] in tipos else tipos
            q_texto = Q(describir_problema__icontains=texto) | Q(describir_solucion__icontains=texto)
            q_inicio = Q(fecha_comunicado__gte=inicio)
            q_fin = Q(fecha_comunicado__lte=fin)
            q_tipo = Q(tipo__in=tipo)
            q_entidad = Q(detecta__entidad=g_e.ronda.entidad)
            reparaciones = Reparacion.objects.filter(q_entidad, q_texto, q_inicio, q_fin, q_tipo)

            fichero = 'Reparaciones%s_%s_%s' % (
                str(g_e.ronda.entidad.code), request.POST['tipo_busqueda'], g_e.gauser.username)
            c = render_to_string('reparaciones2pdf.html', {'reparaciones': reparaciones, 'MA': MEDIA_ANAGRAMAS, },
                                 request=request)
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_REPARACIONES, title=u'Lista de reparaciones')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response

    Reparacion.objects.filter(detecta__entidad=g_e.ronda.entidad, borrar=True).delete()
    reparaciones = Reparacion.objects.filter(detecta__entidad=g_e.ronda.entidad, fecha_comunicado__gte=g_e.ronda.inicio,
                                             detecta__ronda=g_e.ronda).order_by('-fecha_comunicado', 'resuelta')

    return render(request, "reparaciones.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'title': 'Crear una nueva solicitud de reparación',
                            'permiso': 'crea_solicitud_reparacion'},
                           {'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'Informe',
                            'title': 'Generar informe con las reparaciones de la entidad',
                            'permiso': 'genera_informe_reparaciones'},
                           ),
                      'formname': 'Reparaciones',
                      'reparaciones': reparaciones,
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                     aceptado=False),
                  })


def gestionar_reparaciones_ajax(request):
    g_e = request.session["gauser_extra"]

    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_solicitud':
            if g_e.has_permiso('crea_solicitud_reparacion'):
                reparacion = Reparacion.objects.create(detecta=g_e, lugar='', describir_problema='',
                                                       describir_solucion='')
                html = render_to_string('reparacion_accordion.html',
                                        {'buscadas': False, 'reparaciones': [reparacion], 'g_e': g_e, 'nueva':True})
                return JsonResponse({'ok': True, 'html': html})
            else:
                JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            try:
                reparacion = Reparacion.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id'])
                html = render_to_string('reparacion_accordion_content.html', {'reparacion': reparacion, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'update_lugar':
            try:
                reparacion = Reparacion.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id'])
                reparacion.lugar = request.POST['valor']
                if len(reparacion.lugar) < 3:
                    reparacion.borrar = True
                else:
                    reparacion.borrar = False
                reparacion.save()
                return JsonResponse({'ok': True, 'valor': reparacion.lugar})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'update_tipo':
            try:
                reparacion = Reparacion.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id'])
                reparacion.tipo = request.POST['valor']
                reparacion.save()
                return JsonResponse({'ok': True, 'valor': reparacion.get_tipo_display()})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'enviar_mensaje':
            try:
                reparacion = Reparacion.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id'])
                reparacion.comunicado_a_reparador = True
                mensaje = render_to_string('reparaciones_mail.html', {'reparacion': reparacion})
                # mensaje = u'El usuario %s ha grabado una incidencia de reparación. Los datos significativos son:<br><strong>Lugar:</strong> <em>%s</em> <br><strong>Descripción:</strong> <em>%s</em> <br>Gracias por tu atención.' % (
                #     g_e.gauser.get_full_name(), reparacion.lugar, reparacion.describir_problema)
                permisos = ['controla_reparaciones_%s' % reparacion.tipo, 'controla_reparaciones']
                cargos = Cargo.objects.filter(permisos__code_nombre__in=permisos, entidad=g_e.ronda.entidad).distinct()

                receptores = Gauser_extra.objects.filter(Q(ronda=g_e.ronda), Q(permisos__code_nombre__in=permisos) | Q(
                                                             cargos__in=cargos)).values_list('gauser__id', flat=True)
                encolar_mensaje(emisor=g_e, receptores=receptores, asunto='Solicitud de reparación', html=mensaje,
                                etiqueta='reparacion%s' % reparacion.id)
                reparacion.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'update_resuelta':
            try:
                reparacion = Reparacion.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id'])
                reparacion.resuelta = not reparacion.resuelta
                reparacion.reparador = g_e
                reparacion.save()
                html = render_to_string('reparacion_accordion_content.html', {'reparacion': reparacion, 'g_e': g_e})
                if reparacion.resuelta:
                    mensaje = u'El %s grabaste una incidencia de reparación en la que indicabas lo siguiente:<br><br><em>%s</em> <br>A fecha %s se ha indicado en GAUSS que %s ha solucionado la incidencia.<br> <strong>%s</strong><br>Gracias por tu atención' % (
                        reparacion.fecha_comunicado.strftime("%d-%m-%Y"), reparacion.describir_problema,
                        reparacion.fecha_solucion.strftime("%d-%m-%Y"), reparacion.reparador.gauser.get_full_name(),
                        reparacion.describir_solucion)
                    encolar_mensaje(emisor=g_e, receptores=[reparacion.detecta.gauser],
                                    asunto='Reparación solicitada realizada', html=mensaje,
                                    etiqueta='reparacion%s' % reparacion.id)
                return JsonResponse({'ok': True, 'valor': ['No', 'Sí'][reparacion.resuelta],
                                     'resuelta': reparacion.resuelta, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'update_describir_problema':
            try:
                reparacion = Reparacion.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id'])
                reparacion.describir_problema = request.POST['valor']
                if len(reparacion.describir_problema) < 5:
                    reparacion.borrar = True
                else:
                    reparacion.borrar = False
                reparacion.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'update_describir_solucion':
            try:
                reparacion = Reparacion.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id'])
                reparacion.describir_solucion = request.POST['valor']
                reparacion.reparador = g_e
                reparacion.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'borrar_solicitud':
            try:
                Reparacion.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id']).delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'busca_reparaciones':
            try:
                try:
                    inicio = datetime.strptime(request.POST['id_fecha_inicio'], '%d-%m-%Y')
                except:
                    inicio = datetime.strptime('01-01-2000', '%d-%m-%Y')
                try:
                    fin = datetime.strptime(request.POST['id_fecha_fin'], '%d-%m-%Y')
                except:
                    fin = datetime.strptime('01-01-3000', '%d-%m-%Y')
                texto = request.POST['texto'] if request.POST['texto'] else ' '
                tipos = ['inf', 'ele', 'fon', 'alb', 'gen', 'car']
                tipo = [request.POST['tipo_busqueda']] if request.POST['tipo_busqueda'] in tipos else tipos
                q_texto = Q(describir_problema__icontains=texto) | Q(describir_solucion__icontains=texto)
                q_inicio = Q(fecha_comunicado__gte=inicio)
                q_fin = Q(fecha_comunicado__lte=fin)
                q_tipo = Q(tipo__in=tipo)
                q_entidad = Q(detecta__entidad=g_e.ronda.entidad)
                rs = Reparacion.objects.filter(q_entidad, q_texto, q_inicio, q_fin, q_tipo)
                html = render_to_string('reparacion_accordion.html', {'reparaciones': rs, 'g_e': g_e, 'buscadas': True})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
