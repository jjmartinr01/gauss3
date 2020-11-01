# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from datetime import datetime, timedelta

import pdfkit
from dateutil.rrule import rrule, MONTHLY
import csv
import base64
import os, string
import sys
from time import sleep
import requests
import xlrd
from icalendar import Calendar
from calendar import monthrange
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
from pyvirtualdisplay import Display
from time import time
from bs4 import BeautifulSoup

from django.db.models import Q, Sum
from django.core.files.base import ContentFile, File
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.utils import timezone
from django.core.paginator import Paginator
from django.forms.models import model_to_dict

from entidades.models import Gauser_extra, Entidad, DocConfEntidad
from gauss.funciones import html_to_pdf, pass_generator, usuarios_ronda, html_to_pdf_dce
from gauss.rutas import RUTA_MEDIA, MEDIA_VUT, RUTA_BASE
from autenticar.control_acceso import permiso_required
from mensajes.models import Aviso
from autenticar.models import Permiso, Gauser
from mensajes.views import encolar_mensaje, crear_aviso
from vut.models import Vivienda, Ayudante, Reserva, Viajero, RegistroPolicia, PAISES, Autorizado, CalendarioVivienda, \
    ContabilidadVUT, PartidaVUT, AsientoVUT, AutorizadoContabilidadVut, PORTALES, DomoticaVUT, FotoWebVivienda, \
    DayWebVivienda, PropuestaPropietario, ContratoVUT
from vut.tasks import comunica_viajero2PNGC
import locale

# Create your views here.
locale.setlocale(locale.LC_TIME, 'es_ES.utf8')
logger = logging.getLogger('django')


def viviendas_con_permiso(g_e, permiso):
    if type(permiso) is not Permiso:
        permiso = Permiso.objects.get(code_nombre=permiso)
    autorizado = Autorizado.objects.filter(autorizado=g_e, vivienda__borrada=False, permisos__in=[permiso])
    q1 = Q(id__in=autorizado.values_list('vivienda__id', flat=True))
    if g_e.has_permiso(permiso.code_nombre):
        q2 = Q(propietarios__in=[g_e.gauser])
        return Vivienda.objects.filter(q1 | q2)
    else:
        return Vivienda.objects.filter(q1)


def viviendas_autorizado(g_e):
    vvs_id = Autorizado.objects.filter(autorizado=g_e, vivienda__borrada=False).values_list('vivienda__id', flat=True)
    q1 = Q(propietarios__in=[g_e.gauser])
    q2 = Q(borrada=False)
    q3 = Q(id__in=vvs_id)
    return Vivienda.objects.filter((q1 & q2) | q3).distinct()


def has_permiso_on_vivienda(g_e, vivienda, permiso):
    if type(permiso) is str:
        permiso = Permiso.objects.get(code_nombre=permiso)
    if g_e.gauser in vivienda.propietarios.all():
        return g_e.has_permiso(permiso.code_nombre)
    else:
        try:
            Autorizado.objects.get(autorizado=g_e, vivienda=vivienda, permisos__in=[permiso])
            return True
        except:
            return False


# -------------------------------------------------------------------------------


# */2 * * * * /home/gauss/django/gauss3/bin/python /home/gauss/django/gauss3/manage.py runtask comunica_viajero2PNGC  --settings=gauss.settings # krono$
# */2 * * * * /home/gauss/django/gauss3/bin/python /home/gauss/django/gauss3/manage.py runtask mail_mensajes_cola  --settings=gauss.settings # kronos:9$


# -------------------------------------------------------------------------------


@permiso_required('acceso_viviendas')
def viviendas(request):
    g_e = request.session['gauser_extra']
    # Líneas que deben ser borradas:
    v_a_cambiar = Vivienda.objects.all()
    for v in v_a_cambiar:
        if not v.gpropietario:
            v.gpropietario = v.propietarios.all()[0]
            v.save()
    # ttg######################
    vvs = viviendas_autorizado(g_e)
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'libro_registros':
            permiso = Permiso.objects.get(code_nombre='genera_libro_registro_policia')
            vivienda = Vivienda.objects.get(id=request.POST['id_vivienda'])
            if has_permiso_on_vivienda(g_e, vivienda, permiso):
                fecha_anterior_limite = datetime.today().date() - timedelta(1100)
                viajeros = Viajero.objects.filter(reserva__vivienda=vivienda,
                                                  reserva__entrada__gte=fecha_anterior_limite)
                if viajeros.count() > 0:
                    p_d = request.POST['protocol_domain']
                    c = render_to_string('libro_registro_policia.html',
                                         {'vivienda': vivienda, 'viajeros': viajeros, 'p_d': p_d})
                    ruta = '%sentidad_%s/vivienda%s/' % (MEDIA_VUT, vivienda.entidad.code, vivienda.id)
                    fich = html_to_pdf(request, c, fichero='libro_registros', media=ruta,
                                       title='Libro de registro de viajeros', tipo='sin_cabecera')
                    logger.info('Creado pdf libro de registros')
                    response = HttpResponse(fich, content_type='application/pdf')
                    logger.info('Creado pdf libro de registros 2')
                    response['Content-Disposition'] = 'attachment; filename=Libro_registro_viajeros.pdf'
                    logger.info('Creado pdf libro de registros 3')
                    return response
                else:
                    crear_aviso(request, False,
                                '<p>No se puede generar un libro de registros. No hay ningún viajero registrado.</p>')

    return render(request, "viviendas.html",
                  {
                      'formname': 'viviendas',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nueva vivienda',
                            'permiso': 'crea_viviendas', 'title': 'Crear una nueva vivienda'},
                           ),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'viviendas': vvs,
                      'usuarios': usuarios_ronda(g_e.ronda),
                      'propuestas_copropiedad': PropuestaPropietario.objects.filter(propuesto=g_e.gauser,
                                                                                    aceptada=False,
                                                                                    deadline__gt=timezone.now())
                  })


@login_required()
def ajax_viviendas(request):
    g_e = request.session["gauser_extra"]
    if request.is_ajax():
        if request.method == 'POST':
            if request.POST['action'] == 'add_vivienda' and g_e.has_permiso('crea_viviendas'):
                try:
                    vivienda = Vivienda.objects.create(nombre='Nueva vivienda', entidad=g_e.ronda.entidad,
                                                       address='Aquí escribir la dirección de la vivienda',
                                                       habitaciones=1, camas=2, inquilinos=2, iban='',
                                                       nif='', municipio='', provincia='', gpropietario=g_e.gauser)
                    vivienda.propietarios.add(g_e.gauser)
                    html = render_to_string('vivienda_accordion.html', {'viviendas': [vivienda]})
                    return JsonResponse({'html': html, 'ok': True})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'open_accordion':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    if vivienda in viviendas_autorizado(g_e):
                        usuarios = usuarios_ronda(g_e.ronda)
                        html = render_to_string('vivienda_accordion_content.html',
                                                {'vivienda': vivienda, 'g_e': g_e, 'usuarios': usuarios})
                        return JsonResponse({'ok': True, 'html': html})
                    else:
                        return JsonResponse({'ok': False})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'delete_vivienda':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'], propietarios__in=[g_e.gauser])
                    permiso = Permiso.objects.get(code_nombre='borra_viviendas')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        vivienda.delete()
                        return JsonResponse({'ok': True, 'mensaje': "La vivienda se ha borrado sin incidencias."})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar la vivienda."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar la vivienda."})

            elif request.POST['action'] == 'update_campo':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    permiso = Permiso.objects.get(code_nombre='edita_viviendas')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        campo = request.POST['campo']
                        valor = request.POST['valor']
                        setattr(vivienda, campo, valor)
                        vivienda.save()
                        return JsonResponse({'ok': True, 'campo': campo, 'valor': valor})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la vivienda."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la vivienda."})
            elif request.POST['action'] == 'send_propuesta_copropiedad':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'], propietarios__in=[g_e.gauser])
                    propuestos = Gauser.objects.filter(id__in=request.POST.getlist('propuestos[]'))
                    for p in propuestos:
                        PropuestaPropietario.objects.get_or_create(propone=g_e.gauser, propuesto=p, vivienda=vivienda)
                    return JsonResponse({'ok': True, 'p': request.POST.getlist('propuestos[]')})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la vivienda."})
            elif request.POST['action'] == 'aceptar_copropiedad':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    propuesta = PropuestaPropietario.objects.get(id=request.POST['propuesta'], vivienda=vivienda)
                    if request.POST['acepta'] == '1':
                        vivienda.propietarios.add(propuesta.propuesto)
                        propuesta.aceptada = True
                        propuesta.save()
                        return JsonResponse({'ok': True, 'recarga': True, 'p': propuesta.aceptada})
                    else:
                        propuesta.deadline = timezone.now().date()
                        propuesta.save()
                        return JsonResponse({'ok': True, 'recarga': False})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de realizar la acción solicitada."})
            elif request.POST['action'] == 'define_pagador':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'], propietarios__in=[g_e.gauser])
                    gpropietario = Gauser.objects.get(id=request.POST['gpropietario'])
                    vivienda.gpropietario = gpropietario
                    vivienda.save()
                    return JsonResponse({'ok': True})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de realizar la acción solicitada."})
            elif request.POST['action'] == 'update_campo_foto':
                try:
                    foto = FotoWebVivienda.objects.get(id=request.POST['foto'])
                    vivienda = foto.vivienda
                    permiso = Permiso.objects.get(code_nombre='edita_viviendas')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        campo = request.POST['campo']
                        valor = request.POST['valor']
                        setattr(foto, campo, valor)
                        foto.save()
                        return JsonResponse({'ok': True, 'campo': campo, 'valor': valor})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la vivienda."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la vivienda."})
            elif request.POST['action'] == 'remove_foto':
                try:
                    foto = FotoWebVivienda.objects.get(id=request.POST['foto'])
                    os.remove(RUTA_BASE + foto.foto.url)
                    foto.delete()
                    return JsonResponse({'foto': request.POST['foto'], 'ok': True})
                except:
                    return JsonResponse({'foto': request.POST['foto'], 'ok': False})
            elif request.POST['action'] == 'publicar_vivienda_web':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    permiso = Permiso.objects.get(code_nombre='edita_viviendas')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        vivienda.publicarweb = not vivienda.publicarweb
                        vivienda.save()
                        valor = ['No', 'Sí'][vivienda.publicarweb]
                        return JsonResponse({'ok': True, 'vivienda': vivienda.id, 'valor': valor})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la vivienda."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la vivienda."})
            elif request.POST['action'] == 'bloquear_dia_vivienda_web':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    permiso = Permiso.objects.get(code_nombre='edita_viviendas')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        fecha = timezone.datetime.strptime(request.POST['fecha'], '%Y-%m-%d')
                        d, c = DayWebVivienda.objects.get_or_create(vivienda=vivienda, fecha=fecha)
                        d.bloqueado = False if d.bloqueado else True
                        d.save()
                        return JsonResponse({'ok': True, 'vivienda': vivienda.id, 'bloqueado': d.bloqueado,
                                             'fecha': request.POST['fecha'], 'id': d.id})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la vivienda."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la vivienda."})
            elif request.POST['action'] == 'add_calendario_vut':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    permiso = Permiso.objects.get(code_nombre='add_calendario_vut')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        calendario = CalendarioVivienda.objects.create(vivienda=vivienda, ical='')
                        html = render_to_string('vivienda_accordion_content_calendario.html',
                                                {'calendario': calendario, 'g_e': g_e})
                        return JsonResponse({'ok': True, 'html': html, 'vivienda': vivienda.id})
                    else:
                        return JsonResponse(
                            {'ok': False, 'mensaje': "No tienes permiso para añadir un calendario a la vivienda."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error añadiendo un calendario a la vivienda."})
            elif request.POST['action'] == 'delete_calendario_vut':
                try:
                    calendario = CalendarioVivienda.objects.get(id=request.POST['calendario'])
                    vivienda = calendario.vivienda
                    permiso = Permiso.objects.get(code_nombre='delete_calendario_vut')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        calendario.delete()
                        return JsonResponse({'ok': True, 'mensaje': "El calendario se ha borrado sin incidencias."})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "No tienes permisos para borrar el calendario."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar el calendario."})
            elif request.POST['action'] == 'update_campo_calendario_vut':
                try:
                    calendario = CalendarioVivienda.objects.get(id=request.POST['calendario'])
                    vivienda = calendario.vivienda
                    permiso = Permiso.objects.get(code_nombre='edita_calendario_vut')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        campo = request.POST['campo']
                        valor = request.POST['valor']
                        setattr(calendario, campo, valor)
                        calendario.save()
                        return JsonResponse({'ok': True, 'campo': campo, 'valor': valor})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "No tienes permisos para editar el calendario."})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'add_autorizado_vut':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    permiso = Permiso.objects.get(code_nombre='add_autorizado_vut')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        ge = Gauser_extra.objects.get(id=request.POST['autorizado'])
                        autorizado = Autorizado.objects.create(vivienda=vivienda, autorizado=ge)
                        html = render_to_string('vivienda_accordion_content_autorizado.html',
                                                {'autorizado': autorizado, 'g_e': g_e})
                        return JsonResponse({'ok': True, 'html': html, 'vivienda': vivienda.id})
                    else:
                        mensaje = "No tienes permiso para añadir personas autorizadas a la vivienda."
                        return JsonResponse({'ok': False, 'mensaje': mensaje})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error tratando de añadir un ayudante a la vivienda."})
            elif request.POST['action'] == 'delete_autorizado_vut':
                try:
                    autorizado = Autorizado.objects.get(id=request.POST['autorizado'])
                    vivienda = autorizado.vivienda
                    permiso = Permiso.objects.get(code_nombre='delete_autorizado_vut')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        autorizado.delete()
                        return JsonResponse({'ok': True, 'mensaje': "La persona autorizada ha sido borrada."})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "No tienes permisos para borrar autorizados."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar autorizado."})
            elif request.POST['action'] == 'edita_autorizado_vut':
                try:
                    autorizado = Autorizado.objects.get(id=request.POST['autorizado'])
                    autorizado.permisos.clear()
                    permisos = Permiso.objects.filter(code_nombre__in=request.POST.getlist('permisos[]'))
                    autorizado.permisos.add(*permisos)
                    return JsonResponse({'ok': True})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar autorizado."})
            elif request.POST['action'] == 'add_ayudante':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    permiso = Permiso.objects.get(code_nombre='crea_ayudantes')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        ayudante = Ayudante.objects.create(vivienda=vivienda, iban='')
                        html = render_to_string('vivienda_accordion_content_ayudante.html',
                                                {'ayudante': ayudante, 'g_e': g_e})
                        return JsonResponse({'ok': True, 'html': html, 'vivienda': vivienda.id})
                    else:
                        return JsonResponse(
                            {'ok': False, 'mensaje': "No tienes permiso para añadir un ayudante a la vivienda."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error tratando de añadir un ayudante a la vivienda."})
            elif request.POST['action'] == 'delete_ayudante':
                try:
                    ayudante = Ayudante.objects.get(id=request.POST['ayudante'])
                    vivienda = ayudante.vivienda
                    permiso = Permiso.objects.get(code_nombre='borra_ayudantes')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        ayudante.delete()
                        return JsonResponse({'ok': True, 'mensaje': "El ayudante se ha borrado sin incidencias."})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "No tienes permisos para borrar al ayudante."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar al ayudante."})
            elif request.POST['action'] == 'update_campo_ayudante':
                try:
                    ayudante = Ayudante.objects.get(id=request.POST['ayudante'])
                    vivienda = ayudante.vivienda
                    permiso = Permiso.objects.get(code_nombre='edita_ayudantes')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        campo = request.POST['campo']
                        valor = request.POST['valor']
                        setattr(ayudante, campo, valor)
                        ayudante.save()
                        return JsonResponse({'ok': True, 'campo': campo, 'valor': valor})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "No tienes permisos para editar al ayudante."})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'test_webpol':
                try:
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    permiso = Permiso.objects.get(code_nombre='comprueba_conexion_policia')
                    if has_permiso_on_vivienda(g_e, vivienda, permiso):
                        if vivienda.police == 'PN':
                            s = requests.Session()
                            s.verify = False
                            try:
                                p1 = s.get('https://webpol.policia.es/e-hotel/', timeout=5)
                            except:
                                return False
                            cookies_header = ''
                            for c in dict(s.cookies):
                                cookies_header += '%s=%s;' % (c, dict(s.cookies)[c])
                            soup1 = BeautifulSoup(p1.content.decode(p1.encoding), 'html.parser')
                            csrf_token = soup1.find('input', {'name': '_csrf'})['value']
                            payload = {'username': vivienda.police_code, '_csrf': csrf_token,
                                       'password': vivienda.police_pass}
                            execute_login_headers = {
                                'Accept': 'text/html,  application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8',
                                'Accept-Encoding': 'gzip, deflate, br',
                                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                'Connection': 'keep-alive',
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'Cookie': cookies_header,
                                'Host': 'webpol.policia.es', 'Referer': 'https://webpol.policia.es/e-hotel/',
                                'Upgrade-Insecure-Requests': '1', 'User-Agent': 'python-requests/2.21.0'}
                            try:
                                p2 = s.post('https://webpol.policia.es/e-hotel/execute_login', data=payload,
                                            headers=execute_login_headers, timeout=5)
                                if vivienda.police_code in p2.content.decode(p2.encoding):
                                    login_ok = True
                                else:
                                    login_ok = False
                            except:
                                login_ok = False
                            s.close()
                            return JsonResponse({'ok': True, 'login_ok': login_ok})
                        elif vivienda.police == 'GC':
                            s = requests.Session()
                            s.verify = False
                            try:
                                p1 = s.get('https://hospederias.guardiacivil.es/hospederias/configuracion.do',
                                           timeout=5)
                            except:
                                return False
                            cookies_header = ''
                            for c in dict(s.cookies):
                                cookies_header += '%s=%s;' % (c, dict(s.cookies)[c])
                            soup1 = BeautifulSoup(p1.content.decode(p1.encoding), 'html.parser')
                            adaptadores = soup1.find('input', {'name': 'adaptadores'})['value']
                            payload = {'usuario': vivienda.police_code, 'adaptadores': adaptadores,
                                       'pswd': vivienda.police_pass}
                            # Registro de Abel Yécora: 26261AAX00
                            # 251653613716
                            execute_login_headers = {
                                'Accept': 'text/html,  application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8',
                                'Accept-Encoding': 'gzip, deflate, br',
                                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                'Connection': 'keep-alive',
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'Content-Length': '64',
                                'Cookie': cookies_header,
                                'Host': 'hospederias.guardiacivil.es',
                                'Referer': 'https://hospederias.guardiacivil.es/hospederias/configuracion.do',
                                'Upgrade-Insecure-Requests': '1', 'User-Agent': 'python-requests/2.21.0'}
                            try:
                                p2 = s.post('https://hospederias.guardiacivil.es/hospederias/login.do', data=payload,
                                            headers=execute_login_headers, timeout=5)
                                if vivienda.police_code in p2.content.decode(p2.encoding):
                                    login_ok = True
                                else:
                                    login_ok = False
                            except:
                                login_ok = False
                            s.close()
                            return JsonResponse({'ok': True, 'login_ok': login_ok})
                        else:
                            mensaje = 'Debes indicar si la conexión es con Guardia Civil o con Policía Nacional.'
                            return JsonResponse({'ok': False, 'mensaje': mensaje})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para hacer la comprobación'})
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'La conexión sólo es probada por el propietario'})
    else:
        if request.POST['action'] == 'upload_foto_vut':
            vivienda = Vivienda.objects.get(id=request.POST['vivienda'], propietarios__in=[g_e.gauser])
            n_files = int(request.POST['n_files'])
            fotos = []
            for i in range(n_files):
                fichero = request.FILES['foto_xhr' + str(i)]
                code = pass_generator(20)
                fotowebvivienda = FotoWebVivienda.objects.create(vivienda=vivienda, foto=fichero,
                                                                 content_type=fichero.content_type)
                # http: // www.imagemagick.org / discourse - server / viewtopic.php?t = 28069
                # If
                # test = 1, then
                # landscape.If
                # test = 0, then
                # portrait or square
                # CODE: SELECT
                # ALL
                # test = `convert
                # image - format
                # "%[fx:(w/h>1)?1:0]"
                # info:`
                # if [ $test -eq 1]; then
                # convert
                # image - resize
                # 800
                # x
                # result
                # else
                # convert
                # image - resize
                # x800
                # result
                # fi
                html = render_to_string('vivienda_accordion_content_web_fotos.html', {'vivienda': vivienda})
                # fotos.append(
                #     {'file_name': fotowebvivienda.filename(), 'url': fotowebvivienda.foto.url})
            return JsonResponse({'html': html, 'vivienda': vivienda.id})


