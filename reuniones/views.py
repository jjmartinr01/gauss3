# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import pdfkit
# import urlparse
import urllib  # .parse import parse_qs # Sirve para leer los forms serializados y pasados por ajax
import base64
import locale
from datetime import datetime

import simplejson as json
from django.contrib.auth.decorators import login_required
from django.core.files.base import File, ContentFile
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Q

from reuniones.models import *
from autenticar.control_acceso import permiso_required
from calendario.models import Vevent
from entidades.models import Subentidad, Gauser_extra
from entidades.views import decode_selectgcs
from gauss.funciones import human_readable_list, usuarios_ronda, get_dce
from gauss.rutas import MEDIA_ANAGRAMAS, MEDIA_REUNIONES, RUTA_BASE
from gauss.constantes import DIAS, MESES
from mensajes.models import Aviso, Mensaje, Etiqueta
from mensajes.views import crear_aviso, encolar_mensaje, crea_mensaje_cola, enviar_correo

# locale.setlocale(locale.LC_TIME, 'es_ES.utf8')
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

logger = logging.getLogger('django')


# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
# FUNCIONES RELACIONADAS CON LA CREACIÓN DE PLANTILLAS DE CONVOCATORIAS DE REUNIÓN
# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#

@permiso_required('acceso_conv_template')
def conv_template(request):
    g_e = request.session['gauser_extra']
    posibilidades = ConvReunion.objects.filter(entidad=g_e.ronda.entidad, plantilla=True)
    if g_e.has_permiso('w_conv_reunion'):
        configuraciones = posibilidades
    else:
        configuraciones = [p for p in posibilidades if p.permiso(g_e, 'edita_plantilla')]

    return render(request, "conv_template.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'title': 'Crear una nueva configuración de convocatoria',
                            'permiso': 'c_conv_template'},
                           ),
                      'configura': True,
                      'formname': 'conv_template',
                      'configuraciones': configuraciones,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def conv_template_ajax(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'nueva_plantilla' and g_e.has_permiso('c_conv_template'):
            try:
                conv = ConvReunion.objects.create(creador=g_e.gauser, entidad=g_e.ronda.entidad, plantilla=True,
                                                  nombre='Convocatoria de reunion ...', fecha_hora=datetime.now())
                PuntoConvReunion.objects.create(convocatoria=conv, orden=1,
                                                punto='Lectura y aprobación si procede del acta anterior.')
                PuntoConvReunion.objects.create(convocatoria=conv, punto='Punto del orden del día ...', orden=2)
                PuntoConvReunion.objects.create(convocatoria=conv, punto='Ruegos y preguntas.', orden=3)
                html_conv = render_to_string('conv_template_texto.html', {'c': conv})
                conv.texto_convocatoria = html_conv
                conv.save()
                html = render_to_string('conv_template_accordion.html', {'c': conv})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            conv_template = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_template'])
            plantillas = [] if conv_template.plantilla else ConvReunion.objects.filter(entidad=g_e.ronda.entidad,
                                                                                       plantilla=True)
            if g_e.has_permiso('w_conv_template') or conv_template.permiso(g_e, 'edita_plantilla'):
                try:
                    cargos = Gauser_extra.objects.get(gauser=conv_template.convoca, ronda=g_e.ronda).cargos.all()
                except:
                    cargos = []
                ok = True
                puntos = PuntoConvReunion.objects.filter(convocatoria=conv_template)
                html = render_to_string('conv_template_accordion_content.html',
                                        {'conv_template': conv_template, 'g_e': g_e, 'cargos': cargos,
                                         'plantillas': plantillas, 'puntos': puntos})
            else:
                ok = False
                html = ''
            return JsonResponse({'ok': ok, 'html': html})
        elif action == 'delete_conv_template':
            conv_template = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_template'])
            if g_e.has_permiso('w_conv_template') or conv_template.permiso(g_e, 'edita_plantilla'):
                ok = True
                # if request.POST['is_plantilla'] == 'False':
                #     ActaReunion.objects.get(convocatoria=conv_template).delete()
                conv_template.delete()
            else:
                ok = False
            return JsonResponse({'ok': ok})
        elif action == 'update_convoca_conv_template':
            try:
                conv_template = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_template'])
                if g_e.has_permiso('w_conv_template') or conv_template.permiso(g_e, 'edita_plantilla'):
                    ge = Gauser_extra.objects.get(id=request.POST['convoca'], ronda=g_e.ronda)
                    cargos = ge.cargos.all()
                    conv_template.convoca = ge.gauser
                    conv_template.convoca_text = ge.gauser.get_full_name()
                    try:
                        conv_template.cargo_convocante = cargos[0]
                        conv_template.cargo_convocante_text = cargos[0].cargo
                    except:
                        conv_template.cargo_convocante = None
                        conv_template.cargo_convocante_text = ''
                    conv_template.save()
                    cargos = {c[0]: c[1] for c in cargos.values_list('id', 'cargo')}
                    return JsonResponse({'ok': True, 'cargos': cargos, 'convocante': ge.gauser.get_full_name(),
                                         'conv_template': conv_template.id})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_cargo_conv_template':
            try:
                conv_template = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_template'])
                if g_e.has_permiso('w_conv_template') or conv_template.permiso(g_e, 'edita_plantilla'):
                    cargo_convocante = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
                    conv_template.cargo_convocante = cargo_convocante
                    conv_template.cargo_convocante_text = cargo_convocante.cargo
                    conv_template.save()
                return JsonResponse({'ok': True, 'conv_template': conv_template.id})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_lugar_conv_template':
            try:
                conv_template = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_template'])
                if g_e.has_permiso('w_conv_template') or conv_template.permiso(g_e, 'edita_plantilla'):
                    conv_template.lugar = request.POST['lugar']
                    conv_template.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_subentidades_convocadas_conv_template':
            try:
                conv_template = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_template'])
                if g_e.has_permiso('w_conv_template') or conv_template.permiso(g_e, 'edita_plantilla'):
                    subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad,
                                                             id__in=request.POST.getlist('subentidades[]'))
                    conv_template.convocados.clear()
                    conv_template.convocados.add(*subentidades)
                    texto = human_readable_list(conv_template.convocados.all().values_list('nombre', flat=True))
                    if not texto:
                        texto = '«convocados»'
                    conv_template.convocados_text = texto
                    conv_template.save()
                return JsonResponse({'ok': True, 'texto': texto})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_nombre_conv_template':
            try:
                conv_template = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_template'])
                if g_e.has_permiso('w_conv_template') or conv_template.permiso(g_e, 'edita_plantilla'):
                    conv_template.nombre = request.POST['nombre'].strip()
                    conv_template.save()
                    # try:
                    #     acta = ActaReunion.objects.get(convocatoria=conv_template)
                    #     acta.nombre = 'Acta de la reunión: %s' % conv_template.nombre
                    #     acta.save()
                    # except:
                    #     pass
                return JsonResponse({'ok': True, 'nombre': conv_template.nombre})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_texto_configura_convocatoria':
            try:
                configuracion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
                if g_e.has_permiso('w_conv_template') or configuracion.permiso(g_e, 'edita_plantilla'):
                    configuracion.texto_convocatoria = request.POST['texto']
                    configuracion.save()
                    html = render_to_string('convocatoria_texto.html', {'c': configuracion})
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_orden_conv_template':
            try:
                punto = PuntoConvReunion.objects.get(id=request.POST['punto'])
                conv_template = punto.convocatoria
                if g_e.has_permiso('w_conv_template') or conv_template.permiso(g_e, 'edita_plantilla'):
                    puntos = PuntoConvReunion.objects.filter(convocatoria=conv_template)
                    orden_nuevo = int(request.POST['orden'])
                    if orden_nuevo > puntos.count():
                        orden_nuevo = puntos.count()
                    elif orden_nuevo < 1:
                        orden_nuevo = 1
                    orden_viejo = punto.orden
                    if orden_nuevo < orden_viejo:
                        puntoscambiar = puntos.filter(orden__gte=orden_nuevo, orden__lt=orden_viejo)
                        for p in puntoscambiar:
                            p.orden = p.orden + 1
                            p.save()
                    elif orden_nuevo > orden_viejo:
                        puntoscambiar = puntos.filter(orden__gt=orden_viejo, orden__lte=orden_nuevo)
                        for p in puntoscambiar:
                            p.orden = p.orden - 1
                            p.save()
                    punto.orden = orden_nuevo
                    punto.save()
                    puntos = puntos.order_by('orden')
                    html = render_to_string('conv_template_accordion_content_puntos.html', {'puntos': puntos})
                    return JsonResponse({'ok': True, 'html': html, 'conv_template': conv_template.id})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_punto_conv_template':
            try:
                punto = PuntoConvReunion.objects.get(id=request.POST['punto'])
                conv_template = punto.convocatoria
                if g_e.has_permiso('w_conv_template') or conv_template.permiso(g_e, 'edita_plantilla'):
                    punto.punto = request.POST['texto']
                    punto.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_punto_conv_template':
            try:
                conv_template = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_template'])
                if g_e.has_permiso('w_conv_template') or conv_template.permiso(g_e, 'edita_plantilla'):
                    orden_nuevo = PuntoConvReunion.objects.filter(convocatoria=conv_template).count() + 1
                    PuntoConvReunion.objects.create(convocatoria=conv_template, orden=orden_nuevo, punto='Texto ...')
                    puntos = PuntoConvReunion.objects.filter(convocatoria=conv_template)
                    html = render_to_string('conv_template_accordion_content_puntos.html', {'puntos': puntos})
                    return JsonResponse({'ok': True, 'html': html, 'conv_template': conv_template.id})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'del_punto_conv_reunion':
            try:
                punto = PuntoConvReunion.objects.get(id=request.POST['punto'])
                conv_reunion = punto.convocatoria
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.permiso(g_e, 'edita_plantilla'):
                    punto.delete()
                    return JsonResponse({'ok': True, 'punto': request.POST['punto']})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})

        # elif action == 'update_cargos_convocados_configura_convocatoria':
        #     try:
        #         configuracion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
        #         if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.permiso(g_e, 'edita_plantilla'):
        #             cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad,
        #                                           id__in=request.POST.getlist('cargos[]'))
        #             configuracion.cargos_convocados.clear()
        #             configuracion.cargos_convocados.add(*cargos)
        #             configuracion.save()
        #             texto = human_readable_list(configuracion.convocados.all().values_list('nombre', flat=True))
        #             if not texto:
        #                 texto = '«convocados»'
        #         return JsonResponse({'ok': True, 'texto': texto})
        #     except:
        #         return JsonResponse({'ok': False})
        # elif action == 'sub_convocadas_texto':
        #     try:
        #         configuracion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
        #         texto = human_readable_list(configuracion.convocados.all().values_list('nombre', flat=True))
        #         if not texto:
        #             texto = '«convocados»'
        #         return JsonResponse({'ok': True, 'texto': texto})
        #     except:
        #         return JsonResponse({'ok': False})
        #
        #
        # elif action == 'nueva_convocatoria' and g_e.has_permiso('crea_convocatorias'):
        #     try:
        #         conv = ConvReunion.objects.create(creador=g_e.gauser, entidad=g_e.ronda.entidad, plantilla=False,
        #                                           nombre='ConvReunion ...', fecha_hora=datetime.now())
        #         ActaReunion.objects.create(convocatoria=conv, nombre='Acta de la reunión: %s' % conv.nombre)
        #         html_conv = render_to_string('convocatoria_texto.html', {'c': conv})
        #         conv.texto_convocatoria = html_conv
        #         conv.save()
        #         html = render_to_string('configurar_convocatoria_accordion.html', {'c': conv})
        #         return JsonResponse({'ok': True, 'html': html})
        #     except:
        #         return JsonResponse({'ok': False})
        #
        # elif action == 'update_plantilla':
        #     conv = ConvReunion.objects.get(id=request.POST['convocatoria'], entidad=g_e.ronda.entidad, plantilla=False)
        #     if g_e.has_permiso('crea_convocatorias') or conv.permiso(g_e, 'edita_plantilla'):
        #         try:
        #             conf = ConvReunion.objects.get(id=request.POST['plantilla'], entidad=g_e.ronda.entidad,
        #                                            plantilla=True)
        #             conv.texto_convocatoria = conf.texto_convocatoria
        #             conv.convoca = conf.convoca
        #             conv.lugar = conf.lugar
        #             if conf.fecha_hora < timezone.now():
        #                 conv.fecha_hora = timezone.now()
        #             else:
        #                 conv.fecha_hora = conf.fecha_hora
        #             conv.nombre = conf.nombre
        #             conv.cargo_convocante = conf.cargo_convocante
        #             conv.convocados.add(*conf.convocados.all())
        #             conv.save()
        #             if conv.convoca:
        #                 cargos = Gauser_extra.objects.get(gauser=conv.convoca, ronda=g_e.ronda).cargos.all()
        #             else:
        #                 cargos = []
        #             day_name = conv.fecha_hora.strftime('%A').lower()
        #             day_num = conv.fecha_hora.day
        #             month_name = conv.fecha_hora.strftime('%B').lower()
        #             year = conv.fecha_hora.year
        #             datetime_time = conv.fecha_hora.strftime("%H:%M")
        #             html = render_to_string('configurar_convocatoria_accordion_content.html',
        #                                     {'configura_convocatoria': conv, 'g_e': g_e, 'cargos': cargos})
        #             return JsonResponse(
        #                 {'ok': True, 'html': html, 'day_name': day_name, 'day_num': day_num, 'month_name': month_name,
        #                  'year': year, 'datetime_time': datetime_time})
        #         except:
        #             return JsonResponse({'ok': False})
        # elif action == 'update_fecha_hora':
        #     convocatoria = ConvReunion.objects.get(id=request.POST['convocatoria'], entidad=g_e.ronda.entidad)
        #     fecha_hora = datetime.strptime(request.POST['fecha_hora'], "%d/%m/%Y %H:%M")
        #     convocatoria.fecha_hora = fecha_hora
        #     convocatoria.save()
        #     day_name = fecha_hora.strftime('%A').lower()
        #     day_num = fecha_hora.day
        #     month_name = fecha_hora.strftime('%B').lower()
        #     year = fecha_hora.year
        #     datetime_time = fecha_hora.strftime("%H:%M")
        #     return JsonResponse(
        #         {'ok': True, 'day_name': day_name, 'day_num': day_num, 'month_name': month_name, 'year': year,
        #          'datetime_time': datetime_time})
        # elif action == 'update_redacta_acta':
        #     try:
        #         configuracion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
        #         acta = ActaReunion.objects.get(convocatoria=configuracion)
        #         if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.permiso(g_e, 'edita_plantilla'):
        #             ge = Gauser_extra.objects.get(id=request.POST['redacta'], ronda=g_e.ronda)
        #             acta.redacta = ge.gauser
        #             acta.save()
        #             return JsonResponse({'ok': True})
        #         else:
        #             return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos'})
        #     except:
        #         return JsonResponse({'ok': False})


# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
# FUNCIONES RELACIONADAS CON LA CREACIÓN DE CONVOCATORIAS DE REUNIÓN
# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#

def busca_convocatorias(request):
    g_e = request.session['gauser_extra']
    try:
        qin = Q(fecha_hora__gte=datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date())
    except:
        qin = Q(fecha_hora__gte=datetime.strptime('2000-1-1', '%Y-%m-%d').date())
    try:
        qfi = Q(fecha_hora__lte=datetime.strptime(request.POST['fin'], '%Y-%m-%d').date())
    except:
        qfi = Q(fecha_hora__lte=timezone.now().date() + timezone.timedelta(50))
    try:
        id = request.POST['plantilla']
        plantilla = ConvReunion.objects.get(entidad=g_e.ronda.entidad, plantilla=True, id=id)
        q1 = Q(entidad=g_e.ronda.entidad) & Q(plantilla=False) & Q(basada_en=plantilla) & qin & qfi
    except:
        q1 = Q(entidad=g_e.ronda.entidad) & Q(plantilla=False) & qin & qfi
    convs = ConvReunion.objects.filter(q1)
    try:
        texto = request.POST['texto']
    except:
        texto = ''
    puntos = PuntoConvReunion.objects.filter(convocatoria__in=convs, punto__icontains=texto)
    return convs.filter(id__in=puntos.values_list('convocatoria__id', flat=True)).distinct()


@permiso_required('acceso_conv_reunion')
def conv_reunion(request):
    g_e = request.session['gauser_extra']
    posibilidades = ConvReunion.objects.filter(entidad=g_e.ronda.entidad, plantilla=False)
    if g_e.has_permiso('c_conv_reunion'):
        convs = posibilidades
    else:
        convs = [p for p in posibilidades if p.permiso(g_e, 'puede_convocar')]
    if request.method == 'POST':
        if request.POST['action'] == 'pdf_convocatoria':
            try:
                dce = get_dce(g_e.ronda.entidad, 'Configuración para convocatorias de reunión')
                convocatoria = ConvReunion.objects.get(id=request.POST['id_conv_reunion'], entidad=g_e.ronda.entidad)
                fichero = 'convocatoria_%s_%s' % (g_e.ronda.entidad.code, convocatoria.id)
                c = render_to_string('convreunion2pdf.html', {'convocatoria': convocatoria, 'pdf': True})
                fich = pdfkit.from_string(c, False, dce.get_opciones)
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
                return response
            except:
                crear_aviso(request, False, 'No es posible generar el pdf de la convocatoria solicitada')
        elif request.POST['action'] == 'update_page':
            try:
                convs = busca_convocatorias(request)
                paginator = Paginator(convs, 15)
                buscar = {'0': False, '1': True}[request.POST['buscar']]
                convs_paginadas = paginator.page(int(request.POST['page']))
                html = render_to_string('conv_accordion.html', {'convocatorias': convs_paginadas, 'buscar': buscar})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

    paginator = Paginator(convs, 15)
    return render(request, "conv.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'title': 'Crear una nueva convocatoria',
                            'permiso': 'c_conv_reunion'},
                           {'tipo': 'button', 'nombre': 'search', 'texto': 'Buscar',
                            'title': 'Buscar convocatorias',
                            'permiso': 'libre'},
                           ),
                      'formname': 'convocatorias',
                      'convocatorias': paginator.page(1),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


def get_plantillas(g_e):
    if g_e.has_permiso('c_conv_reunion'):
        return ConvReunion.objects.filter(entidad=g_e.ronda.entidad, plantilla=True)
    else:
        q1 = Q(gauser=g_e.gauser) | Q(cargo__in=g_e.cargos.all())
        q2 = Q(puede_convocar=True)
        conv_ids = PermisoReunion.objects.filter(q1, q2).values_list('plantilla__id', flat=True)
        return ConvReunion.objects.filter(entidad=g_e.ronda.entidad, plantilla=True, id__in=conv_ids)


@login_required()
def conv_reunion_ajax(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'nueva_convocatoria':
            try:
                mensaje = ''
                if not get_plantillas(g_e).count() > 0:
                    mensaje = 'Es conveniente que te crees plantillas para que el proceso redactar convocatorias sea más sencillo.'
                conv = ConvReunion.objects.create(creador=g_e.gauser, entidad=g_e.ronda.entidad, plantilla=False,
                                                  nombre='ConvReunion ...')
                ActaReunion.objects.create(convocatoria=conv, nombre='Acta: %s' % conv.nombre)
                conv.texto_convocatoria = render_to_string('conv_texto.html', {'c': conv})
                conv.save()
                html = render_to_string('conv_accordion.html', {'convocatorias': [conv]})
                return JsonResponse({'ok': True, 'html': html, 'mensaje': mensaje})
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            conv = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'], plantilla=False)
            if conv.fecha_hora > timezone.now():
                plantillas = get_plantillas(g_e)
                if conv.basada_en in plantillas or conv.creador == g_e.gauser or g_e.has_permiso('w_conv_reunion'):
                    try:
                        cargos = Gauser_extra.objects.get(gauser=conv.convoca, ronda=g_e.ronda).cargos.all()
                    except:
                        cargos = []
                    puntos = PuntoConvReunion.objects.filter(convocatoria=conv)
                    html = render_to_string('conv_accordion_content.html', {'conv': conv, 'g_e': g_e, 'cargos': cargos,
                                                                            'plantillas': plantillas, 'puntos': puntos})

                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False})
            else:
                html = render_to_string('conv_accordion_content_lectura.html', {'conv': conv, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
        elif action == 'editar_conv':
            conv = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'], plantilla=False)
            plantillas = get_plantillas(g_e)
            if g_e.has_permiso('w_conv_reunion') or conv.creador == g_e.gauser:
                try:
                    cargos = Gauser_extra.objects.get(gauser=conv.convoca, ronda=g_e.ronda).cargos.all()
                except:
                    cargos = []
                puntos = PuntoConvReunion.objects.filter(convocatoria=conv)
                html = render_to_string('conv_accordion_content.html', {'conv': conv, 'g_e': g_e, 'cargos': cargos,
                                                                        'plantillas': plantillas, 'puntos': puntos})

                return JsonResponse({'ok': True, 'html': html})
            else:
                return JsonResponse({'ok': False})
        elif action == 'delete_conv_reunion':
            mensaje = ''
            try:
                convocatoria = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_reunion'])
                if g_e.has_permiso('d_conv_reunion') or convocatoria.creador == g_e.gauser:
                    try:
                        acta = ActaReunion.objects.get(convocatoria=convocatoria)
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
                            ActaReunion.objects.get(convocatoria=convocatoria).delete()
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
            conv = ConvReunion.objects.get(id=request.POST['convocatoria'], entidad=g_e.ronda.entidad, plantilla=False)
            if g_e.has_permiso('w_conv_reunion') or conv.creador == g_e.gauser:
                plantillas = get_plantillas(g_e)
                try:
                    plantilla = plantillas.get(id=request.POST['plantilla'])
                    conv.basada_en = plantilla
                    conv.texto_convocatoria = plantilla.texto_convocatoria
                    conv.convoca = plantilla.convoca
                    conv.convoca_text = plantilla.convoca.get_full_name()
                    conv.lugar = plantilla.lugar
                    conv.nombre = plantilla.nombre
                    conv.cargo_convocante = plantilla.cargo_convocante
                    conv.cargo_convocante_text = plantilla.cargo_convocante.cargo
                    conv.convocados.clear()
                    conv.convocados.add(*plantilla.convocados.all())
                    conv.convocados_text = plantilla.convocados_text
                    conv.save()
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso'})
                try:
                    cargos = Gauser_extra.objects.get(gauser=conv.convoca, ronda=g_e.ronda).cargos.all()
                except:
                    cargos = []
                PuntoConvReunion.objects.filter(convocatoria=conv).delete()
                for p in PuntoConvReunion.objects.filter(convocatoria=plantilla):
                    PuntoConvReunion.objects.create(convocatoria=conv, punto=p.punto, orden=p.orden)
                try:
                    acta = ActaReunion.objects.get(convocatoria=conv)
                    acta.nombre = 'Acta: %s' % conv.nombre
                    acta.save()
                except:
                    pass
                day_name = DIAS[conv.fecha_hora.weekday()][1].lower()
                day_num = conv.fecha_hora.day
                month_name = MESES[conv.fecha_hora.month - 1].lower()
                year = conv.fecha_hora.year
                datetime_time = conv.fecha_hora.strftime("%H:%M")
                lugar = conv.lugar if conv.lugar else '«lugar»'
                texto_convocados = human_readable_list(conv.convocados.all().values_list('nombre', flat=True))
                if not texto_convocados:
                    texto_convocados = conv.entidad.name
                cargo = conv.cargo_convocante.cargo if conv.cargo_convocante.cargo else '«cargo»'
                convoca = conv.convoca.get_full_name()
                puntos = PuntoConvReunion.objects.filter(convocatoria=conv)
                html = render_to_string('conv_accordion_content.html', {'conv': conv, 'g_e': g_e, 'cargos': cargos,
                                                                        'plantillas': plantillas, 'puntos': puntos})
                d = {'ok': True, 'html': html, 'nombre': conv.nombre, 'day_name': day_name, 'day_num': day_num,
                     'month_name': month_name, 'year': year, 'datetime_time': datetime_time, 'lugar': lugar,
                     'texto_convocados': texto_convocados, 'cargo': cargo, 'convoca': convoca}
                return JsonResponse(d)
        elif action == 'update_fecha_hora':
            try:
                convocatoria = ConvReunion.objects.get(id=request.POST['conv_reunion'], entidad=g_e.ronda.entidad)
                if g_e.has_permiso('w_conv_reunion') or convocatoria.creador == g_e.gauser:
                    fecha_hora = datetime.strptime(request.POST['fecha_hora'], "%d/%m/%Y %H:%M")
                    convocatoria.fecha_hora = fecha_hora
                    convocatoria.save()
                    day_name = DIAS[fecha_hora.weekday()][1].lower()
                    day_num = fecha_hora.day
                    month_name = MESES[fecha_hora.month - 1].lower()
                    year = fecha_hora.year
                    datetime_time = fecha_hora.strftime("%H:%M")
                    return JsonResponse(
                        {'ok': True, 'day_name': day_name, 'day_num': day_num, 'month_name': month_name,
                         'year': year, 'datetime_time': datetime_time})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_lugar_convocatoria':
            try:
                conv_reunion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_reunion'])
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.creador == g_e.gauser:
                    conv_reunion.lugar = request.POST['lugar']
                    conv_reunion.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_convoca_conv_reunion':
            try:
                convocatoria = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv'])
                if g_e.has_permiso('w_conv_reunion') or convocatoria.creador == g_e.gauser:
                    ge = Gauser_extra.objects.get(id=request.POST['convoca'], ronda=g_e.ronda)
                    convocatoria.convoca = ge.gauser
                    convocatoria.convoca_text = ge.gauser.get_full_name()
                    convocatoria.save()
                    cargos = {c[0]: c[1] for c in ge.cargos.all().values_list('id', 'cargo')}
                    return JsonResponse({'ok': True, 'cargos': cargos, 'convocante': ge.gauser.get_full_name()})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_cargo_conv_reunion':
            try:
                convocatoria = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_reunion'])
                if g_e.has_permiso('w_conv_reunion') or convocatoria.creador == g_e.gauser:
                    cargo_convocante = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
                    convocatoria.cargo_convocante = cargo_convocante
                    convocatoria.cargo_convocante_text = cargo_convocante.cargo
                    convocatoria.save()
                    return JsonResponse({'ok': True, 'cargo': cargo_convocante.cargo})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_redacta_acta':
            try:
                convocatoria = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv'])
                acta = ActaReunion.objects.get(convocatoria=convocatoria)
                if g_e.has_permiso('w_conv_reunion') or convocatoria.creador == g_e.gauser:
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
                conv_reunion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_reunion'])
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.creador == g_e.gauser:
                    subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad,
                                                             id__in=request.POST.getlist('subentidades[]'))
                    conv_reunion.convocados.clear()
                    conv_reunion.convocados.add(*subentidades)
                    texto = human_readable_list(conv_reunion.convocados.all().values_list('nombre', flat=True))
                    if not texto:
                        texto = "%s" % conv_reunion.entidad.name
                    conv_reunion.convocados_text = texto
                    conv_reunion.save()
                return JsonResponse({'ok': True, 'texto': texto})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_nombre_conv':
            try:
                conv_reunion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_reunion'])
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.creador == g_e.gauser:
                    conv_reunion.nombre = request.POST['nombre'].strip()
                    conv_reunion.save()
                    try:
                        acta = ActaReunion.objects.get(convocatoria=conv_reunion)
                        acta.nombre = 'Acta: %s' % conv_reunion.nombre
                        acta.save()
                    except:
                        pass
                return JsonResponse({'ok': True, 'nombre': conv_reunion.nombre})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_texto_conv_reunion':
            try:
                conv_reunion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_reunion'],
                                                       plantilla=False)
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.creador == g_e.gauser:
                    conv_reunion.texto_convocatoria = request.POST['texto']
                    conv_reunion.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la convocatoria'})
            except:
                return JsonResponse({'ok': False})

        elif action == 'update_orden_conv_reunion':
            try:
                punto = PuntoConvReunion.objects.get(id=request.POST['punto'])
                conv_reunion = punto.convocatoria
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.creador == g_e.gauser:
                    puntos = PuntoConvReunion.objects.filter(convocatoria=conv_reunion)
                    orden_nuevo = int(request.POST['orden'])
                    if orden_nuevo > puntos.count():
                        orden_nuevo = puntos.count()
                    elif orden_nuevo < 1:
                        orden_nuevo = 1
                    orden_viejo = punto.orden
                    if orden_nuevo < orden_viejo:
                        puntoscambiar = puntos.filter(orden__gte=orden_nuevo, orden__lt=orden_viejo)
                        for p in puntoscambiar:
                            p.orden = p.orden + 1
                            p.save()
                    elif orden_nuevo > orden_viejo:
                        puntoscambiar = puntos.filter(orden__gt=orden_viejo, orden__lte=orden_nuevo)
                        for p in puntoscambiar:
                            p.orden = p.orden - 1
                            p.save()
                    punto.orden = orden_nuevo
                    punto.save()
                    puntos = puntos.order_by('orden')
                    html = render_to_string('conv_accordion_content_puntos.html', {'puntos': puntos})
                    return JsonResponse({'ok': True, 'html': html, 'conv_reunion': conv_reunion.id})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_punto_conv_reunion':
            try:
                punto = PuntoConvReunion.objects.get(id=request.POST['punto'])
                conv_reunion = punto.convocatoria
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.creador == g_e.gauser:
                    punto.punto = request.POST['texto']
                    punto.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_punto_conv_reunion':
            try:
                conv_reunion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_reunion'])
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.creador == g_e.gauser:
                    orden_nuevo = PuntoConvReunion.objects.filter(convocatoria=conv_reunion).count() + 1
                    PuntoConvReunion.objects.create(convocatoria=conv_reunion, orden=orden_nuevo, punto='Texto ...')
                    puntos = PuntoConvReunion.objects.filter(convocatoria=conv_reunion)
                    html = render_to_string('conv_accordion_content_puntos.html', {'puntos': puntos})
                    return JsonResponse({'ok': True, 'html': html, 'conv_reunion': conv_reunion.id})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_fecha_firma_conv':
            try:
                conv_reunion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_reunion'])
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.creador == g_e.gauser:
                    fecha = datetime.strptime(request.POST['fecha'], '%d-%m-%Y')
                    conv_reunion.fecha = fecha
                    conv_reunion.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'del_punto_conv_reunion':
            try:
                punto = PuntoConvReunion.objects.get(id=request.POST['punto'])
                conv_reunion = punto.convocatoria
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.creador == g_e.gauser:
                    punto.delete()
                    return JsonResponse({'ok': True, 'punto': request.POST['punto']})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_buscar':
            plantillas = get_plantillas(g_e)
            try:
                html = render_to_string("conv_fieldset_buscar.html", {'plantillas_disponibles': plantillas, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'add_permisos_conv':
            try:
                plantilla = ConvReunion.objects.get(entidad=g_e.ronda.entidad, plantilla=True,
                                                    id=request.POST['plantilla'])
                if plantilla.permiso(g_e, 'edita_plantilla'):
                    ges, cs, ss = decode_selectgcs([request.POST['seleccionado']], g_e.ronda)
                    p, cr = PermisoReunion.objects.none(), False
                    for ge in ges:
                        p, cr = PermisoReunion.objects.get_or_create(plantilla=plantilla, gauser=ge.gauser)
                    for c in cs:
                        p, cr = PermisoReunion.objects.get_or_create(plantilla=plantilla, cargo=c)
                    if cr:
                        html_permiso = render_to_string("conv_template_accordion_content_permiso.html", {'p': p})
                    else:
                        html_permiso = ''
                    return JsonResponse({'ok': True, 'html_permiso': html_permiso, 'plantilla': plantilla.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_permisos_conv':
            try:
                pr = PermisoReunion.objects.get(plantilla__entidad=g_e.ronda.entidad,
                                                plantilla__plantilla=True, id=request.POST['permiso'])
                if pr.plantilla.permiso(g_e, 'edita_plantilla'):
                    estado = getattr(pr, request.POST['tipo'])
                    setattr(pr, request.POST['tipo'], not estado)
                    pr.save()
                    return JsonResponse({'ok': True, 'sino': ['No', 'Sí'][not estado]})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permisos para ejecutar la acción solicitada'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borra_permiso_plantilla':
            try:
                pr = PermisoReunion.objects.get(plantilla__entidad=g_e.ronda.entidad,
                                                plantilla__plantilla=True, id=request.POST['permiso'])
                if pr.plantilla.permiso(g_e, 'edita_plantilla'):
                    pr.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permisos para ejecutar la acción solicitada'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'send_email':
            try:
                convocatoria = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'],
                                                       plantilla=False)
                if g_e.has_permiso('m_conv_reunion') or convocatoria.creador == g_e.gauser:
                    asunto = 'Convocatoria: %s' % (convocatoria.nombre)
                    html = render_to_string('convreunion2pdf.html', {'convocatoria': convocatoria})
                    if convocatoria.convocados.all().count() > 0:
                        rs = [ge.gauser for ge in usuarios_ronda(g_e.ronda, subentidades=convocatoria.convocados.all())]
                    else:
                        rs = [ge.gauser for ge in usuarios_ronda(g_e.ronda)]
                    try:
                        nombre_etiqueta = convocatoria.basada_en.nombre
                    except:
                        nombre_etiqueta = "Convocatoria entidad %s" % g_e.ronda.entidad.name
                    etiqueta = Etiqueta.objects.get_or_create(nombre=nombre_etiqueta, propietario=g_e)
                    enviar_correo(etiqueta=etiqueta, asunto=asunto, texto_html=html, receptores=rs, emisor=g_e)
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para enviar el correo'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error al tratar de llevar a cabo la acción solicitada'})
        elif action == 'crea_evento':
            try:
                convocatoria = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'],
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


# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
# FUNCIONES RELACIONADAS CON LA REDACCIÓN DE ACTAS
# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
def busca_actas_redactar(request):
    g_e = request.session['gauser_extra']
    actas_entidad = ActaReunion.objects.filter(convocatoria__entidad=g_e.ronda.entidad)
    actas_id = [acta.id for acta in actas_entidad if acta.is_redactada_por(g_e)]
    actas = actas_entidad.filter(id__in=actas_id)
    # subentidades = g_e.subentidades.all()
    # if g_e.has_permiso('w_cualquier_acta_reunion'):
    #     actas = ActaReunion.objects.filter(convocatoria__entidad=g_e.ronda.entidad).distinct()
    # elif g_e.has_permiso('w_actas_subentidades_reunion'):
    #     actas = ActaReunion.objects.filter(convocatoria__convocados__in=subentidades).distinct()
    # elif g_e.has_permiso('w_sus_actas_reunion'):
    #     actas = ActaReunion.objects.filter(convocatoria__convoca=g_e.gauser,
    #                                        convocatoria__entidad=g_e.ronda.entidad).distinct()
    # else:
    #     return ActaReunion.objects.none()
    if actas.count() == 0:
        return ActaReunion.objects.none()
    try:
        aprobada_isnull = {'0': True, '1': False}[request.POST['aprobada']]
        qap = Q(fecha_aprobacion__isnull=aprobada_isnull)
    except:
        qap = Q()
    try:
        publicada = {'0': False, '1': True}[request.POST['publicada']]
        qpu = Q(publicada=publicada)
    except:
        qpu = Q()
    try:
        qin = Q(fecha_hora__gte=timezone.datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date())
    except:
        qin = Q(fecha_hora__gte=timezone.datetime.strptime('2000-1-1', '%Y-%m-%d').date())
    try:
        qfi = Q(fecha_hora__lte=timezone.datetime.strptime(request.POST['fin'], '%Y-%m-%d').date())
    except:
        qfi = Q(fecha_hora__lte=timezone.now().date() + timezone.timedelta(50))
    try:
        id = request.POST['plantilla']
        plantilla = ConvReunion.objects.get(entidad=g_e.ronda.entidad, plantilla=True, id=id)
        qpl = Q(basada_en=plantilla)
    except:
        qpl = Q()
    q1 = Q(entidad=g_e.ronda.entidad) & Q(plantilla=False) & qin & qfi & qpl
    convs = ConvReunion.objects.filter(q1)
    q_p1 = Q(convocatoria__in=convs)
    try:
        texto = request.POST['texto']
    except:
        texto = ''
    q_p2 = Q(punto__icontains=texto) | Q(texto_acta__icontains=texto)
    conv_ids = PuntoConvReunion.objects.filter(q_p1, q_p2).values_list('convocatoria__id', flat=True)
    return actas.filter(qap & qpu & Q(convocatoria__id__in=conv_ids)).distinct()


@permiso_required('acceso_redactar_actas_reunion')
def redactar_actas_reunion(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        if request.POST['action'] == 'pdf_acta':
            try:
                dce = get_dce(g_e.ronda.entidad, 'Configuración para actas de reunión')
                acta = ActaReunion.objects.get(id=request.POST['id_acta'], convocatoria__entidad=g_e.ronda.entidad)
                fecha = acta.convocatoria.fecha_hora.strftime('%Y%m%d')
                nombre_fichero = slugify('%s-%s' % (acta.nombre, fecha)) + '.pdf'
                p_d = request.POST['protocol_domain']
                c = render_to_string('acta_reunion2pdf.html', {'acta': acta, 'pdf': True, 'p_d': p_d})
                fich = pdfkit.from_string(c, False, dce.get_opciones)
                logger.info('Creado pdf: %s' % nombre_fichero)
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + nombre_fichero
                return response
            except:
                crear_aviso(request, False, 'No es posible generar el pdf del acta solicitada')
        elif request.POST['action'] == 'upload_archivo_xhr':
            try:
                n_files = int(request.POST['n_files'])
                acta = ActaReunion.objects.get(id=request.POST['acta'])
                for i in range(n_files):
                    fichero = request.FILES['archivo_xhr' + str(i)]
                    FileAttachedAR.objects.create(acta=acta, fich_name=fichero.name,
                                                  content_type=fichero.content_type, fichero=fichero)

                html = render_to_string('redactar_actas_reunion_accordion_content_tr_files.html', {'acta': acta})
                return JsonResponse({'ok': True, 'id': acta.id, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
        elif request.POST['action'] == 'descarga_gauss_file':
            acta = ActaReunion.objects.get(id=request.POST['id_acta'], convocatoria__entidad=g_e.ronda.entidad)
            faar = FileAttachedAR.objects.get(acta=acta, id=request.POST['faar'])
            response = HttpResponse(faar.fichero, content_type='%s' % faar.content_type)
            response['Content-Disposition'] = 'attachment; filename=%s' % faar.fich_name
            return response
        elif request.POST['action'] == 'update_page':
            try:
                actas = busca_actas_redactar(request)
                paginator = Paginator(actas, 15)
                buscar = {'0': False, '1': True}[request.POST['buscar']]
                actas_paginadas = paginator.page(int(request.POST['page']))
                html = render_to_string('redactar_actas_reunion_accordion.html',
                                        {'actas': actas_paginadas, 'buscar': buscar})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

    actas = busca_actas_redactar(request)
    paginator = Paginator(actas, 15)
    return render(request, "redactar_actas_reunion.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'search', 'texto': 'Buscar',
                            'title': 'Buscar actas',
                            'permiso': 'libre'},
                           ),
                      'formname': 'actas',
                      'actas': paginator.page(1),
                      'subentidades': g_e.subentidades.all(),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def redactar_actas_reunion_ajax(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'open_accordion':
            acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
            puntos = PuntoConvReunion.objects.filter(convocatoria=acta.convocatoria)
            if acta.onlyread:
                html_accordion = render_to_string('redactar_actas_reunion_accordion_content_firmado.html',
                                                  {'acta': acta, 'g_e': g_e, 'puntos': puntos})
                return JsonResponse({'html': html_accordion, 'ok': True})
            if not acta.preambulo:
                try:
                    redacta_ge = Gauser_extra.objects.get(ronda=g_e.ronda, gauser=acta.redacta)
                    cargo_redacta = redacta_ge.cargos.order_by('nivel')[0]
                except:
                    cargo_redacta = None
                p_conv = PuntoConvReunion.objects.filter(convocatoria=acta.convocatoria)
                html = render_to_string('redactar_actas_reunion_accordion_content_preambulo.html',
                                        {'convocatoria': acta.convocatoria, 'p_conv': p_conv, 'redacta': acta.redacta,
                                         'cargo_redacta': cargo_redacta})
                acta.preambulo = html
                epilogo_html = '<p>No habiendo más puntos que tratar finaliza la reunión a las ...</p>'
                acta.epilogo = epilogo_html
                acta.save()
            html_accordion = render_to_string('redactar_actas_reunion_accordion_content.html',
                                              {'acta': acta, 'g_e': g_e, 'puntos': puntos})
            return JsonResponse({'html': html_accordion, 'ok': True})
        elif action == 'update_preambulo':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if acta.is_redactada_por(g_e):
                    if acta.onlyread:
                        return JsonResponse({'ok': False, 'mensaje': 'El acta está publicada/aprobada'})
                    texto = request.POST['texto']
                    acta.preambulo = texto
                    acta.save()
                    borrar_firmas_acta(acta, g_e)
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_epilogo':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if acta.is_redactada_por(g_e):
                    if acta.onlyread:
                        return JsonResponse({'ok': False, 'mensaje': 'El acta está publicada/aprobada'})
                    texto = request.POST['texto']
                    acta.epilogo = texto
                    acta.save()
                    borrar_firmas_acta(acta, g_e)
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_punto_acta':
            try:
                punto = PuntoConvReunion.objects.get(id=request.POST['punto'])
                acta = ActaReunion.objects.get(convocatoria=punto.convocatoria, convocatoria__entidad=g_e.ronda.entidad)
                if acta.is_redactada_por(g_e):
                    if acta.onlyread:
                        return JsonResponse({'ok': False, 'mensaje': 'El acta está publicada/aprobada'})
                    texto = request.POST['texto']
                    punto.texto_acta = texto
                    punto.save()
                    borrar_firmas_acta(acta, g_e)
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_nombre_acta':
            try:
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if acta.is_redactada_por(g_e):
                    if acta.onlyread:
                        return JsonResponse({'ok': False})
                    acta.nombre = request.POST['nombre'].strip()
                    acta.save()
                    borrar_firmas_acta(acta, g_e)
                    return JsonResponse({'ok': True, 'nombre': acta.nombre})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_asistentes_reunion':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if acta.is_redactada_por(g_e):
                    if acta.onlyread:
                        return JsonResponse({'ok': False, 'mensaje': 'El acta está publicada/aprobada'})
                    asistente = Gauser_extra.objects.get(id=int(request.POST['asistente'][1:]), ronda=g_e.ronda)
                    if asistente not in acta.asistentes.all():
                        html_span = render_to_string('redactar_actas_reunion_accordion_content_asistente.html',
                                                     {'acta': acta, 'asistente': asistente})
                    else:
                        html_span = ''
                    acta.asistentes.add(asistente)
                    asistentes_text_list = [a.gauser.get_full_name() for a in acta.asistentes.all()]
                    acta.asistentes_text = human_readable_list(asistentes_text_list)
                    acta.save()
                    borrar_firmas_acta(acta, g_e)
                    return JsonResponse({'ok': True, 'acta': acta.id, 'html_span': html_span,
                                         'num_asistentes': acta.asistentes.all().count()})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'borrar_asistente':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if acta.is_redactada_por(g_e):
                    if acta.onlyread:
                        return JsonResponse({'ok': False, 'mensaje': 'El acta está publicada/aprobada'})
                    asistente = Gauser_extra.objects.get(id=int(request.POST['asistente']), ronda=g_e.ronda)
                    acta.asistentes.remove(asistente)
                    asistentes_text_list = [a.gauser.get_full_name() for a in acta.asistentes.all()]
                    acta.asistentes_text = human_readable_list(asistentes_text_list)
                    acta.save()
                    borrar_firmas_acta(acta, g_e)
                    return JsonResponse({'ok': True, 'acta': acta.id, 'asistente': asistente.id,
                                         'num_asistentes': acta.asistentes.all().count()})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_control_code':
            try:
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if acta.is_redactada_por(g_e):
                    if acta.onlyread:
                        return JsonResponse({'ok': False})
                    acta.control = request.POST['code']
                    acta.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'obtener_cargos_firmante':
            try:
                ges, cs, ss = decode_selectgcs([request.POST['firmante']], g_e.ronda)
                ge = ges[0]
                cargos = ge.cargos.all()
                cargos = {c[0]: c[1] for c in cargos.values_list('id', 'cargo')}
                return JsonResponse({'ok': True, 'cargos': cargos, 'acta': request.POST['acta']})
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_firmante_reunion':
            try:
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if acta.is_redactada_por(g_e):
                    if acta.onlyread:
                        return JsonResponse({'ok': False})
                    ges, cs, ss = decode_selectgcs([request.POST['firmante']], g_e.ronda)
                    ge = ges[0]
                    cargo = Cargo.objects.get(id=request.POST['cargo'], entidad=g_e.ronda.entidad).cargo
                    f = FirmaActa.objects.create(acta=acta, tipo=request.POST['tipo'], cargo=cargo,
                                                 firmante=ge.gauser.get_full_name(), ge=ge)
                    html = render_to_string('redactar_actas_reunion_accordion_content_firmante.html', {'f': f})
                    return JsonResponse({'ok': True, 'html': html, 'acta': acta.id})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'del_firmante_reunion':
            try:
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if acta.is_redactada_por(g_e):
                    if acta.onlyread:
                        return JsonResponse({'ok': False})
                    FirmaActa.objects.get(id=request.POST['firmante'], acta=acta).delete()
                    return JsonResponse({'ok': True, 'firmante': request.POST['firmante']})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_publicada':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if acta.is_redactada_por(g_e):
                    acta.publicada = not acta.publicada
                    acta.save()
                    return JsonResponse({'ok': True, 'publicada': acta.publicada, 'acta': acta.id})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_fecha_aprobacion':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if acta.is_redactada_por(g_e):
                    if request.POST['fecha_aprobacion'] == 'borrar':
                        acta.fecha_aprobacion = None
                        acta.save()
                        return JsonResponse({'ok': True, 'acta': acta.id, 'aprobada': False})
                    if acta.fecha_aprobacion:
                        return JsonResponse({'ok': False, 'mensaje': 17})
                    fecha_aprobacion = datetime.strptime(request.POST['fecha_aprobacion'], "%d/%m/%Y")
                    acta.fecha_aprobacion = fecha_aprobacion
                    acta.save()
                    return JsonResponse({'ok': True, 'acta': acta.id, 'aprobada': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 27})
        elif request.POST['action'] == 'borrar_faar':
            try:
                faar = FileAttachedAR.objects.get(id=request.POST['id'])
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=faar.acta.id)
                if acta.is_redactada_por(g_e) and acta.publicada == False:
                    os.remove(faar.fichero.path)
                    faar.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_buscar':
            plantillas = ConvReunion.objects.filter(entidad=g_e.ronda.entidad, plantilla=True)
            try:
                html = render_to_string("redactar_actas_fieldset_buscar.html",
                                        {'plantillas_disponibles': plantillas, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'send_email':
            try:
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if g_e.has_permiso('mail_actas') or acta.is_redactada_por(g_e):
                    asunto = 'Acta: %s' % (acta.convocatoria.nombre)
                    html = render_to_string('acta_reunion2pdf.html', {'acta': acta})
                    if acta.convocatoria.convocados.all().count() > 0:
                        rs = [ge.gauser for ge in
                              usuarios_ronda(g_e.ronda, subentidades=acta.convocatoria.convocados.all())]
                    else:
                        rs = [ge.gauser for ge in usuarios_ronda(g_e.ronda)]
                    try:
                        nombre_etiqueta = "Acta %s" % acta.convocatoria.basada_en.nombre
                    except:
                        nombre_etiqueta = "Acta entidad %s" % g_e.ronda.entidad.name
                    etiqueta = Etiqueta.objects.get_or_create(nombre=nombre_etiqueta, propietario=g_e)
                    enviar_correo(etiqueta=etiqueta, asunto=asunto, texto_html=html, receptores=rs, emisor=g_e)
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para enviar el correo'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error al tratar de llevar a cabo la acción solicitada'})


@permiso_required('acceso_control_asistencia_reunion')
def control_asistencia_reunion(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'check_code':
            try:
                acta = ActaReunion.objects.get(control=request.POST['code'], convocatoria__entidad=g_e.ronda.entidad)
                delta = timezone.now() - acta.convocatoria.fecha_hora
                delta_posible = timezone.timedelta(minutes=180)
                if delta < delta_posible:
                    acta.asistentes.add(g_e)
                    asistentes_text_list = [a.gauser.get_full_name() for a in acta.asistentes.all()]
                    acta.asistentes_text = human_readable_list(asistentes_text_list)
                    acta.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse(
                        {'ok': False, 'mensaje': 'Han transcurrido más de tres horas desde el comienzo de la reunión'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'El código introducido no es válido'})

    return render(request, "control_asistencia_reunion.html",
                  {
                      'formname': 'control_asistencia_reunion',
                  })


def borrar_firmas_acta(acta, g_e):
    firmas = FirmaActa.objects.filter(acta=acta, firmada=True)
    for firma in firmas:
        if firma.firmada:
            emisor = Gauser_extra.objects.get(gauser__username='gauss', ronda=firma.ge.ronda)
            etiqueta, c = Etiqueta.objects.get_or_create(propietario=emisor, nombre='aviso_acta_modificada')
            receptores = [firma.ge.gauser, ]
            asunto = 'Un acta que tienes firmada, ha sido modificada.'
            html = render_to_string('redactar_actas_reunion_correo_acta_modificada.html', {'firma': firma, 'g_e': g_e})
            enviar_correo(etiqueta=etiqueta, asunto=asunto, emisor=emisor, receptores=receptores, texto_html=html)
            if os.path.isfile(RUTA_BASE + firma.firma.url):
                os.remove(RUTA_BASE + firma.firma.url)
            firma.firma = None
            firma.firmada = False
            firma.save()
    return True


@permiso_required('acceso_firmar_actas_reunion')
def firmar_acta_reunion(request):
    g_e = request.session['gauser_extra']
    firmas_requeridas = FirmaActa.objects.filter(ge=g_e, firmada=False)

    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'mostrar_acta':
            try:
                firmaacta = firmas_requeridas.get(id=request.POST['firmaacta'])
                acta = firmaacta.acta
                html = render_to_string('acta_reunion2pdf.html', {'acta': acta})
                return JsonResponse(
                    {'ok': True, 'html': html, 'nombre': firmaacta.firmante})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error para encontrar FirmaActa'})
        elif request.POST['action'] == 'guarda_firma':
            try:
                firmaacta = firmas_requeridas.get(id=request.POST['firmaacta'])
                try:
                    os.remove(RUTA_BASE + firmaacta.firma.url)
                except:
                    pass
                firma_data = request.POST['firma']
                format, imgstr = firma_data.split(';base64,')
                ext = format.split('/')[-1]
                firmaacta.firma = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
                firmaacta.firmada = True
                firmaacta.texto_firmado = render_to_string('acta_reunion2pdf.html', {'acta': firmaacta.acta})
                firmaacta.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error para encontrar FirmaActa'})

    try:
        firmaacta = firmas_requeridas.get(id=request.GET['f'])
        return render(request, "firmar_acta_reunion.html",
                      {
                          'formname': 'firmar_acta_reunion',
                          'firmaacta': firmaacta,
                          'num_firmas': firmas_requeridas.count()
                      })
    except:
        if firmas_requeridas.count() == 1:
            firmaacta = firmas_requeridas[0]
            return render(request, "firmar_acta_reunion.html",
                          {
                              'formname': 'firmar_acta_reunion',
                              'firmaacta': firmaacta,
                              'num_firmas': 1
                          })
        else:
            return render(request, "firmar_acta_reunion_elegir.html",
                          {
                              'formname': 'elegir_acta_para_firma',
                              'firmas_requeridas': firmas_requeridas
                          })


# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
# FUNCIONES RELACIONADAS CON LA LECTURA DE ACTAS
# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
def busca_actas_leer(request):
    g_e = request.session['gauser_extra']
    try:
        qin = Q(fecha_hora__gte=datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date())
    except:
        qin = Q(fecha_hora__gte=datetime.strptime('2000-1-1', '%Y-%m-%d').date())
    try:
        qfi = Q(fecha_hora__lte=datetime.strptime(request.POST['fin'], '%Y-%m-%d').date())
    except:
        qfi = Q(fecha_hora__lte=timezone.now().date() + timezone.timedelta(50))
    try:
        plantilla = ConvReunion.objects.get(entidad=g_e.ronda.entidad, plantilla=True, id=request.POST['plantilla'])
        q = Q(entidad=g_e.ronda.entidad) & qin & qfi & Q(basada_en=plantilla) & Q(plantilla=False)
    except:
        q = Q(entidad=g_e.ronda.entidad) & qin & qfi & Q(plantilla=False)
    if g_e.has_permiso('r_actas_reunion'):
        convs = ConvReunion.objects.filter(q)
    else:
        convs = ConvReunion.objects.filter(q & Q(convocados__in=g_e.subentidades.all())).distinct()
    q_p1 = Q(convocatoria__in=convs)
    try:
        texto = request.POST['texto']
    except:
        texto = ''
    q_p2 = Q(punto__icontains=texto) | Q(texto_acta__icontains=texto)
    convs_id = PuntoConvReunion.objects.filter(q_p1, q_p2).values_list('convocatoria__id', flat=True)
    return ActaReunion.objects.filter(Q(convocatoria__id__in=convs_id), Q(publicada=True)).distinct()


@permiso_required('acceso_lectura_actas_reunion')
def lectura_actas_reunion(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'open_accordion':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                html = render_to_string('acta_reunion2pdf.html', {'acta': acta})
                return JsonResponse(
                    {'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error para encontrar el acta'})
        elif request.POST['action'] == 'ver_formulario_buscar':
            plantillas = ConvReunion.objects.filter(entidad=g_e.ronda.entidad, plantilla=True)
            try:
                html = render_to_string("leer_actas_fieldset_buscar.html",
                                        {'plantillas_disponibles': plantillas, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_page':
            try:
                actas = busca_actas_leer(request)
                paginator = Paginator(actas, 15)
                buscar = {'0': False, '1': True}[request.POST['buscar']]
                actas_paginadas = paginator.page(int(request.POST['page']))
                html = render_to_string('leer_actas_reunion_accordion.html', {'actas_publicadas': actas_paginadas,
                                                                              'buscar': buscar})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
    elif request.method == 'POST' and not request.is_ajax():
        if request.POST['action'] == 'descarga_gauss_file':
            acta = ActaReunion.objects.get(id=request.POST['id_acta'], convocatoria__entidad=g_e.ronda.entidad)
            faar = FileAttachedAR.objects.get(acta=acta, id=request.POST['faar'])
            response = HttpResponse(faar.fichero, content_type='%s' % faar.content_type)
            response['Content-Disposition'] = 'attachment; filename=%s' % faar.fich_name
            return response

    actas = busca_actas_leer(request)
    paginator = Paginator(actas, 15)
    return render(request, "leer_actas_reunion.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'search', 'texto': 'Buscar',
                            'title': 'Buscar actas',
                            'permiso': 'libre'},
                           ),
                      'formname': 'leer_acta_reunion',
                      'actas_publicadas': paginator.page(1)
                  })


a = ['ID', 'Hora de inicio', 'Hora de finalización', 'Nombre del centro educativo', 'Localidad del centro',
     'FLEXIBILIZACIÓN DE JORNADA Y TIPO DE JORNADA: Indicar si como medida del plan de contingencia existen cambios de horario de entrada y salida, recreos, etc. (flexibilización horaria).',
     'Si ha indicado que "Sí", señale a continuación las medidas que se han adoptado.',
     'FLEXIBILIZACIÓN DE JORNADA Y TIPO DE JORNADA: Indicar si existen medidas de escalonamiento de entradas y salidas,turnos de recreo…',
     'Si ha indicado que "Sí", señale a continuación las medidas que se han adoptado.2',
     'FLEXIBILIZACIÓN DE JORNADA Y TIPO DE JORNADA: Indicar si se ha modificado el tipo de jornada del centro.',
     'Si ha indicado que "Sí", señale a continuación la modificación de jornada adoptada.',
     'GRADO DE PRESENCIALIDAD: Indicar si en los niveles de alerta 1 y 2 (nueva normalidad) hay en su centro garantía de presencialidad en todos los niveles y etapas.',
     'GRADO DE PRESENCIALIDAD: Indicar si en los niveles de alerta 3 y 4 existirá en su centro la posibilidad de atender telemáticamente al alumnado que no pudiera asistir presencialmente.',
     'GRUPOS DE CONVIVENCIA ESTABLES. MEDIDAS DE LIMITACIÓN DE CONTACTOS: En los centros de Educación Infantil, Primaria y en Educación Especial, indicar si el centro se ha organizado en grupos de convi...',
     'Si ha indicado que "No", señale los motivos por los que el centro no se ha organizado en GCE y en qué niveles no se ha hecho.',
     'GRUPOS DE CONVIVENCIA ESTABLES. MEDIDAS DE LIMITACIÓN DE CONTACTOS: Indicar si se cumplen las ratios máximas previstas para los distintos niveles y etapas educativas en el PCG.',
     'Si ha indicado que "NO", indique los motivos por los que no se cumplen.',
     'DISTANCIAMIENTO EN AULAS Y OTRAS DEPENDENCIAS Y SERVICIOS. SEÑALIZACIÓN Y SECTORIZACIÓN DE LOS CENTROS: Indicar si se cumple el distanciamiento de 1,2 m. en las aulas de ESO, bachillerato, FP, ens...',
     'Si has indicado que "No", señale en cuántas aulas no se cumple.',
     'DISTANCIAMIENTO EN AULAS Y OTRAS DEPENDENCIAS Y SERVICIOS. SEÑALIZACIÓN Y SECTORIZACIÓN DE LOS CENTROS: Indicar si se cumplen las medidas de distanciamiento en el comedor escolar y en el servicio ...',
     'Si ha indicado que "No", señale en cuál de los servicios no se cumplen las medidas.',
     'DISTANCIAMIENTO EN AULAS Y OTRAS DEPENDENCIAS Y SERVICIOS. SEÑALIZACIÓN Y SECTORIZACIÓN DE LOS CENTROS: Indicar si se cumplen las medidas de distanciamiento en recreos y actividades al aire libre.',
     'Si ha indicado que "No", señale en cuál no se cumplen las medidas.',
     'DISTANCIAMIENTO EN AULAS Y OTRAS DEPENDENCIAS Y SERVICIOS. SEÑALIZACIÓN Y SECTORIZACIÓN DE LOS CENTROS: Indicar si existe la figura del coordinador de transporte escolar y si se cumple el distanci...',
     'Si ha indicado que "No", señale si no existe la figura del coordinador y/o qué medidas no se cumplen.',
     'DISTANCIAMIENTO EN AULAS Y OTRAS DEPENDENCIAS Y SERVICIOS. SEÑALIZACIÓN Y SECTORIZACIÓN DE LOS CENTROS: Indicar si existe la sectorización y señalización de los centros.',
     'Si ha indicado que "No", señale cuál de las dos medidas no existe en el centro.',
     'HORARIO LECTIVO DEL ALUMNO: Indicar si se respeta la distribución temporal ordinaria del horario lectivo del alumno.',
     'Si ha indicado que "No", señale los motivos por los que no se ha respetado.',
     'HORARIO LECTIVO DEL ALUMNO: Indicar si se han realizado actividades formativas del alumno en materia de sanidad, limpieza o similares, incluidas en los períodos lectivos correspondientes, recibien...',
     'HORARIO COMPLEMENTARIO DEL PROFESORADO: Indicar si se han realizado alteraciones en el horario complementario del profesorado,teniendo en cuenta su mayor dedicación de tiempo lectivo y el principi...',
     'HORARIO COMPLEMENTARIO DEL PROFESORADO: Indicar si se ha realizado la atención habitual a las familias.',
     'COORDINADOR/A COVID: Indicar si existe la figura del Coordinador/a Covid-Interlocutor con los servicios sanitarios.',
     'Si existe dicha figura, indique sus datos personales: Nombre, apellidos y correo electrónico.',
     'COORDINADOR/A COVID: Indicar si queda garantizada la correcta información y formación a toda la comunidad educativa de los procedimientos de implementación de los protocolos y medidas de seguridad...',
     'Si ha respondido que "No", indique qué aspectos no se han garantizado correctamente.',
     'EQUIPO DE TRABAJO/COMISIÓN DE SALUD: Indicar si se ha determinado la composición reglamentaria de ese equipo de trabajo: coordinador Covid, dirección del centro, miembro del personal de administra...',
     'ENTRADA AL CENTRO: Indicar si el PCC recoge la medida de prohibición de entrada al centro a toda persona con síntomas o que se encuentre en cuarentena domiciliaria.',
     'USO DE MASCARILLA: Indicar si se contempla el uso correcto de la mascarilla en cada uno de los siguientes casos:',
     'LIMPIEZA: Indicar si se incluye en el PCC el protocolo de limpieza.',
     'VENTILACIÓN: Indicar si se incluyen las medidas de ventilación (natural, mecánica, mediante filtros o purificadores).',
     'Si has respondido que "Sí", indica qué medidas de ventilación se han incluido en tu centro.',
     'VENTILACIÓN: Indicar si existen equipos de medición de CO2 o si se tiene previsto su uso.',
     'GESTIÓN DE RESIDUOS: Indicar si existe en su centro disponibilidad de papeleras con tapa y pedal y otras medidas para la gestión de residuos.',
     'USO DE BAÑOS: Indicar si el PCC hace referencia a un uso de los aseos acorde con las circunstancias del momento.',
     'TOMA DE TEMPERATURA: Indicar si existe un mecanismo establecido en el centro para la toma de temperatura de forma generalizada o aleatoriamente.',
     'GESTIÓN DE CASOS: Indicar si el PCC contempla un protocolo de actuación en caso de detectar síntomas en algún alumno, profesor o personal de administración y servicios, de acuerdo con el punto 4 d...',
     'REGISTRO DE ASISTENCIAS: Indicar si el PCC presenta los siguientes registros para facilitar el estudio de contactos:    -Asistencia ordinaria del alumno, resuelto a través de Racima.',
     'REGISTRO DE ASISTENCIAS: Indicar si el PCC presenta los siguientes registros para facilitar el estudio de contactos:    - Participación del alumno en servicios complementarios y en actividades ex...',
     'REGISTRO DE ASISTENCIAS: Indicar si el PCC presenta los siguientes registros para facilitar el estudio de contactos:  - Asistencia de personas ajenas al centro.']
