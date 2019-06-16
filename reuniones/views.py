# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# import urlparse
import urllib  # .parse import parse_qs # Sirve para leer los forms serializados y pasados por ajax
import base64
from datetime import datetime

import simplejson as json
from django.contrib.auth.decorators import login_required
from django.core.files.base import File, ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.text import slugify

from reuniones.models import *
from autenticar.control_acceso import permiso_required
from calendario.models import Vevent
from entidades.models import Subentidad, Gauser_extra
from gauss.funciones import html_to_pdf, human_readable_list
from gauss.rutas import MEDIA_ANAGRAMAS, MEDIA_REUNIONES, RUTA_BASE
from mensajes.models import Aviso, Mensaje, Etiqueta
from mensajes.views import crear_aviso, encolar_mensaje, crea_mensaje_cola


# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
# FUNCIONES RELACIONADAS CON LA CREACIÓN DE PLANTILLAS DE CONVOCATORIAS DE REUNIÓN
# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#

@permiso_required('acceso_conv_template')
def conv_template(request):
    g_e = request.session['gauser_extra']
    if g_e.has_permiso('w_conv_reunion'):
        configuraciones = ConvReunion.objects.filter(entidad=g_e.ronda.entidad, plantilla=True)
    else:
        configuraciones = ConvReunion.objects.filter(entidad=g_e.ronda.entidad, creador=g_e.gauser, plantilla=True)

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
            if g_e.has_permiso('w_conv_template') or conv_template.creador == g_e.gauser:
                if conv_template.convoca:
                    cargos = Gauser_extra.objects.get(gauser=conv_template.convoca, ronda=g_e.ronda).cargos.all()
                else:
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
            if g_e.has_permiso('w_conv_template') or conv_template.creador == g_e.gauser:
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
                if g_e.has_permiso('w_conv_template') or conv_template.creador == g_e.gauser:
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
                if g_e.has_permiso('w_conv_template') or conv_template.creador == g_e.gauser:
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
                if g_e.has_permiso('w_conv_template') or conv_template.creador == g_e.gauser:
                    conv_template.lugar = request.POST['lugar']
                    conv_template.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_subentidades_convocadas_conv_template':
            try:
                conv_template = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['conv_template'])
                if g_e.has_permiso('w_conv_template') or conv_template.creador == g_e.gauser:
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
                if g_e.has_permiso('w_conv_template') or conv_template.creador == g_e.gauser:
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
                if g_e.has_permiso('w_conv_template') or configuracion.creador == g_e.gauser:
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
                if g_e.has_permiso('w_conv_template') or conv_template.creador == g_e.gauser:
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
                if g_e.has_permiso('w_conv_template') or conv_template.creador == g_e.gauser:
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
                if g_e.has_permiso('w_conv_template') or conv_template.creador == g_e.gauser:
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
                if g_e.has_permiso('w_conv_reunion') or conv_reunion.creador == g_e.gauser:
                    punto.delete()
                    return JsonResponse({'ok': True, 'punto': request.POST['punto']})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para editar la configuración'})
            except:
                return JsonResponse({'ok': False})

        # elif action == 'update_cargos_convocados_configura_convocatoria':
        #     try:
        #         configuracion = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['configuracion'])
        #         if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
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
        #     if g_e.has_permiso('crea_convocatorias') or conv.creador == g_e.gauser:
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
        #         if g_e.has_permiso('edita_configuraciones_convocatorias') or configuracion.creador == g_e.gauser:
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

