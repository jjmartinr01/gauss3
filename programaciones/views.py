# -*- coding: utf-8 -*-
from datetime import date, datetime
import simplejson as json
import unicodedata
import os
import zipfile
import shutil
import locale
from math import modf
import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q, Sum
from django import forms
from django.forms import ModelForm
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.core.files.base import File

from autenticar.control_acceso import permiso_required
from autenticar.models import Gauser
# from autenticar.control_acceso import access_required
from entidades.models import Cargo
from entidades.templatetags.entidades_extras import profesorado
from gauss.funciones import html_to_pdf, usuarios_ronda, usuarios_de_gauss, get_dce
from programaciones.models import *
from gauss.rutas import RUTA_BASE, MEDIA_PROGRAMACIONES
from mensajes.views import crear_aviso
from mensajes.models import Aviso
from estudios.models import ETAPAS

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
            doc_pga = 'Configuración de documentos de la PGA'
            dce = get_dce(g_e.ronda.entidad, doc_pga)
            pga = PGA.objects.get(ronda=g_e.ronda)
            # try:
            # Procesado del archivo de aspectos de la PGA
            c = render_to_string('aspectos_generales_pga2pdf.html', {'pga': pga})
            ruta = rutas_aspectos_pga(pga)['absoluta']
            nombre_fichero = 'aspectos_generales_pga'
            if os.path.exists('%s%s.pdf' % (ruta, nombre_fichero)):
                os.remove('%s%s.pdf' % (ruta, nombre_fichero))
            html_to_pdf(request, c, fichero=nombre_fichero, media=ruta, title='Aspectos Generales de la PGA')
            if os.path.exists('%s%s.html' % (ruta, nombre_fichero)):
                os.remove('%s%s.html' % (ruta, nombre_fichero))
            # Procesado del archivo de aspectos del PEC
            pec = PEC.objects.get(entidad=g_e.ronda.entidad)
            c = render_to_string('aspectos_generales_pec2pdf.html', {'pec': pec})
            ruta = rutas_pec(pec)['absoluta']
            nombre_fichero = 'aspectos_generales_pec'
            if os.path.exists('%s%s.pdf' % (ruta, nombre_fichero)):
                os.remove('%s%s.pdf' % (ruta, nombre_fichero))
            html_to_pdf(request, c, fichero=nombre_fichero, media=ruta, title='Aspectos Generales del PEC')
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
            except:
                return JsonResponse({'ok': False})
        elif action == 'edad_min_departamento' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.edad_min = int(request.POST['edad_min'])
                departamento.save()
                return JsonResponse({'ok': True, 'edad_min': departamento.edad_min})
            except:
                return JsonResponse({'ok': False})
        elif action == 'edad_max_departamento' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.edad_max = int(request.POST['edad_max'])
                departamento.save()
                return JsonResponse({'ok': True, 'edad_max': departamento.edad_max})
            except:
                return JsonResponse({'ok': False})
        elif action == 'mensajes' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.mensajes = not departamento.mensajes
                departamento.save()
                return JsonResponse({'ok': True, 'mensajes': ['No', 'Sí'][departamento.mensajes]})
            except:
                return JsonResponse({'ok': False})
        elif action == 'observaciones' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.observaciones = request.POST['observaciones']
                departamento.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
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
            except:
                return JsonResponse({'ok': False})
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
            except:
                return JsonResponse({'ok': False})
        elif action == 'fecha_expira' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.fecha_expira = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
                departamento.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'clave_ex' and g_e.has_permiso('edita_departamentos'):
            try:
                departamento = Departamento.objects.get(pk=request.POST['id'], entidad=g_e.ronda.entidad)
                departamento.clave_ex = request.POST['clave_ex']
                departamento.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
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
            except:
                return JsonResponse({'ok': False})
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
            except:
                return JsonResponse({'ok': False})
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
            except:
                return JsonResponse({'ok': False})
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
            except:
                return JsonResponse({'ok': False})
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
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            try:
                resultado = Resultado_aprendizaje.objects.get(id=request.POST['id'],
                                                              materia__materia__curso__ronda=g_e.ronda)
                html = render_to_string('resultados_aprendizaje_accordion_content.html', {'r': resultado})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'borrar_resultado':
            try:
                r = Resultado_aprendizaje.objects.get(id=request.POST['id'])
                if r.materia.materia.curso.ronda == g_e.ronda:
                    r.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No puedes borrar el resultado de aprendizaje'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_resultado':
            try:
                r = Resultado_aprendizaje.objects.get(id=request.POST['id'])
                if r.materia.materia.curso.ronda == g_e.ronda:
                    r.resultado = request.POST['html']
                    r.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No puedes modificar el resultado de aprendizaje'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_objetivo':
            try:
                r = Resultado_aprendizaje.objects.get(id=request.POST['id'], materia__materia__curso__ronda=g_e.ronda)
                o = Objetivo.objects.create(materia=r.materia, resultado_aprendizaje=r, texto="Conseguir ...",
                                            crit_eval='El alumno consigue ...')
                html = render_to_string('resultados_aprendizaje_accordion_content_objetivo.html', {'o': o})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'mod_objetivo':
            try:
                o = Objetivo.objects.get(id=request.POST['id'],
                                         resultado_aprendizaje__materia__materia__curso__ronda=g_e.ronda)
                o.texto = request.POST['html']
                o.save()
                return JsonResponse({'ok': True, 'html': o.texto})
            except:
                return JsonResponse({'ok': False})
        elif action == 'mod_crit_eval':
            try:
                o = Objetivo.objects.get(id=request.POST['id'],
                                         resultado_aprendizaje__materia__materia__curso__ronda=g_e.ronda)
                o.crit_eval = request.POST['html']
                o.save()
                return JsonResponse({'ok': True, 'html': o.crit_eval})
            except:
                return JsonResponse({'ok': False})
        elif action == 'borrar_objetivo':
            try:
                o = Objetivo.objects.get(id=request.POST['id'],
                                         resultado_aprendizaje__materia__materia__curso__ronda=g_e.ronda).delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})

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
                fichero = '%s_%s' % (g_e.ronda.entidad.code, programacion.id)
                c = render_to_string('programacion2pdf.html', {'programacion': programacion},
                                     request=request)
                fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_ESCRITOS,
                                   title='Programacion_modulo generado con GAUSS')
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + programacion.asunto.replace(' ',
                                                                                                        '_') + '.pdf'
                return response
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
                crear_aviso(request, True, 'Detecta id y se genera el pdf de la programación: %s' % (programacion))
                c = render_to_string('programacion2pdf.html', {'prog': programacion})
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
                fich = html_to_pdf(request, c, fichero=fichero, media=file_path,
                                   title='Programación del módulo generada con GAUSS')
                crear_aviso(request, True, 'prog 9')
                response = HttpResponse(fich, content_type='application/pdf')
                crear_aviso(request, True, 'prog 10')
                response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
                crear_aviso(request, True, 'prog 11')
                return response
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
            fich = html_to_pdf(request, c, fichero='programacion_ccff', media=ruta,
                               title='Programación del módulo generada con GAUSS')
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
            # -----------------------------------
            # fichero = replace_normalize(programacion.modulo.materia.nombre)
            # curso = g_e.ronda.entidad.ronda.nombre.replace('/', '-')
            # file_path = '%s%s/%s/%s/%s/%s/' % (MEDIA_PROGRAMACIONES, g_e.ronda.entidad.code,
            #                                     curso, g_e.gauser_extra_programaciones.departamento.nombre,
            #                                     programacion.modulo.materia.curso.get_etapa_display(),
            #                                     programacion.modulo.materia.curso.nombre)
            # file_path = replace_normalize(file_path)
            # programacion.file_path = file_path + fichero
            # programacion.save()
            # fich = html_to_pdf(request, c, fichero=fichero, media=file_path,
            #                    title='Programación del módulo generada con GAUSS')
            # response = HttpResponse(fich, content_type='application/pdf')
            # response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            # return response
            # -----------------------------------
            response = HttpResponse(p.archivo, content_type=p.content_type)
            response['Content-Disposition'] = 'attachment; filename=%s' % p.filename
            return response
            # -----------------------------------
        if request.POST['action'] == 'pdf_ud':
            ud = UD_modulo.objects.get(id=request.POST['unidad_didactica'])
            crear_aviso(request, True, 'Genera el pdf de la unidad didáctica: %s' % (ud.nombre))
            fichero = '%s_%s_%s' % (g_e.ronda.entidad.code, ud.programacion.id, ud.id)
            c = render_to_string('ud2pdf.html', {'ud': ud})
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_PROGRAMACIONES,
                               title='Programacion_modulo generado con GAUSS')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + ud.nombre.replace(' ', '_') + '.pdf'
            return response
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
                c = render_to_string('titulo2pdf.html', {'titulo': titulo}, request=request)
                fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_ESCRITOS,
                                   title='Titulo_FP generado con GAUSS')
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + titulo.asunto.replace(' ', '_') + '.pdf'
                return response
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
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_ESCRITOS,
                               title='Titulo_FP generado con GAUSS')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + titulo.asunto.replace(' ',
                                                                                              '_') + '.pdf'
            return response
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
            except:
                return JsonResponse({'ok': False})

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
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_texto_pga':
            try:
                pga = PGA.objects.get(ronda=g_e.ronda, id=request.POST['pga'])
                setattr(pga, request.POST['campo'], request.POST['texto'])
                pga.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
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
            # try:
            # Procesado del archivo de aspectos de la PGA
            c = render_to_string('aspectos_generales_pga2pdf.html', {'pga': pga})
            ruta = rutas_aspectos_pga(pga)['absoluta']
            nombre_fichero = 'aspectos_generales_pga'
            if os.path.exists('%s%s.pdf' % (ruta, nombre_fichero)):
                os.remove('%s%s.pdf' % (ruta, nombre_fichero))
            html_to_pdf(request, c, fichero=nombre_fichero, media=ruta, title='Aspectos Generales de la PGA')
            if os.path.exists('%s%s.html' % (ruta, nombre_fichero)):
                os.remove('%s%s.html' % (ruta, nombre_fichero))
            # Procesado del archivo de aspectos del PEC
            pec = PEC.objects.get(entidad=g_e.ronda.entidad)
            c = render_to_string('aspectos_generales_pec2pdf.html', {'pec': pec})
            ruta = rutas_pec(pec)['absoluta']
            nombre_fichero = 'aspectos_generales_pec'
            if os.path.exists('%s%s.pdf' % (ruta, nombre_fichero)):
                os.remove('%s%s.pdf' % (ruta, nombre_fichero))
            html_to_pdf(request, c, fichero=nombre_fichero, media=ruta, title='Aspectos Generales del PEC')
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
            # except:
            #     pass

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
            except:
                return JsonResponse({'ok': False})
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

