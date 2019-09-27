# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unicodedata
import csv
import logging
import string
import io
import os
import time
import subprocess
import xlrd  # Permite leer archivos xls
# from urllib import unquote
from difflib import get_close_matches
import simplejson as json
from datetime import date, datetime, timedelta
from time import sleep
from django.shortcuts import render, redirect
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.template import RequestContext
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django import forms
from django.forms import ModelForm
from django.utils import translation, timezone
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.utils.encoding import smart_text
from gauss.rutas import *
from gauss.constantes import PROVINCIAS
from gauss.funciones import usuarios_de_gauss, pass_generator
from gauss.settings import RUTA_BASE_SETTINGS
from estudios.models import Grupo, Gauser_extra_estudios
from autenticar.models import Enlace, Permiso, Gauser, Menu_default  # , Candidato
from entidades.models import Subentidad, Cargo, Entidad, Gauser_extra, Menu, Subsubentidad, ConfigurationUpdate, Ronda, Reserva_plaza
from mensajes.views import crear_aviso, crea_mensaje_cola
from mensajes.models import Aviso, Mensaje
from bancos.views import asocia_banco_ge
from autenticar.control_acceso import LogGauss, permiso_required, gauss_required
from captcha.fields import CaptchaField

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
                    gauser_comodin = Gauser.objects.get(username='qazwsxedcrfvtgbyhnujmikolp')
                except:
                    ahora = datetime.now()
                    gauser_comodin = Gauser.objects.create(username='qazwsxedcrfvtgbyhnujmikolp', last_login=ahora)
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
                                      'foto': None, 'tutor1': None, 'tutor2': None, 'ocupacion': None, 'banco': None,
                                      'entidad_bancaria': None, 'num_cuenta_bancaria': None, 'clave_ex': None,
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
                                      'foto': None, 'tutor1': None, 'tutor2': None, 'ocupacion': None, 'banco': None,
                                      'entidad_bancaria': None, 'num_cuenta_bancaria': None, 'clave_ex': None,
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
        logger.info(u'%s, acceso denegado a %s desde %s' % (g_e, request.path_info, ip))
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
                logger.info(u'%s se loguea en GAUSS a través de un enlace' % (full_name))
                return render(request, "enlazar.html", {'page': enlace.enlace})
            else:
                logger.info(u'%s no se puede loguear en GAUSS a través de un enlace caducado' % (full_name))
                return render(request, "no_enlace.html", {'usuario': enlace.usuario, })
        else:
            logger.info(u'%s no se puede loguear en GAUSS. Su usuario no está activo' % (full_name))
            return render(request, "no_cuenta.html", {'usuario': enlace.usuario, })
    except:
        logout(request)
        form = CaptchaForm()
        return render(request, "autenticar.html", {'form': form, 'email': 'aaa@aaa', 'tipo': 'acceso'})


##########################################################################
###############  PÁGINA DE ACCESO

