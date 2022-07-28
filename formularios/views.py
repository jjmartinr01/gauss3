# -*- coding: utf-8 -*-
# from datetime import datetime
import pdfkit
import xlrd
from django.contrib.auth import login
import simplejson as json
import pexpect
import os
import logging
import xlwt
from xlwt import Formula
from time import sleep
from django.utils.timezone import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
import html2text
from bs4 import BeautifulSoup

from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.text import slugify

from autenticar.control_acceso import permiso_required
from autenticar.models import Permiso, Menu_default
from autenticar.views import crea_menu_from_default
from inspeccion_educativa.models import InformeInspeccion
from mensajes.models import Aviso
from mensajes.views import crear_aviso
from formularios.models import *
from gauss.rutas import *
from gauss.funciones import get_dce
from entidades.models import Gauser_extra
from horarios.tasks import carga_masiva_from_file


def gfsi_id_orden(gform):
    gfsis = GformSectionInput.objects.filter(gformsection__gform=gform)
    return [{'id': gfsi.id, 'orden': gfsi.orden} for gfsi in gfsis], gfsis.count()


def gfs_id_orden(gform):
    gfss = GformSection.objects.filter(gform=gform)
    return [{'id': gfs.id, 'orden': gfs.orden} for gfs in gfss], gfss.count()


@permiso_required('acceso_formularios')
def formularios(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'update_page':
            try:
                gforms = Gform.objects.filter(
                    Q(propietario__gauser=g_e.gauser) | Q(colaboradores__gauser__in=[g_e.gauser])).distinct()
                paginator = Paginator(gforms, 15)
                formularios = paginator.page(int(request.POST['page']))
                html = render_to_string('formularios_accordion.html', {'formularios': formularios, 'pag': True})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'crea_formulario':
            if g_e.has_permiso('crea_formularios'):
                gform = Gform.objects.create(propietario=g_e)
                gfs = GformSection.objects.create(gform=gform, orden=1, description='Descripción')
                GformSectionInput.objects.create(gformsection=gfs, orden=1, pregunta='Texto pregunta ...', creador=g_e)
                html = render_to_string('formularios_accordion.html',
                                        {'buscadas': False, 'formularios': [gform], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            else:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            try:
                gform = Gform.objects.get(id=request.POST['id'])
                html = render_to_string('formularios_accordion_content.html', {'gform': gform, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'copy_gform':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                gform_copiado = Gform.objects.get(id=request.POST['gform'])
                gform_copiado.pk = None
                gform_copiado.save()
                for gfs_id in gform.gformsection_set.all().values_list('id', flat=True):
                    gfs = GformSection.objects.get(id=gfs_id)
                    gfs_copiado = GformSection.objects.get(id=gfs_id)
                    gfs_copiado.pk = None
                    gfs_copiado.gform = gform_copiado
                    gfs_copiado.save()
                    for gfsi_id in gfs.gformsectioninput_set.all().values_list('id', flat=True):
                        gfsi = GformSectionInput.objects.get(id=gfsi_id)
                        gfsi_copiado = GformSectionInput.objects.get(id=gfsi_id)
                        gfsi_copiado.pk = None
                        gfsi_copiado.creador = g_e
                        gfsi_copiado.gformsection = gfs_copiado
                        gfsi_copiado.save()
                        for gfsio_id in gfsi.gformsectioninputops_set.all().values_list('id', flat=True):
                            gfsio_copiado = GformSectionInputOps.objects.get(id=gfsio_id)
                            gfsio_copiado.pk = None
                            gfsio_copiado.gformsectioninput = gfsi_copiado
                            gfsio_copiado.save()
                html = render_to_string('formularios_accordion.html',
                                        {'buscadas': False, 'formularios': [gform_copiado], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'del_gform':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                if g_e.has_permiso('borra_formularios') or gform.propietario.gauser == g_e.gauser:
                    gform.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para borrar el formulario'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_nombre':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                if gform.propietario.gauser == g_e.gauser:
                    gform.nombre = request.POST['texto']
                    gform.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'El nombre solo puede ser cambiado por el propietario'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_destinatarios':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                if gform.is_propietario_o_colaborador(g_e):
                    gform.destinatarios = request.POST['valor']
                    gform.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_fecha_limite':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                if gform.is_propietario_o_colaborador(g_e):
                    gform.fecha_max_rellenado = datetime.strptime(request.POST['fecha'], '%Y-%m-%d')
                    gform.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'respuesta_booleana':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                if gform.is_propietario_o_colaborador(g_e):
                    nuevo_valor = not getattr(gform, request.POST['campo'])
                    setattr(gform, request.POST['campo'], nuevo_valor)
                    gform.save()
                    return JsonResponse({'ok': True, 'html': ['No', 'Sí'][nuevo_valor]})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_observaciones':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                if gform.is_propietario_o_colaborador(g_e):
                    gform.observaciones = request.POST['texto']
                    gform.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_template':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                if gform.is_propietario_o_colaborador(g_e):
                    gform.template = request.POST['texto']
                    gform.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_colaboradores':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                if gform.is_propietario_o_colaborador(g_e):
                    colaborador = Gauser_extra.objects.get(id=int(request.POST['ge'][1:]),
                                                           ronda__entidad__organization=g_e.ronda.entidad.organization)
                    gform.colaboradores.add(colaborador)
                    html_span = render_to_string('formularios_accordion_content_colaborador.html',
                                                 {'gform': gform, 'colaborador': colaborador})
                    return JsonResponse({'ok': True, 'gform': gform.id, 'html_span': html_span})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'del_colaborador':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                if gform.propietario.gauser == g_e.gauser:
                    colaborador = gform.colaboradores.get(id=request.POST['colaborador'])
                    colaborador_id = colaborador.id
                    gform.colaboradores.remove(colaborador)
                    return JsonResponse({'ok': True, 'gform': gform.id, 'colaborador': colaborador_id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'Un colaborador solo puede borrarlo el propietario'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'add_gform_destinatario':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                if gform.is_propietario_o_colaborador(g_e):
                    des = Gauser_extra.objects.get(id=int(request.POST['destinatario'][1:]),
                                                   ronda__entidad__organization=g_e.ronda.entidad.organization)
                    cor = Gauser_extra.objects.get(id=int(request.POST['corrector'][1:]),
                                                   ronda__entidad__organization=g_e.ronda.entidad.organization)
                    # Al añadir un destinatario se crea un GformResponde para ese destinatario
                    GformResponde.objects.create(gform=gform, g_e=des)
                    gd, c = GformDestinatario.objects.get_or_create(gform=gform, destinatario=des, corrector=cor)
                    if c:
                        html = render_to_string('formularios_accordion_content_destinatarios_tr.html', {'gd': gd})
                        return JsonResponse({'ok': True, 'gform': gform.id, 'html': html})
                    else:
                        return JsonResponse({'ok': False, 'gform': gform.id, 'msg': 'Ya cargados anteriormente'})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para añadir destinatarios'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif request.POST['action'] == 'del_gform_destinatario':
            try:
                gd = GformDestinatario.objects.get(id=request.POST['gd'])
                if gd.gform.is_propietario_o_colaborador(g_e):
                    if GformDestinatario.objects.filter(gform=gd.gform, destinatario=gd.destinatario).count() == 1:
                        GformResponde.objects.get(gform=gd.gform, g_e=gd.destinatario).delete()
                    gd_id = gd.id
                    gd.delete()
                    return JsonResponse({'ok': True, 'gd': gd_id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para borrar destinatarios'})
            except:
                return JsonResponse({'ok': False})
        # Posibles operaciones en una sección:
        # update_texto_gfs, add_gfsi_after_gfs, copy_gfs, add_gfs_after_gfs, del_gfs
        elif request.POST['action'] == 'update_texto_gfs':  # actualiza title y description
            try:
                gfs = GformSection.objects.get(id=request.POST['gfs'])
                if gfs.gform.is_propietario_o_colaborador(g_e):
                    setattr(gfs, request.POST['campo'], request.POST['texto'])
                    gfs.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'add_gfsi_after_gfs':
            try:
                gfs = GformSection.objects.get(id=request.POST['gfs'])
                if gfs.gform.is_propietario_o_colaborador(g_e):
                    try:
                        gfs_anterior = gfs.gform.gformsection_set.get(orden=gfs.orden - 1)
                        gfsi = gfs_anterior.gformsectioninput_set.all().last()
                        orden = gfsi.orden + 1  # Orden de la nueva gfsi
                    except:
                        # Si no no hay gfs_anterior es porque es el primer gfs y por tanto será la primera pregunta:
                        orden = 1  # Orden de la nueva gfsi
                    gfsis = GformSectionInput.objects.filter(gformsection__gform=gfs.gform, orden__gte=orden)
                    for g in gfsis:
                        g.orden += 1
                        g.save()
                    gfsi = GformSectionInput.objects.create(gformsection=gfs, orden=orden, creador=g_e)
                    html = render_to_string('formularios_accordion_content_ginputs_gi.html', {'gfsi': gfsi, 'g_e': g_e})
                    return JsonResponse(
                        {'ok': True, 'html': html, 'gfsi_id_orden': gfsi_id_orden(gfsi.gformsection.gform)})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'copy_gfs':
            try:
                gfs = GformSection.objects.get(id=request.POST['gfs'])
                if gfs.gform.is_propietario_o_colaborador(g_e):
                    orden = gfs.orden + 1  # El orden del nuevo GformSectionInput
                    gfss = GformSection.objects.filter(gform=gfs.gform, orden__gte=orden)
                    for g in gfss:
                        g.orden += 1
                        g.save()
                    gfs_nuevo = GformSection.objects.create(gform=gfs.gform, orden=orden, title=gfs.title,
                                                            description=gfs.description)
                    for g in gfs.gformsectioninput_set.all():
                        g.gformsection = gfs_nuevo
                        g.save()
                    html = render_to_string('formularios_accordion_content_gfs.html', {'gfs': gfs_nuevo})
                    return JsonResponse({'ok': True, 'html': html, 'gfs_id_orden': gfs_id_orden(gfs.gform)})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'add_gfs_after_gfs':
            try:
                gfs = GformSection.objects.get(id=request.POST['gfs'])
                if gfs.gform.is_propietario_o_colaborador(g_e):
                    orden = gfs.orden + 1  # El orden del nuevo GformSectionInput
                    gfss = GformSection.objects.filter(gform=gfs.gform, orden__gte=orden)
                    for g in gfss:
                        g.orden += 1
                        g.save()
                    gfs_nuevo = GformSection.objects.create(gform=gfs.gform, orden=orden)
                    for g in gfs.gformsectioninput_set.all():
                        g.gformsection = gfs_nuevo
                        g.save()
                    html = render_to_string('formularios_accordion_content_gfs.html', {'gfs': gfs_nuevo})
                    return JsonResponse({'ok': True, 'html': html, 'gfs_id_orden': gfs_id_orden(gfs.gform)})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'del_gfs':
            try:
                gfs = GformSection.objects.get(id=request.POST['gfs'])
                if gfs.gform.is_propietario_o_colaborador(g_e):
                    gform = gfs.gform
                    if gfs.orden > 1:
                        gfs_anterior = GformSection.objects.get(gform=gfs.gform, orden=(gfs.orden - 1))
                        gfsis = gfs.gformsectioninput_set.all()
                        for g in gfsis:
                            g.gformsection = gfs_anterior
                            g.save()
                        gfs.delete()
                        gfss_posteriores = gform.gformsection_set.filter(orden__gt=gfs_anterior.orden)
                        for gfs in gfss_posteriores:
                            gfs.orden -= 1
                            gfs.save()
                        return JsonResponse({'ok': True, 'gfs_id_orden': gfs_id_orden(gform)})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'No es posible borrar la primera sección'})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        # Posibles operaciones en una pregunta:
        # update_gfsi_el, update_gfsi_label, update_gfsio_opcion, update_gfsi_pregunta, add_gfsio, del_gfsio,
        # add_gfsi_after_gfsi, copy_gfsi, add_gfs_after_gfsi, del_gfsi

        elif request.POST['action'] == 'update_gfsi_el':  # actualiza el texto de la opción
            try:
                gfsi = GformSectionInput.objects.get(id=request.POST['gfsi'])
                if gfsi.gformsection.gform.propietario == g_e or gfsi.creador == g_e:
                    valor = int(''.join(c for c in request.POST['texto'] if c.isdigit()))
                    setattr(gfsi, request.POST['campo'], valor)
                    gfsi.save()
                    html = render_to_string('formularios_accordion_content_ginputs_gi_EL.html', {'gfsi': gfsi})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_gfsi_label':  # actualiza el texto de la opción
            try:
                gfsi = GformSectionInput.objects.get(id=request.POST['gfsi'])
                if gfsi.gformsection.gform.propietario == g_e or gfsi.creador == g_e:
                    setattr(gfsi, request.POST['campo'], request.POST['texto'])
                    gfsi.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_gfsio_opcion':  # actualiza el texto de la opción
            try:
                gfsio = GformSectionInputOps.objects.get(id=request.POST['gfsio'])
                if gfsio.gfsi.gformsection.gform.propietario == g_e or gfsio.gfsi.creador == g_e:
                    gfsio.opcion = request.POST['texto']
                    gfsio.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_gfsi_pregunta':  # actualiza el texto de la pregunta
            try:
                gfsi = GformSectionInput.objects.get(id=request.POST['gfsi'])
                if gfsi.gformsection.gform.propietario == g_e or gfsi.creador == g_e:
                    gfsi.pregunta = request.POST['texto']
                    gfsi.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'add_gfsio':
            try:
                gfsi = GformSectionInput.objects.get(id=request.POST['gfsi'])
                if gfsi.gformsection.gform.propietario == g_e or gfsi.creador == g_e:
                    orden = gfsi.gformsectioninputops_set.all().count() + 1
                    gfsio = GformSectionInputOps.objects.create(gformsectioninput=gfsi, orden=orden)
                    template = 'formularios_accordion_content_ginputs_gi_%s_op.html' % gfsi.tipo
                    html = render_to_string(template, {'gfsio': gfsio})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'del_gfsio':
            try:
                gfsio = GformSectionInputOps.objects.get(id=request.POST['gfsio'])
                if gfsio.gfsi.gformsection.gform.propietario == g_e or gfsio.gfsi.creador == g_e:
                    orden = gfsio.orden
                    gfsio.delete()
                    for g in gfsio.gformsectioninput.gformsectioninputops_set.filter(orden__gt=orden):
                        g.orden = orden
                        g.save()
                        orden += 1
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'select_tipo_gfsi':  # actualiza title y description
            try:
                gfsi = GformSectionInput.objects.get(id=request.POST['gfsi'])
                if gfsi.gformsection.gform.propietario == g_e or gfsi.creador == g_e:
                    gfsi.tipo = request.POST['tipo']
                    gfsi.save()
                    if gfsi.tipo in ['EM', 'SC', 'SO']:
                        GformSectionInputOps.objects.get_or_create(gformsectioninput=gfsi, orden=1)
                    template = 'formularios_accordion_content_ginputs_gi_%s.html' % gfsi.tipo
                    html = render_to_string(template, {'gfsi': gfsi})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'add_gfsi_after_gfsi':
            try:
                gfsi = GformSectionInput.objects.get(id=request.POST['gfsi'])
                if gfsi.gfs.gform.is_propietario_o_colaborador(g_e):
                    orden = gfsi.orden + 1  # El orden del nuevo GformSectionInput
                    gfsis = GformSectionInput.objects.filter(gformsection__gform=gfsi.gfs.gform, orden__gte=orden)
                    for g in gfsis:
                        g.orden += 1
                        g.save()
                    gfsi = GformSectionInput.objects.create(gformsection=gfsi.gformsection, orden=orden, creador=g_e)
                    html = render_to_string('formularios_accordion_content_ginputs_gi.html', {'gfsi': gfsi, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html, 'gfsi_id_orden': gfsi_id_orden(gfsi.gfs.gform)})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'copy_gfsi':
            try:
                gfsi = GformSectionInput.objects.get(id=request.POST['gfsi'])
                if gfsi.gfs.gform.is_propietario_o_colaborador(g_e):
                    gfsios = gfsi.gformsectioninputops_set.all()
                    orden = gfsi.orden + 1  # El orden del nuevo GformSectionInput
                    gfsis = GformSectionInput.objects.filter(gformsection__gform=gfsi.gfs.gform, orden__gte=orden)
                    for g in gfsis:
                        g.orden += 1
                        g.save()
                    gfsi.pk = None
                    gfsi.creador = g_e
                    gfsi.orden = orden
                    gfsi.save()
                    for gfsio in gfsios:
                        gfsio.pk = None
                        gfsio.gformsectioninput = gfsi
                        gfsio.save()
                    html = render_to_string('formularios_accordion_content_ginputs_gi.html', {'gfsi': gfsi, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html, 'gfsi_id_orden': gfsi_id_orden(gfsi.gfs.gform)})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_gfsi_requerida':
            try:
                gfsi = GformSectionInput.objects.get(id=request.POST['gfsi'])
                if gfsi.gformsection.gform.propietario == g_e or gfsi.creador == g_e:
                    gfsi.requerida = not gfsi.requerida
                    gfsi.save()
                    texto = ['Requerida: No', 'Requerida: Sí'][gfsi.requerida]
                    return JsonResponse({'ok': True, 'texto': texto})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'add_gfs_after_gfsi':
            try:
                gfsi = GformSectionInput.objects.get(id=request.POST['gfsi'])
                if gfsi.gfs.gform.is_propietario_o_colaborador(g_e):
                    gform = gfsi.gformsection.gform
                    orden = gfsi.gformsection.orden + 1  # El orden del nuevo GformSection
                    gfss = gform.gformsection_set.filter(orden__gte=orden)
                    for g in gfss:
                        g.orden += 1
                        g.save()
                    gfs = GformSection.objects.create(gform=gform, orden=orden)
                    gfsis = GformSectionInput.objects.filter(gformsection__gform=gform, orden__gt=gfsi.orden)
                    for g in gfsis:
                        g.gformsection = gfs
                        g.save()
                    html = render_to_string('formularios_accordion_content_gfs.html', {'gfs': gfs})
                    return JsonResponse({'ok': True, 'html': html, 'gfs_id_orden': gfs_id_orden(gform)})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'del_gfsi':
            try:
                gfsi = GformSectionInput.objects.get(id=request.POST['gfsi'])
                if gfsi.gformsection.gform.propietario == g_e or gfsi.creador == g_e:
                    gform = gfsi.gformsection.gform
                    if gfsi.orden > 1:
                        gfsis = GformSectionInput.objects.filter(gformsection__gform=gform, orden__gt=gfsi.orden)
                        for g in gfsis:
                            g.orden -= 1
                            g.save()
                        gfsi.delete()
                        return JsonResponse({'ok': True, 'gfsi_id_orden': gfsi_id_orden(gform)})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'No es posible borrar la primera pregunta'})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

    elif request.method == 'POST':
        if request.POST['action'] == 'excel_gform':
            gform = Gform.objects.get(id=request.POST['gform'], propietario__ronda__entidad=g_e.ronda.entidad)
            gfsis = GformSectionInput.objects.filter(gformsection__gform=gform)
            gfrs = gform.gformresponde_set.filter(respondido=True)
            ruta = MEDIA_FORMULARIOS + str(g_e.ronda.entidad.code) + '/' + str(gform.id) + '/'
            if not os.path.exists(ruta):
                os.makedirs(ruta)
            fichero_xls = '%s.xls' % slugify(gform.nombre)
            wb = xlwt.Workbook()
            wf = wb.add_sheet('Cuestionario')
            wa = wb.add_sheet('Avisos')
            fila_excel_cuestionario = 0
            fila_excel_avisos = 0
            estilo = xlwt.XFStyle()
            font = xlwt.Font()
            font.bold = True
            estilo.font = font
            wf.write(fila_excel_cuestionario, 0, 'Hora de entrega', style=estilo)
            wf.col(0).width = 8000  # Ancho de la columna para el nombre
            wf.write(fila_excel_cuestionario, 1, 'Nombre usuario', style=estilo)
            wf.col(1).width = 9000  # Ancho de la columna para el nombre
            wf.write(fila_excel_cuestionario, 2, 'Nombre entidad', style=estilo)
            wf.col(2).width = 9000  # Ancho de la columna para el nombre
            col = 3
            h = html2text.HTML2Text()
            for gfsi in gfsis:
                # pregunta = h.handle(gfsi.pregunta)
                pregunta = BeautifulSoup(gfsi.pregunta, features='lxml').get_text()
                wf.write(fila_excel_cuestionario, col, pregunta, style=estilo)
                wf.col(col).width = min(len(pregunta) * 278, 14000)  # Dejamos 278 de ancho por cada caracter
                col += 1

            for gfr in gfrs:
                fila_excel_cuestionario += 1
                wf.write(fila_excel_cuestionario, 0, str(gfr.modificado))
                wf.write(fila_excel_cuestionario, 1, gfr.g_e.gauser.get_full_name())
                wf.write(fila_excel_cuestionario, 2, gfr.g_e.ronda.entidad.name)
                col = 3
                for gfri in gfr.gformrespondeinput_set.all():
                    if gfri.gfsi.tipo == 'EL' or gfri.gfsi.tipo == 'EN':
                        respuesta = gfri.respuesta
                    elif gfri.gfsi.tipo == 'FI':
                        respuesta = '; '.join([gfri.rfirma_nombre, gfri.rfirma_cargo])
                    else:
                        respuesta = BeautifulSoup(gfri.respuesta, features='lxml').get_text().strip().replace('\n', '')
                    wf.write(fila_excel_cuestionario, col, respuesta)
                    col += 1

            # wf.write(fila_excel_cuestionario, 3, Formula("SUM(D2:D%s)" % (fila_excel_cuestionario)), style=estilo)

            wb.save(ruta + fichero_xls)

            xlsfile = open(ruta + '/' + fichero_xls, 'rb')
            response = HttpResponse(xlsfile, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=%s' % (fichero_xls)
            return response
        elif request.POST['action'] == 'pdf_gform':
            dce = get_dce(g_e.ronda.entidad, 'Configuración para cuestionarios')
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                c = render_to_string('gform2pdf.html', {'gfrs': gform.gformresponde_set.filter(respondido=True)})
                fich = pdfkit.from_string(c, False, dce.get_opciones)
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(gform.nombre)
                return response
            except Exception as msg:
                aviso = 'Se ha producido un error en el procesamiento de la platilla que debes corregir: %s' % str(msg)
                crear_aviso(request, False, aviso)
        elif request.POST['action'] == 'upload_archivo_xhr':
            try:
                errores = {}
                gform = Gform.objects.get(id=request.POST['gform'])
                n_files = int(request.POST['n_files'])
                for i in range(n_files):
                    fichero = request.FILES['archivo_xhr' + str(i)]
                    wb = xlrd.open_workbook(file_contents=fichero.read())
                    sheet = wb.sheet_by_index(0)
                    for row_index in range(1, sheet.nrows):
                        try:
                            entidad_destinatario = Entidad.objects.get(code=sheet.cell_value(row_index, 0))
                            destinatario = Gauser_extra.objects.get(gauser__dni=sheet.cell_value(row_index, 1),
                                                                    ronda=entidad_destinatario.ronda)
                            entidad_corrector = Entidad.objects.get(code=sheet.cell_value(row_index, 2))
                            corrector = Gauser_extra.objects.get(gauser__dni=sheet.cell_value(row_index, 3),
                                                                 ronda=entidad_corrector.ronda)
                            GformDestinatario.objects.get_or_create(gform=gform, destinatario=destinatario,
                                                                    corrector=corrector)
                            GformResponde.objects.get_or_create(gform=gform, g_e=destinatario)
                        except Exception as msg:
                            errores[row_index] = {'msg': str(msg), 'des': sheet.cell_value(row_index, 1),
                                                  'cor': sheet.cell_value(row_index, 3)}
                html = render_to_string("formularios_accordion_content_destinatarios.html", {'gform': gform})
                return JsonResponse({'ok': True, 'errores': errores, 'html': html, 'gform': gform.id})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})

    gforms = Gform.objects.filter(
        Q(propietario__gauser=g_e.gauser) | Q(colaboradores__gauser__in=[g_e.gauser])).distinct()
    paginator = Paginator(gforms, 15)
    formularios = paginator.page(1)
    return render(request, "formularios.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'permiso': 'crea_formularios', 'title': 'Crear un nuevo formulario'},
                           ),
                      'formname': 'formularios',
                      'formularios': formularios,
                      'pag': 1,
                      # 'id_gform': id_gform,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def ver_gform(request, id, identificador):
    g_e = request.session["gauser_extra"]
    try:
        if request.is_ajax():
            return JsonResponse({'ok': True, 'msg': 'No se realiza ninguna operación.'})
        elif request.method == 'POST':
            if request.POST['action'] == 'genera_pdf':
                dce = get_dce(g_e.ronda.entidad, 'Configuración para cuestionarios')
                gform = Gform.objects.get(id=request.POST['gform'])
                c = render_to_string('gform2pdf.html', {'template': gform.template_procesado})
                fich = pdfkit.from_string(c, False, dce.get_opciones)
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(gform.nombre)
                return response
        elif request.method == 'GET':
            gform = Gform.objects.get(id=id, identificador=identificador)
            return render(request, "ver_gform.html", {'gform': gform})
    except:
        return HttpResponse('Error')


@login_required()
def ver_resultados(request, id, identificador):
    g_e = request.session["gauser_extra"]

    if request.is_ajax():
        return JsonResponse({'ok': True, 'msg': 'No se realiza ninguna operación.'})
    elif request.method == 'POST':
        if request.POST['action'] == 'genera_pdf':
            dce = get_dce(g_e.ronda.entidad, 'Configuración para cuestionarios')
            gform = Gform.objects.get(id=request.POST['gform'])
            c = render_to_string('gform2pdf.html', {'template': gform.template_procesado})
            fich = pdfkit.from_string(c, False, dce.get_opciones)
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(gform.nombre)
            return response
    elif request.method == 'GET':
        gform = Gform.objects.get(id=id, identificador=identificador)
        gform_respondidos = gform.gformresponde_set.filter(respondido=True)
        return render(request, "ver_resultados.html", {'gform': gform, 'gform_respondidos': gform_respondidos})



    try:
        if request.is_ajax():
            return JsonResponse({'ok': True, 'msg': 'No se realiza ninguna operación.'})
        elif request.method == 'POST':
            if request.POST['action'] == 'genera_pdf':
                dce = get_dce(g_e.ronda.entidad, 'Configuración para cuestionarios')
                gform = Gform.objects.get(id=request.POST['gform'])
                c = render_to_string('gform2pdf.html', {'template': gform.template_procesado})
                fich = pdfkit.from_string(c, False, dce.get_opciones)
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(gform.nombre)
                return response
        elif request.method == 'GET':
            gform = Gform.objects.get(id=id, identificador=identificador)
            return render(request, "ver_resultados.html", {'gform': gform})
    except:
        return HttpResponse('Error')


def mis_formularios(request):
    g_e = request.session["gauser_extra"]
    organization = g_e.ronda.entidad.organization
    gfrs = GformResponde.objects.filter(g_e__gauser=g_e.gauser, g_e__ronda__entidad__organization=organization)

    # gforms_dr = paginator_dr.page(1)
    # gforms_hr = paginator_hr.page(1)
    # gforms_dc = paginator_dc.page(1)
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'change_tab':
            try:
                # gform = Gform.objects.get(id=request.POST['id'])
                # html = render_to_string('mis_formularios_accordion_hr_content.html', {'gform': gform, 'gfrs': gfrs})
                tab = request.POST['tab']
                if tab == 'dr':  # debo_rellenar
                    gfs = Gform.objects.filter(id__in=gfrs.filter(respondido=False).values_list('gform__id'),
                                               fecha_max_rellenado__gte=datetime.now(), activo=True).distinct()
                elif tab == 'hr':  # he_rellenado
                    gfs = Gform.objects.filter(id__in=gfrs.filter(respondido=True).values_list('gform__id')).distinct()
                else:  # debo_corregir
                    gfcorr_id = GformDestinatario.objects.filter(corrector__ronda__entidad__organization=organization,
                                                                 corrector__gauser=g_e.gauser).values_list('gform__id')
                    gfs = Gform.objects.filter(id__in=gfcorr_id).distinct()
                gforms = Paginator(gfs, 15).page(1)
                html = render_to_string('mis_formularios_accordion.html', {'gforms': gforms, 'pag': 1})
                return JsonResponse({'ok': True, 'html': html, 'tab': tab})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})


        elif request.POST['action'] == 'open_accordion':
            try:
                gform = Gform.objects.get(id=request.POST['id'])
                gtab = request.POST['gtab']
                if gtab == 'debo_evaluar':
                    gfds = GformDestinatario.objects.filter(gform=gform, corrector__gauser=g_e.gauser)
                    for gfd in gfds:
                        if GformResponde.objects.filter(gform=gform, g_e=gfd.destinatario).count() == 0:
                            GformResponde.objects.create(gform=gform, g_e=gfd.destinatario)
                else:
                    gfds = GformDestinatario.objects.none()

                html = render_to_string('mis_formularios_accordion_content.html', {'gform': gform, 'gfrs': gfrs,
                                                                                   'gtab': gtab, 'gfds': gfds})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'del_gformresponde':
            try:
                gfr = GformResponde.objects.get(id=request.POST['gformresponde'], g_e=g_e)
                if gfr.gform.fecha_max_rellenado.date() > datetime.now().date():
                    gfr.delete()
                    return JsonResponse({'ok': True})
                else:
                    msg = 'Este cuestionario ya no está activo y no es posible borrar tus respuestas.'
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'get_another_gform':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                gfr = GformResponde.objects.create(gform=gform, g_e=g_e)
                url = '/rellena_gform/%s/%s/%s/' % (gform.id, gform.identificador, gfr.identificador)
                return JsonResponse({'ok': True, 'url': url})
                # return redirect('/rellena_gform/%s/%s/%s/' % (gform.id, gform.identificador, gfr.identificador))
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
    elif request.method == 'POST' and request.POST['action'] == 'gfd_pdf':
        dce = get_dce(g_e.ronda.entidad, 'Configuración para cuestionarios')
        try:
            tipo = request.POST['tipo']
            if tipo == 'general':
                gform = Gform.objects.get(id=request.POST['gform'])
                gfds = gform.gformdestinatario_set.filter(corrector__gauser=g_e.gauser)
            else:
                gfds = GformDestinatario.objects.filter(id=request.POST['gfd'])
            c = render_to_string('mis_formularios_accordion_content_gfd2pdf.html', {'gfds': gfds})
            fich = pdfkit.from_string(c, False, dce.get_opciones)
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=%s_eval.pdf' % slugify(gfds[0].gform.nombre)
            return response
        except Exception as msg:
            aviso = 'Se ha producido un error en el procesamiento de la platilla que debes corregir: %s' % str(msg)
            crear_aviso(request, False, aviso)
    elif request.method == 'POST' and request.POST['action'] == 'gfd_excel':
        tipo = request.POST['tipo']
        if tipo == 'general':
            gform = Gform.objects.get(id=request.POST['gform'])
            gfds = gform.gformdestinatario_set.filter(corrector__gauser=g_e.gauser)
        else:
            gfds = GformDestinatario.objects.filter(id=request.POST['gfd'])
        ruta = MEDIA_FORMULARIOS + str(g_e.ronda.entidad.code) + '/' + str(gform.id) + '/'
        if not os.path.exists(ruta):
            os.makedirs(ruta)
        fichero_xls = '%s.xls' % slugify(gform.nombre)
        wb = xlwt.Workbook()
        for gfd in gfds:
            gform = gfd.gform
            gfsis = GformSectionInput.objects.filter(gformsection__gform=gform)
            gfrs = gform.gformresponde_set.filter(g_e=gfd.destinatario, respondido=True)
            wf = wb.add_sheet('%s' % gfd.destinatario.gauser.get_full_name())
            estilo = xlwt.XFStyle()
            font = xlwt.Font()
            font.bold = True
            estilo.font = font
            wf.write(0, 0, 'Hora de entrega', style=estilo)
            wf.write(1, 0, 'Nombre usuario', style=estilo)
            wf.write(2, 0, 'Nombre entidad', style=estilo)
            fila = 3
            col_0_with = [5000]
            col_1_with = [10000]
            for gfsi in gfsis:
                pregunta = BeautifulSoup(gfsi.pregunta, features='lxml').get_text()
                wf.write(fila, 0, pregunta, style=estilo)
                col_0_with.append(len(pregunta) * 278)  # Dejamos 278 de ancho por cada caracter
                fila += 1
            for gfr in gfrs:
                wf.write(0, 1, str(gfr.modificado))
                wf.write(1, 1, gfr.g_e.gauser.get_full_name())
                wf.write(2, 1, gfr.g_e.ronda.entidad.name)
                fila = 3
                for gfri in gfr.gformrespondeinput_set.all():
                    if gfri.gfsi.tipo == 'EL':
                        respuesta = gfri.respuesta
                    elif gfri.gfsi.tipo == 'FI':
                        respuesta = '; '.join([gfri.rfirma_nombre, gfri.rfirma_cargo])
                    else:
                        respuesta = BeautifulSoup(gfri.respuesta, features='lxml').get_text().strip().replace('\n', '')
                    wf.write(fila, 1, respuesta)
                    fila += 1
                    col_1_with.append(len(str(respuesta)) * 278)
            wf.col(0).width = min(max(col_0_with), 14000)
            wf.col(1).width = min(max(col_1_with), 30000)

        # wf.write(fila_excel_cuestionario, 3, Formula("SUM(D2:D%s)" % (fila_excel_cuestionario)), style=estilo)

        wb.save(ruta + fichero_xls)

        xlsfile = open(ruta + '/' + fichero_xls, 'rb')
        response = HttpResponse(xlsfile, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % (fichero_xls)
        return response

    gfs = Gform.objects.filter(id__in=gfrs.filter(respondido=False).values_list('gform__id'),
                               fecha_max_rellenado__gte=datetime.now(), activo=True).distinct()
    return render(request, "mis_formularios.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'permiso': 'crea_formularios', 'title': 'Crear un nuevo formulario'},
                           ),
                      'formname': 'mis_formularios',
                      'gforms': Paginator(gfs, 15).page(1),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


def get_ges(gauser):
    q1 = Q(ronda__inicio__lt=datetime.now())
    q2 = Q(ronda__fin__gt=datetime.now())
    return Gauser_extra.objects.filter(Q(gauser=gauser), q1, q2)


def rellena_gform(request, id, identificador, gfr_identificador=''):
    try:
        gform = Gform.objects.get(id=id, identificador=identificador)
    except:
        sleep(3)
        return render(request, "gform_no_existe.html")
    try:
        g_e = request.session["gauser_extra"]
    except:
        full_path = request.get_full_path()
        if 'larioja.org' in full_path:
            return redirect('/logincas/?nexturl=/rellena_gform/' + '/'.join([str(id), identificador, gfr_identificador]))
        else:
            return redirect(
                '/?nexturl=/rellena_gform/' + '/'.join([str(id), identificador, gfr_identificador]))
    if not gform.accesible:
        sleep(3)
        return render(request, "gform_no_existe.html", {'error': 'gform no accesible'})
    else:
        if gform.gformdestinatario_set.all().count() > 0:
            if not gform.gformdestinatario_set.filter(destinatario__gauser=g_e.gauser).count() > 0:
                sleep(3)
                return render(request, "gform_no_existe.html", {'error': 'Usuario no destinatario del gform'})
    if gfr_identificador:
        try:
            gformresponde = GformResponde.objects.get(gform=gform, g_e=g_e, identificador=gfr_identificador)
        except:
            sleep(3)
            return render(request, "gform_no_existe.html", {'error': 'Identificador de usuario no válido'})
    elif gform.multiple:
        try:
            gformresponde = GformResponde.objects.filter(gform=gform, g_e=g_e, respondido=False,
                                                         identificador=request.session['gformresponde'])[0]
        except:
            gform_entidad = gform.propietario.ronda.entidad
            con1 = gform.destinatarios == 'ENT' and g_e.ronda.entidad == gform_entidad
            con2 = gform.destinatarios == 'ORG' and g_e.ronda.entidad.organization == gform_entidad.organization
            if con1 or con2:
                gformresponde = GformResponde.objects.create(gform=gform, g_e=g_e)
            else:
                return render(request, "gform_no_existe.html", {'error': 'No destinatario del gform'})
            request.session['gformresponde'] = gformresponde.identificador
    else:
        try:
            gformresponde, c = GformResponde.objects.get_or_create(gform=gform, g_e=g_e)
        except Exception as msg:
            sleep(3)
            return render(request, "gform_no_existe.html", {'error': True, 'msg': str(msg)})
    gfsis = GformSectionInput.objects.filter(gformsection__gform=gformresponde.gform)
    for gfsi in gfsis:  # Creamos todas las respuestas vacías
        g, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
        if gfsi.tipo == 'EN' and c:
            g.rentero = 0
            g.save()
    if request.method == 'POST' and request.is_ajax():
        if gformresponde.respondido:
            return JsonResponse({'ok': False, 'msg': 'Este formulario ya está respondido. No se admiten cambios.'})
        elif not gformresponde.gform.accesible:
            return JsonResponse({'ok': False, 'msg': 'Este formulario no es accesible.'})
        elif request.POST['action'] == 'update_gfr_rtexto':
            try:
                gfsi = gfsis.get(id=request.POST['gfsi'])
                gfri, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
                gfri.rtexto = request.POST['rtexto']
                gfri.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_gfr_rentero':
            try:
                gfsi = gfsis.get(id=request.POST['gfsi'])
                gfri, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
                gfri.rentero = int(request.POST['rentero'])
                gfri.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_gfr_op':
            try:
                gfsi = gfsis.get(id=request.POST['gfsi'])
                gfsio = gfsi.gformsectioninputops_set.get(id=request.POST['gfsio'])
                gfri, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
                gfri.ropciones.clear()
                gfri.ropciones.add(gfsio)
                gfri.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_gfr_el':
            try:
                gfsi = gfsis.get(id=request.POST['gfsi'])
                gfri, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
                gfri.rentero = int(request.POST['valor'])
                gfri.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_gfr_sc':
            try:
                gfsi = gfsis.get(id=request.POST['gfsi'])
                gfsio = gfsi.gformsectioninputops_set.get(id=request.POST['gfsio'])
                gfri, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
                if request.POST['checked'] == 'false':
                    gfri.ropciones.remove(gfsio)
                else:
                    gfri.ropciones.add(gfsio)
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_firma':
            try:
                gfsi = gfsis.get(id=request.POST['gfsi'])
                gfri, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
                gfri.rfirma = request.POST['firma']
                gfri.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_gfr_fi':
            try:
                gfsi = gfsis.get(id=request.POST['gfsi'])
                gfri, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
                setattr(gfri, request.POST['campo'], request.POST['firmante'])
                gfri.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_gfr_ca':
            try:
                gfsi = gfsis.get(id=request.POST['gfsi'])
                gfsios = []
                for fecha_string in request.POST.getlist('selecteddates[]'):
                    tstamp = int(datetime.strptime(fecha_string, '%d/%m/%Y').timestamp())
                    try:
                        gfsios.append(gfsi.gformsectioninputops_set.get(orden=tstamp, opcion=fecha_string))
                    except:
                        gfsios.append(GformSectionInputOps.objects.create(gformsectioninput=gfsi, orden=tstamp,
                                                                    opcion=fecha_string))
                gfri, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
                gfri.ropciones.clear()
                gfri.ropciones.add(*gfsios)
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'borra_gauss_file':
            try:
                gfsi = gfsis.get(id=request.POST['gfsi'])
                gfri = GformRespondeInput.objects.get(gformresponde=gformresponde, gfsi=gfsi)
                if gfri.rarchivo:
                    os.remove(gfri.rarchivo.path)
                    gfri.rarchivo = None
                    gfri.content_type = ''
                    gfri.save()
                return JsonResponse({'ok': True, 'gfsi': gfsi.id})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
        elif request.POST['action'] == 'terminar_gform':
            try:
                requeridas = gfsis.filter(requerida=True)
                no_respondidas = []
                for gfsi in requeridas:
                    gfri, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
                    cond1 = gfri.gfsi.tipo == 'RC' and len(gfri.rtexto) < 2
                    cond2 = gfri.gfsi.tipo == 'RL' and len(gfri.rtexto) < 5
                    cond3 = gfri.gfsi.tipo in ['EM', 'SC', 'SO'] and gfri.ropciones.all().count() == 0
                    cond4 = gfri.gfsi.tipo == 'EL' and not str(gfri.rentero).isdigit()
                    cond5 = gfri.gfsi.tipo == 'FI' and (len(gfri.rfirma_nombre) < 5 or len(gfri.rfirma) < 1000)
                    cond6 = gfri.gfsi.tipo == 'SA' and not gfri.rarchivo
                    cond7 = gfri.gfsi.tipo == 'EN' and not str(gfri.rentero).isdigit()
                    if cond1 or cond2 or cond3 or cond4 or cond5 or cond6 or cond7:
                        no_respondidas.append(str(gfri.gfsi.orden))
                if len(no_respondidas) == 0:
                    gformresponde.respondido = True
                    gformresponde.save()
                    return JsonResponse({'ok': True})
                else:
                    if len(no_respondidas) == 1:
                        return JsonResponse(
                            {'ok': False, 'msg': 'falta por responder la pregunta %s' % no_respondidas[0]})
                    else:
                        return JsonResponse(
                            {'ok': False, 'msg': 'faltan por responder las preguntas %s' % ', '.join(no_respondidas)})
            except:
                return JsonResponse({'ok': False, 'msg': 'Se ha producido un error'})
    elif request.method == 'POST' and not request.is_ajax():
        if request.POST['action'] == 'genera_pdf':
            dce = get_dce(g_e.ronda.entidad, 'Configuración para cuestionarios')
            gfr = GformResponde.objects.get(id=request.POST['gformresponde'], g_e__gauser=g_e.gauser)
            c = render_to_string('gform2pdf.html', {'gfrs': [gfr]})
            fich = pdfkit.from_string(c, False, dce.get_opciones)
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(gfr.gform.nombre)
            return response
        elif request.POST['action'] == 'upload_archivo_xhr':
            try:
                n_files = int(request.POST['n_files'])
                gfsi = gfsis.get(id=request.POST['gfsi'])
                gfri, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
                if gfri.rarchivo:
                    os.remove(gfri.rarchivo.path)
                for i in range(n_files):
                    fichero = request.FILES['archivo_xhr' + str(i)]
                    gfri.rarchivo = fichero
                    gfri.content_type = fichero.content_type
                    gfri.save()
                html = render_to_string('rellena_gform_gfsi_SA_tr_files.html',
                                        {'gfsi': gfsi, 'gformresponde': gformresponde})
                return JsonResponse({'ok': True, 'id': gfsi.id, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
        elif request.POST['action'] == 'descarga_gauss_file':
            gfsi = gfsis.get(id=request.POST['gfsi'])
            gfri = GformRespondeInput.objects.get(gformresponde=gformresponde, gfsi=gfsi)
            fich = gfri.rarchivo
            response = HttpResponse(fich, content_type='%s' % gfri.content_type)
            filename = GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rarchivo.name
            response['Content-Disposition'] = 'attachment; filename=%s' % filename.rpartition('/')[2]
            return response

    return render(request, "rellena_gform.html",
                  {
                      'formname': 'rellena_gform',
                      'gformresponde': gformresponde,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })

def mis_respuestas(request, id, identificador, gfr_identificador=''):
    try:
        gform = Gform.objects.get(id=id, identificador=identificador)
    except:
        sleep(3)
        return render(request, "gform_no_existe.html")
    try:
        g_e = request.session["gauser_extra"]
    except:
        return redirect('/logincas/?nexturl=/rellena_gform/' + '/'.join([str(id), identificador, gfr_identificador]))
    if gform.gformdestinatario_set.all().count() > 0:
        if not gform.gformdestinatario_set.filter(destinatario__gauser=g_e.gauser).count() > 0:
            sleep(3)
            return render(request, "gform_no_existe.html", {'error': 'Usuario no destinatario del gform'})
    if gfr_identificador:
        try:
            gformresponde = GformResponde.objects.get(gform=gform, g_e=g_e, identificador=gfr_identificador)
        except:
            sleep(3)
            return render(request, "gform_no_existe.html", {'error': 'Identificador de usuario no válido'})
    else:
        sleep(3)
        return render(request, "gform_no_existe.html", {'error': 'Identificador de usuario no válido'})

    gfsis = GformSectionInput.objects.filter(gformsection__gform=gformresponde.gform)
    for gfsi in gfsis:  # Creamos todas las respuestas vacías
        g, c = GformRespondeInput.objects.get_or_create(gformresponde=gformresponde, gfsi=gfsi)
        if gfsi.tipo == 'EN' and c:
            g.rentero = 0
            g.save()
    if request.method == 'POST':
        if request.POST['action'] == 'genera_pdf':
            dce = get_dce(g_e.ronda.entidad, 'Configuración para cuestionarios')
            gfr = GformResponde.objects.get(id=request.POST['gformresponde'], g_e__gauser=g_e.gauser)
            c = render_to_string('gform2pdf.html', {'gfrs': [gfr]})
            fich = pdfkit.from_string(c, False, dce.get_opciones)
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(gfr.gform.nombre)
            return response
        elif request.POST['action'] == 'descarga_gauss_file':
            gfsi = gfsis.get(id=request.POST['gfsi'])
            gfri = GformRespondeInput.objects.get(gformresponde=gformresponde, gfsi=gfsi)
            fich = gfri.rarchivo
            response = HttpResponse(fich, content_type='%s' % gfri.content_type)
            filename = GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rarchivo.name
            response['Content-Disposition'] = 'attachment; filename=%s' % filename.rpartition('/')[2]
            return response

    return render(request, "mis_respuestas.html",
                  {
                      'formname': 'mis_respuestas',
                      'gformresponde': gformresponde,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })

def formularios_disponibles(request):
    g_e = request.session["gauser_extra"]
    DESTINATARIOS = (('ENT', 'Personas de mi entidad'), ('ORG', 'Personas de mi organización'))
    q1 = Q(destinatarios='ENT', propietario__ronda__entidad=g_e.ronda.entidad)
    q2 = Q(destinatarios='ORG', propietario__ronda__entidad__organization=g_e.ronda.entidad.organization)
    gforms = Gform.objects.filter(q1 | q2)
    gforms_accesibles = [gform for gform in gforms if gform.accesible]
    paginator = Paginator(gforms_accesibles, 15)
    formularios = paginator.page(1)
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'open_accordion':
            try:
                gform = Gform.objects.get(id=request.POST['id'])
                html = render_to_string('formularios_disponibles_accordion_content.html',
                                        {'gform': gform, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

    return render(request, "formularios_disponibles.html",
                  {
                      'formname': 'gforms_accesibles',
                      'formularios': formularios,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


#########################################################################
################## Evaluación docentes en prácticas #####################
#########################################################################

def carga_cuestionarios_funcionario_practicas(request):
    g_e = request.session["gauser_extra"]
    from formularios.evalfunpract_preguntas import CUE
    nombre = 'Evaluación funcionarios en prácticas (versión: %s)' % datetime.today().strftime('%Y%m%d-%H%M')
    efp, c = EvalFunPract.objects.get_or_create(nombre=nombre, entidad=g_e.ronda.entidad)
    if c:
        for dim in CUE:
            efpd = EvalFunPractDim.objects.create(evalfunpract=efp, dimension=dim['dim'])
            for subdim in dim['subdims']:
                efpds = EvalFunPractDimSub.objects.create(evalfunpractdim=efpd, subdimension=subdim['subdim'],
                                                          valor=subdim['valor'])
                for preg in subdim['pregs']:
                    if preg['subsub']:
                        p = '<b>%s</b><br>%s' % (preg['subsub'], preg['preg'])
                    else:
                        p = '%s' % preg['preg']
                    EvalFunPractDimSubCue.objects.create(evalfunpractdimsub=efpds, pregunta=p,
                                                         responde_doc=preg['docente'],
                                                         responde_doc_jefe=preg['docente-jefe'],
                                                         responde_doc_tutor=preg['docente-tutor'],
                                                         responde_doc_orientador=preg['orientador'],
                                                         responde_ins=preg['inspector'],
                                                         responde_tut=preg['tutor'],
                                                         responde_dir=preg['director'])


def activa_permisos(efpa):
    # Activamos permisos a las personas implicadas en la evaluación
    code_permisos = ['acceso_funcionarios_practicas', 'acceso_mis_evalpract']
    permisos = Permiso.objects.filter(code_nombre__in=code_permisos)
    efpa.docente.permisos.add(*permisos)
    efpa.director.permisos.add(*permisos)
    efpa.tutor.permisos.add(*permisos)
    efpa.inspector.permisos.add(*permisos)


def activa_cuestiones(efpa):
    cs_totales = efpa.procesoevalfunpract.evalfunpract.efpdscs  # Cuestiones totales disponibles
    for c in cs_totales:
        EvalFunPractRes.objects.get_or_create(evalfunpractact=efpa, evalfunpractdimsubcue=c)


# @permiso_required('acceso_procesos_evalpract')
def procesos_evaluacion_funcpract(request):  # procesos_evaluacion_funcionarios_en_prácticas
    g_e = request.session["gauser_extra"]
    pefps = ProcesoEvalFunPract.objects.filter(g_e__ronda__entidad=g_e.ronda.entidad, g_e__gauser=g_e.gauser)

    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_pefp':
            if g_e.has_permiso('acceso_procesos_evalpract'):
                try:
                    evalfunpract = EvalFunPract.objects.filter(entidad=g_e.ronda.entidad)[0]
                except:
                    carga_cuestionarios_funcionario_practicas(request)
                    evalfunpract = EvalFunPract.objects.filter(entidad=g_e.ronda.entidad)[0]
                pefp = ProcesoEvalFunPract.objects.create(g_e=g_e, nombre='Nuevo proceso', evalfunpract=evalfunpract)
                html = render_to_string('procesos_evaluacion_funcpract_accordion.html',
                                        {'buscadas': False, 'pefps': [pefp], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            else:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            try:
                pefp = ProcesoEvalFunPract.objects.get(id=request.POST['id'])
                # Líneas borrables en próximas cargas:
                code_permisos = ['acceso_funcionarios_practicas', 'acceso_mis_evalpract']
                permisos = Permiso.objects.filter(code_nombre__in=code_permisos)
                for efpa in pefp.evalfunpractact_set.all():
                    efpa.inspector.permisos.add(*permisos)
                    efpa.tutor.permisos.add(*permisos)
                    efpa.director.permisos.add(*permisos)
                    efpa.docente.permisos.add(*permisos)
                    menu_default = Menu_default.objects.get(code_menu='acceso_mis_evalpract')
                    crea_menu_from_default(menu_default.parent, efpa.director.ronda.entidad)
                    crea_menu_from_default(menu_default, efpa.director.ronda.entidad)
                # Fin de líneas borrables
                html = render_to_string('procesos_evaluacion_funcpract_accordion_content.html',
                                        {'pefp': pefp, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'del_pefp':
            try:
                pefp = ProcesoEvalFunPract.objects.get(id=request.POST['pefp'])
                if g_e.has_permiso('borra_pefps') or pefp.g_e.gauser == g_e.gauser:
                    pefp.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para borrar el proceso de evaluación'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_nombre':
            try:
                pefp = ProcesoEvalFunPract.objects.get(id=request.POST['pefp'])
                if pefp.g_e.gauser == g_e.gauser:
                    pefp.nombre = request.POST['texto']
                    pefp.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'El nombre solo puede ser cambiado por el propietario'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_fecha_limite':
            try:
                pefp = ProcesoEvalFunPract.objects.get(id=request.POST['pefp'])
                if pefp.g_e.gauser == g_e.gauser:
                    fecha = datetime.strptime(request.POST['fecha'], '%Y-%m-%d')
                    setattr(pefp, request.POST['campo'], fecha)
                    pefp.save()
                    for efpa in pefp.evalfunpractact_set.all():
                        setattr(efpa, request.POST['campo'], fecha)
                        efpa.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para hacer el cambio'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_efp':
            try:
                pefp = ProcesoEvalFunPract.objects.get(id=request.POST['pefp'])
                evalfunpract = EvalFunPract.objects.get(id=request.POST['efp'])
                if pefp.g_e.gauser == g_e.gauser and pefp.fecha_min > now().date():
                    pefp.evalfunpract = evalfunpract
                    pefp.save()
                    EvalFunPractRes.objects.filter(evalfunpractact__procesoevalfunpract=pefp).delete()
                    for efpa in pefp.evalfunpractact_set.all():
                        efpa.actualiza_efprs = True
                        efpa.save()
                        # activa_cuestiones(efpa) # Esta función requiere demasiado tiempo, así que
                        # se debe definir una tarea en segundo plano:
                    carga_masiva_from_file.delay()
                    return JsonResponse({'ok': True})
                else:
                    msg = 'Las cuestiones solo pueden ser cambiadas por el propietario y antes de la fecha de comienzo'
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'del_pefp_destinatario':
            try:
                efpa = EvalFunPractAct.objects.get(id=request.POST['efpa'])
                if efpa.procesoevalfunpract.g_e == g_e:
                    efpa_id = efpa.id
                    efpa.delete()
                    return JsonResponse({'ok': True, 'efpa': efpa_id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para borrar destinatarios'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_nombre_destinatario_reveal':
            try:
                user = request.POST['user']
                ges = Gauser_extra.objects.filter(gauser__dni=request.POST['dni'])
                for ge in ges:
                    if ge.ronda == ge.ronda.entidad.ronda:
                        return JsonResponse({'ok': True, 'nombre': ge.gauser.get_full_name(), 'user': user})
                return JsonResponse({'ok': False, 'nombre': 'No detectado usuario con ese DNI', 'user': user})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_destinatarios_carga_manual':
            try:
                director = Gauser_extra.objects.get(id=request.POST['director'])
                inspector = Gauser_extra.objects.get(id=request.POST['inspector'])
                tutor = Gauser_extra.objects.get(id=request.POST['tutor'])
                docente = Gauser_extra.objects.get(id=request.POST['docente'])
                pefp = ProcesoEvalFunPract.objects.get(id=request.POST['pefp'])
                efpa, c = EvalFunPractAct.objects.get_or_create(procesoevalfunpract=pefp,
                                                                inspector=inspector, tutor=tutor,
                                                                director=director, docente=docente,
                                                                fecha_max=pefp.fecha_max,
                                                                fecha_min=pefp.fecha_min)
                if c:
                    activa_permisos(efpa)
                    activa_cuestiones(efpa)
                html = render_to_string("procesos_evaluacion_funcpract_accordion_content_destinatarios.html",
                                        {'pefp': pefp})
                return JsonResponse({'ok': True, 'html': html, 'pefp': pefp.id})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

    elif request.method == 'POST':
        if request.POST['action'] == 'upload_archivo_xhr':
            try:
                errores = {}
                pefp = ProcesoEvalFunPract.objects.get(id=request.POST['pefp'])
                # code_permisos = ['acceso_funcionarios_practicas', 'acceso_mis_evalpract']
                # permisos = Permiso.objects.filter(code_nombre__in=code_permisos)
                n_files = int(request.POST['n_files'])
                for i in range(n_files):
                    fichero = request.FILES['archivo_xhr' + str(i)]
                    wb = xlrd.open_workbook(file_contents=fichero.read())
                    sheet = wb.sheet_by_index(0)
                    for row_index in range(1, sheet.nrows):
                        doc, dir, tut, insp = False, False, False, False
                        try:
                            code_centro = int(sheet.cell_value(row_index, 1))
                            entidad_funcionario = Entidad.objects.get(code=code_centro)
                            docente = Gauser_extra.objects.get(gauser__dni=str(sheet.cell_value(row_index, 3)).strip(),
                                                               ronda=entidad_funcionario.ronda)
                            doc = True
                            director = Gauser_extra.objects.get(gauser__dni=str(sheet.cell_value(row_index, 5)).strip(),
                                                                ronda=entidad_funcionario.ronda)
                            dir = True
                            tutor = Gauser_extra.objects.get(gauser__dni=str(sheet.cell_value(row_index, 7)).strip(),
                                                             ronda=entidad_funcionario.ronda)
                            tut = True
                            entidad_inspeccion = Entidad.objects.get(name__icontains='inspecc')
                            # entidad_inspeccion = entidad_funcionario
                            inspector = Gauser_extra.objects.get(
                                gauser__dni=str(sheet.cell_value(row_index, 9)).strip(),
                                ronda=entidad_inspeccion.ronda)
                            insp = True
                            efpa, c = EvalFunPractAct.objects.get_or_create(procesoevalfunpract=pefp,
                                                                            inspector=inspector, tutor=tutor,
                                                                            director=director, docente=docente,
                                                                            fecha_max=pefp.fecha_max,
                                                                            fecha_min=pefp.fecha_min)
                            if c:
                                activa_permisos(efpa)
                                activa_cuestiones(efpa)
                                # docente.permisos.add(*permisos)
                                # director.permisos.add(*permisos)
                                # tutor.permisos.add(*permisos)
                                # inspector.permisos.add(*permisos)
                        except Exception as msg:
                            errores[row_index] = {'msg': str(msg), 'fila': row_index,
                                                  'centro': sheet.cell_value(row_index, 1),
                                                  'docente': str(sheet.cell_value(row_index, 3)).strip(),
                                                  'tutor': str(sheet.cell_value(row_index, 7)).strip(),
                                                  'inspector': str(sheet.cell_value(row_index, 9)).strip(),
                                                  'director': str(sheet.cell_value(row_index, 5)).strip(),
                                                  'doc': doc, 'dir': dir, 'tut': tut, 'insp': insp}
                html = render_to_string("procesos_evaluacion_funcpract_accordion_content_destinatarios.html",
                                        {'pefp': pefp})
                return JsonResponse({'ok': True, 'errores': errores, 'html': html, 'pefp': pefp.id})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})

    cargo_inspector = Cargo.objects.filter(entidad=g_e.ronda.entidad, clave_cargo='g_inspector_educacion')
    return render(request, "procesos_evaluacion_funcpract.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'permiso': 'acceso_procesos_evalpract', 'title': 'Crear un nuevo proceso de evaluación'},
                           ),
                      'formname': 'procesos_evaluacion_funcpract',
                      'pefps': pefps,
                      'inspectores': Gauser_extra.objects.filter(ronda=g_e.ronda, cargos__in=cargo_inspector),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


# @permiso_required('acceso_mis_evalpract')
def mis_evalpract(request):  # mis_evaluaciones_prácticas
    g_e = request.session["gauser_extra"]
    fecha_min = datetime.now().date() + timedelta(days=60)
    fecha_max = datetime.now().date() - timedelta(days=200)
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'open_accordion':
            try:
                pefp = ProcesoEvalFunPract.objects.get(id=request.POST['id'], fecha_min__lt=fecha_min,
                                                       fecha_max__gt=fecha_max)
                if g_e.has_permiso('ve_todas_efpas'):
                    efpas = pefp.evalfunpractact_set.all()
                else:
                    q = Q(inspector__gauser=g_e.gauser) | Q(tutor__gauser=g_e.gauser) | Q(
                        docente__gauser=g_e.gauser) | Q(director__gauser=g_e.gauser)
                    efpas = pefp.evalfunpractact_set.filter(q)

                # evfpas_ins = pefp.evalfunpractact_set.filter(inspector__gauser=g_e.gauser)
                # evfpas_tut = pefp.evalfunpractact_set.filter(tutor__gauser=g_e.gauser)
                # evfpas_doc = pefp.evalfunpractact_set.filter(docente__gauser=g_e.gauser)
                # evfpas_dir = pefp.evalfunpractact_set.filter(director__gauser=g_e.gauser)
                html = render_to_string('mis_evalpract_accordion_content.html',
                                        {'pefp': pefp, 'efpas': efpas, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'perfil_docente':
            try:
                efpa = EvalFunPractAct.objects.get(id=request.POST['efpa'])
                if efpa.director == g_e or efpa.inspector == g_e:
                    respuesta = {'true': True, 'false': False}
                    efpa.docente_jefe = respuesta[request.POST['docente_jefe']]
                    efpa.docente_tutor = respuesta[request.POST['docente_tutor']]
                    efpa.docente_orientador = respuesta[request.POST['docente_orientador']]
                    efpa.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_cal_total':
            try:
                efpa = EvalFunPractAct.objects.get(id=request.POST['efpa'])
                return JsonResponse({'valor': efpa.cal_total})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
    elif request.method == 'POST':
        if request.POST['action'] == 'pdf_efpa':
            dce = get_dce(g_e.ronda.entidad, 'Configuración para cuestionarios')
            try:
                efpa = EvalFunPractAct.objects.get(id=request.POST['efpa'])
                # Datos para la creación del informe de Inspección:
                title = 'Informe de evaluación de %s' % efpa.docente.gauser.get_full_name()
                ie, c = InformeInspeccion.objects.get_or_create(title=title)
                ie.inspector = g_e
                ie.asunto = 'Informe de evaluación de %s' % efpa.docente.gauser.get_full_name()
                ie.destinatario = '<p>COMISIÓN DE EVALUACIÓN DE LA FASE DE PRÁCTICAS</p>'
                ie.texto = render_to_string('mis_evalpract_accordion_content_informe_INSP.html', {'efpa': efpa})
                ie.save()
                # Datos para la creación del documento de valoración:
                c = render_to_string('mis_evalpract_accordion_content_informe.html', {'efpa': efpa})
                fich = pdfkit.from_string(c, False, dce.get_opciones)
                response = HttpResponse(fich, content_type='application/pdf')
                nombre = slugify(efpa.docente.gauser.get_full_name())
                response['Content-Disposition'] = 'attachment; filename=Evaluacion_%s.pdf' % nombre
                return response
            except Exception as msg:
                aviso = 'Se ha producido un error en el procesamiento de la evaluación: %s' % str(msg)
                crear_aviso(request, False, aviso)
        elif request.POST['action'] == 'excel_cuestionario':
            efpa = EvalFunPractAct.objects.get(id=request.POST['efpa'])
            efprs = efpa.efprs('docente')
            ronda_slug = slugify(g_e.ronda.nombre)
            ruta = '%s%s/funcionarios_practicas/%s/' % (MEDIA_FORMULARIOS, str(g_e.ronda.entidad.code), ronda_slug)
            if not os.path.exists(ruta):
                os.makedirs(ruta)
            docente_slug = slugify(efpa.docente.gauser.get_full_name())
            fichero_xls = '%s_%s.xls' % (slugify(efpa.procesoevalfunpract.nombre), docente_slug)
            wb = xlwt.Workbook()
            wf = wb.add_sheet('%s' % efpa.docente.gauser.get_full_name())
            estilo = xlwt.XFStyle()
            font = xlwt.Font()
            font.bold = True
            estilo.font = font
            wf.write(0, 0, 'Dimensión', style=estilo)
            wf.write(0, 1, 'Sub-Dimensión', style=estilo)
            wf.write(0, 2, 'Total', style=estilo)
            wf.write(0, 3, 'Pregunta', style=estilo)
            wf.write(0, 4, 'Punt. Docente', style=estilo)
            wf.write(0, 5, 'Punt. Tutor', style=estilo)
            wf.write(0, 6, 'Punt. Director', style=estilo)
            wf.write(0, 7, 'Punt. Inspector', style=estilo)
            wf.write(0, 8, 'Observaciones', style=estilo)
            wf.col(0).width = 5000
            wf.col(1).width = 10000
            wf.col(3).width = 15000
            wf.col(8).width = 15000
            fila = 1

            def calc_valor(valor):
                if valor > -1:
                    return valor
                else:
                    return ' '

            for efpr in efprs:
                cue = efpr.evalfunpractdimsubcue
                subdim = cue.evalfunpractdimsub
                dim = subdim.evalfunpractdim
                wf.write(fila, 0, BeautifulSoup(dim.dimension, features='lxml').get_text(), style=estilo)
                wf.write(fila, 1, BeautifulSoup(subdim.subdimension, features='lxml').get_text(), style=estilo)
                wf.write(fila, 2, dim.valor, style=estilo)
                wf.write(fila, 3, BeautifulSoup(cue.pregunta, features='lxml').get_text(), style=estilo)
                # wf.write(fila, 4, calc_valor(efpr.docente), style=estilo)
                # wf.write(fila, 5, calc_valor(efpr.tutor), style=estilo)
                # wf.write(fila, 6, calc_valor(efpr.director), style=estilo)
                # wf.write(fila, 7, calc_valor(efpr.inspector), style=estilo)
                wf.write(fila, 4, calc_valor([-1, efpr.docente][efpr.evalfunpractact.respondido_doc]), style=estilo)
                wf.write(fila, 5, calc_valor([-1, efpr.tutor][efpr.evalfunpractact.respondido_tut]), style=estilo)
                wf.write(fila, 6, calc_valor([-1, efpr.director][efpr.evalfunpractact.respondido_dir]), style=estilo)
                wf.write(fila, 7, calc_valor([-1, efpr.inspector][efpr.evalfunpractact.respondido_ins]), style=estilo)
                # observaciones = 'Docente: %s\nTutor: %s\nDirector: %s\nInspector: %s' % (efpr.obsdocente,
                #                                                                          efpr.obstutor,
                #                                                                          efpr.obsdirector,
                #                                                                          efpr.obsinspector)
                obsdocente = ['', efpr.obsdocente][efpr.evalfunpractact.respondido_doc]
                obstutor = ['', efpr.obstutor][efpr.evalfunpractact.respondido_tut]
                obsdirector = ['', efpr.obsdirector][efpr.evalfunpractact.respondido_dir]
                obsinspector = ['', efpr.obsinspector][efpr.evalfunpractact.respondido_ins]
                observaciones = 'Docente: %s\nTutor: %s\nDirector: %s\nInspector: %s' % (obsdocente, obstutor,
                                                                                         obsdirector, obsinspector)
                wf.write(fila, 8, observaciones)
                if len(observaciones) > 50:
                    wf.row(fila).height_mismatch = True
                    wf.row(fila).height = 256 * 4
                fila += 1

            # wf.write(fila_excel_cuestionario, 3, Formula("SUM(D2:D%s)" % (fila_excel_cuestionario)), style=estilo)

            wb.save(ruta + fichero_xls)

            xlsfile = open(ruta + '/' + fichero_xls, 'rb')
            response = HttpResponse(xlsfile, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=%s' % (fichero_xls)
            return response

    evfpas_activas = EvalFunPractAct.objects.filter(procesoevalfunpract__fecha_min__lt=fecha_min,
                                                    procesoevalfunpract__fecha_max__gt=fecha_max)
    if g_e.has_permiso('ve_todas_efpas'):
        filtro_usuarios = Q(inspector__ronda__entidad=g_e.ronda.entidad) | Q(
            tutor__ronda__entidad=g_e.ronda.entidad) | Q(docente__ronda__entidad=g_e.ronda.entidad) | Q(
            director__ronda__entidad=g_e.ronda.entidad)
    else:
        filtro_usuarios = Q(inspector__gauser=g_e.gauser) | Q(tutor__gauser=g_e.gauser) | Q(
            docente__gauser=g_e.gauser) | Q(director__gauser=g_e.gauser)
    evfpas = evfpas_activas.filter(filtro_usuarios)
    pefps = ProcesoEvalFunPract.objects.filter(
        id__in=evfpas.values_list('procesoevalfunpract__id', flat=True)).distinct()
    return render(request, "mis_evalpract.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'permiso': 'acceso_procesos_evalpract', 'title': 'Crear un nuevo proceso de evaluación'},
                           ),
                      'formname': 'procesos_evaluacion_funcpract',
                      'pefps': pefps,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


def recufunprac(request, id, actor):  # rellenar_cuestionario_funcionario_practicas
    g_e = request.session["gauser_extra"]
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'update_radio_efpr':
            try:
                efpr = EvalFunPractRes.objects.get(id=request.POST['efpr'])
                hoy = now().date()
                pefp = efpr.evalfunpractact.procesoevalfunpract
                con1 = pefp.fecha_min <= hoy
                con2 = pefp.fecha_max >= hoy
                con3 = (pefp.fecha_max >= (hoy - timedelta(days=200))) and (actor == 'inspector')
                if (con1 and con2) or (con1 and con3):
                    ge_actor = getattr(efpr.evalfunpractact, actor)
                    if ge_actor.gauser == g_e.gauser:
                        setattr(efpr, actor, int(request.POST['valor']))
                        efpr.save()
                        return JsonResponse({'ok': True})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'No tienes permisos para modificar el cuestionario.'})
                else:
                    return JsonResponse({'ok': False, 'msg': 'En esta fecha no es posible la modificación.'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'terminar_efpa':
            try:
                efpa = EvalFunPractAct.objects.get(id=request.POST['efpa'])
                hoy = now().date()
                pefp = efpa.procesoevalfunpract
                con1 = pefp.fecha_min <= hoy
                con2 = pefp.fecha_max >= hoy
                con3 = (pefp.fecha_max >= (hoy - timedelta(days=200))) and (actor == 'inspector')
                if (con1 and con2) or (con1 and con3):
                    if actor == 'docente':
                        efpa.respondido_doc = True
                    elif actor == 'director':
                        efpa.respondido_dir = True
                    elif actor == 'inspector':
                        efpa.respondido_ins = True
                    elif actor == 'tutor':
                        efpa.respondido_tut = True
                    efpa.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'En esta fecha no es posible la modificación.'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'update_observaciones':
            try:
                efpr = EvalFunPractRes.objects.get(id=request.POST['efpr'])
                hoy = now().date()
                pefp = efpr.evalfunpractact.procesoevalfunpract
                con1 = pefp.fecha_min <= hoy
                con2 = pefp.fecha_max >= hoy
                con3 = (pefp.fecha_max >= (hoy - timedelta(days=200))) and (actor == 'inspector')
                if (con1 and con2) or (con1 and con3):
                    ge_actor = getattr(efpr.evalfunpractact, actor)
                    if ge_actor.gauser == g_e.gauser:
                        setattr(efpr, 'obs%s' % actor, request.POST['texto'])
                        efpr.save()
                        return JsonResponse({'ok': True})
                    else:
                        return JsonResponse(
                            {'ok': False, 'msg': 'No tienes permisos para modificar el cuestionario.'})
                else:
                    return JsonResponse({'ok': False, 'msg': 'En esta fecha no es posible la modificación.'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

    filtro_fechas = Q(procesoevalfunpract__fecha_min__lt=datetime.now().date() + timedelta(days=60)) & Q(
        procesoevalfunpract__fecha_max__gt=datetime.now().date() - timedelta(days=200))
    efpa = EvalFunPractAct.objects.get(Q(id=id), filtro_fechas)
    efprs = EvalFunPractRes.objects.none()
    respondido = False
    if getattr(efpa, actor) == g_e:
        efprs = efpa.efprs(actor)
        actores = {'docente': 'respondido_doc', 'inspector': 'respondido_ins', 'director': 'respondido_dir',
                   'tutor': 'respondido_tut'}
        respondido = getattr(efpa, actores[actor])
    ge_actor = getattr(efpa, actor)
    if ge_actor.gauser == g_e.gauser:
        return render(request, "recufunprac.html",
                      {
                          'formname': 'recufunprac',
                          'efpa': efpa,
                          'efprs': efprs,
                          'actor': actor,
                          'respondido': respondido
                      })

    try:
        filtro_fechas = Q(procesoevalfunpract__fecha_min__lt=datetime.now().date() + timedelta(days=60)) & Q(
            procesoevalfunpract__fecha_max__gt=datetime.now().date() - timedelta(days=200))
        efpa = EvalFunPractAct.objects.get(Q(id=id), filtro_fechas)
        efprs = EvalFunPractRes.objects.none()
        respondido = False
        if getattr(efpa, actor) == g_e:
            efprs = efpa.efprs(actor)
            actores = {'docente': 'respondido_doc', 'inspector': 'respondido_ins', 'director': 'respondido_dir',
                       'tutor': 'respondido_tut'}
            respondido = getattr(efpa, actores[actor])
        ge_actor = getattr(efpa, actor)
        if ge_actor.gauser == g_e.gauser:
            return render(request, "recufunprac.html",
                          {
                              'formname': 'recufunprac',
                              'efpa': efpa,
                              'efprs': efprs,
                              'actor': actor,
                              'respondido': respondido
                          })
        else:
            sleep(3)
            return render(request, "recufunprac_no_existe.html", {'error': True, 'msg': 'Sin permisos'})
    except Exception as msg:
        sleep(3)
        return render(request, "recufunprac_no_existe.html", {'error': True, 'msg': str(msg)})


errores = {"2": {"msg": "Gauser_extra matching query does not exist.",
                 "fila": 2, "centro": 26003088.0, "docente": "16588713D"},
           "9": {"msg": "Gauser_extra matching query does not exist.",
                 "fila": 9, "centro": 26003088.0, "docente": "16573619A"},
           "10": {"msg": "Gauser_extra matching query does not exist.",
                  "fila": 10, "centro": 26008219.0, "docente": "16557167L"},
           "11": {"msg": "Gauser_extra matching query does not exist.",
                  "fila": 11, "centro": 26008219.0, "docente": "16810280V"},
           "12": {"msg": "Gauser_extra matching query does not exist.",
                  "fila": 12, "centro": 26008219.0, "docente": "16545913N"},
           "14": {"msg": "Gauser_extra matching query does not exist.", "fila": 14, "centro": 26008219.0,
                  "docente": "72891277E"},
           "15": {"msg": "Gauser_extra matching query does not exist.", "fila": 15, "centro": 26008219.0,
                  "docente": "30236936D"},
           "16": {"msg": "Gauser_extra matching query does not exist.", "fila": 16, "centro": 26008219.0,
                  "docente": "72798036T"},
           "17": {"msg": "Gauser_extra matching query does not exist.", "fila": 17, "centro": 26008219.0,
                  "docente": "72278096S"},
           "18": {"msg": "Gauser_extra matching query does not exist.", "fila": 18, "centro": 26008219.0,
                  "docente": "16596736M"},
           "33": {"msg": "Gauser_extra matching query does not exist.", "fila": 33, "centro": "26000579",
                  "docente": "16585145Y"},
           "39": {"msg": "Gauser_extra matching query does not exist.", "fila": 39, "centro": 26001134.0,
                  "docente": "16554732E"},
           "41": {"msg": "Gauser_extra matching query does not exist.", "fila": 41, "centro": 26001134.0,
                  "docente": "16557943J"},
           "51": {"msg": "Gauser_extra matching query does not exist.", "fila": 51, "centro": "26001559",
                  "docente": "73220500T"},
           "58": {"msg": "Gauser_extra matching query does not exist.", "fila": 58, "centro": "26001560",
                  "docente": "08113180E"},
           "64": {"msg": "Gauser_extra matching query does not exist.", "fila": 64, "centro": "26001560",
                  "docente": "32787439L"},
           "65": {"msg": "Gauser_extra matching query does not exist.", "fila": 65, "centro": "26001560",
                  "docente": "16059799A"},
           "68": {"msg": "Gauser_extra matching query does not exist.", "fila": 68, "centro": "26001596",
                  "docente": "02640625H"},
           "78": {"msg": "Gauser_extra matching query does not exist.", "fila": 78, "centro": "26001596",
                  "docente": "16611860H"},
           "80": {"msg": "Gauser_extra matching query does not exist.", "fila": 80, "centro": "26001638",
                  "docente": "16550467N"},
           "81": {"msg": "Gauser_extra matching query does not exist.", "fila": 81, "centro": "26001638",
                  "docente": "13152390R"},
           "93": {"msg": "Gauser_extra matching query does not exist.", "fila": 93, "centro": "26001638",
                  "docente": "16604192D\t"},
           "94": {"msg": "Gauser_extra matching query does not exist.", "fila": 94, "centro": "26001845",
                  "docente": "44429735Z"},
           "120": {"msg": "Gauser_extra matching query does not exist.", "fila": 120, "centro": "26003091",
                   "docente": "18088578K"},
           "121": {"msg": "Gauser_extra matching query does not exist.", "fila": 121, "centro": "26003091",
                   "docente": "16583196N"},
           "122": {"msg": "Gauser_extra matching query does not exist.", "fila": 122, "centro": "26003091",
                   "docente": "16611358E"},
           "123": {"msg": "Gauser_extra matching query does not exist.", "fila": 123, "centro": "26003091",
                   "docente": "44675337E"},
           "124": {"msg": "Gauser_extra matching query does not exist.", "fila": 124, "centro": "26003091",
                   "docente": "X5831086B"},
           "125": {"msg": "Gauser_extra matching query does not exist.", "fila": 125, "centro": "26003209",
                   "docente": "70904315F"},
           "136": {"msg": "Gauser_extra matching query does not exist.", "fila": 136, "centro": "26003441",
                   "docente": "16595254H"},
           "140": {"msg": "Gauser_extra matching query does not exist.", "fila": 140, "centro": "26003507",
                   "docente": "72786358Y"},
           "154": {"msg": "Gauser_extra matching query does not exist.", "fila": 154, "centro": "26008475",
                   "docente": "72778155Z"},
           "158": {"msg": "Gauser_extra matching query does not exist.", "fila": 158, "centro": "26008475",
                   "docente": "75788540K"},
           "159": {"msg": "Gauser_extra matching query does not exist.", "fila": 159, "centro": "26008773",
                   "docente": "16618555C"},
           "173": {"msg": "Gauser_extra matching query does not exist.", "fila": 173, "centro": "26700073",
                   "docente": "\t71949455G"},
           "176": {"msg": "Gauser_extra matching query does not exist.", "fila": 176, "centro": "26700073",
                   "docente": "\t16603762Q"}}

# def crea_gfris_no_creadas(request):
#     gform = Gform.objects.get(id=36)
#     gfrs = GformResponde.objects.filter(gform=gform)
#     gfsis = GformSectionInput.objects.filter(gformsection__gform=gform)
#     for gfr in gfrs:
#         for gfsi in gfsis:  # Creamos todas las respuestas vacías
#             GformRespondeInput.objects.get_or_create(gformresponde=gfr, gfsi=gfsi)
#     return HttpResponse('Hecho')
