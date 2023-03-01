# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import csv
import os
import re
import logging
import xlwt
import pdfkit
from time import sleep
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.utils import timezone, translation
from django.template import RequestContext
from django.db.models import Q
from django.forms import ModelForm, ModelChoiceField, URLField, Form
from django.core.paginator import Paginator
import sys
from django.core import serializers

from gauss.constantes import CODE_CONTENEDOR
from autenticar.control_acceso import LogGauss, permiso_required, gauss_required
from autenticar.views import crear_nombre_usuario
from mensajes.views import encolar_mensaje, crea_mensaje_cola

# from autenticar.models import Gauser_extra, Gauser, Permiso
# from models import Entidad, Ronda, Subentidad, Alta_Baja, Cargo, Reserva_plaza, Organization, Dependencia
from autenticar.models import Gauser, Permiso
from estudios.models import Gauser_extra_estudios, Grupo
from entidades.models import *
from mensajes.models import Aviso, Mensaje, Etiqueta
from mensajes.views import crear_aviso
from bancos.views import asocia_banco_entidad, num_cuenta2iban
from gauss.rutas import *
from gauss.constantes import CARGOS
from gauss.funciones import usuarios_de_gauss, pass_generator, usuarios_ronda, genera_nie, usuarios_organization
from datetime import date
import simplejson as json
from django.template.loader import render_to_string
from django.http import HttpResponse, FileResponse
from django.utils.timezone import datetime
from entidades.forms import EntidadForm, Gauser_extra_mis_datos_Form
from gauss.constantes import PROVINCIAS
from captcha.fields import CaptchaField

user_language = 'es'
translation.activate(user_language)
logger = logging.getLogger('django')


@LogGauss
@login_required()
def mis_datos(request):
    g_e = request.session['gauser_extra']
    miembro_unidad = g_e

    if request.method == 'POST':
        miembro_unidad = Gauser_extra.objects.get(id=request.POST['miembro_unidad'])
        if request.POST['action'] != 'miembro_unidad':
            form2 = Gauser_extra_mis_datos_Form(request.POST, request.FILES, instance=miembro_unidad)
            if form2.is_valid():
                form2.save()
            else:
                crear_aviso(request, False, form2.errors)

    usuarios_tutorados = Gauser_extra_estudios.objects.filter(Q(tutor=g_e) or Q(cotutor=g_e))
    form2 = Gauser_extra_mis_datos_Form(instance=miembro_unidad)
    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'title': 'Aceptar los cambios realizados',
              'permiso': 'libre'},
             ),
        'formname': 'mis_datos',
        'form2': form2,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
        'miembro_unidad': miembro_unidad,
        'usuarios_tutorados': usuarios_tutorados.order_by('grupo'),
        'provincias': PROVINCIAS,
        'logincas': True if 'service' in request.session else False,
    }
    return render(request, "mis_datos.html", respuesta)


@login_required()
def mis_datos_ajax(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        if request.POST['action'] == 'campo_gauser':
            try:
                ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge_id'])
                g = ge.gauser
                if request.POST['campo'] == 'dni':
                    num_gdni = Gauser.objects.filter(dni=request.POST['valor']).exclude(id=g.id).count()
                    if num_gdni > 1:
                        return JsonResponse({'ok': False, 'msg': 'Existen %s usuarios con ese dni' % num_gdni})
                    elif num_gdni == 1:
                        return JsonResponse({'ok': False, 'msg': 'Ya existe un usuario con ese dni'})
                setattr(g, request.POST['campo'], request.POST['valor'])
                g.save()
                if ge == g_e:
                    request.session['gauser_extra'] = Gauser_extra.objects.get(id=ge.id)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'campo_gauser_extra':
            try:
                ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge_id'])
                setattr(ge, request.POST['campo'], request.POST['valor'])
                ge.save()
                if ge == g_e:
                    request.session['gauser_extra'] = Gauser_extra.objects.get(id=ge.id)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_num_cuenta_bancaria':
            try:
                ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge_id'])
                setattr(ge, 'num_cuenta_bancaria', request.POST['valor'])
                ge.save()
                if ge == g_e:
                    request.session['gauser_extra'] = Gauser_extra.objects.get(id=ge.id)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'change_password':
            try:
                if request.POST['password1'] == request.POST['password2'] and request.POST['password1'] != '':
                    ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge_id'])
                    ge.gauser.set_password(request.POST['password1'])
                    ge.gauser.save()
                    if ge == g_e:
                        request.session['gauser_extra'] = Gauser_extra.objects.get(id=ge.id)
                    return JsonResponse({'ok': True, 'mensaje': 'Cambio de contraseña realizado correctamente.'})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No se ha producido el cambio de contraseña.'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error. Contraseña no cambiada.'})


# Esta función no se está usuando. El objetivo era comenzar el diseño de unos usuarios_entidad con ajax.
# Problemas iniciales encontrados:
# - cargos y subentidades que se ha conseguido a través de templatetags
# - Select2 ajax activarlo para cargar tutores (sin hacer)
# @login_required()
@permiso_required('acceso_miembros_entidad')
def usuarios_entidad_ajax(request):
    g_e = request.session["gauser_extra"]
    if request.is_ajax():
        if request.method == 'GET':
            action = request.GET['action']
            if action == 'select_user':
                items = []
                texto = request.GET['search']
                palabras = texto.split()
                q = Q(gauser__first_name__icontains=palabras[0]) | Q(gauser__last_name__icontains=palabras[0]) | Q(
                    gauser__dni__icontains=palabras[0]) | Q(gauser__username__icontains=palabras[0])
                for palabra in palabras[1:]:
                    qnueva = Q(gauser__first_name__icontains=palabra) | Q(gauser__last_name__icontains=palabra) | Q(
                        gauser__dni__icontains=palabra) | Q(gauser__username__icontains=palabra)
                    q = q & qnueva
                for u in usuarios_ronda(g_e.ronda, subentidades=False).filter(q):
                    items.append({'id': u.id, 'text': '%s, %s' % (u.gauser.last_name, u.gauser.first_name)})
                return JsonResponse({'ok': True, 'items': items})
        else:
            action = request.POST['action']
            if action == 'mod_gauser_data':
                if g_e.has_permiso('modifica_datos_usuarios'):
                    try:
                        gauser = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda).gauser
                        if request.POST['campo'] == 'dni':
                            num_gdni = Gauser.objects.filter(dni=request.POST['valor']).exclude(id=gauser.id).count()
                            if num_gdni > 1:
                                return JsonResponse({'ok': False, 'msg': 'Existen %s usuarios con ese dni' % num_gdni})
                            elif num_gdni == 1:
                                return JsonResponse({'ok': False, 'msg': 'Ya existe un usuario con ese dni'})
                        setattr(gauser, request.POST['campo'], request.POST['valor'])
                        gauser.save()
                        return JsonResponse({'ok': True})
                    except:
                        return JsonResponse({'ok': False, 'error': 'Error. Posiblemente en objects.get()'})
                else:
                    return JsonResponse({'ok': False, 'error': 'No tienes el permiso necesario'})
            elif action == 'mod_tutor':
                if g_e.has_permiso('modifica_datos_usuarios'):
                    try:
                        ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                        tutor = Gauser_extra.objects.get(id=request.POST['valor'], ronda=g_e.ronda)
                        setattr(ge, request.POST['campo'], tutor)
                        ge.save()
                        return JsonResponse({'ok': True})
                    except:
                        return JsonResponse({'ok': False, 'error': 'Error. Posiblemente en objects.get()'})
                else:
                    return JsonResponse({'ok': False, 'error': 'No tienes el permiso necesario'})
            elif request.POST['action'] == 'update_num_cuenta_bancaria':
                try:
                    ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge'])
                    setattr(ge, 'num_cuenta_bancaria', request.POST['valor'])
                    ge.save()
                    if ge == g_e:
                        request.session['gauser_extra'] = Gauser_extra.objects.get(id=ge.id)
                    return JsonResponse({'ok': True})
                except:
                    return JsonResponse({'ok': False})
            elif action == 'mod_gauser_extra_data':
                if g_e.has_permiso('modifica_datos_usuarios'):
                    try:
                        ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                        setattr(ge, request.POST['campo'], request.POST['valor'])
                        ge.save()
                        return JsonResponse({'ok': True})
                    except:
                        return JsonResponse({'ok': False, 'error': 'Error. Posiblemente en objects.get()'})
                else:
                    return JsonResponse({'ok': False, 'error': 'No tienes el permiso necesario'})
            elif action == 'mod_subentidades':
                if g_e.has_permiso('modifica_datos_usuarios'):
                    try:
                        ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                        subentidad = Subentidad.objects.get(id=request.POST['campo'], entidad=g_e.ronda.entidad)
                        if request.POST['valor'] == '1':
                            ge.subentidades.add(subentidad)
                        else:
                            ge.subentidades.remove(subentidad)
                        return JsonResponse({'ok': True})
                    except:
                        return JsonResponse({'ok': False, 'error': 'Error. Posiblemente en objects.get()'})
                else:
                    return JsonResponse({'ok': False, 'error': 'No tienes el permiso necesario'})
            elif action == 'mod_cargos':
                if g_e.has_permiso('asigna_perfiles'):
                    try:
                        ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                        cargo = Cargo.objects.get(id=request.POST['campo'], entidad=g_e.ronda.entidad)
                        if request.POST['valor'] == '1':
                            ge.cargos.add(cargo)
                        else:
                            ge.cargos.remove(cargo)
                        return JsonResponse({'ok': True})
                    except:
                        return JsonResponse({'ok': False, 'error': 'Error. Posiblemente en objects.get()'})
                else:
                    return JsonResponse({'ok': False, 'error': 'No tienes el permiso necesario'})
            elif action == 'mod_password':
                if g_e.has_permiso('modifica_datos_usuarios'):
                    try:
                        # password1 se almacena en 'campo' y password2 en 'valor'
                        if request.POST['campo'] == request.POST['valor'] and request.POST['campo'] != '':
                            ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                            ge.gauser.set_password(request.POST['campo'])
                            ge.gauser.save()
                            return JsonResponse({'ok': True, 'mensaje': '<p>Contraseña cambiada correctamente.</p>'})
                        else:
                            return JsonResponse({'ok': True, 'error': 'Las contraseñas no son iguales.'})
                    except:
                        return JsonResponse({'ok': False, 'error': 'Error. Posiblemente en objects.get()'})
                else:
                    return JsonResponse({'ok': False, 'error': 'No tienes el permiso necesario'})
            elif action == 'load_user':
                entidad_users = usuarios_ronda(g_e.ronda)
                entidad_users_id = list(entidad_users.values_list('id', flat=True))
                g_e_selected = Gauser_extra.objects.get(id=request.POST['ge'])
                # Circular list : http://stackoverflow.com/questions/8951020/pythonic-circular-list
                prev = entidad_users_id[(entidad_users_id.index(g_e_selected.id) - 1) % len(entidad_users_id)]
                prox = entidad_users_id[(entidad_users_id.index(g_e_selected.id) + 1) % len(entidad_users_id)]
                cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad).order_by('nivel')
                subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad,
                                                         fecha_expira__gt=datetime.now().date()).order_by('edad_min')
                # 'entidad_users_id': entidad_users_id
                logincas = True if 'service' in request.session else False
                html = render_to_string("usuarios_entidad_formulario.html", {'gauser_extra_selected': g_e_selected,
                                                                             'cargos': cargos,
                                                                             'subentidades': subentidades,
                                                                             'prev_g_e_selected': prev,
                                                                             'prox_g_e_selected': prox,
                                                                             'g_e': g_e, 'logincas': logincas
                                                                             })
                return JsonResponse({'ok': True, 'html': html})
            elif request.POST['action'] == 'baja_socio':
                if g_e.has_permiso('baja_usuarios'):
                    g_e_selected = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                    obs = '<br>(Autor: %s) Con fecha %s se ha dado de baja a %s.' % (g_e.gauser.get_full_name(),
                                                                                     datetime.now().strftime(
                                                                                         "%d-%m-%Y"),
                                                                                     g_e_selected.gauser.get_full_name())
                    g_e_selected.activo = False
                    g_e_selected.observaciones = g_e_selected.observaciones + obs
                    g_e_selected.save()
                    try:
                        baja = Alta_Baja.objects.get(gauser=g_e_selected.gauser)
                        baja.fecha_baja = datetime.now().date()
                        baja.autor = g_e.gauser.get_full_name()
                    except:
                        baja = Alta_Baja.objects.create(entidad=g_e.ronda.entidad, gauser=g_e_selected.gauser,
                                                        fecha_baja=datetime.now().date(),
                                                        autor=g_e.gauser.get_full_name())
                    if not baja.observaciones: baja.observaciones = ''
                    baja.observaciones = baja.observaciones + obs
                    baja.save()
                    mensaje = '<p>Se ha dado de baja al usuario <strong> %s </strong>.</p> <p> Es posible recuperarlo a través del administrador del sistema.</p>' % g_e_selected.gauser.get_full_name()
                    return JsonResponse({'ok': True, 'mensaje': mensaje})
                else:
                    mensaje = '<p>No tienes permisos para dar de baja a los usuarios.</p>'
                    return JsonResponse({'ok': True, 'mensaje': mensaje})
    else:
        if request.method == 'POST':
            if request.POST['action'] == 'upload_file_foto':
                if g_e.has_permiso('modifica_datos_usuarios'):
                    try:
                        ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                        n_files = int(request.POST['n_files'])
                        for i in range(n_files):
                            fichero = request.FILES['fichero_xhr' + str(i)]
                            ge.foto = fichero
                            ge.save()
                        return JsonResponse({'ok': True, 'url': ge.foto.url})
                    except:
                        return JsonResponse({'ok': False, 'error': 'Error. Posiblemente en objects.get()'})
                else:
                    return JsonResponse({'ok': False, 'error': 'No tienes el permiso necesario'})


@permiso_required('acceso_miembros_entidad')
def usuarios_entidad(request):
    g_e = request.session["gauser_extra"]
    entidad_users = usuarios_ronda(g_e.ronda)
    crear_aviso(request, True, 'Entra en ' + request.META['PATH_INFO'] + ' no POST')
    if 'ge' in request.GET:
        try:
            g_e_selected = entidad_users.get(id=request.GET['ge'])
        except:
            g_e_selected = False
    else:
        try:
            g_e_selected = entidad_users[0]
        except:
            g_e_selected = False
            crear_aviso(request, False, 'No hay ningún usuario.<br>En primer lugar debes crear al menos un usuario.')

    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'list', 'texto': 'Listado', 'title': 'Obtener un listado de usuarios',
              'permiso': 'listado_usuarios'},
             {'tipo': 'button', 'nombre': 'male', 'texto': 'Baja', 'title': 'Dar de baja al usuario',
              'permiso': 'baja_usuarios', 'nombre2': 'times'},
             {'tipo': 'button', 'nombre': 'arrow-left', 'texto': '', 'title': 'Usuario anterior (orden alfabético)',
              'permiso': 'acceso_miembros_entidad'},
             {'tipo': 'button', 'nombre': 'search', 'texto': 'Buscar', 'title': 'Buscar usuario por nombre',
              'permiso': 'acceso_miembros_entidad'},
             {'tipo': 'button', 'nombre': 'arrow-right', 'texto': '', 'title': 'Siguiente usuario (orden alfabético)',
              'permiso': 'acceso_miembros_entidad'},
             ),
        'formname': 'entidad_users',
        'gauser_extra_selected': g_e_selected,
        'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"], aceptado=False),
    }

    return render(request, "usuarios_entidad.html", respuesta)


@permiso_required('configura_auto_id')
def configura_auto_id(request):
    g_e = request.session["gauser_extra"]
    try:
        eai = g_e.ronda.entidad.entidad_auto_id
    except:
        eai = Entidad_auto_id.objects.create(entidad=g_e.ronda.entidad)

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'update_auto':
            g_e.ronda.entidad.entidad_auto_id.auto = request.POST['auto']
            g_e.ronda.entidad.entidad_auto_id.save()
            return JsonResponse({'ok': True, 'auto': g_e.ronda.entidad.entidad_auto_id.auto})
        if action == 'update_campo':
            valor = request.POST['valor']
            if valor == 'num':
                valor = '00457'
            elif valor == 'timestamp':
                valor = '210528173422'
            setattr(g_e.ronda.entidad.entidad_auto_id, request.POST['campo'], request.POST['valor'])
            g_e.ronda.entidad.entidad_auto_id.save()
            return JsonResponse({'ok': True, 'campo': request.POST['campo'], 'valor': valor})

    respuesta = {
        'formname': 'configura_auto_id',
        'eai': eai,
        'g_e': g_e,
        'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"], aceptado=False),
    }
    return render(request, "configura_auto_id.html", respuesta)


########################### FUNCIONES LIGADAS AL LISTADO DE USUARIOS ###########################


@permiso_required('acceso_listados_usuarios')
def listados_usuarios(request):
    g_e = request.session['gauser_extra']
    filtrados = Filtrado.objects.filter(propietario__ronda__entidad=g_e.ronda.entidad, propietario__gauser=g_e.gauser)
    g_es = None

    if request.method == 'POST':

        if request.POST['action'] == 'download_file':
            filtrado = Filtrado.objects.get(propietario__ronda__entidad=g_e.ronda.entidad, id=request.POST['filtrado'])

            query = crea_query(filtrado)
            if 'ronda__id' in filtrado.filtroq_set.all().values_list('filtro', flat=True):
                g_es = usuarios_de_gauss(g_e.ronda.entidad, ronda='all')
            else:
                g_es = usuarios_de_gauss(g_e.ronda.entidad, ronda=g_e.ronda)
            g_es = g_es.filter(query)
            # query = crea_query(filtrado)
            # if 'ronda__id' in filtrado.filtroq_set.all().values_list('filtro', flat=True):
            #     g_es = Gauser_extra.objects.filter(Q(entidad=g_e.ronda.entidad) & query)
            # else:
            #     g_es = Gauser_extra.objects.filter(Q(entidad=g_e.ronda.entidad) & Q(ronda=g_e.ronda) & query)
            campos = filtrado.campof_set.all().values_list('campo', flat=True)
            data = list(g_es.values(*campos))
            ruta = MEDIA_LISTADOS + str(g_e.ronda.entidad.code) + '/'
            if not os.path.exists(ruta):
                os.makedirs(ruta)
            fichero_xls = 'listado%s.xls' % (filtrado.id)
            wb = xlwt.Workbook()
            wr = wb.add_sheet('Listado', cell_overwrite_ok=True)
            fila_excel_listado = 0
            estilo = xlwt.XFStyle()
            font = xlwt.Font()
            font.bold = True
            estilo.font = font
            date_format = xlwt.XFStyle()
            date_format.num_format_str = 'dd/mm/yyyy'
            col = 0
            for campo in filtrado.campof_set.all():
                wr.write(fila_excel_listado, col, campo.get_campo_display(), style=estilo)
                col += 1
            fila_excel_listado = 1
            for g_e in data:
                col = 0
                for campo in filtrado.campof_set.all():
                    if isinstance(g_e[campo.campo], date):
                        wr.write(fila_excel_listado, col, g_e[campo.campo], date_format)
                    else:
                        wr.write(fila_excel_listado, col, g_e[campo.campo])
                    col += 1
                fila_excel_listado += 1
            wb.save(ruta + fichero_xls)
            xlsfile = open(ruta + fichero_xls, 'rb')
            response = FileResponse(xlsfile, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=listado.xls'
            return response
    return render(request, "filtro.html", {'formname': 'filtros',
                                           'g_es': g_es,
                                           'filtrados': filtrados,
                                           'iconos':
                                               ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nuevo filtrado',
                                                 'permiso': 'acceso_listados_usuarios',
                                                 'title': 'Añadir un filtro para obtener un listado de usuarios'},
                                                )})


def crea_query(filtrado):
    F = {}
    for filtro in filtrado.filtroq_set.all():
        if filtro.filtro == 'gauser__first_name__icontains':
            F[filtro.n_filtro] = Q(gauser__first_name__icontains=filtro.value)
        elif filtro.filtro == 'gauser__last_name__icontains':
            F[filtro.n_filtro] = Q(gauser__last_name__icontains=filtro.value)
        elif filtro.filtro == 'subentidades__in':
            F[filtro.n_filtro] = Q(subentidades__in=[filtro.value])
        elif filtro.filtro == 'cargos__in':
            F[filtro.n_filtro] = Q(cargos__in=[filtro.value])
        elif filtro.filtro == 'observaciones__icontains':
            F[filtro.n_filtro] = Q(observaciones__icontains=filtro.value)
        elif filtro.filtro == 'ronda__id':
            F[filtro.n_filtro] = Q(ronda__id=filtro.value)
        elif filtro.filtro == 'tutor1__gauser__first_name__icontains':
            F[filtro.n_filtro] = Q(tutor1__gauser__last_name__icontains=filtro.value)
        elif filtro.filtro == 'tutor1__gauser__last_name__icontains':
            F[filtro.n_filtro] = Q(tutor1__gauser__last_name__icontains=filtro.value)
        elif filtro.filtro == 'tutor2__gauser__first_name__icontains':
            F[filtro.n_filtro] = Q(tutor2__gauser__first_name__icontains=filtro.value)
        elif filtro.filtro == 'tutor2__gauser__last_name__icontains':
            F[filtro.n_filtro] = Q(tutor2__gauser__last_name__icontains=filtro.value)
        elif filtro.filtro == 'ocupacion__icontains':
            F[filtro.n_filtro] = Q(ocupacion__icontains=filtro.value)
        elif filtro.filtro == 'banco__id':
            F[filtro.n_filtro] = Q(banco__id=filtro.value)
        elif filtro.filtro == 'gauser__localidad__icontains':
            F[filtro.n_filtro] = Q(gauser__localidad__icontains=filtro.value)
        elif filtro.filtro == 'gauser__provincia__icontains':
            F[filtro.n_filtro] = Q(gauser__provincia__icontains=filtro.value)
        elif filtro.filtro == 'gauser__nacimiento__gt':
            fecha = datetime.strptime(filtro.value, '%d/%m/%Y')
            F[filtro.n_filtro] = Q(gauser__nacimiento__gt=fecha)
        elif filtro.filtro == 'gauser__nacimiento__lt':
            fecha = datetime.strptime(filtro.value, '%d/%m/%Y')
            F[filtro.n_filtro] = Q(gauser__nacimiento__lt=fecha)
        elif filtro.filtro == 'gauser_extra_estudios__grupo__nombre__icontains':
            F[filtro.n_filtro] = Q(gauser_extra_estudios__grupo__nombre__icontains=filtro.value)
    operacion = re.sub(r'(\d{1,2})', r'[\1]', filtrado.operacion)  # Convierte 'F1 & F2 | F3' en 'F[1] & F[2] | F[3]'
    return eval(operacion)


@login_required()
@permiso_required('acceso_listados_usuarios')
def ajax_filtro(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        if request.POST['action'] == 'buscar_alumno':
            texto = request.POST['q']
            sub_alumnos = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='alumnos')
            usuarios = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_alumnos])
            usuarios = usuarios.exclude(id__in=request.POST.getlist('alumnos_seleccionados'))
            usuarios_contain_texto = usuarios.filter(
                Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)).values_list('id',
                                                                                                            'gauser__last_name',
                                                                                                            'gauser__first_name',
                                                                                                            'grupo__nombre')
            keys = ('id', 'text')
            return HttpResponse(json.dumps(
                [dict(zip(keys, (row[0], '%s, %s (%s)' % (row[1], row[2], row[3])))) for row in
                 usuarios_contain_texto]))

        elif request.POST['action'] == 'add_filtrado':
            f = Filtrado.objects.create(propietario=g_e, nombre='Usuarios cuyo nombre contiene ...', operacion='F1')
            FiltroQ.objects.create(filtrado=f, n_filtro=1, filtro='gauser__first_name__icontains', value='')
            data = render_to_string('filtro_accordion.html', {'filtrado': f})
            return HttpResponse(data)
        elif request.POST['action'] == 'open_accordion':
            filtrado = Filtrado.objects.get(propietario__ronda__entidad=g_e.ronda.entidad, id=request.POST['filtrado'])
            data = render_to_string('filtro_accordion_content.html',
                                    {'filtrado': filtrado, 'campos': CAMPOS, 'g_e': g_e})
            return HttpResponse(data)
        elif request.POST['action'] == 'update_nombre_filtrado':
            try:
                filtrado = Filtrado.objects.get(propietario__ronda__entidad=g_e.ronda.entidad,
                                                id=request.POST['filtrado'])
                filtrado.nombre = request.POST['nombre']
                filtrado.save()
                return JsonResponse({'ok': True, 'nombre': filtrado.nombre})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'add_filtro':
            try:
                f = Filtrado.objects.get(propietario__ronda__entidad=g_e.ronda.entidad, id=request.POST['filtrado'])
                n = f.filtroq_set.all().count() + 1
                q = FiltroQ.objects.create(filtrado=f, n_filtro=n, filtro='gauser__first_name__icontains', value='')
                f.operacion = f.operacion + ' & F' + str(n)
                f.save()
                html = render_to_string('filtro_accordion_content_q.html', {'filtro': q})
                return JsonResponse({'html': html, 'ok': True, 'operacion': f.operacion})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'delete_filtro':
            try:
                q = FiltroQ.objects.get(id=request.POST['filtro'], filtrado__propietario=g_e)
                q_n_filtro = q.n_filtro
                q.delete()
                f = q.filtrado
                f_id = f.id
                var = 'F' + str(q_n_filtro)
                f.operacion = f.operacion.replace('& ' + var, '').replace(var + ' &', '').replace(
                    '&' + var, '').replace(var + '&', '').replace('| ' + var, '').replace(var + ' |', '').replace(
                    '|' + var, '').replace(var + '|', '').replace('  ', ' ')
                f.save()
                cambios = []
                for filtro in f.filtroq_set.all():
                    if filtro.n_filtro > q_n_filtro:
                        f.operacion = f.operacion.replace(str(filtro.n_filtro), str(filtro.n_filtro - 1))
                        filtro.n_filtro -= 1
                        filtro.save()
                        cambios.append({'filtro': filtro.id, 'n_filtro': filtro.n_filtro})
                        f.save()
                if f.filtroq_set.all().count() == 0:
                    delete_filtrado = True
                    f.delete()
                else:
                    delete_filtrado = False
                return JsonResponse({'ok': True, 'operacion': f.operacion, 'filtrado': f_id, 'cambios': cambios,
                                     'delete_filtrado': delete_filtrado})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_tipo_filtro':
            try:
                q = FiltroQ.objects.get(id=request.POST['filtro'],
                                        filtrado__propietario__ronda__entidad=g_e.ronda.entidad)
                q.filtro = request.POST['tipo']
                q.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_value_filtro':
            try:
                q = FiltroQ.objects.get(id=request.POST['filtro'],
                                        filtrado__propietario__ronda__entidad=g_e.ronda.entidad)
                q.value = request.POST['value']
                q.save()
                query = crea_query(q.filtrado)
                if 'ronda__id' in q.filtrado.filtroq_set.all().values_list('filtro', flat=True):
                    g_es = usuarios_de_gauss(g_e.ronda.entidad, ronda='all')
                else:
                    g_es = usuarios_de_gauss(g_e.ronda.entidad, ronda=g_e.ronda)
                g_es = g_es.filter(query)
                campos = list(q.filtrado.campof_set.all().values_list('campo', flat=True))
                campos.append('id')
                data = list(g_es.values(*campos))
                html = render_to_string('filtro_accordion_content_tabla.html', {'data': data, 'filtrado': q.filtrado})
                return JsonResponse({'ok': True, 'resultados': data, 'num': g_es.count(), 'html': html,
                                     'filtrado': q.filtrado.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_operacion':
            try:
                f = Filtrado.objects.get(propietario__ronda__entidad=g_e.ronda.entidad, id=request.POST['filtrado'])
                f.operacion = request.POST['operacion']
                f.save()

                query = crea_query(f)
                if 'ronda__id' in f.filtroq_set.all().values_list('filtro', flat=True):
                    g_es = usuarios_de_gauss(g_e.ronda.entidad, ronda='all')
                else:
                    g_es = usuarios_de_gauss(g_e.ronda.entidad, ronda=g_e.ronda)
                g_es = g_es.filter(query)
                # query = crea_query(f)
                # if 'ronda__id' in f.filtroq_set.all().values_list('filtro', flat=True):
                #     g_es = Gauser_extra.objects.filter(Q(entidad=g_e.ronda.entidad) & query)
                # else:
                #     g_es = Gauser_extra.objects.filter(Q(entidad=g_e.ronda.entidad) & Q(ronda=g_e.ronda) & query)
                campos = list(f.campof_set.all().values_list('campo', flat=True))
                campos.append('id')
                data = list(g_es.values(*campos))
                html = render_to_string('filtro_accordion_content_tabla.html', {'data': data, 'filtrado': f})
                return JsonResponse({'ok': True, 'resultados': data, 'num': g_es.count(), 'html': html,
                                     'filtrado': f.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_campo':
            try:
                f = Filtrado.objects.get(propietario__ronda__entidad=g_e.ronda.entidad, id=request.POST['filtrado'])
                if request.POST['operation'] == 'added':
                    CampoF.objects.create(filtrado=f, campo=request.POST['campo'])
                else:
                    CampoF.objects.get(filtrado=f, campo=request.POST['campo']).delete()

                query = crea_query(f)
                if 'ronda__id' in f.filtroq_set.all().values_list('filtro', flat=True):
                    g_es = usuarios_de_gauss(g_e.ronda.entidad, ronda='all')
                else:
                    g_es = usuarios_de_gauss(g_e.ronda.entidad, ronda=g_e.ronda)
                g_es = g_es.filter(query)
                # query = crea_query(f)
                # if 'ronda__id' in f.filtroq_set.all().values_list('filtro', flat=True):
                #     g_es = Gauser_extra.objects.filter(Q(entidad=g_e.ronda.entidad) & query)
                # else:
                #     g_es = Gauser_extra.objects.filter(Q(entidad=g_e.ronda.entidad) & Q(ronda=g_e.ronda) & query)
                campos = list(f.campof_set.all().values_list('campo', flat=True))
                campos.append('id')
                data = list(g_es.values(*campos))
                html = render_to_string('filtro_accordion_content_tabla.html', {'data': data, 'filtrado': f})
                return JsonResponse({'ok': True, 'resultados': data, 'num': g_es.count(), 'html': html,
                                     'filtrado': f.id})
            except:
                return JsonResponse({'ok': False})


####################### FIN DE LAS FUNCIONES LIGADAS AL LISTADO DE USUARIOS #######################

@LogGauss
@login_required()
def buscar_usuarios(request):
    g_e = request.session['gauser_extra']
    usuarios = usuarios_ronda(g_e.ronda)
    items = []
    texto = request.GET['q']
    palabras = texto.split()
    q = Q(gauser__first_name__icontains=palabras[0]) | Q(gauser__last_name__icontains=palabras[0]) | Q(
        gauser__dni__icontains=palabras[0]) | Q(gauser__username__icontains=palabras[0])
    for palabra in palabras[1:]:
        qnueva = Q(gauser__first_name__icontains=palabra) | Q(gauser__last_name__icontains=palabra) | Q(
            gauser__dni__icontains=palabra) | Q(gauser__username__icontains=palabra)
        q = q & qnueva
    for u in usuarios_ronda(g_e.ronda, subentidades=False).filter(q):
        cargos = []
        for cargo in u.cargos.all():
            cargos.append(cargo.cargo)
        text = '%s, %s (%s)' % (u.gauser.last_name, u.gauser.first_name, ', '.join(cargos))
        items.append({'id': u.id, 'text': text})

    return JsonResponse({'ok': True, 'items': items})
    usuarios_contain_texto = usuarios.filter(
        Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)).values_list('id',
                                                                                                    'gauser__last_name',
                                                                                                    'gauser__first_name',
                                                                                                    'subentidades__nombre')
    keys = ('id', 'last_name', 'first_name', 'perfiles')
    # from django.core import serializers
    # data = serializers.serialize('json', socios2, fields=('gauser__first_name', 'id'))
    return HttpResponse(json.dumps([dict(zip(keys, row)) for row in usuarios_contain_texto]))


@LogGauss
@login_required()
def buscar_usuarios_cargos_subentidades(request):
    texto = request.GET['q']
    g_e = request.session['gauser_extra']
    usuarios = usuarios_ronda(g_e.ronda)
    usuarios_contain_texto = usuarios.filter(
        Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)).values_list('id',
                                                                                                    'gauser__last_name',
                                                                                                    'gauser__first_name',
                                                                                                    'subentidades__nombre')
    # [{"id": 28817, "last_name": "Mart\u00edn Romero", "first_name": "Juan Jos\u00e9",
    #   "perfiles": "Secci\u00f3n de Logro\u00f1o"},
    #  {"id": 28816, "last_name": "Nieto Garc\u00eda", "first_name": "Juan", "perfiles": "Secci\u00f3n de Logro\u00f1o"}]

    a = {}
    a = dict([('usuario__id', 'fafasdfasfadsfa')])
    keys = ('usuario__id', 'last_name', 'first_name', 'perfiles')
    cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad)
    cargos_contain_texto = cargos.filter(cargo__icontains=texto).values_list('id', 'cargo')

    subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad)
    subentidades_contain_texto = subentidades.filter(nombre__icontains=texto).values_list('id', 'nombre')

    # from django.core import serializers
    # data = serializers.serialize('json', socios2, fields=('gauser__first_name', 'id'))
    return HttpResponse(json.dumps([dict(zip(keys, row)) for row in usuarios_contain_texto]))


# ###################################################################################f
# ###################################################################################f
# ###################################################################################f
# ###################################################################################f

@permiso_required('acceso_dependencias_entidad')
def dependencias_entidad(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'add_dependencia':
            dependencia = Dependencia.objects.create(nombre='Nueva dependencia', entidad=g_e.ronda.entidad, edificio='',
                                                     planta='', ancho=5, largo=5)
            accordion = render_to_string('dependencia_accordion.html', {'dependencia': dependencia})
            return HttpResponse(accordion)
        elif action == 'delete_dependencia':
            dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            dependencia.delete()
            return HttpResponse(True)
        elif action == 'nombre_dependencia':
            dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            dependencia.nombre = request.POST['nombre']
            dependencia.save()
            return HttpResponse(dependencia.nombre)
        elif action == 'edificio_dependencia':
            dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            dependencia.edificio = request.POST['edificio']
            dependencia.save()
            return HttpResponse(dependencia.edificio)
        elif action == 'planta_dependencia':
            dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            dependencia.planta = request.POST['planta']
            dependencia.save()
            return HttpResponse(dependencia.planta)
        elif action == 'largo_dependencia':
            dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            dependencia.largo = request.POST['largo']
            try:
                dependencia.save()
                return HttpResponse(dependencia.largo)
            except:
                return HttpResponse('error')
        elif action == 'ancho_dependencia':
            dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            dependencia.ancho = request.POST['ancho']
            try:
                dependencia.save()
                return HttpResponse(dependencia.ancho)
            except:
                return HttpResponse('error')
        elif action == 'abrev_dependencia':
            dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            dependencia.abrev = request.POST['abrev']
            try:
                dependencia.save()
                return HttpResponse(dependencia.abrev)
            except:
                return HttpResponse('error')
        elif action == 'es_aula':
            try:
                dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                dependencia.es_aula = not dependencia.es_aula
                dependencia.save()
                return JsonResponse({'ok': True, 'es_aula': ['No', 'Sí'][dependencia.es_aula]})
            except:
                return JsonResponse({'ok': False})

    return render(request, "dependencias_entidad.html",
                  {
                      'formname': 'dependencias_entidad',
                      'entidad': Entidad.objects.get(id=g_e.ronda.entidad.id),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'dependencias': Dependencia.objects.filter(entidad=g_e.ronda.entidad)
                  })


# ###################################################################################f
# ###################################################################################f
# ###################################################################################f
# ###################################################################################f

@permiso_required('acceso_gestionar_rondas')
def rondas_entidad(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'change_ronda' and g_e.has_permiso('accede_otras_rondas'):
            try:
                ronda = Ronda.objects.get(id=request.POST['ronda'], entidad=g_e.ronda.entidad)
                request.session["ronda"] = ronda
            except:
                crear_aviso(request, False, 'Tienes prohibido el acceso a la ronda solicitada')
                logger.warning('%s Intento de acceso a ronda con id=%s' % (g_e, request.GET['r']))

    return render(request, "rondas_entidad.html",
                  {
                      'formname': 'rondas_entidad',
                      'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                     aceptado=False),
                      'rondas': Ronda.objects.filter(entidad=g_e.ronda.entidad),
                  })


@permiso_required('acceso_gestionar_rondas')
def configura_rondas(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'add_ronda':
            ronda = Ronda.objects.create(nombre='Configuración nueva', entidad=g_e.ronda.entidad)
            gauss = Gauser.objects.get(username='gauss')
            Gauser_extra.objects.create(gauser=gauss, ronda=ronda, activo=True)
            accordion = render_to_string('configura_rondas_accordion.html', {'ronda': ronda})
            return JsonResponse({'ok': True, 'html': accordion})
        elif action == 'delete_ronda':
            try:
                ronda = Ronda.objects.get(id=request.POST['ronda'], entidad=g_e.ronda.entidad)
                if ronda.id > g_e.ronda.entidad.ronda.id:
                    Gauser_extra.objects.filter(ronda=ronda).delete()
                    ronda.delete()
                    return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'upgrade_usuarios':
            ronda = Ronda.objects.get(id=request.POST['ronda'], entidad=g_e.ronda.entidad)
            cargo = Cargo.objects.get(id=request.POST['cargo'], entidad=g_e.ronda.entidad)
            if ronda.id > g_e.ronda.entidad.ronda.id:
                # Capturamos los g_es seleccionados:
                g_es = Gauser_extra.objects.filter(ronda=g_e.ronda, cargos__in=[cargo], activo=True)
                # En caso aumentar de curso creamos g_es si es necesario
                # Los primeros en crearse deben ser los tutores, ya que deberán asignarse a los no tutores
                lista = g_es.values_list('tutor1__id', 'tutor2__id')
                tutores = Gauser_extra.objects.filter(id__in=list(set([a for sublist in lista for a in sublist])))
                otros_usuarios = g_es.exclude(id__in=tutores)
                tutores_nuevos_id = []
                for g__e in tutores:
                    try:
                        Gauser_extra.objects.get(gauser=g__e.gauser, ronda=ronda)
                    except:
                        new_user = Gauser_extra.objects.create(gauser=g__e.gauser,
                                                               ronda=ronda,
                                                               id_entidad=g__e.id_entidad,
                                                               id_organizacion=g__e.id_organizacion,
                                                               alias=g__e.alias, activo=True,
                                                               observaciones=g__e.observaciones,
                                                               foto=g__e.foto,
                                                               ocupacion=g__e.ocupacion,
                                                               num_cuenta_bancaria=g__e.num_cuenta_bancaria)
                        new_user.subentidades.add(*g__e.subentidades.all())
                        new_user.subsubentidades.add(*g__e.subsubentidades.all())
                        new_user.cargos.add(*g__e.cargos.all())
                        new_user.permisos.add(*g__e.permisos.all())
                        tutores_nuevos_id.append(new_user.id)

                tutores_nuevos = Gauser_extra.objects.filter(id__in=tutores_nuevos_id, ronda=g_e.ronda.entidad.ronda)
                for g__e in otros_usuarios:
                    try:
                        Gauser_extra.objects.get(gauser=g__e.gauser, ronda=ronda)
                    except:
                        try:
                            tutor1 = tutores_nuevos.get(gauser=g__e.tutor1.gauser)
                        except:
                            tutor1 = None
                        try:
                            tutor2 = tutores_nuevos.get(gauser=g__e.tutor2.gauser)
                        except:
                            tutor2 = None
                        new_user = Gauser_extra.objects.create(gauser=g__e.gauser,
                                                               ronda=ronda,
                                                               id_entidad=g__e.id_entidad,
                                                               id_organizacion=g__e.id_organizacion,
                                                               alias=g__e.alias, activo=True,
                                                               observaciones=g__e.observaciones,
                                                               foto=g__e.foto,
                                                               tutor1=tutor1, tutor2=tutor2,
                                                               ocupacion=g__e.ocupacion,
                                                               num_cuenta_bancaria=g__e.num_cuenta_bancaria)
                        new_user.subentidades.add(*g__e.subentidades.all())
                        new_user.subsubentidades.add(*g__e.subsubentidades.all())
                        new_user.cargos.add(*g__e.cargos.all())
                        new_user.permisos.add(*g__e.permisos.all())
            cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad)
            html = render_to_string('configura_rondas_accordion_content_cargos.html',
                                    {'cargos': cargos, 'ronda': ronda})
            return JsonResponse({'ok': True, 'html': html, 'ronda': ronda.id})
        elif action == 'change_campo_texto':
            try:
                ronda = Ronda.objects.get(id=request.POST['ronda'], entidad=g_e.ronda.entidad)
                campo = request.POST['campo']
                value = request.POST['value']
                if campo != 'nombre':
                    value = datetime.strptime(value, '%d/%m/%Y')
                setattr(ronda, campo, value)
                ronda.save()
                return JsonResponse({'texto': request.POST['value'], 'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            ronda = Ronda.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad)
            html = render_to_string('configura_rondas_accordion_content.html',
                                    {'ronda': ronda, 'ronda_actual': g_e.ronda.entidad.ronda, 'cargos': cargos})
            return JsonResponse({'html': html, 'ok': True})

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'change_ronda' and g_e.has_permiso('accede_otras_rondas'):
            try:
                ronda = Ronda.objects.get(id=request.POST['ronda'], entidad=g_e.ronda.entidad)
                request.session["ronda"] = ronda
            except:
                crear_aviso(request, False, 'Tienes prohibido el acceso a la ronda solicitada')
                logger.warning('%s Intento de acceso a ronda con id=%s' % (g_e, request.GET['r']))

    return render(request, "configura_rondas.html",
                  {
                      'formname': 'rondas_entidad',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'title': 'Crer una nueva configuración para un periodo',
                            'permiso': 'libre'},
                           ),
                      'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                     aceptado=False),
                      'rondas': Ronda.objects.filter(entidad=g_e.ronda.entidad),
                  })


@permiso_required('acceso_datos_entidad')
def datos_entidad(request):
    g_e = request.session["gauser_extra"]
    docConf, c = DocConfEntidad.objects.get_or_create(entidad=g_e.ronda.entidad, predeterminado=True)
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'update_cabecera_html' and request.is_ajax():
            try:
                docConf.header = request.POST['header']
                docConf.save()
                html_header = render_to_string('documentos_cabecera.html', {'cabecera': docConf.header})
                f = open(MEDIA_ANAGRAMAS + '%s_cabecera.html' % (docConf.entidad.code), 'w+')
                f.write(html_header)
                f.close()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_pie_html' and request.is_ajax():
            try:
                docConf.footer = request.POST['footer']
                docConf.save()
                html_footer = render_to_string('documentos_pie.html', {'pie': docConf.footer})
                f = open(MEDIA_ANAGRAMAS + '%s_pie.html' % (docConf.entidad.code), 'w+')
                f.write(html_footer)
                f.close()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_campo' and request.is_ajax():
            try:
                mensaje = ''
                objeto = docConf if request.POST['objeto'] == 'DocConfEntidad' else g_e.ronda.entidad
                valor = request.POST['valor']
                campo = request.POST['campo']
                if campo == 'iban' and len(valor) == 24:
                    correcto = asocia_banco_entidad(g_e.ronda.entidad)
                    if not correcto:
                        mensaje = "No se ha podido asociar un banco a esa cuenta bancaria."
                setattr(objeto, campo, valor)
                objeto.save()
                entidad = Entidad.objects.get(id=g_e.ronda.entidad.id)
                request.session['gauser_extra'] = Gauser_extra.objects.get(gauser=g_e.gauser, ronda=entidad.ronda)
                return JsonResponse({'ok': True, 'mensaje': mensaje})
            except:
                return JsonResponse({'ok': False})
        elif action == 'borrar_ge' and request.is_ajax():
            ge_borrar = Gauser_extra.objects.get(id=request.POST['id'])
            num_ges = Gauser_extra.objects.filter(ronda=ge_borrar.ronda, gauser=ge_borrar.gauser).count()
            if num_ges > 1:
                try:
                    ge_borrar.delete()
                    return JsonResponse({'ok': True})
                except:
                    nueva_ronda = Ronda.objects.filter(entidad__name__icontains='Borrar')[0]
                    ge_borrar.ronda = nueva_ronda
                    ge_borrar.save()
                    return JsonResponse({'ok': True})
            else:
                return JsonResponse({'ok': False, 'm': 'Solo hay un usuario en esta ronda'})
        elif action == 'update_ronda':
            try:
                form = EntidadForm(request.POST)
                ronda = Ronda.objects.get(id=request.POST['ronda'])
                # compruebo que existe el usuario en la ronda seleccionada:
                Gauser_extra.objects.get(gauser=g_e.gauser, ronda=ronda)
                if form.is_valid():
                    form = EntidadForm(request.POST, instance=g_e.ronda.entidad)
                    form.save()
                    entidad = Entidad.objects.get(id=g_e.ronda.entidad.id)
                    request.session['gauser_extra'] = Gauser_extra.objects.get(gauser=g_e.gauser, ronda=entidad.ronda)
                else:
                    crear_aviso(request, False, form.errors)
                    form = EntidadForm(request.POST)
            except:
                crear_aviso(request, False, 'Error. <br>Deben existir usuarios asociados a la nueva ronda o curso.')
        elif action == 'upload_file_anagrama':
            entidad = Entidad.objects.get(id=g_e.ronda.entidad.id)
            try:
                n_files = int(request.POST['n_files'])
                for i in range(n_files):
                    fichero = request.FILES['fichero_xhr' + str(i)]
                    if fichero.content_type in 'image/jpeg, image/png, image/gif':
                        try:
                            os.remove(entidad.anagrama.path)
                            entidad.anagrama = fichero
                            entidad.save()
                        except:
                            entidad.anagrama = fichero
                            entidad.save()
                    else:
                        return JsonResponse({'ok': False, 'mensaje': 'El fichero debe ser una imagen.'})
                return JsonResponse({'ok': True, 'url': entidad.anagrama.url})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Ha habido un error al procesar el archivo.'})
    else:
        entidad = Entidad.objects.get(id=g_e.ronda.entidad.id)
        form = EntidadForm(instance=entidad)

    try:
        # sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
        # docentes = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_docentes])
        cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, clave_cargo='g_docente')
        docentes = Gauser_extra.objects.filter(ronda=g_e.ronda, cargos__in=[cargo])
    except:
        docentes = []
    return render(request, "datos_entidad.html",
                  {
                      'formname': 'datos_entidad',
                      'entidad': Entidad.objects.get(id=g_e.ronda.entidad.id),
                      'form': form,
                      'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                     aceptado=False),
                      'rondas': Ronda.objects.filter(entidad=g_e.ronda.entidad),
                      'docentes': docentes
                  })


# --------------------------------------------------------------------------------#


class Socio_GauserForm(ModelForm):
    class Meta:
        model = Gauser
        fields = ('first_name', 'last_name', 'email', 'sexo', 'dni', 'address', 'postalcode', 'localidad', 'provincia',
                  'nacimiento', 'telfij', 'telmov')


class Socio_Gauser_extraForm(ModelForm):
    class Meta:
        model = Gauser_extra
        fields = (
            'id_organizacion', 'num_cuenta_bancaria', 'ocupacion', 'tutor1', 'tutor2', 'observaciones', 'id_entidad')


class Reserva_plazaForm(ModelForm):
    class Meta:
        model = Reserva_plaza
        exclude = ('entidad',)


@permiso_required('acceso_reserva_plazas')
def reserva_plazas(request):
    g_e = request.session['gauser_extra']
    # Creamos la clave secreta asociada a una entidad, en el caso de no existir:
    if not g_e.ronda.entidad.secret:
        g_e.ronda.entidad.secret = pass_generator(10)
        g_e.ronda.entidad.save()
    # Creamos los campos de un formulario de reserva por defecto, en el caso de no existir:
    n = 1
    for campo in CAMPOS_RESERVA:
        crp, creado = ConfiguraReservaPlaza.objects.get_or_create(entidad=g_e.ronda.entidad, campo=campo[0])
        if creado:
            crp.texto = campo[1]
            crp.orden = n
            n += 1
            crp.save()
    # Desarrollo de la función propiamente dicha
    reservas = Reserva_plaza.objects.filter(entidad=g_e.ronda.entidad)
    # if request.method == 'POST':
    #     crear_aviso(request, True, request.META['PATH_INFO'] + ' POST')
    #     reserva = Reserva_plaza.objects.create(entidad=g_e.ronda.entidad)
    #     form = Reserva_plazaForm(request.POST, instance=reserva)
    #     form.save()
    # else:
    #     form = Reserva_plazaForm()
    form = Reserva_plazaForm()
    return render(request, "reserva_plazas.html",
                  {
                      'formname': 'Reserva_plaza',
                      'entidad': g_e.ronda.entidad,
                      'form': form,
                      'reservas': reservas,
                      'usuarios': usuarios_ronda(g_e.ronda),
                      'configura_reservas': ConfiguraReservaPlaza.objects.filter(entidad=g_e.ronda.entidad),
                      'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                     aceptado=False),
                  })


class CaptchaForm(Form):
    captcha = CaptchaField()


def formulario_ext_reserva_plaza(request):
    # ARVUTUR:
    # https://gaumentada.es/formulario_ext_reserva_plaza/?c=4rkISXIGXJ
    year = datetime.today().year
    anyos = range(year, year - 100, -1)
    if request.method == 'GET':
        secret = request.GET['c']
        try:
            entidad = Entidad.objects.get(secret=secret)
            return render(request, "formulario_reserva_plaza_externo.html",
                          {
                              'campos': ConfiguraReservaPlaza.objects.filter(entidad=entidad),
                              'formname': 'Reserva_plaza',
                              'form': Reserva_plazaForm(),
                              'entidad': entidad,
                              'reserva_grabada': False,
                              'errores': '',
                              'captcha_form': CaptchaForm(),
                              'anyos': anyos
                          })
        except:
            return render(request, "registro_entrada_viajero_error.html")

    elif request.method == 'POST':
        captcha_form = CaptchaForm(request.POST)
        if captcha_form.is_valid():
            entidad = Entidad.objects.get(id=request.POST['entidad'])
            errores = ''
            html = ''
            campos = ConfiguraReservaPlaza.objects.filter(entidad=entidad)
            for campo in campos:
                if campo.required:
                    if request.POST[campo.campo] == '' or request.POST[campo.campo] == None:
                        errores += '<p>El campo "%s" es obligatorio</p>' % campo.get_campo_display()
            if errores == '':
                reserva = Reserva_plaza.objects.create(entidad=entidad)
                form = Reserva_plazaForm(request.POST, instance=reserva)
                form.save()
                form = Reserva_plazaForm()
                html = render_to_string('formulario_reserva_plaza.html',
                                        {'campos': campos, 'form': form, 'anyos': anyos})
                gauss = Gauser_extra.objects.get(ronda=entidad.ronda, gauser__username='gauss')
                permiso = Permiso.objects.get(code_nombre='recibe_aviso_reserva')
                receptores_id = Gauser_extra.objects.filter(ronda=entidad.ronda, permisos__in=[permiso]).values_list(
                    'gauser__id', flat=True)
                receptores = Gauser.objects.filter(id__in=receptores_id)
                mensaje = render_to_string('mensaje_reserva_grabada.html',
                                           {'crps': campos, 'reserva': reserva, 'mail': True})
                encolar_mensaje(emisor=gauss, receptores=receptores, asunto='Solicitud de plaza en %s' % entidad.name,
                                html=mensaje, etiqueta='reservas%s' % entidad.id)
                ok = True
            else:
                ok = False
            return JsonResponse({'ok': ok, 'html': html, 'mensaje': errores})
        else:
            return JsonResponse({'ok': False,
                                 'mensaje': 'Debes introducir el texto mostrado en la imagen. Si no lo ves claro pulsa en "Recargar"'})


@permiso_required('acceso_listados_usuarios')
def listados_usuarios_entidad(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        crear_aviso(request, True, request.META['PATH_INFO'] + ' POST')
        action = request.POST['action']
        if action == 'update_id_entidad':
            try:
                ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                ge.id_entidad = request.POST['id_entidad']
                ge.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_id_organizacion':
            try:
                ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                ge.id_organizacion = request.POST['id_organizacion']
                ge.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_subentidades':
            try:
                ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                subentidad = Subentidad.objects.get(id=request.POST['subentidad'], entidad=g_e.ronda.entidad)
                if request.POST['is_checked'] == 'true':
                    ge.subentidades.add(subentidad)
                else:
                    ge.subentidades.remove(subentidad)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_cargos':
            try:
                ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                cargo = Cargo.objects.get(id=request.POST['cargo'], entidad=g_e.ronda.entidad)
                if request.POST['is_checked'] == 'true':
                    ge.cargos.add(cargo)
                else:
                    ge.cargos.remove(cargo)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_page':
            try:
                total_ges = usuarios_de_gauss(entidad=g_e.ronda.entidad).order_by('gauser__last_name')
                paginator = Paginator(total_ges, 25)
                ges = paginator.page(int(request.POST['page']))
                html = render_to_string(request.POST['tab'], {'ges': ges})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

    total_ges = usuarios_de_gauss(entidad=g_e.ronda.entidad).order_by('gauser__last_name')
    paginator = Paginator(total_ges, 25)
    return render(request, "listados_usuarios_entidad.html",
                  {
                      'ges': paginator.page(1),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@permiso_required('acceso_crear_usuarios')
def add_usuario(request):
    g_e = request.session['gauser_extra']

    if request.method == 'POST':
        crear_aviso(request, True, request.META['PATH_INFO'] + ' POST')
        dni = genera_nie(request.POST['dni'])
        try:
            gauser = Gauser.objects.get(dni=dni)
            crear_aviso(request, False, 'Un usuario con el mismo DNI ya existe. No se crea uno nuevo.')
        except:
            usuario = crear_nombre_usuario(nombre=request.POST['first_name'], apellidos=request.POST['last_name'])
            gauser = Gauser.objects.create_user(usuario, request.POST['email'], pass_generator(),
                                                last_login=datetime.today())
            form1 = Socio_GauserForm(request.POST, instance=gauser)
            form1.save()
        try:
            gauser_extra = Gauser_extra.objects.get(gauser=gauser, ronda=g_e.ronda)
            crear_aviso(request, False, 'El usuario para esta entidad ya existe y no se crea uno nuevo')
        except:
            gauser_extra = Gauser_extra.objects.create(gauser=gauser, activo=True, ronda=g_e.ronda)
            form2 = Socio_Gauser_extraForm(request.POST, instance=gauser_extra)
            gauser_extra = form2.save()
        gauser_extra.num_cuenta_bancaria = num_cuenta2iban(gauser_extra.num_cuenta_bancaria)
        cargos = Cargo.objects.filter(id__in=request.POST.getlist('cargos'))
        subentidades = Subentidad.objects.filter(id__in=request.POST.getlist('subentidades'), entidad=g_e.ronda.entidad,
                                                 fecha_expira__gt=datetime.now().date())
        gauser_extra.cargos.add(*cargos)
        gauser_extra.subentidades.add(*subentidades)
        gauser_extra.id_entidad = gauser_extra.id_organizacion
        gauser_extra.save()
    ges = usuarios_de_gauss(entidad=g_e.ronda.entidad).order_by('id_organizacion').reverse()[:5]
    sorted_val_list = [ge.id_organizacion for ge in ges if ge.id_organizacion]
    # sorted_val_list.sort()

    return render(request, "add_usuario.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                            'title': 'Guardar datos del nuevo usuario',
                            'permiso': 'crea_usuarios'},),
                      'formname': 'add_usuario',
                      'tipos_socio': Cargo.objects.filter(entidad=g_e.ronda.entidad),
                      'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad,
                                                                fecha_expira__gt=datetime.now().date()),
                      'form1': Socio_GauserForm(),
                      'form2': Socio_Gauser_extraForm(),
                      'ids': sorted_val_list,
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                     aceptado=False),
                  })


@permiso_required('acceso_tutores_entidad')
def tutores_entidad(request):
    g_e = request.session['gauser_extra']
    # sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
    # docentes = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_docentes])
    cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, clave_cargo='g_docente')
    docentes = Gauser_extra.objects.filter(ronda=g_e.ronda, cargos__in=[cargo])
    grupos = Grupo.objects.filter(ronda=g_e.ronda).order_by('cursos__etapa', 'nombre')
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'selecciona_docente':
            try:
                docente = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['docente'])
                if request.POST['tipo'] == 'tutor':
                    alumnos_tutorados = Gauser_extra_estudios.objects.filter(grupo__ronda=g_e.ronda, tutor=docente)
                else:
                    alumnos_tutorados = Gauser_extra_estudios.objects.filter(grupo__ronda=g_e.ronda, cotutor=docente)

                grupos_tutorados_id = set(alumnos_tutorados.values_list('grupo', flat=True))
                grupos_tutorados = grupos.filter(id__in=grupos_tutorados_id, ronda=g_e.ronda).distinct()
                alumnos = []
                for g in grupos_tutorados:
                    alumnos_grupo = Gauser_extra_estudios.objects.filter(grupo=g)
                    for alumno in alumnos_grupo:
                        nombre = '%s, %s' % (alumno.ge.gauser.last_name, alumno.ge.gauser.first_name)
                        if alumno in alumnos_tutorados:
                            alumnos.append(
                                {'grupo': g.nombre, 'grupo_id': g.id, 'id': alumno.id, 'nombre': nombre,
                                 'tutorado': True})
                        else:
                            alumnos.append(
                                {'grupo': g.nombre, 'grupo_id': g.id, 'id': alumno.id, 'nombre': nombre,
                                 'tutorado': False})
                html = render_to_string('tutores_entidad_alumnos.html', {'alumnos': alumnos})

                return JsonResponse({'ok': True, 'html': html, 'grupos': list(grupos_tutorados_id)})
            except:
                return JsonResponse({'ok': False})

        elif action == 'selecciona_grupos':
            try:
                docente = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['docente'])
                # if request.POST['tipo'] == 'tutor':
                #     alumnos_tutorados = Gauser_extra_estudios.objects.filter(grupo__ronda=g_e.ronda, tutor=docente)
                # else:
                #     alumnos_tutorados = Gauser_extra_estudios.objects.filter(grupo__ronda=g_e.ronda, cotutor=docente)

                grupos_tutorados = Grupo.objects.filter(id__in=request.POST.getlist('grupos[0][]'), ronda=g_e.ronda)
                html = render_to_string('tutores_entidad_alumnos.html',
                                        {'grupos': grupos_tutorados, 'tipo': request.POST['tipo'],
                                         'docente': docente})

                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif action == 'selecciona_todos_ninguno':
            try:
                docente = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['docente'])
                grupo = Grupo.objects.get(ronda=g_e.ronda, id=request.POST['grupo'])
                alumnos = Gauser_extra_estudios.objects.filter(grupo=grupo)
                docente_asignado = docente if request.POST['select'] == 'todos' else None
                if request.POST['tipo'] == 'tutor':
                    for alumno in alumnos:
                        alumno.tutor = docente_asignado
                        alumno.save()
                    alumnos_tutorados = Gauser_extra_estudios.objects.filter(grupo__ronda=g_e.ronda, tutor=docente)
                else:
                    for alumno in alumnos:
                        alumno.cotutor = docente_asignado
                        alumno.save()
                    alumnos_tutorados = Gauser_extra_estudios.objects.filter(grupo__ronda=g_e.ronda, cotutor=docente)
                grupos_tutorados_id = alumnos_tutorados.values_list('grupo', flat=True).distinct()
                grupos_seleccionados = grupos.filter(
                    Q(id__in=request.POST.getlist('grupos[0][]')) | Q(id__in=grupos_tutorados_id))
                html = render_to_string('tutores_entidad_alumnos.html',
                                        {'grupos': grupos_seleccionados, 'tipo': request.POST['tipo'],
                                         'docente': docente_asignado})

                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif action == 'selecciona_alumno':
            try:
                docente = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['docente'])
                alumno = Gauser_extra_estudios.objects.get(grupo__ronda=g_e.ronda, id=request.POST['alumno'])
                docente_asignado = docente if request.POST['checked'] == 'true' else None
                if request.POST['tipo'] == 'tutor':
                    alumno.tutor = docente_asignado
                else:
                    alumno.cotutor = docente_asignado
                alumno.save()

                return JsonResponse({'ok': True, 'alumno': alumno.id, 'd': docente_asignado})
            except:
                return JsonResponse({'ok': False})

    return render(request, "tutores_entidad.html",
                  {
                      'formname': 'tutores_entidad',
                      'docentes': docentes,
                      'grupos': grupos,
                      'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                     aceptado=False),
                  })


@permiso_required('acceso_getion_bajas')
def bajas_usuarios(request):
    g_e = request.session['gauser_extra']
    bajas = Alta_Baja.objects.filter(entidad=g_e.ronda.entidad, fecha_baja__isnull=False).order_by('-fecha_baja')

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'busca_bajas':
            texto = request.POST['texto']
            bajas = bajas.filter(Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto))
            html = render_to_string('bajas_accordion.html', {'bajas': bajas})
            return JsonResponse({'html': html, 'ok': True})
        elif action == 'open_accordion':
            baja = Alta_Baja.objects.get(id=request.POST['baja'], entidad=g_e.ronda.entidad)
            ges = Gauser_extra.objects.filter(ronda__entidad=g_e.ronda.entidad, gauser=baja.gauser)
            gs = baja.estado_unidad_familiar
            data = render_to_string('bajas_accordion_content.html', {'baja': baja, 'ges': ges, 'gs': gs})
            return HttpResponse(data)
        elif action == 'close_accordion':
            try:
                baja = Alta_Baja.objects.get(id=request.POST['baja'], entidad=g_e.ronda.entidad)
                return JsonResponse({'borrar': False})
            except:
                return JsonResponse({'borrar': True})
        elif action == 'dar_alta':
            gauser = Gauser.objects.get(id=request.POST['gauser'])
            baja_actuar = Alta_Baja.objects.get(gauser=gauser, entidad=g_e.ronda.entidad, id=request.POST['baja'])
            datos = baja_actuar.dar_alta(autor=g_e.gauser.get_full_name())
            baja = Alta_Baja.objects.get(id=request.POST['baja'], entidad=g_e.ronda.entidad)
            ges = Gauser_extra.objects.filter(ronda__entidad=g_e.ronda.entidad, gauser=baja.gauser)
            gs = baja.estado_unidad_familiar
            html = render_to_string('bajas_accordion_content.html', {'baja': baja, 'ges': ges, 'gs': gs})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'dar_baja':
            gauser = Gauser.objects.get(id=request.POST['gauser'])
            try:
                ge = Gauser_extra.objects.get(gauser=gauser, ronda=g_e.ronda)
            except:
                ge = Gauser_extra.objects.filter(ronda__entidad=g_e.ronda.entidad, gauser=gauser).reverse()[0]
                ge.pk = None
                ge.ronda = g_e.ronda.entidad.ronda
                ge.save()
            ge.dar_baja(g_e.gauser.get_full_name())
            baja = Alta_Baja.objects.get(id=request.POST['baja'], entidad=g_e.ronda.entidad)
            ges = Gauser_extra.objects.filter(ronda__entidad=g_e.ronda.entidad, gauser=baja.gauser)
            gs = baja.estado_unidad_familiar
            html = render_to_string('bajas_accordion_content.html', {'baja': baja, 'ges': ges, 'gs': gs})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'borrar_usuario':
            gauser = Gauser.objects.get(id=request.POST['gauser'])
            ges = Gauser_extra.objects.filter(ronda__entidad=g_e.ronda.entidad, gauser=gauser)
            for ge in ges:
                ge.delete()
            try:
                baja_borrar = Alta_Baja.objects.get(gauser=gauser, entidad=g_e.ronda.entidad)
            except:
                baja_borrar = None
            baja = Alta_Baja.objects.get(id=request.POST['baja'], entidad=g_e.ronda.entidad)
            if baja_borrar == baja:
                baja_borrar.delete()
                html = '<h1>Usuario borrado</h1>'
            else:
                ges = Gauser_extra.objects.filter(ronda__entidad=g_e.ronda.entidad, gauser=baja.gauser)
                gs = baja.estado_unidad_familiar
                html = render_to_string('bajas_accordion_content.html', {'baja': baja, 'ges': ges, 'gs': gs})
            return JsonResponse({'ok': True, 'html': html})

    if request.method == 'POST':
        crear_aviso(request, True, request.META['PATH_INFO'] + ' POST')
        if request.POST['action'] == 'dar_altas':
            permiso_alta = g_e.has_permiso('da_alta_socios')
            if permiso_alta or g_e.has_cargos([1, 2]):
                # nuevas_altas = Alta_Baja.objects.filter(pk__in=request.POST['id_bajas'].split(','))
                nuevas_altas = Alta_Baja.objects.filter(id=request.POST['id_baja_selected'])
                for n_a in nuevas_altas:
                    n_a.fecha_baja = None
                    if not n_a.observaciones: n_a.observaciones = ''
                    n_a.observaciones = n_a.observaciones + '<br>Con fecha %s se ha dado de alta a %s (%s).<br>' % (
                        datetime.now().strftime("%d-%m-%Y"), n_a.gauser.get_full_name(), n_a.entidad)
                    n_a.fecha_alta = datetime.now().date()
                    n_a.save()
                    try:
                        g_e_selected = Gauser_extra.objects.get(gauser=n_a.gauser, ronda=n_a.entidad.ronda)
                        crear_aviso(request, False, 'Se ha recuperado al usuario %s' % (g_e_selected))
                    except:
                        g_e_selected = Gauser_extra.objects.create(gauser=n_a.gauser, ronda=n_a.entidad.ronda)
                        crear_aviso(request, False,
                                    'Se ha recuperado al usuario %s creando un usuario para esta ronda. Es necesario asignar perfiles manualmente.' % (
                                        g_e_selected))
                    g_e_selected.activo = True
                    if not g_e_selected.observaciones: g_e_selected.observaciones = ''
                    obs = '<br>Con fecha %s se ha dado de alta de nuevo a %s.' % (
                        datetime.now().strftime("%d-%m-%Y"), g_e_selected.gauser.get_full_name())
                    g_e_selected.observaciones = g_e_selected.observaciones + obs
                    g_e_selected.save()
            else:
                crear_aviso(request, False, 'No tienes permiso para dar de alta a los usuarios')

        if request.POST['action'] == 'borrar_bajas2':
            permiso_borrar = g_e.has_permiso('borrar_datos_socios')
            if permiso_borrar:
                usuarios_borrados = Alta_Baja.objects.filter(pk__in=request.POST['id_bajas'].split(','))
                for u_b in usuarios_borrados:
                    gauser = u_b.gauser
                    # Falta por escribir el código:
                    # - Eliminar sólo alta_baja?
                    # - Eliminar los gauser_extra relacionados con la entidad?
                    # - Eliminar los gauser_extra y el gauser?

    return render(request, "bajas_usuarios.html",
                  {
                      'formname': 'bajas_usuarios',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'male', 'texto': 'Alta', 'nombre2': 'check',
                            'title': 'Volver a dar de alta al ex-usuario seleccionado',
                            'permiso': 'm25i12i20'},
                           {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                            'title': 'Borrar el cargo seleccionado', 'permiso': 'm25i12i10'}),
                      'bajas': bajas[:10],
                      'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                     aceptado=False),
                  })


@permiso_required('acceso_gestionar_perfiles')
def organigrama(request):
    g_e = request.session['gauser_extra']
    crear_aviso(request, True, request.META['PATH_INFO'])

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        crear_aviso(request, True, request.META['PATH_INFO'] + ' POST')
        if action == 'open_accordion':
            cargo = Cargo.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            usuarios = usuarios_ronda(g_e.ronda, cargos=[cargo])
            html = render_to_string("formulario_cargo.html", {'usuarios': usuarios, 'cargo': cargo, 'g_e': g_e})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'add_permiso' and g_e.has_permiso('asigna_permisos'):
            permiso = Permiso.objects.get(id=request.POST['permiso'])
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
            cargo.permisos.add(permiso)
            return HttpResponse(True)
        elif action == 'del_permiso' and g_e.has_permiso('asigna_permisos'):
            permiso = Permiso.objects.get(id=request.POST['permiso'])
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
            cargo.permisos.remove(permiso)
            return HttpResponse(True)
        elif action == 'change_name_cargo' and g_e.has_permiso('edita_perfiles'):
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
            cargo.cargo = request.POST['texto']
            cargo.save()
            return HttpResponse(cargo.cargo)
        elif action == 'change_nivel_cargo' and g_e.has_permiso('edita_perfiles'):
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
            cargo.nivel = request.POST['nivel']
            cargo.save()
            niveles = {1: 'Cargo/Perfil de primer nivel', 2: 'Cargo/Perfil de segundo nivel',
                       3: 'Cargo/Perfil de tercer nivel', 4: 'Cargo/Perfil de cuarto nivel',
                       5: 'Cargo/Perfil de quinto nivel', 6: 'Cargo/Perfil de sexto nivel'}
            return HttpResponse(niveles[int(cargo.nivel)])
        elif action == 'update_usuarios_cargo':
            try:
                cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
                if g_e.has_permiso('asigna_perfiles'):
                    usuarios_cargo = usuarios_ronda(g_e.ronda, cargos=[cargo])
                    for u in usuarios_cargo:
                        u.cargos.remove(cargo)
                    usuarios = Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('usuarios[]'))
                    for u in usuarios:
                        u.cargos.add(cargo)
                    return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})

            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
            for ga in Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=list(request.POST.getlist('added[]'))):
                ga.cargos.add(cargo)
            for gr in Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=list(request.POST.getlist('removed[]'))):
                gr.cargos.remove(cargo)
            return JsonResponse({'ok': False})
            try:
                cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
                for ga in Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('added[]')):
                    ga.cargos.add(cargo)
                for gr in Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('removed[]')):
                    gr.cargos.remove(cargo)
                # ges_removed = Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('removed[]'))
                # ge.cargos.add(cargo)
                # try:
                #     for id in request.POST.getlist('added[]'):
                #         ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=id)
                #         ge.cargos.add(cargo)
                # if 'removed[]' in request.POST:
                #     # ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['removed[]'])
                #     # ge.cargos.remove(cargo)
                #     for id in request.POST.getlist('removed[]'):
                #         ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=id)
                #         ge.cargos.remove(cargo)
                return JsonResponse({'ok': True, 'cargo': cargo.id})
            except:
                return JsonResponse({'ok': False})
        elif action == 'del_cargo' and g_e.has_permiso('borra_perfiles'):
            try:
                cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
                id = cargo.id
                cargo.delete()
                return JsonResponse({'ok': True, 'id': id})
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_cargo' and g_e.has_permiso('crea_perfiles'):
            cargo = Cargo.objects.create(entidad=g_e.ronda.entidad, cargo='Nuevo cargo', nivel=6)
            data = render_to_string("accordion_cargo.html", {'cargo': cargo})
            return HttpResponse(data)
        elif action == 'copiar_cargo_sin' and g_e.has_permiso('crea_perfiles'):
            try:
                cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
                permisos = cargo.permisos.all()
                cargo.pk = None
                cargo.cargo = cargo.cargo + ' (copia)'
                cargo.save()
                cargo.permisos.add(*permisos)
                html = render_to_string("accordion_cargo.html", {'cargo': cargo})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'copiar_cargo_con' and g_e.has_permiso('crea_perfiles'):
            try:
                cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, id=request.POST['cargo'])
                usuarios = usuarios_ronda(g_e.ronda, cargos=[cargo])
                permisos = cargo.permisos.all()
                cargo.pk = None
                cargo.cargo = cargo.cargo + ' (copia)'
                cargo.save()
                cargo.permisos.add(*permisos)
                for u in usuarios:
                    u.cargos.add(cargo)
                html = render_to_string("accordion_cargo.html", {'cargo': cargo})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

    cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad).order_by('nivel')
    menus = Menu.objects.filter(entidad=g_e.ronda.entidad, menu_default__tipo='Accesible')
    return render(request, "organigrama.html",
                  {
                      'formname': 'Cargos',
                      'cargos': cargos,
                      'menus': menus,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


class MiModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return '%s' % (obj.nombre)


class SubentidadForm(ModelForm):
    # def __init__(self, *args, **kwargs):
    # super(SubentidadForm, self).__init__(*args, **kwargs)
    # perfiles = Perfil.objects.filter(pk__gte=70)
    # self.fields['perfil'] = MiModelChoiceField(queryset=perfiles)

    class Meta:
        model = Subentidad
        exclude = ('entidad', 'perfil')


@permiso_required('acceso_gestionar_subentidades')
def subentidades(request):
    g_e = request.session['gauser_extra']
    ronda = request.session['ronda']
    if request.method == 'POST':
        action = request.POST['action']
        logger.info('%s post %s' % (g_e, action))
        # if action == 'formulario_subentidad' and request.is_ajax():
        #     if request.POST['id']:
        #         subentidad = Subentidad.objects.get(id=request.POST['id'])
        #         g_es = usuarios_de_gauss(entidad=g_e.ronda.entidad, subentidades=[subentidad]).values_list('id',
        #                                                                                              'gauser__last_name',
        #                                                                                              'gauser__first_name')
        #         keys = ('id', 'text')
        #         usuarios = json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in g_es])
        #         form = SubentidadForm(instance=subentidad)
        #     else:
        #         usuarios = None
        #         form = SubentidadForm()
        #     data = render_to_string("formulario_subentidad.html", {'form': form, 'usuarios': usuarios})
        #     return HttpResponse(data)

        if action == 'guardar_subentidad' and request.is_ajax():
            if request.POST['id_subentidad_selected']:
                subentidad = Subentidad.objects.get(id=request.POST['id_subentidad_selected'])
                g_es = usuarios_de_gauss(entidad=g_e.ronda.entidad, subentidades=[subentidad])
            else:
                subentidad = Subentidad(entidad=g_e.ronda.entidad)
                g_es = []
            form = SubentidadForm(request.POST, instance=subentidad)
            if form.is_valid():
                subentidad = form.save()
                for ge in g_es:
                    ge.subentidades.remove(subentidad)
                try:
                    g_es = Gauser_extra.objects.filter(id__in=request.POST['usuarios_subentidad'].split(','))
                except:
                    g_es = []
                for ge in g_es:
                    ge.subentidades.add(subentidad)
                error = None
                crear_aviso(request, True,
                            'Modificación/Creación del subentidad: <strong>%s</strong>' % subentidad.nombre)
            else:
                crear_aviso(request, True,
                            'Error en la modificación/mreación del subentidad: <strong>%s</strong>' % subentidad.nombre)
                error = form.errors
            data = render_to_string("list_subentidades.html",
                                    {'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad,
                                                                               fecha_expira__gt=ronda.fin),
                                     'error': error, 'request': request})
            return HttpResponse(data)
        elif action == 'mostrar_usuarios' and request.is_ajax():
            subentidad = Subentidad.objects.get(id=request.POST['id'])
            data = render_to_string("list_usuarios_subentidad.html", {'subentidad': subentidad, 'tipo': 'mostrar'})
            return HttpResponse(data)
        elif action == 'ocultar_usuarios' and request.is_ajax():
            subentidad = Subentidad.objects.get(id=request.POST['id'])
            data = render_to_string("list_usuarios_subentidad.html", {'subentidad': subentidad, 'tipo': 'ocultar'})
            return HttpResponse(data)

    subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.now().date())
    return render(request, "subentidades.html",
                  {
                      'formname': 'Subentidades',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                            'title': 'Aceptar los cambios realizados', 'permiso': 'edita_subentidades'},
                           {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Secciones',
                            'title': 'Ver la lista de secciones/departamentos/subentidades creadas',
                            'permiso': 'edita_subentidades'},
                           {'tipo': 'button', 'nombre': 'plus', 'texto': 'Sección',
                            'title': 'Añadir una nueva sección/departamento/subentidad',
                            'permiso': 'edita_subentidades'},
                           {'tipo': 'button', 'nombre': 'pencil', 'texto': 'Editar',
                            'title': 'Editar la sección/departamento/subentidad para su modificación',
                            'permiso': 'edita_subentidades'},
                           {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                            'title': 'Borrar la sección/departamento/subentidad seleccionada',
                            'permiso': 'edita_subentidades'}),
                      'subentidades': subentidades,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def subentidades_ajax(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        action = request.POST['action']
        if action == 'add_subentidad' and g_e.has_permiso('crea_subentidades'):
            subentidad = Subentidad.objects.create(entidad=g_e.ronda.entidad, nombre='Nueva sección/departamento',
                                                   edad_min=1,
                                                   edad_max=90, observaciones='')
            data = render_to_string("accordion_subentidad.html", {'subentidad': subentidad})
            return HttpResponse(data)
        elif action == 'open_accordion':
            subentidad = Subentidad.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad,
                                                     fecha_expira__gte=datetime.now().date()).exclude(
                id=subentidad.id)
            # g_es = usuarios_de_gauss(entidad=g_e.ronda.entidad, subentidades=[subentidad]).values_list('id',
            #                                                                                      'gauser__last_name',
            #                                                                                      'gauser__first_name')
            g_es = usuarios_ronda(g_e.ronda, subentidades=[subentidad])
            # keys = ('id', 'text')
            # usuarios = json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in g_es])
            data = render_to_string("formulario_subentidad.html",
                                    {'entidad': g_e.ronda.entidad, 'g_es': g_es, 'subentidad': subentidad,
                                     'gauser_extra': g_e, 'request': request, 'subentidades': subentidades
                                     })
            return HttpResponse(data)
        elif action == 'del_subentidad' and g_e.has_permiso('borra_subentidades'):
            try:
                subentidad = Subentidad.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                nombre = subentidad.nombre
                try:
                    subentidad.delete()
                    mensaje = 'Se ha borrado el departamento/sección: <strong>%s</strong>' % nombre
                    return JsonResponse({'ok': True, 'mensaje': mensaje})
                except:
                    contenedor, c = Entidad.objects.get_or_create(code=CODE_CONTENEDOR)
                    subentidad.entidad = contenedor
                    subentidad.save()
                    mensaje = 'Se ha asignado el departamento/sección: <strong>%s</strong> al Contenedor.' % nombre
                    return JsonResponse({'ok': True, 'mensaje': mensaje})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Posiblemente no se ha podido cargar la subentidad.'})
        elif action == 'nombre_subentidad' and g_e.has_permiso('edita_subentidades'):
            try:
                subentidad = Subentidad.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                subentidad.nombre = request.POST['nombre']
                subentidad.save()
                return JsonResponse({'ok': True, 'nombre': subentidad.nombre})
            except:
                return JsonResponse({'ok': False})
        elif action == 'edad_min_subentidad' and g_e.has_permiso('edita_subentidades'):
            try:
                subentidad = Subentidad.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                subentidad.edad_min = int(request.POST['edad_min'])
                subentidad.save()
                return JsonResponse({'ok': True, 'edad_min': subentidad.edad_min})
            except:
                return JsonResponse({'ok': False})
        elif action == 'edad_max_subentidad' and g_e.has_permiso('edita_subentidades'):
            try:
                subentidad = Subentidad.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                subentidad.edad_max = int(request.POST['edad_max'])
                subentidad.save()
                return JsonResponse({'ok': True, 'edad_max': subentidad.edad_max})
            except:
                return JsonResponse({'ok': False})
        elif action == 'mensajes' and g_e.has_permiso('edita_subentidades'):
            try:
                subentidad = Subentidad.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                subentidad.mensajes = not subentidad.mensajes
                subentidad.save()
                return JsonResponse({'ok': True, 'mensajes': ['No', 'Sí'][subentidad.mensajes]})
            except:
                return JsonResponse({'ok': False})
        elif action == 'observaciones' and g_e.has_permiso('edita_subentidades'):
            try:
                subentidad = Subentidad.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                subentidad.observaciones = request.POST['observaciones']
                subentidad.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'buscar_usuarios':
            texto = request.POST['q']
            usuarios = usuarios_de_gauss(g_e.ronda.entidad)
            filtrado = usuarios.filter(Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto))
            return HttpResponse(json.dumps([{'id': u.id, 'text': u.gauser.get_full_name()} for u in filtrado]))
        elif action == 'usuarios_subentidad' and g_e.has_permiso('edita_subentidades'):
            try:
                subentidad = Subentidad.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                old_users = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[subentidad])
                new_users = Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('users[]'))
                added_users = new_users.exclude(id__in=old_users)
                removed_users = old_users.exclude(id__in=new_users)
                for u in added_users:
                    u.subentidades.add(subentidad)
                for u in removed_users:
                    u.subentidades.remove(subentidad)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'sub_padre' and g_e.has_permiso('edita_subentidades'):
            try:
                subentidad = Subentidad.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                pk = request.POST['sub_padre']
                if pk:
                    subentidad.parent = Subentidad.objects.get(pk=pk, entidad=g_e.ronda.entidad)
                else:
                    subentidad.parent = None
                subentidad.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'fecha_expira' and g_e.has_permiso('edita_subentidades'):
            try:
                subentidad = Subentidad.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                subentidad.fecha_expira = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
                subentidad.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'clave_ex' and g_e.has_permiso('edita_subentidades'):
            try:
                subentidad = Subentidad.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                subentidad.clave_ex = request.POST['clave_ex']
                subentidad.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        else:
            return JsonResponse({'ok': False})


@LogGauss
@login_required()
def buscar_asociados(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        subentidad = Subentidad.objects.get(id=request.POST['id'])
        socios = usuarios_de_gauss(g_e.ronda.entidad, edad_max=subentidad.edad_max, edad_min=subentidad.edad_min)
        socios_seleccionados = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[subentidad.id])
        html = render_to_string("posibles_asociados.html",
                                {'socios': socios, 'socios_seleccionados': socios_seleccionados, 'sub': subentidad})
        return HttpResponse(html)


@LogGauss
@login_required()
def ajax_entidades(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        if request.POST['action'] == 'reserva2usuario':
            ahora = datetime.now()
            # try:
            reserva = Reserva_plaza.objects.get(id=request.POST['reserva'])
            dni = genera_nie(reserva.dni)
            try:
                g = Gauser.objects.get(dni=dni)
            except:
                try:
                    g = Gauser.objects.get(email=reserva.email)
                except:
                    g = Gauser.objects.create_user(crear_nombre_usuario(reserva.first_name, reserva.last_name),
                                                   email=reserva.email, password=pass_generator(),
                                                   first_name=reserva.first_name, last_name=reserva.last_name,
                                                   address=reserva.address, telfij=reserva.telfij,
                                                   telmov=reserva.telmov, sexo=reserva.sexo, last_login=ahora,
                                                   nacimiento=reserva.nacimiento, dni=dni)
            cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('cargos[]'))
            subs = Subentidad.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('subentidades[]'))
            if reserva.first_name_tutor1:
                dni_tutor1 = genera_nie(reserva.dni_tutor1)
                try:
                    g1 = Gauser.objects.get(dni=dni_tutor1)
                except:
                    try:
                        g1 = Gauser.objects.get(email=reserva.email_tutor1)
                    except:
                        g1 = Gauser.objects.create_user(
                            crear_nombre_usuario(reserva.first_name_tutor1, reserva.last_name_tutor1),
                            email=reserva.email_tutor1, password=pass_generator(), dni=dni_tutor1,
                            first_name=reserva.first_name_tutor1, last_name=reserva.last_name_tutor1, last_login=ahora,
                            address=reserva.address, telfij=reserva.telfij_tutor1, telmov=reserva.telmov_tutor1)
                try:
                    g_e1 = Gauser_extra.objects.get(gauser=g1, ronda=g_e.ronda)
                    g_e1.activo = True
                    g_e1.save()
                except:
                    g_e1 = Gauser_extra.objects.create(gauser=g1, activo=True, ronda=g_e.ronda)
                g_e1.cargos.add(*cargos)
                g_e1.subentidades.add(*subs)
            else:
                g1, g_e1, g1_name = None, None, None
            if reserva.first_name_tutor2:
                dni_tutor2 = genera_nie(reserva.dni_tutor2)
                try:
                    g2 = Gauser.objects.get(dni=dni_tutor2)
                except:
                    try:
                        g2 = Gauser.objects.get(email=reserva.email_tutor2)
                    except:
                        g2 = Gauser.objects.create_user(
                            crear_nombre_usuario(reserva.first_name_tutor2, reserva.last_name_tutor2),
                            email=reserva.email_tutor2, password=pass_generator(), dni=dni_tutor2,
                            first_name=reserva.first_name_tutor2, last_name=reserva.last_name_tutor2, last_login=ahora,
                            address=reserva.address, telfij=reserva.telfij_tutor2, telmov=reserva.telmov_tutor2)
                try:
                    g_e2 = Gauser_extra.objects.get(gauser=g2, ronda=g_e.ronda)
                    g_e2.activo = True
                    g_e2.save()
                except:
                    g_e2 = Gauser_extra.objects.create(gauser=g2, activo=True, ronda=g_e.ronda)
                g_e2.cargos.add(*cargos)
                g_e2.subentidades.add(*subs)
            else:
                g2, g_e2, g2_name = None, None, None
            try:
                ge = Gauser_extra.objects.get(gauser=g, ronda=g_e.ronda)
                ge.tutor1 = g_e1
                ge.tutor2 = g_e2
                ge.activo = True
                ge.save()
            except:
                ge = Gauser_extra.objects.create(gauser=g, tutor1=g_e1, tutor2=g_e2, activo=True, ronda=g_e.ronda,
                                                 observaciones=reserva.observaciones,
                                                 num_cuenta_bancaria=reserva.num_cuenta_bancaria)
            ge.cargos.add(*cargos)
            ge.subentidades.add(*subs)
            receptores = [i for i in [g1, g2, g] if i]
            mensaje = render_to_string('mensaje_reserva_aceptada.html', {'reserva': reserva, 'mail': True})
            encolar_mensaje(emisor=g_e, receptores=receptores, etiqueta='reservas%s' % g_e.ronda.entidad.id,
                            asunto='Solicitud de plaza aceptada en %s' % g_e.ronda.entidad.name, html=mensaje)
            reserva.delete()
            mensaje = render_to_string('reserva2usuario.html', {'g1': g1, 'g2': g2, 'g': g})
            return JsonResponse({'ok': True, 'mensaje': mensaje})
            # except:
            #     return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_reserva':
            reserva = Reserva_plaza.objects.get(id=request.POST['id'])
            data = render_to_string('contenido_reserva.html', {'reserva': reserva})
            return HttpResponse(data)
        elif request.POST['action'] == 'configura_reservas':
            try:
                conf = ConfiguraReservaPlaza.objects.get(id=request.POST['id'])
                campo = request.POST['campo']
                html = False
                if campo == 'orden':
                    orden_nuevo = min(int(request.POST['valor']),
                                      ConfiguraReservaPlaza.objects.filter(entidad=conf.entidad).count())
                    confs = ConfiguraReservaPlaza.objects.filter(entidad=conf.entidad).exclude(id=conf.id)
                    cambiado = False
                    n = 1
                    for u in confs:
                        if n == orden_nuevo:
                            conf.orden = orden_nuevo
                            conf.save()
                            n += 1
                            cambiado = True
                        u.orden = n
                        u.save()
                        n += 1
                    if not cambiado:
                        conf.orden = orden_nuevo
                        conf.save()
                    confs = ConfiguraReservaPlaza.objects.filter(entidad=conf.entidad)
                    html = render_to_string('reserva_plazas_tabla_configuraciones.html', {'configura_reservas': confs})
                setattr(conf, campo, request.POST['valor'])
                conf.save()
                return JsonResponse({'ok': True, 'campo': campo, 'valor': getattr(conf, campo), 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'change_tab_formulario_reserva':
            campos = ConfiguraReservaPlaza.objects.filter(entidad=g_e.ronda.entidad)
            form = Reserva_plazaForm()
            year = datetime.today().year
            anyos = range(year, year - 100, -1)
            html = render_to_string('formulario_reserva_plaza.html', {'campos': campos, 'form': form, 'anyos': anyos})
            return JsonResponse({'ok': True, 'html': html})
        elif request.POST['action'] == 'change_tab_reservas_espera':
            reservas = Reserva_plaza.objects.filter(entidad=g_e.ronda.entidad)
            html = render_to_string('reserva_plazas_tabla_espera.html', {'reservas': reservas})
            return JsonResponse({'ok': True, 'html': html})
        elif request.POST['action'] == 'add_reserva':
            errores = ''
            campos = ConfiguraReservaPlaza.objects.filter(entidad=g_e.ronda.entidad)
            for campo in campos:
                if campo.required:
                    if request.POST[campo.campo] == '' or request.POST[campo.campo] == None:
                        errores += '<p>El campo "%s" es obligatorio</p>' % campo.get_campo_display()
            if errores == '':
                reserva = Reserva_plaza.objects.create(entidad=g_e.ronda.entidad)
                form = Reserva_plazaForm(request.POST, instance=reserva)
                form.save()
                form = Reserva_plazaForm()
                year = datetime.today().year
                anyos = range(year, year - 100, -1)
                html = render_to_string('formulario_reserva_plaza.html',
                                        {'campos': campos, 'form': form, 'anyos': anyos})
                return JsonResponse({'ok': True, 'html': html})
            else:
                return JsonResponse({'ok': False, 'errores': errores})
        elif request.POST['action'] == 'borrar_reserva':
            try:
                Reserva_plaza.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id']).delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'usuarios_aviso_reserva':
            try:
                permiso = Permiso.objects.get(code_nombre='recibe_aviso_reserva')
                con_permiso = Gauser_extra.objects.filter(ronda=g_e.ronda, permisos__in=[permiso])
                for ge in con_permiso:
                    ge.permisos.remove(permiso)
                seles = Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('seleccionados[]'))
                for s in seles:
                    s.permisos.add(permiso)
                    s.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'info_reserva':
            try:
                reserva = Reserva_plaza.objects.get(entidad=g_e.ronda.entidad, id=request.POST['reserva'])
                campos = ConfiguraReservaPlaza.objects.filter(entidad=reserva.entidad)
                mensaje = render_to_string('mensaje_reserva_grabada.html',
                                           {'crps': campos, 'reserva': reserva, 'mail': False})
                return JsonResponse({'ok': True, 'mensaje': mensaje})
            except:
                return JsonResponse({'ok': False})

            # elif request.POST['action'] == 'add_dependencia':
            #     dependencia = Dependencia.objects.create(nombre='Nueva dependencia', entidad=g_e.ronda.entidad, edificio='',
            #                                              planta='', ancho=5, largo=5)
            #     accordion = render_to_string('dependencia_accordion.html', {'dependencia': dependencia})
            #     return HttpResponse(accordion)
            # elif request.POST['action'] == 'delete_dependencia':
            #     dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            #     dependencia.delete()
            #     return HttpResponse(True)
            # elif request.POST['action'] == 'nombre_dependencia':
            #     dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            #     dependencia.nombre = request.POST['nombre']
            #     dependencia.save()
            #     return HttpResponse(dependencia.nombre)
            # elif request.POST['action'] == 'edificio_dependencia':
            #     dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            #     dependencia.edificio = request.POST['edificio']
            #     dependencia.save()
            #     return HttpResponse(dependencia.edificio)
            # elif request.POST['action'] == 'planta_dependencia':
            #     dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            #     dependencia.planta = request.POST['planta']
            #     dependencia.save()
            #     return HttpResponse(dependencia.planta)
            # elif request.POST['action'] == 'largo_dependencia':
            #     dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            #     dependencia.largo = request.POST['largo']
            #     try:
            #         dependencia.save()
            #         return HttpResponse(dependencia.largo)
            #     except:
            #         return HttpResponse('error')
            # elif request.POST['action'] == 'ancho_dependencia':
            #     dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            #     dependencia.ancho = request.POST['ancho']
            #     try:
            #         dependencia.save()
            #         return HttpResponse(dependencia.ancho)
            #     except:
            #         return HttpResponse('error')
            # elif request.POST['action'] == 'abrev_dependencia':
            #     dependencia = Dependencia.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            #     dependencia.abrev = request.POST['abrev']
            #     try:
            #         dependencia.save()
            #         return HttpResponse(dependencia.abrev)
            #     except:
            #         return HttpResponse('error')


class oForm(ModelForm):
    web = URLField(required=False)

    class Meta:
        model = Organization
        exclude = []


class rForm(ModelForm):
    class Meta:
        model = Ronda
        exclude = ['entidad']


class eForm(ModelForm):
    class Meta:
        model = Entidad
        exclude = ['organization', 'ronda', 'anagrama']


@gauss_required
def crea_entidad(request):
    g_e = request.session['gauser_extra']
    oform = oForm()
    rform = rForm()
    eform = eForm()
    if g_e.gauser.username == 'gauss':
        if request.method == 'POST':
            o_creada, e_creada, r_credada = False, False, False
            # Código para determinar la organización:
            if request.POST['organization_id']:
                organization = Organization.objects.get(id=request.POST['organization_id'])
                o_creada = True
            else:
                oform = oForm(request.POST, request.FILES)
                if oform.is_valid():
                    organization = oform.save()
                    o_creada = True
                    crear_aviso(request, False, 'La organization ha sido creada')
                else:
                    crear_aviso(request, False, oform.errors)

            if o_creada:
                # Código para definir la entidad
                eform = eForm(request.POST, request.FILES)
                if eform.is_valid():
                    entidad = eform.save()
                    # entidad.ronda = ronda
                    entidad.organization = organization
                    entidad.save()
                    # ronda.entidad = entidad
                    # ronda.save()
                    e_creada = True
                    crear_aviso(request, False,
                                'La entidad y la ronda han sido creadas. El usuario gauss tiene su gauser_extra')
                else:
                    crear_aviso(request, False, eform.errors)
            if e_creada:
                # Código para determinar la ronda asociada a la entidad
                inicio = datetime.strptime(request.POST['inicio_ronda'], '%Y-%m-%d')
                fin = datetime.strptime(request.POST['fin_ronda'], '%Y-%m-%d')
                ronda, c = Ronda.objects.get_or_create(nombre=request.POST['nombre_ronda'], entidad=entidad,
                                                       inicio=inicio, fin=fin)
                r_credada = True
            if r_credada:
                # Asignamos ronda a la entidad:
                entidad.ronda = ronda
                entidad.save()
                # Código para establecer el usuario gauss en la nueva entidad
                ge = Gauser_extra.objects.create(gauser=g_e.gauser, ronda=ronda, activo=True)
                permisos = Permiso.objects.all()
                ge.permisos.add(*permisos)
                # Código para crear usuario con todos los permisos disponibles a través de los cargos:
                ahora = datetime.now()
                email = 'inventado@%s.com' % entidad.code
                gauser_entidad = Gauser.objects.create_user(entidad.code, email, entidad.code, last_login=ahora)
                g_e_entidad = Gauser_extra.objects.create(gauser=gauser_entidad, ronda=ronda, activo=True)
                try:
                    e_copiar = Entidad.objects.get(id=request.POST['entidad_copiar'])
                    subentidades = Subentidad.objects.filter(entidad=e_copiar)
                    cargos = Cargo.objects.filter(entidad=e_copiar)
                    menus = Menu.objects.filter(entidad=e_copiar)
                    for s in subentidades:
                        s.pk = None
                        s.entidad = entidad
                        s.save()
                    for c in cargos:
                        permisos = c.permisos.all()
                        c.pk = None
                        c.entidad = entidad
                        c.save()
                        c.permisos.add(*permisos)
                        # Los permisos asociados  los cargos son asociados al g_e_entidad
                        g_e_entidad.permisos.add(*permisos)
                    for m in menus:
                        m.pk = None
                        m.entidad = entidad
                        m.save()
                    crear_aviso(request, False, 'Se ha copiado la estructura de la entidad: %s' % e_copiar.name)
                except:
                    crear_aviso(request, False, 'No se ha copiado la estructura de ninguna otra entidad.')

        return render(request, "crea_entidad.html",
                      {
                          'formname': 'crea_entidad',
                          'iconos':
                              ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                                'title': 'Aceptar los cambios realizados', 'permiso': 'edita_subentidades'},
                               ),
                          'oform': oform,
                          'rform': rform,
                          'eform': eform,
                          'organizations': Organization.objects.all(),
                          'entidades': Entidad.objects.filter(name__iregex='[A-Z]'),
                          'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      })
    else:
        crear_aviso(request, False, 'No tienes permiso para acceder a crear una entidad')
        return redirect('/calendario/')


#########################################################################
@gauss_required
def crear_entidades_from_file(request):
    '''
    Esta función ha sido creada para cargar el archivo de Racima que lista los centros:
    Racima -> Gestión -> Seguimiento -> Catálogo de consultas -> Centro -> Datos de los centros
    '''
    g_e = request.session['gauser_extra']

    if g_e.gauser.username == 'gauss':
        from gauss.settings import INSTALLED_APPS
        if request.method == 'POST':
            pass

    else:
        crear_aviso(request, False, 'No tienes permiso para gestionar los módulos de la entidad')
        return redirect('/calendario/')


#########################################################################

@gauss_required
def modulos_entidad(request):
    g_e = request.session['gauser_extra']

    if g_e.gauser.username == 'gauss':
        from gauss.settings import INSTALLED_APPS
        if request.method == 'POST':
            pass

    else:
        crear_aviso(request, False, 'No tienes permiso para gestionar los módulos de la entidad')
        return redirect('/calendario/')


@gauss_required
def get_entidad_general():
    errores = []
    o, c = Organization.objects.get_or_create(organization='Organización_general', iniciales='OG',
                                              web='https://organizaciongeneralgauss.es')
    r, c = Ronda.objects.get_or_create(nombre='Ronda_general', inicio=datetime(2000, 1, 1),
                                       fin=datetime(2100, 1, 1))
    e, c = Entidad.objects.get_or_create(organization=o, ronda=r, code=11235813, name='Entidad_general')
    r.entidad = e
    r.save()
    gauss = Gauser.objects.get(username='gauss')
    Gauser_extra.objects.get_or_create(gauser=gauss, ronda=r, activo=True)
    try:
        for menu_default in Menu_default.objects.all():
            pos = Menu.objects.filter(entidad=e, menu_default__nivel=menu_default.nivel,
                                      menu_default__parent=menu_default.parent).count() + 1
            m, c = Menu.objects.get_or_create(entidad=e, menu_default=menu_default)
            m.texto_menu = menu_default.texto_menu
            m.pos = pos
            m.save()
    except Exception as msg:
        errores.append(str(msg))
    for c in CARGOS:
        try:
            Cargo.objects.get(entidad=e, clave_cargo=c['clave_cargo'], borrable=False)
        except:
            try:
                cargo = Cargo.objects.create(entidad=e, clave_cargo=c['clave_cargo'], borrable=False, cargo=c['cargo'])
                for code_nombre in c['permisos']:
                    cargo.permisos.add(Permiso.objects.get(code_nombre=code_nombre))
            except Exception as msg:
                errores.append(str(msg))
    return e, errores


# ##############################################################################
# ##############################################################################
# Funciones a borrar tras la migración a gauss_asocia
# ##############################################################################
# ##############################################################################

# def load_gauser_extra_educa(request):
#     params_asocia = ['gauser', 'entidad', 'ronda', 'subentidades', 'id_organizacion',
#                      'id_entidad', 'activo', 'observaciones', 'tutor1', 'tutor2', 'clave_ex']
#
#     dict_params = {'gauser_username': 'gauser', 'gauser': 'gauser', 'entidad': 'centro', 'ronda': 'curso_escolar',
#                    'id_organizacion': 'historial',
#                    'id_entidad': 'idcentro', 'activo': 'activo', 'observaciones': 'datos', 'tutor1': 'tutor1',
#                    'tutor2': 'tutor2', 'clave_ex': 'clave_ex', 'grupo': 'grupo'}
#
#     params = ['gauser_username', 'gauser_dni', 'centro', 'curso_escolar', 'historial', 'grupo_nombre',
#               'grupo_clave_ex', 'activo', 'idcentro', 'datos', 'clave_ex', 'educa_pk']
#     data = {}
#     for p in params:
#         try:
#             data[p] = request.GET[p]
#         except:
#             if p == 'gauser_dni':
#                 data['gauser_dni'] = ""
#             else:
#                 data[p] = 'sin_%s' % p
#             logger.info("Error GET con %s\n" % p)
#
#     gauser = Gauser.objects.filter(username__icontains=data['gauser_username'], dni=data['gauser_dni'])
#     if gauser.count() == 1:
#         gauser = gauser[0]
#     elif gauser.count() == 0:
#         logger.info("No gauser con username %s y dni %s\n" % (data['gauser_username'], data['gauser_dni']))
#         return HttpResponse(False)
#     else:
#         logger.info("Varios gauser con username %s y dni %s\n" % (data['gauser_username'], data['gauser_dni']))
#         return HttpResponse(False)
#
#     logger.info("Centro %s\n" % (data['centro']))
#     entidad = Entidad.objects.get(code=data['centro'])
#     logger.info("Entidad %s\n" % (entidad))
#     logger.info("Curso escolar %s\n" % (data['curso_escolar']))
#     ronda = Ronda.objects.get(entidad=entidad, nombre__icontains=data['curso_escolar'])
#     logger.info("Ronda %s\n" % (ronda))
#
#     logger.info("Grupo clave_ex %s y nombre %s\n" % (data['grupo_clave_ex'], data['grupo_nombre']))
#     if data['grupo_clave_ex'] != '0' and data['grupo_nombre'] != '0':
#         try:
#             grupo = Grupo.objects.get(clave_ex__icontains=data['grupo_clave_ex'])
#             logger.info("Grupo identificado por clave_ex %s\n" % (data['grupo_clave_ex']))
#         except:
#             grupo = Grupo.objects.create(nombre=data['grupo_nombre'], clave_ex=data['grupo_clave_ex'], ronda=ronda)
#             logger.info("Grupo creado con clave_ex %s\n" % (data['grupo_clave_ex']))
#     else:
#         grupo = None
#
#     try:
#         ge = Gauser_extra.objects.get(gauser=gauser, entidad=entidad, ronda=ronda)
#         ge.educa_pk = data['educa_pk']
#         ge.save()
#         logger.info("Existe gauser_extra para gauser %s\n" % (ge))
#         try:
#             Gauser_extra_estudios.objects.get(ge=ge, grupo=grupo)
#             logger.info("Existe gauser_extra_estudios %s\n" % (gauser))
#         except:
#             Gauser_extra_estudios.objects.create(ge=ge, grupo=grupo)
#             logger.info("Creado gauser_extra_estudios para ge %s\n" % (ge))
#     except:
#         ge = Gauser_extra.objects.create(gauser=gauser, entidad=entidad, ronda=ronda, id_organizacion=data['historial'],
#                                          activo=data['activo'], id_entidad=data['idcentro'], clave_ex=data['clave_ex'],
#                                          observaciones=data['datos'], educa_pk=data['educa_pk'])
#         Gauser_extra_estudios.objects.create(ge=ge, grupo=grupo)
#         logger.info("Creados gauser_extra y gauser_extra_estudios, ge: %s\n" % (ge))
#
#     data['perfiles'] = request.GET.getlist('perfiles')
#     logger.info("perfiles %s\n" % (', '.join(data['perfiles'])))
#
#     if '12' in data['perfiles'] or 12 in data['perfiles']:
#         ge.subentidades.add(Subentidad.objects.get(entidad=entidad, clave_ex='docente'))
#         logger.info("Added al grupo de docentes %s\n" % (ge))
#     elif '21' in data['perfiles'] or 21 in data['perfiles']:
#         ge.subentidades.add(Subentidad.objects.get(entidad=entidad, clave_ex='madres_padres'))
#         logger.info("Added al grupo de madres %s\n" % (ge))
#     elif '22' in data['perfiles'] or 22 in data['perfiles']:
#         ge.subentidades.add(Subentidad.objects.get(entidad=entidad, clave_ex='alumnos'))
#         logger.info("Added al grupo de alumnos %s\n" % (ge))
#     # if '13' in data['perfiles'] or '14' in data['perfiles'] or '15' in data['perfiles']:
#     else:
#         ge.subentidades.add(Subentidad.objects.get(entidad=entidad, clave_ex='no_docente'))
#         logger.info("Added al grupo de no docentes %s\n" % (ge))
#
#     return HttpResponse('<h1>Trabajo terminado</h1>')

@LogGauss
def linkge(request, code):
    try:
        enlace = EnlaceGE.objects.get(code=code, deadline__gte=timezone.datetime.today().date())
        user = enlace.usuario.gauser
        if user.is_active and enlace.usuario.activo:
            login(request, user)
            request.session["hoy"] = timezone.datetime.today().date()
            request.session[translation.LANGUAGE_SESSION_KEY] = user_language
            request.session["gauser_extra"] = enlace.usuario
            request.session["ronda"] = request.session["gauser_extra"].ronda
            request.session['num_items_page'] = 15
            logger.info('%s se loguea en GAUSS a través de un enlace.' % (request.session["gauser_extra"]))
            return redirect(enlace.enlace)
        else:
            # Si el usuario no está activo lo conduce a la página de inicio
            return redirect('/')
    except:
        try:
            enlace = EnlaceGE.objects.get(code=code)
            # Si llega aquí es porque el enlace está caducado. Se carga en la página de inicio para acceder
            # directamente al mismo tras hacer login en el sistema
            return redirect('/?link=%s&r=%s' % (enlace.enlace, enlace.usuario.ronda.id))
        except:
            return redirect('/')


@permiso_required('acceso_getion_bajas')
def crealinkge(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        asunto = 'Notificación de GAUSS'
        texto = '<p>Este es el correo para tener un enlace:</p>'
        etiqueta = Etiqueta.objects.create(propietario=g_e, nombre='___' + pass_generator(size=15))
        ahora = timezone.datetime.now()
        deadline = ahora + timezone.timedelta(7)
        # for u in usuarios_ronda(g_e.ronda):
        for u in [g_e]:
            enlace = EnlaceGE.objects.create(usuario=u, enlace='/mis_datos/', deadline=deadline)
            link = '%s://%s:%s/linkge/%s' % (
                request.scheme, request.META['SERVER_NAME'], request.META['SERVER_PORT'], enlace.code)
            texto = texto + '<p><a href="%s">%s</a></p>' % (link, link)
            mensaje = Mensaje.objects.create(emisor=g_e, fecha=ahora, tipo='mail', asunto=asunto, mensaje=texto,
                                             borrador=False)
            mensaje.receptores.add(u.gauser)
            mensaje.etiquetas.add(etiqueta)
            crea_mensaje_cola(mensaje)

    codes_menu = []
    for p in g_e.permisos_list:
        codes_menu.append(p.code_nombre)
    menus = Menu.objects.filter(entidad=g_e.ronda.entidad, menu_default__code_menu__in=codes_menu,
                                menu_default__href__regex=r'[a-z]')
    return render(request, "crealinkge.html",
                  {
                      'formname': 'crealinkge',
                      'menus': menus,
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'info-circle', 'texto': 'Ayuda',
                            'title': 'Ayuda sobre está página', 'permiso': 'libre'},),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@permiso_required('acceso_doc_configuration')
def doc_configuration(request):
    g_e = request.session['gauser_extra']
    dces = DocConfEntidad.objects.filter(entidad=g_e.ronda.entidad)
    try:
        DocConfEntidad.objects.get(entidad=g_e.ronda.entidad, predeterminado=True)
    except:
        try:
            dce = dces[0]
            dce.predeterminado = True
            dce.save()
        except:
            dce = DocConfEntidad.objects.create(entidad=g_e.ronda.entidad, predeterminado=True)
            dces = [dce]
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_doc_conf':
            if g_e.has_permiso('acceso_doc_configuration'):
                dce = DocConfEntidad.objects.create(entidad=g_e.ronda.entidad)
                html = render_to_string('doc_configuration_accordion.html', {'docs_conf': [dce], 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            else:
                JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            try:
                dce = dces.get(id=request.POST['id'])
                html = render_to_string('doc_configuration_accordion_content.html', {'doc_conf': dce, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_campo_char':
            try:
                dce = dces.get(id=request.POST['doc_conf'])
                setattr(dce, request.POST['campo'], request.POST['valor'])
                dce.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_campo_select':
            try:
                dce = dces.get(id=request.POST['doc_conf'])
                if request.POST['campo'] == 'predeterminado':
                    for d in dces:
                        d.predeterminado = False
                        d.save()
                    dce.predeterminado = True
                    dce.save()
                    valor = 'Sí'
                elif request.POST['campo'] == 'orientation':
                    o = {'Landscape': 'Portrait', 'Portrait': 'Landscape'}
                    o_es = {'Landscape': 'Horizontal', 'Portrait': 'Vertical'}
                    dce.orientation = o[dce.orientation]
                    dce.save()
                    valor = o_es[dce.orientation]
                else:
                    valor = 'Error'
                return JsonResponse({'ok': True, 'valor': valor, 'id': dce.id, 'campo': request.POST['campo']})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_html':
            if not os.path.exists(os.path.dirname(MEDIA_DOCCONF)):
                os.makedirs(os.path.dirname(MEDIA_DOCCONF))
            try:
                dce = dces.get(id=request.POST['id'])
                if request.POST['editor'] == 'cabecera':
                    dce.header = request.POST['html']
                    # fichero_html = dce.url_header
                else:
                    dce.footer = request.POST['html']
                    # fichero_html = dce.url_footer
                dce.save()
                # html = render_to_string('template_cabecera_pie.html', {'html': request.POST['html']})
                # with open(fichero_html, "w") as html_file:
                #     html_file.write("{0}".format(html))
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_doc_conf':
            try:
                dce = dces.get(id=request.POST['id'])
                if dce.predeterminado:
                    return JsonResponse({'ok': False, 'msg': 'No se puede borrar la configuración predeterminada'})
                else:
                    dce.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
    elif request.method == 'POST' and not request.is_ajax():
        if request.POST['action'] == 'pdf_doc_conf':
            dce = dces.get(id=request.POST['doc_conf'])
            c = render_to_string('docconf_pruebas_template.html', {'g_e': g_e})
            # if not os.path.exists(os.path.dirname(dce.url_pdf)):
            #     os.makedirs(os.path.dirname(dce.url_pdf))
            # pdfkit.from_string(c, dce.url_pdf, dce.get_opciones)
            # fich = open(dce.url_pdf, 'rb')
            fich = pdfkit.from_string(c, False, dce.get_opciones)
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=doc_conf%s.pdf' % dce.id
            return response

    return render(request, "doc_configuration.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nueva',
                            'permiso': 'acceso_doc_configuration',
                            'title': 'Nueva configuración de documento'},
                           ),
                      'formname': 'doc_configuration',
                      'docs_conf': dces,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


def selectgcs_organization(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        if request.method == 'GET':
            rondas = Entidad.objects.filter(organization=g_e.ronda.entidad.organization).values_list('ronda__id',
                                                                                                     flat=True)
            texto = request.GET['q']
            palabras = texto.split()
            q = Q(gauser__first_name__icontains=palabras[0]) | Q(gauser__last_name__icontains=palabras[0]) | Q(
                gauser__dni__icontains=palabras[0]) | Q(gauser__username__icontains=palabras[0])
            for palabra in palabras[1:]:
                qnueva = Q(gauser__first_name__icontains=palabra) | Q(gauser__last_name__icontains=palabra) | Q(
                    gauser__dni__icontains=palabra) | Q(gauser__username__icontains=palabra)
                q = q & qnueva
            ges = Gauser_extra.objects.filter(q & Q(ronda__id__in=rondas))
            # q1 = Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)
            # q2 = Q(ronda__id__in=rondas)
            # ges = Gauser_extra.objects.filter(q1 & q2)
            options = []
            for ge in ges.distinct():
                options.append(
                    {'id': ge.id, 'first_name': ge.gauser.first_name, 'last_name': ge.gauser.last_name,
                     'entidad': ge.ronda.entidad.name, 'tipo': 'g'})
            return JsonResponse(options, safe=False)
        else:
            return JsonResponse({'ok': False, 'm': 'No es GET'})
    else:
        return JsonResponse({'ok': False, 'm': 'No es ajax'})


def selectgcs(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        if request.method == 'GET':
            texto = request.GET['q']
            if request.GET['scope'] == 'ronda':
                entidades = [g_e.ronda.entidad]
                rondas = [g_e.ronda]
            else:
                entidades = Entidad.objects.filter(organization=g_e.ronda.entidad.organization)
                rondas = entidades.values_list('ronda', flat=True)

            if 'subs[]' in request.GET:
                # subs = Subentidad.objects.filter(entidad=g_e.ronda.entidad, id__in=request.GET.getlist('subs[]'))
                subs = Subentidad.objects.filter(entidad__in=entidades, id__in=request.GET.getlist('subs[]'))
            else:
                subs = Subentidad.objects.none()
            if 'cars[]' in request.GET:
                # cars = Cargo.objects.filter(entidad=g_e.ronda.entidad, clave_cargo__in=request.GET.getlist('cars[]'))
                cars = Cargo.objects.filter(entidad__in=entidades, clave_cargo__in=request.GET.getlist('cars[]'))
            else:
                cars = Cargo.objects.none()
            ges, cargos, subentidades = Gauser_extra.objects.none(), Cargo.objects.none(), Subentidad.objects.none()
            for tipo in request.GET['tipo']:  # tipo=c implica buscar cargos, tipo=s subentidades y tipo=g gauser_extras
                if tipo == 'g':
                    if request.GET['scope'] == 'ronda':
                        usposibles = usuarios_ronda(g_e.ronda, subentidades=subs, cargos=cars)
                    else:
                        usposibles = usuarios_organization(g_e.ronda, subentidades=subs, cargos=cars)
                    palabras = texto.split()
                    q = Q(gauser__first_name__icontains=palabras[0]) | Q(gauser__last_name__icontains=palabras[0]) | Q(
                        gauser__dni__icontains=palabras[0]) | Q(gauser__username__icontains=palabras[0])
                    for palabra in palabras[1:]:
                        qnueva = Q(gauser__first_name__icontains=palabra) | Q(gauser__last_name__icontains=palabra) | Q(
                            gauser__dni__icontains=palabra) | Q(gauser__username__icontains=palabra)
                        q = q & qnueva
                    # ges = usronda.filter(q)
                    ges = usposibles.filter(q)
                elif tipo == 'c':
                    if cars:
                        cargos = cars
                    else:
                        cargos = Cargo.objects.filter(entidad__in=entidades, cargo__icontains=texto)
                elif tipo == 's':
                    if subs:
                        subentidades = subs
                    else:
                        subentidades = Subentidad.objects.filter(entidad__in=entidades, nombre__icontains=texto)
            # sub_alumnos = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='alumnos')
            # usuarios = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_alumnos])
            # filtrados = usuarios.filter(Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto))
            options = []
            for ge in ges.distinct():
                try:
                    grupo = ge.gauser_extra_estudios.grupo.nombre
                    tutor = ge.gauser_extra_estudios.tutor.gauser.get_full_name()
                    cotutor = ge.gauser_extra_estudios.cotutor.gauser.get_full_name()
                except:
                    grupo, tutor, cotutor = '', '', ''
                cargos_ge = [c.cargo for c in ge.cargos.all()]
                options.append(
                    {'id': ge.id, 'first_name': ge.gauser.first_name, 'last_name': ge.gauser.last_name,
                     'grupo': grupo, 'tutor': tutor, 'cotutor': cotutor, 'tipo': 'g', 'cargos': ', '.join(cargos_ge),
                     'entidad': ge.ronda.entidad.name})
            for c in cargos.distinct():
                options.append({'id': c.id, 'cargo': c.cargo, 'tipo': 'c', 'entidad': c.entidad.name})
            for s in subentidades.distinct():
                options.append({'id': s.id, 'subentidad': s.nombre, 'tipo': 's', 'entidad': s.entidad.name})
            return JsonResponse(options, safe=False)
        else:
            return JsonResponse({'ok': False, 'm': 'No es GET'})
    else:
        return JsonResponse({'ok': False, 'm': 'No es ajax'})


def decode_selectgcs(coded_ids, ronda):
    ges_ids = [int(idx[1:]) for idx in coded_ids if idx.startswith('g')]
    ges = Gauser_extra.objects.filter(id__in=ges_ids, ronda=ronda)
    cs_ids = [int(idx[1:]) for idx in coded_ids if idx.startswith('c')]
    cs = Cargo.objects.filter(id__in=cs_ids, entidad=ronda.entidad)
    ss_ids = [int(idx[1:]) for idx in coded_ids if idx.startswith('s')]
    ss = Subentidad.objects.filter(id__in=ss_ids, entidad=ronda.entidad)
    return ges, cs, ss


def decode_select_allges(coded_ids, ronda):
    ges_ids = [int(idx[1:]) for idx in coded_ids if idx.startswith('g')]
    cs_ids = [int(idx[1:]) for idx in coded_ids if idx.startswith('c')]
    ss_ids = [int(idx[1:]) for idx in coded_ids if idx.startswith('s')]
    ges = usuarios_ronda(ronda)
    return ges.filter(Q(id__in=ges_ids) | Q(cargos__id__in=cs_ids) | Q(subentidades__id__in=ss_ids)).distinct()


#############################################################################
####################### API llamadas desde otro dominio #####################
#############################################################################

dic = {'first_name': '', 'last_name': '', 'address': '', 'sexo': '',
       'email': '', 'telfij': '', 'telmov': '',
       'nacimiento': '', 'dni': '',
       'first_name_tutor1': '', 'dni_tutor1': '',
       'last_name_tutor1': '',
       'telfij_tutor1': '',
       'telmov_tutor1': '', 'email_tutor1': '',
       'first_name_tutor2': '', 'dni_tutor2': '',
       'last_name_tutor2': '',
       'telfij_tutor2': '',
       'telmov_tutor2': '', 'email_tutor2': '',
       'observaciones': '', 'num_cuenta_bancaria': ''}

dic_arvutur = {'first_name': '', 'last_name': '', 'address': '', 'sexo': '',
               'email': '', 'telfij': '', 'telmov': '',
               'nacimiento': '', 'dni': '',
               'observaciones': '', 'num_cuenta_bancaria': ''}


def postnewreserva(request, entidad_code):
    sleep(3)
    try:
        entidad = Entidad.objects.get(code=entidad_code)
        errores = ''
        campos = ConfiguraReservaPlaza.objects.filter(entidad=entidad)
        for campo in campos:
            if campo.required:
                if campo.campo in request.GET:
                    if request.GET[campo.campo] == '' or request.GET[campo.campo] == None:
                        errores += '<p>El campo "%s" es obligatorio</p>' % campo.get_campo_display()
                else:
                    errores += '<p>El campo "%s" es obligatorio</p>' % campo.get_campo_display()
        if errores == '':
            reserva = Reserva_plaza.objects.create(entidad=entidad)
            for campo in campos:
                if campo.campo in request.GET:
                    setattr(reserva, campo.campo, request.GET[campo.campo])
            # form = Reserva_plazaForm(request.GET, instance=reserva)
            # form.save()
            reserva.save()
            gauss = Gauser_extra.objects.get(ronda=entidad.ronda, gauser__username='gauss')
            permiso = Permiso.objects.get(code_nombre='recibe_aviso_reserva')
            receptores_id = Gauser_extra.objects.filter(ronda=entidad.ronda, permisos__in=[permiso]).values_list(
                'gauser__id', flat=True)
            receptores = Gauser.objects.filter(id__in=receptores_id)
            mensaje = render_to_string('mensaje_reserva_grabada.html',
                                       {'crps': campos, 'reserva': reserva, 'mail': True})
            encolar_mensaje(emisor=gauss, receptores=receptores, asunto='Solicitud de plaza en %s' % entidad.name,
                            html=mensaje, etiqueta='reservas%s' % entidad.id)
            ok = True
        else:
            ok = False
        return HttpResponse('informa_reserva(%s)' % json.dumps({'ok': ok, 'mensaje': errores}))
    except Exception as msg:
        return HttpResponse('informa_reserva(%s)' % json.dumps({'ok': False, 'mensaje': str(msg)}))


def arreglar_dnis(request):
    '''
    Los DNIs deberían tener 8 números y una letra (9 caracteres). Racima devuelve DNIs
    con 8 caracteres cuando la primera cifra es un 0. Esto genera problemas al identificar
    los usuarios a través de su DNI.
    Este problema fue detectado al importar datos para evaluar funcionarios en prácticas.
    '''
    Gauser.objects.extra(where=["CHAR_LENGTH(dni) = 8"])


@gauss_required
def crear_ges_sies2ies(request):
    # Función para crear gauser_extras en los IES a partir de los usuarios de sus secciones
    # En primer lugar cargamos las SIES:
    msgs = 'Creación de GES de SIES a IES realizada. <br>'
    siess = EntidadExtra.objects.filter(depende_de__isnull=False)
    for sies in Entidad.objects.filter(entidadextra__depende_de__isnull=False):
        try:
            ies = sies.entidadextra.depende_de
            cargo_ies = Cargo.objects.get(entidad=ies, clave_cargo='g_docente', borrable=False)
            msgs += '<br><br>' + str(ies) + '<br>'
            for ge_sies in Gauser_extra.objects.filter(ronda=sies.ronda):
                try:
                    ge_ies, c = Gauser_extra.objects.get_or_create(ronda=ies.ronda, gauser=ge_sies.gauser)
                    ge_ies.activo = True
                    ge_ies.puesto = ge_sies.puesto
                    ge_ies.tipo_personal = ge_sies.tipo_personal
                    ge_ies.jornada_contratada = ge_sies.jornada_contratada
                    ge_ies.cargos.add(cargo_ies)
                    ge_ies.save()
                    msgs += str(ge_sies) + '-->' + str(ge_ies) + '<br>'
                except Exception as msg2:
                    msgs += 'for2: ' + str(msg2)
        except Exception as msg1:
            msgs += 'for1: ' + str(msg1)
    return HttpResponse(msgs)


@gauss_required
def add_permiso_cargo(request):
    try:
        clave_cargo = request.GET['clave_cargo']
    except:
        return HttpResponse('<p>La solicitud no contiene el parámetro "clave_cargo"</p>')
    try:
        code_nombre = request.GET['code_nombre']
    except:
        return HttpResponse('<p>La solicitud no contiene el parámetro "code_nombre"</p>')
    try:
        permiso = Permiso.objects.get(code_nombre=code_nombre)
    except:
        return HttpResponse('<p>El permiso indicado no existe</p>')
    if 'entidad' in request.GET:
        try:
            entidad = Entidad.objects.get(code=request.GET['entidad'])
            cargos = Cargo.objects.filter(clave_cargo=clave_cargo, entidad=entidad)
            if cargos.count() == 0:
                return HttpResponse('<p>En la entidad indicada no existe el cargo %s</p>' % clave_cargo)
        except:
            return HttpResponse('<p>La entidad indicada no existe</p>')
    else:
        cargos = Cargo.objects.filter(clave_cargo=clave_cargo)
        if cargos.count() == 0:
            return HttpResponse('<p>No existe ninguna entidad con el cargo %s</p>' % clave_cargo)
    for cargo in cargos:
        cargo.permisos.add(permiso)
    return HttpResponse('<p>Proceso de asignación del permiso finalizado</p>')


@gauss_required
def del_permiso_cargo(request):
    try:
        clave_cargo = request.GET['clave_cargo']
    except:
        return HttpResponse('<p>La solicitud no contiene el parámetro "clave_cargo"</p>')
    try:
        code_nombre = request.GET['code_nombre']
    except:
        return HttpResponse('<p>La solicitud no contiene el parámetro "code_nombre"</p>')
    try:
        permiso = Permiso.objects.get(code_nombre=code_nombre)
    except:
        return HttpResponse('<p>El permiso indicado no existe</p>')
    if 'entidad' in request.GET:
        try:
            entidad = Entidad.objects.get(code=request.GET['entidad'])
            cargos = Cargo.objects.filter(clave_cargo=clave_cargo, entidad=entidad)
            if cargos.count() == 0:
                return HttpResponse('<p>En la entidad indicada no existe el cargo %s</p>' % clave_cargo)
        except:
            return HttpResponse('<p>La entidad indicada no existe</p>')
    else:
        cargos = Cargo.objects.filter(clave_cargo=clave_cargo)
        if cargos.count() == 0:
            return HttpResponse('<p>No existe ninguna entidad con el cargo %s</p>' % clave_cargo)
    for cargo in cargos:
        cargo.permisos.remove(permiso)
    return HttpResponse('<p>Proceso de borrado del permiso finalizado</p>')