@permiso_required('acceso_reservas')
def reservas_vut(request):
    g_e = request.session['gauser_extra']
    request.session['next_days_reserva_vut'] = 7
    request.session['prev_days_reserva_vut'] = 7
    data_calendarios = False
    viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_reservas')
    # Las siguientes líneas son para actualizar las reservas a partir de los calendarios
    # la primera vez que entra en reservas_vut durante la sesión actual

    if 'updated_calendarios_vut' not in request.session:
        request.session['updated_calendarios_vut'] = datetime.now()
        data_calendarios = update_calendarios_vut(viviendas)
    try:
        fecha_inicio = datetime.strptime(request.GET['fi'], '%d%m%Y')
    except:
        fecha_inicio = datetime.today() - timedelta(request.session['prev_days_reserva_vut'])
    try:
        fecha_fin = datetime.strptime(request.GET['ff'], '%d%m%Y')
    except:
        fecha_fin = datetime.today() + timedelta(request.session['next_days_reserva_vut'])
    try:
        vivienda = viviendas.get(id=request.GET['v'])
        reservas = Reserva.objects.filter(vivienda=vivienda, borrada=False, entrada__gte=fecha_inicio,
                                          entrada__lte=fecha_fin, estado='ACE')
    except:
        reservas = Reserva.objects.filter(vivienda__in=viviendas, borrada=False, entrada__gte=fecha_inicio,
                                          entrada__lte=fecha_fin, estado='ACE')
    if request.method == 'POST' and not request.is_ajax():
        if request.POST['action'] == 'descargar_fichero_policia':
            r_p = RegistroPolicia.objects.get(vivienda__propietario=g_e, id=request.POST['fichero_policia'])
            response = HttpResponse(r_p.parte, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=%s' % r_p.filename
            return response
        elif request.POST['action'] == 'descarga_parte_pdf_PN':
            viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_viajeros')
            r_p = RegistroPolicia.objects.get(vivienda__in=viviendas, id=request.POST['fichero_policia'])
            response = HttpResponse(r_p.pdf_PN, content_type='application/pdf')
            nombre = os.path.basename(r_p.pdf_PN.name)
            response['Content-Disposition'] = 'attachment; filename=%s' % nombre
            return response

    return render(request, "reservas_vut.html",
                  {
                      'formname': 'reservas_vut',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'Libro de registro',
                            'permiso': 'crea_reservas', 'title': 'Crear una nueva reserva'},
                           ),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'reservas': reservas,
                      'viviendas': viviendas,
                      'fecha_inicio': fecha_inicio,
                      'fecha_fin': fecha_fin,
                      'portales': PORTALES,
                      'data_calendarios': data_calendarios
                  })


def get_viviendas(g_e):
    viviendas_autorizadas = Autorizado.objects.filter(autorizado=g_e, vivienda__propietario__entidad=g_e.ronda.entidad)
    viviendas_autorizadas_id = viviendas_autorizadas.values_list('vivienda__id', flat=True)
    viviendas = Vivienda.objects.filter(Q(id__in=viviendas_autorizadas_id) | Q(propietarios__in=[g_e.gauser]))
    return viviendas


def get_reservas(g_e, fecha_entrada_min=(datetime.today() - timedelta(10))):
    viviendas = get_viviendas(g_e)
    return Reserva.objects.filter(vivienda__in=viviendas, entrada__gte=fecha_entrada_min)


def get_viajeros(g_e, fecha_entrada_min=(datetime.today() - timedelta(10))):
    reservas = get_reservas(g_e, fecha_entrada_min=fecha_entrada_min)
    return Viajero.objects.filter(reserva__in=reservas)


def update_calendarios_vut(viviendas):
    n, e, u = 0, '', 0
    s = []
    mensaje = ''
    for v in viviendas:
        for calviv in v.calendariovivienda_set.all():
            try:
                if 'airbnb' in calviv.ical:
                    calviv.portal = 'AIR'
                elif 'booking' in calviv.ical:
                    calviv.portal = 'BOO'
                elif 'tripadvisor' in calviv.ical:
                    calviv.portal = 'TRI'
                elif 'homeaway' in calviv.ical:
                    calviv.portal = 'HOM'
                else:
                    calviv.portal = 'OTR'
                calviv.save()
                ical = requests.get(calviv.ical, allow_redirects=True)
                gcal = Calendar.from_ical(ical.content)
                for c in gcal.walk():  # for component in gcal.walk
                    if c.name == 'VEVENT':
                        try:
                            summary = c.get('SUMMARY')
                            if calviv.portal == 'AIR':
                                if 'Reserved' in summary:
                                    description = c.get('DESCRIPTION')
                                    code = description.split('code=')[1].split('\n')[0]
                                    nombre = 'Anónimo Airbnb'
                                    reserva, creada = Reserva.objects.get_or_create(vivienda=v, code=code)
                                    if creada:
                                        reserva.nombre = nombre
                                    reserva.entrada = c.get('dtstart').dt
                                    reserva.noches = int((c.get('dtend').dt - c.get('dtstart').dt).days)
                                    reserva.portal = calviv.portal
                                    reserva.save()
                                    if creada:
                                        n += 1
                                    else:
                                        u += 1
                            elif calviv.portal == 'BOO':
                                if 'vailable' not in summary:
                                    nombre = summary.replace('CLOSED -', '')
                                    entrada = c.get('dtstart').dt
                                    reserva, creada = Reserva.objects.get_or_create(vivienda=v, entrada=entrada,
                                                                                    estado='ACE', portal=calviv.portal)
                                    reserva.nombre = nombre
                                    reserva.noches = int((c.get('dtend').dt - c.get('dtstart').dt).days)
                                    if creada:
                                        reserva.code = pass_generator(size=10)
                                        n += 1
                                    else:
                                        u += 1
                                    reserva.save()
                                else:
                                    try:
                                        entrada = c.get('dtstart').dt
                                        reserva = Reserva.objects.get(vivienda=v, entrada=entrada, estado='ACE',
                                                                      portal=calviv.portal)
                                        reserva.estado = 'CAN'
                                        reserva.save()
                                    except:
                                        # Si llega a este punto es porque seguramente hay un VEVENT del tipo:
                                        # BEGIN: VEVENT
                                        # DTSTART;DTEND;
                                        # VALUE = DATE:20190824
                                        # UID: 6e5f3f2c0b862c4b8821b890d549d4d7 @ booking.com
                                        # SUMMARY: CLOSED - Not Available
                                        # END: VEVENT
                                        # Por tanto no hay que hacer nada:
                                        pass
                                        # mensaje += '<li>Error en la lectura de una reserva de Booking (%s).</li>' % (v.nombre)

                            elif calviv.portal == 'HOM':
                                if 'vailable' not in summary or 'loqueado' not in summary:
                                    nombre = summary.split('-')[1].strip()
                                    entrada = c.get('dtstart').dt
                                    reserva, creada = Reserva.objects.get_or_create(vivienda=v, entrada=entrada,
                                                                                    estado='ACE', portal=calviv.portal)
                                    reserva.nombre = nombre
                                    reserva.noches = int((c.get('dtend').dt - c.get('dtstart').dt).days)
                                    if creada:
                                        reserva.code = pass_generator(size=10)
                                        n += 1
                                    else:
                                        u += 1
                                    reserva.save()
                                else:
                                    try:
                                        entrada = c.get('dtstart').dt
                                        reserva = Reserva.objects.get(vivienda=v, entrada=entrada, estado='ACE',
                                                                      portal=calviv.portal)
                                        reserva.estado = 'CAN'
                                        reserva.save()
                                    except:
                                        # Mirar mensaje escrito en BOOKING
                                        pass
                                        # mensaje += '<li>Error en la lectura de una reserva de Homeaway (%s).</li>' % (v.nombre)
                            elif calviv.portal == 'TRI':
                                if 'vailable' not in summary or 'loqueado' not in summary:
                                    nombre, code = [b for b in summary.split(':')[1].replace(')', '').split('(')]
                                    entrada = c.get('dtstart').dt
                                    reserva, creada = Reserva.objects.get_or_create(vivienda=v, entrada=entrada,
                                                                                    estado='ACE', portal=calviv.portal)
                                    reserva.code = code
                                    reserva.nombre = nombre
                                    reserva.portal = calviv.portal
                                    reserva.noches = int((c.get('dtend').dt - c.get('dtstart').dt).days)
                                    if creada:
                                        n += 1
                                    else:
                                        u += 1
                                    reserva.save()
                                else:
                                    try:
                                        entrada = c.get('dtstart').dt
                                        reserva = Reserva.objects.get(vivienda=v, entrada=entrada, estado='ACE',
                                                                      portal=calviv.portal)
                                        reserva.estado = 'CAN'
                                        reserva.save()
                                    except:
                                        # Mirar mensaje escrito en BOOKING
                                        pass
                                        # mensaje += '<li>Error en la lectura de una reserva de TripAdvisor (%s).</li>' % (v.nombre)
                            else:
                                nombre = summary
                                entrada = c.get('dtstart').dt
                                reserva, creada = Reserva.objects.get_or_create(vivienda=v, entrada=entrada)
                                reserva.nombre = nombre
                                reserva.portal = calviv.portal
                                reserva.noches = int((c.get('dtend').dt - c.get('dtstart').dt).days)
                                if creada:
                                    reserva.code = pass_generator(size=10)
                                    n += 1
                                else:
                                    u += 1
                                reserva.save()
                            solapadas = reservas_solapadas(reserva)
                            for solapada in solapadas:
                                s.append(solapada)
                        except:
                            e += c.get('summary') + v.nombre
            except:
                mensaje += '<li>Error en la lectura de un calendario. Posiblemente esté vacío (%s).</li>' % (v.nombre)
    html = render_to_string('mensaje_update_calendarios_vut.html',
                            {'nuevas': n, 'actualizadas': u, 'errores': e, 'mensaje': mensaje, 'solapadas': s})
    return {'nuevas': n, 'actualizadas': u, 'errores': e, 'mensaje': mensaje, 'html': html}


def string2float(s):
    cantidad = ''
    for a in s:
        if a.isdigit():
            cantidad += a
        elif a == ',' or a == '.':
            cantidad += '.'
    return float(cantidad)


def reservas_solapadas(reserva):  # reserva es la que acabamos de leer del fichero
    entrada = reserva.entrada
    salida = reserva.salida
    vivienda = reserva.vivienda
    solapadas = Reserva.objects.filter(Q(vivienda=vivienda), Q(estado='ACE'), Q(borrada=False), (
            (Q(entrada__gte=entrada) & Q(entrada__lt=salida)) | (Q(entrada__lte=entrada) & Q(salida__gt=entrada))))

    # Casos en los que podría ser eliminada una reserva solapada:
    # 1ª Cuando el code de ambas es el mismo. Nos quedamos con la que acabamos de leer del fichero
    borrar = []
    for r in solapadas.exclude(id=reserva.id):
        # Para asegurarnos que no borramos una reserva real y la sustituimos por una reserva de update_calendario:
        es_borrable = ((reserva.total > 0) or (r.total == 0)) and r.viajero_set.all().count() == 0
        if r.code == reserva.code and es_borrable:
            r.borrada = True
            r.save()
    # 2º Cuando el nombre coincide en las reservas:
    for r in solapadas.exclude(id=reserva.id):
        if r.nombre in reserva.nombre and es_borrable:
            r.borrada = True
            r.save()
    # Volvemos a hacer la query para que no tenga las reservas borradas
    reservas = Reserva.objects.filter(Q(vivienda=vivienda), Q(estado='ACE'), Q(borrada=False), (
            (Q(entrada__gte=entrada) & Q(entrada__lt=salida)) | (Q(entrada__lte=entrada) & Q(salida__gt=entrada))))
    if reservas.count() > 1:
        return reservas
    else:
        return False