def reordenar_saberes(saber, valor):
    borrar_saber = True if valor > 999 else False
    progsec = saber.psec
    orden_saber = saber.orden
    saberes = progsec.saberbas_set.exclude(id=saber.id)
    num_saberes = saberes.count() + 1
    valor = num_saberes if valor > num_saberes else valor
    if valor > orden_saber:
        nuevo_orden = 0
        for s in saberes.filter(orden__lte=valor):
            nuevo_orden += 1
            s.orden = nuevo_orden
            s.save()
    if valor < orden_saber:
        nuevo_orden = valor
        for s in saberes.filter(orden__gte=valor):
            nuevo_orden += 1
            s.orden = nuevo_orden
            s.save()
    saber.orden = valor
    saber.save()
    if borrar_saber:
        saber.delete()
    return render_to_string('progsec_accordion_content_saberes.html', {'progsec': progsec})


@permiso_required('acceso_progsecundaria')
def progsecundaria(request):
    try:
        g_e = request.session['gauser_extra']
        g_ep, c = Gauser_extra_programaciones.objects.get_or_create(ge=g_e)
        if c:
            g_ep.puesto = g_e.puesto
            g_ep.save()
        pga, c = PGA.objects.get_or_create(ronda=g_e.ronda)
        if g_e.has_permiso('ve_todas_programaciones'):
            progsecs = ProgSec.objects.filter(pga=pga)
        else:
            progsecs = ProgSec.objects.filter(pga=pga, gep=g_ep)
        if request.method == 'POST' and request.is_ajax():
            action = request.POST['action']
            if action == 'crea_progsec':
                try:
                    if g_e.has_permiso('crea_programaciones'):
                        # materia = Materia.objects.get(id=request.POST['materia'])
                        # mp, c = Materia_programaciones.objects.get_or_create(materia=materia)
                        areamateria = AreaMateria.objects.get(id=request.POST['areamateria'])
                        curso = Curso.objects.get(id=request.POST['curso'], ronda=g_e.ronda)
                        progsec = ProgSec.objects.create(pga=pga, gep=g_ep, areamateria=areamateria, curso=curso)
                        DocProgSec.objects.get_or_create(psec=progsec, gep=g_ep, permiso='X')
                        for ce in areamateria.competenciaespecifica_set.all():
                            cepsec = CEProgSec.objects.create(psec=progsec, ce=ce)
                            for cev in ce.criterioevaluacion_set.all():
                                CEvProgSec.objects.create(cepsec=cepsec, cev=cev)
                        html = render_to_string('progsec_accordion.html',
                                                {'buscadas': False, 'progsecs': [progsec], 'g_e': g_e, 'nueva': True})
                        return JsonResponse({'ok': True, 'html': html})
                    else:
                        JsonResponse({'ok': False, 'msg': 'Sin permiso'})
                except Exception as msg:
                    return JsonResponse({'ok': False, 'msg': str(msg)})
            elif action == 'open_accordion':
                try:
                    progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                                  id=request.POST['id'])
                    docentes_id = DocProgSec.objects.filter(psec=progsec).values_list('gep__ge', flat=True)
                    departamentos = Departamento.objects.filter(ronda=g_e.ronda)
                    if departamentos.count() == 0:
                        crea_departamentos(g_e.ronda)
                        departamentos = Departamento.objects.filter(ronda=g_e.ronda)
                    html = render_to_string('progsec_accordion_content.html',
                                            {'progsec': progsec, 'gep': g_ep, 'departamentos': departamentos,
                                             'docentes': profesorado(g_e.ronda.entidad), 'docentes_id': docentes_id})
                    return JsonResponse({'ok': True, 'html': html})
                except:
                    return JsonResponse({'ok': False})
            elif action == 'borrar_progsec':
                try:
                    progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                                  id=request.POST['id'])
                    permiso = progsec.get_permiso(g_ep)
                    if permiso == 'X':
                        progsec.delete()
                        return JsonResponse({'ok': True})
                    else:
                        return JsonResponse({'ok': False, 'msg': permiso})
                except Exception as msg:
                    return JsonResponse({'ok': False, 'msg': str(msg)})
            elif action == 'update_texto':
                try:
                    progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                                  id=request.POST['id'])
                    permiso = progsec.get_permiso(g_ep)
                    if permiso in 'EX':
                        texto = request.POST['texto']
                        setattr(progsec, request.POST['campo'], texto)
                        progsec.save()
                        return JsonResponse({'ok': True, 'progsec': progsec.id, 'html': texto})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
                except Exception as msg:
                    return JsonResponse({'ok': False, 'msg': str(msg)})
            elif action == 'select_departamento':
                try:
                    progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                                  id=request.POST['id'])
                    permiso = progsec.get_permiso(g_ep)
                    if permiso in 'EX':
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
                    if permiso in 'EX':
                        ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['jefe'])
                        departamento = progsec.departamento
                        geps = departamento.gauser_extra_programaciones_set.all()
                        for gep in geps.filter(jefe=True):
                            gep.jefe = False
                            try:
                                dps = DocProgSec.objects.get(gep=gep, psec=progsec)
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
                    if permiso in 'EX':
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
            elif action == 'update_pesocep':
                try:
                    progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                                  id=request.POST['id'])
                    permiso = progsec.get_permiso(g_ep)
                    if permiso in 'EX':
                        cep = CEProgSec.objects.get(psec=progsec, id=request.POST['cep'])
                        cep.valor = int(request.POST['cep_peso'])
                        cep.save()
                        return JsonResponse({'ok': True, 'progsec': progsec.id})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
                except Exception as msg:
                    return JsonResponse({'ok': False, 'msg': str(msg)})
            elif action == 'update_pesocevp':
                try:
                    progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                                  id=request.POST['id'])
                    permiso = progsec.get_permiso(g_ep)
                    if permiso in 'EX':
                        cevp = CEvProgSec.objects.get(cepsec__psec=progsec, id=request.POST['cevp'])
                        cevp.valor = int(request.POST['cevp_peso'])
                        cevp.save()
                        return JsonResponse({'ok': True, 'progsec': progsec.id})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
                except Exception as msg:
                    return JsonResponse({'ok': False, 'msg': str(msg)})
            elif action == 'cargar_libro':
                try:
                    progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                                  id=request.POST['id'])
                    permiso = progsec.get_permiso(g_ep)
                    if permiso in 'EX':
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
                    if permiso in 'EX':
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
                    if permiso in 'EX':
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
                    if permiso in 'EX':
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
                    if permiso in 'EX':
                        orden = progsec.saberbas_set.all().count() + 1
                        saber = SaberBas.objects.create(psec=progsec, orden=orden)
                        html = render_to_string('progsec_accordion_content_saberes_tr.html', {'saber': saber})
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
                    if permiso in 'EX':
                        html = None
                        saber = progsec.saberbas_set.get(id=request.POST['saber'])
                        campo = request.POST['campo']
                        if campo == 'nombre':
                            valor = request.POST['valor']
                        else:
                            valor = int(request.POST['valor'])
                        if campo == 'orden':
                            html = reordenar_saberes(saber, valor)
                        else:
                            setattr(saber, campo, valor)
                            saber.save()
                        return JsonResponse({'ok': True, 'html': html})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
                except Exception as msg:
                    return JsonResponse({'ok': False, 'msg': str(msg)})
            elif action == 'borrar_saber':
                try:
                    progsec = ProgSec.objects.get(gep__ge__ronda__entidad=g_e.ronda.entidad,
                                                  id=request.POST['id'])
                    permiso = progsec.get_permiso(g_ep)
                    if permiso in 'EX':
                        saber = progsec.saberbas_set.get(id=request.POST['saber'])
                        saber_id = saber.id
                        html = reordenar_saberes(saber, 1000)  # Si orden es > que 999 el saber se borra
                        return JsonResponse({'ok': True, 'saber_id': saber_id, 'html': html})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'No tiene permiso'})
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
                                                            content_type=fichero.content_type,
                                                            tipo=request.POST['name'])
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

        cursos = Curso.objects.filter(ronda=g_e.ronda)
        if cursos.count() == 0:
            Curso.objects.create(ronda=g_e.ronda, nombre="Curso genérico de ESO")
            Curso.objects.create(ronda=g_e.ronda, nombre="Curso genérico de Primaria")
            Curso.objects.create(ronda=g_e.ronda, nombre="Curso genérico de Bachillerato")
            Curso.objects.create(ronda=g_e.ronda, nombre="Curso genérico de Infantil")
            cursos = Curso.objects.filter(ronda=g_e.ronda)

        return render(request, "progsec.html",
                      {
                          'formname': 'progsec',
                          'iconos':
                              ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Crear',
                                'title': 'Crear una nueva programación de una materia de secundaria',
                                'permiso': 'libre'},
                               {'tipo': 'button', 'nombre': 'search', 'texto': 'Buscar',
                                'title': 'Buscar programación a través del nombre de la materia de secundaria',
                                'permiso': 'libre'},
                               ),
                          'g_e': g_e,
                          'progsecs': progsecs,
                          'cursos': cursos,
                          'areasmateria': AreaMateria.objects.all(),
                          'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)
                      })
    except Exception as msg:
        return HttpResponse(str(msg))