@LogGauss
def index(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    dominio = request.META['HTTP_HOST'].split('.')[0]
    entidad = Entidad.objects.filter(dominio=dominio)

    #############################################################################
    # Las siguientes líneas son para entrar en nuevo gauss a través de gauss_educa:
    if request.method == 'GET':
        if 'p' in request.GET and 'u' in request.GET:
            p = request.GET['p']
            u = request.GET['u']
            # user = Gauser.objects.get(username=u, password=p)
            user = authenticate(username=u, password=p)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    request.session["hoy"] = datetime.today()
                    request.session[translation.LANGUAGE_SESSION_KEY] = user_language
                    # Identificación de la entidad en el que está el usuario:
                    gauser_extras = Gauser_extra.objects.filter(Q(gauser=user) & Q(activo=True))
                    g_cs = gauser_extras
                    entidades_disponibles = 0
                    for gauser_extra in g_cs:
                        if gauser_extra.ronda == gauser_extra.ronda.entidad.ronda:
                            entidades_disponibles += 1
                        else:
                            gauser_extras = gauser_extras.exclude(pk=gauser_extra.id)
                    if entidades_disponibles > 1:
                        logger.info(u'Gauser con acceso a múltiples entidades.')
                        return render(request, "select_entidad.html", {'gauser_extras': gauser_extras, })
                    elif entidades_disponibles == 1:
                        request.session["gauser_extra"] = gauser_extras[0]
                        request.session["ronda"] = request.session["gauser_extra"].ronda
                        request.session['num_items_page'] = 15
                        logger.info(u'%s se loguea en GAUSS.' % (request.session["gauser_extra"]))
                        usernombre = request.session['gauser_extra'].gauser.username
                        # if request.session['gauser_extra'].ronda.entidad.id in [14, 16] and usernombre != 'jjmartinr01':
                        #     return render(request, "enlace_gauss_larioja_org.html")
                        return redirect('/calendario/')
                    else:
                        logger.info(u'Gauser activo, pero no tiene asociada ninguna entidad.')
                        return render(request, "no_cuenta.html", {'usuario': user, })
                else:
                    return render(request, "no_cuenta.html", {'usuario': user, })
            else:
                sleep(3)
                logger.info(u'Usuario: %s, no reconocido. Intenta acceso desde %s' % (u, ip))
                logout(request)
                form = CaptchaForm()
                return render(request, "autenticar.html", {'form': form, 'email': 'aaa@aaa', 'tipo': 'acceso'})
    #############################################################################
    #############################################################################

    if request.method == 'POST':
        # return render(request, "temporalmente_inactivo.html")
        if request.POST['action'] == 'acceso':
            usuario = request.POST['usuario']
            passusuario = request.POST['passusuario']
            user = authenticate(username=usuario, password=passusuario)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    request.session["hoy"] = datetime.today()
                    request.session[translation.LANGUAGE_SESSION_KEY] = user_language
                    # Identificación de la entidad en el que está el usuario:
                    gauser_extras = Gauser_extra.objects.filter(Q(gauser=user) & Q(activo=True))
                    g_cs = gauser_extras
                    entidades_disponibles = 0
                    for gauser_extra in g_cs:
                        if gauser_extra.ronda == gauser_extra.ronda.entidad.ronda:
                            entidades_disponibles += 1
                        else:
                            gauser_extras = gauser_extras.exclude(pk=gauser_extra.id)
                    if entidades_disponibles > 1:
                        logger.info(u'Gauser con acceso a múltiples entidades.')
                        return render(request, "select_entidad.html", {'gauser_extras': gauser_extras, })
                    elif entidades_disponibles == 1:
                        request.session["gauser_extra"] = gauser_extras[0]
                        request.session["ronda"] = request.session["gauser_extra"].ronda
                        request.session['num_items_page'] = 15
                        logger.info(u'%s se loguea en GAUSS.' % (request.session["gauser_extra"]))
                        usernombre = request.session['gauser_extra'].gauser.username
                        # if request.session['gauser_extra'].ronda.entidad.id in [14, 16] and usernombre != 'jjmartinr01':
                        #     return render(request, "enlace_gauss_larioja_org.html")
                        return redirect('/calendario/')
                    else:
                        logger.info(u'Gauser activo, pero no tiene asociada ninguna entidad.')
                        return render(request, "no_cuenta.html", {'usuario': user, })
                else:
                    return render(request, "no_cuenta.html", {'usuario': user, })
            else:
                sleep(3)
                logger.info(u'Usuario: %s, no reconocido. Intenta acceso desde %s' % (usuario, ip))
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
                    texto_mail = render_to_string("mail_recupera_password.html", {'enlaces': enlaces},
                                                  request=request)
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
            logger.info(u'%s se loguea en GAUSS.' % (request.session["gauser_extra"]))
            usernombre = request.session['gauser_extra'].gauser.username
            # if request.session['gauser_extra'].ronda.entidad.id in [14, 16] and usernombre != 'jjmartinr01':
            #     return render(request, "enlace_gauss_larioja_org.html")
            return redirect('/calendario/')

            # elif len(entidad) > 0:
            # tw = Template_web.objects.filter(entidad=entidad, home=True)[0]
            # template_webs = Template_web.objects.filter(entidad=entidad)
            # if hasattr(tw, 't_blog'):
            # pag = tw.t_blog
            # categorias = Cate_Blog.objects.filter(entidad=entidad)
            # data = render_to_string('blog.html',
            #                        {'pag': pag, 'template_webs': template_webs, 'categorias': categorias
            #                        }, request=request)
            #     elif hasattr(tw, 't_banded'):
            #         pag = tw.t_banded
            #         data = render_to_string('banded.html', {'pag': pag, 'template_webs': template_webs},
            #                                 request=request)
            #     return HttpResponse(data)
    else:
        logout(request)
        form = CaptchaForm()
        return render(request, "autenticar.html", {'form': form, 'email': 'aaa@aaa', 'tipo': 'acceso'})


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
            user = Gauser.objects.get(username=username)
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
    dni = datos['dni' + tipo] if len(datos['dni' + tipo]) > 6 else 'DNI inventado para generar error en el try'
    try:
        gauser = Gauser.objects.get(dni=dni)
        logger.info('Existe Gauser con dni %s' % (dni))
    except ObjectDoesNotExist:
        logger.warning('No existe Gauser con dni %s' % (dni))
        try:
            gauser_extra = Gauser_extra.objects.get(id_entidad=datos['id_socio'], entidad=g_e.ronda.entidad)
            gauser = gauser_extra.gauser
            logger.warning('Encontrado Gauser y Gauser_extra con id_socio %s' % (datos['id_socio']))
        except ObjectDoesNotExist:
            gauser = None
            logger.warning('No existe Gauser con id_socio %s' % (datos['id_socio']))
        except MultipleObjectsReturned:
            gauser_extra = Gauser_extra.objects.filter(id_entidad=datos['id_socio'], entidad=g_e.ronda.entidad)[0]
            logger.warning('Existen varios Gauser_extra asociados al Gauser encontrado. Se elige %s' % (gauser_extra))
            gauser = gauser_extra.gauser
    except MultipleObjectsReturned:
        gauser = Gauser.objects.filter(dni=dni)[0]
        logger.warning('Existen varios Gauser con el mismo DNI. Se elige %s' % (gauser))

    if gauser:
        try:
            gauser_extra = Gauser_extra.objects.get(gauser=gauser, entidad=g_e.ronda.entidad,
                                                    ronda=g_e.ronda.entidad.ronda)
            mensaje = u'Existe el g_e %s con el dni %s. No se vuelve a crear.' % (gauser, datos['dni' + tipo])
            logger.info(mensaje)
        except ObjectDoesNotExist:
            gauser_extra = None
            logger.warning('No existe Gauser_extra asociado al Gauser %s, deberemos crearlo' % (gauser))
        except MultipleObjectsReturned:
            ges = Gauser_extra.objects.filter(gauser=gauser, entidad=g_e.ronda.entidad, ronda=g_e.ronda.entidad.ronda)
            gauser_extra = ges[0]
            ges.exclude(id=gauser_extra.id).delete()
            logger.warning('Varios Gauser_extra asociados al Gauser %s, se borran todos menos uno.' % (gauser))
            mensaje = u'Varios Gauser_extra asociados al Gauser %s, se borran todos menos uno.' % (gauser)
            crear_aviso(request, False, mensaje)
    else:
        gauser_extra = None

    if not gauser:
        if datos['nombre' + tipo] and datos['apellidos' + tipo]:
            nombre = datos['nombre' + tipo]
            apellidos = datos['apellidos' + tipo]
            usuario = crear_nombre_usuario(nombre, apellidos)
            gauser = Gauser.objects.create_user(usuario, email=datos['email' + tipo].lower(),
                                                password=datos['dni' + tipo], last_login=timezone.now())
            gauser.first_name = string.capwords(nombre.title()[0:28])
            gauser.last_name = string.capwords(apellidos.title()[0:28])
            gdata = {'dni': datos['dni' + tipo], 'telfij': datos['telefono_fijo' + tipo], 'sexo': datos['sexo' + tipo],
                     'telmov': datos['telefono_movil' + tipo], 'localidad': datos['localidad' + tipo],
                     'address': datos['direccion' + tipo], 'provincia': get_provincia(datos['provincia' + tipo]),
                     'nacimiento': devuelve_fecha(datos['nacimiento' + tipo]), 'postalcode': datos['cp' + tipo],
                     'fecha_alta': devuelve_fecha(datos['fecha_alta' + tipo])}
            for key, value in gdata.items():
                setattr(gauser, key, value)
            gauser.save()
        else:
            mensaje = u'No se ha podido crear un usuario porque no se han indicado nombre y apellidos'
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
                        u'El IBAN asociado a %s parece no ser correcto. No se ha podido asociar una entidad bancaria al mismo.' % (
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


# @permiso_required('acceso_carga_masiva')
def carga_masiva(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST':
        logger.info(u'Carga de archivo de tipo: ' + request.FILES['file_masivo'].content_type)
        ronda = request.session['gauser_extra'].ronda
        action = request.POST['action']
        if action == 'carga_masiva_csv':
            if 'csv' in request.FILES['file_masivo'].content_type:
                fichero = request.FILES['file_masivo']
                # if fichero.multiple_chunks():
                # csv_file = u''
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
                book = xlrd.open_workbook(file_contents=request.FILES['file_masivo'].read())
                sheet = book.sheet_by_index(0)
                # Get the keys from line 5 of excel file:
                keys0 = [sheet.cell(4, col_index).value for col_index in range(sheet.ncols)]
                # Get the keys removing accents:
                # keys = [filter(lambda x: x in set(string.printable), k) for k in keys0]
                keys = keys0
                # Join the two earlier lines in one:
                # kk = [filter(lambda x: x in set(string.printable), sheet.cell(4, col_index).value) for col_index in xrange(sheet.ncols)]

                # Keys Reference for Personal:
                krp = {'Empleado': 'empleado', 'DNI/Pasaporte': 'dni', 'Tipo de personal': 'subentidades',
                       'Puesto': 'perfiles',
                       'Fecha de nacimiento': 'nacimiento', 'Activo': 'activo',
                       'Fecha del último nombramiento': 'fecha_alta',
                       'Fecha de cese': 'baja', 'Dirección': 'direccion', 'Código Postal': 'cp', 'Sexo': 'sexo',
                       'Localidad': 'localidad', 'Provincia': 'provincia', 'Teléfono 1': 'telefono_fijo',
                       'Teléfono 2': 'telefono_movil', 'Correo electrónico': 'email', 'Especialidad': 'especialidad'}
                pdic = {'empleado': '', 'dni': '', 'subentidades': '', 'perfiles': '', 'nacimiento': '', 'activo': '',
                        'fecha_alta': '', 'baja': '', 'direccion': '', 'cp': '', 'sexo': '', 'localidad': '',
                        'iban': '',
                        'provincia': '', 'telefono_fijo': '', 'telefono_movil': '', 'email': '', 'especialidad': ''}
                # Keys Reference for Alumnos:
                kra = {'Alumno': 'alumno', 'Estado Matrícula': 'estado_matricula', 'Nº id. Racima': 'id_socio',
                       'DNI/Pasaporte': 'dni', 'Dirección': 'direccion', 'Código postal': 'cp',
                       'Localidad de residencia': 'localidad', 'Fecha de nacimiento': 'nacimiento',
                       'Provincia de residencia': 'provincia', 'Teléfono': 'telefono_fijo',
                       'Teléfono móvil': 'telefono_movil',
                       'Correo electrónico': 'email', 'Curso': 'curso', 'Nº historial académico': 'id_organizacion',
                       'Grupo': 'subentidades', 'Primer apellido': 'last_name1', 'Segundo apellido': 'last_name2',
                       'Nombre': 'nombre', 'DNI/Pasaporte Primer tutor': 'dni_tutor1',
                       'Primer apellido Primer tutor': 'last_name1_tutor1',
                       'Segundo apellido Primer tutor': 'last_name2_tutor1', 'Nombre Primer tutor': 'nombre_tutor1',
                       'Tfno. Primer tutor': 'telefono_fijo_tutor1',
                       'Tfno. Móvil Primer tutor': 'telefono_movil_tutor1',
                       'Sexo Primer tutor': 'sexo_tutor1', 'DNI/Pasaporte Segundo tutor': 'dni_tutor2',
                       'Primer apellido Segundo tutor': 'last_name1_tutor2',
                       'Segundo apellido Segundo tutor': 'last_name2_tutor2',
                       'Nombre Segundo tutor': 'nombre_tutor2', 'Tfno. Segundo tutor': 'telefono_fijo_tutor2',
                       'Tfno. Móvil Segundo tutor': 'telefono_movil_tutor2', 'Sexo Segundo tutor': 'sexo_tutor2',
                       'Localidad de nacimiento': 'localidad_nacimiento', 'Nacionalidad': 'nacionalidad',
                       'Código País nacimiento': 'code_pais_nacimiento', 'País de nacimiento': 'pais_nacimiento',
                       'Código Provincia nacimiento': 'code_provincia_nacimiento',
                       'Pago   Seguro escolar': 'pago_seguro_escolar', 'Sexo': 'sexo',
                       'Año de la matrícula': 'year_matricula', 'Nº de matrículas en este curso': 'num_matriculas',
                       'Observaciones de la matrícula': 'observaciones_matricula', 'Número SS': 'num_ss',
                       'Nº expte. en el centro': 'num_exp', 'Fecha de la matrícula': 'fecha_matricula',
                       'Nº de matrículas en el expediente': 'num_matriculas_exp',
                       'Repeticiones en el curso': 'rep_curso',
                       'Familia numerosa': 'familia_numerosa', 'Lengua materna': 'lengua_materna',
                       'Año incorporación al sistema educativo': 'year_incorporacion', 'Bilingüe': 'bilingue',
                       'Correo electrónico Primer tutor': 'email_tutor1',
                       'Correo electrónico Segundo tutor': 'email_tutor2',
                       'Autoriza el uso de imagenes': 'uso_imagenes'}

                adic = {'alumno': '', 'estado_matricula': '', 'id_socio': '', 'dni': '', 'direccion': '', 'cp': '',
                        'localidad': '', 'nacimiento': '', 'provincia': '', 'telefono_fijo': '', 'telefono_movil': '',
                        'email': '', 'curso': '', 'id_organizacion': '', 'subentidades': '', 'last_name1': '',
                        'last_name2': '', 'nombre': '', 'dni_tutor1': '', 'last_name1_tutor1': '',
                        'last_name2_tutor1': '', 'nombre_tutor1': '', 'telefono_fijo_tutor1': '', 'fecha_alta': '',
                        'telefono_movil_tutor1': '', 'sexo_tutor1': '', 'dni_tutor2': '', 'last_name1_tutor2': '',
                        'last_name2_tutor2': '', 'nombre_tutor2': '', 'telefono_fijo_tutor2': '', 'perfiles': '',
                        'telefono_movil_tutor2': '', 'sexo_tutor2': '', 'localidad_nacimiento': '', 'nacionalidad': '',
                        'code_pais_nacimiento': '', 'pais_nacimiento': '', 'code_provincia_nacimiento': '',
                        'pago_seguro_escolar': '', 'sexo': '', 'year_matricula': '', 'num_matriculas': '',
                        'observaciones_matricula': '', 'num_ss': '', 'num_exp': '', 'fecha_matricula': '',
                        'num_matriculas_exp': '', 'rep_curso': '', 'familia_numerosa': '', 'lengua_materna': '',
                        'year_incorporacion': '', 'bilingue': '', 'email_tutor1': '', 'email_tutor2': '', 'iban': '',
                        'localidad_tutor1': '', 'localidad_tutor2': '', 'direccion_tutor1': '', 'direccion_tutor2': '',
                        'cp_tutor1': '', 'cp_tutor2': '', 'nacimiento_tutor1': '', 'nacimiento_tutor2': '',
                        'provincia_tutor1': '', 'provincia_tutor2': '', 'iban_tutor1': '', 'iban_tutor2': '',
                        'id_socio_tutor1': '', 'id_socio_tutor2': '', 'fecha_alta_tutor1': '', 'fecha_alta_tutor2': '',
                        'observaciones_tutor1': '', 'observaciones_tutor2': '',
                        'perfiles_tutor1': '', 'perfiles_tutor2': '', }

                if len(keys) < 30:  # This implies the file is from Personal (RegInfPerCen.xls)
                    for row_index in range(5, sheet.nrows):
                        d = pdic
                        # d = {krp[keys[col_index]]: sheet.cell(row_index, col_index).value for col_index in
                        #      xrange(sheet.ncols)}
                        for col_index in range(sheet.ncols):
                            d[krp[keys[col_index]]] = sheet.cell(row_index, col_index).value
                        d['apellidos'] = d['empleado'].split(', ')[0]
                        d['nombre'] = d['empleado'].split(', ')[1]
                        d['id_socio'] = d['dni']
                        clave_ex = d['subentidades'].replace(' ', '_').lower()

                        sub1s = Subentidad.objects.filter(entidad=g_e.ronda.entidad, clave_ex=clave_ex)
                        if sub1s.count() > 0:
                            sub1 = sub1s[0]
                        else:
                            sub1 = Subentidad.objects.create(nombre=d['subentidades'], mensajes=True, edad_min=18,
                                                             entidad=g_e.ronda.entidad, clave_ex=clave_ex, edad_max=67)
                        # try:
                        #     sub1 = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex=clave_ex)
                        # except:
                        #     sub1 = Subentidad.objects.create(nombre=d['subentidades'], mensajes=True, edad_min=18,
                        #                                      entidad=g_e.ronda.entidad, clave_ex=clave_ex, edad_max=67)

                        sub2s = Subentidad.objects.filter(nombre=d['perfiles'], entidad=g_e.ronda.entidad)
                        if sub2s.count() > 0:
                            sub2 = sub2s[0]
                        else:
                            sub2 = Subentidad.objects.create(nombre=d['perfiles'], mensajes=True, edad_min=18,
                                                             edad_max=67, entidad=g_e.ronda.entidad, parent=sub1)
                        # try:
                        #     sub2 = Subentidad.objects.get(nombre=d['perfiles'], entidad=g_e.ronda.entidad)
                        # except:
                        #     sub2 = Subentidad.objects.create(nombre=d['perfiles'], mensajes=True, edad_min=18,
                        #                                      edad_max=67, entidad=g_e.ronda.entidad, parent=sub1)
                        cargo = Cargo.objects.get_or_create(entidad=g_e.ronda.entidad, cargo=d['subentidades'])
                        d['subentidades'] = str(sub1.id) + ',' + str(sub2.id)
                        d['activo'] = True if 'S' in d['activo'] else False
                        d['perfiles'] = str(cargo[0].id)
                        d['observaciones'] = d['especialidad'] + '<br>Causa baja el ' + d['baja']
                        create_usuario(d, request, '')
                else:
                    fecha_expira = g_e.ronda.entidad.ronda.fin + timedelta(days=5)  # Expiración para los grupos
                    subas = Subentidad.objects.filter(clave_ex='alumnos', entidad=g_e.ronda.entidad)
                    if subas.count() > 0:
                        suba = subas[0]
                    else:
                        suba = Subentidad.objects.create(nombre='Alumnos', mensajes=True, clave_ex='alumnos',
                                                         entidad=g_e.ronda.entidad, edad_min=12, edad_max=67)
                    # try:
                    #     suba = Subentidad.objects.get(clave_ex='alumnos', entidad=g_e.ronda.entidad)
                    # except:
                    #     suba = Subentidad.objects.create(nombre='Alumnos', mensajes=True, clave_ex='alumnos',
                    #                                      entidad=g_e.ronda.entidad, edad_min=12, edad_max=67)

                    subps = Subentidad.objects.filter(clave_ex='madres_padres', entidad=g_e.ronda.entidad)
                    if subps.count() > 0:
                        subp = subps[0]
                    else:
                        subp = Subentidad.objects.create(nombre='Madres/Padres', mensajes=True,
                                                         entidad=g_e.ronda.entidad,
                                                         clave_ex='madres_padres', edad_min=18, edad_max=67)
                    # try:
                    #     subp = Subentidad.objects.get(clave_ex='madres_padres', entidad=g_e.ronda.entidad)
                    # except:
                    #     subp = Subentidad.objects.create(nombre='Madres/Padres', mensajes=True, entidad=g_e.ronda.entidad,
                    #                                      clave_ex='madres_padres', edad_min=18, edad_max=67)
                    cargoa = Cargo.objects.get_or_create(cargo='Alumno/a', entidad=g_e.ronda.entidad, nivel=6)
                    cargop = Cargo.objects.get_or_create(cargo='Padre/Madre', entidad=g_e.ronda.entidad, nivel=6)
                    for row_index in range(5, sheet.nrows):
                        d = adic
                        # d = {kra[keys[col_index]]: sheet.cell(row_index, col_index).value for col_index in
                        #      xrange(sheet.ncols)}
                        for col_index in range(sheet.ncols):
                            d[kra[keys[col_index]]] = sheet.cell(row_index, col_index).value
                        d['apellidos'] = '%s %s' % (d['last_name1'], d['last_name2'])
                        d['apellidos_tutor1'] = '%s %s' % (d['last_name1_tutor1'], d['last_name2_tutor1'])
                        d['apellidos_tutor2'] = '%s %s' % (d['last_name1_tutor2'], d['last_name2_tutor2'])
                        # sub = Subentidad.objects.get_or_create(nombre=d['subentidades'], mensajes=True,
                        #                                        entidad=g_e.ronda.entidad, parent=suba,
                        #                                        edad_min=12, edad_max=67, fecha_expira=fecha_expira)
                        # d['subentidades'] = str(sub[0].id) + ',' + str(suba.id)
                        grupo, c = Grupo.objects.get_or_create(nombre=d['subentidades'], ronda=g_e.ronda)
                        if c:
                            crear_aviso(request, False, u'No existía el grupo %s y se ha creado' % (grupo.nombre))
                            logger.info(u'Carga masiva xls. Se crea grupo %s' % grupo.nombre)
                        d['subentidades'] = str(suba.id)
                        d['subentidades_tutor1'] = str(subp.id)
                        d['subentidades_tutor2'] = str(subp.id)
                        d['activo'] = True
                        d['observaciones'] = u'<b>Localidad de nacimiento:</b> %s<br><b>Nacionalidad:</b> %s<br>' \
                                             u'<b>Código del país de nacimiento:</b> %s<br><b>País de nacimiento:</b> %s<br>' \
                                             u'<b>Código de la provincia de nacimiento:</b> %s<br><b>Ha pagado el seguro escolar:</b> %s<br>' \
                                             u'<b>Año de la matrícula:</b> %s<br><b>Número de matrículas en este curso:</b> %s<br>' \
                                             u'<b>Observaciones de la matrícula:</b> %s<br><b>Número de SS:</b> %s<br>' \
                                             u'<b>Nº de expediente en el centro:</b> %s<br><b>Fecha de matrícula:</b> %s<br>' \
                                             u'<b>Nº de matrículas en el expediente:</b> %s<br><b>Repeticiones en el curso:</b> %s<br>' \
                                             u'<b>Familia numerosa:</b> %s<br><b>Lengua materna:</b> %s<br><b>Año de incorporación al sistema educativo:</b> %s<br>' % (
                                                 d['localidad_nacimiento'], d['nacionalidad'],
                                                 d['code_pais_nacimiento'],
                                                 d['pais_nacimiento'], d['code_provincia_nacimiento'],
                                                 d['pago_seguro_escolar'], d['year_matricula'], d['num_matriculas'],
                                                 d['observaciones_matricula'],
                                                 d['num_ss'], d['num_exp'], d['fecha_matricula'],
                                                 d['num_matriculas_exp'],
                                                 d['rep_curso'], d['familia_numerosa'], d['lengua_materna'],
                                                 d['year_incorporacion'])

                        tutor1 = create_usuario(d, request, '_tutor1')
                        if tutor1:
                            tutor1.cargos.add(cargop[0])
                            tutor1.save()
                        tutor2 = create_usuario(d, request, '_tutor2')
                        if tutor2:
                            tutor2.cargos.add(cargop[0])
                            tutor2.save()
                        gauser_extra = create_usuario(d, request, '')
                        gauser_extra.tutor1 = tutor1
                        gauser_extra.tutor2 = tutor2
                        gauser_extra.subentidades.add(suba)
                        gauser_extra.cargos.add(cargoa[0])
                        gauser_extra.save()
                        gauser_extra.gauser_extra_estudios.grupo = grupo
                        gauser_extra.gauser_extra_estudios.save()
                        # elif 'excel' in request.FILES['file_masivo'].content_type:
                        #     pass

                        # for row in fichero:
                        #     if len(row['id_socio']) > 2:
                        #         tutor1 = create_usuario(row, request, '_tutor1')
                        #         tutor2 = create_usuario(row, request, '_tutor2')
                        #         gauser_extra = create_usuario(row, request, '')
                        #         gauser_extra.tutor1 = tutor1
                        #         gauser_extra.tutor2 = tutor2
                        #         gauser_extra.save()
        else:
            crear_aviso(request, False, u'El archivo cargado no tiene el formato adecuado.')

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
    usuarios = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, ronda=g_e.ronda).distinct()
    gauser_extra = usuarios[0]
    form = Gauser_per_Form(instance=gauser_extra)
    if request.is_ajax() and request.method == 'POST':
        action = request.POST['action']
        if action == 'add_cargo' and g_e.has_permiso('asigna_perfiles'):
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
            ge = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['ge'])
            ge.cargos.add(cargo)
            permisos_cargo = dict(ge.cargos.all().values_list('permisos__id', 'permisos__id'))
            return JsonResponse(permisos_cargo)
        elif action == 'del_cargo' and g_e.has_permiso('asigna_perfiles'):
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
            ge = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['ge'])
            ge.cargos.remove(cargo)
            permisos_cargo = dict(ge.cargos.all().values_list('permisos__id', 'permisos__id'))
            return JsonResponse(permisos_cargo)
        elif action == 'add_permiso' and g_e.has_permiso('asigna_permisos'):
            permiso = Permiso.objects.get(id=request.POST['permiso'])
            ge = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['ge'])
            ge.permisos.add(permiso)
            return HttpResponse(True)
        elif action == 'del_permiso' and g_e.has_permiso('asigna_permisos'):
            permiso = Permiso.objects.get(id=request.POST['permiso'])
            ge = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['ge'])
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
        crear_aviso(request, True, u'Entra en ' + request.META['PATH_INFO'] + ' POST action: ' + request.POST['action'])
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
                ges = Gauser_extra.objects.filter(entidad=entidad)
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