@login_required()
def ajax_reservas_vut(request):
    g_e = request.session["gauser_extra"]
    if request.is_ajax():
        if request.method == 'POST':
            if request.POST['action'] == 'add_nueva_reserva':
                try:
                    viviendas = viviendas_con_permiso(g_e, 'crea_reservas')
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    entrada = timezone.datetime.strptime(request.POST['entrada'], '%d/%m/%Y').date()
                    salida = timezone.datetime.strptime(request.POST['salida'], '%d/%m/%Y').date()
                    noches = (salida - entrada).days
                    if vivienda in viviendas and float(request.POST['total']) >= 0:
                        reserva = Reserva.objects.create(vivienda=vivienda, entrada=entrada, noches=noches,
                                                         total=float(request.POST['total']), code=pass_generator(),
                                                         nombre=request.POST['nombre'], portal='OTR')
                        html = render_to_string('tr_reserva.html', {'r': reserva})
                        return JsonResponse({'html': html, 'ok': True})
                    else:
                        return JsonResponse({'ok': False})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'change_num_viajeros':
                try:
                    viviendas = viviendas_con_permiso(g_e, 'edita_reservas')
                    reserva = Reserva.objects.get(id=request.POST['reserva'])
                    if reserva.vivienda in viviendas:
                        reserva.num_viajeros = request.POST['valor']
                        reserva.save()
                        return JsonResponse({'ok': True})
                    else:
                        return JsonResponse({'ok': False})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'match_vivienda':
                vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                if has_permiso_on_vivienda(g_e, vivienda, 'edita_viviendas'):
                    vivienda.observaciones = request.POST['texto']
                    vivienda.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'change_tab_reservas':
                fecha_inicio = datetime.today() - timedelta(request.session['prev_days_reserva_vut'])
                fecha_fin = datetime.today() + timedelta(request.session['next_days_reserva_vut'])
                viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_reservas')
                reservas = Reserva.objects.filter(vivienda__in=viviendas, borrada=False,
                                                  entrada__gte=fecha_inicio, estado='ACE',
                                                  entrada__lte=fecha_fin)
                html = render_to_string('reservas_vut_tab.html', {'reservas': reservas, 'fecha_inicio': fecha_inicio,
                                                                  'fecha_fin': fecha_fin, 'viviendas': viviendas,
                                                                  'portales': PORTALES})
                return JsonResponse({'ok': True, 'html': html})
            elif request.POST['action'] == 'change_select_reservas':
                viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_reservas')
                mes = int(request.POST['mes'])
                vivienda = request.POST['vivienda']
                portal = request.POST['portal']
                if mes == 0:
                    fecha_inicio = datetime.today() - timedelta(request.session['prev_days_reserva_vut'])
                    fecha_fin = datetime.today() + timedelta(request.session['next_days_reserva_vut'])
                else:
                    year = timezone.now().year
                    fecha_inicio = timezone.datetime(year, mes, 1)
                    fecha_fin = timezone.datetime(year, mes, monthrange(year, mes)[1])
                if vivienda == 'todas':
                    vivienda = viviendas
                    vivienda_selected = 'todas'
                else:
                    vivienda = [viviendas.get(id=request.POST['vivienda'])]
                    vivienda_selected = vivienda[0].id
                if portal == 'todos':
                    reservas = Reserva.objects.filter(vivienda__in=vivienda, borrada=False,
                                                      entrada__gte=fecha_inicio, estado='ACE',
                                                      entrada__lte=fecha_fin)
                else:
                    reservas = Reserva.objects.filter(vivienda__in=vivienda, borrada=False,
                                                      entrada__gte=fecha_inicio, estado='ACE',
                                                      entrada__lte=fecha_fin, portal=portal)
                total = reservas.aggregate(Sum('total'))['total__sum']
                dias = reservas.aggregate(Sum('noches'))['noches__sum']
                viajeros = Viajero.objects.filter(reserva__in=reservas).count()
                html = render_to_string('reservas_vut_tab.html', {'reservas': reservas, 'fecha_inicio': fecha_inicio,
                                                                  'fecha_fin': fecha_fin, 'viviendas': viviendas,
                                                                  'portales': PORTALES, 'portal_selected': portal,
                                                                  'vivienda_selected': vivienda_selected,
                                                                  'mes_selected': mes, 'total': total, 'dias': dias,
                                                                  'viajeros': viajeros})
                return JsonResponse({'ok': True, 'html': html})
            elif request.POST['action'] == 'change_tab_registros_policia':
                # registros = RegistroPolicia.objects.filter(vivienda__propietario=g_e)
                # html = render_to_string('reservas_vut_registros.html', {'registros': registros})
                fecha_inicio = datetime.today() - timedelta(request.session['prev_days_reserva_vut'])
                fecha_fin = datetime.today() + timedelta(1)
                viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_viajeros')
                reservas = Reserva.objects.filter(vivienda__in=viviendas, borrada=False,
                                                  entrada__gte=fecha_inicio,
                                                  entrada__lte=fecha_fin)
                viajeros = Viajero.objects.filter(reserva__in=reservas).order_by('-creado')
                html = render_to_string('reservas_vut_registros.html', {'viajeros': viajeros})
                return JsonResponse({'ok': True, 'html': html})
            elif request.POST['action'] == 'activar_registro':
                try:
                    viviendas = viviendas_con_permiso(g_e, 'comunica_registro_policia')
                    viajero = Viajero.objects.get(id=request.POST['viajero'])
                    vivienda = viajero.reserva.vivienda
                    if vivienda in viviendas:
                        try:
                            registro = RegistroPolicia.objects.get(viajero=viajero, vivienda=vivienda)
                            if isinstance(registro.observaciones, str):
                                registro.observaciones += '<br>Se hace un nuevo intento de registro.'
                            else:
                                registro.observaciones = '<br>Se hace un nuevo intento de registro.'
                            registro.enviado = False
                            registro.save()
                            comunica_viajero2PNGC.delay()
                            viajero.observaciones += '<br>Se hace un nuevo intento de registro.'
                        except:
                            crea_fichero_policia(viajero)
                            # registro = RegistroPolicia.objects.get(viajero=viajero, vivienda=vivienda)
                        # estado = graba_registro(registrPo)

                        return JsonResponse({'ok': True, 'observaciones': viajero.observaciones})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para realizar esta acción.'})
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
            elif request.POST['action'] == 'registrado_manualmente':
                try:
                    viviendas = viviendas_con_permiso(g_e, 'comunica_registro_policia')
                    viajero = Viajero.objects.get(id=request.POST['viajero'])
                    vivienda = viajero.reserva.vivienda
                    if vivienda in viviendas:
                        viajero.fichero_policia = True
                        viajero.observaciones = 'El viajero ha sido registrado manualmente a través de la página web ' \
                                                'de la Policía o de la Guardia Civil.'
                        viajero.save()
                        return JsonResponse({'ok': True, 'observaciones': viajero.observaciones})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para realizar esta acción.'})
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
            elif request.POST['action'] == 'viajeros_list':
                try:
                    viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_viajeros')
                    reserva = Reserva.objects.get(id=request.POST['reserva'], vivienda__in=viviendas)
                    viajeros = reserva.viajero_set.all()
                    html = render_to_string('reservas_vut_viajeros_reveal.html', {'viajeros': viajeros})
                    return JsonResponse({'ok': True, 'html': html})
                except:
                    return JsonResponse({'ok': True, 'mensaje': 'No tienes permiso para ver la información solicitada'})
            elif request.POST['action'] == 'update_calendarios':
                if request.POST['tipo'] == 'change_tab':
                    if 'updated_calendarios_vut' in request.session:
                        viviendas = []
                        r = {'nuevas': 0, 'actualizadas': 0, 'errores': 0, 'mensaje': ''}
                    else:
                        request.session['updated_calendarios_vut'] = datetime.now()
                        viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_reservas')
                        r = update_calendarios_vut(viviendas)
                else:
                    request.session['updated_calendarios_vut'] = datetime.now()
                    viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_reservas')
                    r = update_calendarios_vut(viviendas)
                    r['time'] = request.session['updated_calendarios_vut'].strftime('%H:%M')
                return JsonResponse({'ok': True, 'respuesta': r})
            elif request.POST['action'] == 'add_next_days_reserva_vut':
                viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_reservas')
                fecha_inicio = datetime.today() + timedelta(request.session['next_days_reserva_vut'])
                request.session['next_days_reserva_vut'] += 7
                fecha_fin = datetime.today() + timedelta(request.session['next_days_reserva_vut'])
                reservas = Reserva.objects.filter(vivienda__in=viviendas, borrada=False, entrada__gt=fecha_inicio,
                                                  entrada__lte=fecha_fin).distinct()
                html = render_to_string("reservas_vut_table.html", {'reservas': reservas})
                return JsonResponse({'ok': True, 'html': html, 'fecha': fecha_fin.strftime('%d-%m-%Y')})
            elif request.POST['action'] == 'add_prev_days_reserva_vut':
                viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_reservas')
                fecha_fin = datetime.today() - timedelta(request.session['prev_days_reserva_vut'])
                request.session['prev_days_reserva_vut'] += 7
                fecha_inicio = datetime.today() - timedelta(request.session['prev_days_reserva_vut'])
                reservas = Reserva.objects.filter(vivienda__in=viviendas, borrada=False, entrada__gte=fecha_inicio,
                                                  entrada__lt=fecha_fin).distinct()
                html = render_to_string("reservas_vut_table.html", {'reservas': reservas})
                return JsonResponse({'ok': True, 'html': html, 'fecha': fecha_inicio.strftime('%d-%m-%Y')})
            elif request.POST['action'] == 'delete_reserva':
                try:
                    viviendas = viviendas_con_permiso(g_e, 'borra_reservas')
                    reserva = Reserva.objects.get(id=request.POST['reserva'])
                    if reserva.vivienda in viviendas or not reserva.vivienda:
                        if Viajero.objects.filter(reserva=reserva).count() == 0:
                            reserva.borrada = True
                            reserva.save()
                            return JsonResponse({'ok': True})
                        else:
                            return JsonResponse({'ok': False, 'mensaje': 'Tiene viajeros registrados.'})
                    else:
                        return JsonResponse({'ok': False})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'open_accordion_registro':
                try:
                    viviendas = viviendas_con_permiso(g_e, 'autorizado_ver_viajeros')
                    viajero = Viajero.objects.get(id=request.POST['viajero'])
                    reserva = viajero.reserva
                    if reserva.vivienda in viviendas:
                        html = render_to_string('reservas_vut_registros_content.html', {'v': viajero, 'paises': PAISES})
                        reserva.save()
                        return JsonResponse({'ok': True, 'html': html})
                    else:
                        return JsonResponse({'ok': False})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'select_vivienda_reserva':
                try:
                    viviendas = viviendas_con_permiso(g_e, 'crea_reservas')
                    reserva = Reserva.objects.get(id=request.POST['reserva'])
                    vivienda = viviendas.get(id=request.POST['vivienda'])
                    reserva.vivienda = vivienda
                    reserva.save()
                    return JsonResponse({'ok': True})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'update_viajero':
                try:
                    viviendas = viviendas_con_permiso(g_e, 'crea_reservas')
                    viajero = Viajero.objects.get(id=request.POST['id_viajero'])
                    vivienda = viajero.reserva.vivienda
                    if vivienda in viviendas:
                        setattr(viajero, request.POST['campo'], request.POST['valor'])
                        viajero.save()
                        return JsonResponse({'ok': True})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': 'Sin permiso con ese viajero'})
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'Error'})
            elif request.POST['action'] == 'update_viajero_fecha':
                try:
                    viviendas = viviendas_con_permiso(g_e, 'crea_reservas')
                    viajero = Viajero.objects.get(id=request.POST['id_viajero'])
                    vivienda = viajero.reserva.vivienda
                    if vivienda in viviendas:
                        fecha = datetime.strptime(request.POST['valor'], '%d/%m/%Y')
                        setattr(viajero, request.POST['campo'], fecha)
                        viajero.save()
                        return JsonResponse({'ok': True})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': 'Sin permiso con ese viajero'})
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'Error'})
    else:
        if request.POST['action'] == 'upload_vut_file':
            excepciones = ''
            portales = {'BOO': 'Booking', 'WIM': 'Wimdu', 'HOM': 'Homeaway', 'AIR': 'Airbnb', 'REN': 'Rentalia',
                        'OAP': 'Only Apartments', 'NIU': 'Niumba'}
            air = ['Código de confirmación', 'Estado', 'Nombre de la persona', 'Contacto', 'N.º de adultos',
                   'N.º de niños', 'N.º de bebés', 'Fecha de inicio', 'Fecha de finalización', 'N.º de noches',
                   'Reservada', 'Anuncio', 'Pago de la ayuda por el coronavirus', 'Importe total del cobro',
                   'Importe de la reserva']
            # air = ['Código de confirmación', 'Estado', 'Nombre de la persona', 'Contacto', 'N.º de adultos',
            #        'N.º de niños', 'N.º de bebés', 'Fecha de inicio', 'Fecha de finalización', 'N.º de noches',
            #        'Reservada', 'Anuncio', 'Ingresos']
            # boo = ['Número de reserva', 'Reservado por', 'Nombre del cliente (o clientes)', 'Entrada', 'Salida',
            #        'Fecha de reserva', 'Estado', 'Habitaciones', 'Personas', 'Adultos', 'Niños', 'Edades de los niños:',
            #        'Precio', 'Comisión %', 'Importe de la comisión', 'Estado del pago', 'Forma de pago', 'Comentarios']
            boo = ['Número de reserva', 'Reservado por', 'Nombre del cliente (o clientes)', 'Entrada', 'Salida',
                   'Fecha de reserva', 'Estado', 'Habitaciones', 'Personas', 'Adultos', 'Niños', 'Edades de los niños:',
                   'Precio', 'Comisión %', 'Importe de la comisión', 'Estado del pago', 'Forma de pago', 'Comentarios',
                   'Grupo de reserva']
            portal = None
            n_files = int(request.POST['n_files'])
            informe_reservas = {'errores': [], 'nuevas': [], 'actualizadas': [], 'info': [], 'canceladas': [],
                                'solapadas': []}
            viviendas = viviendas_con_permiso(g_e, 'crea_reservas')
            fieldnames = []
            for i in range(n_files):
                fichero = request.FILES['fichero_xhr' + str(i)]
                if fichero.content_type == 'text/csv':
                    # a = fichero.file
                    # b= d
                    from io import TextIOWrapper
                    # f = TextIOWrapper(fichero.file, encoding=request.encoding)
                    # datareader = csv.reader(io.TextIOWrapper(webpage))
                    reader = csv.DictReader(TextIOWrapper(fichero))
                    fieldnames = reader.fieldnames
                    # if air[0] in fieldnames and len(fieldnames) == 13:
                    if air[0] in fieldnames:
                        portal = 'AIR'
                elif fichero.content_type == 'application/vnd.ms-excel':
                    book = xlrd.open_workbook(file_contents=fichero.read())
                    sheet = book.sheet_by_index(0)
                    fieldnames = [sheet.cell(0, col_index).value for col_index in range(sheet.ncols)]
                    # if boo[0] in fieldnames and len(fieldnames) == 18:
                    if boo[0] in fieldnames:
                        portal = 'BOO'
                if portal:
                    if portal == 'AIR':
                        # Equivalencia de campos y nuestro modelo en AIRBNB
                        obs = 'Anuncio'
                        code = 'Código de confirmación'  # .encode('utf-8')
                        entrada = 'Fecha de inicio'
                        noches = 'N.º de noches'  # .encode('utf-8')
                        adultos = 'N.º de adultos'  # .encode('utf-8')
                        ninos = 'N.º de niños'  # .encode('utf-8')
                        nombre = 'Nombre de la persona'
                        # total = 'Ingresos'
                        total = 'Importe total del cobro'
                        estado = 'Estado'
                        estados = {'Aceptada': 'ACE', 'Cancelada': 'CAN'}
                        for row in reader:
                            try:
                                reserva = Reserva.objects.get(code=row[code], vivienda__in=viviendas)
                                reserva.entrada = datetime.strptime(row[entrada], '%Y-%m-%d')
                                reserva.noches = int(row[noches])
                                reserva.num_viajeros = int(row[adultos]) + int(row[ninos])
                                reserva.borrada = False
                                reserva.estado = estados[row[estado]]
                                reserva.nombre = row[nombre]  # .decode('utf-8')
                                reserva.total = string2float(row[total])
                                reserva.portal = portal
                                reserva.save()
                                informe_reservas['actualizadas'].append(reserva)
                                solapadas = reservas_solapadas(reserva)
                                if solapadas:
                                    informe_reservas['solapadas'].append(solapadas)
                            except Exception as ex:
                                error = ''
                                if n_files > 1:
                                    error += 'Fichero: %s (%s). ' % (fichero.name, portales[portal])
                                error += 'La reserva %s (%s) no se ha podido registrar. Su estado es: %s' % (
                                    row[code], portales[portal], row[estado])
                                excepciones += "{0} {1} - {2!r}".format(row[code], type(ex).__name__, ex.args)
                                informe_reservas['errores'].append(error)
                    elif portal == 'BOO':
                        for row_index in range(1, sheet.nrows):
                            row = {fieldnames[col_index]: sheet.cell(row_index, col_index).value
                                   for col_index in range(sheet.ncols)}
                            reserva = None
                            entrada = datetime.strptime(row['Entrada'], '%Y-%m-%d').date()
                            code = '%s' % int(row['Número de reserva'])
                            estado = 'CAN' if 'cancelled' in row['Estado'] else 'ACE'
                            num_viajeros = row['Personas']
                            try:
                                reserva = Reserva.objects.get(entrada=entrada, code=code, vivienda__in=viviendas,
                                                              portal=portal)
                                if estado == 'CAN':
                                    informe_reservas['canceladas'].append(reserva)
                                else:
                                    informe_reservas['actualizadas'].append(reserva)
                            except:
                                reservas = Reserva.objects.filter(entrada=entrada, vivienda__in=viviendas,
                                                                  portal=portal)
                                for r in reservas:
                                    logger.info('reserva: %s -> Reservado por: %s. Coincide: %s' % (
                                        r.nombre, row['Reservado por'], (r.nombre.strip() in row['Reservado por'])))
                                    if r.nombre.strip() in row['Reservado por']:
                                        reserva = r
                                        if estado == 'CAN':
                                            informe_reservas['canceladas'].append(reserva)
                                        else:
                                            informe_reservas['actualizadas'].append(reserva)
                                if not reserva:
                                    reserva = Reserva.objects.create(entrada=entrada, code=code, portal=portal)
                                    if estado == 'CAN':
                                        informe_reservas['canceladas'].append(reserva)
                                    else:
                                        informe_reservas['nuevas'].append(reserva)
                            reserva.borrada = False
                            reserva.nombre = row['Reservado por']
                            salida = datetime.strptime(row['Salida'], '%Y-%m-%d').date()
                            reserva.noches = (salida - entrada).days
                            if row['Importe de la comisión']:
                                imp_comision = float(row['Importe de la comisión'].split()[0].replace(',', '.'))
                                comision = float(str(row['Comisión %']).split()[0].replace(',', '.'))
                            else:
                                imp_comision = 0
                                comision = 100
                            reserva.total = imp_comision * (100 - comision) / comision
                            # Se podría haber calculado el total así:
                            # total = float(row['Precio'].split()[0].replace(',', '.'))
                            # reserva.total = total - imp_comision
                            # Pero en las reservas canceladas podría ocurrir algún error.
                            reserva.limpieza = 0
                            reserva.estado = estado
                            reserva.code = code
                            reserva.num_viajeros = num_viajeros
                            reserva.save()
                            solapadas = reservas_solapadas(reserva)
                            if solapadas:
                                informe_reservas['solapadas'].append(solapadas)
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No se sabe el portal'})
            html = render_to_string('reservas_vut_mensaje_upload_vut_file.html',
                                    {'informe': informe_reservas, 'viviendas': viviendas})
            return JsonResponse({'html': html, 'portal': portal, 'ok': True, 'excepciones': excepciones})


