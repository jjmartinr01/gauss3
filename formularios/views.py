# -*- coding: utf-8 -*-
from datetime import datetime
import pdfkit
from django.contrib.auth import login
import simplejson as json
import pexpect
import os
import logging
import xlwt
from xlwt import Formula
from time import sleep
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
from mensajes.models import Aviso
from mensajes.views import crear_aviso
from formularios.models import *
from gauss.rutas import *
from gauss.funciones import get_dce
from entidades.models import Gauser_extra


def gfsi_id_orden(gform):
    gfsis = GformSectionInput.objects.filter(gformsection__gform=gform)
    return [{'id': gfsi.id, 'orden': gfsi.orden} for gfsi in gfsis], gfsis.count()


def gfs_id_orden(gform):
    gfss = GformSection.objects.filter(gform=gform)
    return [{'id': gfs.id, 'orden': gfs.orden} for gfs in gfss], gfss.count()


# @login_required()
def formularios(request):
    g_e = request.session["gauser_extra"]
    gforms = Gform.objects.filter(propietario__ronda__entidad=g_e.ronda.entidad)
    paginator = Paginator(gforms, 15)
    formularios = paginator.page(1)
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_formulario':
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
                html = render_to_string('formularios_accordion_content.html',
                                        {'gform': gform, 'g_e': g_e, 'tipos': TIPOS, 'grupos': GRUPOS})
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
                    colaborador = Gauser_extra.objects.get(id=int(request.POST['ge'][1:]), ronda=g_e.ronda)
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
                    html = render_to_string('formularios_accordion_content_ginputs_gi.html', {'gfsi': gfsi})
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
        # add_gfsi_after_gfsi, add_gfsi_after_gfsi, copy_gfsi, add_gfs_after_gfsi, del_gfsi

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
                    if gfri.gfsi.tipo == 'EL':
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
        if request.POST['action'] == 'pdf_gform':
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

    return render(request, "formularios.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'permiso': 'crea_formularios', 'title': 'Crear un nuevo formulario'},
                           ),
                      'formname': 'formularios',
                      'formularios': formularios,
                      # 'id_gform': id_gform,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


# @login_required()
def resultados_gform(request):
    g_e = request.session["gauser_extra"]
    try:
        gform = Gform.objects.get(id=request.GET['gform'], propietario=g_e)
    except:
        crear_aviso(request, False, "No tienes permiso para ver los resultados formulario/cuestionario solicitado")
        return redirect('/calendario/')
    original_ginputs = gform.ginput_set.filter(ginput__isnull=True).order_by('row', 'col')
    ginputs = gform.ginput_set.filter(ginput__isnull=False).order_by('rellenador__gauser__last_name',
                                                                     'rellenador__gauser__first_name', 'rellenador__id',
                                                                     'ginput__row', 'ginput__col')
    if request.method == 'POST':
        if request.POST['action'] == 'descarga_gfile':
            ginput = Ginput.objects.get(id=request.POST['id_ginput'], gform__propietario__entidad=g_e.ronda.entidad)
            fichero = ginput.archivo.read()
            response = HttpResponse(fichero, content_type=ginput.content_type_archivo)
            response['Content-Disposition'] = 'attachment; filename=%s' % ginput.fich_name
            return response
    return render(request, "resultados_gform.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Volver',
                            'permiso': 'm67i10', 'title': 'Volver a la lista de formularios'},
                           {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                            'permiso': 'm67i10', 'title': 'Borrar las respuestas seleccionadas'},
                           ),
                      'formname': 'resultados_gform',
                      'original_ginputs': original_ginputs,
                      'ginputs': ginputs,
                      'gform': gform,
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
    gfs = Gform.objects.filter(id__in=gfrs.values_list('gform__id')).distinct()
    paginator = Paginator(gfs, 15)
    gforms = paginator.page(1)
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'open_accordion':
            try:
                gform = Gform.objects.get(id=request.POST['id'])
                html = render_to_string('mis_formularios_accordion_content.html', {'gform': gform, 'gfrs': gfrs})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'del_gformresponde':
            try:
                GformResponde.objects.get(id=request.POST['gformresponde'], g_e=g_e).delete()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'get_another_gform':
            try:
                gform = Gform.objects.get(id=request.POST['gform'])
                gfr = GformResponde.objects.create(gform=gform, g_e=g_e)
                url = '/rellena_gform/%s/%s/%s/' % (gform.id, gform.identificador, gfr.identificador)
                return JsonResponse({'ok': True , 'url': url})
                # return redirect('/rellena_gform/%s/%s/%s/' % (gform.id, gform.identificador, gfr.identificador))
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

    return render(request, "mis_formularios.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'permiso': 'crea_formularios', 'title': 'Crear un nuevo formulario'},
                           ),
                      'formname': 'mis_formularios',
                      'gforms': gforms,
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
        return redirect('/logincas/?nexturl=/rellena_gform/' + '/'.join([str(id), identificador, gfr_identificador]))
    if not gform.accesible:
        sleep(3)
        return render(request, "gform_no_existe.html", {'error': True})
    if gfr_identificador:
        try:
            gformresponde = GformResponde.objects.get(gform=gform, g_e=g_e, identificador=gfr_identificador)
        except:
            sleep(3)
            return render(request, "gform_no_existe.html")
    elif gform.multiple:
        try:
            gformresponde = GformResponde.objects.filter(gform=gform, g_e=g_e, respondido=False,
                                                         identificador=request.session['gformresponde'])[0]
        except:
            gformresponde = GformResponde.objects.create(gform=gform, g_e=g_e)
            request.session['gformresponde'] = gformresponde.identificador
    else:
        try:
            gformresponde, c = GformResponde.objects.get_or_create(gform=gform, g_e=g_e)
        except Exception as msg:
            sleep(3)
            return render(request, "gform_no_existe.html", {'error': True})
    gfsis = GformSectionInput.objects.filter(gformsection__gform=gformresponde.gform)
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
                    if cond1 or cond2 or cond3 or cond4 or cond5 or cond6:
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