# ##############################################################################
# ##############################################################################
# Funciones a borrar tras la migración a gauss_asocia
# ##############################################################################
# ##############################################################################

# def load_gauser_educa(request):
#     # for k in request.GET.keys():
#     #     logger.info(u'%s valor: %s' % (k, request.GET[k]))
#
#     params = ['sexo', 'dni', 'address', 'postalcode', 'localidad', 'provincia', 'nacimiento', 'telfij', 'telmov',
#               'familia', 'username', 'email', 'password', 'first_name', 'last_name']
#     data = {}
#     for p in params:
#         try:
#             data[p] = request.GET[p]
#         except:
#             logger.info("Error al leer el %s del gauser\n" % p)
#
#     try:
#         nacimiento = datetime.strptime(data['nacimiento'], '%d/%m/%Y')
#     except:
#         nacimiento = date.today()
#     sexo = 'H' if data['sexo'] == 'H' else 'M'
#     try:
#         Gauser.objects.get(dni=data['dni'])
#         logger.info("Existe usuario con dni %s: %s %s %s\n" % (
#             data['dni'], data['username'], data['first_name'], data['last_name']))
#     except:
#         try:
#             g = Gauser.objects.get(username=data['username'])
#             logger.info("Intengo grabar usuario  %s con dni %s\n" % (
#                 data['username'], data['dni']))
#             logger.info("Existe username %s con dni %s \n" % (g.username, g.dni))
#             Candidato.objects.create(gauser=g, email=data['email'], username=data['username'],
#                                      password=data['password'],
#                                      sexo=sexo, dni=data['dni'], telmov=data['telmov'],
#                                      address=data['address'].encode('utf-8'), postalcode=data['postalcode'],
#                                      last_name=data['last_name'].encode('utf-8'),
#                                      localidad=data['localidad'], provincia=data['provincia'], telfij=data['telfij'],
#                                      nacimiento=nacimiento, familia=data['familia'],
#                                      first_name=data['first_name'].encode('utf-8'))
#         except:
#             logger.info("No existe usuario con username %s ni dni %s \n" % (data['username'], data['dni']))
#             # try:
#
#             Gauser.objects.create(email=data['email'], username=data['username'], password=data['password'],
#                                   last_login='2017-10-01', sexo=sexo, dni=data['dni'],
#                                   telmov=data['telmov'],
#                                   address=data['address'].encode('utf-8'), postalcode=data['postalcode'],
#                                   last_name=data['last_name'].encode('utf-8'),
#                                   localidad=data['localidad'], provincia=data['provincia'], telfij=data['telfij'],
#                                   nacimiento=nacimiento, familia=data['familia'],
#                                   first_name=data['first_name'].encode('utf-8'))
#             logger.info("Creado usuario: %s %s %s\n" % (data['username'], data['first_name'], data['last_name']))
#             # except:
#             #     logger.info(
#             #         "Imposible crear usuario: %s %s %s\n" % (data['username'], data['first_name'], data['last_name']))
#     return HttpResponse('<h1>Trabajo terminado</h1>')