def graba_registro(registro):
    viajero = registro.viajero
    vivienda = registro.vivienda
    try:
        if vivienda.police == 'GC':
            fichero = open(RUTA_BASE + registro.parte.url)
            logger.info("4")
            url = 'https://%s:%s@hospederias.guardiacivil.es/hospederias/servlet/ControlRecepcionFichero' % (
                vivienda.police_code, vivienda.police_pass)
            try:
                r = requests.post(url, files={'fichero': fichero}, data={}, verify=False, timeout=5)
            except:
                return False
            if r.status_code == 200:
                if 'Errores' in r.text:
                    gauser_autorizados = Autorizado.objects.filter(vivienda=vivienda).values_list('gauser__id',
                                                                                                  flat=True)
                    receptores = Gauser.objects.filter(
                        Q(id__in=gauser_autorizados) | Q(id__in=vivienda.propietarios.all()))
                    mensaje = '<p>En el registro de %s, reserva %s</p><p>La Guardia Civil dice:</p>%s' % (
                        viajero.nombre_completo, viajero.reserva, r.text.replace('\r\n', '<br>'))
                    viajero.observaciones += mensaje
                    emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0],
                                                      ronda=vivienda.entidad.ronda)
                    encolar_mensaje(emisor=emisor, receptores=receptores,
                                    asunto='Error en comunicación a la Guardia Civil', html=mensaje,
                                    etiqueta='guardia_civl%s' % vivienda.id)
                else:
                    viajero.fichero_policia = True
                    mensaje = '<p>En el registro de %s, reserva %s</p><p>La Guardia Civil dice:</p>%s' % (
                        viajero.nombre_completo, viajero.reserva, r.text.replace('\r\n', '<br>'))
                    viajero.observaciones += mensaje
                    emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0],
                                                      ronda=vivienda.entidad.ronda)
                    encolar_mensaje(emisor=emisor, receptores=vivienda.propietarios.all(),
                                    asunto='Comunicación a la Guardia Civil', html=mensaje,
                                    etiqueta='guardia_civl%s' % vivienda.id)
                viajero.save()
                fichero.close()
                return True
            else:
                gauser_autorizados = Autorizado.objects.filter(vivienda=vivienda).values_list('gauser__id',
                                                                                              flat=True)
                receptores = Gauser.objects.filter(id__in=gauser_autorizados)
                mensaje = '<p>No se ha podido establecer comunicación con la Guardia Civil.</p>'
                viajero.observaciones += mensaje
                emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
                encolar_mensaje(emisor=emisor, receptores=receptores,
                                asunto='Error en comunicación a la Guardia Civil', html=mensaje,
                                etiqueta='guardia_civl%s' % vivienda.id)
                viajero.save()
                fichero.close()
                return False
        elif vivienda.police == 'PN':
            logger.info("entra al registro PN. Viajero: %s" % viajero)
            # Iniciamos una sesión
            s = requests.Session()
            s.verify = False  # Para que los certificados ssl no sean verificados. Comunicación https confiada
            # Accedemos a la página de inicio y de la respuesta capturamos el token csrf
            try:
                p1 = s.get('https://webpol.policia.es/e-hotel/', timeout=5)
            except:
                return False
            # Escribimos las cookies en una cadena de texto, para introducirlas en las distintas cabeceras
            cookies_header = ''
            for c in dict(s.cookies):
                cookies_header += '%s=%s;' % (c, dict(s.cookies)[c])
            # Debemos salvar el token csrf de la sesión, que utilizaremos en los diferentes enlaces
            soup1 = BeautifulSoup(p1.content.decode(p1.encoding), 'html.parser')
            csrf_token = soup1.find('input', {'name': '_csrf'})['value']
            # El siguiente paso que da el sistema es la obtención de etiquetas de su sistema "ARGOS"
            # obtener_etiquetas_url = 'https://webpol.policia.es/e-hotel/obtenerEtiquetas'
            # obtener_etiquetas_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
            #                              'Accept-Encoding': 'gzip, deflate, br',
            #                              'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            #                              'Ajax-Referer': '/e-hotel/obtenerEtiquetas', 'Connection': 'keep-alive',
            #                              'Content-Length': '0',
            #                              'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            #                              'Cookie': cookies_header,
            #                              'Host': 'webpol.policia.es',
            #                              'Referer': 'https://webpol.policia.es/e-hotel/',
            #                              'User-Agent': 'python-requests/2.11.1',
            #                              'X-CSRF-TOKEN': csrf_token,
            #                              'X-Requested-With': 'XMLHttpRequest'}
            # try:
            #     p11 = s.post(obtener_etiquetas_url, headers=obtener_etiquetas_headers, cookies=dict(s.cookies),
            #                  timeout=5)
            # except:
            #     return False
            # Cargamos los valores de los inputs demandados para hacer el login y enviamos el post con el payload
            # En este caso enviamos: headers, cookies y parámetros (payload)
            payload = {'username': vivienda.police_code, '_csrf': csrf_token, 'password': vivienda.police_pass}
            execute_login_headers = {'Accept': 'text/html,  application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8',
                                     'Accept-Encoding': 'gzip, deflate, br',
                                     'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                     'Connection': 'keep-alive',
                                     'Content-Type': 'application/x-www-form-urlencoded',
                                     'Cookie': cookies_header,
                                     'Host': 'webpol.policia.es', 'Referer': 'https://webpol.policia.es/e-hotel/',
                                     'Upgrade-Insecure-Requests': '1', 'User-Agent': 'python-requests/2.21.0'}
            try:
                p2 = s.post('https://webpol.policia.es/e-hotel/execute_login', data=payload,
                            headers=execute_login_headers, timeout=5)
            except:
                return False
            # A continuación hacemos una petición GET a inicio sin ningún parámetro
            execute_inicio_headers = {
                'Accept': 'text/html,  application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                'Connection': 'keep-alive', 'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                'Referer': 'https://webpol.policia.es/e-hotel/', 'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'python-requests/2.21.0'}
            try:
                p21 = s.get('https://webpol.policia.es/e-hotel/inicio', headers=execute_inicio_headers, timeout=5)
            except:
                return False
            # Hacemos una comprabción para asegurarnos de que se ha accedido correctamente a la webpol.
            # Si la respuesta es correcta la respuesta contendrá el usuario:
            if vivienda.police_code in p21.content.decode(p2.encoding):
                # El siguiente paso es obtener etiquetas. Esta es una solicitud POST sin payload
                # obtener_etiquetas_url = 'https://webpol.policia.es/e-hotel/obtenerEtiquetas'
                # obtener_etiquetas_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                #                              'Accept-Encoding': 'gzip, deflate, br',
                #                              'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                #                              'Ajax-Referer': '/e-hotel/obtenerEtiquetas',
                #                              'Connection': 'keep-alive',
                #                              'Content-Length': '0',
                #                              'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                #                              'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                #                              'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                #                              'User-Agent': 'python-requests/2.11.1',
                #                              'X-CSRF-TOKEN': '92a4cc08-b50b-4be3-8a98-8adf8bb1db2e',
                #                              'X-Requested-With': 'XMLHttpRequest'}
                # try:
                #     p22 = s.post(obtener_etiquetas_url, headers=obtener_etiquetas_headers, cookies=dict(s.cookies),
                #                  timeout=5)
                # except:
                #     return False
                # A continuación debemos ir a la grabación manual. Antes se hace una llamada para limpiar la sesión
                limpiar_sesion_temporal_url = 'https://webpol.policia.es/e-hotel/limpiarSesionTemporal'
                limpiar_sesion_temporal_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                                                   'Accept-Encoding': 'gzip, deflate, br',
                                                   'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                                   'Ajax-Referer': '/e-hotel/limpiarSesionTemporal',
                                                   'Connection': 'keep-alive', 'Content-Length': '0',
                                                   'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                                   'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                                   'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                                   'User-Agent': 'python-requests/2.21.0',
                                                   'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                try:
                    p23 = s.post(limpiar_sesion_temporal_url, headers=limpiar_sesion_temporal_headers, timeout=5)
                except:
                    return False
                # Ahora es cuando se hace otra petición POST para llegar a la grabación manual sin payload
                logger.info("5")
                grabador_manual_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/vista/grabadorManual'
                grabador_manual_headers = {'Accept': 'text/html, */*; q=0.01',
                                           'Accept-Encoding': 'gzip, deflate, br',
                                           'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                           'Ajax-Referer': '/e-hotel/hospederia/manual/vista/grabadorManual',
                                           'Connection': 'keep-alive',
                                           'Content-Length': '0',
                                           'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                           'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                           'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                           'User-Agent': 'python-requests/2.21.0',
                                           'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                try:
                    p3 = s.post(grabador_manual_url, headers=grabador_manual_headers, timeout=5)
                    logger.info("Entrada en grabador manual")
                    sleep(10)
                except:
                    logger.info("Error al entrar en grabador manual")
                    return False
                # En esta petición nos han devuelto el id de la hospedería. Lo tenemos que guardar:
                soup3 = BeautifulSoup(p3.content.decode(p3.encoding), 'html.parser')
                idHospederia = soup3.find('input', {'id': 'idHospederia'})['value']
                logger.info('idHospederia %s' % idHospederia)
                # Pasamos a rellenar el parte del viajero. Necesitamos algunos campos como sexoStr o tipoDocumentoStr.
                # En el caso de sexoStr debemos asignar el texto MASCULINO o FEMENINO, que es diferente de
                # get_sexo_display() y por eso definimos el siguiente diccionario.
                sexo = {'M': 'MASCULINO', 'F': 'FEMENINO'}
                data_viajero = {'nombre': viajero.nombre, 'apellido1': viajero.apellido1,
                                'apellido2': viajero.apellido2, 'nacionalidad': viajero.pais,
                                'tipoDocumento': viajero.tipo_ndi, 'numIdentificacion': viajero.ndi,
                                'fechaExpedicionDoc': viajero.fecha_exp.strftime('%d/%m/%Y'),
                                'dia': '%s' % viajero.nacimiento.day, 'mes': '%s' % viajero.nacimiento.month,
                                'ano': '%s' % viajero.nacimiento.year, 'idHospederia': idHospederia,
                                'fechaEntrada': viajero.fecha_entrada.strftime('%d/%m/%Y'), 'sexo': viajero.sexo,
                                'fechaNacimiento': viajero.nacimiento.strftime('%d/%m/%Y'), '_csrf': csrf_token,
                                'jsonHiddenComunes': '',
                                'nacionalidadStr': viajero.get_pais_display().encode('utf-8'),
                                'sexoStr': sexo[viajero.sexo], 'tipoDocumentoStr': viajero.get_tipo_ndi_display()}
                logger.info("Definido data_viajero")
                huesped_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/insertar/huesped'
                huesped_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                   'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                   'Ajax-Referer': '/e-hotel/hospederia/manual/insertar/huesped',
                                   'Connection': 'keep-alive',
                                   'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                   'Cookie': cookies_header,
                                   'Host': 'webpol.policia.es',
                                   'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                   'User-Agent': 'python-requests/2.21.0',
                                   'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                logger.info("Definido huesped_headers")
                try:
                    p4 = s.post(huesped_url, data=data_viajero, headers=huesped_headers, timeout=5)
                    logger.info("Enviados datos del huesped")
                    sleep(4)
                except:
                    logger.info("Error al enviar datos del huesped")
                    return False
                # En esta petición nos devuelven datos que no vamos a necesitar, pero que almacenamos para guarar en
                # la información del registro.
                soup4 = BeautifulSoup(p4.content.decode(p4.encoding), 'html.parser')
                logger.info("Se ha recibido respuesta de la policia")
                mensaje = soup4.find('em')
                logger.info("Parseado mensaje de correcto o incorrecto")
                huespedJson = soup4.find('input', {'name': 'huespedJson'})['value']
                logger.info("Parseado huespedJson")
                idHuesped = soup4.find('input', {'name': 'idHuesped'})['value']
                logger.info("Parseado idHuesped")
                viajero.observaciones += "Mensaje de la Policía: %s<br>idHuesped: %s<br>idHospederia: %s" % (
                    mensaje, idHuesped, idHospederia)
                logger.info("Se han grabado las observaciones")
                # Para completar la grabación es necesario llamar a parteViajero a través de una petición GET:
                parte_viajero_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/vista/parteViajero'
                parte_viajero_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                         'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                         'Ajax-Referer': '/e-hotel/hospederia/manual/insertar/huesped',
                                         'Connection': 'keep-alive',
                                         'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                         'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                         'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                         'User-Agent': 'python-requests/2.21.0',
                                         'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                try:
                    p5 = s.get(parte_viajero_url, headers=parte_viajero_headers, timeout=5)
                    logger.info("Enviado GET a parteViajero")
                    sleep(4)
                except:
                    logger.info("Error al procesar parteViajero")
                # En siguiente paso dado a través de un navegador es llamar a tipoDocumentoNacionalidad con una
                # petición POST enviando como parámetro la "nacionalidad":
                nacionalidad_url = 'https://webpol.policia.es/e-hotel/combo/tipoDocumentoNacionalidad'
                nacionalidad_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                        'Ajax-Referer': '/e-hotel/combo/tipoDocumentoNacionalidad',
                                        'Connection': 'keep-alive',
                                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                        'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                        'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                        'User-Agent': 'python-requests/2.21.0',
                                        'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                payload = {'nacionalidad': viajero.pais}
                try:
                    p6 = s.post(nacionalidad_url, headers=nacionalidad_headers, data=payload, timeout=5)
                    logger.info("Enviado POST a tipoDocumentoNacionalidad")
                except:
                    logger.info("Error al enviar POST a tipoDocumentoNacionalidad")

                generar_parte_url = 'https://webpol.policia.es/e-hotel/hospederia/generarParteHuesped'
                generar_parte_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                         'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                         'Ajax-Referer': '/e-hotel/hospederia/generarParteHuesped',
                                         'Connection': 'keep-alive',
                                         'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                         'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                         'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                         'User-Agent': 'python-requests/2.21.0',
                                         'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                payload = {'huespedJson': huespedJson, 'idHuesped': idHuesped}

                try:
                    p7 = s.post(generar_parte_url, headers=generar_parte_headers, data=payload, timeout=5)
                    logger.info("Solicitud generar PDF")
                except:
                    logger.info("Error al solicitar generar PDF")

                previsualiza_url = 'https://webpol.policia.es/e-hotel/previsualizacionPdf/'
                previsualiza_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                        'Ajax-Referer': '/e-hotel/hospederia/generarParteHuesped',
                                        'Connection': 'keep-alive',
                                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                        'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                        'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                        'User-Agent': 'python-requests/2.21.0',
                                        'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}

                try:
                    p8 = s.get(previsualiza_url, headers=previsualiza_headers, timeout=5)
                    logger.info("Solicitud previsualizar PDF")
                except:
                    logger.info("Error al solicitar previsualizar PDF")

                genera_url = 'https://webpol.policia.es/e-hotel/hospederia/generarPDFparteHuesped'
                genera_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                  'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                  'Connection': 'keep-alive',
                                  'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                  'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                  'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                  'User-Agent': 'python-requests/2.21.0',
                                  'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                try:
                    p9 = s.get(genera_url, headers=genera_headers, timeout=5)
                    fPN = ContentFile(p9.content)
                    fPN.name = '%s.pdf' % viajero.id
                    registro.pdf_PN = fPN
                    registro.save()
                    logger.info("Solicitud generar parte PDF")
                except:
                    logger.info("Error al solicitar generar parte PDF")

                # En este punto termina el proceso de grabación
                if p4.status_code == 200:
                    logger.info(u'Todo correcto')
                    s.close()
                    viajero.fichero_policia = True
                    viajero.observaciones += '<br><span style="color:green;">Registro finalizado con todas las comunicaciones correctas.</span>'
                    viajero.observaciones += '<hr>Información JSON: <br> %s' % huespedJson
                    viajero.save()
                    return True
                else:
                    logger.info('Error durante el grabado del viajero. Hacer el registro manualmente.')
                    viajero.observaciones += '<br><span style="color:red;">Error durante el grabado del viajero. Hacer el registro manualmente.</span>'
                    viajero.save()
                    s.close()
                    return p4
            else:
                logger.info('Error al hacer el login en webpol para el viajero: %s' % (viajero))
                viajero.observaciones += 'Error al hacer el login en webpol para el viajero'
                viajero.save()
                s.close()
        else:
            return False
    except:
        logger.info("6")
        mensaje = 'Error en la comunicación con Policía/Guardia Civil. Se debe hacer el registro manualmente.'
        ronda = viajero.reserva.vivienda.entidad.ronda
        permiso = Permiso.objects.get(code_nombre='recibe_errores_de_viajeros')
        receptores_ge = Gauser_extra.objects.filter(ronda=ronda, permisos__in=[permiso])
        receptores = Gauser.objects.filter(id__in=receptores_ge.values_list('gauser__id', flat=True))
        emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
        encolar_mensaje(emisor=emisor, receptores=receptores,
                        asunto='Error en RegistroPolicia', html=mensaje, etiqueta='error%s' % ronda.id)
        return False


def crea_fichero_policia(viajero):
    logger.info("1")
    if type(viajero) is not Viajero:
        return False
    if not viajero.observaciones:
        viajero.observaciones = ''
        viajero.save()
    vivienda = viajero.reserva.vivienda
    try:
        fich_name = '%s.001' % (vivienda.police_code)
        ruta = os.path.join("%svut/" % (RUTA_MEDIA), fich_name)
        f = open(ruta, "wb+")
        contenido = render_to_string('fichero_registro_policia.vut', {'v': vivienda, 'vs': [viajero]})
        f.write(contenido.encode('utf-8'))
        RegistroPolicia.objects.create(vivienda=vivienda, parte=File(f), viajero=viajero)
        comunica_viajero2PNGC.delay()
        f.close()
        if os.path.isfile(ruta):
            os.remove(ruta)
        logger.info("2")
        return True
    except:
        mensaje = 'Error en la elaboración del RegistroPolicia. No se ha podido crear el fichero de registro.'
        ronda = viajero.reserva.vivienda.entidad.ronda
        emisor = Gauser_extra.objects.get(gauser=viajero.reserva.vivienda.propietarios.all()[0], ronda=ronda)
        permiso = Permiso.objects.get(code_nombre='recibe_errores_de_viajeros')
        receptores_ge = Gauser_extra.objects.filter(ronda=ronda, permisos__in=[permiso], activo=True)
        receptores = Gauser.objects.filter(id__in=receptores_ge.values_list('gauser__id', flat=True))
        encolar_mensaje(emisor=emisor, receptores=receptores,
                        asunto='Error en RegistroPolicia', html=mensaje, etiqueta='error%s' % ronda.id)
        logger.info(mensaje)
        return False


@permiso_required('edita_reservas')
def registro_viajero_manual(request):
    g_e = request.session['gauser_extra']
    year = datetime.today().year
    anyos = range(year, year - 100, -1)
    if request.method == 'GET':
        try:
            secret = request.GET['s']
            code = request.GET['c']
            viviendas = viviendas_con_permiso(g_e, 'edita_reservas')
            reserva = Reserva.objects.get(secret=secret, code=code)
            if reserva.vivienda in viviendas:
                domoticas = DomoticaVUT.objects.filter(vivienda=reserva.vivienda)
                return render(request, "registro_entrada_viajero_manual.html",
                              {
                                  'formname': 'registro_viajero',
                                  'reserva': reserva,
                                  'paises': PAISES,
                                  'secret': secret,
                                  'code': code,
                                  'anyos': anyos,
                                  'domoticas': domoticas
                              })
        except:
            return render(request, "registro_entrada_viajero_error.html", {'mensaje': 'No tienes permisos'})
    elif request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'enviar_datos':
            try:
                secret = request.POST['secret']
                code = request.POST['code']
                reserva = Reserva.objects.get(secret=secret, code=code)
                viajero, creado = Viajero.objects.get_or_create(reserva=reserva, ndi=request.POST['ndi'])
                if not creado:
                    ruta = os.path.join(
                        "%svut/%s/firmas/" % (RUTA_MEDIA, reserva.vivienda.id),
                        str(reserva.code) + '_' + str(viajero.ndi) + '.png')
                    if os.path.isfile(ruta):
                        os.remove(ruta)
                firma_data = request.POST['firma']
                format, imgstr = firma_data.split(';base64,')
                ext = format.split('/')[-1]
                viajero.firma = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
                viajero.tipo_ndi = request.POST['tipo_ndi']
                viajero.fecha_exp = datetime.strptime(request.POST['fecha_exp'], '%Y-%m-%d')
                viajero.apellido1 = request.POST['apellido1'][:30]
                viajero.apellido2 = request.POST['apellido2'][:30]
                viajero.nombre = request.POST['nombre'][:30]
                viajero.sexo = request.POST['sexo']
                viajero.nacimiento = datetime.strptime(request.POST['nacimiento'], '%Y-%m-%d')
                viajero.pais = request.POST['pais']
                viajero.save()
                crea_fichero_policia(viajero)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'domotica':
            try:
                domotica = DomoticaVUT.objects.get(id=request.POST['domotica'])
                s = requests.Session()
                s.verify = False
                p = s.post(domotica.url, timeout=5)
                return JsonResponse({'ok': True, 'response': p.status_code})
            except:
                return JsonResponse({'ok': False})

    return JsonResponse({'ok': False})


################################################################################

def viajeros(request):
    year = datetime.today().year
    anyos = range(year, year - 100, -1)
    hoy = datetime.today().date()
    if request.method == 'GET':
        try:
            secret = request.GET['s']
            code = request.GET['c']
            reserva = Reserva.objects.get(secret=secret, code=code, entrada__lte=hoy)
            domoticas = DomoticaVUT.objects.filter(vivienda=reserva.vivienda)
            if reserva.salida < hoy:
                return render(request, "registro_entrada_viajero_error.html", {'fechas': False})
            else:
                return render(request, "registro_entrada_viajero.html",
                              {
                                  'formname': 'registro_viajero',
                                  'reserva': reserva,
                                  'paises': PAISES,
                                  'secret': secret,
                                  'code': code,
                                  'anyos': anyos,
                                  'domoticas': domoticas
                              })
        except:
            try:
                reserva = Reserva.objects.get(secret=secret, code=code, entrada__gt=hoy)
                data = {'fechas': True, 'entrada': reserva.entrada, 'salida': reserva.salida}
            except:
                data = {'fechas': False}
            return render(request, "registro_entrada_viajero_error.html", data)
    elif request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'enviar_datos':
            try:
                secret = request.POST['secret']
                code = request.POST['code']
                hoy = datetime.today().date()
                reserva = Reserva.objects.get(secret=secret, code=code, entrada__lte=hoy)
                if reserva.salida < hoy:
                    return JsonResponse({'ok': False})
                else:
                    viajero, creado = Viajero.objects.get_or_create(reserva=reserva, ndi=request.POST['ndi'])
                    if not creado:
                        ruta = os.path.join(
                            "%svut/%s/firmas/" % (RUTA_MEDIA, reserva.vivienda.id),
                            str(reserva.code) + '_' + str(viajero.ndi) + '.png')
                        if os.path.isfile(ruta):
                            os.remove(ruta)
                    firma_data = request.POST['firma']
                    format, imgstr = firma_data.split(';base64,')
                    ext = format.split('/')[-1]
                    viajero.firma = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
                    viajero.tipo_ndi = request.POST['tipo_ndi']
                    viajero.fecha_exp = datetime.strptime(request.POST['fecha_exp'], '%Y-%m-%d')
                    viajero.apellido1 = request.POST['apellido1'][:30]
                    viajero.apellido2 = request.POST['apellido2'][:30]
                    viajero.nombre = request.POST['nombre'][:30]
                    viajero.sexo = request.POST['sexo']
                    viajero.nacimiento = datetime.strptime(request.POST['nacimiento'], '%Y-%m-%d')
                    viajero.pais = request.POST['pais']
                    viajero.save()
                    crea_fichero_policia(viajero)
                    return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'domotica':
            try:
                domotica = DomoticaVUT.objects.get(id=request.POST['domotica'])
                secret = request.POST['secret']
                code = request.POST['code']
                hoy = datetime.today().date()
                reserva = Reserva.objects.get(secret=secret, code=code, entrada__lte=hoy)
                if reserva.salida < hoy:
                    return JsonResponse({'ok': False})
                else:
                    s = requests.Session()
                    s.verify = False
                    p = s.post(domotica.url, timeout=5)
                    return JsonResponse({'ok': True, 'response': p.status_code})
            except:
                return JsonResponse({'ok': False})

    return JsonResponse({'ok': False})


def rvpd(request, secret_id):  # rvpd: recepción viajeros policía y domótica
    year = datetime.today().year
    anyos = range(year, year - 100, -1)
    hoy = datetime.today().date()
    try:
        reserva = Reserva.objects.get(secret=secret_id)
        if hoy < reserva.entrada:
            data = {'fechas': True, 'entrada': reserva.entrada, 'salida': reserva.salida}
            return render(request, "rvpd_error.html", data)
        elif hoy > reserva.salida:
            return render(request, "rvpd_error.html", {'fechas': True, 'entrada': False})
    except:
        return render(request, "rvpd_error.html", {'fechas': False})

    if request.method == 'GET':
        domoticas = DomoticaVUT.objects.filter(vivienda=reserva.vivienda)
        return render(request, "rvpd.html",
                      {
                          'formname': 'rvpd',
                          'reserva': reserva,
                          'paises': PAISES,
                          'anyos': anyos,
                          'domoticas': domoticas
                      })
    elif request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'enviar_datos':
            try:
                viajero, creado = Viajero.objects.get_or_create(reserva=reserva, ndi=request.POST['ndi'])
                if not creado:
                    ruta = os.path.join(
                        "%svut/%s/firmas/" % (RUTA_MEDIA, reserva.vivienda.id),
                        str(reserva.code) + '_' + str(viajero.ndi) + '.png')
                    if os.path.isfile(ruta):
                        os.remove(ruta)
                firma_data = request.POST['firma']
                format, imgstr = firma_data.split(';base64,')
                ext = format.split('/')[-1]
                viajero.firma = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
                viajero.tipo_ndi = request.POST['tipo_ndi']
                viajero.fecha_exp = datetime.strptime(request.POST['fecha_exp'], '%Y-%m-%d')
                viajero.apellido1 = request.POST['apellido1'][:30]
                viajero.apellido2 = request.POST['apellido2'][:30]
                viajero.nombre = request.POST['nombre'][:30]
                viajero.sexo = request.POST['sexo']
                viajero.nacimiento = datetime.strptime(request.POST['nacimiento'], '%Y-%m-%d')
                viajero.pais = request.POST['pais']
                viajero.save()
                crea_fichero_policia(viajero)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'domotica':
            try:
                domotica = DomoticaVUT.objects.get(id=request.POST['domotica'])
                s = requests.Session()
                s.verify = False
                p = s.post(domotica.url, timeout=5)
                return JsonResponse({'ok': True, 'response': p.status_code})
            except:
                return JsonResponse({'ok': False})
    return JsonResponse({'ok': False})


################################################################################

@permiso_required('viviendas_registradas_vut')
def viviendas_registradas_vut(request):
    g_e = request.session['gauser_extra']
    usuarios = usuarios_ronda(g_e.ronda)
    propietarios = usuarios.values_list('gauser__id', flat=True)
    viviendas = Vivienda.objects.filter(propietarios__in=propietarios, borrada=False)
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'borra_vivienda_registrada':
            try:
                usuario = Gauser_extra.objects.get(id=request.POST['usuario'], ronda=g_e.ronda)
                vivienda = Vivienda.objects.get(id=request.POST['vivienda'], propietarios__in=[usuario.gauser])
                if vivienda.propietarios.all().count() >= 1:
                    vivienda.propietarios.remove(usuario.gauser)
                else:
                    vivienda.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'crea_nueva_vivienda':
            try:
                usuario = Gauser_extra.objects.get(id=request.POST['usuario'], ronda=g_e.ronda)
                vivienda = Vivienda.objects.create(nregistro=request.POST['num_registro'], gpropietario=usuario.gauser,
                                                   nombre='Vivienda creada', entidad=g_e.ronda.entidad)
                vivienda.propietarios.add(usuario.gauser)
                return JsonResponse({'ok': True, 'id': vivienda.id, 'reg': vivienda.nregistro})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'filtra_viviendas':
            try:
                texto = request.POST['texto']
                f_u = Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)
                usuarios_f = usuarios.filter(f_u)
                propietarios = usuarios_f.values_list('gauser__id', flat=True)
                f_v = Q(nombre__icontains=texto) | Q(address__icontains=texto) | Q(municipio__icontains=texto) | Q(
                    propietarios__in=propietarios)
                viviendas = viviendas.filter(f_v)
                set_usuarios = set(viviendas.values_list('propietarios__id', flat=True)) | set(propietarios)
                usuarios = usuarios.filter(gauser__id__in=set_usuarios)
                html = render_to_string("viviendas_registradas_vut_tbody.html",
                                        {'socios': usuarios, 'viviendas': viviendas, 'g_e': g_e})
                return JsonResponse({'ok': True, 'texto': texto, 'html': html})
            except:
                return JsonResponse({'ok': False})

    return render(request, "viviendas_registradas_vut.html",
                  {
                      'formname': 'viviendas_registradas_vut',
                      'socios': usuarios,
                      'num_propietarios': len(set(viviendas.values_list('propietarios', flat=True))),
                      'viviendas': viviendas,
                      'g_e': g_e
                  })


################################################################################
################################################################################

def contabilidades_autorizado(g_e):
    cbs_id = AutorizadoContabilidadVut.objects.filter(autorizado=g_e.gauser, contabilidad__borrada=False).values_list(
        'contabilidad__id', flat=True)
    q1 = Q(propietario=g_e.gauser)
    q2 = Q(borrada=False)
    q3 = Q(id__in=cbs_id)
    return ContabilidadVUT.objects.filter((q1 & q2) | q3).distinct()


@permiso_required('acceso_contabilidad_vut')
def contabilidad_vut(request):
    g_e = request.session['gauser_extra']
    ca = AutorizadoContabilidadVut.objects.filter(autorizado=g_e.gauser).values_list('contabilidad__id', flat=True)
    q = (Q(propietario=g_e.gauser) | Q(id__in=ca)) & Q(borrada=False)
    contabilidades = ContabilidadVUT.objects.filter(q).distinct()
    hoy = timezone.now().date()
    actuales = contabilidades.filter(inicio__lte=hoy, fin__gte=hoy)
    for con_actual in actuales:
        for portal in con_actual.portales:
            try:
                PartidaVUT.objects.get(contabilidad=con_actual, tipo='I_%s' % portal)
            except:
                PartidaVUT.objects.create(contabilidad=con_actual, tipo='I_%s' % portal,
                                          nombre='Ingresos realizados por plataforma')
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'libro_contabilidad_vut':
            permiso = Permiso.objects.get(code_nombre='genera_libro_registro_policia')
            vivienda = Vivienda.objects.get(id=request.POST['id_vivienda'])
            if has_permiso_on_vivienda(g_e, vivienda, permiso):
                fecha_anterior_limite = datetime.today().date() - timedelta(1100)
                viajeros = Viajero.objects.filter(reserva__vivienda=vivienda,
                                                  reserva__entrada__gte=fecha_anterior_limite)
                c = render_to_string('libro_registro_policia.html',
                                     {'vivienda': vivienda, 'viajeros': viajeros, 'ruta_base': RUTA_BASE})
                ruta = '%sentidad_%s/vivienda%s/' % (MEDIA_VUT, vivienda.entidad.code, vivienda.id)
                fich = html_to_pdf(request, c, fichero='libro_registros', media=ruta,
                                   title=u'Libro de registro de viajeros', tipo='sin_cabecera')
                response = FileResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=Libro_registro_viajeros.pdf'
                return response
        elif action == 'download_file_asiento':
            asiento = AsientoVUT.objects.get(id=request.POST['asiento'])
            permiso = Permiso.objects.get(code_nombre='edita_asiento_vut')
            a = AutorizadoContabilidadVut.objects.filter(contabilidad=asiento.partida.contabilidad,
                                                         autorizado=g_e.gauser, permisos__in=[permiso]).count()
            if asiento.partida.contabilidad.propietario == g_e.gauser or a > 0:
                fich = open(RUTA_BASE + asiento.fichero.url, 'rb')
                response = FileResponse(fich, content_type=asiento.content_type)
                response['Content-Disposition'] = 'attachment; filename=' + asiento.fich_name
                return response

    return render(request, "contabilidad_vut.html",
                  {
                      'formname': 'contabilidad_vut',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nueva contabilidad',
                            'permiso': 'crea_contabilidad_vut', 'title': 'Crear un nuevo registro de contabilidad'},
                           ),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'contabilidades': contabilidades,
                      'usuarios': usuarios_ronda(g_e.ronda)
                  })