@permiso_required('acceso_conv_reunion')
def conv_reunion(request):
    g_e = request.session['gauser_extra']
    if g_e.has_permiso('c_conv_reunion'):
        convs = ConvReunion.objects.filter(entidad=g_e.ronda.entidad, plantilla=False)
    else:
        convs = ConvReunion.objects.filter(entidad=g_e.ronda.entidad, creador=g_e.gauser, plantilla=False)
    if request.method == 'POST':
        if request.POST['action'] == 'pdf_convocatoria':
            # try:
            convocatoria = ConvReunion.objects.get(id=request.POST['id_conv_reunion'], entidad=g_e.ronda.entidad)
            fichero = 'convocatoria_%s_%s' % (g_e.ronda.entidad.code, convocatoria.id)
            c = render_to_string('convreunion2pdf.html', {
                'convocatoria': convocatoria,
                'puntos': PuntoConvReunion.objects.filter(convocatoria=convocatoria),
                'MA': MEDIA_ANAGRAMAS,
            }, request=request)
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_REUNIONES, title=u'Convocatoria de reunión')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response
            # except:
            #     crear_aviso(request, False, 'No es posible generar el pdf de la convocatoria solicitada')

    return render(request, "conv.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'title': 'Crear una nueva convocatoria',
                            'permiso': 'c_conv_reunion'},
                           ),
                      'formname': 'convocatorias',
                      'convocatorias': convs,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def conv_reunion_ajax(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'nueva_convocatoria' and g_e.has_permiso('c_conv_reunion'):
            try:
                conv = ConvReunion.objects.create(creador=g_e.gauser, entidad=g_e.ronda.entidad, plantilla=False,
                                                  nombre='ConvReunion ...')
                ActaReunion.objects.create(convocatoria=conv, nombre='Acta: %s' % conv.nombre)
                conv.texto_convocatoria = render_to_string('conv_texto.html', {'c': conv})
                conv.save()
                html = render_to_string('conv_accordion.html', {'c': conv})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            conv = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'], plantilla=False)
            plantillas = ConvReunion.objects.filter(entidad=g_e.ronda.entidad, plantilla=True)
            if g_e.has_permiso('w_conv_reunion') or conv.creador == g_e.gauser:
                if conv.convoca:
                    cargos = Gauser_extra.objects.get(gauser=conv.convoca, ronda=g_e.ronda).cargos.all()
                else:
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
                plantillas = ConvReunion.objects.filter(entidad=g_e.ronda.entidad, plantilla=True)
                # try:
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
                if conv.convoca:
                    cargos = Gauser_extra.objects.get(gauser=conv.convoca, ronda=g_e.ronda).cargos.all()
                else:
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
                day_name = conv.fecha_hora.strftime('%A').lower()
                day_num = conv.fecha_hora.day
                month_name = conv.fecha_hora.strftime('%B').lower()
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
                # except:
                #     return JsonResponse({'ok': False})
        elif action == 'update_fecha_hora':
            try:
                convocatoria = ConvReunion.objects.get(id=request.POST['conv_reunion'], entidad=g_e.ronda.entidad)
                if g_e.has_permiso('w_conv_reunion') or convocatoria.creador == g_e.gauser:
                    fecha_hora = datetime.strptime(request.POST['fecha_hora'], "%d/%m/%Y %H:%M")
                    convocatoria.fecha_hora = fecha_hora
                    convocatoria.save()
                    day_name = fecha_hora.strftime('%A').lower()
                    day_num = fecha_hora.day
                    month_name = fecha_hora.strftime('%B').lower()
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






        elif action == 'send_email':
            try:
                convocatoria = ConvReunion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['convocatoria'],
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
                    encolar_mensaje(emisor=g_e, receptores=rs, asunto='ConvReunion: %s' % n, html=html,
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

# @permiso_required('acceso_redactar_actas_reunion')
def redactar_actas_reunion(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        if request.POST['action'] == 'pdf_acta':
            try:
                acta = ActaReunion.objects.get(id=request.POST['id_acta'], convocatoria__entidad=g_e.ronda.entidad)
                fecha = acta.convocatoria.fecha_hora.strftime('%Y%m%d')
                nombre_fichero = slugify('%s-%s' % (acta.nombre, fecha)) + '.pdf'
                # if acta.fecha_aprobacion or acta.publicada:
                #     fichero = acta.pdf.read()
                #     response = HttpResponse(fichero, content_type='application/pdf')
                #     response['Content-Disposition'] = 'attachment; filename=' + nombre_fichero
                #     return response
                # else:
                fichero = '%s/borradores/acta' % (g_e.ronda.entidad.code)
                firmas = FirmaActa.objects.filter(acta=acta)
                c = render_to_string('acta_reunion2pdf.html', {
                    'acta': acta,
                    'puntos': PuntoConvReunion.objects.filter(convocatoria=acta.convocatoria),
                    'MA': MEDIA_ANAGRAMAS,
                    'firmas': firmas,
                    'ruta_base': RUTA_BASE
                }, request=request)
                fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_REUNIONES, title=u'Acta de reunión')
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
        actas_publicadas = ActaReunion.objects.filter(convocatoria__entidad=g_e.ronda.entidad).distinct()
        # actas_sin_publicar = ActaReunion.objects.filter(convocatoria__entidad=g_e.ronda.entidad,
        #                                                 publicada=False).distinct()
    elif g_e.has_permiso('redacta_actas_subentidades'):
        actas_publicadas = ActaReunion.objects.filter(convocatoria__convocados__in=subentidades).distinct()
        # actas_sin_publicar = ActaReunion.objects.filter(convocatoria__convocados__in=subentidades,
        #                                                 publicada=False).distinct()
    elif g_e.has_permiso('redacta_sus_actas'):
        actas_publicadas = ActaReunion.objects.filter(convocatoria__convoca=g_e.gauser,
                                                      convocatoria__entidad=g_e.ronda.entidad).distinct()
        # actas_sin_publicar = ActaReunion.objects.filter(convocatoria__convoca=g_e.gauser,
        #                                                 convocatoria__entidad=g_e.ronda.entidad,
        #                                                 publicada=False).distinct()
    else:
        actas_publicadas = []
        actas_sin_publicar = []

    return render(request, "redactar_actas_reunion.html",
                  {
                      'formname': 'actas',
                      'actas_publicadas': actas_publicadas,
                      # 'actas_sin_publicar': actas_sin_publicar,
                      'subentidades': subentidades,
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
                acta.save()
            # g_es = acta.asistentes.all().values_list('id', 'gauser__last_name', 'gauser__first_name')
            # keys = ('id', 'text')
            # asistentes = json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in g_es])
            html_accordion = render_to_string('redactar_actas_reunion_accordion_content.html',
                                              {'acta': acta, 'g_e': g_e, 'puntos': puntos})
            return JsonResponse({'html': html_accordion, 'ok': True})
        elif action == 'update_preambulo':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if g_e.has_permiso('w_cualquier_acta_reunion') or acta.redacta == g_e.gauser:
                    if acta.onlyread:
                        return JsonResponse({'ok': False, 'mensaje': 'El acta está publicada/aprobada'})
                    texto = request.POST['texto']
                    acta.preambulo = texto
                    acta.save()
                    borrar_firmas_acta(acta)
                    return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_epilogo':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if g_e.has_permiso('w_cualquier_acta_reunion') or acta.redacta == g_e.gauser:
                    if acta.onlyread:
                        return JsonResponse({'ok': False, 'mensaje': 'El acta está publicada/aprobada'})
                    texto = request.POST['texto']
                    acta.epilogo = texto
                    acta.save()
                    borrar_firmas_acta(acta)
                    return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_punto_acta':
            try:
                punto = PuntoConvReunion.objects.get(id=request.POST['punto'])
                acta = ActaReunion.objects.get(convocatoria=punto.convocatoria, convocatoria__entidad=g_e.ronda.entidad)
                if g_e.has_permiso('w_cualquier_acta_reunion') or acta.redacta == g_e.gauser:
                    if acta.onlyread:
                        return JsonResponse({'ok': False, 'mensaje': 'El acta está publicada/aprobada'})
                    texto = request.POST['texto']
                    punto.texto_acta = texto
                    punto.save()
                    borrar_firmas_acta(acta)
                    return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_nombre_acta':
            try:
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if g_e.has_permiso('w_cualquier_acta_reunion') or acta.redacta == g_e.gauser:
                    if acta.onlyread:
                        return JsonResponse({'ok': False})
                    acta.nombre = request.POST['nombre'].strip()
                    acta.save()
                    borrar_firmas_acta(acta)
                    return JsonResponse({'ok': True, 'nombre': acta.nombre})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_asistentes_reunion':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                if g_e.has_permiso('w_cualquier_acta_reunion') or acta.redacta == g_e.gauser:
                    if acta.onlyread:
                        return JsonResponse({'ok': False, 'mensaje': 'El acta está publicada/aprobada'})
                    asistentes = Gauser_extra.objects.filter(ronda=g_e.ronda,
                                                             id__in=request.POST.getlist('asistentes[]'))
                    acta.asistentes.clear()
                    acta.asistentes.add(*asistentes)
                    asistentes_text_list = [a.gauser.get_full_name() for a in acta.asistentes.all()]
                    acta.asistentes_text = human_readable_list(asistentes_text_list)
                    acta.save()
                    borrar_firmas_acta(acta)
                    return JsonResponse({'ok': True, 'asist': asistentes.count()})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_control_code':
            try:
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if g_e.has_permiso('w_cualquier_acta_reunion') or acta.redacta == g_e.gauser:
                    if acta.onlyread:
                        return JsonResponse({'ok': False})
                    acta.control = request.POST['code']
                    acta.save()
                    return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'obtener_cargos_firmante':
            try:
                ge = Gauser_extra.objects.get(id=request.POST['firmante'], ronda=g_e.ronda)
                cargos = ge.cargos.all()
                cargos = {c[0]: c[1] for c in cargos.values_list('id', 'cargo')}
                return JsonResponse({'ok': True, 'cargos': cargos, 'acta': request.POST['acta']})
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_firmante_reunion':
            try:
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if g_e.has_permiso('w_cualquier_acta_reunion') or acta.redacta == g_e.gauser:
                    if acta.onlyread:
                        return JsonResponse({'ok': False})
                    ge = Gauser_extra.objects.get(id=request.POST['firmante'], ronda=g_e.ronda)
                    cargo = Cargo.objects.get(id=request.POST['cargo'], entidad=g_e.ronda.entidad).cargo
                    f = FirmaActa.objects.create(acta=acta, tipo=request.POST['tipo'], cargo=cargo,
                                                 firmante=ge.gauser.get_full_name(), ge=ge)
                    html = render_to_string('redactar_actas_reunion_accordion_content_firmante.html', {'f': f})
                    return JsonResponse({'ok': True, 'html': html, 'acta': acta.id})
            except:
                return JsonResponse({'ok': False})
        elif action == 'del_firmante_reunion':
            try:
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                if g_e.has_permiso('w_cualquier_acta_reunion') or acta.redacta == g_e.gauser:
                    if acta.onlyread:
                        return JsonResponse({'ok': False})
                    FirmaActa.objects.get(id=request.POST['firmante'], acta=acta).delete()
                    return JsonResponse({'ok': True, 'firmante': request.POST['firmante']})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_publicada':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                # if acta.fecha_aprobacion:
                #     return JsonResponse({'ok': False})
                acta.publicada = not acta.publicada
                acta.save()
                return JsonResponse({'ok': True, 'publicada': acta.publicada, 'acta': acta.id})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_fecha_aprobacion':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
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
            except:
                return JsonResponse({'ok': False, 'mensaje': 27})





        elif action == 'send_email':
            try:
                acta = ActaReunion.objects.get(convocatoria__entidad=g_e.ronda.entidad, id=request.POST['acta'])
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

def borrar_firmas_acta(acta):
    firmas = FirmaActa.objects.filter(acta=acta, firmada=True)
    for firma in firmas:
        emisor = Gauser_extra.objects.get(gauser__username='gauss', ronda=firma.ge.ronda)
        etiqueta, c = Etiqueta.objects.get_or_create(propietario=emisor, nombre='aviso_acta_modificada')
        receptores = [firma.ge.gauser,]
        fecha = timezone.now()
        asunto = 'Un acta que tienes firmada, ha sido modificada.'
        mensaje = '<p>El acta %s ha sido modificada y tu firma ha sido eliminada.</p><p>Debes releer el acta y firmarla de nuevo.</p>' %(firma.acta.nombre)
        mensaje_texto = 'El acta %s ha sido modificada y tu firma ha sido eliminada. Debes releer el acta y firmarla de nuevo.' % (firma.acta.nombre)
        mensaje = Mensaje.objects.create(borrador=False, emisor=emisor, fecha=fecha, asunto=asunto, mensaje=mensaje, mensaje_texto=mensaje_texto)
        mensaje.receptores.add(*receptores)
        mensaje.etiquetas.add(etiqueta)
        crea_mensaje_cola(mensaje)
        firma.firma = None
        if firma.firma:
            if os.path.isfile(firma.firma.path):
                os.remove(firma.firma.path)
        firma.save()
    return True

@permiso_required('acceso_firmar_actas_reunion')
def firmar_acta_reunion(request):
    g_e = request.session['gauser_extra']
    if request.method == 'GET' and 'f' in request.GET:
        firmas_requeridas = FirmaActa.objects.filter(id=request.GET['f'], ge=g_e, firmada=False)
    else:
        firmas_requeridas = FirmaActa.objects.filter(ge=g_e, firmada=False)
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'mostrar_acta':
            try:
                firmaacta = FirmaActa.objects.get(id=request.POST['firmaacta'], ge=g_e, firmada=False)
                acta = firmaacta.acta
                firmas = FirmaActa.objects.filter(acta=acta)
                html = render_to_string('acta_reunion2pdf.html', {
                    'acta': acta,
                    'puntos': PuntoConvReunion.objects.filter(convocatoria=acta.convocatoria),
                    'firmas': firmas,
                    'ruta_base': ''
                }, request=request)
                return JsonResponse(
                        {'ok': True, 'html': html, 'nombre': firmaacta.firmante})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error para encontrar FirmaActa'})
        elif request.POST['action'] == 'guarda_firma':
            try:
                firmaacta = FirmaActa.objects.get(id=request.POST['firmaacta'], ge=g_e, firmada=False)
                try:
                    os.remove( firmaacta.firma.path)
                except:
                    pass
                firma_data = request.POST['firma']
                format, imgstr = firma_data.split(';base64,')
                ext = format.split('/')[-1]
                firmaacta.firma = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
                firmaacta.firmada = True
                firmaacta.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error para encontrar FirmaActa'})

    if firmas_requeridas.count() == 1:
        firmaacta = firmas_requeridas[0]
        acta = firmaacta.acta
        firmas = FirmaActa.objects.filter(acta=acta)

        return render(request, "firmar_acta_reunion.html",
                      {
                          'formname': 'firmar_acta_reunion',
                          'firmaacta': firmaacta,
                          'acta': acta,
                          'puntos': PuntoConvReunion.objects.filter(convocatoria=acta.convocatoria),
                          'firmas': firmas,
                          'num_firmas': 1
                      })
    else:
        return render(request, "firmar_acta_reunion_elegir.html",
                  {
                      'formname': 'firmar_acta_reunion',
                      'firmas_requeridas': firmas_requeridas
                  })

# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#
# FUNCIONES RELACIONADAS CON LA LECTURA DE ACTAS
# ----------------------------------------------------------------------------------------------------#
# ----------------------------------------------------------------------------------------------------#


@permiso_required('acceso_lectura_actas_reunion')
def lectura_actas_reunion(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'open_accordion':
            try:
                acta = ActaReunion.objects.get(id=request.POST['acta'], convocatoria__entidad=g_e.ronda.entidad)
                firmas = FirmaActa.objects.filter(acta=acta)
                html = render_to_string('acta_reunion2pdf.html', {
                    'acta': acta,
                    'puntos': PuntoConvReunion.objects.filter(convocatoria=acta.convocatoria),
                    'firmas': firmas,
                    'ruta_base': ''
                }, request=request)
                return JsonResponse(
                    {'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error para encontrar el acta'})

    actas_publicadas = ActaReunion.objects.filter(convocatoria__entidad=g_e.ronda.entidad,
                                                    publicada=True).distinct()
    return render(request, "leer_actas_reunion.html",
                      {
                          'formname': 'leer_acta_reunion',
                          'actas_publicadas': actas_publicadas
                      })