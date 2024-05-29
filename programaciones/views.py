# -*- coding: utf-8 -*-
import re
import pytz
from datetime import date, datetime
import simplejson as json
import unicodedata
import os
import zipfile
import shutil
import locale
from math import modf
import logging
import requests
import xlrd
from bs4 import BeautifulSoup
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q, Sum
from django import forms
from django.forms import ModelForm
from django.http import HttpResponse, JsonResponse, FileResponse
from django.template.loader import render_to_string
from django.core.files.base import File
from django.core.paginator import Paginator
from django.utils.timezone import now

from autenticar.control_acceso import permiso_required, gauss_required
from autenticar.models import Gauser
# from autenticar.control_acceso import access_required
from entidades.models import Cargo, EntidadExtra, DocConfEntidad
from entidades.templatetags.entidades_extras import profesorado
from gauss.funciones import usuarios_ronda, usuarios_de_gauss, get_dce, clone_object, genera_pdf
from programaciones.models import *
from gauss.rutas import RUTA_BASE, MEDIA_PROGRAMACIONES
from mensajes.views import crear_aviso
from mensajes.models import Aviso
from estudios.models import ETAPAS, Gauser_extra_estudios, PerfilSalida, DescriptorOperativo, TablaCompetenciasClave

locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')

logger = logging.getLogger('django')


def pecjson(request, code):
    entidad = Entidad.objects.get(code=code)
    pec = PEC.objects.get(entidad=entidad)
    archivos = pec.pecdocumento_set.all()
    docs = [{'title': a.doc_nombre, 'url': a.doc_file.url} for a in archivos]
    data = {
        'signos': {'title': 'Signos de identidad del centro', 'text': pec.signos},
        'organizacion': {'title': 'Organización general del centro', 'text': pec.organizacion},
        'lineapedagogica': {'title': 'Línea pedagógica', 'text': pec.lineapedagogica},
        'participacion': {'title': 'Modelo de participación en la vida escolar', 'text': pec.participacion},
        'proyectos': {'title': 'Proyectos que desarrolla el centro', 'text': pec.proyectos},
        'documentos': docs
    }
    a = 'proyecto('
    b = json.dumps(data)
    c = ')'
    # jsonresponse = JsonResponse(data)
    # jsonresponse['Access-Control-Allow-Origin'] = 'https://stackoverflow.com'
    # return jsonresponse
    # return JsonResponse(data)
    response = HttpResponse(a + b + c)
    # response['Access-Control-Allow-Origin'] = 'https://stackoverflow.com'
    return response


def pgajson(request, code):
    entidad = Entidad.objects.get(code=code)
    ronda = entidad.ronda
    pga = PGA.objects.get(ronda=ronda)
    archivos = pga.pgadocumento_set.all()
    docs = [{'title': a.doc_nombre, 'url': a.doc_file.url} for a in archivos]
    data = {
        'centro': entidad.name,
        'curso_escolar': ronda.nombre,
        'documentos': docs
    }
    a = 'pga('
    b = json.dumps(data)
    c = ')'
    # return JsonResponse(data)
    return HttpResponse(a + b + c)


@permiso_required('acceso_cargar_programaciones')
def cargar_programaciones(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and not request.is_ajax():
        action = request.POST['action']
        if action == 'descargar_fichero_programacion':
            p = ProgramacionSubida.objects.get(sube__ronda=g_e.ronda, id=request.POST['programacion'])
            if g_e == p.sube or g_e.has_permiso('descarga_programaciones'):
                response = HttpResponse(p.archivo, content_type=p.content_type)
                response['Content-Disposition'] = 'attachment; filename=%s' % p.filename
                return response
            else:
                crear_aviso(request, False, 'No tienes permiso para descargar programaciones cargadas por otros')
        elif action == 'generar_zip_pga' and g_e.has_permiso('descarga_pga'):
            try:
                doc_pga = 'Configuración de documentos de la PGA'
                dce = get_dce(g_e.ronda.entidad, doc_pga)
                pga = PGA.objects.get(ronda=g_e.ronda)
                # try:
                # Procesado del archivo de aspectos de la PGA
                c = render_to_string('aspectos_generales_pga2pdf.html', {'pga': pga, 'dce': dce})
                ruta = rutas_aspectos_pga(pga)['absoluta']
                nombre_fichero = 'aspectos_generales_pga'
                if os.path.exists('%s%s.pdf' % (ruta, nombre_fichero)):
                    os.remove('%s%s.pdf' % (ruta, nombre_fichero))
                genera_pdf(c, dce, ruta_archivo=ruta)
                if os.path.exists('%s%s.html' % (ruta, nombre_fichero)):
                    os.remove('%s%s.html' % (ruta, nombre_fichero))
                # Procesado del archivo de aspectos del PEC
                pec = PEC.objects.get(entidad=g_e.ronda.entidad)
                c = render_to_string('aspectos_generales_pec2pdf.html', {'pec': pec, 'dce': dce})
                ruta = rutas_pec(pec)['absoluta']
                nombre_fichero = 'aspectos_generales_pec'
                if os.path.exists('%s%s.pdf' % (ruta, nombre_fichero)):
                    os.remove('%s%s.pdf' % (ruta, nombre_fichero))
                genera_pdf(c, dce, ruta_archivo=ruta)
                if os.path.exists('%s%s.html' % (ruta, nombre_fichero)):
                    os.remove('%s%s.html' % (ruta, nombre_fichero))
                # Generación del ZIP que contiene toda la PGA
                ruta_centro = ruta_programaciones(g_e.ronda, tipo='centro')
                ruta_curso_escolar = ruta_programaciones(g_e.ronda, tipo='ronda')
                fichero = "PGA_{0}_{1}".format(g_e.ronda.entidad.code, slugify(g_e.ronda.nombre))
                ruta_zip = ruta_programaciones(g_e.ronda, tipo='centro')
                try:
                    # Create target Directory. Si existiera se produciría la excepción
                    os.mkdir(ruta_curso_escolar)
                    os.chdir(ruta_curso_escolar)  # Determino el directorio de trabajo
                except FileExistsError:
                    os.chdir(ruta_curso_escolar)  # Determino el directorio de trabajo
                shutil.make_archive(ruta_zip + fichero, 'zip', ruta_curso_escolar)
                fich = open(ruta_zip + fichero + '.zip', 'rb')
                crear_aviso(request, True, "%s genera y descarga %s" % (g_e.gauser.get_full_name(), fichero))
                response = HttpResponse(fich, content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=%s' % (fichero + '.zip')
                return response
            except Exception as msg:
                crear_aviso(request, False, 'Se ha producido un error: %s' % str(msg))
                # return JsonResponse({'error': True, 'msg': str(msg)})
            # except:
            #     pass

            # curso_escolar = g_e.ronda.nombre.replace('/', '-')
            # ruta_centro = MEDIA_PROGRAMACIONES + "{0}/".format(g_e.ronda.entidad.code)
            # ruta_curso_escolar = "{0}{1}/".format(ruta_centro, curso_escolar)
            # fichero = "programaciones_{0}_{1}.zip".format(g_e.ronda.entidad.code, curso_escolar)
            # ruta_fichero = "{0}{1}".format(ruta_centro, fichero)
            # # Comprobamos si existe un fichero zip en el directorio de las programaciones. Esto solo
            # # ocurre hasta el curso 2019-2020. A partir de ese curso las programaciones se guardan
            # # en el directorio asociado al centro y no al del curso:
            # if os.path.exists("{0}{1}".format(ruta_curso_escolar, fichero)):
            #     os.remove("{0}{1}".format(ruta_curso_escolar, fichero))
            # try:
            #     # Create target Directory
            #     os.mkdir(ruta_centro)
            #     os.chdir(ruta_centro)  # Determino el directorio de trabajo
            # except FileExistsError:
            #     os.chdir(ruta_centro)  # Determino el directorio de trabajo
            #
            # # zip_file = zipfile.ZipFile(ruta_fichero, 'w')
            # # for root, dirs, files in os.walk('./'):  # Se comprime el directorio actual determinado por "ruta"
            # #     for file in files:
            # #         zip_file.write(os.path.join(root, file))
            # # zip_file.close()
            # output_filename = "programaciones_{0}_{1}".format(g_e.ronda.entidad.code, curso_escolar)
            # shutil.make_archive(output_filename, 'zip', ruta_curso_escolar)
            # fich = open(ruta_fichero, 'rb')
            # crear_aviso(request, True,
            #             "Genera y descarga .zip con programaciones: %s" % (g_e.gauser.get_full_name()))
            # response = HttpResponse(fich, content_type='application/zip')
            # response['Content-Disposition'] = 'attachment; filename=%s' % fichero
            # return response

    return render(request, "cargar_programaciones.html",
                  {
                      'formname': 'cargar_programaciones',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'check', 'texto': 'Descarga PGA',
                            'title': 'Decarga la PGA completa', 'permiso': 'descarga_pga'},),
                      'cursos': Curso.objects.filter(ronda=g_e.ronda),
                      'etapas': ETAPAS,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def cargar_programaciones_ajax(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        action = request.POST['action']
        if action == 'open_accordion':
            curso = Curso.objects.get(id=request.POST['id'])
            materias = curso.materia_set.all()
            html = render_to_string('cargar_programaciones_formulario_content.html', {'g_e': g_e, 'curso': curso})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'delete_programacion':
            try:
                p = ProgramacionSubida.objects.get(sube__ronda=g_e.ronda, id=request.POST['programacion'])
                if p.sube == g_e or g_e.has_permiso('borra_programaciones_cargadas'):
                    curso = p.materia.curso
                    # Borramos el posible fichero existente:
                    # ruta = os.path.join(RUTA_BASE, p.archivo.url)
                    ruta = "%s%s" % (RUTA_BASE, p.archivo.url)
                    os.remove(ruta)
                    # Fin de las instrucciones para borrar el posible archivo
                    p.delete()
                    html = render_to_string('cargar_programaciones_formulario_content.html',
                                            {'curso': curso, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html, 'curso': curso.id, 'mensaje': False})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permiso para borrar esta programación'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Ha ocurrido un error y no se ha podido borrar'})
    else:
        if request.POST['action'] == 'upload_programacion_file':
            materia = Materia.objects.get(id=request.POST['materia'])
            curso = materia.curso
            n_files = int(request.POST['n_files'])
            mensaje = False
            if g_e.has_permiso('carga_programaciones'):
                for i in range(n_files):
                    fichero = request.FILES['fichero_xhr' + str(i)]
                    try:
                        p = ProgramacionSubida.objects.get(materia=materia)
                        p.sube = g_e
                        p.archivo = fichero
                        p.content_type = fichero.content_type
                        p.save()
                    except:
                        ProgramacionSubida.objects.create(materia=materia, sube=g_e, archivo=fichero,
                                                          content_type=fichero.content_type)
            else:
                mensaje = 'No tienes permiso para cargar programaciones.'
            html = render_to_string('cargar_programaciones_formulario_content.html', {'curso': curso, 'g_e': g_e})
            return JsonResponse({'ok': True, 'html': html, 'curso': curso.id, 'mensaje': mensaje})


@permiso_required('acceso_departamentos_centro_educativo')
def departamentos_centro_educativo(request):
    # Esta función esta inoperativa. Sólo se ha copiado de subentidades y cambiado nombres
    g_e = request.session['gauser_extra']
    ronda = request.session['ronda']
    if request.method == 'POST':
        action = request.POST['action']
        logger.info('%s post %s' % (g_e, action))
        # if action == 'formulario_departamento' and request.is_ajax():
        #     if request.POST['id']:
        #         departamento = Departamento.objects.get(id=request.POST['id'])
        #         g_es = usuarios_de_gauss(entidad=g_e.ronda.entidad, departamentos=[departamento]).values_list('id',
        #                                                                                              'gauser__last_name',
        #                                                                                              'gauser__first_name')
        #         keys = ('id', 'text')
        #         usuarios = json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in g_es])
        #         form = DepartamentoForm(instance=departamento)
        #     else:
        #         usuarios = None
        #         form = DepartamentoForm()
        #     data = render_to_string("formulario_departamento.html", {'form': form, 'usuarios': usuarios})
        #     return HttpResponse(data)

        if action == 'guardar_departamento' and request.is_ajax():
            if request.POST['id_departamento_selected']:
                departamento = Departamento.objects.get(id=request.POST['id_departamento_selected'])
                g_es = usuarios_de_gauss(entidad=g_e.ronda.entidad, departamentos=[departamento])
            else:
                departamento = Departamento(entidad=g_e.ronda.entidad)
                g_es = []
            form = DepartamentoForm(request.POST, instance=departamento)
            if form.is_valid():
                departamento = form.save()
                for ge in g_es:
                    ge.departamentos.remove(departamento)
                try:
                    g_es = Gauser_extra.objects.filter(id__in=request.POST['usuarios_departamento'].split(','))
                except:
                    g_es = []
                for ge in g_es:
                    ge.departamentos.add(departamento)
                error = None
                crear_aviso(request, True,
                            'Modificación/Creación del departamento: <strong>%s</strong>' % departamento.nombre)
            else:
                crear_aviso(request, True,
                            'Error en la modificación/mreación del departamento: <strong>%s</strong>' % departamento.nombre)
                error = form.errors
            data = render_to_string("list_departamentos.html",
                                    {'departamentos': Departamento.objects.filter(entidad=g_e.ronda.entidad,
                                                                                  fecha_expira__gt=ronda.fin),
                                     'error': error, 'request': request})
            return HttpResponse(data)
        elif action == 'mostrar_usuarios' and request.is_ajax():
            departamento = Departamento.objects.get(id=request.POST['id'])
            data = render_to_string("list_usuarios_departamento.html",
                                    {'departamento': departamento, 'tipo': 'mostrar'})
            return HttpResponse(data)
        elif action == 'ocultar_usuarios' and request.is_ajax():
            departamento = Departamento.objects.get(id=request.POST['id'])
            data = render_to_string("list_usuarios_departamento.html",
                                    {'departamento': departamento, 'tipo': 'ocultar'})
            return HttpResponse(data)

    departamentos = Departamento.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=date.today())
    return render(request, "departamentos.html",
                  {
                      'formname': 'departamentos',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                            'title': 'Aceptar los cambios realizados', 'permiso': 'edita_departamentos'},
                           {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Secciones',
                            'title': 'Ver la lista de secciones/departamentos/departamentos creadas',
                            'permiso': 'edita_departamentos'},
                           {'tipo': 'button', 'nombre': 'plus', 'texto': 'Sección',
                            'title': 'Añadir una nueva sección/departamento/departamento',
                            'permiso': 'edita_departamentos'},
                           {'tipo': 'button', 'nombre': 'pencil', 'texto': 'Editar',
                            'title': 'Editar la sección/departamento/departamento para su modificación',
                            'permiso': 'edita_departamentos'},
                           {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                            'title': 'Borrar la sección/departamento/departamento seleccionada',
                            'permiso': 'edita_departamentos'}),
                      'departamentos': departamentos,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def departamentos_centro_educativo_ajax(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        action = request.POST['action']
        if action == 'add_departamento' and g_e.has_permiso('crea_departamentos'):
            departamento = Departamento.objects.create(entidad=g_e.ronda.entidad, nombre='Nueva sección/departamento',
                                                       edad_min=1,
                                                       edad_max=90, observaciones='')
            data = render_to_string("accordion_departamento.html", {'departamento': departamento})
            return HttpResponse(data)
        elif action == 'open_accordion':
            departamento = Departamento.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            departamentos = Departamento.objects.filter(entidad=g_e.ronda.entidad,
                                                        fecha_expira__gte=date.today()).exclude(
                id=departamento.id)
            # g_es = usuarios_de_gauss(entidad=g_e.ronda.entidad, departamentos=[departamento]).values_list('id',
            #                                                                                      'gauser__last_name',
            #                                                                                      'gauser__first_name')
            g_es = usuarios_de_gauss(entidad=g_e.ronda.entidad, departamentos=[departamento])
            # keys = ('id', 'text')
            # usuarios = json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in g_es])
            data = render_to_string("formulario_departamento.html",
                                    {'entidad': g_e.ronda.entidad, 'g_es': g_es, 'departamento': departamento,
                                     'gauser_extra': g_e, 'request': request, 'departamentos': departamentos
                                     })
            return HttpResponse(data)
        elif action == 'del_departamento' and g_e.has_permiso('borra_departamentos'):
            departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
            nombre = departamento.nombre
            departamento.delete()
            return HttpResponse('Se ha borrado el departamento/sección: <strong>%s</strong>' % nombre)
        elif action == 'nombre_departamento' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.nombre = request.POST['nombre']
                departamento.save()
                return JsonResponse({'ok': True, 'nombre': departamento.nombre})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'edad_min_departamento' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.edad_min = int(request.POST['edad_min'])
                departamento.save()
                return JsonResponse({'ok': True, 'edad_min': departamento.edad_min})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'edad_max_departamento' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.edad_max = int(request.POST['edad_max'])
                departamento.save()
                return JsonResponse({'ok': True, 'edad_max': departamento.edad_max})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'mensajes' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.mensajes = not departamento.mensajes
                departamento.save()
                return JsonResponse({'ok': True, 'mensajes': ['No', 'Sí'][departamento.mensajes]})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'observaciones' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.observaciones = request.POST['observaciones']
                departamento.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'buscar_usuarios':
            texto = request.POST['q']
            usuarios = usuarios_de_gauss(g_e.ronda.entidad)
            filtrado = usuarios.filter(Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto))
            return HttpResponse(json.dumps([{'id': u.id, 'text': u.gauser.get_full_name()} for u in filtrado]))
        elif action == 'usuarios_departamento' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                old_users = usuarios_de_gauss(g_e.ronda.entidad, departamentos=[departamento])
                new_users = Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('users[]'))
                added_users = new_users.exclude(id__in=old_users)
                removed_users = old_users.exclude(id__in=new_users)
                for u in added_users:
                    u.departamentos.add(departamento)
                for u in removed_users:
                    u.departamentos.remove(departamento)
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'sub_padre' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                pk = request.POST['sub_padre']
                if pk:
                    departamento.parent = Departamento.objects.get(pk=pk, entidad=g_e.ronda.entidad)
                else:
                    departamento.parent = None
                departamento.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'fecha_expira' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.fecha_expira = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
                departamento.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'clave_ex' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.clave_ex = request.POST['clave_ex']
                departamento.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        else:
            return JsonResponse({'ok': False})


@permiso_required('acceso_profesores_centro_educativo')
def profesores_centro_educativo(request):
    g_e = request.session['gauser_extra']
    profesores = usuarios_ronda(g_e.ronda, subentidades=False).filter(subentidades__clave_ex='docente')
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'change_especialidad':
            try:
                especialidad = Especialidad_entidad.objects.get(ronda=g_e.ronda, id=request.POST['especialidad'])
                ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                try:
                    ge.gauser_extra_programaciones.especialidad = especialidad
                    ge.gauser_extra_programaciones.save()
                    return JsonResponse({'ok': True})
                except:
                    gep = Gauser_extra_programaciones.objects.create(ge=ge)
                    gep.especialidad = especialidad
                    gep.save()
                    return JsonResponse({'ok': True, 'creado': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'change_departamento':
            try:
                departamento = Departamento.objects.get(ronda=g_e.ronda, id=request.POST['departamento'])
                ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                try:
                    ge.gauser_extra_programaciones.departamento = departamento
                    ge.gauser_extra_programaciones.save()
                    return JsonResponse({'ok': True})
                except:
                    gep = Gauser_extra_programaciones.objects.create(ge=ge)
                    gep.departamento = departamento
                    gep.save()
                    return JsonResponse({'ok': True, 'creado': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'change_puesto':
            try:
                puesto = request.POST['puesto']
                ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                try:
                    ge.gauser_extra_programaciones.puesto = puesto
                    ge.gauser_extra_programaciones.save()
                    return JsonResponse({'ok': True})
                except:
                    gep = Gauser_extra_programaciones.objects.create(ge=ge)
                    gep.puesto = puesto
                    gep.save()
                    return JsonResponse({'ok': True, 'creado': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'change_jefe_departamento':
            try:
                jefe = {'true': True, 'false': False}[request.POST['checked']]
                ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
                try:
                    ge.gauser_extra_programaciones.jefe = jefe
                    ge.gauser_extra_programaciones.save()
                    return JsonResponse({'ok': True})
                except:
                    gep = Gauser_extra_programaciones.objects.create(ge=ge)
                    gep.jefe = jefe
                    gep.save()
                    return JsonResponse({'ok': True, 'creado': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
    respuesta = {
        'formname': 'profesores_centro_educativo',
        'profesores': profesores,
        'departamentos': Departamento.objects.filter(ronda=g_e.ronda),
        'especialidades': Especialidad_entidad.objects.filter(ronda=g_e.ronda),
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "profesores_centro_educativo.html", respuesta)


@permiso_required('acceso_resultados_aprendizaje')
def resultados_aprendizaje(request):
    g_e = request.session['gauser_extra']
    if request.method == 'GET':
        materia = Materia.objects.get(id=request.GET['m'], curso__ronda__entidad=g_e.ronda.entidad)
        m, c = Materia_programaciones.objects.get_or_create(materia=materia)

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'add_resultado':
            try:
                materia = Materia.objects.get(id=request.POST['id'], curso__ronda=g_e.ronda)
                r = Resultado_aprendizaje.objects.create(materia=materia.materia_programaciones,
                                                         resultado='Resultado añadido')
                html = render_to_string('resultados_aprendizaje_accordion.html', {'r': r})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'open_accordion':
            try:
                resultado = Resultado_aprendizaje.objects.get(id=request.POST['id'],
                                                              materia__materia__curso__ronda=g_e.ronda)
                html = render_to_string('resultados_aprendizaje_accordion_content.html', {'r': resultado})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_resultado':
            try:
                r = Resultado_aprendizaje.objects.get(id=request.POST['id'])
                if r.materia.materia.curso.ronda == g_e.ronda:
                    r.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No puedes borrar el resultado de aprendizaje'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'change_resultado':
            try:
                r = Resultado_aprendizaje.objects.get(id=request.POST['id'])
                if r.materia.materia.curso.ronda == g_e.ronda:
                    r.resultado = request.POST['html']
                    r.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No puedes modificar el resultado de aprendizaje'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'add_objetivo':
            try:
                r = Resultado_aprendizaje.objects.get(id=request.POST['id'], materia__materia__curso__ronda=g_e.ronda)
                o = Objetivo.objects.create(materia=r.materia, resultado_aprendizaje=r, texto="Conseguir ...",
                                            crit_eval='El alumno consigue ...')
                html = render_to_string('resultados_aprendizaje_accordion_content_objetivo.html', {'o': o})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'mod_objetivo':
            try:
                o = Objetivo.objects.get(id=request.POST['id'],
                                         resultado_aprendizaje__materia__materia__curso__ronda=g_e.ronda)
                o.texto = request.POST['html']
                o.save()
                return JsonResponse({'ok': True, 'html': o.texto})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'mod_crit_eval':
            try:
                o = Objetivo.objects.get(id=request.POST['id'],
                                         resultado_aprendizaje__materia__materia__curso__ronda=g_e.ronda)
                o.crit_eval = request.POST['html']
                o.save()
                return JsonResponse({'ok': True, 'html': o.crit_eval})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_objetivo':
            try:
                o = Objetivo.objects.get(id=request.POST['id'],
                                         resultado_aprendizaje__materia__materia__curso__ronda=g_e.ronda).delete()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

    respuesta = {
        # 'iconos':
        #     ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir resultado',
        #       'title': 'Crear un nuevo resultado de aprendizaje', 'permiso': 'crea_resultados_aprendizaje_ccff'},
        #      ),
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir resultado',
              'title': 'Crear un nuevo resultado de aprendizaje', 'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Volver',
              'title': 'Volver a la lista de materias', 'permiso': 'libre'},
             ),
        'formname': 'resultados_aprendizaje',
        'materia': m,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "resultados_aprendizaje.html", respuesta)


@permiso_required('acceso_programaciones_ccff')
def programaciones(request):
    g_e = request.session['gauser_extra']
    crear_aviso(request, True, 'Entra en programaciones')
    if request.method == 'POST':
        if request.POST['action'] == 'pdf_programacion' and g_e.has_permiso('crea_programaciones_ccff'):
            programacion = Programacion_modulo.objects.get(id=request.POST['id_programacion'])
            fichero = '%s_%s.pdf' % (g_e.ronda.entidad.code, programacion.id)
            try:
                fich = open(MEDIA_ESCRITOS + fichero)
                crear_aviso(request, True, "Descarga pdf: %s" % (programacion.asunto))
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + programacion.asunto.replace(' ',
                                                                                                        '_') + '.pdf'
                return response
            except:
                dce = get_dce(g_e.ronda.entidad, 'Configuración de programaciones de CCFF')
                fichero = '%s_%s' % (g_e.ronda.entidad.code, programacion.id)
                ruta = MEDIA_PROGRAMACIONES + g_e.ronda.entidad.code + '/' + fichero + '.pdf'
                c = render_to_string('programacion2pdf.html', {'programacion': programacion, 'dce': dce},
                                     request=request)
                genera_pdf(c, dce, ruta_archivo=ruta)
                return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename='%s.pdf' % fichero,
                                    content_type='application/pdf')
        elif request.POST['action'] == 'download_pdf':
            programacion = Programacion_modulo.objects.get(id=request.POST['id_programacion'])
            try:
                fich_name = replace_normalize(programacion.modulo.nombre) + '.pdf'
                fichero = open(programacion.file_path + '.pdf', 'rb')
                crear_aviso(request, True, "Descarga programacion (pdf): %s" % (programacion))
                response = HttpResponse(fichero, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + fich_name
                return response
            except:
                dce = get_dce(g_e.ronda.entidad, 'Configuración de programaciones de CCFF')
                crear_aviso(request, True, 'Detecta id y se genera el pdf de la programación: %s' % (programacion))
                c = render_to_string('programacion2pdf.html', {'prog': programacion, 'dce': dce})
                crear_aviso(request, True, 'prog 2')
                fichero = replace_normalize(programacion.modulo.materia.nombre)
                crear_aviso(request, True, 'prog 3')
                ronda = g_e.ronda.entidad.ronda.nombre.replace('/', '-')
                crear_aviso(request, True, 'prog 4')
                try:
                    file_path = '%s%s/%s/%s/%s/%s/' % (MEDIA_PROGRAMACIONES, g_e.ronda.entidad.code,
                                                       ronda, g_e.gauser_extra_programaciones.departamento.nombre,
                                                       programacion.modulo.materia.curso.get_etapa_display(),
                                                       programacion.modulo.materia.curso.nombre)
                except:
                    crear_aviso(request, False,
                                'Se ha producido un error. Probablemente se deba a que no te han asociado un departamento.')
                    HttpResponse('Error. Probablemente se deba a que no te han asignado un departamento.')
                crear_aviso(request, True, 'prog 5')
                file_path = replace_normalize(file_path)
                crear_aviso(request, True, 'prog 6')
                programacion.file_path = file_path + fichero
                crear_aviso(request, True, 'prog 7')
                programacion.save()
                crear_aviso(request, True, 'prog 8')
                dce = get_dce(g_e.ronda.entidad, 'Configuración de programaciones de CCFF')
                ruta = MEDIA_PROGRAMACIONES + g_e.ronda.entidad.code + '/' + fichero + '.pdf'
                genera_pdf(c, dce, ruta_archivo=ruta)
                return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename='%s.pdf' % fichero,
                                    content_type='application/pdf')
        elif request.POST['action'] == 'download_html':
            programacion = Programacion_modulo.objects.get(id=request.POST['id_programacion'])
            fich_name = replace_normalize(programacion.modulo.materia.nombre) + '.html'
            fichero = open(programacion.file_path + '.html')
            crear_aviso(request, True, "Descarga programacion (html): %s" % (programacion))
            response = HttpResponse(fichero, content_type='text/html')
            response['Content-Disposition'] = 'attachment; filename=' + fich_name
            return response

    # if request.method == 'GET':
    # Si no es POST será GET y por tanto no hay que comprobarlo. En caso de que el POST se haga
    # con una 'action' incorrecta se procederá como si fuera una petición GET:
    rondas = Ronda.objects.filter(entidad=g_e.ronda.entidad, id__gt=25)
    if 'ronda' in request.GET:
        ronda = rondas.get(id=request.GET['ronda'])
    else:
        ronda = g_e.ronda
    cursos = Curso.objects.filter(ronda=ronda, etapa__in=['ga', 'ha'])
    cursos_clave_ex = cursos.values_list('clave_ex', flat=True)
    progs = Programacion_modulo.objects.filter(modulo__isnull=False,
                                               modulo__materia__curso__clave_ex__in=cursos_clave_ex)
    if 'curso' in request.GET:
        try:
            curso_clave_ex = cursos.get(id=request.GET['curso']).clave_ex
        except:
            curso_clave_ex = cursos[0].clave_ex
    else:
        curso_clave_ex = cursos[0].clave_ex

    progs = progs.filter(g_e__ronda=ronda, modulo__materia__curso__clave_ex=curso_clave_ex)

    return render(request, "programaciones_foundation.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nueva',
                            'title': 'Crear una nueva programación',
                            'permiso': 'crea_programaciones_ccff'},
                           ),
                      'formname': 'Programacion_modulos',
                      'borradores': Programacion_modulo.objects.filter(
                          g_e__ronda=g_e.ronda, modulo__isnull=True).order_by('-id'),
                      'programaciones': progs,
                      'cursos': cursos,
                      'curso_clave_ex': curso_clave_ex,
                      'rondas': rondas,
                      'ronda': ronda,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
# @access_required
def objetivos_criterios(request):
    g_e = request.session['gauser_extra']
    crear_aviso(request, True, 'Entra en objetivos criterios')
    return render(request, "objetivos_criterios_evaluacion_foundation.html",
                  {
                      'formname': 'objetivos_criterios',
                      'estudios': Curso.objects.filter(ronda=g_e.ronda, etapa__in=['ea', 'ga', 'ha']).order_by(
                          'tipo', 'nombre_especifico'),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def ajax_objetivos_criterios(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        action = request.POST['action']
        if action == 'list_raprendizajes':
            materia = Materia.objects.get(id=request.POST['id'])
            raprendizajes = Resultado_aprendizaje.objects.filter(materia=materia)
            html = render_to_string("list_raprendizajes.html",
                                    {'raprendizajes': raprendizajes, 'materia': materia.id})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'cont_raprendizaje':
            raprendizaje = Resultado_aprendizaje.objects.get(id=request.POST['id'])
            objetivos = Objetivo.objects.filter(resultado_aprendizaje=raprendizaje)
            html = render_to_string("objetivos_en_raprendizaje.html",
                                    {'objetivos': objetivos, 'raprendizaje': raprendizaje.id})
            return JsonResponse({'ok': True, 'html': html, 'id': raprendizaje.id})
        elif action == 'change_texto_raprendizaje':
            raprendizaje = Resultado_aprendizaje.objects.get(id=request.POST['id'])
            raprendizaje.resultado = request.POST['texto']
            raprendizaje.save()
            return JsonResponse({'ok': True, 'texto': raprendizaje.resultado, 'id': raprendizaje.id})
        elif action == 'add_objetivo':
            raprendizaje = Resultado_aprendizaje.objects.get(id=request.POST['id'])
            materia = raprendizaje.materia
            objetivo = Objetivo.objects.create(materia=materia, resultado_aprendizaje=raprendizaje,
                                               texto='Escribir texto del objetivo',
                                               crit_eval='Se ha escrito el texto del objetivo')
            html = render_to_string("objetivo_fieldset.html", {'objetivo': objetivo, })
            return JsonResponse({'ok': True, 'html': html, 'id': raprendizaje.id})
        elif action == 'del_objetivo':
            id = request.POST['id']
            Objetivo.objects.get(id=id).delete()
            return JsonResponse({'ok': True, 'id': id})
        elif action == 'texto_criterio':
            id = request.POST['id']
            objetivo = Objetivo.objects.get(id=id)
            objetivo.crit_eval = request.POST['texto']
            objetivo.save()
            return JsonResponse({'ok': True, })
        elif action == 'texto_objetivo':
            id = request.POST['id']
            objetivo = Objetivo.objects.get(id=id)
            objetivo.texto = request.POST['texto']
            objetivo.save()
            return JsonResponse({'ok': True, })
        elif action == 'add_raprendizaje':
            materia = Materia.objects.get(id=request.POST['materia'])
            raprendizaje = Resultado_aprendizaje.objects.create(materia=materia,
                                                                resultado="Ejemplo de resultado de aprendizaje")
            Objetivo.objects.create(materia=materia, resultado_aprendizaje=raprendizaje,
                                    texto='Escribir texto del objetivo',
                                    crit_eval='Se ha escrito el texto del objetivo')
            html = render_to_string("raprendizaje.html", {'raprendizaje': raprendizaje, })
            return JsonResponse({'ok': True, 'html': html, 'id': materia.id})
        elif action == 'del_raprendizaje':
            id = request.POST['id']
            Resultado_aprendizaje.objects.get(id=id).delete()
            return JsonResponse({'ok': True, 'id': id})
        elif action == 'change_titulo':
            curso = Curso.objects.get(id=request.POST['id'])
            # mods = {m.id: m.nombre for m in g_e.ronda.entidad.materias.filter(estudio=estudio)}
            mods = {m.id: m.nombre for m in curso.materia_set.all()}
            return JsonResponse({'ok': True, 'modulos': mods})


@permiso_required('acceso_programaciones_ccff')
def ajax_programaciones(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        action = request.POST['action']
        if action == 'busca_programacion':
            texto = request.POST['q']
            try:
                inicio = datetime.strptime(request.POST['fecha_inicio'], '%d-%m-%Y')
            except:
                inicio = datetime.strptime(request.POST['fecha_inicio'], '%d/%m/%Y')
            try:
                fin = datetime.strptime(request.POST['fecha_fin'], '%d-%m-%Y')
            except:
                fin = datetime.strptime(request.POST['fecha_fin'], '%d/%m/%Y')
            programaciones = Programacion_modulo.objects.filter(creado__gte=inicio, creado__lte=fin)
            try:
                seleccionados = request.POST.getlist('programaciones_listadas')
            except:
                seleccionados = []
            programaciones_contain_texto = programaciones.filter(
                Q(titulo__nombre__icontains=texto) | Q(modulo__nombre__icontains=texto),
                ~Q(id__in=seleccionados)).order_by(
                '-creado').values_list('id', 'titulo__nombre', 'modulo__nombre')
            ps = [[v[0], v[1], v[2]] for v in programaciones_contain_texto]
            keys = ('id', 'text')
            d = [dict(zip(keys, (row[0], '<b>Título: </b>%s<br><b>Módulo: </b>%s' % (row[1], row[2])))) for row in ps]
            return HttpResponse(json.dumps(d))
        elif action == 'programacion_append':
            programacion = Programacion_modulo.objects.get(id=request.POST['id_programacion'])
            accordion = render_to_string('programacion_append.html', {'programacion': programacion})
            return HttpResponse(accordion)
        elif action == 'del_programacion':
            programacion = Programacion_modulo.objects.get(id=request.POST['id'])
            try:
                crear_aviso(request, True, 'Ejecuta borrar programación: %s' % (programacion.modulo.nombre))
            except:
                pass
            programacion.delete()
            return HttpResponse(True)
        elif action == 'copy_programacion':
            try:
                prog_original = Programacion_modulo.objects.get(id=request.POST['id'])
            except Exception as e:
                return JsonResponse({'ok': False, 'mensaje': str(e)})
            try:
                Programacion_modulo.objects.get(modulo=prog_original.modulo, gep__ge__ronda=g_e.ronda)
                return JsonResponse({'ok': False})  # No copiar porque ya existe una programación
            except:
                try:
                    # Al copiar la programación se quedará con el curso en el que fue creada, al igual que la materia
                    # Esto no debería plantear ningún problema ya que el propietario se corresponde con la ronda actual.
                    programacion = Programacion_modulo.objects.get(id=request.POST['id'])
                    programacion.g_e = g_e
                    programacion.gep = g_e.gauser_extra_programaciones
                    programacion.pk = None
                    programacion.file_path = None
                    programacion.save()
                    programacion.obj_gen.add(*prog_original.obj_gen.all())
                    uds = prog_original.ud_modulo_set.all()
                    for ud in uds:
                        ud_original = UD_modulo.objects.get(id=ud.id)
                        ud.pk = None
                        ud.programacion = programacion
                        ud.save()
                        ud.objetivos.add(*ud_original.objetivos.all())
                        conts = ud_original.cont_unidad_modulo_set.all()
                        for cont in conts:
                            cont.pk = None
                            cont.unidad = ud
                            cont.save()
                    accordion = render_to_string('programacion_append.html', {'programacion': programacion, },
                                                 request=request)
                    crear_aviso(request, True, 'Ejecuta copiar programacion: %s' % (programacion.modulo))
                    # return HttpResponse(json.dumps({'ok': True, 'accordion': accordion, 'id': programacion.id}))
                    return JsonResponse({'ok': True, 'accordion': accordion, 'id': programacion.id})
                except Exception as e:
                    return JsonResponse({'ok': False, 'mensaje': str(e)})
        elif action == 'busca_ccff':
            texto = request.POST['q']
            familias = dict(FAMILIAS)
            tits = Titulo_FP.objects.filter(nombre__icontains=texto).values_list('id', 'nombre', 'nivel', 'familia',
                                                                                 'duracion', 'ref_eu')
            keys = ('id', 'nombre', 'nivel', 'familia', 'duracion', 'ref_eu')
            listados = [dict(zip(keys, (row[0], row[1], row[2], familias[row[3]], row[4], row[5]))) for row in tits]
            return HttpResponse(json.dumps(listados))
        elif action == 'busca_modulo':
            id_titulo = int(request.POST['titulo'])
            titulo = Titulo_FP.objects.get(id=id_titulo)
            try:
                programacion = Programacion_modulo.objects.get(id=request.POST['programacion'])
                programacion.titulo = titulo
                programacion.save()
            except:
                crear_aviso(request, True, 'Busca materia para objetivos y criterios')
            texto = request.POST['q']
            estudios = titulo.cursos.all()
            ex_modulos = Programacion_modulo.objects.filter(g_e__ronda=g_e.ronda).values_list(
                'modulo__id', flat=True)
            ex_modulos = [ex for ex in ex_modulos if ex]
            mods = Materia_programaciones.objects.filter(Q(nombre__icontains=texto), Q(estudio__in=estudios),
                                                         ~Q(id__in=ex_modulos)).values_list('id', 'nombre', 'horas')
            keys = ('id', 'nombre', 'horas')
            listados = [dict(zip(keys, (row[0], row[1], str(row[2])))) for row in mods]
            # listados.append(list(ex_modulos))
            return HttpResponse(json.dumps(listados))
        elif action == 'datos_modulo':
            programacion = Programacion_modulo.objects.get(id=request.POST['programacion'])
            modulo = Materia_programaciones.objects.get(id=request.POST['modulo'])
            programacion.modulo = modulo
            programacion.save()
            titulo = programacion.titulo
            obj_generales = dict(Obj_general.objects.filter(titulo=programacion.titulo).values_list('id', 'objetivo'))
            datos = [modulo.codigo, modulo.ects, modulo.duracion, modulo.id, obj_generales]
            # return HttpResponse(json.dumps(datos))
            return JsonResponse(datos, safe=False)
        elif action == 'guardar_datos_modulo_codigo':  # comprobado
            try:
                modulo = Materia_programaciones.objects.get(id=request.POST['id'])
                modulo.codigo = request.POST['val']
                modulo.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False, 'error': "No se puede encontrar la materia"})
        elif action == 'guardar_datos_modulo_horas':  # comprobado
            try:
                modulo = Materia_programaciones.objects.get(id=request.POST['id'])
                modulo.materia.duracion = int(request.POST['val'])
                modulo.materia.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False, 'error': "Las horas deben ser números enteros"})
        elif action == 'guardar_datos_modulo_ects':  # comprobado
            try:
                modulo = Materia_programaciones.objects.get(id=request.POST['id'])
                modulo.ects = int(request.POST['val'])
                modulo.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False, 'error': "Las horas deben ser números enteros"})
        elif action == 'save_obj_general':  # comprobado
            programacion = Programacion_modulo.objects.get(id=request.POST['prog'])
            obj_general = Obj_general.objects.get(id=request.POST['obj'])
            programacion.obj_gen.add(obj_general)
            return HttpResponse(True)
        elif action == 'del_obj_general':  # comprobado
            programacion = Programacion_modulo.objects.get(id=request.POST['prog'])
            obj_general = Obj_general.objects.get(id=request.POST['obj'])
            programacion.obj_gen.remove(obj_general)
            return HttpResponse(True)
        elif action == 'save_obj_criterios':
            materia = Materia.objects.get(id=request.POST['modulo'])
            ra = Resultado_aprendizaje.objects.create(materia=materia, resultado=request.POST['resultado'])
            for i in range(1, 16):
                criterio = 'criterio' + str(i)
                texto = request.POST[criterio].replace('Se han ', '', 1).replace('Se ha ', '', 1)
                trozos = texto.split(' ', 1)
                trozos[0] = trozos[0].replace('ado', 'ar').replace('ido', 'er')
                texto = ' '.join(trozos)
                if len(texto) > 5:
                    Objetivo.objects.create(resultado_aprendizaje=ra, materia=materia, crit_eval=request.POST[criterio],
                                            texto=texto.capitalize())
            return HttpResponse(True)
        elif action == 'add_ud':
            programacion = Programacion_modulo.objects.get(id=request.POST['programacion'])
            n = UD_modulo.objects.filter(programacion=programacion).count() + 1
            ud = UD_modulo.objects.create(programacion=programacion, nombre='Nueva unidad', orden=n, duracion=10)
            accordion = render_to_string('crear_accordion_unidad_didactica_append.html', {'ud': ud})
            return HttpResponse(accordion)
        elif action == 'delete_ud':
            ud = UD_modulo.objects.get(id=request.POST['ud'])
            prog = ud.programacion
            ud.delete()
            uds = UD_modulo.objects.filter(programacion=prog)
            n = 1
            for u in uds:
                u.orden = n
                u.save()
                n += 1
            uds = dict(UD_modulo.objects.filter(programacion=prog).values_list('id', 'orden'))
            return JsonResponse(uds)
        elif action == 'pdf_ud':
            # Esta action hay que hacerla desde editar_programacion con un submit
            return HttpResponse(True)
        elif action == 'update_pos_ud':
            ud = UD_modulo.objects.get(id=request.POST['ud'])
            orden_nuevo = min(int(request.POST['orden']),
                              UD_modulo.objects.filter(programacion=ud.programacion).count())
            uds = UD_modulo.objects.filter(programacion=ud.programacion).exclude(id=ud.id)
            cambiado = False
            n = 1
            for u in uds:
                if n == orden_nuevo:
                    ud.orden = orden_nuevo
                    ud.save()
                    n += 1
                    cambiado = True
                u.orden = n
                u.save()
                n += 1
            if not cambiado:
                ud.orden = orden_nuevo
                ud.save()
            uds = dict(UD_modulo.objects.filter(programacion=ud.programacion).values_list('id', 'orden'))
            return JsonResponse(uds)
        elif action == 'update_nombre_ud':
            ud = UD_modulo.objects.get(id=request.POST['ud'])
            ud.nombre = request.POST['nombre']
            ud.save()
            return HttpResponse(ud.nombre)
        elif action == 'update_duracion_ud':
            ud = UD_modulo.objects.get(id=request.POST['ud'])
            ud.duracion = request.POST['duracion']
            ud.save()
            total_d = UD_modulo.objects.filter(programacion=ud.programacion).aggregate(t=Sum('duracion'))['t']
            mod_d = ud.programacion.modulo.duracion
            if total_d > mod_d:
                uds_d = dict(UD_modulo.objects.filter(programacion=ud.programacion).values_list('id', 'duracion'))
                err = True
            else:
                uds_d = ''
                err = False
            return JsonResponse({'ud_d': ud.duracion, 'error': err, 'uds_d': uds_d, 'mod_d': mod_d, 'total_d': total_d})
        elif action == 'adjust_uds_duration':
            ud = UD_modulo.objects.get(id=request.POST['ud'])
            uds = UD_modulo.objects.filter(programacion=ud.programacion)
            total_d = uds.aggregate(t=Sum('duracion'))['t']
            mod_d = ud.programacion.modulo.duracion
            for u in uds:
                u.duracion = int(round(mod_d * u.duracion / total_d))
                u.save()
            new_total_d = uds.aggregate(t=Sum('duracion'))['t']
            sin_asignar = mod_d - new_total_d
            i = 1
            if sin_asignar > 0:
                for u in uds:
                    u.duracion = u.duracion + i
                    u.save()
                    sin_asignar -= 1
                    if sin_asignar == 0:
                        i = 0
            # uds_d = dict(UD_modulo.objects.filter(programacion=ud.programacion).values_list('id', 'duracion'))
            uds_d = dict(uds.values_list('id', 'duracion'))
            return JsonResponse(uds_d)
        elif action == 'ra_objetivos':
            ud = UD_modulo.objects.get(id=request.POST['ud'])
            ra = Resultado_aprendizaje.objects.get(id=request.POST['ra'])
            objs = dict(Objetivo.objects.filter(resultado_aprendizaje=ra).values_list('id', 'texto'))
            objs_selected = list(ud.objetivos.all().values_list('id', flat=True))
            return JsonResponse([objs, objs_selected], safe=False)
        elif action == 'save_objetivo':
            ud = UD_modulo.objects.get(id=request.POST['ud'])
            obj = Objetivo.objects.get(id=request.POST['obj'])
            ud.objetivos.add(obj)
            return HttpResponse(True)
        elif action == 'delete_objetivo':
            ud = UD_modulo.objects.get(id=request.POST['ud'])
            obj = Objetivo.objects.get(id=request.POST['obj'])
            ud.objetivos.remove(obj)
            return HttpResponse(True)
        elif action == 'get_ud_contents':
            ud = UD_modulo.objects.get(id=request.POST['ud'])
            data = render_to_string('unidad_didactica_append.html', {'ud': ud})
            return HttpResponse(data)
        elif action == 'add_contenido_ud':
            ud = UD_modulo.objects.get(id=request.POST['ud'])
            n = Cont_unidad_modulo.objects.filter(unidad=ud).count() + 1
            con = Cont_unidad_modulo.objects.create(unidad=ud, contenido='', actividades='', duracion=1, nombre='',
                                                    orden=n, objetivos='')
            data = render_to_string('contenidos_unidad_didactica_append.html', {'ud': ud, 'con': con})
            # return HttpResponse(data)
            return JsonResponse({'html': data, 'con_id': con.id})
        elif action == 'del_contenido_ud':
            con = Cont_unidad_modulo.objects.get(id=request.POST['con'])
            unidad = con.unidad
            con.delete()
            cons = Cont_unidad_modulo.objects.filter(unidad=unidad)
            n = 1
            for c in cons:
                c.orden = n
                c.save()
                n += 1
            cons = dict(Cont_unidad_modulo.objects.filter(unidad=unidad).values_list('id', 'orden'))
            return JsonResponse(cons)
        elif action == 'update_pos_con':
            con = Cont_unidad_modulo.objects.get(id=request.POST['con'])
            orden_nuevo = min(int(request.POST['orden']), Cont_unidad_modulo.objects.filter(unidad=con.unidad).count())
            cons = Cont_unidad_modulo.objects.filter(unidad=con.unidad).exclude(id=con.id)
            cambiado = False
            n = 1
            for c in cons:
                if n == orden_nuevo:
                    con.orden = orden_nuevo
                    con.save()
                    n += 1
                    cambiado = True
                c.orden = n
                c.save()
                n += 1
            if not cambiado:
                con.orden = orden_nuevo
                con.save()
            cons = dict(Cont_unidad_modulo.objects.filter(unidad=con.unidad).values_list('id', 'orden'))
            return JsonResponse(cons)
        elif action == 'update_nombre_con':
            con = Cont_unidad_modulo.objects.get(id=request.POST['con'])
            con.nombre = request.POST['nombre']
            con.save()
            return HttpResponse(con.nombre)
        elif action == 'update_duracion_con':
            con = Cont_unidad_modulo.objects.get(id=request.POST['con'])
            con.duracion = request.POST['duracion']
            con.save()
            total_d = Cont_unidad_modulo.objects.filter(unidad=con.unidad).aggregate(t=Sum('duracion'))['t']
            uni_d = con.unidad.duracion
            err = True if total_d > uni_d else False
            return JsonResponse({'con_d': con.duracion, 'error': err})
        elif action == 'adjust_cons_duration':
            con = Cont_unidad_modulo.objects.get(id=request.POST['con'])
            cons = Cont_unidad_modulo.objects.filter(unidad=con.unidad)
            total_d = cons.aggregate(t=Sum('duracion'))['t']
            uni_d = con.unidad.duracion
            for c in cons:
                c.duracion = int(round(uni_d * c.duracion / total_d))
                c.save()
            new_total_d = cons.aggregate(t=Sum('duracion'))['t']
            sin_asignar = uni_d - new_total_d
            i = 1
            if sin_asignar > 0:
                for c in cons:
                    c.duracion = c.duracion + i
                    c.save()
                    sin_asignar -= 1
                    if sin_asignar == 0:
                        i = 0
            cons_d = dict(cons.values_list('id', 'duracion'))
            # cons_d = dict(Cont_unidad_modulo.objects.filter(unidad=con.unidad).values_list('id', 'duracion'))
            return JsonResponse(cons_d)
        elif action == 'update_horas_contenidos':
            con = Cont_unidad_modulo.objects.get(id=request.POST['con'])
            con.duracion = request.POST['duracion']
            con.save()
            return HttpResponse(True)
        elif action == 'guarda_objetivos_ud':
            con = Cont_unidad_modulo.objects.get(id=request.POST['con'])
            con.objetivos = request.POST['texto']
            con.save()
            return HttpResponse(True)
        elif action == 'guarda_contenidos_ud':
            con = Cont_unidad_modulo.objects.get(id=request.POST['con'])
            con.contenido = request.POST['texto']
            con.save()
            return HttpResponse(True)
        elif action == 'guarda_actividades_ud':
            con = Cont_unidad_modulo.objects.get(id=request.POST['con'])
            con.actividades = request.POST['texto']
            con.save()
            return HttpResponse(True)
        elif action == 'save_refuerzo_recuperacion':
            prog = Programacion_modulo.objects.get(id=request.POST['prog'])
            prog.act_refuerzo = request.POST['texto']
            prog.save()
            return HttpResponse(True)
        elif action == 'save_progreso_calificacion':
            prog = Programacion_modulo.objects.get(id=request.POST['prog'])
            prog.crit_eval_gen = request.POST['texto']
            prog.save()
            return HttpResponse(True)
        elif action == 'save_propuesta_formacion':
            prog = Programacion_modulo.objects.get(id=request.POST['prog'])
            prog.pro_formacion = request.POST['texto']
            prog.save()
            return HttpResponse(True)

            # Este código únicamente es para relacionar los resultados de aprendizaje con sus criterios de evaluación
            # Se puede borrar una vez esté corregido el problema de asignación
            # elif action == 'ra_modulo':
            #     modulo = Materia.objects.get(id=request.POST['modulo'])
            #     ras = dict(Resultado_aprendizaje.objects.filter(materia=modulo).values_list('id', 'resultado'))
            #     return JsonResponse(ras, safe=False)
            # elif action == 'load_criterios':
            #     modulo = Materia.objects.get(id=request.POST['modulo'])
            #     crits = dict(Objetivo.objects.filter(materia=modulo, resultado_aprendizaje__isnull=True).values_list('id',
            #                                                                                                          'crit_eval'))
            #     # return HttpResponse(json.dumps(datos))
            #     return JsonResponse(crits, safe=False)
            # elif action == 'match_crit_ra':
            #     ra = Resultado_aprendizaje.objects.get(id=request.POST['ra'])
            #     cr = Objetivo.objects.get(id=request.POST['cr'])
            #     cr.resultado_aprendizaje = ra
            #     cr.save()
            #     return HttpResponse(True)


# @login_required()  # Esta función se podrá borrar una vez corregido el error
# def resultados_aprendizaje(request):
#     g_e = request.session['gauser_extra']
#     return render(request, "resultados_aprendizaje-criterios_evaluacion.html",
#                               {
#                                   'formname': 'resultados_aprendizaje',
#                                   'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
#                               })

def replace_normalize(string):
    for ch in [',', ';', '.', ')', '(']:
        string = string.replace(ch, '')
    string = string.replace(' ', '_')
    return slugify(string)


@permiso_required('acceso_programaciones_ccff')
def editar_programacion(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        if request.POST['action'] == 'pdf':
            programacion = Programacion_modulo.objects.get(id=request.POST['programacion'])
            crear_aviso(request, True, 'Detecta id y se genera el pdf de la programación: %s' % (programacion))
            c = render_to_string('programacion2pdf.html', {'prog': programacion})
            # -----------------------------------
            ruta = '%s%s/' % (MEDIA_PROGRAMACIONES, g_e.ronda.entidad.code)
            dce = get_dce(g_e.ronda.entidad, 'Configuración de programaciones de CCFF')
            genera_pdf(c, dce)
            fich = open(dce.url_pdf, 'rb')
            materia = Materia.objects.get(curso__ronda=g_e.ronda, clave_ex=programacion.modulo.materia.clave_ex)
            try:
                p = ProgramacionSubida.objects.get(materia=materia)
                # Borramos el posible fichero existente:
                ruta = "%s%s" % (RUTA_BASE, p.archivo.url)
                os.remove(ruta)
                # Grabamos los campos de la programación
                p.sube = g_e
                p.archivo = File(fich)
                p.content_type = 'application/pdf'
                p.save()
            except:
                p = ProgramacionSubida.objects.create(materia=materia, sube=g_e, archivo=File(fich),
                                                      content_type='application/pdf')
            programacion.file_path = p.archivo.url
            programacion.save()
            response = HttpResponse(p.archivo, content_type=p.content_type)
            response['Content-Disposition'] = 'attachment; filename=%s' % p.filename
            return response
            # -----------------------------------
        if request.POST['action'] == 'pdf_ud':
            dce = get_dce(g_e.ronda.entidad, 'Configuración de programaciones de CCFF')
            ud = UD_modulo.objects.get(id=request.POST['unidad_didactica'])
            crear_aviso(request, True, 'Genera el pdf de la unidad didáctica: %s' % (ud.nombre))
            fichero = '%s_%s_%s' % (g_e.ronda.entidad.code, ud.programacion.id, ud.id)
            c = render_to_string('ud2pdf.html', {'ud': ud, 'dce': dce})
            dce = get_dce(g_e.ronda.entidad, 'Configuración de programaciones de CCFF')
            ruta = MEDIA_PROGRAMACIONES + g_e.ronda.entidad.code + '/' + fichero + '.pdf'
            genera_pdf(c, dce, ruta_archivo=ruta)
            return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename='%s.pdf' % fichero,
                                content_type='application/pdf')
    else:
        if 'prog' in request.GET:
            try:
                if g_e.has_permiso('edita_programaciones_ccff'):
                    programacion = Programacion_modulo.objects.get(pk=request.GET['prog'],
                                                                   g_e__ronda__entidad=g_e.ronda.entidad)
                else:
                    programacion = Programacion_modulo.objects.get(pk=request.GET['prog'], g_e=g_e)
                crear_aviso(request, True, 'Entra en editar el programacion %s.' % (programacion.id))
            except:
                return redirect('/programaciones/')
        else:
            try:
                programacion = Programacion_modulo.objects.filter(g_e=g_e, modulo__isnull=True)[0]
            except:
                c = '<p>Además, para verificar el progreso y calificar adecuadamente a los alumnos se establece ...</p>'
                programacion = Programacion_modulo.objects.create(g_e=g_e, act_refuerzo='', act_fct='', crit_eval_gen=c,
                                                                  pro_formacion='')
            crear_aviso(request, True, 'Entra en crear programacion.')
    return render(request, "crear_programacion_foundation.html",
                  {
                      'formname': 'Crear_programacion',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF',
                            'title': 'Generar pdf de la programación',
                            'permiso': 'libre'},
                           {'tipo': 'button', 'nombre': 'list', 'texto': 'Programaciones',
                            'title': 'Volver a la lista de programaciones',
                            'permiso': 'libre'}
                           ),
                      'programacion': programacion,
                      'unidades': UD_modulo.objects.filter(programacion=programacion),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


class Titulo_FPForm(ModelForm):
    class Meta:
        model = Titulo_FP
        fields = ('nombre', 'duracion', 'familia', 'ref_eu', 'cursos')


@login_required()
# @access_required
def titulos(request):
    g_e = request.session['gauser_extra']
    crear_aviso(request, True, 'Entra en títulos educativos')
    if request.method == 'POST':
        if request.POST['action'] == 'pdf_titulo' and g_e.has_permiso('crear_titulo'):
            titulo = Titulo_FP.objects.get(id=request.POST['id_titulo'])
            fichero = '%s_%s.pdf' % (g_e.ronda.entidad.code, titulo.id)
            try:
                fich = open(MEDIA_ESCRITOS + fichero, 'rb')
                crear_aviso(request, True, "Descarga pdf: %s" % (titulo.asunto))
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + titulo.asunto.replace(' ', '_') + '.pdf'
                return response
            except:
                fichero = '%s_%s' % (g_e.ronda.entidad.code, titulo.id)
                dce = get_dce(g_e.ronda.entidad, 'Configuración de programaciones de CCFF')
                c = render_to_string('titulo2pdf.html', {'titulo': titulo, 'dce': dce}, request=request)
                ruta = MEDIA_PROGRAMACIONES + g_e.ronda.entidad.code + '/' + fichero + '.pdf'
                genera_pdf(c, dce, ruta_archivo=ruta)
                return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename='%s.pdf' % fichero,
                                    content_type='application/pdf')
    return render(request, "titulosFP_foundation.html",
                  {
                      'iconos':
                          ({'nombre': 'plus', 'texto': 'Nuevo',
                            'title': 'Crear un nuevo titulo', 'permiso': 'libre'},
                           ),
                      'formname': 'Titulos_FP',
                      'recientes': Titulo_FP.objects.all().order_by('-id')[0:5],
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def ajax_titulos(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        action = request.POST['action']
        if action == 'busca_titulo':
            texto = request.POST['q']
            try:
                inicio = datetime.strptime(request.POST['fecha_inicio'], '%d-%m-%Y')
            except:
                inicio = datetime.strptime(request.POST['fecha_inicio'], '%d/%m/%Y')
            try:
                fin = datetime.strptime(request.POST['fecha_fin'], '%d-%m-%Y')
            except:
                fin = datetime.strptime(request.POST['fecha_fin'], '%d/%m/%Y')
            titulos = Titulo_FP.objects.filter(autores__in=[g_e.gauser], creado__gte=inicio, creado__lte=fin,
                                               borrador=False)
            try:
                seleccionados = request.POST.getlist('titulos_seleccionados')
            except:
                seleccionados = []
            titulos_contain_texto = titulos.filter(
                Q(asunto__icontains=texto) | Q(texto__icontains=texto), ~Q(id__in=seleccionados)).order_by(
                '-creado').values_list(
                'id',
                'asunto',
                'receptores',
                'creado')
            titulos_contain_texto_list = [
                [v[0], v[1], Contacto.objects.get(id=v[2]).nombre if v[2] else 'Sin definir en el documento', v[3]] for
                v in titulos_contain_texto]
            keys = ('id', 'text')
            return HttpResponse(
                json.dumps([dict(zip(keys, (
                    row[0],
                    '<b>Asunto: </b>%s<br><b>Receptor: </b>%s<br><b>Creado: </b>%s' % (row[1], row[2], row[3]))))
                            for row in titulos_contain_texto_list]))
        elif action == 'titulo_append':
            titulo = Titulo_FP.objects.get(id=request.POST['id_titulo'])
            accordion = render_to_string('titulo_append_foundation.html', {'titulo': titulo})
            return HttpResponse(accordion)
        elif action == 'delete_titulo':
            titulo = Titulo_FP.objects.get(id=request.POST['id'])
            crear_aviso(request, True, 'Ejecuta borrar titulo: %s' % (titulo.asunto))
            titulo.delete()
            return HttpResponse(True)
        elif action == 'copy_titulo':
            titulo = Titulo_FP.objects.get(id=request.POST['id_titulo'])
            copia = Titulo_FP.objects.create(asunto=titulo.asunto + ' (copia de titulo)', firmante=g_e.gauser,
                                             entidad=g_e.ronda.entidad, texto=titulo.texto)
            copia.autores.add(g_e.gauser)
            accordion = render_to_string('titulo_append_foundation.html', {'titulo': copia, 'borrador': True})
            crear_aviso(request, True, 'Ejecuta copiar titulo: %s' % (titulo.asunto))
            return HttpResponse(json.dumps({'accordion': accordion, 'id': copia.id}))
        elif action == 'busca_receptor':
            texto = request.POST['q']
            g_es = Gauser_extra.objects.filter(ronda=g_e.ronda, perfiles__in=[12])
            g_es1 = g_es.filter(Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto) | Q(
                cargo__icontains=texto)).values_list('id', 'gauser__last_name', 'gauser__first_name', 'cargo')
            g_es2 = Contacto.objects.filter(Q(nombre__icontains=texto) | Q(cargo__icontains=texto),
                                            Q(creador=g_e.gauser)).values_list('id', 'nombre', 'cargo')
            keys = ('id', 'text')
            list1 = [dict(zip(keys, (str(row[0]) + '___ge', '%s, %s (%s)' % (row[1], row[2], row[3])))) for row in
                     g_es1]
            list2 = [dict(zip(keys, (str(row[0]) + '___contacto', '%s (%s)' % (row[1], row[2])))) for row in g_es2]
            return HttpResponse(json.dumps(list1 + list2))
        elif action == 'crea_contacto' and g_e.has_permiso('crear_contacto'):
            contacto = Contacto(creador=g_e.gauser)
            form = ContactoForm(request.POST, instance=contacto)
            if form.is_valid():
                contacto = form.save()
                crear_aviso(request, True, 'Contacto creado correctamente.')
                texto = '%s (%s)' % (contacto.nombre, contacto.cargo)
                return HttpResponse(json.dumps({'id': str(contacto.id) + "___contacto", 'text': texto}))
        elif action == 'busca_gausers':
            texto = request.POST['q']
            g_es = Gauser_extra.objects.filter(ronda=g_e.ronda, perfiles__in=[12, 13, 14])
            g_es1 = g_es.filter(Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto) | Q(
                cargo__icontains=texto)).values_list('gauser__id', 'gauser__last_name', 'gauser__first_name', 'cargo')
            keys = ('id', 'text')
            list1 = [dict(zip(keys, (row[0], '%s, %s (%s)' % (row[1], row[2], row[3])))) for row in g_es1]
            return HttpResponse(json.dumps(list1))
        elif action == 'guardar_texto':
            titulo = Titulo_FP.objects.get(id=request.POST['id'])
            titulo.texto = request.POST['val']
            titulo.borrador = False if (len(titulo.texto) > 10 and len(titulo.asunto) > 5) else True
            titulo.save()
            return HttpResponse(titulo.texto)
        elif action == 'guardar_asunto':
            titulo = Titulo_FP.objects.get(id=request.POST['id'])
            titulo.asunto = request.POST['val']
            titulo.borrador = False if (len(titulo.texto) > 10 and len(titulo.asunto) > 5) else True
            titulo.save()
            return HttpResponse(titulo.asunto)
        elif action == 'check_print_asunto':
            titulo = Titulo_FP.objects.get(id=request.POST['id'])
            titulo.print_asunto = not titulo.print_asunto
            titulo.save()
            return HttpResponse('')
        elif action == 'guardar_fecha_firma':
            titulo = Titulo_FP.objects.get(id=request.POST['id'])
            titulo.fecha_firma = datetime.strptime(request.POST['val'], "%d-%m-%Y").date()
            titulo.save()
            return HttpResponse('')
        elif action == 'guardar_firmante':
            titulo = Titulo_FP.objects.get(id=request.POST['id'])
            try:
                titulo.firmante = Gauser.objects.get(id=request.POST['val'])
            except:
                titulo.firmante = None
            titulo.save()
            return HttpResponse('')
        elif action == 'guardar_receptores':
            titulo = Titulo_FP.objects.get(id=request.POST['id'])
            titulo.receptores.clear()
            receptores = request.POST.getlist('val[]')
            for receptor in receptores:
                data = receptor.split('___')
                if data[1] == 'ge':
                    ge = Gauser_extra.objects.get(id=data[0])
                    contacto = Contacto.objects.create(creador=g_e.gauser, empresa=ge.ronda.entidad.name,
                                                       cargo=ge.cargo,
                                                       direccion=ge.ronda.entidad.address,
                                                       cp=ge.ronda.entidad.localidad,
                                                       localidad=ge.ronda.entidad.get_localidad_display(),
                                                       provincia='La Rioja',
                                                       email=ge.gauser.email, telefono=ge.gauser.telmov,
                                                       nombre=ge.gauser.get_full_name())
                else:
                    contacto = Contacto.objects.get(id=data[0])
                titulo.receptores.add(contacto)
            return HttpResponse(receptores)
        elif action == 'guardar_autores':
            titulo = Titulo_FP.objects.get(id=request.POST['id'])
            titulo.autores.clear()
            autores = Gauser.objects.filter(id__in=request.POST.getlist('val[]'))
            titulo.autores.add(*autores)
            return HttpResponse(autores)


@login_required()
def editar_titulo(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        if request.POST['action'] == 'pdf' and g_e.has_permiso('crear_titulo'):
            titulo = Titulo_FP.objects.get(id=request.POST['titulo'])
            titulo.asunto = request.POST['asunto']
            titulo.texto = request.POST['texto']
            titulo.save()
            crear_aviso(request, True, 'Detecta id y se propone a generar el pdf de: %s' % (titulo.asunto))
            fichero = '%s_%s' % (g_e.ronda.entidad.code, titulo.id)
            c = render_to_string('titulo2pdf.html', {
                'titulo': titulo,
            }, request=request)
            dce = get_dce(g_e.ronda.entidad, 'Configuración de programaciones de CCFF')
            ruta = MEDIA_PROGRAMACIONES + g_e.ronda.entidad.code + '/' + fichero + '.pdf'
            genera_pdf(c, dce, ruta_archivo=ruta)
            return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename='%s.pdf' % fichero,
                                content_type='application/pdf')
    else:
        form_contacto = ContactoForm()
        try:
            titulo = Titulo_FP.objects.get(pk=request.GET['doc'])
            crear_aviso(request, True, 'Entra en editar el titulo %s.' % (titulo.id))
        except:
            titulo = Titulo_FP.objects.create(entidad=g_e.ronda.entidad, firmante=g_e.gauser, fecha_firma=date.today(),
                                              asunto='', texto='')
            titulo.autores.add(g_e.gauser)
            crear_aviso(request, True, 'Entra en crear titulo.')
    # return render(request, "crear_titulo_foundation.html",
    return render(request, "crear_titulo_foundation_ckeditor.html",
                  {
                      'formname': 'Crear_titulo',
                      'iconos':
                          ({'nombre': 'check', 'texto': 'PDF',
                            'title': 'Generar pdf del documento', 'permiso': 'crear_titulo'},
                           {'nombre': 'list', 'texto': 'Mis titulos',
                            'title': 'Volver a la lista de mis titulos', 'permiso': 'crear_titulo'},
                           ),
                      'form_contacto': form_contacto,
                      'titulo': titulo,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@permiso_required('acceso_cuerpos_funcionarios')
def cuerpos_funcionarios_entidad(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'check_especialidad':
            c_id = request.POST['cuerpo']
            e_id = request.POST['especialidad']
            try:
                e = Especialidad_funcionario.objects.get(cuerpo__id=c_id, id=e_id)
                ee, c = Especialidad_entidad.objects.get_or_create(ronda=g_e.ronda, especialidad=e)
                if c:
                    return JsonResponse({'ok': True, 'checked': True})
                else:
                    ee.delete()
                    return JsonResponse({'ok': True, 'checked': False})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

    elif request.method == 'POST':
        if request.POST['action'] == 'pdf' and g_e.has_permiso('crear_titulo'):
            pass

    cuerpos = Cuerpo_funcionario.objects.all()
    especialidades_entidad = Especialidad_entidad.objects.filter(ronda=g_e.ronda)
    cuerpos_entidad_id = especialidades_entidad.values_list('especialidad__cuerpo__id', flat=True)
    cuerpos_entidad = cuerpos.filter(id__in=cuerpos_entidad_id)
    return render(request, "cuerpos_funcionarios_entidad.html",
                  {
                      'formname': 'cuerpos_funcionarios_entidad',
                      'iconos':
                          ({'nombre': 'check', 'texto': 'PDF',
                            'title': 'Generar pdf del documento', 'permiso': 'crear_titulo'},
                           {'nombre': 'list', 'texto': 'Mis titulos',
                            'title': 'Volver a la lista de mis titulos', 'permiso': 'crear_titulo'},
                           ),
                      'cuerpos': cuerpos,
                      'cuerpos_entidad': cuerpos_entidad,
                      'especialidades_entidad': especialidades_entidad.values_list('especialidad__id', flat=True),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


def arreglar_infinitivo_verbos():
    texto_error = ['Meder o visualizado', 'Meder y visualizado', 'Meder', 'Definer', 'Uner',
                   'Identificar y relacionado', 'Descrito', 'Distribuer',
                   'Fijar y conexionado', 'Ubicar y fijado', 'Tender y conexionado', 'Propuesto']
    t_corregido = ['Medir o visualizar', 'Medir y visualizar', 'Medir', 'Definir', 'Unir', 'Identificar y relacionar',
                   'Describir', 'Distribuir',
                   'Fijar y conexionar', 'Ubicar y fijar', 'Tender y conexionar', 'Proponer']
    obs = Objetivo.objects.all()
    for o in obs:
        for i in range(len(texto_error)):
            o.texto = o.texto.replace(texto_error[i], t_corregido[i])
            o.save()


@login_required()
def copiar_programacion(request):
    prog = Programacion_modulo.objects.get(id=request.GET['prog'])
    ge = Gauser_extra.objects.get(id=request.GET['ge'])
    tit = Titulo_FP.objects.get(id=request.GET['tit'])
    mat = Materia.objects.get(id=request.GET['mat'])
    nueva_prog = prog
    nueva_prog.pk = None
    nueva_prog.g_e = ge
    nueva_prog.titulo = tit
    nueva_prog.modulo = mat
    nueva_prog.file_path = ''
    nueva_prog.save()
    nueva_prog.obj_gen.clear()
    for ud in prog.ud_modulo_set.all():
        old_ud = ud
        ud.pk = None
        ud.programacion = nueva_prog
        ud.save()
        for con in old_ud.cont_unidad_modulo_set.all():
            con.pk = None
            con.unidad = ud
            con.save()
    return HttpResponse('Progamación copiada')


def generar_datos(request):
    import random
    c = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    SEXO = 'HM'
    n = int(request.GET['n'])
    gs = Gauser.objects.all()
    max = gs.count()
    fallos = 0
    fichero_csv = '/home/juanjo/django/gauss_asocia/media/' + 'datos_aleatorios_carga_masiva.csv'
    header = 'id_socio;id_organizacion;nombre;apellidos;dni;telefono_fijo;telefono_movil;direccion;cp;localidad;provincia;sexo;email;nacimiento;fecha_alta;observaciones;iban;nombre_tutor1;apellidos_tutor1;dni_tutor1;telefono_fijo_tutor1;telefono_movil_tutor1;direccion_tutor1;cp_tutor1;localidad_tutor1;provincia_tutor1;sexo_tutor1;email_tutor1;nacimiento_tutor1;fecha_alta_tutor1;observaciones_tutor1;iban_tutor1;nombre_tutor2;apellidos_tutor2;dni_tutor2;telefono_fijo_tutor2;telefono_movil_tutor2;direccion_tutor2;cp_tutor2;localidad_tutor2;provincia_tutor2;sexo_tutor2;email_tutor2;nacimiento_tutor2;fecha_alta_tutor2;observaciones_tutor2;iban_tutor2\n'
    with open(fichero_csv, "w") as myfile:
        myfile.write("{0}".format(header))
    for i in range(n):
        try:
            id_socio = str(random.randrange(1000, 9999, 1))
            id_organizacion = str(random.randrange(10000, 99999, 1))
            nombre = gs[random.randrange(0, max)].first_name
            apellidos = gs[random.randrange(0, max)].last_name.split()[0] + ' ' + \
                        gs[random.randrange(0, max)].last_name.split()[0]
            dni = str(random.randrange(10000000, 99999999, 1)) + random.choice(c)
            telefono_fijo = str(random.randrange(911000000, 999999999, 1))
            telefono_movil = str(random.randrange(611000000, 699999999, 1))
            direccion = ''
            cp = '26' + str(random.randrange(000, 999, 1))
            localidad = gs[random.randrange(0, max)].localidad
            provincia = gs[random.randrange(0, max)].provincia
            sexo = random.choice(SEXO)
            email = dni + '@gaumentada.es'
            nacimiento = str(random.randrange(0, 30, 1)) + '/' + str(random.randrange(0, 12, 1)) + '/' + str(
                random.randrange(1995, 2015, 1))
            fecha_alta = str(random.randrange(0, 30, 1)) + '/' + str(random.randrange(0, 12, 1)) + '/' + str(
                random.randrange(2016, 2017, 1))
            observaciones = ''
            iban = 'ES' + str(random.randrange(1000000000000000000000, 3000000000000000000000, 1))
            nombre_tutor1 = gs[random.randrange(0, max)].first_name
            apellidos_tutor1 = gs[random.randrange(0, max)].last_name.split()[0] + ' ' + \
                               gs[random.randrange(0, max)].last_name.split()[0]
            dni_tutor1 = str(random.randrange(10000000, 99999999, 1)) + random.choice(c)
            telefono_fijo_tutor1 = str(random.randrange(911000000, 999999999, 1))
            telefono_movil_tutor1 = str(random.randrange(611000000, 699999999, 1))
            direccion_tutor1 = ''
            cp_tutor1 = cp
            localidad_tutor1 = localidad
            provincia_tutor1 = provincia
            sexo_tutor1 = 'M'
            email_tutor1 = dni_tutor1 + '@gaumentada.es'
            nacimiento_tutor1 = str(random.randrange(0, 30, 1)) + '/' + str(random.randrange(0, 12, 1)) + '/' + str(
                random.randrange(1968, 1975, 1))
            fecha_alta_tutor1 = fecha_alta
            observaciones_tutor1 = ''
            iban_tutor1 = iban
            nombre_tutor2 = gs[random.randrange(0, max)].first_name
            apellidos_tutor2 = gs[random.randrange(0, max)].last_name.split()[0] + ' ' + \
                               gs[random.randrange(0, max)].last_name.split()[0]
            dni_tutor2 = str(random.randrange(10000000, 99999999, 1)) + random.choice(c)
            telefono_fijo_tutor2 = str(random.randrange(911000000, 999999999, 1))
            telefono_movil_tutor2 = str(random.randrange(611000000, 699999999, 1))
            direccion_tutor2 = ''
            cp_tutor2 = cp
            localidad_tutor2 = localidad
            provincia_tutor2 = provincia
            sexo_tutor2 = 'H'
            email_tutor2 = dni_tutor2 + '@gaumentada.es'
            nacimiento_tutor2 = str(random.randrange(0, 30, 1)) + '/' + str(random.randrange(0, 12, 1)) + '/' + str(
                random.randrange(1968, 1975, 1))
            fecha_alta_tutor2 = fecha_alta
            observaciones_tutor2 = ''
            iban_tutor2 = iban
            fila = '%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s\n' % (
                id_socio, id_organizacion, nombre, apellidos, dni, telefono_fijo, telefono_movil, direccion, cp,
                localidad,
                provincia, sexo, email, nacimiento, fecha_alta, observaciones, iban, nombre_tutor1, apellidos_tutor1,
                dni_tutor1, telefono_fijo_tutor1, telefono_movil_tutor1, direccion_tutor1, cp_tutor1, localidad_tutor1,
                provincia_tutor1, sexo_tutor1, email_tutor1, nacimiento_tutor1, fecha_alta_tutor1, observaciones_tutor1,
                iban_tutor1, nombre_tutor2, apellidos_tutor2, dni_tutor2, telefono_fijo_tutor2, telefono_movil_tutor2,
                direccion_tutor2, cp_tutor2, localidad_tutor2, provincia_tutor2, sexo_tutor2, email_tutor1,
                nacimiento_tutor2,
                fecha_alta_tutor2, observaciones_tutor2, iban_tutor2)
            with open(fichero_csv, "a") as myfile:
                myfile.write("{0}".format(fila.encode('utf-8')))
        except:
            fallos += 1
    total = n - fallos
    return HttpResponse('Se han generado datos aleatorios de %s usuarios, finalizado con %s fallos' % (total, fallos))


@permiso_required('acceso_aspectos_pga')
def aspectos_pga(request):
    g_e = request.session['gauser_extra']
    pga, c = PGA.objects.get_or_create(ronda=g_e.ronda)
    claustros = ReunionesPrevistas.objects.filter(pga=pga, tipo='CLA')
    consejos = ReunionesPrevistas.objects.filter(pga=pga, tipo='CON')
    evaluaciones = ReunionesPrevistas.objects.filter(pga=pga, tipo='EVA')
    pgadocs = PGAdocumento.objects.filter(pga=pga)
    try:
        aaee_file = pgadocs.get(doc_nombre='programa_actividades_extraescolares')
    except:
        aaee_file = False
    try:
        libros_file = pgadocs.get(doc_nombre='libros_de_texto_y_materiales')
    except:
        libros_file = False
    try:
        estadistica_file = pgadocs.get(doc_nombre='estadistica_comienzo_curso')
    except:
        estadistica_file = False

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'check_especialidad':
            c_id = request.POST['cuerpo']
            e_id = request.POST['especialidad']
            try:
                e = Especialidad_funcionario.objects.get(cuerpo__id=c_id, id=e_id)
                ee, c = Especialidad_entidad.objects.get_or_create(ronda=g_e.ronda, especialidad=e)
                if c:
                    return JsonResponse({'ok': True, 'checked': True})
                else:
                    ee.delete()
                    return JsonResponse({'ok': True, 'checked': False})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_texto_pga':
            try:
                pga = PGA.objects.get(ronda=g_e.ronda, id=request.POST['pga'])
                setattr(pga, request.POST['campo'], request.POST['texto'])
                pga.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'aceptar_reunion':
            fecha = datetime.strptime(request.POST['fecha'], '%d/%m/%Y %H:%M')
            pga = PGA.objects.get(ronda=g_e.ronda, id=request.POST['pga'])
            r = ReunionesPrevistas.objects.create(pga=pga, description=request.POST['description'],
                                                  nombre=request.POST['nombre'], tipo=request.POST['tipo'], fecha=fecha)
            li = render_to_string('aspectos_pga_accordion_content_li.html', {'r': r})
            return JsonResponse({'ok': True, 'li': li, 'id': '#%s%s' % (r.tipo, pga.id)})
        elif request.POST['action'] == 'delete_li':
            r = ReunionesPrevistas.objects.get(pga__id=request.POST['pga'], pga__ronda=g_e.ronda, id=request.POST['id'])
            r.delete()
            return JsonResponse({'ok': True})
    elif request.method == 'POST':
        if request.POST['action'] == 'sube_file_pga':
            pga = PGA.objects.get(id=request.POST['pga'])
            n_files = int(request.POST['n_files'])
            mensaje = False
            p = {'doc_nombre': False}
            if g_e.has_permiso('carga_programaciones'):
                for i in range(n_files):
                    fichero = request.FILES['fichero_xhr' + str(i)]
                    try:
                        p = PGAdocumento.objects.get(pga=pga, doc_nombre=request.POST['name'])
                        if p.doc_file:
                            os.remove(p.doc_file.path)
                        p.doc_file = fichero
                        p.content_type = fichero.content_type
                        p.save()
                    except:
                        p = PGAdocumento.objects.create(pga=pga, doc_nombre=request.POST['name'], doc_file=fichero,
                                                        content_type=fichero.content_type)
                return JsonResponse({'ok': True, 'mensaje': mensaje, 'file': p.doc_nombre})
            else:
                mensaje = 'No tienes permiso para cargar archivos de la PGA.'
                return JsonResponse({'ok': False, 'mensaje': mensaje, 'file': False})
        elif request.POST['action'] == 'download_file':
            try:
                pgadoc = PGAdocumento.objects.get(id=request.POST['archivo'], pga__id=request.POST['pga'])
                response = HttpResponse(pgadoc.doc_file, content_type=pgadoc.content_type)
                response['Content-Disposition'] = 'attachment; filename=%s' % pgadoc.filename
                return response
            except:
                pass
        elif request.POST['action'] == 'downloadpga':
            pga = PGA.objects.get(id=request.POST['pga'], ronda=g_e.ronda)
            try:
                # Procesado del archivo de aspectos de la PGA
                dce = get_dce(g_e.ronda.entidad, 'Configuración de programaciones de CCFF')
                c = render_to_string('aspectos_generales_pga2pdf.html', {'pga': pga, 'dce': dce})
                ruta = rutas_aspectos_pga(pga)['absoluta']
                nombre_fichero = 'aspectos_generales_pga'
                if os.path.exists('%s%s.pdf' % (ruta, nombre_fichero)):
                    os.remove('%s%s.pdf' % (ruta, nombre_fichero))
                ruta = MEDIA_PROGRAMACIONES + g_e.ronda.entidad.code + '/' + nombre_fichero + '.pdf'
                genera_pdf(c, dce, ruta_archivo=ruta)
                if os.path.exists('%s%s.html' % (ruta, nombre_fichero)):
                    os.remove('%s%s.html' % (ruta, nombre_fichero))
                # Procesado del archivo de aspectos del PEC
                pec = PEC.objects.get(entidad=g_e.ronda.entidad)
                c = render_to_string('aspectos_generales_pec2pdf.html', {'pec': pec, 'dce': dce})
                ruta = rutas_pec(pec)['absoluta']
                nombre_fichero = 'aspectos_generales_pec'
                if os.path.exists('%s%s.pdf' % (ruta, nombre_fichero)):
                    os.remove('%s%s.pdf' % (ruta, nombre_fichero))
                ruta = MEDIA_PROGRAMACIONES + g_e.ronda.entidad.code + '/' + nombre_fichero + '.pdf'
                genera_pdf(c, dce, ruta_archivo=ruta)
                if os.path.exists('%s%s.html' % (ruta, nombre_fichero)):
                    os.remove('%s%s.html' % (ruta, nombre_fichero))
                # Generación del ZIP que contiene toda la PGA
                ruta_centro = ruta_programaciones(g_e.ronda, tipo='centro')
                ruta_curso_escolar = ruta_programaciones(g_e.ronda, tipo='ronda')
                fichero = "PGA_{0}_{1}".format(g_e.ronda.entidad.code, slugify(g_e.ronda.nombre))
                ruta_zip = ruta_programaciones(g_e.ronda, tipo='centro')
                try:
                    # Create target Directory. Si existiera se produciría la excepción
                    os.mkdir(ruta_curso_escolar)
                    os.chdir(ruta_curso_escolar)  # Determino el directorio de trabajo
                except FileExistsError:
                    os.chdir(ruta_curso_escolar)  # Determino el directorio de trabajo
                shutil.make_archive(ruta_zip + fichero, 'zip', ruta_curso_escolar)
                fich = open(ruta_zip + fichero + '.zip', 'rb')
                crear_aviso(request, True, "%s genera y descarga %s" % (g_e.gauser.get_full_name(), fichero))
                response = HttpResponse(fich, content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=%s' % (fichero + '.zip')
                return response
            except Exception as msg:
                crear_aviso(request, False, 'Se ha producido un error: %s' % str(msg))

    return render(request, "aspectos_pga.html",
                  {
                      'formname': 'aspectos_pga',
                      'pgas': PGA.objects.filter(ronda__entidad=g_e.ronda.entidad),
                      'evaluaciones': evaluaciones,
                      'consejos': consejos,
                      'claustros': claustros,
                      'aaee_file': aaee_file,
                      'libros_file': libros_file,
                      'estadistica_file': estadistica_file,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@permiso_required('acceso_pec')
def proyecto_educativo_centro(request):
    g_e = request.session['gauser_extra']
    pec, c = PEC.objects.get_or_create(entidad=g_e.ronda.entidad)
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'update_texto_pec':
            try:
                pec = PEC.objects.get(entidad=g_e.ronda.entidad, id=request.POST['pec'])
                setattr(pec, request.POST['campo'], request.POST['texto'])
                pec.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
    elif request.method == 'POST':
        if request.POST['action'] == 'sube_file_pec':
            pec = PEC.objects.get(id=request.POST['pec'])
            n_files = int(request.POST['n_files'])
            mensaje = False
            p = {'doc_nombre': False}
            if g_e.has_permiso('carga_programaciones'):
                for i in range(n_files):
                    fichero = request.FILES['fichero_xhr' + str(i)]
                    try:
                        p = PECdocumento.objects.get(pec=pec, tipo=request.POST['name'])
                        if p.doc_file:
                            os.remove(p.doc_file.path)
                        p.doc_file = fichero
                        p.doc_nombre = slugify(p.get_tipo_display())
                        p.content_type = fichero.content_type
                        p.save()
                    except:
                        p = PECdocumento.objects.create(pec=pec, doc_nombre=request.POST['name'], doc_file=fichero,
                                                        content_type=fichero.content_type, tipo=request.POST['name'])
                        p.doc_nombre = slugify(p.get_tipo_display())
                        p.save()
                return JsonResponse({'ok': True, 'mensaje': mensaje})
            else:
                mensaje = 'No tienes permiso para cargar archivos del PEC.'
                return JsonResponse({'ok': False, 'mensaje': mensaje})
        elif request.POST['action'] == 'download_file':
            try:
                pecdoc = PECdocumento.objects.get(id=request.POST['archivo'], pec__id=request.POST['pec'],
                                                  pec__entidad=g_e.ronda.entidad)
                response = HttpResponse(pecdoc.doc_file, content_type=pecdoc.content_type)
                response['Content-Disposition'] = 'attachment; filename=%s' % pecdoc.filename
                return response
            except:
                pass
    return render(request, "proyecto_educativo_centro.html",
                  {
                      'formname': 'pec',
                      'pec': pec,
                      'TIPOS': (('pat', 'Plan de Acción Tutorial'),
                                ('poap', 'Plan de Orientación Académica y Profesional'),
                                ('pad', 'Plan de Atención a la Diversidad'),
                                ('pc', 'Plan de Convivencia'),
                                ('rof', 'Reglamento de Organización y Funcionamiento')),
                      'aspectos': ['signos', 'organizacion', 'lineapedagogica', 'participacion', 'proyectos'],
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


#############################################################################
################# PROGRAMACIONES LOMLOE SECUNDARIA ##########################
#############################################################################

# def reordenar_saberes(saber, valor):
#     borrar_saber = True if valor > 999 else False
#     progsec = saber.psec
#     orden_saber = saber.orden
#     saberes = progsec.saberbas_set.exclude(id=saber.id)
#     num_saberes = saberes.count() + 1
#     valor = num_saberes if valor > num_saberes else valor
#     if valor > orden_saber:
#         nuevo_orden = 0
#         for s in saberes.filter(orden__lte=valor):
#             nuevo_orden += 1
#             s.orden = nuevo_orden
#             s.save()
#     if valor < orden_saber:
#         nuevo_orden = valor
#         for s in saberes.filter(orden__gte=valor):
#             nuevo_orden += 1
#             s.orden = nuevo_orden
#             s.save()
#     saber.orden = valor
#     saber.save()
#     if borrar_saber:
#         saber.borrado = True
#         saber.save()
# return render_to_string('progsec_accordion_content_saberes.html', {'progsec': progsec})


def reordenar_saberes_comienzo(psec):
    for i, s in enumerate(psec.saberbas_set.filter(borrado=False)):
        s.orden = i + 1
        s.save()
    return render_to_string('progsec_accordion_content_saberes.html', {'progsec': psec})


# @permiso_required('acceso_progsecundaria')
def progsecundaria(request):
    # for p in ProgSec.objects.all():
    #     p.identificador = pass_generator()
    #     p.save()
    # try:
    g_e = request.session['gauser_extra']
    try:
        ies = request.session['ronda'].entidad.entidadextra.depende_de
    except:
        # Esta excepción ocurre en centros que no se cargan de Racima, por ejemplo el CRIE
        EntidadExtra.objects.get_or_create(entidad=g_e.ronda.entidad)
        ies = request.session['ronda'].entidad.entidadextra.depende_de
    if ies:
        try:
            g_eies = Gauser_extra.objects.get(gauser=g_e.gauser, ronda=ies.ronda)
            g_ep, c = Gauser_extra_programaciones.objects.get_or_create(ge=g_eies)
            request.session['es_sies'] = True
        except:
            return HttpResponse('Error. No tienes usuario en tu IES. Comunica incidencia al Administrador')
    else:
        g_ep, c = Gauser_extra_programaciones.objects.get_or_create(ge=g_e)
        request.session['es_sies'] = False
    if c:
        g_ep.puesto = g_e.puesto
        g_ep.save()
    if ies:
        pga, c = PGA.objects.get_or_create(ronda=ies.ronda)
    else:
        pga, c = PGA.objects.get_or_create(ronda=g_e.ronda)
    # Las siguientes líneas son para asegurar que los creadores de una ProgSec siempre tendrán permiso 'X'
    psecs_ge_propietario = ProgSec.objects.filter(pga=pga, gep=g_ep)
    for psec in psecs_ge_propietario:
        dps, c = DocProgSec.objects.get_or_create(psec=psec, gep=g_ep)
        dps.permiso = 'X'
        dps.save()
    # Fin de las líneas que aseguran que el propietario tiene permiso 'X'
    if g_e.has_permiso('ve_todas_programaciones'):
        progsecs = ProgSec.objects.filter(pga=pga, borrado=False).order_by('areamateria__curso')
        #progsecs = ProgSec.objects.filter(pga=pga, borrado=False)
        
    else:
        progsec_ids = DocProgSec.objects.filter(gep=g_ep).values_list('psec__id', flat=True)
        progsecs = ProgSec.objects.filter(pga=pga, id__in=progsec_ids, borrado=False).order_by('areamateria__curso')
        #progsecs = ProgSec.objects.filter(pga=pga, id__in=progsec_ids, borrado=False)
    if request.method == 'POST' and request.is_ajax() and not ies:
        action = request.POST['action']
        if action == 'get_areasmaterias':
            try:
                ams = AreaMateria.objects.filter(curso=request.POST['curso'])
                return JsonResponse({'ok': True, 'valores': [{'valor': am.id, 'texto': am.nombre} for am in ams]})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'crea_progsec':
            try:
                if g_e.has_permiso('crea_programaciones'):
                    CURSOS_CICLOS = {'00INF0': 'Primer Ciclo Infantil', '00INF1': 'Primer Ciclo Infantil',
                                     '00INF2': 'Primer Ciclo Infantil', '00INF3': 'Segundo Ciclo Infantil',
                                     '00INF4': 'Segundo Ciclo Infantil', '00INF5': 'Segundo Ciclo Infantil',
                                     '10PRI1': 'Primer Ciclo Primaria', '10PRI2': 'Primer Ciclo Primaria',
                                     '10PRI3': 'Segundo Ciclo Primaria', '10PRI4': 'Segundo Ciclo Primaria',
                                     '10PRI5': 'Tercer Ciclo Primaria', '10PRI6': 'Tercer Ciclo Primaria'}
                    areamateria = AreaMateria.objects.get(id=request.POST['areamateria'])
                    nombre_psec = '%s - %s' % (areamateria.get_curso_display(), areamateria.nombre)
                    try:
                        ciclo = CURSOS_CICLOS[request.POST['curso']]
                        etapa = ''.join([i for i in request.POST['curso'] if not i.isdigit()])
                        dep, c = Departamento.objects.get_or_create(ronda=g_e.ronda, nombre=ciclo, etapa=etapa,
                                                                    abreviatura=etapa)
                        progsec = ProgSec.objects.create(pga=pga, gep=g_ep, areamateria=areamateria,
                                                         departamento=dep, nombre=nombre_psec)
                    except:
                        crea_departamentos(g_e.ronda)
                        progsec = ProgSec.objects.create(pga=pga, gep=g_ep, areamateria=areamateria, nombre=nombre_psec)
                    DocProgSec.objects.get_or_create(psec=progsec, gep=g_ep, permiso='X')
                    for ce in areamateria.competenciaespecifica_set.all():
                        cepsec = CEProgSec.objects.create(psec=progsec, ce=ce)
                        for cev in ce.criterioevaluacion_set.all():
                            CEvProgSec.objects.create(cepsec=cepsec, cev=cev)
                    html = render_to_string('progsec_accordion.html',
                                            {'buscadas': False, 'progsecs': [progsec], 'g_e': g_e, 'nueva': True})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    JsonResponse({'ok': False, 'msg': 'No tienes permiso para crear programaciones.'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'busca_progsec_manual':
            try:
                ronda = Ronda.objects.get(id=request.POST['ronda'])
                if g_e.has_claves_cargos(['g_director_centro', 'g_miembro_equipo_directivo']):
                    id_progsecs = ProgSec.objects.filter(pga__ronda=ronda).values_list('id', flat=True)
                else:
                    id_progsecs1 = DocProgSec.objects.filter(gep__ge__gauser=g_e.gauser,
                                                             gep__ge__ronda=ronda).values_list('psec__id', flat=True)
                    id_progsecs2 = ProgSec.objects.filter(gep__ge__gauser=g_e.gauser,
                                                          gep__ge__ronda=ronda).values_list('id', flat=True)
                    id_progsecs = list(set(list(id_progsecs1) + list(id_progsecs2)))
                progsecs = ProgSec.objects.filter(id__in=id_progsecs)
                html = render_to_string('progsec_accordion.html', {'progsecs': progsecs, 'buscadas': True})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'open_accordion':
            try:
                progsec = ProgSec.objects.get(id=request.POST['id'], identificador=request.POST['identificador'])
                # Durante la copia de programaciones el departamento es None, pero si es INF o PRI no debería ser así:
                CURSOS_CICLOS = {'00INF0': 'Primer Ciclo Infantil', '00INF1': 'Primer Ciclo Infantil',
                                 '00INF2': 'Primer Ciclo Infantil', '00INF3': 'Segundo Ciclo Infantil',
                                 '00INF4': 'Segundo Ciclo Infantil', '00INF5': 'Segundo Ciclo Infantil',
                                 '10PRI1': 'Primer Ciclo Primaria', '10PRI2': 'Primer Ciclo Primaria',
                                 '10PRI3': 'Segundo Ciclo Primaria', '10PRI4': 'Segundo Ciclo Primaria',
                                 '10PRI5': 'Tercer Ciclo Primaria', '10PRI6': 'Tercer Ciclo Primaria'}
                if not progsec.departamento and progsec.areamateria.curso in CURSOS_CICLOS:
                    ciclo = CURSOS_CICLOS[progsec.areamateria.curso]
                    etapa = ''.join([i for i in progsec.areamateria.curso if not i.isdigit()])
                    dep, c = Departamento.objects.get_or_create(ronda=g_e.ronda, nombre=ciclo, etapa=etapa,
                                                                abreviatura=etapa)
                    progsec.departamento = dep
                    progsec.save()
                # Fin de las líneas para evitar tener programaciones de INF o PRI sin ciclo asignado
                docentes_id = DocProgSec.objects.filter(psec=progsec).values_list('gep__ge', flat=True)
                departamentos = Departamento.objects.filter(ronda=g_e.ronda)
                # if departamentos.count() == 0:
                #     crea_departamentos(g_e.ronda)
                #     departamentos = Departamento.objects.filter(ronda=g_e.ronda)
                html = render_to_string('progsec_accordion_content.html',
                                        {'progsec': progsec, 'gep': g_ep, 'departamentos': departamentos,
                                         'docentes': profesorado(g_e.ronda.entidad), 'docentes_id': docentes_id})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_progsec':
            # progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
            #                               id=request.POST['id'])
            # msg = 'Opción desabilita temporalmente. Disculpe las molestias. %s' % progsec.es_borrable
            # return JsonResponse({'ok': False, 'msg': msg})
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                # if 'C' in permiso:
                #     msg = '<p>Hay cuadernos de docentes creados. Primero deberían ser borrados.</p>'
                #     cuadernos = []
                #     for cuaderno in progsec.cuadernoprof_set.filter(borrado=False):
                #         cuadernos.append('<br>%s - (%s)' % (cuaderno.nombre, cuaderno.ge.gauser.get_full_name()))
                #     msg += ''.join(cuadernos)
                #     return JsonResponse({'ok': False, 'msg': msg})
                if (permiso == 'X' or progsec.gep.ge == g_e):
                    if progsec.es_borrable:
                        progsec.tipo = "BOR" 
                        progsec.borrado = True
                        progsec.save()
                        return JsonResponse({'ok': True})
                    else:
                        msg = 'La programación está siendo usada en uno o varios cuadernos docentes que ya contienen calificaciones.'
                        return JsonResponse({'ok': False, 'msg': msg})
                else:
                    msg = 'No tienes permiso para borrar esta programación didáctica.'
                    return JsonResponse({'ok': False, 'msg': msg, 'permiso': permiso})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'recuperar_progsec':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if (permiso == 'X' or progsec.gep.ge == g_e):
                    progsec.borrado = False
                    progsec.save()
                    progsec_ids = DocProgSec.objects.filter(gep=g_ep).values_list('psec__id', flat=True)
                    progsecs = ProgSec.objects.filter(pga=pga, id__in=progsec_ids, borrado=False)
                    html = render_to_string('progsec_accordion.html', {'progsecs': progsecs})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    msg = 'No tienes permiso para recuperar esta programación didáctica.'
                    return JsonResponse({'ok': False, 'msg': msg, 'permiso': permiso})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'copiar_progsec':
            try:
                crea_departamentos(g_e.ronda)
                ps = ProgSec.objects.get(id=request.POST['progsec'])
                ps_nueva = ProgSec.objects.get(id=ps.id)
                ps_nueva.pk = None
                ps_nueva.pga = pga
                ps_nueva.gep = g_ep
                ps_nueva.nombre = ps.nombre + ' (Copia)'
                ps_nueva.departamento = None
                ps_nueva.tipo = 'BOR'
                ps_nueva.borrado = False
                ps_nueva.save()
                DocProgSec.objects.create(psec=ps_nueva, gep=g_ep, permiso='X')
                for ceps in ps.ceprogsec_set.all():
                    ceps_nueva = CEProgSec.objects.create(psec=ps_nueva, ce=ceps.ce, valor=ceps.valor)
                    for cevps in ceps.cevprogsec_set.all():
                        CEvProgSec.objects.create(cepsec=ceps_nueva, cev=cevps.cev, valor=cevps.valor)
                for lr in ps.librorecurso_set.all():
                    lr.pk = None
                    lr.psec = ps_nueva
                    lr.save()
                for actex in ps.actexcom_set.all():
                    actex.pk = None
                    actex.psec = ps_nueva
                    actex.save()
                for sb in ps.saberbas_set.all():
                    sb_nuevo = SaberBas.objects.get(id=sb.id)
                    sb_nuevo.pk = None
                    sb_nuevo.psec = ps_nueva
                    sb_nuevo.save()
                    for actex in sb.actexcoms.all():
                        sb_nuevo.actexcoms.add(*ps_nueva.actexcom_set.filter(nombre=actex.nombre))
                    for lr in sb.librorecursos.all():
                        sb_nuevo.actexcoms.add(*ps_nueva.librorecurso_set.filter(nombre=lr.nombre))
                    for sa in sb.sitapren_set.all():
                        sa_nueva = SitApren.objects.create(sbas=sb_nuevo, objetivo=sa.objetivo, nombre=sa.nombre,
                                                           contenidos_sbas=sa.contenidos_sbas)
                        for cep in sa.ceps.all():
                            sa_nueva.ceps.add(*ps_nueva.ceprogsec_set.filter(ce=cep.ce))
                        for asa in sa.actsitapren_set.all():
                            asa_nueva = ActSitApren.objects.get(id=asa.id)
                            asa_nueva.pk = None
                            asa_nueva.sapren = sa_nueva
                            asa_nueva.save()
                            for ieval in asa.instreval_set.all():
                                ieval_nuevo = InstrEval.objects.get(id=ieval.id)
                                ieval_nuevo.pk = None
                                ieval_nuevo.asapren = asa_nueva
                                ieval_nuevo.save()
                                for cieval in ieval.criinstreval_set.all():
                                    cevps = CEvProgSec.objects.get(cepsec__psec=ps_nueva, cev=cieval.cevps.cev)
                                    CriInstrEval.objects.create(ieval=ieval_nuevo, cevps=cevps, peso=cieval.peso)
                html = render_to_string('progsec_accordion.html',
                                        {'buscadas': False, 'progsecs': [ps_nueva], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'msg': str(msg), 'ok': False})
        # Espe: Enviar Copia de la programación al docente seleccionado
        elif action == 'enviar_copia_progsec':
            try:
                ps = ProgSec.objects.get(id=request.POST['progsec'])
                doc_sel = Gauser_extra.objects.get(id=request.POST['docente'])
                ronda_destino = doc_sel.ronda
                pga_destino, c = PGA.objects.get_or_create(ronda=ronda_destino)
                doc_progsec, c = Gauser_extra_programaciones.objects.get_or_create(ge=doc_sel)
                crea_departamentos(ronda_destino)
                ps_nueva = ProgSec.objects.get(id=ps.id)
                ps_nueva.pk = None
                ps_nueva.pga = pga_destino
                # ps_nueva.gep = g_ep
                ps_nueva.gep = doc_progsec
                ps_nueva.nombre = ps.nombre + ' (Copia de: ' + g_ep.ge.gauser.first_name + ')'
                ps_nueva.departamento = None
                ps_nueva.tipo = 'BOR'
                ps_nueva.save()
                # DocProgSec.objects.create(psec=ps_nueva, gep=g_ep, permiso='X')
                DocProgSec.objects.create(psec=ps_nueva, gep=doc_progsec, permiso='X')
                for ceps in ps.ceprogsec_set.all():
                    ceps_nueva = CEProgSec.objects.create(psec=ps_nueva, ce=ceps.ce, valor=ceps.valor)
                    for cevps in ceps.cevprogsec_set.all():
                        CEvProgSec.objects.create(cepsec=ceps_nueva, cev=cevps.cev, valor=cevps.valor)
                for lr in ps.librorecurso_set.all():
                    lr.pk = None
                    lr.psec = ps_nueva
                    lr.save()
                for actex in ps.actexcom_set.all():
                    actex.pk = None
                    actex.psec = ps_nueva
                    actex.save()
                for sb in ps.saberbas_set.all():
                    sb_nuevo = SaberBas.objects.get(id=sb.id)
                    sb_nuevo.pk = None
                    sb_nuevo.psec = ps_nueva
                    sb_nuevo.save()
                    for actex in sb.actexcoms.all():
                        sb_nuevo.actexcoms.add(*ps_nueva.actexcom_set.filter(nombre=actex.nombre))
                    for lr in sb.librorecursos.all():
                        sb_nuevo.actexcoms.add(*ps_nueva.librorecurso_set.filter(nombre=lr.nombre))
                    for sa in sb.sitapren_set.all():
                        sa_nueva = SitApren.objects.create(sbas=sb_nuevo, objetivo=sa.objetivo, nombre=sa.nombre,
                                                           contenidos_sbas=sa.contenidos_sbas)
                        for cep in sa.ceps.all():
                            sa_nueva.ceps.add(*ps_nueva.ceprogsec_set.filter(ce=cep.ce))
                        for asa in sa.actsitapren_set.all():
                            asa_nueva = ActSitApren.objects.get(id=asa.id)
                            asa_nueva.pk = None
                            asa_nueva.sapren = sa_nueva
                            asa_nueva.save()
                            for ieval in asa.instreval_set.all():
                                ieval_nuevo = InstrEval.objects.get(id=ieval.id)
                                ieval_nuevo.pk = None
                                ieval_nuevo.asapren = asa_nueva
                                ieval_nuevo.save()
                                for cieval in ieval.criinstreval_set.all():
                                    cevps = CEvProgSec.objects.get(cepsec__psec=ps_nueva, cev=cieval.cevps.cev)
                                    CriInstrEval.objects.create(ieval=ieval_nuevo, cevps=cevps, peso=cieval.peso)
                # html = render_to_string('progsec_accordion.html',
                #                         {'buscadas': False, 'progsecs': [ps_nueva], 'g_e': g_e, 'nueva': True})
                # return JsonResponse({'ok': True, 'html': html})
                return JsonResponse({'ok': True, 'msg': 'Programación enviada correctamente'})
            except Exception as msg:
                return JsonResponse({'msg': str(msg), 'ok': False})
        
        # Espe: Fin Enviar Copia de la programación
        elif action == 'update_texto':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    if '_clases' in request.POST['campo']:  # inicio_clases o fin_clases
                        texto = datetime.strptime(request.POST['texto'], '%Y-%m-%d')
                    else:
                        texto = request.POST['texto']
                    setattr(progsec, request.POST['campo'], texto)
                    if request.POST['campo'] == 'nombre' and not texto:
                        texto = '%s - %s' % (progsec.areamateria.get_curso_display(), progsec.areamateria.nombre)
                        progsec.nombre = texto
                    progsec.save()
                    return JsonResponse({'ok': True, 'progsec': progsec.id, 'html': texto})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        
        elif action == 'select_tipo':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                if progsec.tipo == request.POST['tipo']:
                    return JsonResponse({'ok': True, 'msg': 'No se cambia el tipo'})
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    if request.POST['tipo'] == 'DEF':
                        definitivas = ProgSec.objects.filter(tipo='DEF', pga=pga, areamateria=progsec.areamateria)
                        for d in definitivas:
                            if d.borrado:
                                d.tipo = 'BOR'
                                d.save()
                            else:
                                msg = '<p>Ya existe una programación "Definitiva" asociada a esta materia en su centro.</p>'
                                msg += '<p>Dicha programación es propiedad de %s.</p>' % d.gep.ge.gauser.get_full_name()
                                msg += '<p>Antes de hacer este cambio, esa programación debe marcarse como "Borrador" '
                                msg += 'o proceder a su borrado.</p>'
                                return JsonResponse(
                                    {'ok': False, 'msg': msg, 'tipo': progsec.tipo, 'progsec': progsec.id})
                    progsec.tipo = request.POST['tipo']
                    progsec.save()
                    if request.POST['grados_100'] == 'Y':
                        progsec.ceprogsec_set.filter(grado__lt=100).update(grado=100)
                    return JsonResponse({'ok': True, 'progsec': progsec.id})
                else:
                    msg = '<p>No tiene permiso para hacer el cambio solicitado.</p>'
                    return JsonResponse({'ok': False, 'msg': msg, 'tipo': progsec.tipo, 'progsec': progsec.id})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'select_departamento':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    departamento = Departamento.objects.get(id=request.POST['departamento'], ronda=g_e.ronda)
                    g_ep.departamento = departamento
                    g_ep.save()
                    progsec.departamento = departamento
                    progsec.save()
                    return JsonResponse({'ok': True, 'progsec': progsec.id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'select_jefe':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['jefe'])
                    try:
                        departamento = progsec.departamento
                        geps = departamento.gauser_extra_programaciones_set.all()
                    except:
                        geps = Gauser_extra_programaciones.objects.filter(ge__ronda=g_e.ronda)
                    for gep in geps.filter(jefe=True):
                        gep.jefe = False
                        try:
                            dps = DocProgSec.objects.get(gep=gep, psec=progsec)
                            if progsec.gep == gep:  # Si el jefe era el creador de la progsec se queda con permiso 'X'
                                dps.permiso = 'X'
                            else:
                                dps.permiso = 'L'
                            dps.save()
                        except:
                            pass
                        gep.save()
                    try:
                        nuevo_ge_jefe = geps.get(ge=ge)
                    except:
                        nuevo_ge_jefe, c = Gauser_extra_programaciones.objects.get_or_create(ge=ge)
                    nuevo_ge_jefe.departamento = departamento
                    nuevo_ge_jefe.jefe = True
                    nuevo_ge_jefe.save()
                    nuevo_gep_jefe, c = DocProgSec.objects.get_or_create(gep=nuevo_ge_jefe, psec=progsec)
                    nuevo_gep_jefe.permiso = 'X'
                    nuevo_gep_jefe.save()
                    return JsonResponse({'ok': True, 'progsec': progsec.id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'add_docprogsec':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    cdocentes = Cargo.objects.filter(entidad=g_e.ronda.entidad, clave_cargo='g_docente')
                    DocProgSec.objects.filter(psec=progsec, gep__jefe=False, gep__ge__cargos__in=cdocentes).delete()
                    ges = Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('ges[]'))
                    for ge in ges:
                        gep, c = Gauser_extra_programaciones.objects.get_or_create(ge=ge)
                        gep.departamento = progsec.departamento
                        gep.save()
                        dps, c = DocProgSec.objects.get_or_create(gep=gep, psec=progsec)
                        dps.permiso = 'X' if gep.jefe else 'E'
                        dps.save()
                    return JsonResponse({'ok': True, 'progsec': progsec.id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'alumno_destinatario':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['progsec'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    progsec.alumno = Gauser_extra.objects.get(id=request.POST['alumno'])
                    progsec.save()
                    return JsonResponse({'ok': True, 'progsec': progsec.id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_pesocep':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    cep = CEProgSec.objects.get(psec=progsec, id=request.POST['cep'])
                    valor = int(request.POST['cep_peso'])
                    if valor in [1, 2, 3, 4, 5]:
                        cep.valor = valor
                        cep.save()
                        return JsonResponse({'ok': True, 'progsec': progsec.id,
                                             'ceprogsec_porcentajes': progsec.ceprogsec_porcentajes})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'El peso solo puede tomar valores entre 1 y 5'})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'mod_grado_cep':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['progsec'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    cep = CEProgSec.objects.get(psec=progsec, id=request.POST['cep'])
                    valor = int(request.POST['valor'])
                    if valor in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]:
                        cep.grado = valor
                        cep.save()
                        return JsonResponse({'ok': True, 'progsec': progsec.id})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'Valor de grado de adquisición no permitido'})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_pesocevp':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    cevp = CEvProgSec.objects.get(cepsec__psec=progsec, id=request.POST['cevp'])
                    valor = int(request.POST['cevp_peso'])
                    if valor in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                        cevp.valor = valor
                        cevp.save()
                        html = render_to_string('progsec_accordion_content_cevalponderada.html', {'cep': cevp.cepsec})
                        return JsonResponse({'ok': True, 'progsec': progsec.id, 'html': html,
                                             'cevrogsec_porcentajes': cevp.cepsec.cevrogsec_porcentajes})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'El peso solo puede tomar valores entre 1 y 10'})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'cargar_libro':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    nombre = request.POST['nombre']
                    isbn = request.POST['isbn']
                    observaciones = request.POST['observaciones']
                    libro = LibroRecurso.objects.create(psec=progsec, nombre=nombre, isbn=isbn,
                                                        observaciones=observaciones)
                    html = render_to_string('progsec_accordion_content_libro.html', {'libro': libro})
                    return JsonResponse({'ok': True, 'progsec': progsec.id, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_libro':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    libro = LibroRecurso.objects.get(psec=progsec, id=request.POST['libro'])
                    libro_id = libro.id
                    libro.delete()
                    return JsonResponse({'ok': True, 'libro_id': libro_id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'cargar_actex':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    nombre = request.POST['nombre']
                    inicio = datetime.strptime(request.POST['inicio'], '%Y-%m-%d')
                    fin = datetime.strptime(request.POST['fin'], '%Y-%m-%d')
                    observaciones = request.POST['observaciones']
                    actex = ActExCom.objects.create(psec=progsec, nombre=nombre, inicio=inicio, fin=fin,
                                                    observaciones=observaciones)
                    html = render_to_string('progsec_accordion_content_actex.html', {'actex': actex})
                    return JsonResponse({'ok': True, 'progsec': progsec.id, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_actex':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    actex = ActExCom.objects.get(psec=progsec, id=request.POST['actex'])
                    actex_id = actex.id
                    actex.delete()
                    return JsonResponse({'ok': True, 'actex_id': actex_id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'add_saber':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    saber = SaberBas.objects.create(psec=progsec)
                    html = reordenar_saberes_comienzo(saber.psec)
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'mod_saber':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    html = None
                    saber = progsec.saberbas_set.get(id=request.POST['saber'], borrado=False)
                    campo = request.POST['campo']
                    if campo == 'nombre':
                        saber.nombre = request.POST['valor']
                        saber.save()
                    elif campo == 'comienzo':
                        comienzo = datetime.strptime(request.POST['valor'], '%Y-%m-%d')
                        saber.comienzo = comienzo
                        saber.save()
                        html = render_to_string('progsec_accordion_content_gantt.html', {'progsec': progsec})
                    else:
                        saber.periodos = int(request.POST['valor'])
                        saber.save()
                        html = render_to_string('progsec_accordion_content_gantt.html', {'progsec': progsec})
                    # if campo == 'orden':
                    #     html = reordenar_saberes(saber, valor)
                    # else:
                    #     setattr(saber, campo, valor)
                    #     saber.save()
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'ordenar_saberes':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['id'])
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    html = reordenar_saberes_comienzo(progsec)
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_saber':
            try:
                progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                              id=request.POST['progsec'], borrado=False)
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    saber = progsec.saberbas_set.get(id=request.POST['saber'])
                    if saber.es_borrable:
                        psec = saber.psec
                        saber.borrado = True
                        saber.save()
                        html = reordenar_saberes_comienzo(psec)
                        return JsonResponse({'ok': True, 'html': html})
                    else:
                        msg = 'Esta unidad de programación está siendo usada en uno o varios cuadernos docentes que ya contienen calificaciones.'
                        return JsonResponse({'ok': False, 'msg': msg})
                else:
                    msg = 'No tienes permiso para borrar esta programación didáctica.'
                    return JsonResponse({'ok': False, 'msg': msg, 'permiso': permiso})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'programaciones_borradas':
            try:
                progsec_ids = DocProgSec.objects.filter(gep=g_ep).values_list('psec__id', flat=True)
                progsecs = ProgSec.objects.filter(pga=pga, id__in=progsec_ids, borrado=True)
                html = render_to_string('progsec_accordion.html', {'progsecs': progsecs})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
    elif request.method == 'POST':
        if request.POST['action'] == 'pdf_progsec':
            dce = get_dce(g_e.ronda.entidad, 'Configuración de programaciones didácticas')
            progsec = ProgSec.objects.get(id=request.POST['id_progsec'])
            c = render_to_string('verprogramacion.html', {'progsec': progsec, 'pdf': True, 'dce': dce})
            genera_pdf(c, dce)
            nombre = slugify('%s_%s' % (progsec.areamateria.nombre, progsec.areamateria.get_curso_display()))
            return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename=nombre + '.pdf',
                                content_type='application/pdf')

            # p_dfkit.from_string(c, dce.url_pdf, dce.get_opciones)
            # fich = open(dce.url_pdf, 'rb')
            # response = HttpResponse(fich, content_type='application/pdf')
            # nombre = progsec.areamateria.nombre + '_' + progsec.areamateria.get_curso_display()
            # response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(nombre)
            # return response
        elif request.POST['action'] == 'download_file':
            try:
                pecdoc = PECdocumento.objects.get(id=request.POST['archivo'], pec__id=request.POST['pec'],
                                                  pec__entidad=g_e.ronda.entidad)
                response = HttpResponse(pecdoc.doc_file, content_type=pecdoc.content_type)
                response['Content-Disposition'] = 'attachment; filename=%s' % pecdoc.filename
                return response
            except:
                pass

    try:
        prog = int(request.GET['prog'])
    except:
        prog = False
    return render(request, "progsec.html",
                  {
                      'formname': 'progsec',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Programación',
                            'title': 'Crear una nueva programación de una materia de secundaria',
                            'permiso': 'libre'},
                           {'tipo': 'button', 'nombre': 'link', 'texto': 'Enlace web',
                            'title': 'Obtener el código a escribir en la página web del centro para ver programaciones',
                            'permiso': 'libre'},
                           {'tipo': 'button', 'nombre': 'search', 'texto': 'Buscar',
                            'title': 'Buscar programación a través del nombre de la materia de secundaria',
                            'permiso': 'libre'},
                           {'tipo': 'button', 'nombre': 'times-rectangle', 'texto': 'Programaciones borradas',
                            'title': 'Mostrar programaciones borradas y restaurar alguna de ellas',
                            'permiso': 'libre'},
                           # {'tipo': 'button', 'nombre': 'file-text', 'texto': 'Programaciones otros cursos',
                           #  'title': 'Mostrar programaciones de otros curso',
                           #  'permiso': 'libre'},
                           ),
                      'g_e': g_e,
                      'g_ep': g_ep,
                      'prog': prog,
                      'progsecs': progsecs,
                      'cursos': AreaMateria.CURSOS_LOMLOE,
                      'areasmateria': AreaMateria.objects.all(),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)
                  })


# except Exception as msg:
#     return HttpResponse(str(msg))


def verprogramacion(request, secret, id):
    try:
        entidad = Entidad.objects.get(secret=secret)
        progsec = ProgSec.objects.get(id=id, pga__ronda__entidad=entidad)
        if 'pdf' in request.GET:
            doc_progsec = 'Configuración de programaciones didácticas'
            dce = get_dce(entidad, doc_progsec)
            c = render_to_string('verprogramacion.html', {'progsec': progsec, 'pdf': True, 'dce': dce})
            genera_pdf(c, dce)
            nombre = slugify('%s_%s' % (progsec.areamateria.nombre, progsec.areamateria.get_curso_display()))
            return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename=nombre + '.pdf',
                                content_type='application/pdf')
            # p_dfkit.from_string(c, dce.url_pdf, dce.get_opciones)
            # fich = open(dce.url_pdf, 'rb')
            # response = HttpResponse(fich, content_type='application/pdf')
            # nombre = progsec.areamateria.nombre + '_' + progsec.areamateria.get_curso_display()
            # response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(nombre)
            # return response

        return render(request, "verprogramacion.html",
                      {
                          'formname': 'verprogramacion',
                          'progsec': progsec,
                          'tipos_procedimientos': InstrEval.TIPOS,
                      })
    except:
        pass


def verprogramaciones(request, secret):
    try:
        entidad = Entidad.objects.get(secret=secret)
        pga = PGA.objects.get(ronda=entidad.ronda)
        progsecs = ProgSec.objects.filter(pga=pga, tipo__in=('DEF', 'BIN', 'BNO', 'BDI', 'EOI')).order_by(
            'areamateria__curso')
        return render(request, "verprogramaciones.html",
                      {
                          'formname': 'verprogramaciones',
                          'progsecs': progsecs,
                          'entidad': entidad,
                      })
    except:
        return HttpResponse('<h1>Se ha producido un error. Petición no llevada a cabo.</h1>')


# @permiso_required('acceso_progsecundaria')
def progsecundaria_sb(request, id):
    g_e = request.session['gauser_extra']
    g_ep, c = Gauser_extra_programaciones.objects.get_or_create(ge=g_e)
    pga = PGA.objects.get(ronda=g_e.ronda)
    sb = SaberBas.objects.get(psec__pga=pga, id=id)
    permiso = sb.psec.get_permiso(g_ep)
    if not ('L' in permiso or 'E' in permiso or 'X' in permiso):
        return HttpResponse('Sin permiso')

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'crea_sap':
            try:
                sap = SitApren.objects.create(sbas=sb)
                act = ActSitApren.objects.create(sapren=sap, nombre='Nombre de la actividad')
                InstrEval.objects.create(asapren=act, tipo='TMONO', nombre='Procedimiento 1')
                html = render_to_string('progsec_sap_accordion.html', {'sap': sap})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                # sap = SitApren.objects.create(sbas=sb)
                # html = render_to_string('progsec_sap_accordion.html', {'sap': sap})
                return JsonResponse({'ok': False, 'msg': str(msg)})
                # return JsonResponse({'ok': True, 'html': html})
        elif action == 'exportar_sap':
            try:  ## Comentarios
                ## Se obtiene el objeto SitAprend
                sapren = SitApren.objects.get(id=request.POST['id'])
                ## Se obtienen las actividades de aprendizaje asociadas
                actsapren_all = ActSitApren.objects.filter(sapren=sapren, borrado=False)
                ## Se obtiene el objeto SaberBas
                saberbas = SaberBas.objects.get(id=sapren.sbas.id)
                ## Se obtiene el objeto ProgSec
                progsec = ProgSec.objects.get(id=saberbas.psec.id)
                ## Se obtiene un objeto AreaMateria
                areamateria = AreaMateria.objects.get(id=progsec.areamateria.id)
                ## Se crea un repositorio de situación de aprendizaje con el area materia
                ## de la situación de aprendizaje de la que se exporta.
                sap = RepoSitApren.objects.create(autor=g_e, areamateria=areamateria, nombre=sapren.nombre,
                                                  contenidos_sbas=sapren.contenidos_sbas, objetivo=sapren.objetivo)
                ## Se obtienen las competencias especificas de la situación de aprendizaje
                for cep in sapren.ceps.all():
                    sap.ces.add(cep.ce)  # Se agregan las competencias al repo de la situacion de aprendizaje
                for asa in actsapren_all:  # Se recorren las actividades de aprendizaje
                    act = RepoActSitApren.objects.create(sapren=sap, nombre=asa.nombre, description=asa.description)
                    ## Se obtienen los intrumentos de evaluación, que son objetos InstrEval, de una actividad de aprendizaje
                    instreval_all = InstrEval.objects.filter(asapren=asa, borrado=False)
                    for ie in instreval_all:  # se recorren los instrumentos de evaluacion
                        repoIEval = RepoInstrEval.objects.create(asapren=act, tipo=ie.tipo, nombre=ie.nombre)
                        criinstreval_all = CriInstrEval.objects.filter(
                            ieval=ie, borrado=False)  # se obtienen los criterios de evaluacion
                        for criinstreval in criinstreval_all:
                            # Este condicional es para no crear más de un RepoCEv asociado a una sap y un cev
                            # por que si no el refrescon en la vista de la interfaz da un error
                            repocev_all = RepoCEv.objects.filter(sapren=sap, cev=criinstreval.cevps.cev)
                            if repocev_all.count() == 0:
                                repocev = RepoCEv.objects.create(sapren=sap, cev=criinstreval.cevps.cev,
                                                                 valor=criinstreval.peso,
                                                                 modificado=criinstreval.modificado)
                                RepoCriInstrEval.objects.create(ieval=repoIEval, cevps=repocev, peso=criinstreval.peso,
                                                                modificado=criinstreval.modificado)
                            else:
                                repocev = repocev_all[0]
                                RepoCriInstrEval.objects.create(ieval=repoIEval, cevps=repocev, peso=criinstreval.peso,
                                                                modificado=criinstreval.modificado)
                if sapren.sbas.psec.docprogsec_set.get(gep=g_ep).permiso == 'X':
                    return JsonResponse({'ok': True})
                else:
                    msg = 'No tienes permiso para borrar esta situación de aprendizaje.'
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_sap':
            try:
                sapren = SitApren.objects.get(id=request.POST['id'])
                progsec = sapren.sbas.psec
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    if sapren.es_borrable:
                        sapren.borrado = True
                        sapren.save()
                        return JsonResponse({'ok': True})
                    else:
                        msg = 'Esta situación de aprendizaje ha sido evaluada en uno o varios cuadernos docentes que ya contienen calificaciones.'
                        return JsonResponse({'ok': False, 'msg': msg})
                else:
                    msg = 'No tienes permiso para borrar esta situación de aprendizaje.'
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        # Espe: Copiar (duplicar) SAP
        elif action == 'copiar_sap':
            try:
                # codigo copiar_sap
                # obtenemos la unidad de programacion (saber basico) a la que pertenece
                sb = SaberBas.objects.get(id=request.POST['sb'])
                # obtenemos la programacion a la que pertenece
                # psec = ProgSec.objects.get(id=sb.psec.id)
                # obtenemos la situación de aprendizaje a duplicar
                sap = SitApren.objects.get(id=request.POST['sap'], sbas=sb)
                sap_nueva = SitApren.objects.get(id=sap.id)
                # se borra clave primaria y se modifica nombre sap
                sap_nueva.pk = None
                sap_nueva.nombre = '%s (Copia)' % sap.nombre
                sap_nueva.save()
                # se copian las competencias especificas de la sap
                # relation: many to many
                # for cep in sap.ceps.all():
                #    sap_nueva.ceps.add(cep.ce)
                sap_nueva.ceps.add(*sap.ceps.all())
                # obtenemos las actividades
                for act in sap.actsitapren_set.all():
                    act_nueva = ActSitApren.objects.get(id=act.id)
                    act_nueva.pk = None
                    act_nueva.sapren = sap_nueva
                    act_nueva.save()
                    for instev in act.instreval_set.all():
                        instev_nuevo = InstrEval.objects.get(id=instev.id)
                        instev_nuevo.pk = None
                        instev_nuevo.asapren = act_nueva
                        instev_nuevo.save()
                        for criinstev in instev.criinstreval_set.all():
                            criinstev_nuevo = CriInstrEval.objects.get(id=criinstev.id)
                            criinstev_nuevo.pk = None
                            criinstev_nuevo.ieval = instev_nuevo
                            criinstev_nuevo.save()
                html = render_to_string('progsec_sap_accordion.html', {'sap': sap_nueva})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        # Espe: Fin
        elif action == 'open_accordion':
            try:
                sap = SitApren.objects.get(sbas__psec__gep__ge__ronda__entidad=g_e.ronda.entidad,
                                           id=request.POST['id'])
                html = render_to_string('progsec_sap_accordion_content.html', {'sap': sap, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'busca_saps':
            try:
                am = AreaMateria.objects.get(id=request.POST['am_sap'])
                texto = request.POST['texto']
                q1 = Q(areamateria=am, borrada=False, autor__gauser=g_e.gauser)
                q2 = Q(autor__gauser__first_name__icontains=texto) | Q(autor__gauser__last_name__icontains=texto) | Q(
                    nombre__icontains=texto) | Q(objetivo__icontains=texto)
                if request.POST['tipo'] == 'ASAP':
                    q1 = q1 | Q(areamateria=am, borrada=False, publicar=True)
                reposaps = RepoSitApren.objects.filter(q1, q2).distinct()
                html = render_to_string('progsec_sap_buscada_accordion.html', {'reposaps': reposaps})
                return JsonResponse({'ok': True, 'html': html, 'am': am.id})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'open_repoaccordion':
            try:
                sap = RepoSitApren.objects.get(id=request.POST['id'])
                html = render_to_string('progsec_sap_buscada_accordion_content.html', {'sap': sap, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'importar_reposap':
            try:
                reposap = RepoSitApren.objects.get(id=request.POST['reposap'])
                sbas = SaberBas.objects.get(id=request.POST['sb'])
                if sbas.psec.areamateria == reposap.areamateria:
                    ceps = CEProgSec.objects.filter(psec=sbas.psec, ce__in=reposap.ces.all())
                    sap = SitApren.objects.create(sbas=sbas, nombre=reposap.nombre, objetivo=reposap.objetivo,
                                                  contenidos_sbas=reposap.contenidos_sbas)
                    sap.ceps.add(*ceps)
                    for repoact in reposap.repoactsitapren_set.all():
                        asapren = ActSitApren.objects.create(sapren=sap, nombre=repoact.nombre,
                                                             description=repoact.description, producto=repoact.producto)
                        for repoieval in repoact.repoinstreval_set.all():
                            ieval = InstrEval.objects.create(asapren=asapren, tipo=repoieval.tipo,
                                                             nombre=repoieval.nombre)
                            for repocrieval in repoieval.repocriinstreval_set.all():
                                cevps = CEvProgSec.objects.get(cepsec__psec=sbas.psec, cev=repocrieval.cevps.cev)
                                CriInstrEval.objects.create(ieval=ieval, cevps=cevps, peso=repocrieval.peso)
                    html = render_to_string('progsec_sap_accordion.html', {'sap': sap})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'Asignaturas de SAP y programación no coinciden.'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_texto':
            try:
                clase = eval(request.POST['clase'])
                objeto = clase.objects.get(id=request.POST['id'])
                setattr(objeto, request.POST['campo'], request.POST['texto'])
                objeto.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_select':
            try:
                clase = eval(request.POST['clase'])
                objeto = clase.objects.get(id=request.POST['id'])
                if clase == CriInstrEval and request.POST['campo'] == 'peso' and int(request.POST['valor']) == 0:
                    if objeto.es_borrable:
                        setattr(objeto, request.POST['campo'], request.POST['valor'])
                        objeto.save()
                        return JsonResponse({'ok': True})
                    else:
                        msg = 'Este criterio de evaluación ha sido calificado en uno o más cuadernos docentes.'
                        return JsonResponse({'ok': False, 'msg': msg, 'mensaje': True})
                else:
                    setattr(objeto, request.POST['campo'], request.POST['valor'])
                    objeto.save()
                    return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_many2many':
            try:
                clase = eval(request.POST['clase'])
                clasem2m = eval(request.POST['clasem2m'])
                objeto = clase.objects.get(id=request.POST['id'])
                objetom2m = clasem2m.objects.get(id=request.POST['idm2m'])
                manytomany = getattr(objeto, request.POST['campo'])
                if request.POST['checked'] == 'true':
                    manytomany.add(objetom2m)
                    return JsonResponse({'ok': True})
                else:
                    if clase == SitApren and request.POST['campo'] == 'ceps':
                        if objeto.ceps_es_borrable(objetom2m):
                            manytomany.remove(objetom2m)
                            return JsonResponse({'ok': True})
                        else:
                            msg = 'Esta competencia específica tiene criterios de evaluación calificados en uno o más cuadernos docentes.'
                            return JsonResponse({'ok': False, 'msg': msg, 'mensaje': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'add_sap_actividad':
            try:
                sap = sb.sitapren_set.get(id=request.POST['sap'])
                act = ActSitApren.objects.create(sapren=sap, nombre='Nombre de la actividad')
                InstrEval.objects.create(asapren=act, tipo='TMONO', nombre='Procedimiento 1')
                html = render_to_string('progsec_sap_accordion_content_act.html', {'actividad': act})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_sap_actividad':
            try:
                asapren = ActSitApren.objects.get(id=request.POST['id'])
                progsec = asapren.sapren.sbas.psec
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    if asapren.es_borrable:
                        asapren.borrado = True
                        asapren.save()
                        return JsonResponse({'ok': True})
                    else:
                        msg = 'Esta actividad ha sido evaluada en uno o varios cuadernos docentes que ya contienen calificaciones.'
                        return JsonResponse({'ok': False, 'msg': msg})
                else:
                    msg = 'No tienes permiso para borrar esta actividad.'
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'add_act_instrumento':
            try:
                act = ActSitApren.objects.get(id=request.POST['act'])
                if act.sapren.sbas == sb:
                    inst = InstrEval.objects.create(asapren=act, nombre='Procedimiento', tipo='TMONO')
                    html = render_to_string('progsec_sap_accordion_content_act_proc.html', {'instrumento': inst})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    JsonResponse({'ok': False, 'msg': 'Error en la relación sb-instrumento'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_act_instrumento':
            try:
                ieval = InstrEval.objects.get(id=request.POST['id'])
                progsec = ieval.asapren.sapren.sbas.psec
                permiso = progsec.get_permiso(g_ep)
                if 'E' in permiso or 'X' in permiso:
                    if ieval.es_borrable:
                        ieval.borrado = True
                        ieval.save()
                        return JsonResponse({'ok': True})
                    else:
                        msg = 'Este procedimiento de evaluación ya contiene calificaciones en uno o varios cuadernos docentes.'
                        return JsonResponse({'ok': False, 'msg': msg})
                else:
                    msg = 'No tienes permiso para borrar este procedimiento de evaluación.'
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'table_criteval':
            try:
                inst = InstrEval.objects.get(id=request.POST['id'])
                if inst.asapren.sapren.sbas == sb:
                    criinstrevals = []
                    for cep in inst.asapren.sapren.ceps.all():
                        for cevps in cep.cevprogsec_set.all():
                            criinstreval, c = CriInstrEval.objects.get_or_create(ieval=inst, cevps=cevps)
                            criinstrevals.append(criinstreval.id)
                    for cr in inst.criinstreval_set.all():
                        if cr.id not in criinstrevals:
                            cr.delete()
                    html = render_to_string('progsec_sap_accordion_content_act_proc_crits.html', {'instrumento': inst})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

    # elif request.method == 'POST':
    #     if request.POST['action'] == 'sube_file_pec':
    #         pec = PEC.objects.get(id=request.POST['pec'])
    #         n_files = int(request.POST['n_files'])
    #         mensaje = False
    #         p = {'doc_nombre': False}
    #         if g_e.has_permiso('carga_programaciones'):
    #             for i in range(n_files):
    #                 fichero = request.FILES['fichero_xhr' + str(i)]
    #                 try:
    #                     p = PECdocumento.objects.get(pec=pec, tipo=request.POST['name'])
    #                     if p.doc_file:
    #                         os.remove(p.doc_file.path)
    #                     p.doc_file = fichero
    #                     p.doc_nombre = slugify(p.get_tipo_display())
    #                     p.content_type = fichero.content_type
    #                     p.save()
    #                 except:
    #                     p = PECdocumento.objects.create(pec=pec, doc_nombre=request.POST['name'], doc_file=fichero,
    #                                                     content_type=fichero.content_type, tipo=request.POST['name'])
    #                     p.doc_nombre = slugify(p.get_tipo_display())
    #                     p.save()
    #             return JsonResponse({'ok': True, 'mensaje': mensaje})
    #         else:
    #             mensaje = 'No tienes permiso para cargar archivos del PEC.'
    #             return JsonResponse({'ok': False, 'mensaje': mensaje})
    #     elif request.POST['action'] == 'download_file':
    #         try:
    #             pecdoc = PECdocumento.objects.get(id=request.POST['archivo'], pec__id=request.POST['pec'],
    #                                               pec__entidad=g_e.ronda.entidad)
    #             response = HttpResponse(pecdoc.doc_file, content_type=pecdoc.content_type)
    #             response['Content-Disposition'] = 'attachment; filename=%s' % pecdoc.filename
    #             return response
    #         except:
    #             pass
    return render(request, "progsec_sap.html",
                  {
                      'formname': 'progsec_sap',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'sign-in', 'texto': 'Importar SAP', 'permiso': 'libre',
                            'title': 'Importar una situación de aprendizaje del repositorio'},
                           {'tipo': 'button', 'nombre': 'plus', 'texto': 'Crear SAP', 'permiso': 'libre',
                            'title': 'Crear una nueva situación de aprendizaje para este saber básico'},
                           {'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Volver', 'permiso': 'libre',
                            'title': 'Volver a la programación didáctica'},
                           ),
                      'g_e': g_e,
                      'sb': sb,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


# @permiso_required('acceso_estadistica_programaciones')
def estadistica_prog(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'estadistica_entidad' and request.is_ajax():
            try:
                entidad = Entidad.objects.get(id=request.POST['entidad'])
                dep_ids = ProgSec.objects.filter(pga__ronda=entidad.ronda).values_list('departamento__id', flat=True)
                departamentos = Departamento.objects.filter(id__in=dep_ids)
                html = render_to_string('estadistica_prog_tabla.html', {'objeto': entidad,
                                                                        'departamentos': departamentos})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'genera_pdf':
            doc_progsec_estadistica = 'Configuración de estadística para las programaciones'
            dce = get_dce(g_e.ronda.entidad, doc_progsec_estadistica)
            tablas = request.POST['textarea_listado_estadistica']
            c = render_to_string('estadistica_prog_html2pdf.html', {'tablas': tablas, 'dce': dce})
            genera_pdf(c, dce)
            nombre = slugify('Informe_estadística')
            return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename=nombre + '.pdf',
                                content_type='application/pdf')
            # p_dfkit.from_string(c, dce.url_pdf, dce.get_opciones)
            # fich = open(dce.url_pdf, 'rb')
            # response = HttpResponse(fich, content_type='application/pdf')
            # nombre = 'Informe_estadística'
            # response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(nombre)
            # return response

    return render(request, "estadistica_prog.html",
                  {
                      'formname': 'estadistica_prog',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF', 'permiso': 'libre',
                            'title': 'Generar PDF a partir de la información mostrada en pantalla'},
                           ),
                      'departamentos': None,
                      'entidades': Entidad.objects.filter(entidadextra__isnull=False),
                      'g_e': g_e,
                      'objeto': g_e.ronda.entidad.organization,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


# @permiso_required('acceso_repositorio_sap')
def repositorio_sap(request):
    g_e = request.session['gauser_extra']
    g_ep, c = Gauser_extra_programaciones.objects.get_or_create(ge=g_e)

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'crea_sap':
            try:
                sap = RepoSitApren.objects.create(autor=g_e)
                act = RepoActSitApren.objects.create(sapren=sap, nombre='Nombre de la actividad')
                RepoInstrEval.objects.create(asapren=act, tipo='TMONO', nombre='Procedimiento 1')
                html = render_to_string('repositorio_sap_accordion.html', {'sap': sap})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_sap':
            try:
                sapren = RepoSitApren.objects.get(id=request.POST['id'])
                if sapren.autor.gauser == g_e.gauser:
                    sapren.delete()
                    return JsonResponse({'ok': True})
                else:
                    msg = 'No tienes permiso para borrar esta situación de aprendizaje.'
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'open_accordion':
            try:
                sap = RepoSitApren.objects.get(id=request.POST['id'])
                try:
                    like = sap.repositaprenlike_set.get(ge__gauser=g_e.gauser).like
                except:
                    like = 0
                html = render_to_string('repositorio_sap_accordion_content.html', {'sap': sap, 'g_e': g_e, 'like': like,
                                                                                   'areamaterias': AreaMateria.objects.all()})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'click_star':
            try:
                rsap = RepoSitApren.objects.get(id=request.POST['sap'])
                rsaplike, c = RepoSitAprenLike.objects.get_or_create(rsap=rsap, ge=g_e)
                like = int(request.POST['valor'])
                rsaplike.like = like
                rsaplike.save()
                html = render_to_string('repositorio_sap_accordion_content_stars.html',
                                        {'sap': rsap, 'g_e': g_e, 'like': like})
                return JsonResponse({'ok': True, 'html': html, 'val_global': rsap.val_global})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'vincula_areamateria_sap':
            try:
                sap = RepoSitApren.objects.get(id=request.POST['sap'])
                am = AreaMateria.objects.get(id=request.POST['am'])
                if sap.autor.gauser == g_e.gauser:
                    sap.areamateria = am
                    sap.save()
                    html = render_to_string('repositorio_sap_accordion_content.html', {'sap': sap, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'Solo el autor puede elegir la asignatura'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_texto':
            try:
                clase = eval(request.POST['clase'])
                objeto = clase.objects.get(id=request.POST['id'])
                setattr(objeto, request.POST['campo'], request.POST['texto'])
                objeto.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_select':
            try:
                clase = eval(request.POST['clase'])
                objeto = clase.objects.get(id=request.POST['id'])
                setattr(objeto, request.POST['campo'], request.POST['valor'])
                objeto.save()
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_many2many':
            try:
                clase = eval(request.POST['clase'])
                clasem2m = eval(request.POST['clasem2m'])
                objeto = clase.objects.get(id=request.POST['id'])
                objetom2m = clasem2m.objects.get(id=request.POST['idm2m'])
                manytomany = getattr(objeto, request.POST['campo'])
                if request.POST['checked'] == 'true':
                    manytomany.add(objetom2m)
                else:
                    manytomany.remove(objetom2m)
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'add_sap_actividad':
            try:
                sap = RepoSitApren.objects.get(id=request.POST['sap'], autor__gauser=g_e.gauser)
                act = RepoActSitApren.objects.create(sapren=sap, nombre='Nombre de la actividad')
                RepoInstrEval.objects.create(asapren=act, tipo='TMONO', nombre='Procedimiento 1')
                html = render_to_string('repositorio_sap_accordion_content_act.html', {'actividad': act})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_sap_actividad':
            try:
                act = RepoActSitApren.objects.get(id=request.POST['id'])
                if act.sapren.actsitapren_set.all().count() > 1 and act.sapren.autor.gauser == g_e.gauser:
                    act.delete()
                    return JsonResponse({'ok': True})
                else:
                    msg = 'No es posible borrar. Al menos, debe existir una actividad y ser el autor de la SAP.'
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'add_act_instrumento':
            try:
                act = RepoActSitApren.objects.get(id=request.POST['act'])
                if act.sapren.autor.gauser == g_e.gauser:
                    inst = RepoInstrEval.objects.create(asapren=act, nombre='Procedimiento', tipo='TMONO')
                    html = render_to_string('repositorio_sap_accordion_content_act_proc.html', {'instrumento': inst})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    JsonResponse({'ok': False, 'msg': 'Error en la relación sb-instrumento'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_act_instrumento':
            try:
                inst = RepoInstrEval.objects.get(id=request.POST['id'])
                if inst.asapren.instreval_set.all().count() > 1 and inst.asapren.sapren.autor.gauser == g_e.gauser:
                    inst.delete()
                    return JsonResponse({'ok': True})
                else:
                    msg = 'No es posible borrar. Al menos, debe existir un procedimiento de evaluación y ser autor.'
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'table_criteval':
            try:
                inst = RepoInstrEval.objects.get(id=request.POST['id'])
                sapren = inst.asapren.sapren
                if inst.asapren.sapren.autor.gauser == g_e.gauser:
                    rcev_ids = []
                    rcriinstrevals_ids = []
                    for ce in sapren.ces.all():
                        for cev in ce.criterioevaluacion_set.all():
                            rcev, c = RepoCEv.objects.get_or_create(sapren=sapren, cev=cev)
                            rcev_ids.append(rcev.id)
                    RepoCEv.objects.filter(sapren=sapren).exclude(id__in=rcev_ids).delete()

                    for cev in sapren.repocev_set.all():
                        rcriinstreval, c = RepoCriInstrEval.objects.get_or_create(ieval=inst, cevps=cev)
                        rcriinstrevals_ids.append(rcriinstreval.id)
                    RepoCriInstrEval.objects.filter(ieval=inst).exclude(id__in=rcriinstrevals_ids).delete()
                    html = render_to_string('repositorio_sap_accordion_content_act_proc_crits.html',
                                            {'instrumento': inst})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
    q1 = Q(borrada=False) & Q(publicar=True)
    q2 = Q(autor__gauser=g_e.gauser)
    sap_all = RepoSitApren.objects.filter(q1 | q2)
    RepoSitAprenLike.objects.all().delete()
    return render(request, "repositorio_sap.html",
                  {
                      'formname': 'repositorio_sap',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Crear SAP', 'permiso': 'libre',
                            'title': 'Crear una nueva situación de aprendizaje'},
                           {'tipo': 'button', 'nombre': 'search', 'texto': 'Filtrar', 'permiso': 'libre',
                            'title': 'Filtrar situaciones de aprendizaje'},
                           ),
                      'g_e': g_e,
                      'saps': sap_all,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })

# Index
# @permiso_required('acceso_cuaderno_docente')
def cuadernosdocentes(request):
    g_e = request.session['gauser_extra']
    g_ep, c = Gauser_extra_programaciones.objects.get_or_create(ge=g_e)

    if request.session.get('is_superuser'):
        cuadernos = CuadernoProf.objects.filter(ge=g_e, psec__borrado=False) | CuadernoProf.objects.filter(ge=g_e, psec=None)
    else:
        cuadernos = CuadernoProf.objects.filter(ge=g_e, borrado=False, psec__borrado=False) | CuadernoProf.objects.filter(ge=g_e, borrado=False, psec=None)
    # if request.method == 'POST':
    #     action = request.POST['action']
    #     if action == 'ver_progs_borradas' and g_e.has_permiso('ve_cuadernos_borrados_por_usuario'):
    #         try:
                
    #             return JsonResponse({'ok': True, 'html': html})
    #         except Exception as msg:
    #             return JsonResponse({'ok': False, 'msg': str(msg)})
    return render(request, "cuadernosdocentes.html",
        {
            'iconos':
                ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Crear Cuaderno', 'permiso': 'libre',
                  'title': 'Crear un nuevo cuaderno de profesor asociado a una programación'},
                 ),
            'g_e': g_e,
            # Mostramos todos los cuadernos no borrados que tengan psec no barrada o que no tengan psec(nuevos)
            'cuadernos': cuadernos ,
            'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
        })

# Get & Post
# @permiso_required('acceso_cuaderno_docente')
def cuadernodocente(request, id=None):
    g_e = request.session['gauser_extra']
    g_ep, c = Gauser_extra_programaciones.objects.get_or_create(ge=g_e)

    if request.method == 'GET':
        # Uso filter en vez de get para evitar el error si no existe el cuaderno
        cuaderno = CuadernoProf.objects.filter(ge__gauser=g_e.gauser, id=id).first()
        
        if not cuaderno:
            return redirect('/cuadernosdocentes/')

        docentes = profesorado(g_e.ronda.entidad)
        cuaderno.log += '%s %s %s\n' % ("Ver cuaderno "+str(id), now(), g_e)
        cuaderno.save()
        return render(request, "cuadernodocente.html",
            {
                'iconos':
                    ({'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Cuadernos docentes',
                        'title': 'Volver a la lista de cuadernos docentes', 'permiso': 'libre'},
                     ),
                'g_e': g_e,
                'cuaderno': cuaderno,
                'docentes': docentes,
            })

            
            
  

    # Borrar definitivamente cuadernos borrados por los docentes la ronda anterior
    # CuadernoProf.objects.filter(borrado=True, ge__ronda__fin__lt=g_e.ronda.inicio).delete()
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'crea_cuaderno':
            
            try:
                # Comprobamos si el usuario tiene programaciones asociadas.
                # Serán válidas tanto las de la entidad a la que pertenece, como de la entidad
                # de la que depende (por ejemplo una SIES de un IES).
                ies = g_e.ronda.entidad.entidadextra.depende_de
                if ies:
                    ge_ies = Gauser_extra.objects.get(gauser=g_e.gauser, ronda=ies.ronda)
                    q = Q(gep__ge=g_e) | Q(gep__ge=ge_ies)
                else:
                    q = Q(gep__ge=g_e)
                if DocProgSec.objects.filter(q).count() < 1:
                    msg = 'Primero tienes que participar como docente en alguna programación didáctica.'
                    return JsonResponse({'ok': False, 'msg': msg})
                log = '%s %s %s\n' % (action, now(), g_e)
                cuaderno = CuadernoProf.objects.create(ge=g_e, log=log)
                html = render_to_string('cuadernosdocentes_link.html', {'cuaderno': cuaderno})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
            
        # DEPRECATED    
        elif action == 'open_accordion':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['id'])
                # cievals = CriInstrEval.objects.filter(ieval__asapren__sapren__sbas__psec=cuaderno.psec)
                # for alumno in cuaderno.alumnos.all():
                #     for cieval in cievals:
                #         ecp, c = EscalaCP.objects.get_or_create(cp=cuaderno, ieval=cieval.ieval)
                #         CalAlum.objects.get_or_create(cp=cuaderno, alumno=alumno, cie=cieval, ecp=ecp)
                docentes = profesorado(g_e.ronda.entidad)
                html = render_to_string('cuadernodocente_accordion_content.html', {'cuaderno': cuaderno,
                                                                                   'docentes': docentes})
                cuaderno.log += '%s %s %s\n' % (action, now(), g_e)
                cuaderno.save()
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        # También sirve para recuperar cuadernos docentes. Realmente hace un toggle del campo cuaderno.borrado    
        elif action == 'borrar_cuadernoprof':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                
                # Si el cuaderno no tiene programación asignada, lo borramos directamente porque se acaba de crear.
                # De esta forma no guardamos cuadernos nuevos vacíos

                if cuaderno.psec_id == None:
                    cuaderno.delete()
                    return JsonResponse({'ok': True, 'redirect': "/cuadernosdocentes/"})
                
                # Si el cuaderno tiene programación asignada, simplemente cambiamos el estado a borrado
                if cuaderno.borrado:
                    cuaderno.borrado = False
                else:
                    cuaderno.borrado = True
                
                cuaderno.log += '%s %s %s\n' % (action, now(), g_e)
                cuaderno.save()
                
                return JsonResponse({'ok': True, 'cuaderno': cuaderno.id, 'redirect': "/cuadernosdocentes/"})
            except Exception as msg:
                return JsonResponse({'ok': False})
            
        elif action == 'copiar_cuadernoprof':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                cuaderno_copiado = clone_object(cuaderno)
                html = render_to_string('cuadernodocente_accordion.html', {'cuaderno': cuaderno_copiado})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'select_psec':
            try:
                psec = ProgSec.objects.get(id=request.POST['psec'], borrado=False)
                try:
                    ies = g_e.ronda.entidad.entidadextra.depende_de
                    if ies:
                        ge_ies = Gauser_extra.objects.get(gauser=g_e.gauser, ronda=ies.ronda)
                        DocProgSec.objects.get(gep__ge=ge_ies, psec=psec)
                    else:
                        DocProgSec.objects.get(gep__ge=g_e, psec=psec)
                    # grupos = psec.curso.grupos
                    grupos = Grupo.objects.filter(ronda=g_e.ronda)
                    html = render_to_string('cuadernodocente_accordion_content_grupos.html', {'grupos': grupos})
                    return JsonResponse({'ok': True, 'html': html})
                except Exception as msg:
                    return JsonResponse({'ok': False, 'msg': str(msg)})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
            
        elif action == 'configura_cuaderno':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                cuaderno.psec = ProgSec.objects.get(id=request.POST['psec'])
                cuaderno.grupo = Grupo.objects.get(id=request.POST['grupo'])
                cuaderno.tipo = request.POST['tipo']
                cuaderno.log += '%s %s %s | %s\n' % (action, now(), g_e, request.POST)
                cuaderno.save()
                cuaderno.alumnos.add(*cuaderno.grupo.gauser_extra_estudios_set.all().values_list('ge', flat=True))
                for alumno in cuaderno.alumnos.all():
                    for cep in cuaderno.psec.ceprogsec_set.all():
                        calalumce, c = CalAlumCE.objects.get_or_create(cp=cuaderno, alumno=alumno, cep=cep)
                        for cevp in cep.cevprogsec_set.all():
                            CalAlumCEv.objects.get_or_create(calalumce=calalumce, cevp=cevp)
                html = render_to_string('cuadernodocente_content.html', {'cuaderno': cuaderno})
                return JsonResponse({'ok': True, 'html': html, 'nombre': cuaderno.nombre, 'redirect': '/cuadernodocente/%s/'%(cuaderno.id)})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
            
        elif action == 'select_asignar_cuaderno':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                if g_e.has_permiso('asigna_cuadernos_profesor') or cuaderno.ge.gauser == g_e.gauser:
                    ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['docente'])
                    cuaderno.ge = ge
                    cuaderno.log += '%s %s %s | %s\n' % (action, now(), g_e, ge.gauser)
                    cuaderno.save()
                    return JsonResponse({'ok': True, 'redirect': '/cuadernosdocentes/' })
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        elif action == 'cuaderno_competencias':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                cuaderno.vista = request.POST['vista']
                cuaderno.log += '%s %s %s | %s\n' % (action, now(), g_e, request.POST['vista'])
                cuaderno.save()
            
                return JsonResponse({'ok': True, 'redirect': '/cuadernodocente/%s/'%(cuaderno.id)})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        elif action == 'define_ecp':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                ieval = InstrEval.objects.get(id=request.POST['ieval'], asapren__sapren__sbas__psec=cuaderno.psec)
                ecp, c = EscalaCP.objects.get_or_create(cp=cuaderno, ieval=ieval)
                if CalAlumValor.objects.filter(ca__cp=cuaderno, ecpv__valor__gt=0, ca__cie__ieval=ieval).count() == 0:
                    html = render_to_string('cuadernodocente_content_ecp.html', {'ecp': ecp})
                    cuaderno.log += '%s %s %s | %s\n' % (action, now(), g_e, request.POST)
                    cuaderno.save()
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False,
                                         'msg': 'Si existen calificaciones no se puede modificar el instrumento.'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        elif action == 'update_texto':
            try:
                clase = eval(request.POST['clase'])
                objeto = clase.objects.get(id=request.POST['id'])
        
                # Si es un esclaValor, para tipo ListaDeControl y no es la primera columna
                # Actulizamos los valores para todas las celdas de la columna
                if request.POST['clase']== "EscalaCPvalor" and objeto.ecp.tipo == "LCONT" and objeto.x > 0:
                    for obj in objeto.ecp.escalacpvalor_set.filter(x=objeto.x):
                        setattr(obj, request.POST['campo'], request.POST['texto'])
                        obj.save()
                else:
                    setattr(objeto, request.POST['campo'], request.POST['texto'])
                    objeto.save()

                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                cuaderno.log += '%s %s %s | %s\n' % (action, now(), g_e, request.POST)
                cuaderno.save()
            
                if request.POST['clase'] == "EscalaCPvalor":
                    rubrica = render_to_string('cuadernodocente_content_rubrica.html', {'ecp': objeto.ecp})
                    return JsonResponse({'ok': True, 'rubrica': rubrica, 'ieval_id': objeto.ecp.ieval.id  })

                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        elif action == 'update_select':
            try:
                clase = eval(request.POST['clase'])
                objeto = clase.objects.get(id=request.POST['id'])
                setattr(objeto, request.POST['campo'], request.POST['valor'])
                objeto.save()
                if request.POST['clase'] == 'EscalaCP' and request.POST['valor'] == 'ESVCL':
                    objeto.escalacpvalor_set.all().delete()
                    casillas = [{'x': 0, 'y': 0, 't': '', 'valor': 0},
                                {'x': 0, 'y': 1, 't': 'Aspecto 1', 'valor': 0},
                                {'x': 0, 'y': 2, 't': 'Aspecto 2', 'valor': 0},
                                {'x': 1, 'y': 0, 't': 'Grado 1', 'valor': 0},
                                {'x': 1, 'y': 1, 't': 'Criterio 11', 'valor': 0},
                                {'x': 1, 'y': 2, 't': 'Criterio 12', 'valor': 0},
                                {'x': 2, 'y': 0, 't': 'Grado 2', 'valor': 0},
                                {'x': 2, 'y': 1, 't': 'Criterio 21', 'valor': 0},
                                {'x': 2, 'y': 2, 't': 'Criterio 22', 'valor': 0},
                                {'x': 3, 'y': 0, 't': 'Grado 3', 'valor': 0},
                                {'x': 3, 'y': 1, 't': 'Criterio 31', 'valor': 0},
                                {'x': 3, 'y': 2, 't': 'Criterio 32', 'valor': 0}]
                    for c in casillas:
                        EscalaCPvalor.objects.create(ecp=objeto, x=c['x'], y=c['y'], valor=c['valor'],
                                                     texto_cualitativo=c['t'])
                elif request.POST['clase'] == 'EscalaCP' and request.POST['valor'] == 'LCONT':
                    objeto.escalacpvalor_set.all().delete()
                    casillas = [{'x': 0, 'y': 0, 't': '', 'valor': 0},
                                {'x': 0, 'y': 1, 't': 'Aspecto 1', 'valor': 0},
                                {'x': 0, 'y': 2, 't': 'Aspecto 2', 'valor': 0},
                                {'x': 1, 'y': 0, 't': 'Valoración 1', 'valor': 2},
                                {'x': 1, 'y': 1, 't': 'Valoración 1', 'valor': 2},
                                {'x': 1, 'y': 2, 't': 'Valoración 1', 'valor': 2},
                                {'x': 2, 'y': 0, 't': 'Valoración 2', 'valor': 5},
                                {'x': 2, 'y': 1, 't': 'Valoración 2', 'valor': 5},
                                {'x': 2, 'y': 2, 't': 'Valoración 2', 'valor': 5},
                                {'x': 3, 'y': 0, 't': 'Valoración 3', 'valor': 10},
                                {'x': 3, 'y': 1, 't': 'Valoración 3', 'valor': 10},
                                {'x': 3, 'y': 2, 't': 'Valoración 3', 'valor': 10}]
                    for c in casillas:
                        EscalaCPvalor.objects.create(ecp=objeto, x=c['x'], y=c['y'], valor=c['valor'],
                                                     texto_cualitativo=c['t'])
                elif request.POST['clase'] == 'EscalaCP' and request.POST['valor'] == 'ESVCN':
                    objeto.escalacpvalor_set.all().delete()
                    
                    # Quitamos la opción de los botones del 1 al 10
                    #casillas = [{'x': i, 'y': 0, 't': i + 1, 'valor': i + 1} for i in range(0, 10)]
                    #for c in casillas:
                    #    EscalaCPvalor.objects.create(ecp=objeto, x=c['x'], y=c['y'], valor=c['valor'],
                    #                                 texto_cualitativo=c['t'])
                        
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                cuaderno.log += '%s %s %s | %s\n' % (action, now(), g_e, request.POST)
                cuaderno.save()
                html = render_to_string('cuadernodocente_content_ecp.html', {'ecp': objeto})
                rubrica = render_to_string('cuadernodocente_content_rubrica.html', {'ecp': objeto})
                return JsonResponse({'ok': True, 'html': html, 'rubrica': rubrica, 'ecp_tipo': objeto.tipo, 'ecp_tipo_display': objeto.get_tipo_display()  })
                
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        elif action == 'add_row_ecp':
            try:
                ecp = EscalaCP.objects.get(id=request.POST['ecp'], cp__ge=g_e)
                nueva_row_index = max(ecp.get_ecpvys) + 1
                if ecp.tipo == 'LCONT':
                    columns_index = ecp.escalacpvalor_set.filter(y=0).values_list('x', 'valor')
                    for x, valor in columns_index:
                        EscalaCPvalor.objects.create(ecp=ecp, x=x, y=nueva_row_index,
                                                     texto_cualitativo='Nuevo aspecto', valor=valor)
                else:
                    columns_index = ecp.escalacpvalor_set.filter(y=0).values_list('x', flat=True)
                    for x in columns_index:
                        EscalaCPvalor.objects.create(ecp=ecp, x=x, y=nueva_row_index,
                                                     texto_cualitativo='Texto', valor=0)
                html = render_to_string('cuadernodocente_content_ecp.html', {'ecp': ecp})
                rubrica = render_to_string('cuadernodocente_content_rubrica.html', {'ecp': ecp})
                return JsonResponse({'ok': True, 'html': html, 'rubrica': rubrica, 'ieval_id': ecp.ieval.id  })
                #return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        elif action == 'add_column_ecp':
            try:
                ecp = EscalaCP.objects.get(id=request.POST['ecp'], cp__ge=g_e)
                rows_index = ecp.get_ecpvys
                nueva_column_index = max(ecp.escalacpvalor_set.filter(y=0).values_list('x', flat=True)) + 1
                for i in rows_index:
                    EscalaCPvalor.objects.get_or_create(ecp=ecp, y=i, x=nueva_column_index,
                                                        texto_cualitativo='Texto', valor=0)
                html = render_to_string('cuadernodocente_content_ecp.html', {'ecp': ecp})
                rubrica = render_to_string('cuadernodocente_content_rubrica.html', {'ecp': ecp})
                return JsonResponse({'ok': True, 'html': html, 'rubrica': rubrica, 'ieval_id': ecp.ieval.id  })
                #return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        elif action == 'del_rc_ecp':
            try:
                ecp = EscalaCP.objects.get(id=request.POST['ecp'], cp__ge=g_e)
                if request.POST['borrar'] == 'x':
                    ecp.escalacpvalor_set.filter(x=request.POST['i']).delete()
                else:
                    ecp.escalacpvalor_set.filter(y=request.POST['i']).delete()
                html = render_to_string('cuadernodocente_content_ecp.html', {'ecp': ecp})
                rubrica = render_to_string('cuadernodocente_content_rubrica.html', {'ecp': ecp})
                return JsonResponse({'ok': True, 'html': html, 'rubrica': rubrica, 'ieval_id': ecp.ieval.id  })
                #return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'enviar2repo':
            try:
                ecp = EscalaCP.objects.get(id=request.POST['ecp'], cp__ge=g_e)
                observaciones = ecp.cp.psec.areamateria.nombre + ' <br>' + ecp.cp.psec.areamateria.get_curso_display()
                ecp_nueva = RepoEscalaCP.objects.get_or_create(tipo=ecp.tipo, nombre=ecp.nombre, creador=g_e,
                                                               observaciones=observaciones)
                ecp_nueva[0].repoescalacpvalor_set.all().delete()
                for ecpv in ecp.escalacpvalor_set.all():
                    RepoEscalaCPvalor.objects.create(ecp=ecp_nueva[0], x=ecpv.x, y=ecpv.y, valor=ecpv.valor,
                                                     texto_cualitativo=ecpv.texto_cualitativo)
                return JsonResponse({'ok': True})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'repo2cuaderno':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                cuaderno.log += '%s %s %s | %s\n' % (action, now(), g_e, request.POST)
                cuaderno.save()
                recp = RepoEscalaCP.objects.get(identificador=request.POST['identificador'])
                ecp = EscalaCP.objects.get(id=request.POST['ecp'], cp=cuaderno)
                ecp.tipo = recp.tipo
                ecp.nombre = recp.nombre
                ecp.save()
                ecp.escalacpvalor_set.all().delete()
                for recpv in recp.repoescalacpvalor_set.all():
                    EscalaCPvalor.objects.create(ecp=ecp, x=recpv.x, y=recpv.y, valor=recpv.valor,
                                                 texto_cualitativo=recpv.texto_cualitativo)
                html = render_to_string('cuadernodocente_content_ecp.html', {'ecp': ecp})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_calalumce':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                calalumce = CalAlumCE.objects.get(id=request.POST['calalumce'], cp=cuaderno)
                calalumce.valor = max(min(10, float(request.POST['valor'])), 0)
                calalumce.save()
                alumno = calalumce.alumno
                asignatura = calalumce.cep.ce.asignatura
                cal_am = cuaderno.calificacion_alumno_asignatura(alumno, asignatura)
                return JsonResponse(
                    {'ok': True, 'cal_am': cal_am, 'asignatura': slugify(asignatura), 'alumno': alumno.id})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'update_calalumcev':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                calalumcev = CalAlumCEv.objects.get(id=request.POST['calalumcev'], calalumce__cp=cuaderno)
                calalumcev.valor = max(min(10, float(request.POST['valor'])), 0)
                calalumcev.save()
                calalumce = calalumcev.calalumce
                alumno = calalumce.alumno
                asignatura = calalumce.cep.ce.asignatura
                cal_am = cuaderno.calificacion_alumno_asignatura(alumno, asignatura)
                return JsonResponse({'ok': True, 'cal_am': cal_am, 'calalumce': calalumce.valor, 'alumno': alumno.id,
                                     'asignatura': slugify(asignatura), 'cep': calalumce.cep.id})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        # DEPRECATED. No guardamos la nota en dos pasos
        elif action == 'update_calalum':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                cieval = CriInstrEval.objects.get(id=request.POST['cieval'],
                                                  ieval__asapren__sapren__sbas__psec=cuaderno.psec)
                alumno = Gauser_extra.objects.get(id=request.POST['alumno'], ronda=g_e.ronda)
                ecp, c = EscalaCP.objects.get_or_create(cp=cuaderno, ieval=cieval.ieval)
                ca, c = CalAlum.objects.get_or_create(cp=cuaderno, alumno=alumno, cie=cieval, ecp=ecp)
                html = render_to_string('cuadernodocente_accordion_content_calalum.html', {'calalum': ca})
                return JsonResponse({'ok': True, 'html': html, 'calalum': ca.id, 'alumno': alumno.id, 'cal': ca.cal,
                                     'cieval': cieval.id})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        elif action == 'update_rubrica':
            try:
                
                ca = None # Inicializamos la variable para meter la calificación
                
                if request.POST['calalum']:
                    # ca = CalAlum.objects.get(id=request.POST['calalum']) => evitor tratar la excepción MyModel.DoesNotExists:
                    ca = CalAlum.objects.filter(id=request.POST['calalum']).first()
                   
                # Si no hay CalAlum, la creo partiendo del cuaderno, del alumno y del criterio
                if not ca: 
                    cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                    cieval = CriInstrEval.objects.get(id=request.POST['cieval'],
                                                  ieval__asapren__sapren__sbas__psec=cuaderno.psec)
                    alumno = Gauser_extra.objects.get(id=request.POST['alumno'], ronda=g_e.ronda)
                    ecp, c = EscalaCP.objects.get_or_create(cp=cuaderno, ieval=cieval.ieval)
                    ca, c = CalAlum.objects.get_or_create(cp=cuaderno, alumno=alumno, cie=cieval, ecp=ecp)

                
                # Guardamos observaciones si vienen
                if request.POST['obs']:
                    ca.obs = request.POST['obs']
                    ca.save()
                
                ecpv = EscalaCPvalor.objects.get(id=request.POST['ecpv'], ecp__cp__ge=g_e)  # Valor de la escala
                if ca.ecp.tipo == "LCONT":
                    # En las lista de control, cuando modificamos los valores de de la escala, se hace únicamente en las cabeceras
                    # Debemos por tanto recoger el valor de la cabecera correspondiente
                    # Nota: Se ha modificado update_texto para no tener que hacer esta asignació
                    # Ahora en update_texto se actualizan completamente los valores de la columna de la rúbrica al cambiar la cabecera
                    # Mantengo estas dos líneas porque si no, en rúbricas antiguas, no recogerían bien los valores
                    ecpv.valor = ecpv.ecp.escalacpvalor_set.get(y=0, x=ecpv.x).valor
                    ecpv.save()



                # Puntero de la nota particular al valor de la escala
                cav, c = CalAlumValor.objects.get_or_create(ca=ca, ecpv=ecpv)    

                # En función del tipo de rúbrica tenemos dos comportamientos
                if ca.ecp.tipo == "ESVCL":
                    
                    # Si hay creación seleccionamos, no hay creación, ya estaba el Valor => deseleccionamos
                    if c:
                        selected = True
                    else:
                        cav.delete()
                        selected = False
                        

                # Se comporta como un radio button
                elif ca.ecp.tipo == "LCONT":
                    # Si hay creación, hemos cambiado de valor dentro de la fila. Borramos el resto de la fila
                    if c:
                        ca.calalumvalor_set.filter(ecpv__y=ecpv.y).exclude(ecpv=ecpv).delete()
                        selected = True
                    else:
                        # No hacemos nada porque hemos pinchado en el seleccionado
                        selected = False

                # Lista de todos los valores de la rúbrica seleccionados
                queryset = ca.calalumvalor_set.all().values_list('ecpv', flat=True)
                ecpvs_selected = list(queryset)

                return JsonResponse({'ok': True, 'selected': selected, 'cal': ca.cal, 'ca_id': ca.id, 'ecpvs_selected': ecpvs_selected})

            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        
        
        # DEPRECATED
        elif action == 'update_lcont':
            try:
                ecpv = EscalaCPvalor.objects.get(id=request.POST['ecpv'], ecp__cp__ge=g_e)
                
                # A estas dos líneas no les veo sentido, porque estamos modificando la rúbrica general asociada al instrumento
                #ecpv.valor = ecpv.ecp.escalacpvalor_set.get(y=0, x=ecpv.x).valor
                #ecpv.save()
                
                
                ca = CalAlum.objects.get(id=request.POST['calalum'], ecp=ecpv.ecp)
                cav, c = CalAlumValor.objects.get_or_create(ca=ca, ecpv=ecpv)
                if c:
                    ca.calalumvalor_set.filter(ecpv__y=ecpv.y).exclude(ecpv=ecpv).delete()
                return JsonResponse({'ok': True, 'alumno': ca.alumno.id, 'cal': ca.cal})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
            
        elif action == 'update_esvcn':
            # Params: cuaderno, cieval, alumno, calcalum, ecpv, valor
            try:
                ca = None # Inicializamos la variable para meter la calificación
                
                if request.POST['calalum']:
                    # ca = CalAlum.objects.get(id=request.POST['calalum']) => evitor tratar la excepción MyModel.DoesNotExists:
                    ca = CalAlum.objects.filter(id=request.POST['calalum']).first()
                   
                # Si no hay CalAlum, la creo partiendo del cuaderno, del alumno y del criterio
                if not ca: 
                    cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                    cieval = CriInstrEval.objects.get(id=request.POST['cieval'],
                                                  ieval__asapren__sapren__sbas__psec=cuaderno.psec)
                    alumno = Gauser_extra.objects.get(id=request.POST['alumno'], ronda=g_e.ronda)
                    ecp, c = EscalaCP.objects.get_or_create(cp=cuaderno, ieval=cieval.ieval)
                    ca, c = CalAlum.objects.get_or_create(cp=cuaderno, alumno=alumno, cie=cieval, ecp=ecp)

                # Guardamos observaciones si vienen
                if request.POST['obs']:
                    ca.obs = request.POST['obs']
                    ca.save()
                
                # Borramos valores anteriores
                ca.calalumvalor_set.all().delete()          # Borramos CalALumValor's valores (solo tendría que tener 1)
                
                # Error de concepto!
                # ca.ecp.escalacpvalor_set.all().delete()     
                # Borramos EscalaCPValor's ya no mantenemos un listado con opciones del 1 al 10 
                # No puedo borrar esto. ¿Por qué? Cada vez que se mete una nota, se crea un valor asociado a la escala
                # Y el CalAlum apunta a ese valor por medio de CalAlumnValor
                # Si borro los escalacpvalor, el resto de CalalumValor pierden su nota
                

                # Cuando mantenía lista con opciones, los ordenaba 
                # for idx, e in enumerate(ca.ecp.escalacpvalor_set.all().order_by('valor')):
                    # print("entro")
                    # print(idx)
                    # e.y = idx
                    # e.save()

                # Metemos el valor
                valor = max(0, min(10, float(request.POST['valor'])))
                ecpv, c = EscalaCPvalor.objects.get_or_create(ecp=ca.ecp, ecp__cp__ge=g_e, valor=valor)                
                CalAlumValor.objects.create(ca=ca, ecpv=ecpv)

                return JsonResponse({'ok': True, 'cal': ca.cal, 'ca_id': ca.id})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
            
        elif action == 'delete_calalum_valores':
            try:
                ca = CalAlum.objects.get(id=request.POST['calalum'])
                cieval = ca.cie.id
                
                #ca.obs = "" # Quitamos también las observaciones
                #ca.calalumvalor_set.all().delete()
                ca.delete() 

                return JsonResponse({'ok': True, 'cieval': cieval })
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        

        elif action == 'update_obs':
            try:
                ca = None # Inicializamos la variable para meter la calificación

                if request.POST['calalum']:
                    # ca = CalAlum.objects.get(id=request.POST['calalum']) => evitor tratar la excepción MyModel.DoesNotExists:
                    ca = CalAlum.objects.filter(id=request.POST['calalum']).first()
                   
                # Si no hay CalAlum, la creo partiendo del cuaderno, del alumno y del criterio
                if not ca: 
                    cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                    cieval = CriInstrEval.objects.get(id=request.POST['cieval'],
                                                  ieval__asapren__sapren__sbas__psec=cuaderno.psec)
                    alumno = Gauser_extra.objects.get(id=request.POST['alumno'], ronda=g_e.ronda)
                    ecp, c = EscalaCP.objects.get_or_create(cp=cuaderno, ieval=cieval.ieval)
                    ca, c = CalAlum.objects.get_or_create(cp=cuaderno, alumno=alumno, cie=cieval, ecp=ecp)

                ca.obs = request.POST['obs']
                ca.save()
                #return JsonResponse({'ok': True, 'obs': ca.obs})
                return JsonResponse({'ok': True, 'cal': ca.cal, 'ca_id': ca.id})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
            

        elif action == 'gestionar_alumnos':
            try:
                cuaderno = CuadernoProf.objects.get(id=request.POST['cuaderno'], ge=g_e)
                html = render_to_string('cuadernodocente_content_ga.html', {'cuaderno': cuaderno})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'update_alumnos_cuaderno':
            try:
                cuaderno = CuadernoProf.objects.get(id=request.POST['cuaderno'], ge=g_e)
                alumno = Gauser_extra.objects.get(id=int(request.POST['alumno'][1:]), ronda=g_e.ronda)
                if alumno not in cuaderno.alumnos.all():
                    if cuaderno.tipo == 'PRO':
                        cievals = CriInstrEval.objects.filter(ieval__asapren__sapren__sbas__psec=cuaderno.psec,
                                                              borrado=False)
                        for cieval in cievals:
                            try:
                                ecp = EscalaCP.objects.get(cp=cuaderno, ieval=cieval.ieval)
                                CalAlum.objects.get_or_create(cp=cuaderno, alumno=alumno, cie=cieval, ecp=ecp)
                            except:
                                pass
                    for cep in cuaderno.psec.ceprogsec_set.all():
                        calalumce, c = CalAlumCE.objects.get_or_create(cp=cuaderno, alumno=alumno, cep=cep)
                        for cevp in cep.cevprogsec_set.all():
                            CalAlumCEv.objects.get_or_create(calalumce=calalumce, cevp=cevp)
                    html_span = render_to_string('cuadernodocente_content_ga_alumno.html',
                                                 {'cuaderno': cuaderno, 'alumno': alumno})
                else:
                    html_span = ''
                cuaderno.alumnos.add(alumno)
                return JsonResponse({'ok': True, 'cuaderno': cuaderno.id, 'html_span': html_span,
                                     'num_alumnos': cuaderno.alumnos.all().count()})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        
        
        elif action == 'borrar_alumno_cuaderno':
            try:
                cuaderno = CuadernoProf.objects.get(id=request.POST['cuaderno'], ge=g_e)
                alumno = Gauser_extra.objects.get(id=int(request.POST['alumno']), ronda=g_e.ronda)
                cuaderno.calalum_set.filter(alumno=alumno).delete()
                CalAlumCEv.objects.filter(calalumce__cp=cuaderno, calalumce__alumno=alumno).delete()
                cuaderno.calalumce_set.filter(alumno=alumno).delete()
                cuaderno.alumnos.remove(alumno)
                return JsonResponse({'ok': True, 'cuaderno': cuaderno.id, 'alumno': alumno.id,
                                     'num_alumnos': cuaderno.alumnos.all().count()})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
    

def carga_edrubrics(id):
    s = requests.Session()
    s.verify = False
    try:
        edrubrics = s.get('https://edrubrics.additioapp.com/item/view/%s' % id, timeout=5)
    except:
        return False, 'Error en la carga de la web'
    html_parseado = BeautifulSoup(edrubrics.content.decode(edrubrics.encoding), 'html.parser')
    nombre_rubrica = html_parseado.find('title').text
    if 'Not Found' in nombre_rubrica:
        return False, 'La rúbrica solicitada no existe.'
    observaciones = 'Edrubrics %s' % id
    recp, c = RepoEscalaCP.objects.get_or_create(tipo='ESVCL', nombre=nombre_rubrica, observaciones=observaciones)
    if c:
        max_length = RepoEscalaCPvalor._meta.get_field('texto_cualitativo').max_length
        RepoEscalaCPvalor.objects.create(ecp=recp, x=0, y=0, texto_cualitativo='')
        elementos_primera_columna = html_parseado.findAll('div', {'class': 'rows-column-style'})
        for n, elem in enumerate(elementos_primera_columna):
            texto_cualitativo = elem.text.strip()[:max_length]
            RepoEscalaCPvalor.objects.create(ecp=recp, x=0, y=n + 1, texto_cualitativo=texto_cualitativo)
        elementos_cabecera = html_parseado.findAll('div', {'class': 'title-columns-style'})
        valores_sin_normalizar = []
        for n, elem in enumerate(elementos_cabecera):
            tds = elem.findAll('td')
            texto_cualitativo = tds[0].text.strip()[:max_length]
            valor = float(tds[2].text.strip().replace(',', '.'))
            valores_sin_normalizar.append(valor)
            RepoEscalaCPvalor.objects.create(ecp=recp, x=n + 1, y=0, texto_cualitativo=texto_cualitativo)
        # Normalizar los valores a 10:
        escala = 10 / max(valores_sin_normalizar)
        valores = [round(v * escala, 2) for v in valores_sin_normalizar]
        column_values = html_parseado.findAll('ul')
        for x, cv in enumerate(column_values):
            for y, li in enumerate(cv.findAll('li')):
                texto_cualitativo = li.text.strip()[:max_length]
                RepoEscalaCPvalor.objects.create(ecp=recp, x=x + 1, y=y + 1, valor=valores[x],
                                                 texto_cualitativo=texto_cualitativo)
        return True, recp
    return False, 'La rúbrica ya existe en Gauss y no se vuelve a cargar.'


@permiso_required('acceso_repositorio_instrumento')
def repoescalacp(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'carga_edrubrics':
            try:
                carga_correcta, recp = carga_edrubrics(request.POST['id'])
                if not carga_correcta:
                    return JsonResponse({'ok': False, 'msg': str(recp)})
                else:
                    recp.creador = g_e
                    recp.save()
                    html = render_to_string('repoescalacp_accordion.html', {'recp': recp})
                    return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'open_accordion':
            try:
                recp = RepoEscalaCP.objects.get(id=request.POST['id'])
                html = render_to_string('repoescalacp_accordion_content.html', {'recp': recp, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_repoescalacp':
            try:
                recp = RepoEscalaCP.objects.get(id=request.POST['recp'])
                if g_e.has_permiso('borra_instrumento_repositorio') or g_e == recp.creador:
                    recp.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para borrar este instrumento.'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'buscar_repositorio':
            try:
                palabras = request.POST['texto'].split()
                if len(palabras) > 0:
                    q = Q(creador__gauser__first_name__icontains=palabras[0]) | Q(
                        creador__gauser__last_name__icontains=palabras[0])
                    for palabra in palabras:
                        q = q | Q(nombre__icontains=palabra) | Q(observaciones__icontains=palabra)
                    paginator = Paginator(RepoEscalaCP.objects.filter(q).distinct(), 25)
                    recps = paginator.page(1)
                    html = render_to_string('repoescalacp_accordion.html', {'recps': recps, 'buscar': True})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'Debes escribir algo para poder buscar.'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'go_page':
            try:
                palabras = request.POST['texto'].split()
                if len(palabras) > 0:
                    q = Q(creador__gauser__first_name__icontains=palabras[0]) | Q(
                        creador__gauser__last_name__icontains=palabras[0])
                    for palabra in palabras:
                        q = q | Q(nombre__icontains=palabra) | Q(observaciones__icontains=palabra)
                    paginator = Paginator(RepoEscalaCP.objects.filter(q).distinct(), 5)
                    buscar = True
                else:
                    paginator = Paginator(RepoEscalaCP.objects.all(), 5)
                    buscar = False
                recps = paginator.page(request.POST['page'])
                html = render_to_string('repoescalacp_accordion.html', {'recps': recps, 'buscar': buscar})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

    elif request.method == 'POST' and request.POST['action'] == 'upload_archivo_xhr':
        try:
            # Al no permitir carga múltiple de archivos n_files es siempre 1
            # n_files = int(request.POST['n_files'])
            # for i in range(n_files):
            #     fichero = request.FILES['archivo_xhr' + str(i)]
            fichero = request.FILES['archivo_xhr0']
            if fichero.content_type in 'application/vnd.ms-excel application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                rows = []
                book = xlrd.open_workbook(file_contents=fichero.read())
                sheet = book.sheet_by_index(0)
                valores_sin_normalizar = []
                for n, texto in enumerate([sheet.cell(0, col_index).value for col_index in range(sheet.ncols)]):
                    punto = False
                    valor = ''
                    texto_cualitativo = ''
                    for caracter in texto:
                        if caracter.isdigit():
                            valor += caracter
                        elif caracter == '.' and not punto:
                            valor += caracter
                            punto = True
                        else:
                            texto_cualitativo += caracter
                    try:
                        valor = float(valor)
                    except:
                        valor = 0
                    rows.append({'x': n, 'y': 0, 'valor': valor, 'texto': texto_cualitativo})
                    valores_sin_normalizar.append(valor)
                escala = 10 / max(valores_sin_normalizar)
                valores = [round(v * escala, 2) for v in valores_sin_normalizar]
                for row_index in range(1, sheet.nrows):
                    for col_index in range(sheet.ncols):
                        rows.append({'x': col_index, 'y': row_index, 'valor': valores[col_index],
                                     'texto': sheet.cell(row_index, col_index).value})
            nombre_rubrica = fichero.name.rpartition('.')[0].replace('-', ' ').capitalize()
            obs = 'Importación xls iDoceo %s' % fichero.name
            recp, c = RepoEscalaCP.objects.get_or_create(tipo='ESVCL', nombre=nombre_rubrica, observaciones=obs)
            if c:
                recp.creador = g_e
                recp.save()
                for row in rows:
                    RepoEscalaCPvalor.objects.create(ecp=recp, x=row['x'], y=row['y'], texto_cualitativo=row['texto'],
                                                     valor=row['valor'])
            html = render_to_string('repoescalacp_accordion.html', {'recp': recp})
            return JsonResponse({'ok': True, 'html': html})
        except:
            return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})

    paginator = Paginator(RepoEscalaCP.objects.all(), 25)
    return render(request, "repoescalacp.html",
                  {
                      'formname': 'repoescalacp',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Importar instrumento', 'permiso': 'libre',
                            'title': 'Importar un instrumento de evaluación al repositorio.'},
                           {'tipo': 'button', 'nombre': 'info-circle', 'texto': 'Ayuda', 'permiso': 'libre',
                            'title': 'Ayuda sobre el uso del repositorio de instrumentos de evaluación.'},
                           ),
                      'recps': paginator.page(1),
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


# @permiso_required('acceso_repositorio_instrumento')
def calificacc(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'select_grupo':
            try:
                grupo = Grupo.objects.get(id=request.POST['grupo'])
                try:
                    min_datetime = datetime.strptime('01/05/2024 23:05', '%d/%m/%Y %H:%M')
                    madrid_timezone = pytz.timezone('Europe/Madrid')
                    min_datetime_timezone = madrid_timezone.localize(min_datetime)
                    tabla_cc = TablaCompetenciasClave.objects.get(grupo=grupo, modificado__gt=min_datetime_timezone)
                    ps = tabla_cc.ps
                    html = tabla_cc.tabla
                except:
                    TablaCompetenciasClave.objects.filter(grupo=grupo).delete()
                    alumnos = Gauser_extra.objects.filter(gauser_extra_estudios__grupo=grupo)
                    cuadernos = CuadernoProf.objects.filter(alumnos__in=alumnos, borrado=False).distinct()
                    am_ids = cuadernos.values_list('psec__areamateria__id', flat=True)
                    ams = AreaMateria.objects.filter(id__in=am_ids)
                    ps = ams[0].ps
                    alum_order = alumnos.order_by('gauser__last_name')
                    html = render_to_string('calificacc_tabla.html', {'alumnos': alum_order, 'ps': ps, 'ams': ams,
                                                                      'cuadernos': cuadernos,
                                                                      'fecha_hora': datetime.now(), 'grupo': grupo})
                    TablaCompetenciasClave.objects.create(grupo=grupo, ps=ps, tabla=html)
                return JsonResponse({'ok': True, 'html': html, 'ps': ps.id})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'actualizar_datos':
            try:
                grupo = Grupo.objects.get(id=request.POST['grupo'])
                TablaCompetenciasClave.objects.filter(grupo=grupo).delete()
                tabla_cc = TablaCompetenciasClave.objects.create(grupo=grupo)
                alumnos = Gauser_extra.objects.filter(gauser_extra_estudios__grupo=grupo)
                cuadernos = CuadernoProf.objects.filter(alumnos__in=alumnos, borrado=False).distinct()
                am_ids = cuadernos.values_list('psec__areamateria__id', flat=True)
                ams = AreaMateria.objects.filter(id__in=am_ids)
                ps = ams[0].ps
                alum_order = alumnos.order_by('gauser__last_name')
                html = render_to_string('calificacc_tabla.html', {'alumnos': alum_order, 'ps': ps, 'ams': ams,
                                                                  'cuadernos': cuadernos,
                                                                  'fecha_hora': datetime.now(), 'grupo': grupo})
                tabla_cc.ps = ps
                tabla_cc.tabla = html
                tabla_cc.save()
                return JsonResponse({'ok': True, 'html': html, 'ps': ps.id})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'carga_alumnocc':
            try:
                cal_dos = {}
                cal_ces = {}
                alumno = Gauser_extra.objects.get(id=request.POST['alumno'], ronda=g_e.ronda)
                cuadernos = CuadernoProf.objects.filter(alumnos__in=[alumno], borrado=False)
                cursos = []
                ams = []
                # Cada AreaMateria debería estar evaluada en un solo cuaderno. Registro de cuadernos múltiples:
                ams_multiples = {}
                for cuaderno in cuadernos:
                    curso = cuaderno.psec.areamateria.get_curso_display()
                    am = cuaderno.psec.areamateria.id
                    if curso not in cursos:
                        cursos.append(curso)
                    if am not in ams:
                        ams.append(am)
                        ams_multiples[am] = 1
                    else:
                        ams_multiples[am] += 1
                msg_ams_multiples = ''
                for k, v in ams_multiples.items():
                    if v > 1:
                        am = AreaMateria.objects.get(id=k).nombre
                        msg_ams_multiples += '<li><b>La asignatura %s tiene %s cuadernos diferentes.</b></li>' % (am, v)
                html = render_to_string('calificacc_tabla_alumno.html', {'cuadernos': cuadernos})
                ps = PerfilSalida.objects.get(id=request.POST['ps'])
                cc_siglas = []
                dos_claves = []
                for cc in ps.competenciaclave_set.all():
                    cc_siglas.append(cc.siglas)
                    for do in DescriptorOperativo.objects.filter(cc=cc):
                        dos_claves.append(do.clave)
                cals_ces_alumnos = CalAlumCE.objects.filter(alumno=alumno, cp__borrado=False)
                for cal_ce_alumno in cals_ces_alumnos:
                    ce = cal_ce_alumno.cep.ce
                    cal_ce = cal_ce_alumno.valor
                    cal_ces['cal_ce_informe%s' % ce.id] = cal_ce
                    for do in ce.dos.all():
                        key = 'do-%s-%s-%s' % (ce.am.id, ce.id, do.id)
                        cal_dos[key] = cal_ce
                informe = calcula_calificaciones_cc(alumno)
                return JsonResponse({'ok': True, 'cal_dos': cal_dos, 'cc_siglas': cc_siglas, 'dos_claves': dos_claves,
                                     'nombre_alumno': alumno.gauser.get_full_name(), 'cal_ces': cal_ces, 'html': html,
                                     'grupo': alumno.gauser_extra_estudios.grupo.nombre, 'cursos': cursos, 'ams': ams,
                                     'msg_ams_multiples': msg_ams_multiples, 'informe': informe})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'buscar_repositorio':
            try:
                palabras = request.POST['texto'].split()
                if len(palabras) > 0:
                    q = Q(creador__gauser__first_name__icontains=palabras[0]) | Q(
                        creador__gauser__last_name__icontains=palabras[0])
                    for palabra in palabras:
                        q = q | Q(nombre__icontains=palabra) | Q(observaciones__icontains=palabra)
                    paginator = Paginator(RepoEscalaCP.objects.filter(q).distinct(), 25)
                    recps = paginator.page(1)
                    html = render_to_string('repoescalacp_accordion.html', {'recps': recps, 'buscar': True})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': 'Debes escribir algo para poder buscar.'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
    elif request.method == 'POST' and request.POST['action'] == 'genera_pdf':
        doc_progsec_informe_cc = 'Configuración para el informe de adquisición de competencias clave'
        dce = get_dce(g_e.ronda.entidad, doc_progsec_informe_cc)
        tablas = request.POST['textarea_tabla_generar_informe']
        c = render_to_string('califcacc_tabla_alumno_html2pdf.html', {'tablas': tablas, 'dce': dce})
        genera_pdf(c, dce)
        nombre = slugify('Informe_competencias_clave')
        return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename=nombre + '.pdf',
                            content_type='application/pdf')
    alumnos_id = CuadernoProf.objects.filter(ge__ronda=g_e.ronda, borrado=False).values_list('alumnos', flat=True)
    grupos_id = Gauser_extra_estudios.objects.filter(ge__id__in=alumnos_id, grupo__isnull=False).values_list('grupo', flat=True)
    grupos = Grupo.objects.filter(id__in=grupos_id).distinct().order_by('cursos')
    return render(request, "calificacc.html",
                  {
                      'formname': 'calificacc',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'file-o', 'texto': 'Generar informes', 'permiso': 'libre',
                            'title': 'Generar todos los informes del grupo a la vez.'},
                           {'tipo': 'button', 'nombre': 'info-circle', 'texto': 'Ayuda', 'permiso': 'libre',
                            'title': 'Ayuda sobre el uso del repositorio de instrumentos de evaluación.'},
                           ),
                      # 'grupos': set(grupos),
                      'grupos': grupos,
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


def calcula_calificaciones_cc__antiguo(alumno):
    try:
        cuadernos = CuadernoProf.objects.filter(alumnos__in=[alumno], borrado=False)
        cursos = []
        ams_ids = []
        # Cada AreaMateria debería estar evaluada en un solo cuaderno. Registro de cuadernos múltiples:
        ams_multiples = {}
        for cuaderno in cuadernos:
            curso = cuaderno.psec.areamateria.get_curso_display()
            am_id = cuaderno.psec.areamateria.id
            if curso not in cursos:
                cursos.append(curso)
            if am_id not in ams_ids:
                ams_ids.append(am_id)
                ams_multiples[am_id] = 1
            else:
                ams_multiples[am_id] += 1
        msg_cua_ams_multiples = ''
        for k, v in ams_multiples.items():
            if v > 1:
                am = AreaMateria.objects.get(id=k).nombre
                msg_cua_ams_multiples += '<li><b>La asignatura %s tiene %s cuadernos diferentes.</b></li>' % (am, v)
        html = render_to_string('calificacc_tabla_alumno.html', {'cuadernos': cuadernos,
                                                                 'msg_cua_ams_multiples': msg_cua_ams_multiples})

        ams = AreaMateria.objects.filter(id__in=ams_ids)
        ps = ams[0].ps
        cal_ccs = {}
        cal_dos = {}
        cal_ces = {}
        calificaciones = {}
        for cc in ps.competenciaclave_set.all():
            calificaciones[cc.siglas] = {}
            cal_ccs['cal_cc_informe%s_%s' % (cc.siglas, alumno.id)] = 0
            for do in DescriptorOperativo.objects.filter(cc=cc):
                calificaciones[cc.siglas][do.clave] = []
                cal_dos['cal_do_informe%s_%s' % (do.clave, alumno.id)] = 0
        cals_ces_alumno = CalAlumCE.objects.filter(alumno=alumno, cp__borrado=False)
        for cal_ce_alumno in cals_ces_alumno:
            ce = cal_ce_alumno.cep.ce
            cal_ce = cal_ce_alumno.valor
            cal_ces['cal_ce_informe%s_%s' % (ce.id, alumno.id)] = cal_ce
            for do in ce.dos.all():
                if cal_ce > 0:
                    calificaciones[do.cc.siglas][do.clave].append(cal_ce)
        for cc in calificaciones:
            num_dos = 0
            cal_cc = 0
            for do in calificaciones[cc]:
                try:
                    cal_dos['cal_do_informe%s_%s' % (do, alumno.id)] = sum(calificaciones[cc][do]) / len(
                        calificaciones[cc][do])
                except:
                    cal_dos['cal_do_informe%s_%s' % (do, alumno.id)] = 0
                if cal_dos['cal_do_informe%s_%s' % (do, alumno.id)] > 0:
                    cal_cc += cal_dos['cal_do_informe%s_%s' % (do, alumno.id)]
                    num_dos += 1
            try:
                cal_cc_num = cal_cc / num_dos
            except:
                cal_cc_num = 0

            if cal_cc_num <= 4:
                cal_ccs['cal_cc_informe%s_%s' % (cc, alumno.id)] = 'D'
            elif cal_cc_num <= 6:
                cal_ccs['cal_cc_informe%s_%s' % (cc, alumno.id)] = 'C'
            elif cal_cc_num <= 8:
                cal_ccs['cal_cc_informe%s_%s' % (cc, alumno.id)] = 'B'
            else:
                cal_ccs['cal_cc_informe%s_%s' % (cc, alumno.id)] = 'A'

        html = render_to_string('calificacc_alumno.html',
                                {'cal_dos': cal_dos, 'cal_ccs': cal_ccs, 'cal_ces': cal_ces, 'ams': ams_ids,
                                 'alumno_id': alumno.id})
        return {'ok': True, 'cal_dos': cal_dos, 'cal_ccs': cal_ccs, 'cal_ces': cal_ces, 'ams': ams_ids,
                'alumno_id': alumno.id, 'html': html}
    except Exception as msg:
        return {'ok': False, 'msg': str(msg)}


def calcula_calificaciones_cc(alumno):
    try:
        cuadernos = CuadernoProf.objects.filter(alumnos__in=[alumno], borrado=False)
        cursos = []
        ams_ids = []
        # Cada AreaMateria debería estar evaluada en un solo cuaderno. Registro de cuadernos múltiples:
        ams_multiples = {}
        for cuaderno in cuadernos:
            curso = cuaderno.psec.areamateria.get_curso_display()
            am_id = cuaderno.psec.areamateria.id
            if curso not in cursos:
                cursos.append(curso)
            if am_id not in ams_ids:
                ams_ids.append(am_id)
                ams_multiples[am_id] = 1
            else:
                ams_multiples[am_id] += 1
        msg_cua_ams_multiples = ''
        for k, v in ams_multiples.items():
            if v > 1:
                am = AreaMateria.objects.get(id=k).nombre
                msg_cua_ams_multiples += '<li><b>La asignatura %s tiene %s cuadernos diferentes.</b></li>' % (am, v)
        html = render_to_string('calificacc_tabla_alumno.html', {'cuadernos': cuadernos,
                                                                 'msg_cua_ams_multiples': msg_cua_ams_multiples})

        ams = AreaMateria.objects.filter(id__in=ams_ids)
        ps = ams[0].ps
        cal_ccs = {}
        cal_dos = {}
        cal_ces = {}
        calificaciones = {}
        for cc in ps.competenciaclave_set.all():
            calificaciones[cc.siglas] = {}
            cal_ccs['cal_cc_informe%s' % (cc.siglas)] = 0
            for do in DescriptorOperativo.objects.filter(cc=cc):
                calificaciones[cc.siglas][do.clave] = []
                cal_dos['cal_do_informe%s' % (do.clave)] = 0
        cals_ces_alumno = CalAlumCE.objects.filter(alumno=alumno, cp__borrado=False)
        for cal_ce_alumno in cals_ces_alumno:
            ce = cal_ce_alumno.cep.ce
            cal_ce = cal_ce_alumno.valor
            cal_ces['cal_ce_informe%s' % (ce.id)] = cal_ce
            for do in ce.dos.all():
                if cal_ce > 0:
                    calificaciones[do.cc.siglas][do.clave].append(cal_ce)
        for cc in calificaciones:
            num_dos = 0
            cal_cc = 0
            for do in calificaciones[cc]:
                try:
                    cal_dos['cal_do_informe%s' % (do)] = sum(calificaciones[cc][do]) / len(
                        calificaciones[cc][do])
                except:
                    cal_dos['cal_do_informe%s' % (do)] = 0
                if cal_dos['cal_do_informe%s' % (do)] > 0:
                    cal_cc += cal_dos['cal_do_informe%s' % (do)]
                    num_dos += 1
            try:
                cal_cc_num = cal_cc / num_dos
            except:
                cal_cc_num = 0

            if cal_cc_num <= 4:
                cal_ccs['cal_cc_informe%s' % (cc)] = 'D'
            elif cal_cc_num <= 6:
                cal_ccs['cal_cc_informe%s' % (cc)] = 'C'
            elif cal_cc_num <= 8:
                cal_ccs['cal_cc_informe%s' % (cc)] = 'B'
            else:
                cal_ccs['cal_cc_informe%s' % (cc)] = 'A'

        return render_to_string('calificacc_alumno.html',
                                {'cal_dos': cal_dos, 'cal_ccs': cal_ccs, 'cal_ces': cal_ces, 'ams': ams_ids,
                                 'alumno': alumno, 'ps': ps, 'ams': ams})
    except Exception as msg:
        return {'ok': False, 'msg': str(msg)}


@permiso_required('acceso_calificaciones_competencias_clave')
def calificacc_all(request, grupo_id):
    g_e = request.session['gauser_extra']
    grupo = Grupo.objects.get(id=grupo_id, ronda__entidad=g_e.ronda.entidad)
    alumnos = Gauser_extra.objects.filter(gauser_extra_estudios__grupo=grupo)
    if request.method == 'POST' and request.POST['action'] == 'carga_alumnocc':
        try:
            alumno = alumnos.get(id=request.POST['alumno_id'])
            return JsonResponse({'ok': True, 'informe': calcula_calificaciones_cc(alumno)})
        except Exception as msg:
            return JsonResponse({'ok': False, 'msg': str(msg)})
        # try:
        #     alumno = alumnos.get(id=request.POST['alumno_id'])
        #     cuadernos = CuadernoProf.objects.filter(alumnos__in=[alumno], borrado=False)
        #     cursos = []
        #     ams_ids = []
        #     # Cada AreaMateria debería estar evaluada en un solo cuaderno. Registro de cuadernos múltiples:
        #     ams_multiples = {}
        #     for cuaderno in cuadernos:
        #         curso = cuaderno.psec.areamateria.get_curso_display()
        #         am_id = cuaderno.psec.areamateria.id
        #         if curso not in cursos:
        #             cursos.append(curso)
        #         if am_id not in ams_ids:
        #             ams_ids.append(am_id)
        #             ams_multiples[am_id] = 1
        #         else:
        #             ams_multiples[am_id] += 1
        #     msg_ams_multiples = ''
        #     for k, v in ams_multiples.items():
        #         if v > 1:
        #             am = AreaMateria.objects.get(id=k).nombre
        #             msg_ams_multiples += '<li><b>La asignatura %s tiene %s cuadernos diferentes.</b></li>' % (am, v)
        #     html = render_to_string('calificacc_tabla_alumno.html', {'cuadernos': cuadernos})
        #
        #     ams = AreaMateria.objects.filter(id__in=ams_ids)
        #     ps = ams[0].ps
        #     cal_ccs = {}
        #     cal_dos = {}
        #     cal_ces = {}
        #     calificaciones = {}
        #     for cc in ps.competenciaclave_set.all():
        #         calificaciones[cc.siglas] = {}
        #         cal_ccs['cal_cc_informe%s_%s' % (cc.siglas, alumno.id)] = 0
        #         for do in DescriptorOperativo.objects.filter(cc=cc):
        #             calificaciones[cc.siglas][do.clave] = []
        #             cal_dos['cal_do_informe%s_%s' % (do.clave, alumno.id)] = 0
        #     cals_ces_alumnos = CalAlumCE.objects.filter(alumno=alumno, cp__borrado=False)
        #     for cal_ce_alumno in cals_ces_alumnos:
        #         ce = cal_ce_alumno.cep.ce
        #         cal_ce = cal_ce_alumno.valor
        #         cal_ces['cal_ce_informe%s_%s' % (ce.id, alumno.id)] = cal_ce
        #         for do in ce.dos.all():
        #             calificaciones[do.cc.siglas][do.clave].append(cal_ce)
        #     for cc in calificaciones:
        #         num_dos = 0
        #         cal_cc = 0
        #         for do in calificaciones[cc]:
        #             try:
        #                 cal_dos['cal_do_informe%s_%s' % (do, alumno.id)] = sum(calificaciones[cc][do]) / len(
        #                     calificaciones[cc][do])
        #             except:
        #                 cal_dos['cal_do_informe%s_%s' % (do, alumno.id)] = 0
        #             if cal_dos['cal_do_informe%s_%s' % (do, alumno.id)] > 0:
        #                 cal_cc += cal_dos['cal_do_informe%s_%s' % (do, alumno.id)]
        #                 num_dos += 1
        #         try:
        #             cal_ccs['cal_cc_informe%s_%s' % (cc, alumno.id)] = cal_cc / num_dos
        #         except:
        #             cal_ccs['cal_cc_informe%s_%s' % (cc, alumno.id)] = 0
        #
        #     return JsonResponse({'ok': True, 'cal_dos': cal_dos, 'cal_ccs': cal_ccs, 'cal_ces': cal_ces, 'ams': ams_ids,
        #                          'alumno_id': alumno.id})
        # except Exception as msg:
        #     return JsonResponse({'ok': False, 'msg': str(msg)})

    if request.method == 'POST' and request.POST['action'] == 'genera_pdf':
        doc_progsec_informe_cc = 'Configuración para el informe de adquisición de competencias clave'
        dce = get_dce(g_e.ronda.entidad, doc_progsec_informe_cc)
        tablas = request.POST['textarea_tabla_generar_informe']
        c = render_to_string('califcacc_tabla_alumno_html2pdf.html', {'tablas': tablas, 'dce': dce,
                                                                      'grupo': grupo})
        genera_pdf(c, dce)
        nombre = slugify('Informe_competencias_clave')
        return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename=nombre + '.pdf',
                            content_type='application/pdf')

    cuadernos = CuadernoProf.objects.filter(alumnos__in=alumnos, borrado=False).distinct()
    am_ids = cuadernos.values_list('psec__areamateria__id', flat=True)
    ams = AreaMateria.objects.filter(id__in=am_ids)
    return render(request, "calificacc_all.html",
                  {
                      'formname': 'calificacc_all',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF',
                            'title': 'Generar pdf de los informes competenciales',
                            'permiso': 'libre'},
                           # {'tipo': 'button', 'nombre': 'info-circle', 'texto': 'Ayuda', 'permiso': 'libre',
                           #  'title': 'Ayuda sobre el uso del repositorio de instrumentos de evaluación.'},
                           ),
                      'grupo_id': grupo_id,
                      'alumnos': alumnos,
                      'alumnos_id': json.dumps(list(alumnos.values_list('id', flat=True))),
                      'ps': ams[0].ps,
                      'ams': ams,
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@gauss_required
def configurar_cargos_permisos(request):
    from gauss.constantes import CARGOS
    from entidades.menus_entidades import TiposCentro
    from autenticar.models import Permiso
    mensaje = 'Hecho.'
    for e in Entidad.objects.all():
        try:
            if e.entidadextra.tipo_centro in TiposCentro:
                for c in CARGOS:
                    cargo, creado = Cargo.objects.get_or_create(entidad=e, borrable=False, clave_cargo=c['clave_cargo'])
                    if creado:
                        cargo.cargo = c['cargo']
                        cargo.save()
                    for code_nombre in c['permisos']:
                        try:
                            cargo.permisos.add(Permiso.objects.get(code_nombre=code_nombre))
                        except Exception as msg:
                            mensaje += '<br>%s -- %s' % (code_nombre, str(msg))
        except Exception as msg:
            mensaje += '<br>%s -- %s' % (e, str(msg))
    return HttpResponse(mensaje)


@gauss_required
def arregla_cuaderno(request, cuaderno_id, max_cal):
    # La siguiente llamada https://gauss.larioja.org/456/100  significaría:
    # Arreglar el cuaderno con id=456
    # Coger todas las calificaciones del cuaderno y hacer la operación: cal/100*10
    # La operación en realidad es: cal/max_cal*10 para normalizar la calificación entre 0 y 10
    try:
        cuaderno = CuadernoProf.objects.get(id=cuaderno_id)
        ecpvs = EscalaCPvalor.objects.filter(ecp__cp=cuaderno)
        for ecpv in ecpvs:
            if ecpv.valor > 10:
                ecpv.valor = ecpv.valor / max_cal * 10
                ecpv.save()
        cavs = CalAlumValor.objects.filter(ca__cp=cuaderno)
        for cav in cavs:
            # Provoco que la señal de cálculo de 'update_calalumcev' se ejecute:
            cav.save()
        return HttpResponse('Operación de ajuste de calificaciones realizada.')
    except Exception as msg:
        return HttpResponse(str(msg))


@gauss_required
def arregla_cuaderno2(request, cuaderno_id, max_cal):
    # La siguiente llamada https://gauss.larioja.org/456/100  significaría:
    # Arreglar el cuaderno con id=456
    # Coger todas las calificaciones del cuaderno y hacer la operación: cal/100*10
    # La operación en realidad es: cal/max_cal*10 para normalizar la calificación entre 0 y 10
    try:
        cuaderno = CuadernoProf.objects.get(id=cuaderno_id)
        cavs = CalAlumValor.objects.filter(ca__cp=cuaderno).order_by('id')
        partes = int(str(max_cal)[0])
        parte = int(str(max_cal)[1])
        paginator = Paginator(cavs, int(cavs.count() / partes))
        for cav in paginator.get_page(parte):
            # Provoco que la señal de cálculo de 'update_calalumcev' se ejecute:
            cav.save()
        return HttpResponse('Operación de ajuste de calificaciones realizada 2.')
    except Exception as msg:
        return HttpResponse(str(msg))


@gauss_required
def arregla_cuaderno3(request, cuaderno_id, max_cal):
    # La siguiente llamada https://gauss.larioja.org/456/100  significaría:
    # Arreglar el cuaderno con id=456
    # Coger todas las calificaciones del cuaderno y hacer la operación: cal/100*10
    # La operación en realidad es: cal/max_cal*10 para normalizar la calificación entre 0 y 10
    try:
        cuaderno = CuadernoProf.objects.get(id=cuaderno_id)
        ecpvs = EscalaCPvalor.objects.filter(ecp__cp=cuaderno)
        for ecpv in ecpvs:
            ecpv.valor = ecpv.valor / max_cal * 10
            ecpv.save()
        return HttpResponse('Operación de ajuste de calificaciones realizada 3.')
    except Exception as msg:
        return HttpResponse(str(msg))


#########################################################
################### Crear los nuevos CalAlumCE y CalAlumCEv asociados a las CalAlumValor ya existentes
# Esta función hay que borrarla tras la primera ejecución sin errores
@gauss_required
def crea_calalumce_cev(request):
    try:
        from entidades.tasks import ejecutar_crea_calalumce_cev
        ejecutar_crea_calalumce_cev.apply_async(expires=300)
        return HttpResponse('Esta operación puede requerir varios minutos')
    except Exception as msg:
        return HttpResponse(str(msg))


@gauss_required
def arregla_instrevals(request):
    info = 0
    repoinfo = 0
    try:
        tipos = [t[0] for t in InstrEval.TIPOS]
        for instreval in InstrEval.objects.all():
            if instreval.tipo not in tipos:
                instreval.tipo = 'OBSS'
                instreval.save()
                info += 1
        for instreval in RepoInstrEval.objects.all():
            if instreval.tipo not in tipos:
                instreval.tipo = 'OBSS'
                instreval.save()
                repoinfo += 1
        return HttpResponse('InstrEvals (%s) y RepoInstrEvals (%s) arreglados' % (info, repoinfo))
    except Exception as msg:
        return HttpResponse(str(msg))


from programaciones.models import *
from django.core import serializers
from django.core.signing import Signer


# t='''Texto para
# ser separado
# en sus diferentes líneas'''
# for i, p in enumerate(t.splitlines()):
#     if p:
#         print(i, p.strip())

def copiaSeguridadCuaderno(cuaderno):
    ProgSecs = ProgSec.objects.filter(id=cuaderno.psec.id)
    CEProgSecs = CEProgSec.objects.filter(psec=cuaderno.psec)
    CEvProgSecs = CEvProgSec.objects.filter(cepsec__psec=cuaderno.psec)
    LibroRecursos = LibroRecurso.objects.filter(psec=cuaderno.psec)
    ActExComs = ActExCom.objects.filter(psec=cuaderno.psec)
    SaberBass = SaberBas.objects.filter(psec=cuaderno.psec, borrado=False)
    SitAprens = SitApren.objects.filter(sbas__psec=cuaderno.psec, borrado=False)
    ActSitAprens = ActSitApren.objects.filter(sapren__sbas__psec=cuaderno.psec, borrado=False)
    InstrEvals = InstrEval.objects.filter(asapren__sapren__sbas__psec=cuaderno.psec, borrado=False)
    CriInstrEvals = CriInstrEval.objects.filter(ieval__asapren__sapren__sbas__psec=cuaderno.psec, borrado=False)
    CuadernoProfs = [cuaderno]
    # CalAlumCEs = cuaderno.calalumce_set.all()
    CalAlumCEs = CalAlumCE.objects.filter(cp=cuaderno)
    CalAlumCEvs = CalAlumCEv.objects.filter(calalumce__cp=cuaderno)
    EscalaCPs = EscalaCP.objects.filter(cp=cuaderno)
    EscalaCPvalors = EscalaCPvalor.objects.filter(ecp__cp=cuaderno)
    CalAlums = CalAlum.objects.filter(cp=cuaderno)
    CalAlumValors = CalAlumValor.objects.filter(ca__cp=cuaderno)
    objetos = [*ProgSecs, *CEProgSecs, *CEvProgSecs, *LibroRecursos, *ActExComs, *SaberBass, *SitAprens, *ActSitAprens,
               *InstrEvals, *CriInstrEvals, *CuadernoProfs, *CalAlumCEs, *CalAlumCEvs, *EscalaCPs, *EscalaCPvalors,
               *CalAlums, *CalAlumValors]
    data = serializers.serialize('jsonl', objetos)
    signer = Signer()
    data_signed = signer.sign(data)
    with open("Output.cua", "w") as text_file:
        text_file.write(data_signed)


def restaurarCopiaSeguridadCuaderno(ruta_archivo):
    # with open('Output.cua', 'r') as file:
    with open(ruta_archivo, 'r') as file:
        data_read = file.read()
        # Se supone que data_read y data_signed son iguales. Por tanto, se podría hacer:
        signer2 = Signer()
        datos_recuperados = signer2.unsign(data_read)
        dict_relaciones = {}
        for deserialized_object in serializers.deserialize("jsonl", datos_recuperados):
            pk_antiguo = deserialized_object.object.pk
            deserialized_object.save()
            pk_nuevo = deserialized_object.object.pk
            try:
                dict_relaciones[deserialized_object.object.__class__.__name__][pk_antiguo] = pk_nuevo
            except:
                dict_relaciones[deserialized_object.object.__class__.__name__] = {}
                dict_relaciones[deserialized_object.object.__class__.__name__][pk_antiguo] = pk_nuevo

            # Guardaremos en un diccionario la relación entre los antiguos objetos y los nuevos:
