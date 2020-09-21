# -*- coding: utf-8 -*-
import logging
import xlwt
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.timezone import localdate, timedelta, datetime
from django.template import RequestContext
from django.db.models import Q
from django.forms import ModelForm, ModelChoiceField, URLField, Form
from django.core.paginator import Paginator
import sys
from django.core import serializers

from gauss.constantes import CODE_CONTENEDOR
from autenticar.control_acceso import LogGauss, permiso_required, gauss_required
from inspeccion_educativa.models import *
from autenticar.views import crear_nombre_usuario
from mensajes.views import encolar_mensaje, crea_mensaje_cola

logger = logging.getLogger('django')


@gauss_required
def cargar_centros_mdb(request):
    from inspeccion_educativa.models import CENTROS
    # ("742", "C.R.A. ENTREVALLES", "C.R.A.", "BADARÁN")
    for centro in CENTROS:
        CentroMDB.objects.get_or_create(code_mdb=centro[0], tipo=centro[2], nombre=centro[1], localidad=centro[3])
    return HttpResponse('CentrosMDB creados')


# @permiso_required('acceso_miembros_entidad')
def tareas_ie(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_tarea_ie':
            if g_e.has_permiso('crea_tareas_ie'):
                tarea = TareaInspeccion.objects.create(ronda_centro=g_e.ronda.entidad.ronda, fecha=datetime.today(),
                                                       # asunto='Nueva actuación de Inspección Educativa',
                                                       observaciones='')
                itarea = InspectorTarea.objects.create(inspector=g_e, tarea=tarea, permiso='rwx')
                html = render_to_string('tareas_ie_accordion.html',
                                        {'buscadas': False, 'tareas_ie': [itarea], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            else:
                JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            try:
                itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad,
                                                    id=request.POST['id'])
                centros = CentroMDB.objects.all()
                html = render_to_string('tareas_ie_accordion_content.html',
                                        {'instarea': itarea, 'g_e': g_e, 'localizaciones': LOCALIZACIONES,
                                         'objetos': OBJETOS, 'tipos': TIPOS, 'funciones': FUNCIONES,
                                         'actuaciones': ACTUACIONES, 'niveles': NIVELES, 'sectores': SECTORES,
                                         'centros': centros, 'inspectores': INSPECTORES})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'update_selector':
            try:
                valor = request.POST['valor']
                campo = request.POST['campo']
                id = request.POST['id']
                itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=id)
                setattr(itarea.tarea, campo, valor)
                itarea.tarea.save()
                return JsonResponse({'ok': True, 'tipo': itarea.tarea.get_tipo_display()})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_centro':
            try:
                centro = CentroMDB.objects.get(id=request.POST['centro_id'])
                itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                itarea.tarea.centro_mdb = centro
                itarea.tarea.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_realizada':
            try:
                itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                itarea.tarea.realizada = not itarea.tarea.realizada
                itarea.tarea.save()
                centros = CentroMDB.objects.all()
                html = render_to_string('tareas_ie_accordion_content.html',
                                        {'instarea': itarea, 'g_e': g_e, 'localizaciones': LOCALIZACIONES,
                                         'objetos': OBJETOS, 'tipos': TIPOS, 'funciones': FUNCIONES,
                                         'actuaciones': ACTUACIONES, 'niveles': NIVELES, 'sectores': SECTORES,
                                         'centros': centros, 'inspectores': INSPECTORES})
                # if reparacion.resuelta:
                #     mensaje = u'El %s grabaste una incidencia de reparación en la que indicabas lo siguiente:<br><br><em>%s</em> <br>A fecha %s se ha indicado en GAUSS que %s ha solucionado la incidencia.<br> <strong>%s</strong><br>Gracias por tu atención' % (
                #         reparacion.fecha_comunicado.strftime("%d-%m-%Y"), reparacion.describir_problema,
                #         reparacion.fecha_solucion.strftime("%d-%m-%Y"), reparacion.reparador.gauser.get_full_name(),
                #         reparacion.describir_solucion)
                #     encolar_mensaje(emisor=g_e, receptores=[reparacion.detecta.gauser],
                #                     asunto='Reparación solicitada realizada', html=mensaje,
                #                     etiqueta='reparacion%s' % reparacion.id)
                return JsonResponse({'ok': True, 'valor': ['No', 'Sí'][itarea.tarea.realizada],
                                     'realizada': itarea.tarea.realizada, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_texto':
            try:
                itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                setattr(itarea.tarea, request.POST['campo'], request.POST['valor'])
                # if len(reparacion.describir_problema) < 5:
                #     reparacion.borrar = True
                # else:
                #     reparacion.borrar = False
                itarea.tarea.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_tarea_ie':
            try:
                itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                if g_e.has_permiso('borra_cualquier_tarea_ie'):
                    itarea.tarea.delete()  # Borrar la tarea y los inspectores asociados
                elif itarea.inspector.gauser == g_e.gauser and itarea.inspector.ronda.entidad == g_e.ronda.entidad:
                    if itarea.tarea.inspectortarea_set.all().count() == 1:
                        itarea.tarea.delete()  # Borrar la tarea y el inspector asociado
                    else:
                        itarea.delete()  # Borrar solo al inspector asociado a esa tarea
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})



        # elif request.POST['action'] == 'update_tipo':
        #     try:
        #         reparacion = InspectorTarea.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id'])
        #         reparacion.tipo = request.POST['valor']
        #         reparacion.save()
        #         return JsonResponse({'ok': True, 'valor': reparacion.get_tipo_display()})
        #     except:
        #         return JsonResponse({'ok': False})
        #
        # elif request.POST['action'] == 'enviar_mensaje':
        #     try:
        #         reparacion = InspectorTarea.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id'])
        #         reparacion.comunicado_a_reparador = True
        #         mensaje = render_to_string('tareas_ie_mail.html', {'reparacion': reparacion})
        #         # mensaje = u'El usuario %s ha grabado una incidencia de reparación. Los datos significativos son:<br><strong>Lugar:</strong> <em>%s</em> <br><strong>Descripción:</strong> <em>%s</em> <br>Gracias por tu atención.' % (
        #         #     g_e.gauser.get_full_name(), reparacion.lugar, reparacion.describir_problema)
        #         permisos = ['controla_tareas_ie_%s' % reparacion.tipo, 'controla_tareas_ie']
        #         cargos = Cargo.objects.filter(permisos__code_nombre__in=permisos, entidad=g_e.ronda.entidad).distinct()
        #
        #         receptores = Gauser_extra.objects.filter(Q(ronda=g_e.ronda), Q(permisos__code_nombre__in=permisos) | Q(
        #             cargos__in=cargos)).values_list('gauser__id', flat=True)
        #         encolar_mensaje(emisor=g_e, receptores=receptores, asunto='Solicitud de reparación', html=mensaje,
        #                         etiqueta='reparacion%s' % reparacion.id)
        #         reparacion.save()
        #         return JsonResponse({'ok': True})
        #     except:
        #         return JsonResponse({'ok': False})

        # elif request.POST['action'] == 'update_describir_solucion':
        #     try:
        #         reparacion = InspectorTarea.objects.get(detecta__entidad=g_e.ronda.entidad, id=request.POST['id'])
        #         reparacion.describir_solucion = request.POST['valor']
        #         reparacion.reparador = g_e
        #         reparacion.save()
        #         return JsonResponse({'ok': True})
        #     except:
        #         return JsonResponse({'ok': False})

        elif request.POST['action'] == 'busca_tareas_ie':
            try:
                try:
                    inicio = datetime.strptime(request.POST['id_fecha_inicio'], '%d-%m-%Y')
                except:
                    inicio = datetime.strptime('01-01-2000', '%d-%m-%Y')
                try:
                    fin = datetime.strptime(request.POST['id_fecha_fin'], '%d-%m-%Y')
                except:
                    fin = datetime.strptime('01-01-3000', '%d-%m-%Y')
                texto = request.POST['texto'] if request.POST['texto'] else ''
                tipos = [t[0] for t in TIPOS]
                tipo = [request.POST['tipo_busqueda']] if request.POST['tipo_busqueda'] in tipos else tipos
                q_texto = Q(tarea__observaciones__icontains=texto)  # | Q(describir_solucion__icontains=texto)
                q_inicio = Q(tarea__fecha__gte=inicio)
                q_fin = Q(tarea__fecha__lte=fin)
                q_tipo = Q(tarea__tipo__in=tipo)
                q_entidad = Q(inspector__ronda__entidad=g_e.ronda.entidad)
                its = InspectorTarea.objects.filter(q_entidad, q_texto, q_inicio, q_fin, q_tipo)
                html = render_to_string('tareas_ie_accordion.html', {'tareas_ie': its, 'g_e': g_e, 'buscadas': True})
                a = ', '.join(tipo)
                return JsonResponse({'ok': True, 'html': html, 'a': a})
            except:
                return JsonResponse({'ok': False})

    fecha_min = localdate() - timedelta(2)
    fecha_max = localdate() + timedelta(7)
    q = Q(tarea__realizada=False) | Q(tarea__fecha__gte=fecha_min, tarea__fecha__lte=fecha_max)
    tareas = InspectorTarea.objects.filter(Q(inspector=g_e) & q)
    logger.info('Entra en ' + request.META['PATH_INFO'])
    if 'ge' in request.GET:
        pass
    return render(request, "tareas_ie.html", {
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
              'title': 'Crear una nueva actuación de Inspección',
              'permiso': 'crea_tareas_ie'},
             {'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'Informe',
              'title': 'Generar informe con las reparaciones de la entidad',
              'permiso': 'genera_informe_tareas_ie'},
             ),
        'g_e': g_e, 'tareas_ie': tareas, 'tipos': TIPOS})


# @permiso_required('acceso_informes_ie')
def informes_ie(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_informe_ie':
            if g_e.has_permiso('crea_informes_ie') or True:  # El permiso da igual
                p = InformeInspeccion.objects.create(inspector=g_e, title='Nuevo informe de Inspección')
                html = render_to_string('informes_ie_accordion.html',
                                        {'buscadas': False, 'informes_ie': [p], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            else:
                JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            try:
                ie = InformeInspeccion.objects.get(inspector__ronda__entidad=g_e.ronda.entidad,
                                                           id=request.POST['id'])
                vs = VariantePII.objects.filter(plantilla__creador__ronda__entidad=g_e.ronda.entidad)
                html = render_to_string('informes_ie_accordion_content.html', {'ie': ie, 'g_e': g_e, 'vs': vs})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_texto':
            try:
                ie = InformeInspeccion.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                setattr(ie, request.POST['campo'], request.POST['valor'])
                ie.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_texto_variante2':
            try:
                id = request.POST['id']
                vp_ie = VariantePII.objects.get(informe__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                setattr(vp_ie, request.POST['campo'], request.POST['valor'])
                vp_ie.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'copiar_variante2':
            try:
                id = request.POST['id']
                vp_ie = VariantePII.objects.get(informe__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                nombre = vp_ie.nombre + ' (copia)'
                variante = VariantePII.objects.create(informe=vp_ie.informe, nombre=nombre, texto=vp_ie.texto)
                html = render_to_string('informes_ie_accordion_content_variante.html',
                                        {'p_ie': vp_ie.informe, 'variante': variante})
                return JsonResponse({'ok': True, 'html': html, 'p_ie': vp_ie.informe.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'select_variante2':
            try:
                id = request.POST['id']
                variante = VariantePII.objects.get(informe__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                html = render_to_string('informes_ie_accordion_content_variante.html',
                                        {'p_ie': variante.informe, 'variante': variante})
                return JsonResponse({'ok': True, 'html': html, 'p_ie': variante.informe.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_p_ie2':
            try:
                p_ie = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad,
                                                              id=request.POST['id'])
                if g_e.has_permiso('borra_cualquier_informe_ie') or g_e.gauser == p_ie.creador.gauser:
                    p_ie.delete()  # Borrar la informe y todas sus variantes
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_variante2':
            try:
                id = request.POST['id']
                variante = VariantePII.objects.get(informe__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                p_ie = variante.informe
                if g_e.has_permiso('borra_cualquier_informe_ie') or g_e.gauser == variante.informe.creador.gauser:
                    if p_ie.variantepii_set.all().count() > 1:
                        variante.delete()  # Borrar la variante
                    else:
                        return JsonResponse({'ok': False,
                                             'mensaje': 'No es posible el borrado. Al menos debe haber un modelo de informe.'})
                html = render_to_string('informes_ie_accordion_content_variante.html',
                                        {'p_ie': p_ie, 'variante': p_ie.variantepii_set.all()[0]})
                return JsonResponse({'ok': True, 'html': html, 'p_ie': variante.informe.id})
            except:
                return JsonResponse(
                    {'ok': False, 'mensaje': 'Se ha producido un error y no se ha podido hacer borrado'})



    # informes = PlantillaInformeInspeccion.objects.filter(creador__ronda__entidad=g_e.ronda.entidad)
    # logger.info('Entra en ' + request.META['PATH_INFO'])
    # if 'ge' in request.GET:
    #     pass
    # return render(request, "informes_ie.html", {
    #     'iconos':
    #         ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
    #           'title': 'Crear una nueva informe de Informe de Inspección',
    #           'permiso': 'acceso_informes_informes_ie'},
    #          ),
    #     'g_e': g_e, 'informes_ie': informes})





        elif request.POST['action'] == 'busca_informes_ie':
            try:
                try:
                    inicio = datetime.strptime(request.POST['id_fecha_inicio'], '%d-%m-%Y')
                except:
                    inicio = datetime.strptime('01-01-2000', '%d-%m-%Y')
                try:
                    fin = datetime.strptime(request.POST['id_fecha_fin'], '%d-%m-%Y')
                except:
                    fin = datetime.strptime('01-01-3000', '%d-%m-%Y')
                texto = request.POST['texto'] if request.POST['texto'] else ''
                tipos = [t[0] for t in TIPOS]
                tipo = [request.POST['tipo_busqueda']] if request.POST['tipo_busqueda'] in tipos else tipos
                q_texto = Q(tarea__observaciones__icontains=texto)  # | Q(describir_solucion__icontains=texto)
                q_inicio = Q(tarea__fecha__gte=inicio)
                q_fin = Q(tarea__fecha__lte=fin)
                q_tipo = Q(tarea__tipo__in=tipo)
                q_entidad = Q(inspector__ronda__entidad=g_e.ronda.entidad)
                its = InspectorTarea.objects.filter(q_entidad, q_texto, q_inicio, q_fin, q_tipo)
                html = render_to_string('informes_ie_accordion.html',
                                        {'informes_ie': its, 'g_e': g_e, 'buscadas': True})
                a = ', '.join(tipo)
                return JsonResponse({'ok': True, 'html': html, 'a': a})
            except:
                return JsonResponse({'ok': False})

    informes = InformeInspeccion.objects.filter(inspector=g_e)
    logger.info('Entra en ' + request.META['PATH_INFO'])
    if 'ge' in request.GET:
        pass
    return render(request, "informes_ie.html", {
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
              'title': 'Crear una nueva actuación de Inspección',
              'permiso': 'crea_informes_ie'},
             {'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'informe',
              'title': 'Generar informe con las reparaciones de la entidad',
              'permiso': 'genera_informe_informes_ie'},
             ),
        'g_e': g_e, 'informes_ie': informes, 'tipos': TIPOS})


# @permiso_required('acceso_plantillas_informes_ie')
def plantillas_ie(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_plantilla_ie':
            if g_e.has_permiso('crea_plantillas_ie') or True:  # El permiso da igual
                p = PlantillaInformeInspeccion.objects.create(creador=g_e)
                VariantePII.objects.create(plantilla=p, nombre='Modelo a utilizar en caso de ...')
                html = render_to_string('plantillas_ie_accordion.html',
                                        {'buscadas': False, 'plantillas_ie': [p], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            else:
                JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            try:
                p = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad,
                                                    id=request.POST['id'])
                v = p.variantepii_set.all()[0]
                html = render_to_string('plantillas_ie_accordion_content.html', {'p_ie': p, 'g_e': g_e, 'variante': v})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_texto':
            try:
                p_ie = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                setattr(p_ie, request.POST['campo'], request.POST['valor'])
                p_ie.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_texto_variante':
            try:
                id = request.POST['id']
                vp_ie = VariantePII.objects.get(plantilla__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                setattr(vp_ie, request.POST['campo'], request.POST['valor'])
                vp_ie.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'copiar_variante':
            try:
                id = request.POST['id']
                vp_ie = VariantePII.objects.get(plantilla__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                nombre = vp_ie.nombre + ' (copia)'
                variante = VariantePII.objects.create(plantilla=vp_ie.plantilla, nombre=nombre, texto=vp_ie.texto)
                html = render_to_string('plantillas_ie_accordion_content_variante.html', {'p_ie': vp_ie.plantilla, 'variante': variante})
                return JsonResponse({'ok': True, 'html': html, 'p_ie': vp_ie.plantilla.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'select_variante':
            try:
                id = request.POST['id']
                variante = VariantePII.objects.get(plantilla__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                html = render_to_string('plantillas_ie_accordion_content_variante.html', {'p_ie': variante.plantilla, 'variante': variante})
                return JsonResponse({'ok': True, 'html': html, 'p_ie': variante.plantilla.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_p_ie':
            try:
                p_ie = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                if g_e.has_permiso('borra_cualquier_plantilla_ie') or g_e.gauser == p_ie.creador.gauser:
                    p_ie.delete()  # Borrar la plantilla y todas sus variantes
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_variante':
            try:
                id = request.POST['id']
                variante = VariantePII.objects.get(plantilla__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                p_ie = variante.plantilla
                if g_e.has_permiso('borra_cualquier_plantilla_ie') or g_e.gauser == variante.plantilla.creador.gauser:
                    if p_ie.variantepii_set.all().count() > 1:
                        variante.delete()  # Borrar la variante
                    else:
                        return JsonResponse({'ok': False, 'mensaje': 'No es posible el borrado. Al menos debe haber un modelo de informe.'})
                html = render_to_string('plantillas_ie_accordion_content_variante.html',
                                        {'p_ie': p_ie, 'variante': p_ie.variantepii_set.all()[0]})
                return JsonResponse({'ok': True, 'html': html, 'p_ie': variante.plantilla.id})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error y no se ha podido hacer borrado'})

        elif request.POST['action'] == 'busca_plantillas_ie':
            try:
                try:
                    inicio = datetime.strptime(request.POST['id_fecha_inicio'], '%d-%m-%Y')
                except:
                    inicio = datetime.strptime('01-01-2000', '%d-%m-%Y')
                try:
                    fin = datetime.strptime(request.POST['id_fecha_fin'], '%d-%m-%Y')
                except:
                    fin = datetime.strptime('01-01-3000', '%d-%m-%Y')
                texto = request.POST['texto'] if request.POST['texto'] else ''
                tipos = [t[0] for t in TIPOS]
                tipo = [request.POST['tipo_busqueda']] if request.POST['tipo_busqueda'] in tipos else tipos
                q_texto = Q(tarea__observaciones__icontains=texto)  # | Q(describir_solucion__icontains=texto)
                q_inicio = Q(tarea__fecha__gte=inicio)
                q_fin = Q(tarea__fecha__lte=fin)
                q_tipo = Q(tarea__tipo__in=tipo)
                q_entidad = Q(inspector__ronda__entidad=g_e.ronda.entidad)
                its = InspectorTarea.objects.filter(q_entidad, q_texto, q_inicio, q_fin, q_tipo)
                html = render_to_string('plantillas_ie_accordion.html',
                                        {'plantillas_ie': its, 'g_e': g_e, 'buscadas': True})
                a = ', '.join(tipo)
                return JsonResponse({'ok': True, 'html': html, 'a': a})
            except:
                return JsonResponse({'ok': False})

    plantillas = PlantillaInformeInspeccion.objects.filter(creador__ronda__entidad=g_e.ronda.entidad)
    logger.info('Entra en ' + request.META['PATH_INFO'])
    if 'ge' in request.GET:
        pass
    return render(request, "plantillas_ie.html", {
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
              'title': 'Crear una nueva plantilla de Informe de Inspección',
              'permiso': 'acceso_plantillas_informes_ie'},
             ),
        'g_e': g_e, 'plantillas_ie': plantillas})