@login_required()
def ajax_contabilidad_vut(request):
    g_e = request.session["gauser_extra"]
    if request.is_ajax():
        if request.method == 'POST':
            if request.POST['action'] == 'crea_contabilidad_vut' and g_e.has_permiso('crea_contabilidad_vut'):
                try:
                    year = timezone.now().year
                    inicio = timezone.datetime.strptime('01/01/%s' % year, '%d/%m/%Y')
                    fin = timezone.datetime.strptime('31/12/%s' % year, '%d/%m/%Y')
                    contabilidad = ContabilidadVUT.objects.create(propietario=g_e.gauser, entidad=g_e.ronda.entidad,
                                                                  inicio=inicio, fin=fin, describir='')
                    viviendas = viviendas_con_permiso(g_e, 'crea_contabilidad_vut')
                    contabilidad.viviendas.add(*viviendas)
                    for portal in contabilidad.portales:
                        try:
                            PartidaVUT.objects.get(contabilidad=contabilidad, tipo='I_%s' % portal)
                        except:
                            PartidaVUT.objects.create(contabilidad=contabilidad, tipo='I_%s' % portal,
                                                      nombre='Ingresos realizados por plataforma')
                    html = render_to_string('contabilidad_vut_accordion.html', {'contabilidad': contabilidad})
                    return JsonResponse({'html': html, 'ok': True})
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para crear una contabilidad'})
            elif request.POST['action'] == 'open_accordion':
                try:
                    contabilidad = ContabilidadVUT.objects.get(id=request.POST['contabilidad'])
                    if contabilidad in contabilidades_autorizado(g_e):
                        html = render_to_string('contabilidad_vut_accordion_content.html',
                                                {'contabilidad': contabilidad, 'g_e': g_e})
                        return JsonResponse({'ok': True, 'html': html})
                    else:
                        return JsonResponse({'ok': False})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'borra_contabilidad_vut' and g_e.has_permiso('borra_contabilidad_vut'):
                try:
                    contabilidad = ContabilidadVUT.objects.get(id=request.POST['contabilidad'])
                    permiso = Permiso.objects.get(code_nombre='borra_contabilidad_vut')
                    a = AutorizadoContabilidadVut.objects.filter(contabilidad=contabilidad, autorizado=g_e.gauser,
                                                                 permisos__in=[permiso]).count()
                    if contabilidad.propietario == g_e.gauser or a > 0:
                        contabilidad.borrada = True
                        contabilidad.save()
                        return JsonResponse({'ok': True, 'mensaje': "La contabilidad se ha borrado sin incidencias."})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar la contabilidad."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar la contabilidad."})
            elif request.POST['action'] == 'update_campo':
                try:
                    contabilidad = ContabilidadVUT.objects.get(id=request.POST['contabilidad'])
                    permiso = Permiso.objects.get(code_nombre='edita_contabilidad_vut')
                    a = AutorizadoContabilidadVut.objects.filter(contabilidad=contabilidad, autorizado=g_e.gauser,
                                                                 permisos__in=[permiso]).count()
                    if contabilidad.propietario == g_e.gauser or a > 0:
                        campo = request.POST['campo']
                        valor = request.POST['valor']
                        if campo == 'inicio' or campo == 'fin':
                            valor = timezone.datetime.strptime(valor, '%d/%m/%Y').date()
                            setattr(contabilidad, campo, valor)
                            if contabilidad.inicio < contabilidad.fin:
                                contabilidad.save()
                            else:
                                return JsonResponse(
                                    {'ok': False, 'mensaje': "La fecha de inicio debe ser inferior a la de fin."})
                        else:
                            setattr(contabilidad, campo, valor)
                            contabilidad.save()
                        return JsonResponse({'ok': True, 'campo': campo, 'valor': request.POST['valor']})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la contabilidad."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la contabilidad."})
            elif request.POST['action'] == 'update_vivienda_contabilidad':
                try:
                    contabilidad = ContabilidadVUT.objects.get(id=request.POST['contabilidad'])
                    vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                    if vivienda in Vivienda.objects.filter(propietarios__in=[contabilidad.propietario]):
                        permiso = Permiso.objects.get(code_nombre='edita_contabilidad_vut')
                        a = AutorizadoContabilidadVut.objects.filter(contabilidad=contabilidad, autorizado=g_e.gauser,
                                                                     permisos__in=[permiso]).count()
                        if contabilidad.propietario == g_e.gauser or a > 0:
                            if request.POST['checked'] == 'true':
                                contabilidad.viviendas.add(vivienda)
                                html1 = ''
                                html2 = ''
                                for portal in vivienda.portales:
                                    try:
                                        PartidaVUT.objects.get(contabilidad=contabilidad, tipo='I_%s' % portal)
                                    except:
                                        p = PartidaVUT.objects.create(contabilidad=contabilidad, tipo='I_%s' % portal,
                                                                      nombre='Ingresos realizados por plataforma')
                                        html1 += render_to_string('contabilidad_vut_accordion_content_partida.html',
                                                                  {'partida': p})
                                        html2 += render_to_string('contabilidad_vut_accordion_content_asiento.html',
                                                                  {'partida': p})
                                html3 = render_to_string(
                                    "contabilidad_vut_accordion_content_asiento_option_vivienda.html", {'v': vivienda})
                                return JsonResponse({'ok': True, 'html1': html1, 'html2': html2, 'html3': html3})
                            else:
                                ps_v = vivienda.portales
                                contabilidad.viviendas.remove(vivienda)
                                portales_borrar = list(set(ps_v) - set(contabilidad.portales))
                                partidas_borrar = []
                                for portal_borrar in portales_borrar:
                                    p = PartidaVUT.objects.get(contabilidad=contabilidad, tipo='I_%s' % portal_borrar)
                                    partidas_borrar.append(p.id)
                                    p.delete()
                                return JsonResponse({'ok': True, 'partidas_borrar': partidas_borrar})
                        else:
                            return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la contabilidad."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la contabilidad."})
            elif request.POST['action'] == 'add_partida_vut':
                try:
                    contabilidad = ContabilidadVUT.objects.get(id=request.POST['contabilidad'])
                    permiso = Permiso.objects.get(code_nombre='crea_partida_vut')
                    a = AutorizadoContabilidadVut.objects.filter(contabilidad=contabilidad, autorizado=g_e.gauser,
                                                                 permisos__in=[permiso]).count()
                    if contabilidad.propietario == g_e.gauser or a > 0:
                        p = PartidaVUT.objects.create(nombre=request.POST['nombre'], tipo=request.POST['tipo'],
                                                      contabilidad=contabilidad)
                        html1 = render_to_string("contabilidad_vut_accordion_content_partida.html", {'partida': p})
                        html2 = render_to_string("contabilidad_vut_accordion_content_asiento.html", {'partida': p})
                        html3 = render_to_string("contabilidad_vut_accordion_content_asiento_option_partida.html",
                                                 {'p': p})
                        return JsonResponse({'ok': True, 'contabilidad': contabilidad.id, 'html1': html1,
                                             'html2': html2, 'html3': html3})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de crear la partida."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de crear la partida."})
            elif request.POST['action'] == 'borrar_partida':
                try:
                    partida = PartidaVUT.objects.get(id=request.POST['partida'])
                    permiso = Permiso.objects.get(code_nombre='borra_partida_vut')
                    a = AutorizadoContabilidadVut.objects.filter(contabilidad=partida.contabilidad,
                                                                 autorizado=g_e.gauser, permisos__in=[permiso]).count()
                    if partida.contabilidad.propietario == g_e.gauser or a > 0:
                        asientos = AsientoVUT.objects.filter(partida=partida)
                        for asiento in asientos:
                            os.remove(RUTA_BASE + asiento.fichero.url)
                            asiento.delete()
                        partida.delete()
                        return JsonResponse({'ok': True, 'mensaje': "La partida se ha borrado sin incidencias."})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar la partida."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar la partida."})
            elif request.POST['action'] == 'borrar_asiento':
                try:
                    asiento = AsientoVUT.objects.get(id=request.POST['asiento'])
                    permiso = Permiso.objects.get(code_nombre='borra_asiento_vut')
                    a = AutorizadoContabilidadVut.objects.filter(contabilidad=asiento.partida.contabilidad,
                                                                 autorizado=g_e.gauser, permisos__in=[permiso]).count()
                    if asiento.partida.contabilidad.propietario == g_e.gauser or a > 0:
                        if asiento.fichero:
                            os.remove(RUTA_BASE + asiento.fichero.url)
                        asiento.delete()
                        return JsonResponse({'ok': True, 'mensaje': "El asiento se ha borrado sin incidencias."})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar el asiento."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar el asiento."})
            elif request.POST['action'] == 'actualizar_asientos':
                try:
                    partida = PartidaVUT.objects.get(id=request.POST['partida'])
                    portal = partida.tipo.replace('I_', '')
                    permiso = Permiso.objects.get(code_nombre='edita_asiento_vut')
                    a = AutorizadoContabilidadVut.objects.filter(contabilidad=partida.contabilidad,
                                                                 autorizado=g_e.gauser, permisos__in=[permiso]).count()
                    if partida.contabilidad.propietario == g_e.gauser or a > 0:
                        MESES = ('', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
                                 'septiembre', 'octubre', 'noviembre', 'diciembre',)
                        inicio = partida.contabilidad.inicio
                        fin = partida.contabilidad.fin
                        strt_dt = datetime(inicio.year, inicio.month, 1).date()
                        end_dt = datetime(fin.year, fin.month, 1).date()
                        dates = [dt for dt in rrule(MONTHLY, dtstart=strt_dt, until=end_dt)]
                        dates[0] = inicio
                        dates[-1] = fin + timedelta(1)
                        for vivienda in partida.contabilidad.viviendas.all():
                            AsientoVUT.objects.filter(vivienda=vivienda, partida=partida).delete()
                            for d in range(len(dates) - 1):
                                total = Reserva.objects.filter(Q(entrada__gte=dates[d]), Q(entrada__lt=dates[d + 1]),
                                                               Q(vivienda=vivienda), Q(estado='ACE'),
                                                               Q(portal=portal)).aggregate(Sum('total'))['total__sum']
                                concepto = 'Ingresos del mes de %s' % MESES[dates[d].month]
                                if total:
                                    AsientoVUT.objects.create(partida=partida, vivienda=vivienda, concepto=concepto,
                                                              cantidad=total)
                        html = render_to_string("contabilidad_vut_accordion_content_asiento.html", {'partida': partida})
                        return JsonResponse(
                            {'ok': True, 'mensaje': "Asientos actualizados sin incidencias.", 'html': html})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al actualizar los asientos."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al actualizar los asientos."})
            elif request.POST['action'] == 'add_autorizado_contabilidad_vut':
                try:
                    contabilidad = ContabilidadVUT.objects.get(id=request.POST['contabilidad'])
                    permiso = Permiso.objects.get(code_nombre='add_autorizado_contabilidad_vut')
                    a = AutorizadoContabilidadVut.objects.filter(contabilidad=contabilidad,
                                                                 autorizado=g_e.gauser, permisos__in=[permiso]).count()
                    if contabilidad.propietario == g_e.gauser or a > 0:
                        gauser = Gauser.objects.get(id=request.POST['autorizado'])
                        autorizado = AutorizadoContabilidadVut.objects.create(contabilidad=contabilidad,
                                                                              autorizado=gauser)
                        html = render_to_string('contabilidad_vut_accordion_content_autorizado.html',
                                                {'autorizado': autorizado, 'contabilidad': contabilidad})
                        return JsonResponse({'ok': True, 'html': html, 'contabilidad': contabilidad.id})
                    else:
                        mensaje = "No tienes permiso para añadir personas autorizadas a la vivienda."
                        return JsonResponse({'ok': False, 'mensaje': mensaje})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error tratando de añadir un ayudante a la vivienda."})
            elif request.POST['action'] == 'delete_autorizado_contabilidad_vut':
                try:
                    autorizado = AutorizadoContabilidadVut.objects.get(id=request.POST['autorizado'])
                    contabilidad = autorizado.contabilidad
                    permiso = Permiso.objects.get(code_nombre='delete_autorizado_contabilidad_vut')
                    a = AutorizadoContabilidadVut.objects.filter(contabilidad=contabilidad,
                                                                 autorizado=g_e.gauser, permisos__in=[permiso]).count()
                    if contabilidad.propietario == g_e.gauser or a > 0:
                        autorizado.delete()
                        return JsonResponse({'ok': True, 'mensaje': "La persona autorizada ha sido borrada."})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "No tienes permisos para borrar autorizados."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar autorizado."})
            elif request.POST['action'] == 'edita_autorizado_contabilidad_vut':
                try:
                    autorizado = AutorizadoContabilidadVut.objects.get(id=request.POST['autorizado'])
                    autorizado.permisos.clear()
                    permisos = Permiso.objects.filter(code_nombre__in=request.POST.getlist('permisos[]'))
                    autorizado.permisos.add(*permisos)
                    return JsonResponse({'ok': True})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar autorizado."})
    else:
        if request.POST['action'] == 'add_asiento_vut':
            try:
                contabilidad = ContabilidadVUT.objects.get(id=request.POST['contabilidad'])
                permiso = Permiso.objects.get(code_nombre='crea_asiento_vut')
                a = AutorizadoContabilidadVut.objects.filter(contabilidad=contabilidad, autorizado=g_e.gauser,
                                                             permisos__in=[permiso]).count()
                if contabilidad.propietario == g_e.gauser or a > 0:
                    partida = PartidaVUT.objects.get(id=request.POST['partida'], contabilidad=contabilidad)
                    vivienda = contabilidad.viviendas.get(id=request.POST['vivienda'])
                    if 'file_asiento' in request.FILES:
                        fichero = request.FILES['file_asiento']
                        avut = AsientoVUT.objects.create(partida=partida, vivienda=vivienda,
                                                         concepto=request.POST['concepto'][:99],
                                                         cantidad=request.POST['cantidad'], fichero=fichero,
                                                         content_type=fichero.content_type)
                    else:
                        avut = AsientoVUT.objects.create(partida=partida, vivienda=vivienda,
                                                         concepto=request.POST['concepto'][:99],
                                                         cantidad=request.POST['cantidad'])

                    html = render_to_string("contabilidad_vut_accordion_content_asiento_tr.html", {'asiento': avut})
                    return JsonResponse({'ok': True, 'partida': partida.id, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de crear el asiento3."})
            except:
                return JsonResponse({'ok': False, 'mensaje': "Error al tratar de crear el asiento."})


# @permiso_required('acceso_domotica_vut')
def domotica_vut(request):
    g_e = request.session['gauser_extra']
    viviendas = viviendas_autorizado(g_e)

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'boton_domotico' and request.is_ajax():
            try:
                domotica = DomoticaVUT.objects.get(id=request.POST['domotica'])
                s = requests.Session()
                s.verify = False
                p = s.post(domotica.url, timeout=5)
                return JsonResponse({'ok': True, 'response': p.status_code})
            except:
                return JsonResponse({'ok': False})
        elif action == 'download_file_asiento':
            asiento = AsientoVUT.objects.get(id=request.POST['asiento'])
            permiso = Permiso.objects.get(code_nombre='edita_asiento_vut')
            a = AutorizadoContabilidadVut.objects.filter(contabilidad=asiento.partida.contabilidad,
                                                         autorizado=g_e.gauser, permisos__in=[permiso]).count()
            if asiento.partida.contabilidad.propietario == g_e.gauser or a > 0:
                fich = open(RUTA_BASE + asiento.fichero.url, 'rb')
                response = FileResponse(fich, content_type=asiento.content_type)
                response['Content-Disposition'] = 'attachment; filename=' + asiento.fich_name
                return response

    return render(request, "domotica_vut.html",
                  {
                      'formname': 'contabilidad_vut',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nueva contabilidad',
                            'permiso': 'crea_contabilidad_vut', 'title': 'Crear un nuevo registro de contabilidad'},
                           ),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'viviendas': viviendas,
                      'usuarios': usuarios_ronda(g_e.ronda)
                  })


@login_required()
def ajax_domotica_vut(request):
    g_e = request.session["gauser_extra"]
    if request.is_ajax():
        if request.POST['action'] == 'open_accordion':
            try:
                vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                if vivienda in viviendas_autorizado(g_e):
                    domoticas = DomoticaVUT.objects.filter(vivienda=vivienda)
                    html = render_to_string('domotica_vut_accordion_content.html', {'g_e': g_e, 'domoticas': domoticas,
                                                                                    'vivienda': vivienda})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'add_dispositivo_domotica':
            try:
                vivienda = Vivienda.objects.get(id=request.POST['vivienda'])
                if vivienda in viviendas_autorizado(g_e):
                    d = DomoticaVUT.objects.create(vivienda=vivienda, url='Aquí la url del dispositivo',
                                                   nombre='Nombre del dispositivo', texto='Descripción',
                                                   propietario=g_e.gauser)
                    html = render_to_string('domotica_vut_accordion_content_dispositivo.html',
                                            {'g_e': g_e, 'domotica': d})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'delete_dispositivo_domotica':
            try:
                d = DomoticaVUT.objects.get(id=request.POST['domotica'])
                if d.vivienda in viviendas_autorizado(g_e) and g_e.has_permiso('delete_dispositivo_domotica'):
                    d.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_campo':
            try:
                domotica = DomoticaVUT.objects.get(id=request.POST['domotica'])
                if g_e.has_permiso('edita_dispositivo_domotica'):
                    campo = request.POST['campo']
                    valor = request.POST['valor']
                    setattr(domotica, campo, valor)
                    domotica.save()
                    return JsonResponse({'ok': True, 'campo': campo, 'valor': valor})
                else:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
            except:
                return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
        elif request.POST['action'] == 'update_tipo_dispositivo':
            try:
                domotica = DomoticaVUT.objects.get(id=request.POST['domotica'])
                if g_e.has_permiso('edita_dispositivo_domotica'):
                    domotica.tipo = request.POST['valor']
                    domotica.save()
                    html = render_to_string('dispositivo_domotico.html', {'domotica': domotica})
                    return JsonResponse({'ok': True, 'campo': 'tipo', 'valor': request.POST['valor'], 'html': html})
                else:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
            except:
                return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})


################################################################################
################################################################################
################################################################################
################################################################################

# Como entrar en una página con usuario y contraseña para después submit un form
# https://stackoverflow.com/questions/12399087/curl-to-access-a-page-that-requires-a-login-from-a-different-page


# https://unix.stackexchange.com/questions/138669/login-site-using-curl
# curl -s https://gaumentada.es -c cookiefle -d "usuario=jjmartinr01&passusuario=contraseña"

# def actualiza_registro_policia(viajero):
#     reserva = viajero.reserva
#     vivienda = reserva.vivienda
#     hoy = datetime.today().date()
#     registro, c = RegistroPolicia.objects.get_or_create(creado__year=hoy.year, creado__month=hoy.month,
#                                                         creado__day=hoy.day, vivienda=vivienda)
#     registro.viajeros.add(viajero)
#     genera_parte_policia(registro)
#     return registro
#
#
# def genera_parte_policia(registro):
#     vivienda = registro.vivienda
#     # Borramos el posible fichero existente:
#     ruta = os.path.join("%svut/%s/%s/partes/" % (RUTA_MEDIA, vivienda.propietario.id, vivienda.id),
#                         "%s.%s" % (vivienda.codigo_entidad_emisora, registro.ext))
#     if os.path.isfile(ruta):
#         os.remove(ruta)
#     # Fin de las instrucciones para borrar el posible archivo
#     fich_name = 'parte_temporal%s.txt' % (vivienda.propietario.id)
#     ruta = os.path.join("%svut/" % (RUTA_MEDIA), fich_name)
#     f = open(ruta, "w+")
#     contenido = render_to_string('fichero_registro_policia.txt', {'v': vivienda, 'vs': registro.viajeros.all()})
#     f.write(contenido.encode('utf-8'))
#     registro.parte = File(f)
#     registro.save()
#     f.close()
#     return registro.parte
#
#
# def enviarFicheroGuardiaCivil():
#     f = open('', 'r')
#     url = 'https://28000AAA00:73257125D@hospederias.guardiacivil.es/hospederias/servlet/ControlRecepcionFichero'
#     r = requests.post(url, files={'fichero': f}, data={}, verify=False)


# def comprueba_registros(vivienda):
#     """
#     Esta función se encarga de entrar en el registro de la policía
#     para ir a SEGUIMIENTO y obtener los últimos registros realizados.
#     El objetivo es leer dichos registros para actualizar la información
#     sobre viajeros registrados.
#     """
#     hoy = datetime.today().date()
#     antesdeayer = hoy - timedelta(2)
#     options = Options()
#     # options.add_argument("--headless")
#     # display = Display(visible=0, size=(800, 600))
#     # display.start()
#
#     profile = webdriver.FirefoxProfile()
#     profile.accept_untrusted_certs = True
#     driver = webdriver.Firefox(firefox_profile=profile, firefox_options=options,
#                                log_path='%sgeckodriver.log' % MEDIA_VUT)
#     driver.delete_all_cookies()
#     wait = WebDriverWait(driver, 10)
#     driver.get("https://webpol.policia.es/e-hotel/login")
#     driver.find_element_by_name("username").send_keys(vivienda.police_code)
#     driver.find_element_by_name("password").send_keys(vivienda.police_pass)
#     driver.find_element_by_id('loginButton').click()
#     dropdown_seguimiento = driver.find_element_by_class_name('fa-caret-down')
#     # El elemnto padre al anterior debe contener el texto SEGUIMIENTO. Lo comprobamos:
#     parent = dropdown_seguimiento.find_element_by_xpath('.. ')
#     if 'SEGUIMIENTO' in parent.text:
#         dropdown_seguimiento.click()
#         sleep(0.5)
#         # Se despliega el dropdown y pulsamos en 'segAgrHuespedes'
#         driver.find_element_by_id('segAgrHuespedes').click()
#         f = driver.find_element_by_id('fechaDesde')
#         f.send_keys(antesdeayer.strftime('%d/%m/%Y'))
#         botonera = driver.find_element_by_class_name('contenido-body')
#         botones = botonera.find_elements_by_xpath('//button')
#         for b in botones:
#             if 'Buscar' in b.text:
#                 buscar = b
#                 buscar.click()


def registra_viajero_policia(viajero):
    hoy = datetime.today().date()
    ayer = hoy - timedelta(1)

    # options = webdriver.ChromeOptions()
    # options.add_argument('--ignore-certificate-errors')
    # driver = webdriver.Chrome(chrome_options=options)

    options = Options()
    # options.add_argument("--headless")
    # display = Display(visible=0, size=(800, 600))
    # display.start()

    profile = webdriver.FirefoxProfile()
    profile.accept_untrusted_certs = True
    driver = webdriver.Firefox(firefox_profile=profile, firefox_options=options,
                               log_path='%sgeckodriver.log' % MEDIA_VUT)
    driver.delete_all_cookies()
    wait = WebDriverWait(driver, 10)
    driver.get("https://webpol.policia.es/e-hotel/login")
    driver.find_element_by_name("username").send_keys(viajero.reserva.vivienda.police_code)
    driver.find_element_by_name("password").send_keys(viajero.reserva.vivienda.police_pass)
    driver.find_element_by_id('loginButton').click()
    driver.find_element_by_id('grabadorManual').click()
    # wait.until(EC.presence_of_element_located((By.ID, 'nombre')))
    wait.until(lambda gdriver: driver.execute_script("return jQuery.active == 0"))
    driver.execute_script("$('#nombre').val('%s')" % viajero.nombre)
    driver.execute_script("$('#apellido1').val('%s')" % viajero.apellido1)
    driver.execute_script("$('#apellido2').val('%s')" % viajero.apellido2)
    driver.execute_script("$('#nacionalidad').val('%s')" % viajero.pais)
    driver.execute_script("$('#nacionalidad').trigger('chosen:updated').change()")
    # Al actualizar la nacionalidad se hace una petición ajax para actualizar el 'tipoDocumento'
    # http://www.mahsumakbas.net/selenium-webdrvier-wait-jquery-ajax-request-complete-in-python/
    # Esperaremos a que esta petición finalice:
    wait.until(lambda gdriver: driver.execute_script("return jQuery.active == 0"))
    driver.execute_script("$('#tipoDocumento').val('%s')" % viajero.tipo_ndi)
    driver.execute_script("$('#tipoDocumento').trigger('chosen:updated').change()")
    driver.execute_script("$('#numIdentificacion').val('%s')" % viajero.ndi)
    driver.execute_script(
        "$('#fechaExpedicionDoc').datepicker('update', '%s')" % viajero.fecha_exp.strftime('%d/%m/%Y'))
    driver.execute_script("$('#dia').val('%s')" % viajero.nacimiento.day)
    driver.execute_script("$('#mes').val('%s')" % viajero.nacimiento.month)
    driver.execute_script("$('#ano').val('%s')" % viajero.nacimiento.year)
    driver.execute_script("$('#sexo').val('%s')" % viajero.sexo)
    driver.execute_script("$('#sexo').trigger('chosen:updated').change()")
    if viajero.reserva.entrada == hoy or viajero.reserva.entrada == ayer:
        fechaEntrada = viajero.reserva.entrada.strftime('%d/%m/%Y')
    else:
        fechaEntrada = hoy.strftime('%d/%m/%Y')
    driver.execute_script("$('#fechaEntrada').datepicker('update', '%s')" % fechaEntrada)

    # #----------------------------------------------------------------#
    # # -----Esta parte debería utilizarse si no funcionara 'wait'-----#
    # # ---------------------------------------------------------------#
    # # Queda por rellenar el tipo de documento. Al cambiar la nacionalidad se borran tanto
    # # el tipo de documento como el número de documento
    # intentos = 10
    # n = 0
    # while n < intentos:
    #     n += 1
    #     sleep(0.5)
    #     tipo_documento = driver.find_element_by_id('tipoDocumento').get_attribute('value')
    #     if tipo_documento == viajero.tipo_ndi:
    #         n = 11
    #     else:
    #         driver.execute_script("$('#tipoDocumento').val('%s')" % viajero.tipo_ndi)
    #         driver.execute_script("$('#tipoDocumento').trigger('chosen:updated').change()")
    # if driver.find_element_by_id('tipoDocumento').get_attribute('value') == viajero.tipo_ndi:
    #     driver.find_element_by_id('numIdentificacion').send_keys(viajero.ndi)
    # else:
    #     viajero.observaciones += '<p>Registro cancelado. No se puede establecer el tipo de ndi</p>'
    #     viajero.save()
    #     return False
    # # ----------------------------------------------------------------#

    # Si la grabación de datos ha ido bien el siguiente paso es pulsar en 'btnGuardar':
    sleep(2)
    guardar = wait.until(EC.presence_of_element_located((By.ID, 'btnGuardar')))
    guardar.click()
    # sleep(5)
    # driver.close()
    # return False
    sleep(2)
    # Si esta acción funciona correctamente se mostrará un reval modal
    wait.until(lambda gdriver: driver.execute_script("return jQuery.active == 0"))
    try:
        modal = wait.until(EC.presence_of_element_located((By.ID, 'modal-parteHuesped')))
        # modal = driver.find_element_by_id('modal-parteHuesped')
        # Si existe el modal es porque se ha registrado correctamente el viajero
        # El siguiente paso sería buscar el botón de cancelar (la 'x' superior derecha)
        x = modal.find_element_by_xpath('//button')  # Botón 'x' para Cancelar
        x.click()  # Pulsamos para eliminar el modal
        # A continuación esperamos a que se recargue la página y salimos:
        wait.until(lambda gdriver: driver.execute_script("return jQuery.active == 0"))
        salir = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'fa-sign-out')))
        driver.find_element_by_class_name("fa-sign-out").click()
        salir.click()
        sleep(5)
        driver.close()
        return True
    except:
        # Si se produce una excepción aparecerá un mensaje genérico indicando los errores:
        try:
            e = driver.find_element_by_id('divMensajeGenerico')
            viajero.observaciones = e.text
            viajero.save()
            driver.find_element_by_class_name("fa-sign-out").click()
            driver.close()
            return False
        except:
            error = wait.until(EC.presence_of_element_located((By.ID, 'contenedor-error')))
            viajero.observaciones = error.text
            viajero.save()
            driver.find_element_by_class_name("fa-sign-out").click()
            driver.close()
            return False


#
# def registra_viajero(viajero):
#     if type(viajero) is not Viajero:
#         return False
#     vivienda = viajero.reserva.vivienda
#     print ("entra al registro PN. Viajero: %s" % viajero)
#     # Iniciamos una sesión
#     s = requests.Session()
#     s.verify = False  # Para que los certificados ssl no sean verificados. Comunicación https confiada
#     # Accedemos a la página de inicio y de la respuesta capturamos el token csrf
#     p1 = s.get('https://webpol.policia.es/e-hotel/')
#     # Escribimos las cookies en una cadena de texto, para introducirlas en las distintas cabeceras
#     cookies_header = ''
#     for c in dict(s.cookies):
#         print c, dict(s.cookies)[c]
#         cookies_header += '%s=%s;' % (c, dict(s.cookies)[c])
#     # Debemos salvar el token csrf de la sesión, que utilizaremos en los diferentes enlaces
#     soup1 = BeautifulSoup(p1.content.decode(p1.encoding), 'html.parser')
#     csrf_token = soup1.find('input', {'name': '_csrf'})['value']
#     # El siguiente paso que da el sistema es la obtención de etiquetas de su sistema "ARGOS"
#     obtener_etiquetas_url = 'https://webpol.policia.es/e-hotel/obtenerEtiquetas'
#     obtener_etiquetas_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
#                                  'Accept-Encoding': 'gzip, deflate, br',
#                                  'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                  'Ajax-Referer': '/e-hotel/obtenerEtiquetas', 'Connection': 'keep-alive',
#                                  'Content-Length': '0',
#                                  'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                  'Cookie': cookies_header,
#                                  'Host': 'webpol.policia.es', 'Referer': 'https://webpol.policia.es/e-hotel/',
#                                  'User-Agent': 'python-requests/2.11.1',
#                                  'X-CSRF-TOKEN': csrf_token,
#                                  'X-Requested-With': 'XMLHttpRequest'}
#     p11 = s.post(obtener_etiquetas_url, headers=obtener_etiquetas_headers, cookies=dict(s.cookies))
#     # Cargamos los valores de los inputs demandados para hacer el login y enviamos el post con el payload
#     # En este caso enviamos: headers, cookies y parámetros (payload)
#     payload = {'username': vivienda.police_code, '_csrf': csrf_token, 'password': vivienda.police_pass}
#     execute_login_headers = {'Accept': 'text/html,  application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8',
#                              'Accept-Encoding': 'gzip, deflate, br',
#                              'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                              'Connection': 'keep-alive',
#                              'Content-Type': 'application/x-www-form-urlencoded',
#                              'Cookie': cookies_header,
#                              'Host': 'webpol.policia.es', 'Referer': 'https://webpol.policia.es/e-hotel/',
#                              'Upgrade-Insecure-Requests': '1', 'User-Agent': 'python-requests/2.11.1'}
#     print(dict(s.cookies))
#     p2 = s.post('https://webpol.policia.es/e-hotel/execute_login', data=payload, headers=execute_login_headers,
#                 cookies=dict(s.cookies))
#     # A continuación hacemos una petición GET a inicio sin ningún parámetro
#     execute_inicio_headers = {'Accept': 'text/html,  application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8',
#                               'Accept-Encoding': 'gzip, deflate, br',
#                               'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                               'Connection': 'keep-alive', 'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                               'Referer': 'https://webpol.policia.es/e-hotel/', 'Upgrade-Insecure-Requests': '1',
#                               'User-Agent': 'python-requests/2.11.1'}
#     p21 = s.get('https://webpol.policia.es/e-hotel/inicio', headers=execute_inicio_headers, cookies=dict(s.cookies))
#     # Hacemos una comprabción para asegurarnos de que se ha accedido correctamente a la webpol.
#     # Si la respuesta es correcta la respuesta contendrá el usuario:
#     if vivienda.police_code in p21.content.decode(p2.encoding):
#         # El siguiente paso es obtener etiquetas. Esta es una solicitud POST sin payload
#         obtener_etiquetas_url = 'https://webpol.policia.es/e-hotel/obtenerEtiquetas'
#         obtener_etiquetas_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
#                                      'Accept-Encoding': 'gzip, deflate, br',
#                                      'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                      'Ajax-Referer': '/e-hotel/obtenerEtiquetas', 'Connection': 'keep-alive',
#                                      'Content-Length': '0',
#                                      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                      'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                                      'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                      'User-Agent': 'python-requests/2.11.1',
#                                      'X-CSRF-TOKEN': '92a4cc08-b50b-4be3-8a98-8adf8bb1db2e',
#                                      'X-Requested-With': 'XMLHttpRequest'}
#         p22 = s.post(obtener_etiquetas_url, headers=obtener_etiquetas_headers, cookies=dict(s.cookies))
#         # A continuación debemos ir a la grabación manual. Antes se hace una llamada para limpiar la sesión
#         limpiar_sesion_temporal_url = 'https://webpol.policia.es/e-hotel/limpiarSesionTemporal'
#         limpiar_sesion_temporal_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
#                                            'Accept-Encoding': 'gzip, deflate, br',
#                                            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                            'Ajax-Referer': '/e-hotel/limpiarSesionTemporal',
#                                            'Connection': 'keep-alive', 'Content-Length': '0',
#                                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                            'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                                            'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                            'User-Agent': 'python-requests/2.11.1',
#                                            'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
#         p23 = s.post(limpiar_sesion_temporal_url, headers=limpiar_sesion_temporal_headers, cookies=dict(s.cookies))
#         # Ahora es cuando se hace otra petición POST para llegar a la grabación manual sin payload
#         print("5")
#         grabador_manual_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/vista/grabadorManual'
#         grabador_manual_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
#                                    'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                    'Ajax-Referer': '/e-hotel/hospederia/manual/vista/grabadorManual',
#                                    'Connection': 'keep-alive',
#                                    'Content-Length': '0',
#                                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                    'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                                    'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                    'User-Agent': 'python-requests/2.11.1',
#                                    'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
#         p3 = s.post(grabador_manual_url, headers=grabador_manual_headers, cookies=dict(s.cookies))
#         # En esta petición nos han devuelto el id de la hospedería. Lo tenemos que guardar:
#         soup3 = BeautifulSoup(p3.content.decode(p3.encoding), 'html.parser')
#         idHospederia = soup3.find('input', {'id': 'idHospederia'})['value']
#         print(idHospederia)
#         # Pasamos a rellenar el parte del viajero. Necesitamos algunos campos como sexoStr o tipoDocumentoStr.
#         # En el caso de sexoStr debemos asignar el texto MASCULINO o FEMENINO, que es diferente de
#         # get_sexo_display() y por eso definimos el siguiente diccionario.
#         sexo = {'M': 'MASCULINO', 'F': 'FEMENINO'}
#         data_viajero = {'nombre': viajero.nombre, 'apellido1': viajero.apellido1,
#                         'apellido2': viajero.apellido2, 'nacionalidad': viajero.pais,
#                         'tipoDocumento': viajero.tipo_ndi, 'numIdentificacion': viajero.ndi,
#                         'fechaExpedicionDoc': viajero.fecha_exp.strftime('%d/%m/%Y'),
#                         'dia': '%s' % viajero.nacimiento.day, 'mes': '%s' % viajero.nacimiento.month,
#                         'ano': '%s' % viajero.nacimiento.year, 'idHospederia': idHospederia,
#                         'fechaEntrada': viajero.fecha_entrada.strftime('%d/%m/%Y'), 'sexo': viajero.sexo,
#                         'fechaNacimiento': viajero.nacimiento.strftime('%d/%m/%Y'), '_csrf': csrf_token,
#                         'jsonHiddenComunes': '', 'nacionalidadStr': viajero.get_pais_display().encode('utf-8'),
#                         'sexoStr': sexo[viajero.sexo], 'tipoDocumentoStr': viajero.get_tipo_ndi_display()}
#         huesped_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/insertar/huesped'
#         huesped_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
#                            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                            'Ajax-Referer': '/e-hotel/hospederia/manual/insertar/huesped',
#                            'Connection': 'keep-alive',
#                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                            'Cookie': cookies_header,
#                            'Host': 'webpol.policia.es', 'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                            'User-Agent': 'python-requests/2.11.1',
#                            'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
#         p4 = s.post(huesped_url, data=data_viajero, headers=huesped_headers, cookies=dict(s.cookies))
#         # En esta petición nos devuelven datos que no vamos a necesitar, pero que almacenamos para guarar en
#         # la información del registro.
#         soup4 = BeautifulSoup(p4.content.decode(p4.encoding), 'html.parser')
#         huespedJson = soup4.find('input', {'name': 'huespedJson'})['value']
#         idHuesped = soup4.find('input', {'name': 'idHuesped'})['value']
#         # Para completar la grabación es necesario llamar a parteViajero a través de una petición GET:
#         parte_viajero_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/vista/parteViajero'
#         parte_viajero_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
#                                  'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                  'Ajax-Referer': '/e-hotel/hospederia/manual/insertar/huesped',
#                                  'Connection': 'keep-alive',
#                                  'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                  'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                                  'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                  'User-Agent': 'python-requests/2.11.1',
#                                  'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
#         p5 = s.get(parte_viajero_url, headers=parte_viajero_headers, cookies=dict(s.cookies))
#         # En siguiente paso dado a través de un navegador es llamar a tipoDocumentoNacionalidad con una
#         # petición POST enviando como parámetro la "nacionalidad":
#         nacionalidad_url = 'https://webpol.policia.es/e-hotel/combo/tipoDocumentoNacionalidad'
#         nacionalidad_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
#                                 'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                 'Ajax-Referer': '/e-hotel/combo/tipoDocumentoNacionalidad',
#                                 'Connection': 'keep-alive',
#                                 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                 'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                                 'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                 'User-Agent': 'python-requests/2.11.1',
#                                 'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
#         payload = {'nacionalidad': viajero.pais}
#         p6 = s.post(nacionalidad_url, headers=nacionalidad_headers, cookies=dict(s.cookies), data=payload)
#         # En este punto termina el proceso de grabación
#         if p6.status_code == 200:
#             print(u'Todo correcto')
#             s.close()
#             viajero.fichero_policia = True
#             viajero.save()
#             return p4
#         else:
#             print('Error durante el grabado del viajero. Hacer el registro manualmente.')
#             s.close()
#             return p4
#     else:
#         print(u'Error al hacer el login en webpol para el viajero: %s' % (viajero))
#         s.close()
#

#
# def registro_automatico():
#     from selenium import webdriver
#     from selenium.webdriver.common.keys import Keys
#     import time
#
#     driver = webdriver.Firefox()
#     driver.get("https://webpol.policia.es/e-hotel/login")
#     elem = driver.find_element_by_name("username")
#     elem.send_keys('H26441AAV5B')
#     elem = driver.find_element_by_name("password")
#     elem.send_keys('Villeman2018')
#     driver.find_element_by_id('loginButton').click()
#     driver.find_element_by_id('envioFicherosPrueba').click()
#     driver.find_element_by_id('fichero').send_keys('/home/juanjo/Descargas/borrar/26441AAV4L.001')
#
#     # elem.clear()
#     # elem.send_keys("pycon")
#     # elem.send_keys(Keys.RETURN)
#     # assert "No results found." not in driver.page_source
#     # driver.close()
#
#     # headless browsers
#     # http://allselenium.info/selenium-headless-mode-tests-chrome-firefox/
#
#
# def registro_automatico2():
#     from selenium import webdriver
#     from selenium.webdriver.common.keys import Keys
#     from selenium.webdriver.firefox.options import Options
#     from selenium.webdriver.support.ui import Select
#     from .models import Viajero, Vivienda
#     vivienda = Vivienda.objects.get(id=1)
#     viajero = Viajero.objects.get(id=14)
#     options = Options()
#     # options.add_argument("--headless")
#     # display = Display(visible=0, size=(800, 600))
#     # display.start()
#     driver = webdriver.Firefox(firefox_options=options, log_path='%sgeckodriver.log' % MEDIA_VUT)
#     driver.get("https://webpol.policia.es/e-hotel/login")
#     driver.find_element_by_name("username").send_keys(vivienda.police_code)
#     driver.find_element_by_name("password").send_keys(vivienda.police_pass)
#     driver.find_element_by_id('loginButton').click()
#     driver.find_element_by_id('grabadorManual').click()
#
#     # driver.find_element_by_id("nombre").send_keys(viajero.nombre)
#     sleep(0.5)
#     driver.execute_script("$('#nombre').val('%s')" % viajero.nombre)
#     sleep(0.5)
#     driver.execute_script("$('#apellido1').val('%s')" % viajero.apellido1)
#     sleep(0.5)
#     driver.execute_script("$('#apellido2').val('%s')" % viajero.apellido2)
#     sleep(0.5)
#     driver.execute_script("$('#nacionalidad').val('%s')" % viajero.pais)
#     sleep(0.5)
#     driver.execute_script("$('#nacionalidad').trigger('chosen:updated')")
#     sleep(0.5)
#     driver.execute_script("$('#tipoDocumento').val('%s')" % viajero.tipo_ndi)
#     sleep(0.5)
#     driver.execute_script("$('#numIdentificacion').val('%s')" % viajero.ndi)
#     sleep(0.5)
#     driver.execute_script("$('#fechaExpedicionDoc').val('%s')" % viajero.fecha_exp.strftime('%d/%m/%Y'))
#     sleep(0.5)
#     driver.execute_script("$('#dia').val('%s')" % viajero.nacimiento.day)
#     sleep(0.5)
#     driver.execute_script("$('#mes').val('%s')" % viajero.nacimiento.month)
#     sleep(0.5)
#     driver.execute_script("$('#ano').val('%s')" % viajero.nacimiento.year)
#     sleep(0.5)
#     driver.execute_script("$('#sexo').val('%s')" % viajero.sexo)
#     sleep(0.5)
#     driver.execute_script("$('#fechaEntrada').val('%s')" % datetime.today().date().strftime('%d/%m/%Y'))
#     sleep(3.5)
#     for b in driver.find_element_by_class_name('fa-sign-out'):
#         b.click()
#     sleep(3.5)
#
#
# def conexion():
#     data_viajero = {'nombre': 'JUAN JOSE', 'apellido1': 'MARTIN', 'apellido2': 'ROMERO', 'nacionalidad': 'A9109AAAAA',
#                     'tipoDocumento': 'D', 'numIdentificacion': '73257125D', 'fechaExpedicionDoc': '21/07/2015',
#                     'dia': '07',
#                     'mes': '05', 'ano': '1972', 'sexo': 'M', 'fechaEntrada': '23/10/2018', 'idHospederia': '32609',
#                     'fechaNacimiento': '07/05/1972'}
#
#     url_inicio = 'https://webpol.policia.es/e-hotel/'
#     url_login = 'https://webpol.policia.es/e-hotel/execute_login'
#     url_manual = 'https://webpol.policia.es/e-hotel/hospederia/manual/vista/grabadorManual'
#     url_grabar = 'https://webpol.policia.es/e-hotel/hospederia/manual/insertar/huesped'
#     url_otra = 'https://webpol.policia.es/e-hotel/hospederia/manual/vista/grabadorManual'
#
#     payload = {'username': 'H26441AAV5B', '_csrf': '', 'password': 'Villeman2018'}
#
#     s = requests.Session()
#     p1 = s.get(url_inicio, verify=False)
#     csrf_token = p1.content.split('_csrf" content="')[1].split('"/>')[0]
#     payload['_csrf'] = csrf_token
#     p2 = s.post(url_login, data=payload, verify=False)
#     p3 = s.get(url_manual, verify=False)
#     data_viajero['_csrf'] = csrf_token
#     p4 = s.post(url_grabar, data=data_viajero, verify=False)
#     s.close()
#
#
# def registra_en_policia(viajero):
#     vivienda = viajero.reserva.vivienda
#     if vivienda.police == 'GC':
#         logger.info("4")
#         url = 'https://%s:%s@hospederias.guardiacivil.es/hospederias/servlet/ControlRecepcionFichero' % (
#             vivienda.police_code, vivienda.police_pass)
#         r = requests.post(url, files={'fichero': fichero}, data={}, verify=False)
#         if r.status_code == 200:
#             if 'Errores' in r.text:
#                 gauser_autorizados = Autorizado.objects.filter(vivienda=vivienda).values_list('gauser__id',
#                                                                                               flat=True)
#                 receptores = Gauser.objects.filter(
#                     Q(id__in=gauser_autorizados) | Q(id=vivienda.propietario.gauser.id))
#                 mensaje = '<p>En el registro de %s, reserva %s</p><p>La Guardia Civil dice:</p>%s' % (
#                     viajero.nombre_completo, viajero.reserva, r.text.replace('\r\n', '<br>'))
#                 encolar_mensaje(emisor=vivienda.propietario, receptores=receptores,
#                                 asunto='Error en comunicación a la Guardia Civil', html=mensaje,
#                                 etiqueta='guardia_civl%s' % vivienda.id)
#             else:
#                 viajero.fichero_policia = True
#                 mensaje = '<p>En el registro de %s, reserva %s</p><p>La Guardia Civil dice:</p>%s' % (
#                     viajero.nombre_completo, viajero.reserva, r.text.replace('\r\n', '<br>'))
#                 encolar_mensaje(emisor=vivienda.propietario, receptores=[vivienda.propietario.gauser],
#                                 asunto='Comunicación a la Guardia Civil', html=mensaje,
#                                 etiqueta='guardia_civl%s' % vivienda.id)
#                 viajero.save()
#                 fichero.close()
#                 return True
#         else:
#             gauser_autorizados = Autorizado.objects.filter(vivienda=vivienda).values_list('gauser__id', flat=True)
#             receptores = Gauser.objects.filter(id__in=gauser_autorizados)
#             mensaje = '<p>No se ha podido establecer comunicación con la Guardia Civil.</p>'
#             encolar_mensaje(emisor=vivienda.propietario, receptores=receptores,
#                             asunto='Error en comunicación a la Guardia Civil', html=mensaje,
#                             etiqueta='guardia_civl%s' % vivienda.id)
#             fichero.close()
#             return False
#     elif vivienda.police == 'PN':
#         logger.info("entra al registro PN. Viajero: %s" % viajero)
#         # Iniciamos una sesión
#         s = requests.Session()
#         s.verify = False  # Para que los certificados ssl no sean verificados. Comunicación https confiada
#         # Accedemos a la página de inicio y de la respuesta capturamos el token csrf
#         p1 = s.get('https://webpol.policia.es/e-hotel/')
#         print p1.encoding
#         csrf_token = p1.content.decode(p1.encoding).split('_csrf" content="')[1].split('"/>')[0]
#         # Cargamos los valores de los inputs demandados para hacer el login y enviamos el post con el payload
#         payload = {'username': vivienda.police_code, '_csrf': csrf_token, 'password': vivienda.police_pass}
#         p2 = s.post('https://webpol.policia.es/e-hotel/execute_login', data=payload)
#         print "p2 %s" % p2.encoding
#         # Si la respuesta es correcta la respuesta contendrá el usuario:
#         if vivienda.police_code in p2.content.decode(p2.encoding):
#             logger.info("5")
#             # Pasamos a la página de introducción de datos manual
#             p3 = s.get('https://webpol.policia.es/e-hotel/hospederia/manual/vista/grabadorManual')
#             print "p3 %s" % p3.encoding
#             idHospederia = p3.content.decode(p3.encoding).split('idHospederia" type="hidden" value="')[1].split('"/>')[
#                 0]
#             data_viajero = {'nombre': viajero.nombre.upper(), 'apellido1': viajero.apellido1.upper(),
#                             'apellido2': viajero.apellido2.upper(), 'nacionalidad': viajero.pais,
#                             'tipoDocumento': viajero.tipo_ndi, 'numIdentificacion': viajero.ndi.upper(),
#                             'fechaExpedicionDoc': viajero.fecha_exp.strftime('%d/%m/%Y'),
#                             'dia': viajero.nacimiento.day, 'mes': viajero.nacimiento.month,
#                             'ano': viajero.nacimiento.year, 'sexo': viajero.sexo, 'idHospederia': idHospederia,
#                             'fechaEntrada': viajero.reserva.entrada.strftime('%d/%m/%Y'),
#                             'fechaNacimiento': viajero.nacimiento.strftime('%d/%m/%Y'), '_csrf': csrf_token}
#             p4 = s.post('https://webpol.policia.es/e-hotel/hospederia/manual/insertar/huesped', data=data_viajero)
#             s.close()
#         else:
#             logger.info(u'Error al registrar al viajero %s' % (viajero))
#             s.close()
#     else:
#         return False


# Ejemplo de convertir base64 descargado de la policía en pdf

# import base64
#
# img_data = b'JVBERi0xLjQKJeLjz9MKNCAwIG9iago8PC9GaWx0ZXIvRmxhdGVEZWNvZGUvTGVuZ3RoIDE1NDM+PnN0cmVhbQp4nK1Z3XLaOBS+5ynOJZ2hjiXbGGdmL9hAsmQgZDHpdGazk1FthapjW6wMadJH23fYiz5CH6AXnd71ao8UIEDAZGI7M7YsLH1H5/eT8k/t93HNaYLnBTCOa91x7c8ahXPdS8DGP333Ag/Gae3olACxYXxbq78Zf9LfPn1iQ5SuDyIBtXwKXtPTDzOYLgbb5hM1qdXbF933Qz2VDZMd0/31Nz5jI87WL49TjM5qtuXqCz7XHM+zKAJ6jhUQSGuuTZYvSS3EEWc4yed1EVcjXMvzlyK2NiUcs5T9kNB+671GzHV9EN8KfPCcoEAfAxnzRELMYcrUjOsGz2aKxUw37wT7xJXMy0ri+8YytFkgyR/yE3s74hORz5QsC9h0LIIeRhyLOks/2tLzdX3Ek4RnTEEkM0jZw688micsv35T0j88vJpoeOK2rBYFN8BHC/2D+tQiwfJ9j4usBhVZrcNmMkcDJcDzGfuQ8EikAu1WVm/UBtdvrYDJM+CL3ulxWQy/dQDk0nhi9m9pJFzNWjLYsRqZflDc6LG7qccqoD1aAD2YZyISU1EJ0lqE79CmknciiwQri0TQfR30TIJRvC+oQgwpuUuhJbEx3xb7DGnZjkscEpYEcpxDIUBKq/GQW172wmEI46vRf+G4d4LNd71+v3vWDqFXEttvHnDL/vBsNPw6BEyOveF5+3WpcAuw0Dv7bTBI5aPACRzLdvdmzPYYFdnp9lGZ7fPu6FUcYAuwOFP+Si3oyGieavfXxVTE2BIxiysIeafQgcZiahDjJfzxdZ2UtqWGLXSeUx59ZMDvpzzG3PYzM3ngSYYK4A8kOpFyBWyKOUjEleAhfzhUPaqAse0CmJDfa/vRKuxHW/5B+6HfZGxVB6/rTiXAvltY8L/nS1yZscQEyXXdrQS5SV6y5AXpRVSvNCrxHcvxgTr+iuU/K5Q3W1cDbm60HJu9uofaNzdl1eBgyW4CpXT/tuNUqJSZiH33SPrLq560Wpa7YgrNDTwbtyZN3CiNP2PfOMJCwEDxSE7Q9vAAaIwZe3RByDl8ZOqb1gWL5lzF0hD2hEGfP8BQTb4hlWJAvCMSBEFDf0ccfe9gFuI6Rk0f8qAZjxZ5CZYMGk5w6mjG1XK59kqkjZUQyzUb0rUF+C6l3tMCLrnKtfOi9HhjKe6nTBLWfEjk0zkydYluBqhh5LffcashgXoWMd9srcU9ojbxjNjIR/A+YOqLbEAuNV/dXAmODflkrnTQFC8CY9BtFi/iRMxxGpYx6/lUr42GoHWgVPoO9XxCvU7ZuNNIhYWxEoTCGkjJke0b61UBVVh/zq/aF3A+DLtVIBWWoEE7PLnq9y7KkiaNVFyCUHe2jmOfVgFVWHS64WX7a1neaWAKK4yNDmHCOaiAKKwdoOwiCpN5hsmxKgJk/KKQcQ3ao3HvogqYwoWNhoNKCDvxbMtdnals1qN6L8tnah5pAsJNYcAac7vKsgmIdKp4Lq0KxEBeENDdZbFuiDomdGBxKmY8K2tErFqE+nvLcP0tXDKFpD2fsh8y4fkxdC56DZiynE2lPoaRMOUqFblc6CSeR0JVoAU/2C+UYbtwCr9h7b+XcMtxAyEyrH8PMFh2pkyf1mFvBbI0CxRkCDB0Td2+lciRsIq38RoMOp2GrvQoGzIJJCm4z5kmQu91NFvRZf6H3GTTFnT19zmuQ++MvjOs6EIPjXmOqpURzxog1LcMFZ1WQMA8t2hdSK9h7QTskolnJLwC3bq0SAZvr25fCq3JyfnT6evyN/y86Vre4lT+sa1PXF8cNMQ7HDT3SFMzc0B+jD2LiGlAhPyOYeDEO3f/cF2f6tHRgmo90lBkcVeZzjXduZJTjp7RxlyuFDZ6ecKyWGArnIsvrLFUzLq0dmubn+L2VM35BEcNWDLTj59oWYmuF7JM80kMHVT+RnhjgtNiRmKVEDRhvRMTqcDInJT+VwBKGTT3azbcCiNMRxjwJiVdYmNNySf4uiMzobrwh2ILNOBCz7UavEOhreCZPp8rpwHvN+ZZ1x++yRluAPQxKNbkgdmIyF2Wfpmj/w9NjEZVCmVuZHN0cmVhbQplbmRvYmoKMSAwIG9iago8PC9UYWJzL1MvR3JvdXA8PC9TL1RyYW5zcGFyZW5jeS9UeXBlL0dyb3VwL0NTL0RldmljZVJHQj4+L0NvbnRlbnRzIDQgMCBSL1R5cGUvUGFnZS9SZXNvdXJjZXM8PC9Db2xvclNwYWNlPDwvQ1MvRGV2aWNlUkdCPj4vUHJvY1NldCBbL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSV0vRm9udDw8L0YxIDIgMCBSL0YyIDMgMCBSPj4+Pi9QYXJlbnQgNSAwIFIvTWVkaWFCb3hbMCAwIDQyMSA1OTVdPj4KZW5kb2JqCjYgMCBvYmoKWzEgMCBSL1hZWiAwIDYwNSAwXQplbmRvYmoKMiAwIG9iago8PC9TdWJ0eXBlL1R5cGUxL1R5cGUvRm9udC9CYXNlRm9udC9IZWx2ZXRpY2EvRW5jb2RpbmcvV2luQW5zaUVuY29kaW5nPj4KZW5kb2JqCjMgMCBvYmoKPDwvU3VidHlwZS9UeXBlMS9UeXBlL0ZvbnQvQmFzZUZvbnQvSGVsdmV0aWNhLUJvbGQvRW5jb2RpbmcvV2luQW5zaUVuY29kaW5nPj4KZW5kb2JqCjUgMCBvYmoKPDwvS2lkc1sxIDAgUl0vVHlwZS9QYWdlcy9Db3VudCAxL0lUWFQoMi4xLjcpPj4KZW5kb2JqCjcgMCBvYmoKPDwvTmFtZXNbKEpSX1BBR0VfQU5DSE9SXzBfMSkgNiAwIFJdPj4KZW5kb2JqCjggMCBvYmoKPDwvRGVzdHMgNyAwIFI+PgplbmRvYmoKOSAwIG9iago8PC9OYW1lcyA4IDAgUi9UeXBlL0NhdGFsb2cvUGFnZXMgNSAwIFIvVmlld2VyUHJlZmVyZW5jZXM8PC9QcmludFNjYWxpbmcvQXBwRGVmYXVsdD4+Pj4KZW5kb2JqCjEwIDAgb2JqCjw8L01vZERhdGUoRDoyMDE5MDQwMTIyMjAzNCswMicwMCcpL0NyZWF0b3IoSmFzcGVyUmVwb3J0cyBMaWJyYXJ5IHZlcnNpb24gNi4zLjApL0NyZWF0aW9uRGF0ZShEOjIwMTkwNDAxMjIyMDM0KzAyJzAwJykvUHJvZHVjZXIoaVRleHQgMi4xLjcgYnkgMVQzWFQpPj4KZW5kb2JqCnhyZWYKMCAxMQowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDE2MjYgMDAwMDAgbiAKMDAwMDAwMTkxMSAwMDAwMCBuIAowMDAwMDAxOTk5IDAwMDAwIG4gCjAwMDAwMDAwMTUgMDAwMDAgbiAKMDAwMDAwMjA5MiAwMDAwMCBuIAowMDAwMDAxODc2IDAwMDAwIG4gCjAwMDAwMDIxNTUgMDAwMDAgbiAKMDAwMDAwMjIwOSAwMDAwMCBuIAowMDAwMDAyMjQxIDAwMDAwIG4gCjAwMDAwMDIzNDQgMDAwMDAgbiAKdHJhaWxlcgo8PC9JbmZvIDEwIDAgUi9JRCBbPDE4OTE2ZDk3YTAyNzE2YTFlMDU5ZjA5YTJiN2YzMzU5PjwyNjFhNjI5ZGFkYzM0YmE5ZmEwZGNmMzM1YjQ1YjYxNj5dL1Jvb3QgOSAwIFIvU2l6ZSAxMT4+CnN0YXJ0eHJlZgoyNTEyCiUlRU9GCg=='
# with open("imageToSave.pdf", "wb") as fh:
#     fh.write(base64.decodebytes(img_data))

def web_vut(request):
    if request.method == 'GET':
        try:
            entidad = Entidad.objects.get(id=request.GET['e'])
        except:
            entidades_id = Vivienda.objects.filter(publicarweb=True).values_list('entidad__id', flat=True).distinct()
            entidades = Entidad.objects.filter(id__in=entidades_id)
            c = entidades.count()
            if c == 0:
                from autenticar.views import CaptchaForm
                form = CaptchaForm()
                return render(request, "autenticar.html", {'form': form, 'email': 'aaa@aaa', 'tipo': 'acceso'})
            elif c == 1:
                entidad = entidades[0]
            else:
                return render(request, "web_vut_choose.html", {'entidades': entidades})

        viviendas = Vivienda.objects.filter(entidad=entidad, borrada=False, publicarweb=True)
        paginator = Paginator(viviendas, 15)
        try:
            page = paginator.get_page(request.GET.get('p'))
        except:
            page = paginator.get_page(1)

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'libro_contabilidad_vut':
            permiso = Permiso.objects.get(code_nombre='genera_libro_registro_policia')
            vivienda = Vivienda.objects.get(id=request.POST['id_vivienda'])
            if has_permiso_on_vivienda(g_e, vivienda, permiso):
                fecha_anterior_limite = datetime.today().date() - timedelta(1100)
                viajeros = Viajero.objects.filter(reserva__vivienda=vivienda,
                                                  reserva__entrada__gte=fecha_anterior_limite)
                c = render_to_string('libro_registro_policia.html',
                                     {'vivienda': vivienda, 'viajeros': viajeros, 'ruta_base': RUTA_BASE})
                ruta = '%sentidad_%s/vivienda%s/' % (MEDIA_VUT, vivienda.entidad.code, vivienda.id)
                fich = html_to_pdf(request, c, fichero='libro_registros', media=ruta,
                                   title=u'Libro de registro de viajeros', tipo='sin_cabecera')
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=Libro_registro_viajeros.pdf'
                return response

    return render(request, "web_vut.html",
                  {
                      'formname': 'web_vut',
                      'page': page,
                      'entidad': entidad,
                      'localidades': viviendas.values_list('municipio', flat=True).distinct()
                  })


def web_vut_id(request, vivienda_id):
    if vivienda_id == 7334:
        return render(request, "web_vut_prueba.html",
                      {
                          'formname': 'web_vut_prueba',
                          'vivienda': Vivienda.objects.get(id=1)
                      })
    if request.method == 'GET':
        try:
            vivienda = Vivienda.objects.get(id=vivienda_id)
            # vivienda = Vivienda.objects.get(id=request.GET['v'])
        except:
            return redirect(web_vut)

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'libro_contabilidad_vut':
            permiso = Permiso.objects.get(code_nombre='genera_libro_registro_policia')
            vivienda = Vivienda.objects.get(id=request.POST['id_vivienda'])
            if has_permiso_on_vivienda(g_e, vivienda, permiso):
                fecha_anterior_limite = datetime.today().date() - timedelta(1100)
                viajeros = Viajero.objects.filter(reserva__vivienda=vivienda,
                                                  reserva__entrada__gte=fecha_anterior_limite)
                c = render_to_string('libro_registro_policia.html',
                                     {'vivienda': vivienda, 'viajeros': viajeros, 'ruta_base': RUTA_BASE})
                ruta = '%sentidad_%s/vivienda%s/' % (MEDIA_VUT, vivienda.entidad.code, vivienda.id)
                fich = html_to_pdf(request, c, fichero='libro_registros', media=ruta,
                                   title=u'Libro de registro de viajeros', tipo='sin_cabecera')
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=Libro_registro_viajeros.pdf'
                return response

    return render(request, "web_vut_id.html",
                  {
                      'formname': 'web_vut_id',
                      'vivienda': vivienda
                  })


def reserva_vut_crea_recibo(request, reserva_id):
    g_e = request.session['gauser_extra']

    viviendas = viviendas_con_permiso(g_e, 'crea_reservas')
    reserva = Reserva.objects.get(id=reserva_id)
    if reserva.vivienda in viviendas:
        if request.method == 'POST':
            c = request.POST['recibo_html']
            ruta = '%sentidad_%s/vivienda%s/' % (MEDIA_VUT, reserva.vivienda.entidad.code, reserva.vivienda.id)
            fich = html_to_pdf(request, c, fichero='recibo_viajero', media=ruta,
                               title='Justificante de pago', tipo='sin_cabecera')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=justificante_de_pago.pdf'
            return response
        return render(request, "reserva_vut_crea_recibo.html",
                      {
                          'formname': 'reserva_vut_crea_recibo',
                          'reserva': reserva
                      })

    try:
        viviendas = viviendas_con_permiso(g_e, 'crea_reservas')
        reserva = Reserva.objects.get(id=reserva_id)
        if reserva.vivienda in viviendas:
            if request.method == 'POST':
                c = request.POST['html']
                ruta = '%sentidad_%s/vivienda%s/' % (MEDIA_VUT, reserva.vivienda.entidad.code, reserva.vivienda.id)
                fich = html_to_pdf(request, c, fichero='recibo_viajero', media=ruta,
                                   title='Justificante de pago', tipo='sin_cabecera')
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=justificante_de_pago.pdf'
                return response
            return render(request, "reserva_vut_crea_recibo.html",
                          {
                              'formname': 'reserva_vut_crea_recibo',
                              'reserva': reserva
                          })
        else:
            return render(request, "no_login.html", {'pag': '"Crear recibo para esta reserva"', })
    except:
        return render(request, "no_login.html", {'pag': '"Crear recibo para esta reserva"', })


# @permiso_required('acceso_contratos_vut')
def contratos_vut(request):
    g_e = request.session['gauser_extra']
    vvs = viviendas_autorizado(g_e)
    contratos = ContratoVUT.objects.filter(propietario=g_e)

    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_contrato_vut':
            try:
                if request.POST['reserva']:
                    reserva = Reserva.objects.get(vivienda__in=vvs, id=request.POST['id'])
                    contrato_vut = ContratoVUT.objects.create(entrada=reserva.entrada, nombre=str(reserva),
                                                              vivienda=vvs[0],
                                                              salida=reserva.salida, fecha=timezone.datetime.today(),
                                                              total=reserva.total, max_per=4, propietario=g_e)
                else:
                    ahora = timezone.datetime.now()
                    nombre = 'Nuevo contrato para VUT'
                    contrato_vut = ContratoVUT.objects.create(entrada=ahora, salida=ahora + timedelta(days=10),
                                                              max_per=4, vivienda=vvs[0],
                                                              fecha=ahora, total=100, propietario=g_e, nombre=nombre)
                texto = render_to_string('contratos_vut_accordion_content_texto.html', {'contrato': contrato_vut})
                contrato_vut.texto = texto
                contrato_vut.save()
                html = render_to_string('contratos_vut_accordion.html',
                                        {'buscadas': False, 'contratos_vut': [contrato_vut], 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': msg})
        elif request.POST['action'] == 'open_accordion':
            try:
                contrato_vut = ContratoVUT.objects.get(id=request.POST['id'], propietario=g_e)
                html = render_to_string('contratos_vut_accordion_content.html',
                                        {'contrato': contrato_vut, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html, 'editado': contrato_vut.editado})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'borrar_contrato_vut':
            try:
                contrato_vut = ContratoVUT.objects.get(id=request.POST['id'], propietario=g_e)
                contrato_vut.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_texto':
            try:
                msg = ''
                contrato_vut = ContratoVUT.objects.get(id=request.POST['id'], propietario=g_e)
                hay_firmas = contrato_vut.hay_firmas
                setattr(contrato_vut, request.POST['campo'], request.POST['valor'])
                if request.POST['campo'] != 'nombre' and hay_firmas:
                    contrato_vut.firma0, contrato_vut.firma1, contrato_vut.firma2, contrato_vut.firma3 = '', '', '', ''
                    msg = 'Firmas eliminadas'
                contrato_vut.save()
                return JsonResponse({'ok': True, 'msg': msg})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_fecha':
            try:
                contrato_vut = ContratoVUT.objects.get(id=request.POST['id'], propietario=g_e)
                fecha_anterior = getattr(contrato_vut, request.POST['campo'])
                fecha = timezone.datetime.strptime(request.POST['valor'], '%Y-%m-%d')
                if request.POST['campo'] != 'fecha':
                    fecha = fecha.replace(hour=fecha_anterior.hour, minute=fecha_anterior.minute)
                setattr(contrato_vut, request.POST['campo'], fecha)
                contrato_vut.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_hora':
            try:
                contrato_vut = ContratoVUT.objects.get(id=request.POST['id'], propietario=g_e)
                fecha_anterior = getattr(contrato_vut, request.POST['campo'])
                hora = timezone.datetime.strptime(request.POST['valor'], '%H:%M')
                fecha_real = fecha_anterior.replace(hour=hora.hour, minute=hora.minute)
                setattr(contrato_vut, request.POST['campo'], fecha_real)
                contrato_vut.save()
                return JsonResponse({'ok': True, 'f': str(fecha_real)})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_animales':
            try:
                contrato_vut = ContratoVUT.objects.get(id=request.POST['id'], propietario=g_e)
                contrato_vut.animales = not contrato_vut.animales
                contrato_vut.save()
                return JsonResponse({'ok': True, 'html': ['No', 'Sí'][contrato_vut.animales]})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_contrato':
            try:
                contrato_vut = ContratoVUT.objects.get(id=request.POST['id'], propietario=g_e)
                texto = render_to_string('contratos_vut_accordion_content_texto.html', {'contrato': contrato_vut})
                contrato_vut.texto = texto
                contrato_vut.editado = True
                contrato_vut.save()
                return JsonResponse({'ok': True, 'texto': texto})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_vivienda':
            try:
                contrato_vut = ContratoVUT.objects.get(id=request.POST['id'], propietario=g_e)
                vivienda = vvs.get(id=request.POST['valor'])
                contrato_vut.vivienda = vivienda
                contrato_vut.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})


        elif request.POST['action'] == 'paginar_contratos_vut':
            try:
                q1 = Q(tarea__fecha__gte=g_e.ronda.inicio, tarea__fecha__lte=g_e.ronda.fin)
                if g_e.has_permiso('ve_cualquier_contrato_vut'):
                    q2 = Q(tarea__creador__ronda__entidad=g_e.ronda.entidad)
                else:
                    q2 = Q(tarea__creador__gauser=g_e.gauser) | Q(inspector__gauser=g_e.gauser)
                posibles_contratos_vut = InspectorTarea.objects.filter(q1 & q2)
                paginator = Paginator(posibles_contratos_vut, 25)
                contratos_vut = paginator.page(int(request.POST['page']))
                html = render_to_string('contratos_vut_accordion.html', {'contratos_vut': contratos_vut, 'pag': True})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
    elif request.method == 'POST' and not request.is_ajax():
        if request.POST['action'] == 'pdf_contrato':
            contrato_vut = ContratoVUT.objects.get(id=request.POST['id_contrato_vut'], propietario=g_e)
            return genera_pdf_contrato(contrato_vut)

    return render(request, "contratos_vut.html",
                  {
                      'formname': 'contratos_vut',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nuevo contrato',
                            'permiso': 'libre', 'title': 'Crear un nuevo contrato para vut'},
                           ),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'contratos_vut': contratos,
                      'g_e': g_e
                  })


def genera_pdf_contrato(contrato):
    dce_nombre = 'Contrato alquiler VUT'
    try:
        dce = DocConfEntidad.objects.get(entidad=contrato.propietario.ronda.entidad, nombre=dce_nombre)
    except:
        dce = DocConfEntidad.objects.get(entidad=contrato.propietario.ronda.entidad, predeterminado=True)
        dce.pk = None
        dce.nombre = dce_nombre
        dce.predeterminado = False
        dce.editable = False
        dce.save()
    contrato_vut = contrato
    preambulo = """<!DOCTYPE html>
                                <html lang="es">
                                <head>
                                    <meta charset="UTF-8">
                                    <title>Contrato VUT ARVUTUR</title>
                                    <style>
                                    body { font-family: sans-serif; }
                                    p, li { text-align: justify; }
                                    </style>
                                </head>
                                <body>"""
    if contrato_vut.hay_firmas:
        firmas = render_to_string('contratos_vut_accordion_content_texto_firmas.html',
                              {'contrato': contrato_vut})
    else:
        firmas = ''
    final = "</body></html>"
    html = preambulo + contrato_vut.texto + firmas + final
    filename = 'Contrato_%s_%s.pdf' % (str(contrato_vut.propietario.gauser.id), str(contrato_vut.id))
    ruta = MEDIA_VUT + '%s/contratos_alquiler/' % contrato_vut.propietario.ronda.entidad.code
    fichero = '%s%s' % (ruta, filename)
    if not os.path.exists(os.path.dirname(ruta)):
        os.makedirs(os.path.dirname(ruta))
    pdfkit.from_string(html, fichero, dce.get_opciones)
    fich = open(fichero, 'rb')
    response = HttpResponse(fich, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    logger.info('Se genera pdf del contrato id: %s ' % contrato_vut.id)
    return response


def firconvut(request, secret_id, n):
    try:
        if n == '0':
            g_e = request.session['gauser_extra']
            contrato = ContratoVUT.objects.get(secret=secret_id, salida__gte=timezone.datetime.now(), propietario=g_e)
            nombre_firmante = g_e.gauser.get_full_name()
        else:
            contrato = ContratoVUT.objects.get(secret=secret_id, salida__gte=timezone.datetime.now())
            nombre_firmante = getattr(contrato, 'viajero%s' % n)
            if not nombre_firmante:
                return redirect('/')
        if request.method == 'POST':
            if request.POST['action'] == 'add_firma':
                setattr(contrato, 'firma%s' % n, request.POST['firma'])
                contrato.save()
            elif request.POST['action'] == 'genera_pdf':
                return genera_pdf_contrato(contrato)
        firmado = True if getattr(contrato, 'firma%s' % n) else False
        return render(request, "contratos_vut_firmar.html",
                      {
                          'formname': 'firma_contrato_vut',
                          'contrato': contrato,
                          'firmante': (n, nombre_firmante, firmado)
                      })
    except:
        return redirect('/')