@permiso_required('acceso_progsecundaria')
def progsecundaria_sb(request, id):
    g_e = request.session['gauser_extra']
    g_ep = Gauser_extra_programaciones.objects.get(ge=g_e)
    pga = PGA.objects.get(ronda=g_e.ronda)
    sb = SaberBas.objects.get(psec__pga=pga, id=id)
    permiso = sb.psec.get_permiso(g_ep)
    if permiso not in 'LEX':
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
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'open_accordion':
            try:
                sap = SitApren.objects.get(sbas__psec__gep__ge__ronda__entidad=g_e.ronda.entidad,
                                           id=request.POST['id'])
                html = render_to_string('progsec_sap_accordion_content.html', {'sap': sap, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_texto':
            try:
                clase = eval(request.POST['clase'])
                objeto = clase.objects.get(id=request.POST['id'])
                setattr(objeto, request.POST['campo'], request.POST['texto'])
                objeto.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_select':
            try:
                clase = eval(request.POST['clase'])
                objeto = clase.objects.get(id=request.POST['id'])
                setattr(objeto, request.POST['campo'], request.POST['valor'])
                objeto.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
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
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_sap_actividad':
            try:
                sap = sb.sitapren_set.get(id=request.POST['sap'])
                act = ActSitApren.objects.create(sapren=sap, nombre='Nombre de la actividad')
                InstrEval.objects.create(asapren=act, tipo='TMONO', nombre='Procedimiento 1')
                html = render_to_string('progsec_sap_accordion_content_act.html', {'actividad': act})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'borrar_sap_actividad':
            try:
                act = ActSitApren.objects.get(id=request.POST['id'])
                if act.sapren.actsitapren_set.all().count() > 1:
                    if act.sapren.sbas == sb:
                        act.delete()
                    return JsonResponse({'ok': True})
                else:
                    msg = 'No es posible borrar. Al menos, debe existir una actividad.'
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'add_act_instrumento':
            try:
                act = ActSitApren.objects.get(id=request.POST['act'])
                if act.sapren.sbas == sb:
                    inst = InstrEval.objects.create(asapren=act, nombre='Nombre del instrumento')
                    html = render_to_string('progsec_sap_accordion_content_act_proc.html', {'instrumento': inst})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    JsonResponse({'ok': False, 'msg': 'Error en la relación sb-instrumento'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'borrar_act_instrumento':
            try:
                inst = InstrEval.objects.get(id=request.POST['id'])
                if inst.asapren.instreval_set.all().count() > 1:
                    if inst.asapren.sapren.sbas == sb:
                        inst.delete()
                    return JsonResponse({'ok': True})
                else:
                    msg = 'No es posible borrar. Al menos, debe existir un procedimiento de evaluación.'
                    return JsonResponse({'ok': False, 'msg': msg})
            except:
                return JsonResponse({'ok': False})
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
                      'formname': 'progsec',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Crear SAP', 'permiso': 'libre',
                            'title': 'Crear una nueva situación de aprendizaje para este saber básico'},
                           {'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Volver', 'permiso': 'libre',
                            'title': 'Volver a la programación didáctica'},
                           ),
                      'g_e': g_e,
                      'sb': sb,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@permiso_required('acceso_cuaderno_docente')
def cuadernodocente(request):
    g_e = request.session['gauser_extra']
    g_ep = Gauser_extra_programaciones.objects.get(ge=g_e)
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'crea_cuaderno':
            try:
                if DocProgSec.objects.filter(psec__pga__ronda=g_e.ronda).count() < 1:
                    msg = 'Primero tienes que participar como docente en alguna programación didáctica.'
                    return JsonResponse({'ok': False, 'msg': msg})
                cuaderno = CuadernoProf.objects.create(ge=g_e)
                html = render_to_string('cuadernodocente_accordion.html', {'cuaderno': cuaderno})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'open_accordion':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['id'])
                cievals = CriInstrEval.objects.filter(ieval__asapren__sapren__sbas__psec=cuaderno.psec)
                for alumno in cuaderno.alumnos.all():
                    for cieval in cievals:
                        ecp = EscalaCP.objects.get(cp=cuaderno, ieval=cieval.ieval)
                        CalAlum.objects.get_or_create(cp=cuaderno, alumno=alumno, cie=cieval, ecp=ecp)
                html = render_to_string('cuadernodocente_accordion_content.html', {'cuaderno': cuaderno})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'select_psec':
            try:
                psec = ProgSec.objects.get(id=request.POST['psec'])
                try:
                    DocProgSec.objects.get(gep__ge=g_e, psec=psec)
                    grupos = psec.curso.grupos
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
                cuaderno.save()
                cuaderno.alumnos.add(*cuaderno.grupo.gauser_extra_estudios_set.all().values_list('ge', flat=True))
                html = render_to_string('cuadernodocente_accordion_content.html', {'cuaderno': cuaderno})
                return JsonResponse({'ok': True, 'html': html, 'nombre': cuaderno.nombre})
            except:
                return JsonResponse({'ok': False})
        elif action == 'define_ecp':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                ieval = InstrEval.objects.get(id=request.POST['ieval'], asapren__sapren__sbas__psec=cuaderno.psec)
                ecp, c = EscalaCP.objects.get_or_create(cp=cuaderno, ieval=ieval)
                html = render_to_string('cuadernodocente_accordion_content_ecp.html', {'ecp': ecp})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_texto':
            try:
                clase = eval(request.POST['clase'])
                objeto = clase.objects.get(id=request.POST['id'])
                setattr(objeto, request.POST['campo'], request.POST['texto'])
                objeto.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
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
                    casillas = [{'x': i, 'y': 0, 't': i + 1, 'valor': i + 1} for i in range(0, 10)]
                    for c in casillas:
                        EscalaCPvalor.objects.create(ecp=objeto, x=c['x'], y=c['y'], valor=c['valor'],
                                                     texto_cualitativo=c['t'])
                html = render_to_string('cuadernodocente_accordion_content_ecp.html', {'ecp': objeto})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_row_ecp':
            try:
                ecp = EscalaCP.objects.get(id=request.POST['ecp'], cp__ge=g_e)
                nueva_row_index = max(ecp.get_ecpvys) + 1
                if ecp.tipo == 'LCONT':
                    columns_index = ecp.escalacpvalor_set.filter(y=0).values_list('x', 'valor')
                    for x, valor in columns_index:
                        EscalaCPvalor.objects.create(ecp=ecp, x=x, y=nueva_row_index,
                                                     texto_cualitativo='', valor=valor)
                else:
                    columns_index = ecp.escalacpvalor_set.filter(y=0).values_list('x', flat=True)
                    for x in columns_index:
                        EscalaCPvalor.objects.create(ecp=ecp, x=x, y=nueva_row_index,
                                                     texto_cualitativo='Texto', valor=0)
                html = render_to_string('cuadernodocente_accordion_content_ecp.html', {'ecp': ecp})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_column_ecp':
            try:
                ecp = EscalaCP.objects.get(id=request.POST['ecp'], cp__ge=g_e)
                rows_index = ecp.get_ecpvys
                nueva_column_index = max(ecp.escalacpvalor_set.filter(y=0).values_list('x', flat=True)) + 1
                for i in rows_index:
                    EscalaCPvalor.objects.get_or_create(ecp=ecp, y=i, x=nueva_column_index,
                                                        texto_cualitativo='Texto', valor=0)
                html = render_to_string('cuadernodocente_accordion_content_ecp.html', {'ecp': ecp})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'del_rc_ecp':
            try:
                ecp = EscalaCP.objects.get(id=request.POST['ecp'], cp__ge=g_e)
                if request.POST['borrar'] == 'x':
                    ecp.escalacpvalor_set.filter(x=request.POST['i']).delete()
                else:
                    ecp.escalacpvalor_set.filter(y=request.POST['i']).delete()
                html = render_to_string('cuadernodocente_accordion_content_ecp.html', {'ecp': ecp})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_calalum':
            try:
                cuaderno = CuadernoProf.objects.get(ge__gauser=g_e.gauser, id=request.POST['cuaderno'])
                cieval = CriInstrEval.objects.get(id=request.POST['cieval'],
                                                  ieval__asapren__sapren__sbas__psec=cuaderno.psec)
                alumno = Gauser_extra.objects.get(id=request.POST['alumno'], ronda=g_e.ronda)
                ecp, c = EscalaCP.objects.get_or_create(cp=cuaderno, ieval=cieval.ieval)
                ca, c = CalAlum.objects.get_or_create(cp=cuaderno, alumno=alumno, cie=cieval, ecp=ecp)
                html = render_to_string('cuadernodocente_accordion_content_calalum.html', {'calalum': ca})
                return JsonResponse({'ok': True, 'html': html, 'calalum': ca.id, 'alumno': alumno.id, 'cal': ca.cal})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_esvcl':
            try:
                ecpv = EscalaCPvalor.objects.get(id=request.POST['ecpv'], ecp__cp__ge=g_e)
                ca = CalAlum.objects.get(id=request.POST['calalum'], ecp=ecpv.ecp)
                cav, c = CalAlumValor.objects.get_or_create(ca=ca, ecpv=ecpv)
                if c:
                    return JsonResponse({'ok': True, 'alumno': ca.alumno.id, 'selected': True, 'cal': ca.cal})
                else:
                    cav.delete()
                    return JsonResponse({'ok': True, 'alumno': ca.alumno.id, 'selected': False, 'cal': ca.cal})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_lcont':
            try:
                ecpv = EscalaCPvalor.objects.get(id=request.POST['ecpv'], ecp__cp__ge=g_e)
                ecpv.valor = ecpv.ecp.escalacpvalor_set.get(y=0, x=ecpv.x).valor
                ecpv.save()
                ca = CalAlum.objects.get(id=request.POST['calalum'], ecp=ecpv.ecp)
                cav, c = CalAlumValor.objects.get_or_create(ca=ca, ecpv=ecpv)
                if c:
                    ca.calalumvalor_set.filter(ecpv__y=ecpv.y).exclude(ecpv=ecpv).delete()
                return JsonResponse({'ok': True, 'alumno': ca.alumno.id, 'cal': ca.cal})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_esvcn':
            try:
                ca = CalAlum.objects.get(id=request.POST['calalum'])
                ca.calalumvalor_set.all().delete()
                valor = float(request.POST['valor'])
                ecpv, c = EscalaCPvalor.objects.get_or_create(ecp=ca.ecp, ecp__cp__ge=g_e, valor=valor)
                for idx, e in enumerate(ca.ecp.escalacpvalor_set.all().order_by('valor')):
                    e.y = idx
                    e.save()
                CalAlumValor.objects.create(ca=ca, ecpv=ecpv)
                return JsonResponse({'ok': True, 'alumno': ca.alumno.id, 'cal': ca.cal})
            except:
                return JsonResponse({'ok': False})
        elif action == 'gestionar_alumnos':
            try:
                cuaderno = CuadernoProf.objects.get(id=request.POST['cuaderno'], ge=g_e)
                html = render_to_string('cuadernodocente_accordion_content_ga.html', {'cuaderno': cuaderno})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif action == 'update_alumnos_cuaderno':
            try:
                cuaderno = CuadernoProf.objects.get(id=request.POST['cuaderno'], ge=g_e)
                alumno = Gauser_extra.objects.get(id=int(request.POST['alumno'][1:]), ronda=g_e.ronda)
                if alumno not in cuaderno.alumnos.all():
                    cievals = CriInstrEval.objects.filter(ieval__asapren__sapren__sbas__psec=cuaderno.psec)
                    for cieval in cievals:
                        ecp = EscalaCP.objects.get(cp=cuaderno, ieval=cieval.ieval)
                        CalAlum.objects.get_or_create(cp=cuaderno, alumno=alumno, cie=cieval, ecp=ecp)
                    html_span = render_to_string('cuadernodocente_accordion_content_ga_alumno.html',
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
                cuaderno.alumnos.remove(alumno)
                return JsonResponse({'ok': True, 'cuaderno': cuaderno.id, 'alumno': alumno.id,
                                     'num_alumnos': cuaderno.alumnos.all().count()})
            except:
                return JsonResponse({'ok': False})
    return render(request, "cuadernodocente.html",
                  {
                      'formname': 'progsec',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Crear Cuaderno', 'permiso': 'libre',
                            'title': 'Crear un nuevo cuaderno de profesor asociado a una programación'},
                           ),
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })
