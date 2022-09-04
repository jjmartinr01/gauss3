# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import io
import logging
import os
import string
import subprocess
import time
import unicodedata
from difflib import get_close_matches

import requests
import simplejson as json
try:
    from cryptography.fernet import Fernet
    from gauss.settings import RACIMA_KEY
except:
    pass
from datetime import date, datetime, timedelta, timezone
from time import sleep
from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django import forms
from django.forms import ModelForm
from django.utils import translation, timezone
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.utils.encoding import smart_text
from gauss.constantes import PROVINCIAS, GAUSER_COMODIN
from gauss.funciones import pass_generator, genera_nie
from gauss.settings import RUTA_BASE_SETTINGS
from estudios.models import Gauser_extra_estudios
from autenticar.models import Enlace, Permiso, Gauser, Menu_default
from entidades.models import Subentidad, Cargo, Entidad, Gauser_extra, Menu, CargaMasiva, ConfigurationUpdate, Ronda, \
    Reserva_plaza
from entidades.tasks import carga_masiva_from_excel, ejecutar_configurar_cargos_permisos, \
    ejecutar_configurar_menus_centros_educativos, ejecutar_configurar_docs_conf_educarioja
from mensajes.views import crear_aviso, crea_mensaje_cola
from mensajes.models import Aviso, Mensaje
from bancos.views import asocia_banco_ge
from autenticar.control_acceso import LogGauss, permiso_required, gauss_required
from captcha.fields import CaptchaField
# try:
#     from gauss.settings import CAS_URL
# except:
#     CAS_URL = 'https://ias1.larioja.org/eduCas/'

CAS_URL = 'https://ias1.larioja.org/casLR/'


# La línea "from django.utils import translation, timezone" y las siguientes 2 líneas, así como la nº 234 (o alrededor)
# que contiene la variable "user_language" son para establecer el español como idioma por defecto a través de una
#  variable de session
user_language = 'es'
translation.activate(user_language)

logger = logging.getLogger('django')


##########################################################################
###############  FUNCIONES RELACIONADAS CON EL CAPTCHA PARA RECUPERAR LA PASSWORD

class CaptchaForm(forms.Form):
    captcha = CaptchaField()


def recarga_captcha(request):
    if request.is_ajax():
        form = CaptchaForm()
        data = render_to_string("captcha.html", {'form': form})
        return HttpResponse(data)


##########################################################################
###############  FUNCIONES RELACIONADAS CON USUARIO GAUSS
@gauss_required
def carga_docentes_general(request):
    #Esta función carga los docentes de los centros a través del archivo xls obtenido de:
    # Racima -> Gestión -> Seguimiento -> Catálogo de consultas -> Módulo: Empleados -> Consulta: Plantillas orgánicas
    g_e = request.session['gauser_extra']
    if g_e.gauser.username == 'gauss':
        if request.method == 'POST':
            action = request.POST['action']
            if action == 'carga_masiva_docentes_racima':
                if 'excel' in request.FILES['file_masivo'].content_type:
                    CargaMasiva.objects.create(g_e=g_e, ronda=g_e.ronda, fichero=request.FILES['file_masivo'],
                                               tipo='DOCENTES_RACIMA')
                    try:
                        carga_masiva_from_excel.apply_async(expires=300)
                        crear_aviso(request, True, 'cdg_manual')
                        crear_aviso(request, False, 'El archivo cargado puede tardar unos minutos en ser procesado.')
                    except:
                        crear_aviso(request, False,
                                    'El archivo cargado no se ha encolado. Ejecutar la carga manualmente.')
            else:
                crear_aviso(request, False, 'El archivo cargado no tiene el formato adecuado.')

    return render(request, "carga_masiva_docentes_racima.html",
                  {
                      'iconos': ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                                  'title': 'Subir el archivo a GAUSS',
                                  'permiso': 'acceso_carga_masiva'}, {}),
                      'formname': 'carga_masiva_docentes_racima',
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@gauss_required
def borrar_entidades(request):
    g_e = request.session['gauser_extra']
    if g_e.gauser.username == 'gauss':
        if request.method == 'POST':
            action = request.POST['action']
            if action == 'datos_entidad' and request.is_ajax():
                try:
                    entidad = Entidad.objects.get(id=request.POST['id'])
                    rondas = Ronda.objects.filter(entidad=entidad)
                    html = render_to_string('borrar_entidades_content.html', {'rondas': rondas})
                    return JsonResponse({'ok': True, 'html': html})
                except:
                    return JsonResponse({'ok': False})
            elif action == 'borrar_usuarios' and request.is_ajax():
                try:
                    gauser_comodin = Gauser.objects.get(username=GAUSER_COMODIN)
                except:
                    ahora = datetime.now()
                    gauser_comodin = Gauser.objects.create(username=GAUSER_COMODIN, last_login=ahora)
                ronda = Ronda.objects.get(id=request.POST['ronda'])
                usuarios_ronda = Gauser_extra.objects.filter(Q(ronda=ronda), ~Q(gauser=gauser_comodin))
                num_ge_borrados = 0
                num_g_borrados = 0
                num_g_vaciados = 0
                mensaje = ''
                for usuario in usuarios_ronda:
                    g = usuario.gauser
                    ges = Gauser_extra.objects.filter(gauser=g)
                    if ges.count() == 1 and ges[0] == usuario:
                        try:
                            usuario.delete()
                            num_ge_borrados += 1
                        except:
                            mensaje += '%s no borrado' % usuario.gauser.get_full_name()
                            usuario.permisos.clear()
                            usuario.cargos.clear()
                            usuario.subentidades.clear()
                            usuario.subsubentidades.clear()
                            usuario.hermanos.clear()
                            campos = {'id_organizacion': None, 'id_entidad': None, 'alias': None, 'observaciones': None,
                                      'foto': None, 'tutor1': None, 'tutor2': None, 'ocupacion': None,
                                      'num_cuenta_bancaria': None, 'clave_ex': None,
                                      'educa_pk': None, 'fecha_consentimiento': None, 'activo': False}
                            usuario.gauser = gauser_comodin
                            for key, value in campos.items():
                                setattr(usuario, key, value)
                            usuario.save()
                        try:
                            g.delete()
                            num_g_borrados += 1
                        except:
                            nuevo_username = pass_generator(30)
                            campos = {'first_name': 'borrado', 'last_name': '', 'email': '', 'sexo': None, 'dni': None,
                                      'address': None, 'postalcode': None, 'localidad': None, 'provincia': None,
                                      'nacimiento': None, 'telfij': None, 'telmov': None, 'familia': False,
                                      'fecha_alta': None, 'fecha_baja': None, 'ficticio': True, 'educa_pk': None,
                                      'username': nuevo_username}
                            for key, value in campos.items():
                                setattr(g, key, value)
                            g.save()
                            num_g_vaciados += 1
                    else:
                        try:
                            usuario.delete()
                            num_ge_borrados += 1
                        except:
                            mensaje += '%s modificado a gauser comodín' % usuario.gauser.get_full_name()
                            usuario.permisos.clear()
                            usuario.cargos.clear()
                            usuario.subentidades.clear()
                            usuario.subsubentidades.clear()
                            usuario.hermanos.clear()
                            campos = {'id_organizacion': None, 'id_entidad': None, 'alias': None, 'observaciones': None,
                                      'foto': None, 'tutor1': None, 'tutor2': None, 'ocupacion': None,
                                      'num_cuenta_bancaria': None, 'clave_ex': None,
                                      'educa_pk': None, 'fecha_consentimiento': None, 'activo': False}
                            usuario.gauser = gauser_comodin
                            for key, value in campos.items():
                                setattr(usuario, key, value)
                            usuario.save()
                return JsonResponse({'ok': True, 'num_g_borrados': num_g_borrados, 'num_ge_borrados': num_ge_borrados,
                                     'num_g_vaciados': num_g_vaciados, 'mensaje': mensaje})
            elif action == 'borrar_entidad' and request.is_ajax():
                mensaje = ''
                entidad = Entidad.objects.get(id=request.POST['entidad'])
                reservas = Reserva_plaza.objects.filter(entidad=entidad)
                subentidades = Subentidad.objects.filter(entidad=entidad)
                cargos = Cargo.objects.filter(entidad=entidad)
                try:
                    reservas.delete()
                    mensaje += 'Borradas las reservas de plaza'
                except:
                    mensaje += 'No se han podido borrar las reservas de plaza'
                try:
                    subentidades.delete()
                    mensaje += 'Borradas las subentidades'
                except:
                    mensaje += 'No se han podido borrar las subentidades'
                try:
                    cargos.delete()
                    mensaje += 'Borradas los cargos'
                except:
                    mensaje += 'No se han podido borrar los cargos'
                try:
                    entidad.delete()
                    entidad_borrada = 1
                    entidad_vaciada = 0
                except:
                    campos = {'organization': None, 'ronda': None, 'code': None, 'nif': None, 'banco': None,
                              'iban': None, 'name': None, 'address': None, 'localidad': None, 'postalcode': None,
                              'tel': None, 'fax': None, 'web': None, 'mail': None, 'dominio': None}
                    for key, value in campos.items():
                        setattr(entidad, key, value)
                    entidad.save()
                    entidad_borrada = 0
                    entidad_vaciada = 1
                return JsonResponse({'ok': True, 'entidad_borrada': entidad_borrada,
                                     'entidad_vaciada': entidad_vaciada})
        entidades = Entidad.objects.all()
        return render(request, "borrar_entidades.html",
                      {'formname': 'borrar_entidades',
                       'entidades': entidades,
                       'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                       })


##########################################################################
###############  FUNCIONES RELACIONADAS CON LOS MENÚS

@gauss_required
def actualizar_menus_permisos(request):
    g_e = request.session['gauser_extra']
    if g_e.gauser.username == 'gauss':
        from importlib import import_module
        from gauss.settings import INSTALLED_APPS  # as apps
        for app in INSTALLED_APPS:
            try:
                conf_module = import_module('.configuration', app)
                conf_file = os.path.dirname(conf_module.__file__) + '/configuration.py'
                conf_file_time = os.path.getmtime(conf_file)
                cu, c = ConfigurationUpdate.objects.get_or_create(entidad=g_e.ronda.entidad, app=app)
                if time.mktime(cu.last_update.timetuple()) < conf_file_time:
                    cu.updated = False
                    cu.save()
            except Exception as inst:
                pass
        if request.method == 'POST' and request.is_ajax():
            if request.POST['action'] == 'update_app':
                app = request.POST['app']
                aviso = ''
                ok = True
                # for app in apps:
                try:
                    modulo = import_module('.configuration', app)
                except Exception as inst:
                    modulo = None
                    aviso = app + ': ' + inst.args[0]
                    ok = False
                if modulo:
                    pos_nivel1 = 0
                    aviso += 'pos_nivel1'
                    for menu_default in modulo.MENU_DEFAULT:
                        try:
                            parent = Menu_default.objects.get(code_menu=menu_default['parent'])
                        except:
                            parent = None
                        m = Menu_default.objects.get_or_create(code_menu=menu_default['code_menu'])[0]
                        if menu_default['nivel'] == 1:
                            pos_nivel1 += 1
                            pos = pos_nivel1
                        else:
                            pos = menu_default['pos']
                        m.texto_menu = menu_default['texto_menu']
                        m.href = menu_default['href']
                        m.nivel = menu_default['nivel']
                        m.pos = pos
                        m.tipo = menu_default['tipo']
                        m.parent = parent
                        m.save()
                        aviso += str(m.pos)
                        # Para cada menu_default es necesario crear un permiso asociado (el permiso de acceso a ese menú)
                        texto_permiso = 'Tiene acceso al menú: %s' % (menu_default['texto_menu'])
                        p = Permiso.objects.get_or_create(code_nombre=menu_default['code_menu'], tipo='MENU')[0]
                        p.nombre = texto_permiso
                        p.menu = m
                        p.save()
                    for permiso in modulo.PERMISOS:
                        p = Permiso.objects.get_or_create(code_nombre=permiso['code_nombre'], tipo='ACTION')[0]
                        m = Menu_default.objects.get(code_menu=permiso['menu'])
                        p.nombre = permiso['nombre']
                        p.menu = m
                        p.save()
                if ok:
                    cu = ConfigurationUpdate.objects.get(entidad=g_e.ronda.entidad, app=app)
                    cu.last_update = timezone.now()
                    cu.updated = True
                    cu.save()
                return JsonResponse({'ok': ok, 'aviso': aviso})
            else:
                return JsonResponse({'ok': False, 'aviso': 'Error en la actualización solicitada'})
        return render(request, "actualizar_menus_permisos.html", {'formname': 'actualizar_menus_permisos',
                                                                  'apps_configuration': ConfigurationUpdate.objects.filter(
                                                                      entidad=g_e.ronda.entidad),
                                                                  'avisos': Aviso.objects.filter(usuario=g_e,
                                                                                                 aceptado=False)})
    else:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[-1].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        logger.info('%s, acceso denegado a %s desde %s' % (g_e, request.path_info, ip))
        return render(request, "enlazar.html", {'page': '/principal/', })


def crea_menu_from_default(menu_default, entidad):
    try:
        m = Menu.objects.get(entidad=entidad, menu_default=menu_default)
    except:
        pos = Menu.objects.filter(entidad=entidad, menu_default__nivel=menu_default.nivel,
                                  menu_default__parent=menu_default.parent).count() + 1
        m = Menu.objects.create(entidad=entidad, menu_default=menu_default,
                                texto_menu=menu_default.texto_menu, pos=pos)
    return m


@gauss_required
def asignar_menus_entidad(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'add_menu':
            creados = []
            menu_default = Menu_default.objects.get(id=request.POST['id'])
            if menu_default.parent:
                crea_menu_from_default(menu_default.parent, g_e.ronda.entidad)
                crea_menu_from_default(menu_default, g_e.ronda.entidad)
                creados.append(menu_default.parent.id)
                creados.append(menu_default.id)
            else:
                crea_menu_from_default(menu_default, g_e.ronda.entidad)
                creados.append(menu_default.id)

            for m in menu_default.children:
                crea_menu_from_default(m, g_e.ronda.entidad)
                creados.append(m.id)
            return JsonResponse(creados, safe=False)
        elif action == 'del_menu':
            menu_default = Menu_default.objects.get(id=request.POST['id'])
            parent_default = menu_default.parent if menu_default.parent else None
            borrados = [menu_default.id]
            for m in menu_default.children:
                borrados.append(m.id)
                try:
                    Menu.objects.get(entidad=g_e.ronda.entidad, menu_default=m).delete()
                except:
                    pass
            menu = Menu.objects.get(entidad=g_e.ronda.entidad, menu_default=menu_default)
            pos = 0
            for m in menu.siblings:
                pos += 1
                m.pos = pos
                m.save()
            menu.delete()
            if parent_default:
                parent = Menu.objects.get(entidad=g_e.ronda.entidad, menu_default=parent_default)
                if parent.children.count() == 0:
                    parent.delete()
                    borrados.append(parent_default.id)
            return JsonResponse(borrados, safe=False)
    menus_default = Menu_default.objects.filter(tipo='Accesible', nivel=1).order_by('id')
    menus_entidad = Menu.objects.filter(entidad=g_e.ronda.entidad).values_list('menu_default__code_menu', flat=True)

    return render(request, "menus_entidad.html",
                  {'formname': 'asignar_menus_entidad', 'menus_default': menus_default, 'menus_entidad': menus_entidad,
                   'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                   })


##########################################################################
###############  FUNCIONES RELACIONADAS CON LOS ENLACES


@LogGauss
def enlazar(request):
    try:
        g_e = Gauser_extra.objects.get(id=request.GET['u'])
        enlace = Enlace.objects.get(usuario=g_e.gauser, code=request.GET['c'])
        full_name = enlace.usuario.get_full_name()
        if enlace.usuario.is_active:
            if (enlace.deadline > date.today()):
                enlace.usuario.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, enlace.usuario)
                request.session["gauser_extra"] = g_e
                request.session['num_items_page'] = 15
                logger.info('%s se loguea en GAUSS a través de un enlace' % (full_name))
                return render(request, "enlazar.html", {'page': enlace.enlace})
            else:
                logger.info('%s no se puede loguear en GAUSS a través de un enlace caducado' % (full_name))
                return render(request, "no_enlace.html", {'usuario': enlace.usuario, })
        else:
            logger.info('%s no se puede loguear en GAUSS. Su usuario no está activo' % (full_name))
            return render(request, "no_cuenta.html", {'usuario': enlace.usuario, })
    except:
        logout(request)
        form = CaptchaForm()
        return render(request, "autenticar.html", {'form': form, 'email': 'aaa@aaa', 'tipo': 'acceso'})


@gauss_required
def ejecutar_query(request):
    g_e = request.session['gauser_extra']
    resultado = ''
    query = ''
    if g_e.gauser.username == 'gauss':
        if request.method == 'POST':
            query = request.POST['query']
            try:
                resultado = eval(query)
            except Exception as msg:
                resultado = msg
        import django
        import platform
        from django.db import connection
        return render(request, "ejecutar_query.html",
                      {
                          'iconos': ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                                      'title': 'Ejecutar query',
                                      'permiso': 'libre'}, {}),
                          'formname': 'queryform',
                          'query': query,
                          'resultado': resultado,
                          'version_django': django.get_version(),
                          'version_postgre': connection.cursor().connection.server_version,
                          'platform': platform,
                          'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      })
    else:
        return render(request, "no_login.html", {'pag': ''})


##########################################################################
###############  PÁGINA DE ACCESO

@LogGauss
def index(request):
    if 'nexturl' in request.GET:
        url_destino = request.GET['nexturl']
    else:
        url_destino = '/calendario/'  # Esta será la url a la que el sistema vaya por defecto
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    # dominio = request.META['HTTP_HOST'].split('.')[0]
    # entidad = Entidad.objects.filter(dominio=dominio)

    if request.method == 'POST':
        # return render(request, "temporalmente_inactivo.html")
        if request.POST['action'] == 'acceso':
            usuario = request.POST['usuario']
            passusuario = request.POST['passusuario']
            gauss = authenticate(username='gauss', password=passusuario)
            if gauss is not None:
                logger.info('Se ha conectado con la contraseña de Gauss')
                try:
                    user = Gauser.objects.get(username=usuario)
                    logger.info('Se ha conectado con el usuario %s' % user)
                except:
                    user = None
                    logger.info('No hay usuario con username %s' % usuario)
            else:
                user = authenticate(username=usuario, password=passusuario)
                logger.info('Se ha conectado con el usuario %s con su contraseña' % user)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    request.session["hoy"] = datetime.today()
                    request.session[translation.LANGUAGE_SESSION_KEY] = user_language
                    # Identificación de la entidad en el que está el usuario:
                    try:
                        gauser_extras = [Gauser_extra.objects.get(gauser=user, activo=True, ronda_id=request.POST['r'])]
                        url_destino = request.POST['link']
                    except:
                        gauser_extras = Gauser_extra.objects.filter(Q(gauser=user) & Q(activo=True))
                    g_cs = gauser_extras
                    entidades_disponibles = 0
                    for gauser_extra in g_cs:
                        if gauser_extra.ronda == gauser_extra.ronda.entidad.ronda:
                            entidades_disponibles += 1
                        else:
                            gauser_extras = gauser_extras.exclude(pk=gauser_extra.id)
                    if entidades_disponibles > 1:
                        logger.info('Gauser con acceso a múltiples entidades.')
                        return render(request, "select_entidad.html", {'gauser_extras': gauser_extras, })
                    elif entidades_disponibles == 1:
                        request.session['gauser_extra'] = gauser_extras[0]
                        request.session['ronda'] = request.session["gauser_extra"].ronda
                        request.session['num_items_page'] = 15
                        # Las dos siguientes líneas son para asegurar que gauss existe como usuario en cualquier entidad
                        gauss = Gauser.objects.get(username='gauss')
                        Gauser_extra.objects.get_or_create(gauser=gauss, ronda=request.session["ronda"], activo=True)
                        logger.info('%s se loguea en GAUSS.' % (request.session["gauser_extra"]))
                        return redirect(url_destino)
                    else:
                        logger.info('Gauser activo, pero no tiene asociada ninguna entidad.')
                        return render(request, "no_cuenta.html", {'usuario': user, })
                else:
                    return render(request, "no_cuenta.html", {'usuario': user, })
            else:
                sleep(3)
                logger.info('Usuario: %s, no reconocido. Intenta acceso desde %s' % (usuario, ip))
                logout(request)
                form = CaptchaForm()
                return render(request, "autenticar.html", {'form': form, 'email': 'aaa@aaa', 'tipo': 'acceso'})
        elif request.POST['action'] == 'solicita_pass':
            form = CaptchaForm(request.POST)
            email = request.POST['email']
            if form.is_valid():
                try:
                    g_es = Gauser_extra.objects.filter(gauser__email=email, activo=True)
                    g_s = []
                    enlaces = []
                    for g_e in g_es:
                        if g_e.ronda == g_e.ronda.entidad.ronda and g_e.gauser not in g_s:
                            enlace = Enlace.objects.create(usuario=g_e.gauser, code=pass_generator(size=30),
                                                           enlace='/recupera_password/',
                                                           deadline=date.today() + timedelta(days=7))
                            enlaces.append(enlace)
                            g_s.append(g_e.gauser)

                    emisor = Gauser_extra.objects.filter(gauser__email='gauss@gaumentada.es')[0]
                    if request.POST['port']:
                        h = request.POST['protocol'] + '://' + request.POST['hostname'] + ':' + request.POST['port']
                    else:
                        h = request.POST['protocol'] + '://' + request.POST['hostname']
                    texto_mail = render_to_string("mail_recupera_password.html", {'enlaces': enlaces, 'h': h})
                    mensaje = Mensaje.objects.create(emisor=emisor, fecha=datetime.now(), tipo='mail',
                                                     asunto="Acceso a GAUSS", mensaje=texto_mail)
                    mensaje.receptores.add(g_s[0])
                    crea_mensaje_cola(mensaje)
                    return render(request, "mail_acceso_gauss.html", {'g_es': g_es, 'g_s': g_s})
                except:
                    form = CaptchaForm()
                    return render(request, "autenticar.html", {'form': form, 'tipo': 'introduce_mail',
                                                               'email': email})
            else:
                form = CaptchaForm()
                return render(request, "autenticar.html", {'form': form, 'tipo': 'introduce_captcha',
                                                           'email': email})
        elif request.POST['action'] == 'selecciona_entidad':
            request.session["gauser_extra"] = Gauser_extra.objects.get(pk=request.POST['gauser_extra'])
            request.session["ronda"] = request.session["gauser_extra"].ronda
            request.session['num_items_page'] = 15
            # Las dos siguientes líneas son para asegurar que gauss existe como usuario en cualquier entidad
            gauss = Gauser.objects.get(username='gauss')
            Gauser_extra.objects.get_or_create(gauser=gauss, ronda=request.session["ronda"], activo=True)
            logger.info('%s se loguea en GAUSS.' % (request.session["gauser_extra"]))
            return redirect(url_destino)
    else:
        # if 'service' in request.session:
        #     logout(request)
        #     response = HttpResponse(status=302)
        #     response['Location'] = CAS_URL + 'logout?url=https%3A%2F%2Fgauss.larioja.org%2Flogincas'
        #     return response
        # En el nuevo CAS cambiamos 'service' por 'TARGET'
        if 'TARGET' in request.session:
            logout(request)
            response = HttpResponse(status=302)
            response['Location'] = CAS_URL + 'logout?url=https%3A%2F%2Fgauss.larioja.org%2Flogincas'
            return response
        else:
            logout(request)
            form = CaptchaForm()
            return render(request, "autenticar.html", {'form': form, 'email': 'aaa@aaa', 'tipo': 'acceso', 'ip': ip})

# ------------------------------------------------------------------#
# Login en GAUSS a través del servidor CAS del Gobierno de La Rioja
# ------------------------------------------------------------------#
def logincas(request):
    # CAS_URL = 'https://ias1.larioja.org/casLR/'
    if request.method == 'GET':
        if 'nexturl' in request.GET:
            nexturl = '?nexturl=' + request.GET['nexturl']
            request.session['nexturl'] = request.GET['nexturl']
        else:
            nexturl = '?nexturl=%2Fcalendario%2F' # Por defecto irá a /calendario/
            request.session['nexturl'] = '/calendario/'
        request.session['service'] = 'https%3A%2F%2F' + request.META['HTTP_HOST'] + '%2Flogincas%2F' + nexturl
        if 'ticket' in request.GET:
            ticket = request.GET['ticket']
            url = CAS_URL + 'serviceValidate?service=' + request.session['service'] + '&ticket=' + ticket
            # xml = render_to_string('samlcas.xml', {'request_id': pass_generator(15), 'ticket': ticket,
            #                                        'datetime_iso': datetime.utcnow().isoformat()})
            # url = CAS_URL + 'samlValidate?service=' + request.session['service'] + '&ticket=' + ticket
            s = requests.Session()
            # headers = {'Content-Type': 'application/xml'}
            s.verify = False
            r = s.get(url, verify=False)
            # r = s.post(url, verify=False, data=xml, headers=headers)
            try:
                id = r.text.split('<cas:user>')[1].split('</cas:user>')[0]
            except:
                return HttpResponse(r.text)
            try:
                user = Gauser.objects.get(username=id)
            except:
                try:
                    user = Gauser.objects.get(dni=genera_nie(id))
                except:
                    return HttpResponse(id)
                    # return HttpResponse('Tu usuario en Gauss debe coincidir con el de Racima')
            if user.is_active:
                login(request, user)
                request.session["hoy"] = datetime.today()
                request.session[translation.LANGUAGE_SESSION_KEY] = user_language
                gauser_extras = Gauser_extra.objects.filter(Q(gauser=user) & Q(activo=True))
                g_cs = gauser_extras
                entidades_disponibles = 0
                for gauser_extra in g_cs:
                    if gauser_extra.ronda == gauser_extra.ronda.entidad.ronda:
                        entidades_disponibles += 1
                    else:
                        gauser_extras = gauser_extras.exclude(pk=gauser_extra.id)
                if entidades_disponibles > 1:
                    logger.info('Gauser con acceso a múltiples entidades.')
                    return render(request, "select_entidad.html", {'gauser_extras': gauser_extras, })
                elif entidades_disponibles == 1:
                    request.session["gauser_extra"] = gauser_extras[0]
                    request.session["ronda"] = request.session["gauser_extra"].ronda
                    request.session['num_items_page'] = 15
                    # Las dos siguientes líneas son para asegurar que gauss existe como usuario en cualquier entidad
                    gauss = Gauser.objects.get(username='gauss')
                    Gauser_extra.objects.get_or_create(gauser=gauss, ronda=request.session["ronda"], activo=True)
                    logger.info('%s se loguea en GAUSS.' % (request.session["gauser_extra"]))
                    return redirect(request.session['nexturl'])
                    # if request.session['nexturl']:
                    #     response = HttpResponse(status=302)
                    #     response['Location'] = request.session['nexturl']
                    # else:
                    #     return redirect(request.session['nexturl'])
                else:
                    logger.info('Gauser activo, pero no tiene asociada ninguna entidad.')
                    return render(request, "no_cuenta.html", {'usuario': user, })
            else:
                return render(request, "no_cuenta.html", {'usuario': user, })
        else:
            response = HttpResponse(status=302)
            response['Location'] = CAS_URL + 'login?inst=E&service=' + request.session['service']
            return response
    elif request.method == 'POST':
        if request.POST['action'] == 'selecciona_entidad':
            request.session["gauser_extra"] = Gauser_extra.objects.get(pk=request.POST['gauser_extra'])
            request.session["ronda"] = request.session["gauser_extra"].ronda
            request.session['num_items_page'] = 15
            # Las dos siguientes líneas son para asegurar que gauss existe como usuario en cualquier entidad
            gauss = Gauser.objects.get(username='gauss')
            Gauser_extra.objects.get_or_create(gauser=gauss, ronda=request.session["ronda"], activo=True)
            logger.info('%s se loguea en GAUSS.' % (request.session["gauser_extra"]))
            return redirect(request.session['nexturl'])

def logincas_antiguo(request):
    #Con este logincas solo se puede autenticar con certificado digital. En mensaje del 30/08/2022, Luis Miguel
    #Briones Román <lmbriones@larioja.org> me informa de como utilizar otra url para que aparezcan los mismos accesos
    #que en Racima. Es necesario añadir el parámetro 'inst' y cambiar 'service' por 'TARGET'. Mirar función logincas.
    # CAS_URL = 'https://ias1.larioja.org/casLR/'
    if request.method == 'GET':
        if 'nexturl' in request.GET:
            nexturl = '?nexturl=' + request.GET['nexturl']
            request.session['nexturl'] = request.GET['nexturl']
        else:
            nexturl = '?nexturl=%2Fcalendario%2F' # Por defecto irá a /calendario/
            request.session['nexturl'] = '/calendario/'
        request.session['service'] = 'https%3A%2F%2F' + request.META['HTTP_HOST'] + '%2Flogincas%2F' + nexturl
        if 'ticket' in request.GET:
            ticket = request.GET['ticket']
            url = CAS_URL + 'serviceValidate?service=' + request.session['service'] + '&ticket=' + ticket
            # xml = render_to_string('samlcas.xml', {'request_id': pass_generator(15), 'ticket': ticket,
            #                                        'datetime_iso': datetime.utcnow().isoformat()})
            # url = CAS_URL + 'samlValidate?service=' + request.session['service'] + '&ticket=' + ticket
            s = requests.Session()
            # headers = {'Content-Type': 'application/xml'}
            s.verify = False
            r = s.get(url, verify=False)
            # r = s.post(url, verify=False, data=xml, headers=headers)
            try:
                id = r.text.split('<cas:user>')[1].split('</cas:user>')[0]
            except:
                return HttpResponse(r.text)
            try:
                user = Gauser.objects.get(username=id)
            except:
                try:
                    user = Gauser.objects.get(dni=genera_nie(id))
                except:
                    return HttpResponse(id)
                    # return HttpResponse('Tu usuario en Gauss debe coincidir con el de Racima')
            if user.is_active:
                login(request, user)
                request.session["hoy"] = datetime.today()
                request.session[translation.LANGUAGE_SESSION_KEY] = user_language
                gauser_extras = Gauser_extra.objects.filter(Q(gauser=user) & Q(activo=True))
                g_cs = gauser_extras
                entidades_disponibles = 0
                for gauser_extra in g_cs:
                    if gauser_extra.ronda == gauser_extra.ronda.entidad.ronda:
                        entidades_disponibles += 1
                    else:
                        gauser_extras = gauser_extras.exclude(pk=gauser_extra.id)
                if entidades_disponibles > 1:
                    logger.info('Gauser con acceso a múltiples entidades.')
                    return render(request, "select_entidad.html", {'gauser_extras': gauser_extras, })
                elif entidades_disponibles == 1:
                    request.session["gauser_extra"] = gauser_extras[0]
                    request.session["ronda"] = request.session["gauser_extra"].ronda
                    request.session['num_items_page'] = 15
                    # Las dos siguientes líneas son para asegurar que gauss existe como usuario en cualquier entidad
                    gauss = Gauser.objects.get(username='gauss')
                    Gauser_extra.objects.get_or_create(gauser=gauss, ronda=request.session["ronda"], activo=True)
                    logger.info('%s se loguea en GAUSS.' % (request.session["gauser_extra"]))
                    return redirect(request.session['nexturl'])
                    # if request.session['nexturl']:
                    #     response = HttpResponse(status=302)
                    #     response['Location'] = request.session['nexturl']
                    # else:
                    #     return redirect(request.session['nexturl'])
                else:
                    logger.info('Gauser activo, pero no tiene asociada ninguna entidad.')
                    return render(request, "no_cuenta.html", {'usuario': user, })
            else:
                return render(request, "no_cuenta.html", {'usuario': user, })
        else:
            response = HttpResponse(status=302)
            response['Location'] = CAS_URL + 'login?service=' + request.session['service']
            return response
    elif request.method == 'POST':
        if request.POST['action'] == 'selecciona_entidad':
            request.session["gauser_extra"] = Gauser_extra.objects.get(pk=request.POST['gauser_extra'])
            request.session["ronda"] = request.session["gauser_extra"].ronda
            request.session['num_items_page'] = 15
            # Las dos siguientes líneas son para asegurar que gauss existe como usuario en cualquier entidad
            gauss = Gauser.objects.get(username='gauss')
            Gauser_extra.objects.get_or_create(gauser=gauss, ronda=request.session["ronda"], activo=True)
            logger.info('%s se loguea en GAUSS.' % (request.session["gauser_extra"]))
            return redirect(request.session['nexturl'])
def no_login(request):
    pag = request.GET['next']
    return render(request, "no_login.html", {'pag': pag, })


# ------------------------------------------------------------------#
# DEFINICIÓN DE FUNCIONES BÁSICAS
# ------------------------------------------------------------------#

# Crear el nombre de usuario a partir del nombre real
def crear_nombre_usuario(nombre, apellidos):
    # En primer lugar quitamos tildes, colocamos nombres en minúsculas y :
    nombre = ''.join(
        (c for c in unicodedata.normalize('NFD', smart_text(nombre)) if
         unicodedata.category(c) != 'Mn')).lower().split()
    apellidos = ''.join(
        (c for c in unicodedata.normalize('NFD', smart_text(apellidos)) if
         unicodedata.category(c) != 'Mn')).lower().split()
    iniciales_nombre = ''
    for parte in nombre:
        iniciales_nombre = iniciales_nombre + parte[0]
    try:
        iniciales_apellidos = apellidos[0]
    except:  # Estas dos líneas están para crear usuarios cuando no tienen apellidos
        iniciales_apellidos = 'sin'
    for ind in range(len(apellidos))[1:]:
        try:  # Por si acaso el usuario sólo tuviera un apellido:
            iniciales_apellidos = iniciales_apellidos + apellidos[ind][0]
        except IndexError:
            pass
    usuario = iniciales_nombre + iniciales_apellidos
    valid_usuario = False
    n = 1
    while valid_usuario == False:
        username = usuario + str(n)
        try:
            Gauser.objects.get(username=username)
            n += 1
        except:
            valid_usuario = True
    return username


def devuelve_fecha(string):
    DATE_FORMATS = ['%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y']
    for date_format in DATE_FORMATS:
        try:
            fecha = datetime.strptime(string, date_format)
            return fecha
        except:
            pass
    return datetime.strptime('01/01/1900', '%d/%m/%Y')


def get_provincia(p):  # Devuelve el código de la provincia cuyo nombre se parece más a la string p
    n_ps = [n[1] for n in PROVINCIAS]
    try:
        m = get_close_matches(p, n_ps, 1)[0]
        for n in PROVINCIAS:
            if n[1] == m:
                return n[0]
        return None
    except:
        return None


def create_usuario(datos, request, tipo):
    g_e = request.session['gauser_extra']
    dni = genera_nie(datos['dni' + tipo]) if len(datos['dni' + tipo]) > 6 else 'DNI inventado generar error en el try'
    try:
        gauser = Gauser.objects.get(dni=dni)
        logger.info('Existe Gauser con dni %s' % (dni))
    except ObjectDoesNotExist:
        logger.warning('No existe Gauser con dni %s' % (dni))
        try:
            gauser_extra = Gauser_extra.objects.get(id_entidad=datos['id_socio'], ronda=g_e.ronda)
            gauser = gauser_extra.gauser
            logger.warning('Encontrado Gauser y Gauser_extra con id_socio %s' % (datos['id_socio']))
        except ObjectDoesNotExist:
            gauser = None
            logger.warning('No existe Gauser con id_socio %s' % (datos['id_socio']))
        except MultipleObjectsReturned:
            gauser_extra = Gauser_extra.objects.filter(id_entidad=datos['id_socio'], ronda=g_e.ronda)[0]
            logger.warning('Existen varios Gauser_extra asociados al Gauser encontrado. Se elige %s' % (gauser_extra))
            gauser = gauser_extra.gauser
    except MultipleObjectsReturned:
        gauser = Gauser.objects.filter(dni=dni)[0]
        logger.warning('Existen varios Gauser con el mismo DNI. Se elige %s' % (gauser))

    if gauser:
        try:
            gauser_extra = Gauser_extra.objects.get(gauser=gauser, ronda=g_e.ronda)
            mensaje = 'Existe el g_e %s con el dni %s. No se vuelve a crear.' % (gauser, datos['dni' + tipo])
            logger.info(mensaje)
        except ObjectDoesNotExist:
            gauser_extra = None
            logger.warning('No existe Gauser_extra asociado al Gauser %s, deberemos crearlo' % (gauser))
        except MultipleObjectsReturned:
            ges = Gauser_extra.objects.filter(gauser=gauser, entidad=g_e.ronda.entidad, ronda=g_e.ronda.entidad.ronda)
            gauser_extra = ges[0]
            ges.exclude(id=gauser_extra.id).delete()
            logger.warning('Varios Gauser_extra asociados al Gauser %s, se borran todos menos uno.' % (gauser))
            mensaje = 'Varios Gauser_extra asociados al Gauser %s, se borran todos menos uno.' % (gauser)
            crear_aviso(request, False, mensaje)
    else:
        gauser_extra = None

    if not gauser:
        if datos['nombre' + tipo] and datos['apellidos' + tipo]:
            nombre = datos['nombre' + tipo]
            apellidos = datos['apellidos' + tipo]
            usuario = crear_nombre_usuario(nombre, apellidos)
            gauser = Gauser.objects.create_user(usuario, email=datos['email' + tipo].lower(),
                                                password=pass_generator(), last_login=timezone.now())
            gauser.first_name = string.capwords(nombre.title()[0:28])
            gauser.last_name = string.capwords(apellidos.title()[0:28])
            gdata = {'dni': dni, 'telfij': datos['telefono_fijo' + tipo], 'sexo': datos['sexo' + tipo],
                     'telmov': datos['telefono_movil' + tipo], 'localidad': datos['localidad' + tipo],
                     'address': datos['direccion' + tipo], 'provincia': get_provincia(datos['provincia' + tipo]),
                     'nacimiento': devuelve_fecha(datos['nacimiento' + tipo]), 'postalcode': datos['cp' + tipo],
                     'fecha_alta': devuelve_fecha(datos['fecha_alta' + tipo])}
            for key, value in gdata.items():
                setattr(gauser, key, value)
            gauser.save()
        else:
            mensaje = 'No se ha podido crear un usuario porque no se han indicado nombre y apellidos'
            crear_aviso(request, False, mensaje)
            logger.warning(mensaje)
    if gauser and not gauser_extra:
        if 'id_organizacion' + tipo in datos:
            id_organizacion = datos['id_organizacion' + tipo]
        else:
            id_organizacion = datos['id_socio' + tipo]
        gauser_extra = Gauser_extra.objects.create(gauser=gauser, entidad=g_e.ronda.entidad, ronda=g_e.ronda,
                                                   activo=True,
                                                   id_entidad=datos['id_socio' + tipo],
                                                   num_cuenta_bancaria=datos['iban' + tipo],
                                                   observaciones=datos['observaciones' + tipo],
                                                   id_organizacion=id_organizacion)
        try:
            asocia_banco_ge(gauser_extra)
        except:
            crear_aviso(request, False,
                        'El IBAN asociado a %s parece no ser correcto. No se ha podido asociar una entidad bancaria al mismo.' % (
                                gauser.first_name.decode('utf8') + ' ' + gauser.last_name.decode('utf8')))
    if gauser_extra:
        logger.info('antes de subentidades')
        if datos['subentidades' + tipo]:
            logger.info('entra en subentidades')
            # La siguientes dos líneas no se si funcionarán en python3 debido a que filter en python3 no devuelve
            # una lista. Incluida la conversión list() para evitar errores:
            # http://stackoverflow.com/questions/3845423/remove-empty-strings-from-a-list-of-strings
            subentidades_id = list(filter(None, datos['subentidades' + tipo].replace(' ', '').split(',')))
            logger.info('entra en subentidades %s' % subentidades_id)
            subentidades = Subentidad.objects.filter(id__in=subentidades_id, entidad=g_e.ronda.entidad,
                                                     fecha_expira__gt=datetime.today())
            gauser_extra.subentidades.add(*subentidades)
        if datos['perfiles' + tipo]:
            logger.info('entra en perfiles')
            cargos_id = list(filter(None, datos['perfiles' + tipo].replace(' ', '').split(',')))
            cargos = Cargo.objects.filter(id__in=cargos_id, entidad=g_e.ronda.entidad)
            gauser_extra.cargos.add(*cargos)

    if gauser_extra:
        Gauser_extra_estudios.objects.get_or_create(ge=gauser_extra)
    return gauser_extra


@permiso_required('acceso_carga_masiva')
def carga_masiva(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST':
        logger.info('Carga de archivo de tipo: ' + request.FILES['file_masivo'].content_type)
        ronda = request.session['gauser_extra'].ronda
        action = request.POST['action']
        if action == 'carga_masiva_csv':
            if 'csv' in request.FILES['file_masivo'].content_type:
                fichero = request.FILES['file_masivo']
                # if fichero.multiple_chunks():
                # csv_file = ''
                csv_file = ''
                for chunk in fichero.chunks():
                    # csv_file += chunk.decode('utf-8')
                    csv_file += chunk
                # fichero = csv.DictReader(io.StringIO(csv_file), delimiter=';')
                fichero = csv.DictReader(io.BytesIO(csv_file), delimiter=';')

                # fichero = csv.DictReader(csv_file, delimiter=';')
                # else:
                #
                #     ruta_nombre = "media/%s" % fichero.name
                #     csv_file = open(ruta_nombre, 'wb')
                #     for chunk in fichero.chunks():
                #         csv_file.write(chunk)
                #     csv_file = io.StringIO(csv_file)
                #     fichero = csv.DictReader(csv_file, delimiter=';')

                for row in fichero:
                    if len(row['id_socio']) > 2:
                        tutor1 = create_usuario(row, request, '_tutor1')
                        tutor2 = create_usuario(row, request, '_tutor2')
                        gauser_extra = create_usuario(row, request, '')
                        gauser_extra.tutor1 = tutor1
                        gauser_extra.tutor2 = tutor2
                        gauser_extra.save()
        if action == 'carga_masiva_racima':
            if 'excel' in request.FILES['file_masivo'].content_type:
                CargaMasiva.objects.create(ronda=g_e.ronda, fichero=request.FILES['file_masivo'], tipo='EXCEL')
                carga_masiva_from_excel.apply_async(expires=300)
                crear_aviso(request, False, 'El archivo cargado puede tardar unos minutos en ser procesado.')
        else:
            crear_aviso(request, False, 'El archivo cargado no tiene el formato adecuado.')

    return render(request, "carga_masiva.html",
                  {
                      'iconos': ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                                  'title': 'Subir el archivo a GAUSS',
                                  'permiso': 'acceso_carga_masiva'}, {}),
                      'formname': 'carga_masiva',
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


class Gauser_per_Form(ModelForm):
    class Meta:
        model = Gauser_extra
        fields = ('permisos', 'cargos')


@permiso_required('acceso_perfiles_permisos')
def perfiles_permisos(request):
    g_e = request.session['gauser_extra']
    usuarios = Gauser_extra.objects.filter(ronda=g_e.ronda).distinct()
    gauser_extra = usuarios[0]
    form = Gauser_per_Form(instance=gauser_extra)
    if request.is_ajax() and request.method == 'POST':
        action = request.POST['action']
        if action == 'add_cargo' and g_e.has_permiso('asigna_perfiles'):
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
            ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge'])
            ge.cargos.add(cargo)
            permisos_cargo = dict(ge.cargos.all().values_list('permisos__id', 'permisos__id'))
            return JsonResponse(permisos_cargo)
        elif action == 'del_cargo' and g_e.has_permiso('asigna_perfiles'):
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
            ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge'])
            ge.cargos.remove(cargo)
            permisos_cargo = dict(ge.cargos.all().values_list('permisos__id', 'permisos__id'))
            return JsonResponse(permisos_cargo)
        elif action == 'add_permiso' and g_e.has_permiso('asigna_permisos'):
            permiso = Permiso.objects.get(id=request.POST['permiso'])
            ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge'])
            ge.permisos.add(permiso)
            return HttpResponse(True)
        elif action == 'del_permiso' and g_e.has_permiso('asigna_permisos'):
            permiso = Permiso.objects.get(id=request.POST['permiso'])
            ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge'])
            ge.permisos.remove(permiso)
            return HttpResponse(True)
        elif action == 'change_nombre' and g_e.has_permiso('modifica_texto_menu'):
            menu = Menu.objects.get(entidad=g_e.ronda.entidad, id=request.POST['menu'])
            menu.texto_menu = request.POST['nombre']
            menu.save()
            return JsonResponse({'texto_menu': menu.texto_menu})
        elif action == 'change_pos' and g_e.has_permiso('modifica_pos_menu'):
            menu = Menu.objects.get(entidad=g_e.ronda.entidad, id=request.POST['menu'])
            nivel = menu.menu_default.nivel
            menus_nivel = Menu.objects.filter(entidad=g_e.ronda.entidad, menu_default__nivel=nivel,
                                              menu_default__parent=menu.menu_default.parent)
            new_pos = min(int(request.POST['pos']), menus_nivel.count())
            menus = menus_nivel.exclude(id=menu.id)
            cambiado = False
            n = 1
            for m in menus:
                if n == new_pos:
                    menu.pos = new_pos
                    menu.save()
                    n += 1
                    cambiado = True
                m.pos = n
                m.save()
                n += 1
            if not cambiado:
                menu.pos = new_pos
                menu.save()
            menus = dict(Menu.objects.filter(entidad=g_e.ronda.entidad, menu_default__nivel=nivel,
                                             menu_default__parent=menu.menu_default.parent).values_list('id', 'pos'))
            return JsonResponse(menus)

    elif request.method == 'POST':
        crear_aviso(request, True, 'Entra en ' + request.META['PATH_INFO'] + ' POST action: ' + request.POST['action'])
        if request.POST['action'] == 'gauser_extra_selected':
            gauser_extra = Gauser_extra.objects.get(id=request.POST['gauser_extra_selected'])
            form = Gauser_per_Form(instance=gauser_extra)

        if request.POST['action'] == 'aceptar':
            gauser_extra = Gauser_extra.objects.get(id=request.POST['gauser_extra_selected'])
            form = Gauser_per_Form(request.POST, instance=gauser_extra)
            if form.is_valid():
                form.save()

    menus = Menu.objects.filter(entidad=g_e.ronda.entidad, menu_default__nivel=1).order_by('pos')

    respuesta = {
        'formname': 'permisos_perfiles',
        'form': form,
        'iconos':
            ({'tipo': 'search', 'title': 'Buscar usuario por nombre', 'permiso': 'acceso_perfiles_permisos'},
             {'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
              'title': 'Aceptar los cambios realizados', 'permiso': 'asigna_permisos'},
             ),
        'gauser_extra': gauser_extra,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
        'cargos': Cargo.objects.filter(entidad=g_e.ronda.entidad).order_by('nivel'),
        'g_e': g_e,
        'menus': menus,
    }
    return render(request, "perfiles_permisos.html", respuesta)


@login_required()
def politica_privacidad(request):
    return render(request, "politica_privacidad.html", {})


@login_required()
def aviso_legal(request):
    return render(request, "aviso_legal.html", {})


@permiso_required('acceso_perfiles_permisos34')
def del_entidad_gausers(request):
    g_e = request.session['gauser_extra']
    gauser = g_e.gauser
    if g_e.gauser.username == 'gauss':
        if request.method == 'POST':
            if request.POST['action'] == 'borrar_entidad' and request.POST['pass'] == 'jucarihu':
                entidad = Entidad.objects.get(id=request.POST['entidad'])
                ges = Gauser_extra.objects.filter(ronda__entidad=entidad)
                for ge in ges:
                    g = ge.gauser
                    ge.delete()
                    otros_ge = Gauser_extra.objects.filter(gauser=g)
                    if otros_ge.count() == 0:
                        if g.username == 'gauss' or g.username == 'jjmartinr01':
                            crear_aviso(request, False, 'Intenta borrar a %s' % (g.username))
                        else:
                            g.delete()
                entidad.delete()
        entidades = Entidad.objects.all()
        return render(request, "del_entidad_gausers.html",
                      {
                          'formname': 'del_entidad_gausers',
                          'iconos':
                              ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                                'title': 'Eliminar la entidad y usuarios asociados', 'permiso': 'libre'},
                               ),
                          'entidades': entidades,
                      })
    else:
        return render(request, "no_cuenta.html", {'usuario': gauser, })


def recupera_password(request):
    if request.method == 'GET' and 'id' in request.GET:
        enlaces = Enlace.objects.filter(code=request.GET['id'])
        if enlaces.count() == 1:
            if enlaces[0].deadline >= date.today():
                return render(request, "cambia_password.html", {'enlace': enlaces[0], 'formulario': True})
            else:
                mensaje = 'El enlace se ha caducado. Solicita de nuevo un cambio de contraseña.'
        else:
            mensaje = 'El identificador es erróneo. ¿Has copiado correctamente la url enviada a tu correo?'
    elif request.method == 'POST' and 'action' in request.POST:
        if request.POST['action'] == 'cambia_password':
            if request.POST['passusuario1'] == request.POST['passusuario2'] and request.POST['passusuario1'] != '':
                enlace = Enlace.objects.get(code=request.POST['id'])
                enlace.usuario.set_password(request.POST['passusuario1'])
                enlace.usuario.save()
                mensaje = 'Contraseña cambiada correctamente'
    else:
        mensaje = 'Se ha producido un error y este enlace no es correcto.'

    return render(request, "cambia_password.html", {'formulario': False, 'mensaje': mensaje})


# def acceso_from_racima(request, token):
#     acceso_encriptado = token.encode('utf-8')
#     try:
#         f = Fernet(RACIMA_KEY)
#         utc_token_timestamp = f.extract_timestamp(acceso_encriptado) # timestamp UTC del momento en que fue creado
#         now = datetime.now()
#         # utc_now_timestamp = now.replace(tzinfo=timezone.utc).timestamp()
#         utc_now_timestamp = now.timestamp()
#         segundos_retraso = utc_now_timestamp - utc_token_timestamp
#         acceso = f.decrypt(acceso_encriptado).decode()
#         return HttpResponse("Diferencia en segundos: %s<br><br>Acceso: %s" %(segundos_retraso, acceso))
#     except:
#         return HttpResponse("No está instalado el paquete cryptography")


# ------------------------------------------------------------------#
# DEFINICIÓN DE FUNCIÓN PARA
# ------------------------------------------------------------------#

def getloginlink(request, entidad_code, usuario, passusuario):
    try:
        entidad = Entidad.objects.get(code=entidad_code)
        user = authenticate(username=usuario, password=passusuario)
        logger.info('getloginlink usuario %s con su contraseña' % user)
        if user is not None:
            if user.is_active:
                gauser_extra = Gauser_extra.objects.get(gauser=user, activo=True, ronda=entidad.ronda)
                code = pass_generator(size=39)
                expiration = timezone.now() + timedelta(seconds=100)
                enlace = Enlace.objects.create(usuario=user, code=code, deadline=expiration, expiration=expiration,
                                               enlace=gauser_extra.id)
                data = {'id': enlace.enlace, 'token': enlace.code}
                return HttpResponse('loginlink(%s)' % json.dumps(data))
    except:
        data = {'id': None, 'token': 'error'}
        return HttpResponse('loginlink(%s)' % json.dumps(data))

def loginlink(request, id, token):
    try:
        enlace = Enlace.objects.get(enlace=id, code=token, expiration__gte=timezone.now())
        g_e = Gauser_extra.objects.get(id=enlace.enlace, gauser=enlace.usuario)
        if enlace.usuario.is_active:
            enlace.usuario.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, enlace.usuario)
            request.session['gauser_extra'] = g_e
            request.session['num_items_page'] = 15
            request.session['ronda'] = g_e.ronda
            logger.info('%s se loguea en GAUSS a través de un enlace' % g_e.gauser.get_full_name())
            return redirect('/calendario/')
        else:
            logger.info('%s no se puede loguear en GAUSS. Su usuario no está activo' % g_e.gauser.get_full_name())
            return redirect('/')
    except:
        logout(request)
        return redirect('/')

# ------------------------------------------------------------------#
# DEFINICIÓN DE FUNCIONES PARA ACTUALIZAR GAUSS
# ------------------------------------------------------------------#

@gauss_required
def execute_migrations(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax() and g_e.gauser.username == 'gauss':
        mensajes = ''
        errores = ''
        exec_git_pull = ['git', '--git-dir=%s/.git' % RUTA_BASE_SETTINGS, 'pull', 'origin', 'master']
        exec_makemigrations = ['python', '%s/manage.py' % RUTA_BASE_SETTINGS, 'makemigrations']
        exec_migrate = ['python', '%s/manage.py' % RUTA_BASE_SETTINGS, 'migrate']
        exec_apache_restart = 'sudo /etc/init.d/apache2 restart'
        if request.POST['exec_git_pull'] == 'true':
            # result = subprocess.run([exec_git_pull], stdout=subprocess.PIPE)
            result = subprocess.run([exec_git_pull], capture_output=True)
            return JsonResponse({'mensajes': mensajes, 'errores': errores, 'ok': True})
            mensajes += result.stdout.decode('utf-8')
            errores += result.stderr.decode('utf-8')
        if request.POST['exec_makemigrations'] == '1':
            result = subprocess.run([exec_makemigrations], stdout=subprocess.PIPE)
            mensajes += result.stdout
            errores += result.stderr
        if request.POST['exec_migrate'] == '1':
            result = subprocess.run([exec_migrate], stdout=subprocess.PIPE)
            mensajes += result.stdout
            errores += result.stderr
        if request.POST['exec_apache_restart'] == '1':
            result = subprocess.run([exec_apache_restart], stdout=subprocess.PIPE)
            mensajes += result.stdout
            errores += result.stderr
        return JsonResponse({'mensajes': mensajes, 'errores': errores, 'ok': True})
    else:
        return render(request, "execute_migrations.html")

# --------------------------------------------------------------------------#
# DEFINICIÓN DE FUNCIONES ACTUALIZAR MENUS Y PERMISOS EN ENTIDADES Y CARGOS
# --------------------------------------------------------------------------#

@gauss_required
def configurar_cargos_permisos(request):
    ejecutar_configurar_cargos_permisos.apply_async(expires=300)
    return HttpResponse('Esta operación puede requerir varios minutos')

@gauss_required
def configurar_menus_centros_educativos(request):
    ejecutar_configurar_menus_centros_educativos.apply_async(expires=300)
    return HttpResponse('Esta operación puede requerir varios minutos')

@gauss_required
def configurar_docs_conf_educarioja(request):
    ejecutar_configurar_docs_conf_educarioja.apply_async(expires=300)
    return HttpResponse('Esta operación puede requerir varios minutos')