# def gestionar_candidatos(request):
#     candidatos = Candidato.objects.filter(arreglado=False)[:10]
#     if request.method == 'POST':
#         if request.POST['action'] == 'atributo':
#             atributo = request.POST['atributo']
#             candidato = Candidato.objects.get(id=request.POST['candidato'])
#             gauser = candidato.gauser
#             valor = getattr(candidato, atributo)
#             setattr(gauser, atributo, valor)
#             gauser.save()
#             return JsonResponse({'ok': True, 'atributo': atributo, 'valor': valor, 'candidato': candidato.id})
#         elif request.POST['action'] == 'arreglado':
#             candidato = Candidato.objects.get(id=request.POST['candidato'])
#             candidato.arreglado = True
#             candidato.save()
#             return JsonResponse({'ok': True})
#         elif request.POST['action'] == 'nuevo':
#             c = Candidato.objects.get(id=request.POST['candidato'])
#             nacimiento = c.nacimiento if c.nacimiento else date.today()
#             sexo = 'H' if c.sexo == 'H' else 'M'
#             p = pass_generator(2, chars=string.digits)
#             try:
#                 Gauser.objects.get(dni=c.dni)
#             except:
#                 Gauser.objects.create(email=c.email, username=c.username + p, password=c.password,
#                                       last_login='2017-10-01', sexo=sexo, dni=c.dni,
#                                       telmov=c.telmov,
#                                       address=c.address, postalcode=c.postalcode,
#                                       last_name=c.last_name.encode('utf-8'),
#                                       localidad=c.localidad, provincia=c.provincia, telfij=c.telfij,
#                                       nacimiento=nacimiento, familia=c.familia,
#                                       first_name=c.first_name.encode('utf-8'))
#             c.arreglado = True
#             c.save()
#             return JsonResponse({'ok': True})
#     return render(request, "gestionar_candidatos.html", {'candidatos': candidatos})


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
