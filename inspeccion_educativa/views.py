# -*- coding: utf-8 -*-
import logging
import xlwt
import pdfkit
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render, redirect
from django.utils.text import slugify
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

from gauss.funciones import html_to_pdf_options, usuarios_ronda, html_to_pdf_dce
from gauss.rutas import MEDIA_INSPECCION
from gauss.constantes import CODE_CONTENEDOR
from autenticar.control_acceso import LogGauss, permiso_required, gauss_required
from inspeccion_educativa.models import *
from inspeccion_educativa.templatetags.inspeccion_educativa_extras import get_puntos
from autenticar.views import crear_nombre_usuario
from mensajes.views import encolar_mensaje, crea_mensaje_cola
from entidades.tasks import carga_masiva_from_excel
from entidades.models import CargaMasiva, Cargo, DocConfEntidad
from mensajes.views import crear_aviso
from mensajes.models import Aviso

logger = logging.getLogger('django')


@gauss_required
def cargar_centros_mdb(request):
    from inspeccion_educativa.models import rel_code_MDB
    # ("742", "C.R.A. ENTREVALLES", "C.R.A.", "BADARÁN")
    errores_mdb = 0
    errs = 0
    for centro in rel_code_MDB:
        try:
            c = CentroMDB.objects.get(code_mdb=centro[1])
            c.code = centro[0]
            c.save()
            try:
                e = Entidad.objects.get(code=int(c.code))
                ts = TareaInspeccion.objects.filter(centro_mdb=c)
                for t in ts:
                    t.centro = e
                    t.save()
            except:
                errs += 1
        except:
            errores_mdb += 1
    return HttpResponse('CentrosMDB unidos a los code reales. %s errores mdb, %s errores tareas' % (errores_mdb, errs))
    # from inspeccion_educativa.models import CENTROS
    # # ("742", "C.R.A. ENTREVALLES", "C.R.A.", "BADARÁN")
    # for centro in CENTROS:
    #     CentroMDB.objects.get_or_create(code_mdb=centro[0], tipo=centro[2], nombre=centro[1], localidad=centro[3])
    # return HttpResponse('CentrosMDB creados')


def todos_lunes(ronda):
    d = ronda.inicio
    dias_sumar = 7 - d.weekday() if (
                                            7 - d.weekday()) < 7 else 0  # Días a sumar para obtener el primer lunes de la ronda
    lunes = d + timedelta(days=dias_sumar)  # First lunes
    fechas_lunes = []
    while lunes < ronda.fin:
        lunes += timedelta(days=7)
        fechas_lunes.append(lunes)
    return fechas_lunes


def get_inspectores(request):
    g_e = request.session["gauser_extra"]
    try:
        try:
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, clave_cargo='%s_ie' % g_e.ronda.entidad.code)
            cargo.clave_cargo = 'g_inspector_educacion'
            cargo.save()
        except:
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, clave_cargo='g_inspector_educacion')
        inspectores = usuarios_ronda(g_e.ronda, cargos=[cargo])
    except:
        Cargo.objects.create(entidad=g_e.ronda.entidad, cargo='Inspector de Educación',
                             borrable=False, clave_cargo='%s_ie' % g_e.ronda.entidad.code)
        inspectores = Gauser_extra.objects.none()
        msg = '''Se ha creado el cargo "Inspector de Educación" al que se deben añadir miembros para que
        se pueda asignar una actuación de Inspección a una persona.'''
        crear_aviso(request, False, msg)
    return inspectores


# @permiso_required('acceso_tareas_ie')
def tareas_ie(request):
    g_e = request.session["gauser_extra"]
    inspectores = get_inspectores(request)
    # inf_informe = 'Configuración informes emitidos por Inspección'
    # try:
    #     DocConfEntidad.objects.get(entidad=g_e.ronda.entidad, nombre=inf_informe)
    # except:
    #     dcepred = DocConfEntidad.objects.get(entidad=g_e.ronda.entidad, predeterminado=True)
    #     dcepred.pk = None
    #     dcepred.nombre = inf_informe
    #     dcepred.predeterminado = False
    #     dcepred.save()
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_tarea_ie':
            if g_e.has_permiso('crea_tareas_ie'):
                tarea = TareaInspeccion.objects.create(ronda_centro=g_e.ronda.entidad.ronda,
                                                       # asunto='Nueva actuación de Inspección Educativa',
                                                       observaciones='', fecha=datetime.today().date(), creador=g_e)
                itarea = InspectorTarea.objects.create(inspector=g_e, tarea=tarea, permiso='rwx', rol='1')
                html = render_to_string('tareas_ie_accordion.html',
                                        {'buscadas': False, 'tareas_ie': [itarea], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            else:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            try:
                itarea = InspectorTarea.objects.get(id=request.POST['id'])
                centrosmdb = CentroMDB.objects.all()
                centros = Entidad.objects.filter(organization=g_e.ronda.entidad.organization)
                inspectores = get_inspectores(request)
                html = render_to_string('tareas_ie_accordion_content.html',
                                        {'instarea': itarea, 'g_e': g_e, 'localizaciones': LOCALIZACIONES,
                                         'objetos': OBJETOS, 'tipos': TIPOS, 'funciones': FUNCIONES, 'roles': ROLES,
                                         'actuaciones': ACTUACIONES, 'centros': centros, 'inspectores': inspectores,
                                         'permisos': PERMISOS, 'centrosmdb': centrosmdb})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

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
                itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                if request.POST['campo'] == 'centro':
                    itarea.tarea.centro = Entidad.objects.get(id=request.POST['centro_id'])
                else:
                    itarea.tarea.centro_mdb = CentroMDB.objects.get(id=request.POST['centro_id'])
                itarea.tarea.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        # elif request.POST['action'] == 'update_realizada':
        #     try:
        #         itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
        #         itarea.tarea.realizada = not itarea.tarea.realizada
        #         itarea.tarea.save()
        #         centros = CentroMDB.objects.all()
        #         html = render_to_string('tareas_ie_accordion_content.html',
        #                                 {'instarea': itarea, 'g_e': g_e, 'localizaciones': LOCALIZACIONES,
        #                                  'objetos': OBJETOS, 'tipos': TIPOS, 'funciones': FUNCIONES,
        #                                  'actuaciones': ACTUACIONES, 'niveles': NIVELES, 'sectores': SECTORES,
        #                                  'centros': centros, 'inspectores': INSPECTORES})
        #         return JsonResponse({'ok': True, 'valor': ['No', 'Sí'][itarea.tarea.realizada],
        #                              'realizada': itarea.tarea.realizada, 'html': html})
        #     except:
        #         return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_texto':
            try:
                itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                setattr(itarea.tarea, request.POST['campo'], request.POST['valor'])
                itarea.tarea.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_fecha':
            try:
                itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                itarea.tarea.fecha = datetime.strptime(request.POST['valor'], '%Y-%m-%d').date()
                itarea.tarea.save()
                fecha = render_to_string('tareas_ie_accordion_fecha.html', {'tarea_ie': itarea})
                # return JsonResponse({'ok': True, 'fecha': itarea.tarea.fecha.strftime('%d-%m-%Y'), 'id': itarea.id})
                return JsonResponse({'ok': True, 'fecha': fecha, 'id': itarea.id})
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
        elif request.POST['action'] == 'add_participante':
            try:
                tarea = TareaInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad, id=request.POST['tarea'])
                instarea = InspectorTarea.objects.create(tarea=tarea)
                inspectores = get_inspectores(request)
                html = render_to_string('tareas_ie_accordion_content_tr.html',
                                        {'instarea': instarea, 'inspectores': inspectores, 'roles': ROLES,
                                         'permisos': PERMISOS, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html, 'tarea': tarea.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'mod_participante':
            try:
                instarea = InspectorTarea.objects.get(id=request.POST['instarea'])
                if instarea.tarea.creador.gauser == g_e.gauser or 'w' in instarea.tarea.permiso(g_e.gauser):
                    if request.POST['campo'] == 'inspector':
                        instarea.inspector = inspectores.get(id=request.POST['valor'])
                    else:
                        setattr(instarea, request.POST['campo'], request.POST['valor'])
                    instarea.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'del_participante':
            try:
                instarea = InspectorTarea.objects.get(id=request.POST['instarea'])
                id = instarea.id
                if instarea.tarea.creador.gauser == g_e.gauser or 'x' in instarea.tarea.permiso(g_e.gauser):
                    instarea.delete()
                    return JsonResponse({'ok': True, 'id': id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos de borrado'})
            except:
                return JsonResponse({'ok': False, 'msg': 'Se ha producido un error'})
        elif request.POST['action'] == 'copiar_tareas_ie':
            try:
                if g_e.has_permiso('crea_tareas_ie'):
                    itarea = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad,
                                                        id=request.POST['id'])
                    tarea = itarea.tarea
                    tarea.pk = None
                    tarea.asunto = tarea.asunto + ' (Copia)'
                    tarea.save()
                    itarea_nueva = InspectorTarea.objects.create(inspector=g_e, tarea=tarea, rol='1', permiso='rwx')
                    html = render_to_string('tareas_ie_accordion.html',
                                            {'buscadas': False, 'tareas_ie': [itarea_nueva], 'g_e': g_e, 'nueva': True})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso para crear tareas'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg':str(msg)})
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
                q_texto = Q(tarea__observaciones__icontains=texto) | Q(tarea__asunto__icontains=texto) | Q(
                    inspector__gauser__first_name__icontains=texto) | Q(inspector__gauser__last_name__icontains=texto)
                q_inicio = Q(tarea__fecha__gte=inicio)
                q_fin = Q(tarea__fecha__lte=fin)
                q_tipo = Q(tarea__tipo__in=tipo)
                if g_e.has_permiso('ve_cualquier_tarea_ie'):
                    if request.POST['filtro_inspector_tareas'] == 'general':
                        q_entidad = Q(inspector__ronda__entidad=g_e.ronda.entidad)
                    else:
                        inspector = Gauser_extra.objects.get(id=request.POST['filtro_inspector_tareas'])
                        q_entidad = Q(inspector__gauser=inspector.gauser)
                else:
                    q_entidad = Q(inspector__gauser=g_e.gauser)
                its = InspectorTarea.objects.filter(q_entidad, q_texto, q_inicio, q_fin, q_tipo)
                num_act = its.count()
                max = 100  # Número máximo de actuaciones a mostrar en una búsqueda
                if num_act > max:
                    exc_max = True
                    its = InspectorTarea.objects.none()
                else:
                    exc_max = False
                html = render_to_string('tareas_ie_accordion.html', {'tareas_ie': its, 'g_e': g_e, 'exc_max': exc_max,
                                                                     'buscadas': True, 'num_act': num_act, 'max': max})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'paginar_tareas_ie':
            q1 = Q(tarea__fecha__gte=g_e.ronda.inicio, tarea__fecha__lte=g_e.ronda.fin)
            if g_e.has_permiso('ve_cualquier_tarea_ie'):
                if request.POST['filtro_inspector_tareas'] == 'general':
                    q2 = Q(tarea__creador__ronda__entidad=g_e.ronda.entidad)
                else:
                    inspector = Gauser_extra.objects.get(id=request.POST['filtro_inspector_tareas'])
                    q2 = Q(tarea__creador__gauser=g_e.gauser) | Q(inspector__gauser=inspector.gauser)
            else:
                q2 = Q(tarea__creador__gauser=g_e.gauser) | Q(inspector__gauser=g_e.gauser)
            posibles_tareas_ie = InspectorTarea.objects.filter(q1 & q2)
            paginator = Paginator(posibles_tareas_ie, 25)
            tareas_ie = paginator.page(int(request.POST['page']))
            html = render_to_string('tareas_ie_accordion.html', {'tareas_ie': tareas_ie, 'pag': True})
            return JsonResponse({'ok': True, 'html': html})
            try:
                q1 = Q(tarea__fecha__gte=g_e.ronda.inicio, tarea__fecha__lte=g_e.ronda.fin)
                if g_e.has_permiso('ve_cualquier_tarea_ie'):
                    if request.POST['filtro_inspector_tareas'] == 'general':
                        q2 = Q(tarea__creador__ronda__entidad=g_e.ronda.entidad)
                    else:
                        inspector = Gauser_extra.objects.get(id=request.POST['filtro_inspector_tareas'])
                        q2 = Q(tarea__creador__gauser=g_e.gauser) | Q(inspector__gauser=inspector.gauser)
                else:
                    q2 = Q(tarea__creador__gauser=g_e.gauser) | Q(inspector__gauser=g_e.gauser)
                posibles_tareas_ie = InspectorTarea.objects.filter(q1 & q2)
                paginator = Paginator(posibles_tareas_ie, 25)
                tareas_ie = paginator.page(int(request.POST['page']))
                html = render_to_string('tareas_ie_accordion.html', {'tareas_ie': tareas_ie, 'pag': True})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_fati':
            try:
                fati = FileAttachedTI.objects.get(id=request.POST['id'])
                TareaInspeccion.objects.get(creador__gauser=g_e.gauser, id=fati.tarea.id)
                os.remove(fati.fichero.path)
                fati.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
    elif request.method == 'POST' and not request.is_ajax():
        if request.POST['action'] == 'genera_informe':
            instareas = InspectorTarea.objects.all()
            fichero = 'Informe_%s_%s' % (str(g_e.ronda.entidad.code), g_e.id)
            texto_html = render_to_string('informe_personal2pdf.html', {'instareas': instareas, 'title': fichero})
            ruta = MEDIA_INSPECCION + '%s/' % g_e.ronda.entidad.code
            opciones = {
                'orientation': 'Landscape',
                'page-size': 'A4',
                'margin-top': '5.5cm',
                'margin-right': '0.5cm',
                'margin-bottom': '0.5cm',
                'margin-left': '0.5cm',
            }
            fich = html_to_pdf_options(request, texto_html, opciones, fichero=fichero, media=ruta)
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            logger.info('%s, genera informe de inspección' % (g_e))
            return response
        elif request.POST['action'] == 'crea_informe_excel':
            fecha_inicio = datetime.strptime(request.POST['fecha_inicio_ti'], '%d-%m-%Y')
            fecha_fin = datetime.strptime(request.POST['fecha_fin_ti'], '%d-%m-%Y')
            if request.POST['inspector_informe'] == 'general':
                instareas = InspectorTarea.objects.filter(inspector__ronda__entidad=g_e.ronda.entidad,
                                                          tarea__fecha__gte=fecha_inicio,
                                                          tarea__fecha__lte=fecha_fin).order_by('inspector', 'tarea__fecha')
                fichero_xls = 'Informe_general_%s.xls' % str(g_e.ronda.entidad.code)
            else:
                inspector = inspectores.get(id=request.POST['inspector_informe'])
                instareas = InspectorTarea.objects.filter(inspector=inspector, tarea__fecha__gte=fecha_inicio,
                                                          tarea__fecha__lte=fecha_fin).order_by('tarea__fecha')
                fichero_xls = 'Informe_%s_%s.xls' % (str(g_e.ronda.entidad.code), slugify(inspector.gauser.get_full_name()))
            ruta = MEDIA_INSPECCION + str(g_e.ronda.entidad.code) + '/'
            if not os.path.exists(ruta):
                os.makedirs(ruta)
            wb = xlwt.Workbook()
            wr = wb.add_sheet('Tareas', cell_overwrite_ok=True)
            fila_excel_listado = 0
            estilo = xlwt.XFStyle()
            font = xlwt.Font()
            font.bold = True
            estilo.font = font
            date_format = xlwt.XFStyle()
            date_format.num_format_str = 'dd/mm/yyyy'
            col = 0
            # campos = ['inspector', 'fecha', 'sector', 'localizacion', 'nivel', 'actuacion', 'objeto', 'asunto', 'tipo',
            #           'funcion', 'participacion', 'centro']
            campos = ['Inspector', 'Fecha', 'Centro', 'Localidad', 'Lugar', 'Actuacion', 'Objeto', 'Asunto', 'Tipo',
                      'Funcion', 'Participantes']
            for campo in campos:
                wr.write(fila_excel_listado, col, campo, style=estilo)
                col += 1
            fila_excel_listado = 1
            for instarea in instareas:
                wr.write(fila_excel_listado, 0, instarea.inspector.gauser.get_full_name())
                wr.write(fila_excel_listado, 1, instarea.tarea.fecha, date_format)
                if instarea.tarea.centro:
                    wr.write(fila_excel_listado, 2, instarea.tarea.centro.name)
                    wr.write(fila_excel_listado, 3, instarea.tarea.centro.localidad)
                else:
                    wr.write(fila_excel_listado, 2, '')
                    wr.write(fila_excel_listado, 3, '')
                wr.write(fila_excel_listado, 4, instarea.tarea.get_localizacion_display())
                wr.write(fila_excel_listado, 5, instarea.tarea.get_actuacion_display())
                wr.write(fila_excel_listado, 6, instarea.tarea.get_objeto_display())
                wr.write(fila_excel_listado, 7, instarea.tarea.asunto)
                wr.write(fila_excel_listado, 8, instarea.tarea.get_tipo_display())
                wr.write(fila_excel_listado, 9, instarea.tarea.get_funcion_display())
                wr.write(fila_excel_listado, 10, instarea.tarea.colaboradores)
                # try:
                #     wr.write(fila_excel_listado, 11, instarea.tarea.centro.name)
                # except:
                #     wr.write(fila_excel_listado, 11, 'Tarea no ligada a un centro')
                fila_excel_listado += 1
            wb.save(ruta + fichero_xls)
            xlsfile = open(ruta + fichero_xls, 'rb')
            response = FileResponse(xlsfile, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=%s' % fichero_xls
            return response
        elif request.POST['action'] == 'crea_informe_pdf':
            inf_semanal = 'Configuración informes semanales de actuaciones'
            try:
                dce = DocConfEntidad.objects.get(entidad=g_e.ronda.entidad, nombre=inf_semanal)
            except:
                dce = DocConfEntidad.objects.get(entidad=g_e.ronda.entidad, predeterminado=True)
                dce.pk = None
                dce.nombre = inf_semanal
                dce.predeterminado = False
                dce.editable = False
                dce.save()
            fecha_inicio = datetime.strptime(request.POST['fecha_inicio_ti'], '%d-%m-%Y')
            fecha_fin = datetime.strptime(request.POST['fecha_fin_ti'], '%d-%m-%Y')
            general = True
            if request.POST['inspector_informe'] == 'general':
                instareas = InspectorTarea.objects.filter(inspector__ronda__entidad=g_e.ronda.entidad,
                                                          tarea__fecha__gte=fecha_inicio,
                                                          tarea__fecha__lte=fecha_fin).order_by('inspector', 'tarea__fecha')
                fichero = 'Informe_general_%s.pdf' % str(g_e.ronda.entidad.code)
            else:
                inspector = inspectores.get(id=request.POST['inspector_informe'])
                instareas = InspectorTarea.objects.filter(inspector=inspector, tarea__fecha__gte=fecha_inicio,
                                                          tarea__fecha__lte=fecha_fin).order_by('tarea__fecha')
                fichero = 'Informe_%s_%s.pdf' % (str(g_e.ronda.entidad.code), slugify(inspector.gauser.get_full_name()))
                general = False

            texto_html = render_to_string('informe_personal2pdf.html', {'instareas': instareas, 'fecha_fin': fecha_fin,
                                                                        'fecha_inicio': fecha_inicio,
                                                                        'es_informe_general': general})
            ruta = MEDIA_INSPECCION + '%s/' % g_e.ronda.entidad.code
            opciones = {
                'orientation': 'Landscape',
                'page-size': 'A4',
                'margin-top': '5.5cm',
                'margin-right': '0.5cm',
                'margin-bottom': '0.5cm',
                'margin-left': '0.5cm',
            }
            fich = html_to_pdf_dce(texto_html, dce, ruta, filename=fichero)
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero
            logger.info('%s, genera informe de inspección' % (g_e))
            return response
        elif request.POST['action'] == 'upload_archivo_xhr':
            try:
                n_files = int(request.POST['n_files'])
                ti = TareaInspeccion.objects.get(creador__gauser=g_e.gauser, id=request.POST['ti'])
                for i in range(n_files):
                    fichero = request.FILES['archivo_xhr' + str(i)]
                    FileAttachedTI.objects.create(tarea=ti, fich_name=fichero.name,
                                                  content_type=fichero.content_type, fichero=fichero)
                html = render_to_string('tareas_ie_accordion_content_tr_files.html', {'ti': ti})
                return JsonResponse({'ok': True, 'id': ti.id, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
        elif request.POST['action'] == 'descarga_gauss_file':
            try:
                ti = InspectorTarea.objects.get(inspector__ronda__entidad=g_e.ronda.entidad,
                                                id=request.POST['id_ti']).tarea
                fati = FileAttachedTI.objects.get(tarea=ti, id=request.POST['fati'])
                fich = fati.fichero
                response = HttpResponse(fich, content_type='%s' % fati.content_type)
                response['Content-Disposition'] = 'attachment; filename=%s' % fati.fich_name
                return response
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
    logger.info('Entra en ' + request.META['PATH_INFO'])
    # Para evitar que se añadan participaciones/colaboraciones vacías en las tareas de inspección
    # borramos las que no tienen asociado un inspector.
    InspectorTarea.objects.filter(tarea__creador=g_e, inspector__isnull=True).delete()
    q1 = Q(tarea__fecha__gte=g_e.ronda.inicio, tarea__fecha__lte=g_e.ronda.fin)
    if g_e.has_permiso('ve_cualquier_tarea_ie'):
        q2 = Q(tarea__creador__ronda__entidad=g_e.ronda.entidad)
    else:
        q2 = Q(tarea__creador__gauser=g_e.gauser) | Q(inspector__gauser=g_e.gauser)
    posibles_tareas_ie = InspectorTarea.objects.filter(q1 & q2)
    paginator = Paginator(posibles_tareas_ie, 25)
    tareas_ie = paginator.page(1)
    lunes = todos_lunes(g_e.ronda)
    semanas = []
    for l in lunes:
        v = l + timedelta(days=4)
        l_string = l.strftime("%d-%m-%Y")
        v_string = v.strftime("%d-%m-%Y")
        semanas.append((l_string, 'Semana del %s al %s' % (l_string, v_string)))
    return render(request, "tareas_ie.html", {
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
              'title': 'Crear una nueva actuación de Inspección',
              'permiso': 'crea_tareas_ie'},
             {'tipo': 'button', 'nombre': 'file-text-o', 'texto': 'Informe',
              'title': 'Generar informe con las tareas realizadas',
              'permiso': 'genera_informe_tareas_ie'},
             {'tipo': 'button', 'nombre': 'filter', 'texto': 'Filtro',
              'title': 'Filtrar las tareas por inspector',
              'permiso': 've_cualquier_tarea_ie'},
             {'tipo': 'button', 'nombre': 'search', 'texto': 'Buscar',
              'title': 'Buscar actuaciones de Inspección',
              'permiso': 'acceso_tareas_ie'},
             ),
        'g_e': g_e, 'tareas_ie': tareas_ie, 'tipos': TIPOS, 'pag': 1, 'formname': 'tareas_ie', 'semanas': semanas,
        'inspectores': inspectores})


# def carga_actuaciones_ie(request):
#     campos = ["Id", "Id INSPECTORES", "FECHA", "SECTOR", "CENTRO", "LOCALIZACIÓN", "Especificar otros",
#               "ACTUACIÓN",
#               "NIVEL", "OBJETO", "TEMA", "TIPO DE ACTUACIÓN", "FUNCIÓN INSPECTORA", "PARTICIPACIÓN",
#               "Especificar colaboración", "NOTAS ACLARATORIAS", "NOMBRE INSPECTOR"]
#     errores = ''
#     from horarios.models import CargaMasiva as CargaMasivaHorarios
#     import xlrd
#     cargas_necesarias = CargaMasivaHorarios.objects.filter(cargado=False)
#     for carga in cargas_necesarias:
#         f = carga.fichero.read()
#         book = xlrd.open_workbook(file_contents=f)
#         sheet = book.sheet_by_index(0)
#         Get the keys from line 5 of excel file:
# dict_names = {}
# for col_index in range(sheet.ncols):
#     dict_names[sheet.cell(0, col_index).value] = col_index
# return HttpResponse(sheet.cell(1, dict_names['FECHA'])
# for row_index in range(1, sheet.nrows):
#     try:
# a1 = sheet.cell_value(rowx=row_index, colx=dict_names['FECHA'])
# try:
#     fecha = datetime(*xlrd.xldate_as_tuple(a1, book.datemode))
# except:
#     fecha = None
# centro = CentroMDB.objects.get(code_mdb=str(int(sheet.cell(row_index, dict_names['CENTRO']).value)))
# datetime.strptime(sheet.cell(row_index, dict_names['FECHA']).value,
#                   '%d/%m/%Y')
# t = TareaInspeccion.objects.create(ronda_centro=carga.ronda,
#                                    localizacion=str(
#                                        sheet.cell(row_index, dict_names['LOCALIZACIÓN']).value),
#                                    nivel=str(sheet.cell(row_index, dict_names['NIVEL']).value),
#                                    actuacion=str(sheet.cell(row_index, dict_names['ACTUACIÓN']).value),
#                                    realizada=True,
#                                    inspector_mdb=str(
#                                        int(sheet.cell(row_index, dict_names['Id INSPECTORES']).value)),
#                                    fecha=fecha,
#                                    sector=str(sheet.cell(row_index, dict_names['SECTOR']).value),
#                                    centro_mdb=centro,
#                                    colaboracion=str(
#                                        sheet.cell(row_index, dict_names['Especificar colaboración']).value),
#                                    participacion=str(
#                                        sheet.cell(row_index, dict_names['PARTICIPACIÓN']).value),
#                                    funcion=str(
#                                        sheet.cell(row_index, dict_names['FUNCIÓN INSPECTORA']).value),
#                                    tipo=str(sheet.cell(row_index, dict_names['TIPO DE ACTUACIÓN']).value),
#                                    asunto=str(sheet.cell(row_index, dict_names['TEMA']).value),
#                                    objeto=str(sheet.cell(row_index, dict_names['OBJETO']).value),
#                                    )
# except:
#     errores += ', ' + str(sheet.cell(row_index, dict_names['Id']).value)
# carga.cargado = True
# carga.save()
# return HttpResponse(errores)

@permiso_required('acceso_informes_ie')
def get_informe_ie(request, id):
    ie = InformeInspeccion.objects.get(id=id)
    return JsonResponse({'asunto': ie.asunto, 'texto': ie.texto})


# @permiso_required('acceso_informes_ie')
def informes_ie(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_informe_ie':
            if g_e.has_permiso('crea_informes_ie') or True:  # El permiso da igual
                ie = InformeInspeccion.objects.create(inspector=g_e, title='Nuevo informe de Inspección')
                html = render_to_string('informes_ie_accordion.html',
                                        {'buscadas': False, 'informes_ie': [ie], 'g_e': g_e, 'nueva': True})
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
        elif request.POST['action'] == 'select_variante':
            try:
                va = request.POST['va']
                variante = VariantePII.objects.get(plantilla__creador__ronda__entidad=g_e.ronda.entidad, id=va)
                ie = InformeInspeccion.objects.get(inspector__gauser=g_e.gauser,
                                                   inspector__ronda__entidad=g_e.ronda.entidad,
                                                   id=request.POST['ie'])
                ie.asunto = variante.plantilla.asunto
                ie.destinatario = variante.plantilla.destinatario
                ie.variante = variante
                ie.texto = variante.texto
                ie.save()
                html = render_to_string('informes_ie_accordion_content_texto.html',
                                        {'ie': ie})
                return JsonResponse({'ok': True, 'html': html, 'ie': ie.id, 'destinatario': ie.destinatario,
                                     'asunto': ie.asunto})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_texto':
            try:
                id = request.POST['id']
                if request.POST['v'] == "0":
                    ie = InformeInspeccion.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=id)
                    setattr(ie, request.POST['campo'], request.POST['valor'])
                    ie.save()
                    html_v = render_to_string('informes_ie_accordion_content_texto_variables.html', {'ie': ie})
                else:
                    v = VariableII.objects.get(id=id, informe__inspector__ronda__entidad=g_e.ronda.entidad)
                    v.valor = request.POST['valor']
                    v.save()
                    ie = v.informe
                    html_v = False
                html = render_to_string('informes_ie_accordion_content_texto2pdf.html', {'ie': ie})
                num_v = ie.get_variables.count()
                return JsonResponse({'ok': True, 'html': html, 'ie': ie.id, 'html_v': html_v, 'num_v': num_v})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'copiar_ie':
            try:
                ie = InformeInspeccion.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                ie.pk = None
                ie.asunto = ie.asunto + ' (Copia)'
                ie.save()
                html = render_to_string('informes_ie_accordion.html',
                                        {'buscadas': False, 'informes_ie': [ie], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_ie':
            try:
                ie = InformeInspeccion.objects.get(inspector__ronda__entidad=g_e.ronda.entidad, id=request.POST['id'])
                if g_e.has_permiso('borra_informes_ie') or g_e.gauser == ie.inspector.gauser:
                    ie.delete()  # Borrar la informe y todas sus variantes
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_faii':
            try:
                faii = FileAttachedII.objects.get(id=request.POST['id'])
                InformeInspeccion.objects.get(inspector__gauser=g_e.gauser, id=faii.informe.id)
                os.remove(faii.fichero.path)
                faii.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
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
                ids = VariableII.objects.filter(valor__icontains=texto).values_list('informe__id', flat=True)
                q_texto = Q(texto__icontains=texto) | Q(asunto__icontains=texto) | Q(id__in=ids)
                q_inicio = Q(modificado__gte=inicio)
                q_fin = Q(modificado__lte=fin)
                # q_entidad = Q(inspector__ronda__entidad=g_e.ronda.entidad)
                q_entidad = Q(inspector__gauser=g_e.gauser)
                ies_base = InformeInspeccion.objects.filter(q_entidad, q_inicio, q_fin)
                ies = ies_base.filter(q_texto)
                if request.POST['tipo_busqueda']:
                    p = PlantillaInformeInspeccion.objects.get(id=request.POST['tipo_busqueda'])
                    ies = ies.filter(variante__plantilla=p)
                html = render_to_string('informes_ie_accordion.html',
                                        {'informes_ie': ies, 'g_e': g_e, 'buscadas': True})
                return JsonResponse({'ok': True, 'html': html, 'ids': ids.count()})
            except:
                return JsonResponse({'ok': False})
    elif request.method == 'POST' and not request.is_ajax():
        if request.POST['action'] == 'pdf_ie':
            doc_ie = 'Configuración de informes de Inspección Educativa'
            try:
                dce = DocConfEntidad.objects.get(entidad=g_e.ronda.entidad, nombre=doc_ie)
            except:
                try:
                    dce = DocConfEntidad.objects.get(entidad=g_e.ronda.entidad, predeterminado=True)
                except:
                    dce = DocConfEntidad.objects.filter(entidad=g_e.ronda.entidad)[0]
                    dce.predeterminado = True
                    dce.save()
                dce.pk = None
                dce.nombre = doc_ie
                dce.predeterminado = False
                dce.editable = False
                dce.save()
            ie = InformeInspeccion.objects.get(inspector__gauser=g_e.gauser, id=request.POST['id_ie'])
            if not ie.instarea:
                tarea = TareaInspeccion.objects.create(ronda_centro=g_e.ronda.entidad.ronda, tipo='HA', actuacion='IN',
                                                       observaciones='', fecha=ie.modificado, creador=g_e)
                itarea = InspectorTarea.objects.create(inspector=g_e, tarea=tarea, permiso='rwx', rol='1')
                ie.instarea = itarea
                ie.save()
            ie.instarea.tarea.asunto = ie.asunto
            ie.instarea.tarea.fecha = ie.modificado
            ie.instarea.tarea.save()
            c = render_to_string('informes_ie_accordion_content_texto2pdf.html', {'ie': ie, 'pdf': True})
            pdfkit.from_string(c, dce.url_pdf, dce.get_opciones)
            fich = open(dce.url_pdf, 'rb')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(ie.asunto)
            return response
        elif request.POST['action'] == 'upload_archivo_xhr':
            try:
                n_files = int(request.POST['n_files'])
                ie = InformeInspeccion.objects.get(inspector__gauser=g_e.gauser, id=request.POST['ie'])
                for i in range(n_files):
                    fichero = request.FILES['archivo_xhr' + str(i)]
                    FileAttachedII.objects.create(informe=ie, fich_name=fichero.name,
                                                  content_type=fichero.content_type, fichero=fichero)

                html = render_to_string('informes_ie_accordion_content_tr_files.html', {'ie': ie})
                return JsonResponse({'ok': True, 'id': ie.id, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
        elif request.POST['action'] == 'descarga_gauss_file':
            try:
                ie = InformeInspeccion.objects.get(inspector__gauser=g_e.gauser, id=request.POST['id_ie'])
                faii = FileAttachedII.objects.get(informe=ie, id=request.POST['faii'])
                fich = faii.fichero
                response = HttpResponse(fich, content_type='%s' % faii.content_type)
                response['Content-Disposition'] = 'attachment; filename=%s' % faii.fich_name
                return response
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

    informes = InformeInspeccion.objects.filter(inspector__gauser=g_e.gauser)
    logger.info('Entra en ' + request.META['PATH_INFO'])
    plantillas = PlantillaInformeInspeccion.objects.filter(creador__ronda__entidad=g_e.ronda.entidad)
    return render(request, "informes_ie.html", {
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
              'title': 'Crear una nueva actuación de Inspección',
              'permiso': 'crea_informes_ie'},
             {'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'informe',
              'title': 'Generar informe con las reparaciones de la entidad',
              'permiso': 'genera_informe_informes_ie'},
             ),
        'g_e': g_e, 'informes_ie': informes, 'plantillas': plantillas, 'formname': 'informes_inspeccion'})


@permiso_required('acceso_plantillas_informes_ie')
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
                p_ie = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad,
                                                              id=request.POST['id'])
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
                html = render_to_string('plantillas_ie_accordion_content_variante.html',
                                        {'p_ie': vp_ie.plantilla, 'variante': variante})
                return JsonResponse({'ok': True, 'html': html, 'p_ie': vp_ie.plantilla.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'select_variante':
            try:
                id = request.POST['id']
                variante = VariantePII.objects.get(plantilla__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                html = render_to_string('plantillas_ie_accordion_content_variante.html',
                                        {'p_ie': variante.plantilla, 'variante': variante, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html, 'p_ie': variante.plantilla.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'copiar_p_ie':
            try:
                p_ie = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad,
                                                              id=request.POST['id'])
                variantes = p_ie.variantepii_set.all()
                p_ie.pk = None
                p_ie.asunto = p_ie.asunto + ' (Copia)'
                p_ie.save()
                for v in variantes:
                    v.pk = None
                    v.plantilla = p_ie
                    v.save()
                html = render_to_string('plantillas_ie_accordion.html',
                                        {'buscadas': False, 'plantillas_ie': [p_ie], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_p_ie':
            try:
                p_ie = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad,
                                                              id=request.POST['id'])
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
                        return JsonResponse({'ok': False,
                                             'mensaje': 'No es posible el borrado. Al menos debe haber un modelo de informe.'})
                html = render_to_string('plantillas_ie_accordion_content_variante.html',
                                        {'p_ie': p_ie, 'variante': p_ie.variantepii_set.all()[0]})
                return JsonResponse({'ok': True, 'html': html, 'p_ie': variante.plantilla.id})
            except:
                return JsonResponse(
                    {'ok': False, 'mensaje': 'Se ha producido un error y no se ha podido hacer borrado'})

        elif request.POST['action'] == 'busca_plantillas_ie':
            # try:
            try:
                inicio = datetime.strptime(request.POST['id_fecha_inicio'], '%d-%m-%Y')
            except:
                inicio = datetime.strptime('01-01-2000', '%d-%m-%Y')
            try:
                fin = datetime.strptime(request.POST['id_fecha_fin'], '%d-%m-%Y')
            except:
                fin = datetime.strptime('01-01-3000', '%d-%m-%Y')
            texto = request.POST['texto'] if request.POST['texto'] else ''
            q_variante = Q(nombre__icontains=texto) | Q(texto__icontains=texto)
            ids = VariantePII.objects.filter(q_variante).distinct().values_list('plantilla__id', flat=True)
            q_varios = Q(destinatario__icontains=texto) | Q(asunto__icontains=texto) | Q(id__in=ids)
            q_inicio = Q(modificado__gte=inicio)
            q_fin = Q(modificado__lte=fin)
            q_entidad = Q(creador__ronda__entidad=g_e.ronda.entidad)
            piis_base = PlantillaInformeInspeccion.objects.filter(q_entidad & q_inicio & q_fin)
            piis = piis_base.filter(q_varios)
            # if request.POST['tipo_busqueda']:
            #     p = PlantillaInformeInspeccion.objects.get(id=request.POST['tipo_busqueda'])
            #     ies = ies.filter(variante__plantilla=p)
            html = render_to_string('plantillas_ie_accordion.html',
                                    {'plantillas_ie': piis, 'g_e': g_e, 'buscadas': True})
            return JsonResponse({'ok': True, 'html': html, 'ids': ids.count()})
        # except:
        #     return JsonResponse({'ok': False})

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
        'g_e': g_e, 'plantillas_ie': plantillas,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    })

def get_puntos_inspector(inspectores):
    resultados = {}
    for inspector in inspectores:
        try:
            resultados[inspector.id] = get_puntos(inspector)
        except:
            resultados[0] = 0
    return resultados

# @permiso_required('acceso_asignar_centros_inspeccion')
def asignar_centros_inspeccion(request):
    g_e = request.session["gauser_extra"]
    inspectores = get_inspectores(request)
    if request.method == 'POST':
        if request.POST['action'] == 'update_campo':
            try:
                ci = CentroInspeccionado.objects.get(ronda=g_e.ronda, id=request.POST['ci'])
                if request.POST['campo'] == 'zonai':
                    ci.zonai = request.POST['valor']
                    ci.save()
                    return JsonResponse({'ok': True})
                elif request.POST['campo'] == 'clasificado':
                    ci.clasificado = request.POST['valor']
                    ci.save()
                    return JsonResponse({'ok': True})
                elif request.POST['campo'] == 'puntos':
                    ci.puntos = request.POST['valor']
                    ci.save()
                    puntos = get_puntos_inspector([ci.inspectorasignado_set.all()[0].inspector])
                    return JsonResponse({'ok': True, 'puntos': puntos})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_campoia':
            try:
                ci = CentroInspeccionado.objects.get(ronda=g_e.ronda, id=request.POST['ci'])
                ia = ci.inspectorasignado_set.get(id=request.POST['ia'])
                if request.POST['campo'] == 'inspector':
                    insp_antiguo = ia.inspector
                    ia.inspector = inspectores.get(id=request.POST['valor'])
                    ia.save()
                    puntos= get_puntos_inspector([ia.inspector, insp_antiguo])
                    return JsonResponse({'ok': True, 'puntos': puntos})
                elif request.POST['campo'] == 'etapa':
                    ia.etapa = request.POST['valor']
                    ia.save()
                    return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_observaciones':
            try:
                ci = CentroInspeccionado.objects.get(ronda=g_e.ronda, id=request.POST['ci'])
                if ci.inspectorasignado_set.filter(inspector=g_e).count() > 0:
                    ci.observaciones = request.POST['texto']
                    ci.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No puedes cambiar las observaciones'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'busca_ci':
            try:
                logica = '' # Puede ser OR o AND
                if logica == 'OR':
                    palabras = request.POST['texto'].split()
                    cis_ronda = CentroInspeccionado.objects.filter(ronda=g_e.ronda)
                    cis = CentroInspeccionado.objects.none()
                    for palabra in palabras:
                        q1 = Q(centro__name__icontains=palabra) | Q(zonai__icontains=palabra) | Q(puntos__icontains=palabra) | Q(clasificado__icontains=palabra)
                        cis = cis.union(cis_ronda.filter(q1))
                        q2 = Q(etapa__icontains=palabra[:3]) | Q(inspector__gauser__first_name__icontains=palabra) | Q(inspector__gauser__last_name__icontains=palabra)
                        ias = InspectorAsignado.objects.filter(q2).values_list('cenins__id', flat=True)
                        cis = cis.union(cis_ronda.filter(id__in=ias))
                else:
                    palabras = request.POST['texto'].split()
                    cis_ronda = CentroInspeccionado.objects.filter(ronda=g_e.ronda)
                    resultados = []
                    for palabra in palabras:
                        q1 = Q(centro__name__icontains=palabra) | Q(zonai__icontains=palabra) | Q(
                            puntos__icontains=palabra) | Q(clasificado__icontains=palabra)
                        cis1 = cis_ronda.filter(q1).values_list('id', flat=True)
                        q2 = Q(etapa__icontains=palabra[:3]) | Q(inspector__gauser__first_name__icontains=palabra) | Q(
                            inspector__gauser__last_name__icontains=palabra)
                        cis2 = InspectorAsignado.objects.filter(q2).values_list('cenins__id', flat=True)
                        resultados.append(cis1.union(cis2))
                    cis_ids = cis_ronda.values_list('id', flat=True).intersection(*resultados)
                    cis = cis_ronda.filter(id__in=cis_ids)


                html = render_to_string('asignar_centros_inspector_buscar.html', {'cis': cis, 'buscar': True,
                                                                                  'inspectores': inspectores})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'paginar_cis':
            try:
                cis_posibles = CentroInspeccionado.objects.filter(ronda=g_e.ronda)
                paginator = Paginator(cis_posibles, 25)
                cis = paginator.page(int(request.POST['page']))
                html = render_to_string('asignar_centros_inspector_buscar.html', {'cis': cis, 'pag': True,
                                                                                  'inspectores': inspectores,
                                                                                  })
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif request.POST['action'] == 'listar_centros_sin_asignar':
            try:
                ias = InspectorAsignado.objects.filter(inspector__isnull=True)
                cis_ids = ias.values_list('cenins__centro__id', flat=True)
                cis_posibles = CentroInspeccionado.objects.filter(ronda=g_e.ronda, centro__in=cis_ids)
                paginator = Paginator(cis_posibles, 25)
                cis = paginator.page(1)
                html = render_to_string('asignar_centros_inspector_buscar.html', {'cis': cis, 'pag': True,
                                                                                  'inspectores': inspectores,
                                                                                  })
                return JsonResponse({'ok': True, 'html': html, 'num_centros_sin_asignar': ias.count()})
            except:
                return JsonResponse({'ok': False})

    organization = g_e.ronda.entidad.organization
    for e in Entidad.objects.filter(organization=organization):
        ci, c = CentroInspeccionado.objects.get_or_create(centro=e)
        if ci.ronda != g_e.ronda:
            ci.ronda = g_e.ronda
            ci.save()
        if ci.inspectorasignado_set.all().count() == 0:
            InspectorAsignado.objects.create(cenins=ci)
    cis_posibles = CentroInspeccionado.objects.filter(ronda=g_e.ronda)
    paginator = Paginator(cis_posibles, 25)
    cis = paginator.page(1)

    logger.info('Entra en ' + request.META['PATH_INFO'])
    if 'ge' in request.GET:
        pass
    return render(request, "asignar_centros_inspector.html", {
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
              'title': 'Crear una nueva plantilla de Informe de Inspección',
              'permiso': 'acceso_plantillas_informes_ie'},
             ),
        'g_e': g_e, 'cis': cis,
        'inspectores': inspectores,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
        'pag': 1,
        'num_centros': CentroInspeccionado.objects.filter(ronda=g_e.ronda).count(),
        'num_centros_sin_asignar': InspectorAsignado.objects.filter(inspector__isnull=True).count()
    })


@permiso_required('acceso_carga_masiva_inspeccion')
def carga_masiva_inspeccion(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'carga_masiva_centros_racima':
            crear_aviso(request, True, 'cm_ins1')
            logger.info('Carga de archivo de tipo: ' + request.FILES['file_centros_racima'].content_type)
            CargaMasiva.objects.create(ronda=g_e.ronda, fichero=request.FILES['file_centros_racima'],
                                       tipo='CENTROSRACIMA', g_e=g_e)
            crear_aviso(request, True, 'cm_ins2')
            carga_masiva_from_excel.apply_async(expires=300)
            crear_aviso(request, True, 'cm_ins3')
            crear_aviso(request, False, 'El archivo cargado puede tardar unos minutos en ser procesado.')
        elif action == 'carga_masiva_xls_mdb':
            from inspeccion_educativa.models import INSPECTORES_GAUSER
            logger.info('Carga de archivo de tipo: ' + request.FILES['file_xls_mdb'].content_type)
            carga = CargaMasiva.objects.create(ronda=g_e.ronda, fichero=request.FILES['file_xls_mdb'],
                                               tipo='CENTROSRACIMA', g_e=g_e, cargado=True)
            f = carga.fichero.read()
            import xlrd
            book = xlrd.open_workbook(file_contents=f)
            sheet = book.sheet_by_index(0)

            # Get the keys from line 5 of excel file:
            dict_names = {}
            for col_index in range(sheet.ncols):
                dict_names[sheet.cell(0, col_index).value] = col_index
            # return HttpResponse(sheet.cell(1, dict_names['FECHA'])
            for row_index in range(1, sheet.nrows):
                # try:
                a1 = sheet.cell_value(rowx=row_index, colx=dict_names['FECHA'])
                try:
                    fecha = datetime(*xlrd.xldate_as_tuple(a1, book.datemode))
                except:
                    fecha = None
                centro = CentroMDB.objects.get(code_mdb=str(int(sheet.cell(row_index, dict_names['CENTRO']).value)))
                try:
                    entidad = Entidad.objects.get(code=int(centro.code))
                except:
                    entidad = None
                # datetime.strptime(sheet.cell(row_index, dict_names['FECHA']).value,
                #                   '%d/%m/%Y')
                try:
                    TareaInspeccion.objects.get(clave_ex=sheet.cell(row_index, dict_names['Id']).value)
                except:
                    t = TareaInspeccion.objects.create(ronda_centro=carga.ronda,
                                                       clave_ex=sheet.cell(row_index, dict_names['Id']).value,
                                                       localizacion=str(
                                                           sheet.cell(row_index, dict_names['LOCALIZACIÓN']).value),
                                                       # nivel=str(sheet.cell(row_index, dict_names['NIVEL']).value),
                                                       actuacion=str(
                                                           sheet.cell(row_index, dict_names['ACTUACIÓN']).value),
                                                       realizada=True,
                                                       inspector_mdb=str(
                                                           int(sheet.cell(row_index,
                                                                          dict_names['Id INSPECTORES']).value)),
                                                       fecha=fecha,
                                                       # sector=str(sheet.cell(row_index, dict_names['SECTOR']).value),
                                                       centro_mdb=centro,
                                                       colaboracion=str(
                                                           sheet.cell(row_index,
                                                                      dict_names['Especificar colaboración']).value),
                                                       participacion=str(
                                                           sheet.cell(row_index, dict_names['PARTICIPACIÓN']).value),
                                                       funcion=str(
                                                           sheet.cell(row_index,
                                                                      dict_names['FUNCIÓN INSPECTORA']).value),
                                                       tipo=str(sheet.cell(row_index,
                                                                           dict_names['TIPO DE ACTUACIÓN']).value),
                                                       asunto=str(sheet.cell(row_index, dict_names['TEMA']).value),
                                                       objeto=str(sheet.cell(row_index, dict_names['OBJETO']).value),
                                                       creador=g_e
                                                       )
                    if entidad:
                        t.centro = entidad
                        t.save()
                    # crear_aviso(request, aceptado=False, INSPECTORES_GAUSER[t.inspector_mdb])
                    username = INSPECTORES_GAUSER[t.inspector_mdb]
                    try:
                        ge = Gauser_extra.objects.get(ronda=g_e.ronda, gauser__username=username)
                        t.creador = ge
                        t.save()
                    except:
                        ge = None
                    InspectorTarea.objects.create(tarea=t, inspector=ge, rol='1', permiso='rwx')

    return render(request, "carga_masiva_inspeccion.html",
                  {
                      'formname': 'carga_masiva_inspeccion',
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


# @permiso_required('acceso_actas_firmadas')
def actas_firmadas(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'change_entidad_buscar':
            try:
                entidad = Entidad.objects.get(id=request.POST['entidad'])
                if g_e.has_permiso('descarga_actas_evaluacion') or g_e.ronda == entidad.ronda:
                    acfs_posibles = ActaCursoFirmada.objects.filter(ronda__entidad=entidad)
                    paginator = Paginator(acfs_posibles, 25)
                    acfs = paginator.page(1)
                    html = render_to_string('actas_firmadas_lista.html', {'acfs': acfs, 'pag': 1})
                    opts = render_to_string('actas_firmadas_options.html', {'options': entidad.rondas.all()})
                    return JsonResponse({'ok': True, 'html': html, 'opts': opts})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos para esa búsqueda'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'change_ronda_buscar':
            try:
                ronda = Ronda.objects.get(id=request.POST['ronda'])
                if g_e.has_permiso('descarga_actas_evaluacion') or g_e.ronda.entidad == ronda.entidad:
                    acfs_posibles = ActaCursoFirmada.objects.filter(ronda=ronda)
                    paginator = Paginator(acfs_posibles, 25)
                    acfs = paginator.page(1)
                    html = render_to_string('actas_firmadas_lista.html', {'acfs': acfs, 'pag': 1})
                    opts = render_to_string('actas_firmadas_options.html', {'options': ronda.estudios.all()})
                    return JsonResponse({'ok': True, 'html': html, 'opts': opts})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos para esa búsqueda'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'change_curso_buscar':
            try:
                curso = Curso.objects.get(id=request.POST['curso'])
                if g_e.has_permiso('descarga_actas_evaluacion') or g_e.ronda.entidad == ronda.entidad:
                    acfs_posibles = ActaCursoFirmada.objects.filter(curso=curso)
                    paginator = Paginator(acfs_posibles, 25)
                    acfs = paginator.page(1)
                    html = render_to_string('actas_firmadas_lista.html', {'acfs': acfs, 'pag': 1})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos para esa búsqueda'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'change_ronda_subir':
            try:
                ronda = Ronda.objects.get(id=request.POST['ronda'], entidad=g_e.ronda.entidad)
                cursos = Curso.objects.filter(ronda=ronda)
                html = render_to_string('actas_firmadas_options.html', {'options': cursos})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': True, 'msg': str(msg)})
        elif action == 'acta_subir_button':
            try:
                ronda = Ronda.objects.get(id=request.POST['ronda_subir'], entidad=g_e.ronda.entidad)
                curso = Curso.objects.get(id=request.POST['curso_subir'], ronda__entidad=g_e.ronda.entidad)
                convocatoria = request.POST['convocatoria_subir']
                fichero = request.FILES['acta_subir']
                ActaCursoFirmada.objects.create(subido_por=g_e.gauser, ronda=ronda, curso=curso, acta=fichero,
                                                convocatoria=convocatoria, content_type=fichero.content_type)
            except Exception as msg:
                crear_aviso(request, False, 'Informa al administrador: %s' % str(msg))
        elif action == 'descarga_acta':
            try:
                if g_e.has_permiso('descarga_actas_evaluacion'):
                    acta = ActaCursoFirmada.objects.get(id=request.POST['acta'],
                                                        ronda__entidad__organization=g_e.ronda.entidad.organization)
                else:
                    acta = ActaCursoFirmada.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['acta'])
                response = HttpResponse(acta.acta, content_type=acta.content_type)
                response['Content-Disposition'] = 'attachment; filename=' + acta.fich_name
                return response
            except Exception as msg:
                crear_aviso(request, False, 'Informa al administrador: %s' % str(msg))
        elif action == 'borrar_acta':
            try:
                acta = ActaCursoFirmada.objects.get(subido_por=g_e.gauser, id=request.POST['acta'])
                if datetime.today().date() - acta.creado < timedelta(days=31):
                    os.remove(acta.acta.path)
                    acta.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'Lleva más de un mes subida'})
            except:
                return JsonResponse({'ok': False, 'msg': 'No tienes permisos para borrar el acta'})

    acfs_posibles = ActaCursoFirmada.objects.filter(ronda__entidad=g_e.ronda.entidad)
    paginator = Paginator(acfs_posibles, 25)
    acfs = paginator.page(1)
    entidades = Entidad.objects.filter(organization=g_e.ronda.entidad.organization)
    return render(request, "actas_firmadas.html",
                  {
                      'formname': 'actas_firmadas',
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'pag': 1,
                      'acfs': acfs,
                      'entidades': entidades,
                  })
