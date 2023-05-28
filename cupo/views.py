# -*- coding: utf-8 -*-
import logging
# import datetime
import os
import random

import xlwt
import xlrd
from time import sleep
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.text import slugify
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.utils.timezone import datetime

from autenticar.control_acceso import permiso_required
from cupo.templatetags.cupo_extras import get_columnas_docente, get_columnas_departamento, get_apartados, get_columnas, \
    get_columnas_edb
from entidades.templatetags.entidades_extras import puestos_especialidad
from gauss.funciones import pass_generator, genera_pdf, get_dce
from gauss.rutas import *
from django.http import HttpResponse, FileResponse
from django.db.models import Q
from django.template.loader import render_to_string

from horarios.models import SesionExtra, Horario, Sesion
from mensajes.models import Aviso
from mensajes.views import crear_aviso
from cupo.models import Cupo, Materia_cupo, Profesores_cupo, FiltroCupo, EspecialidadCupo, Profesor_cupo, GrupoExcluido, \
    CursoCupo, EtapaEscolarCupo, CupoPermisos, CargaPlantillaOrganicaCentros, EspecialidadPlantilla, PDocente, CUERPOS
from cupo.models import PlantillaOrganica, PDocenteCol
from cupo.habilitar_permisos import ESPECIALIDADES
from entidades.models import CargaMasiva, Gauser_extra, MiembroDepartamento, Especialidad_funcionario, Entidad, \
    EspecialidadDocenteBasica, Cargo, MiembroEDB, DocConfEntidad, Ronda
from entidades.models import Departamento as Depentidad
from entidades.tasks import carga_masiva_from_excel
from estudios.models import Curso, Materia, Grupo, EtapaEscolar, Gauser_extra_estudios
# from horarios.tasks import carga_masiva_from_file

from programaciones.models import Gauser_extra_programaciones, Departamento, crea_departamentos

logger = logging.getLogger('django')

# Algunos cuerpos contienen las mismas especialidades, por ejemplo 590 (profe secundaria) y 511 (catedrático secund.)
# Para el cupo únicamente importa la especialidad así que para evitar duplicidades en las especialidades
# se toman únicamente los siguientes cuerpos:
CUERPOS_CUPO = ('590', '591', '592', '593', '594', '595', '596')


def get_dce_cupo(g_e):
    doc_progsec = 'Configuración de informe de cupo'
    try:
        dce = DocConfEntidad.objects.get(entidad=g_e.ronda.entidad, nombre=doc_progsec)
    except:
        try:
            dce = DocConfEntidad.objects.get(entidad=g_e.ronda.entidad, predeterminado=True)
        except:
            dce = DocConfEntidad.objects.filter(entidad=g_e.ronda.entidad)[0]
            dce.predeterminado = True
            dce.save()
        dce.pk = None
        dce.nombre = doc_progsec
        dce.predeterminado = False
        dce.editable = False
        dce.save()
    return dce


# @permiso_required('acceso_cupo_profesorado')
def cupo(request):
    g_e = request.session['gauser_extra']
    if 'c' in request.GET:
        cupo_selected = request.GET['c']
    else:
        cupo_selected = None
    # ##########################################
    for ec in EspecialidadCupo.objects.filter(max_media=9, min_media=10):
        ec.max_media = 10
        ec.min_media = 9
        ec.save()
    # ##########################################

    if request.method == 'POST':
        if request.POST['action'] == 'genera_informe':
            cupo = Cupo.objects.get(id=request.POST['cupo'])
            if cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='l').count() > 0:
                dce = get_dce_cupo(g_e)
                c = render_to_string('cupo2pdf.html', {'cupo': cupo, 'dce': dce})
                genera_pdf(c, dce)
                nombre = slugify('cupo%s_%s' % (str(cupo.ronda.entidad.code), cupo.id))
                return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename=nombre + '.pdf',
                                    content_type='application/pdf')
                # pdfkit.from_string(c, dce.url_pdf, dce.get_opciones)
                # fich = open(dce.url_pdf, 'rb')
                # response = HttpResponse(fich, content_type='application/pdf')
                # nombre = 'cupo%s_%s' % (str(cupo.ronda.entidad.code), cupo.id)
                # response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(nombre)
                # return response
            else:
                crear_aviso(request, False, 'No tienes permiso para generar del archivo pdf solicitado')
        elif request.POST['action'] == 'genera_informeRRHH':
            cupo = Cupo.objects.get(id=request.POST['cupo'])
            interinos = Profesor_cupo.objects.filter(profesorado__cupo=cupo, tipo='INT')
            q1 = Q(profesorado__especialidad__cod_espec='')
            q2 = Q(profesorado__especialidad__cod_cuerpo='')
            con1 = interinos.filter(q1 | q2).count() > 0
            con2 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='l').count() > 0
            if not con1:
                if con2:
                    dce = get_dce_cupo(g_e)
                    c = render_to_string('cupoRRHH2pdf.html', {'cupo': cupo, 'dce': dce})
                    genera_pdf(c, dce)
                    nombre = slugify('cupoRRHH%s_%s' % (str(cupo.ronda.entidad.code), cupo.id))
                    return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename=nombre + '.pdf',
                                        content_type='application/pdf')
                    # pdfkit.from_string(c, dce.url_pdf, dce.get_opciones)
                    # fich = open(dce.url_pdf, 'rb')
                    # response = HttpResponse(fich, content_type='application/pdf')
                    # nombre = 'cupoRRHH%s_%s' % (str(cupo.ronda.entidad.code), cupo.id)
                    # response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(nombre)
                    # return response
                else:
                    crear_aviso(request, False, 'No tienes permiso para generar del archivo pdf solicitado')
            else:
                msg = 'Hay especialidades en las que no se ha configurado el código del cuerpo o de la propia especialidad'
                crear_aviso(request, False, msg)
        elif request.POST['action'] == 'genera_excel':
            cupo = Cupo.objects.get(id=request.POST['cupo'])
            if cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='l').count() > 0:
                ruta = '%s%s/%s' % (MEDIA_CUPO, slugify(cupo.ronda.entidad.code), slugify(cupo.ronda.nombre))
                if not os.path.exists(ruta):
                    os.makedirs(ruta)
                fichero_xls = '%s.xls' % slugify(cupo.nombre)
                wb = xlwt.Workbook()
                wc = wb.add_sheet('Cupo')
                fila_excel_cupo = 0
                estilo = xlwt.XFStyle()
                font = xlwt.Font()
                font.bold = True
                estilo.font = font
                for i in range(10):
                    wc.col(i).width = 6000
                wc.write(fila_excel_cupo, 0, 'CENTRO', style=estilo)
                wc.write(fila_excel_cupo, 1, 'LOCALIDAD', style=estilo)
                wc.write(fila_excel_cupo, 2, 'CUERPO', style=estilo)
                wc.write(fila_excel_cupo, 3, 'ESPECIALIDAD', style=estilo)
                wc.write(fila_excel_cupo, 4, 'CARÁCTER (C)', style=estilo)
                wc.write(fila_excel_cupo, 5, 'CARÁCTER (P)', style=estilo)
                wc.write(fila_excel_cupo, 6, 'CARÁCTER (I)', style=estilo)
                wc.write(fila_excel_cupo, 7, 'CARÁCTER (N)', style=estilo)
                wc.write(fila_excel_cupo, 8, 'OBSERVACIONES', style=estilo)
                wc.write(fila_excel_cupo, 9, 'MOTIVACIÓN', style=estilo)
                interinos = Profesor_cupo.objects.filter(profesorado__cupo=cupo, tipo='INT').order_by(
                    'profesorado__especialidad')
                for p in interinos:
                    fila_excel_cupo += 1
                    wc.write(fila_excel_cupo, 0, cupo.ronda.entidad.name)
                    wc.write(fila_excel_cupo, 1, cupo.ronda.entidad.localidad)
                    wc.write(fila_excel_cupo, 2, '')
                    wc.write(fila_excel_cupo, 3, p.profesorado.especialidad.nombre)
                    if p.jornada == '1':
                        wc.write(fila_excel_cupo, 4, p.get_jornada_display())
                    else:
                        wc.write(fila_excel_cupo, 5, p.get_jornada_display())
                    if p.itinerante:
                        wc.write(fila_excel_cupo, 6, 'Sí')
                    if p.noafin:
                        wc.write(fila_excel_cupo, 7, 'Sí')
                    if p.bilingue:
                        wc.write(fila_excel_cupo, 8, 'Es bilingüe')
                    wc.write(fila_excel_cupo, 9, p.observaciones)
                wb.save(ruta + fichero_xls)
                xlsfile = open(ruta + fichero_xls, 'rb')
                response = FileResponse(xlsfile, content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s' % fichero_xls
                return response
            else:
                crear_aviso(request, False, 'No tienes permiso para generar del archivo excel solicitado')

    cupos_id = CupoPermisos.objects.filter(gauser=g_e.gauser).values_list('cupo__id', flat=True)
    f = datetime(2021, 1, 1)
    # cupos = Cupo.objects.filter(Q(creado__gt=f), Q(ronda__entidad=g_e.ronda.entidad) | Q(id__in=cupos_id)).distinct()
    cupos = Cupo.objects.filter(Q(creado__gt=f), Q(id__in=cupos_id)).distinct()
    try:
        cargo_inspector = Cargo.objects.get(entidad=g_e.ronda.entidad, clave_cargo='g_inspector_educacion')
    except:
        cargo_inspector = Cargo.objects.none()
    if cargo_inspector:
        entidades = Entidad.objects.all()
        plantillas_o = []
        for e in entidades:
            try:
                # po = PlantillaOrganica.objects.filter(ronda_centro__entidad=e).order_by('creado').last()
                po = PlantillaOrganica.objects.filter(ronda_centro__entidad=e).latest('creado')
                if po:
                    plantillas_o.append(po)
            except:
                pass
    else:
        plantillas_o = PlantillaOrganica.objects.filter(Q(g_e__gauser=g_e.gauser) | Q(ronda_centro=g_e.ronda))
    cursos_existentes = Curso.objects.filter(ronda__entidad__organization=g_e.ronda.entidad.organization,
                                             clave_ex__isnull=False).values_list('clave_ex', 'nombre').distinct()
    return render(request, "cupo.html",
                  {'iconos':
                       ({'tipo': 'button', 'nombre': 'info-circle', 'texto': 'Información',
                         'title': 'Información sobre la creación de nuevos cupos.',
                         'permiso': 'libre'}, {},
                        ),
                   'formname': 'cupo_profesorado',
                   'cupos': cupos,
                   'cupo_selected': cupo_selected,
                   'g_e': g_e,
                   'plantillas_o': plantillas_o,
                   'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                   'especialidades_existentes': ESPECIALIDADES,
                   'cursos_existentes': cursos_existentes})


def select_po(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        if request.method == 'GET':
            texto = request.GET['q']
            entidades = Entidad.objects.filter(name__icontains=texto)
            options = []
            for e in entidades:
                try:
                    po = PlantillaOrganica.objects.filter(ronda_centro__entidad=e).order_by('creado').last()
                    options.append({'id': po.id, 'param0': po.ronda_centro.entidad.name,
                                    'param1': po.creado.strftime('%d/%m/%Y a las %H:%M'), 'param2': '', 'param3': ''})
                except:
                    pass
            return JsonResponse(options, safe=False)


def cupo_especialidad(cupo, especialidad):
    materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=especialidad)
    profesores_cupo = Profesores_cupo.objects.get(cupo=cupo, especialidad=especialidad)
    profesores_cupo.num_horas = sum([m.total_periodos for m in materias_cupo])
    profesores_cupo.save()
    return profesores_cupo


def ajax_cupo(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        action = request.POST['action']
        if action == 'open_accordion':
            try:
                cupo = Cupo.objects.get(id=request.POST['id'])
                cexs = Curso.objects.filter(ronda__entidad__organization=g_e.ronda.entidad.organization,
                                            clave_ex__isnull=False).values_list('clave_ex', 'nombre').distinct()
                activa_pub_rrhh, msg = cupo.puede_activarse_pub_rrhh(g_e)
                rondas = Ronda.objects.filter(nombre__icontains='/%s' % datetime.today().year)
                html = render_to_string('cupo_accordion_content.html', {'cupo': cupo, 'cursos_existentes': cexs,
                                                                        'especialidades_existentes': ESPECIALIDADES,
                                                                        'request': request, 'aprrhh': activa_pub_rrhh,
                                                                        'rondas': rondas, 'msg': msg})
                return JsonResponse({'ok': True, 'html': html, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'add_cupo' and g_e.has_permiso('crea_cupos'):
            try:
                crea_departamentos(g_e.ronda)
                fecha_hora = datetime.now().strftime('%d-%m-%Y %H:%M')
                nombre = '%s - Cupo creado el %s' % (g_e.ronda.entidad.name, fecha_hora)
                cupo = Cupo.objects.create(ronda=g_e.ronda, nombre=nombre)
                CupoPermisos.objects.create(cupo=cupo, gauser=g_e.gauser, permiso='plwx')
                geps = Gauser_extra_programaciones.objects.filter(ge__ronda=cupo.ronda).order_by('puesto')
                for pd in geps.values_list('puesto', 'departamento__id').distinct():
                    if pd[0]:
                        ec, c = EspecialidadCupo.objects.get_or_create(cupo=cupo, nombre=pd[0])
                        if c and pd[1]:
                            departamento = Departamento.objects.get(ronda=cupo.ronda, id=pd[1])
                            ec.departamento = departamento
                            ec.save()
                        profesores_cupo, created = Profesores_cupo.objects.get_or_create(cupo=cupo, especialidad=ec)
                        if created:
                            geps = Gauser_extra_programaciones.objects.filter(ge__ronda=cupo.ronda, puesto=ec.nombre)
                            for gep in geps:
                                tipo = 'INT' if 'nterino' in gep.ge.tipo_personal else 'DEF'
                                try:
                                    jornada_calculada = int(gep.ge.jornada_contratada.split(':')[0])
                                    if jornada_calculada > 20:
                                        jornada = '1'
                                    elif jornada_calculada > 14 and jornada_calculada < 20:
                                        jornada = '2'
                                    elif jornada_calculada > 9 and jornada_calculada < 13:
                                        jornada = '3'
                                    else:
                                        jornada = '4'
                                except:
                                    jornada = '1'
                                Profesor_cupo.objects.create(profesorado=profesores_cupo, tipo=tipo, jornada=jornada,
                                                             nombre=gep.ge.gauser.get_full_name())
                for etapa in EtapaEscolar.objects.all():
                    EtapaEscolarCupo.objects.get_or_create(cupo=cupo, nombre=etapa.nombre, clave_ex=etapa.clave_ex)
                materias = Materia.objects.filter(curso__ronda=cupo.ronda)
                for m in materias:
                    try:
                        etapa = EtapaEscolarCupo.objects.get(clave_ex=m.curso.etapa_escolar.clave_ex)
                    except:
                        etapa = None
                    try:
                        curso_nombre = m.curso.nombre
                    except:
                        curso_nombre = ''
                    try:
                        curso_tipo = m.curso.tipo
                    except:
                        curso_tipo = ''
                    try:
                        curso_nombre_esp = m.curso.nombre_especifico
                    except:
                        curso_nombre_esp = ''
                    try:
                        curso_clave_ex = m.curso.clave_ex
                    except:
                        curso_clave_ex = ''
                    cc, c = CursoCupo.objects.get_or_create(cupo=cupo, nombre=curso_nombre, etapa_escolar=etapa,
                                                            tipo=curso_tipo,
                                                            nombre_especifico=curso_nombre_esp, clave_ex=curso_clave_ex)
                    try:
                        horas = m.horas
                    except:
                        horas = 0
                    Materia_cupo.objects.create(cupo=cupo, curso_cupo=cc, nombre=m.nombre, periodos=horas)
                logger.info('%s, add_cupo id=%s' % (g_e, cupo.id))
                html = render_to_string('cupo_accordion.html', {'cupo': cupo})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif action == 'crea_cupo_from_po' and g_e.has_permiso('crea_cupos'):
            try:
                centros_primaria = ['C.E.E. - Centro de Educación Especial',
                                    'C.R.A. - Colegio Rural Agrupado',
                                    'C.E.I.P. - Colegio de Educación Infantil y Primaria']
                # condiciones = Q(id=request.POST['po']) & (Q(g_e=g_e) | Q(ronda_centro__entidad__organization=g_e.ronda.entidad.organization))
                condiciones = Q(id=request.POST['po'])
                po = PlantillaOrganica.objects.get(condiciones)
                po.habilitar_miembros_equipo_directivo()
                # if 'I.E.S' in po.ronda_centro.entidad.entidadextra.tipo_centro:
                #     J = {'cmax': 20, 'cmin': 18, 'mmax': 10, 'mmin': 9, 'dmax': 13, 'dmin': 12, 'umax': 7, 'umin': 6}
                # else:
                #     J = {'cmax': 24, 'cmin': 24, 'mmax': 12, 'mmin': 12, 'dmax': 16, 'dmin': 16, 'umax': 8, 'umin': 8}
                fecha_hora = datetime.now().strftime('%d-%m-%Y %H:%M')
                nombre = '%s - Cupo creado el %s' % (po.ronda_centro.entidad.name, fecha_hora)
                # cupo = Cupo.objects.create(ronda=po.ronda_centro, nombre=nombre, max_completa=J['cmax'],
                #                            min_completa=J['cmin'], max_dostercios=J['dmax'], min_dostercios=J['dmin'],
                #                            max_media=J['mmax'], min_media=J['mmin'], max_tercio=J['umax'],
                #                            min_tercio=J['umin'])
                cupo = Cupo.objects.create(ronda=po.ronda_centro, nombre=nombre)
                CupoPermisos.objects.create(cupo=cupo, gauser=g_e.gauser, permiso='plwx')
                # Crea filtros automáticos:
                # filtros = [('Materias Bilingües', 'bilingüe'), ('Reducciones por bilingüismo', 'cción biling'),
                #            ('Tutorías', 'Tutor'), ('Jefaturas de departamento', 'jefatur'),
                #            ('Reducciones mayores de 55 años', '55')]
                if po.ronda_centro.entidad.entidadextra.tipo_centro in centros_primaria:
                    filtros = [('Reducciones mayores de 55 años', '55'), ('Reducciones Equipo Directivo', '(ED)'),
                               ('Horas de apoyo al profesorado', 'apoyo')]
                else:
                    filtros = [('Tutorías', 'Tutor'), ('Jefaturas de departamento', 'atura de dep'),
                               ('Reducciones mayores de 55 años', '55'), ('Reducciones Equipo Directivo', '(ED)')]
                for filtro in filtros:
                    FiltroCupo.objects.create(cupo=cupo, nombre=filtro[0], filtro=filtro[1])
                # Especialidades, Etapas, Cursos, ...
                # EspecialidadCupo.objects.create(cupo=cupo, departamento=None, nombre='Orientación Educativa',
                #                                 clave_ex='17959', dep='Orientación', x_dep='95')
                for pxls in po.plantillaxls_set.all():
                    if po.ronda_centro.entidad.entidadextra.tipo_centro in centros_primaria:
                        mn = 25  # max_num_alumnos en caso de infantil y primaria
                    else:
                        mn = 30  # max_num_alumnos en el resto de casos
                    if pxls.x_puesto == '18429':
                        nombre_especialidad = 'Música de Primaria'
                    elif pxls.x_puesto == '18409':
                        nombre_especialidad = 'Educación Física de Primaria'
                    else:
                        nombre_especialidad = pxls.puesto
                    try:
                        # EspecialidadCupo.objects.get(cupo=cupo, clave_ex=pxls.x_puesto)
                        # Los x_puesto de un catedrático y de un docente son diferentes por lo que
                        # crea dos especialidades con el mismo nombre. Para evitar esto, se crea
                        # únicamente una especialidad obviando si es o no catedrático ya que en el cupo no
                        # tiene importancia.
                        # Ejemplos :    17769 -> Música catedrático; 17957 -> Música
                        #               17761 -> Biología y Geología catedrático; 17949 -> Biología y Geología
                        ec = EspecialidadCupo.objects.get(cupo=cupo, nombre=nombre_especialidad)
                    except:
                        maestros = ['18401', '18407', '18408', '18409', '18410', '18416', '18429', '18431', '18433',
                                    '18434']
                        if pxls.x_puesto in maestros:
                            # J = {'cmax': 21.5, 'cmin': 21.5, 'mmax': 10.75, 'mmin': 10.75, 'dmax': 14.33,
                            #      'dmin': 14.33, 'umax': 7.16, 'umin': 7.16}
                            # Las anteriores horas no tienen en cuenta el recreo, para tenerlo en cuenta:
                            J = {'cmax': 23, 'cmin': 23, 'mmax': 11.5, 'mmin': 11.5, 'dmax': 15.33,
                                 'dmin': 15.33, 'umax': 7.66, 'umin': 7.66}
                        else:
                            J = {'cmax': 20, 'cmin': 18, 'mmax': 10, 'mmin': 9, 'dmax': 13, 'dmin': 12, 'umax': 7,
                                 'umin': 6}
                        ec = EspecialidadCupo.objects.create(cupo=cupo, nombre=nombre_especialidad,
                                                             clave_ex=pxls.x_puesto, dep=pxls.departamento,
                                                             x_dep=pxls.x_departamento, max_completa=J['cmax'],
                                                             min_completa=J['cmin'], max_dostercios=J['dmax'],
                                                             min_dostercios=J['dmin'], max_media=J['mmax'],
                                                             min_media=J['mmin'], max_tercio=J['umax'],
                                                             min_tercio=J['umin'])
                        profesores_cupo = Profesores_cupo.objects.create(cupo=cupo, especialidad=ec)
                        # geps = po.plantillaxls_set.filter(x_puesto=pxls.x_puesto).values_list('docente', flat=True)
                        # for gep in list(set(geps)):
                        #   Profesor_cupo.objects.create(profesorado=profesores_cupo, nombre=gep)
                        geps = po.plantillaxls_set.filter(x_puesto=pxls.x_puesto).values_list('docente', 'x_docente')
                        for gep in list(set(geps)):
                            try:
                                ge = Gauser_extra.objects.get(ronda=po.ronda_centro, clave_ex=gep[1])
                                tipo = 'INT' if 'nterino' in ge.tipo_personal else 'DEF'
                                try:
                                    jornada_calculada = int(ge.jornada_contratada.split(':')[0])
                                    if jornada_calculada > 20:
                                        jornada = '1'
                                    elif jornada_calculada > 14 and jornada_calculada < 20:
                                        jornada = '2'
                                    elif jornada_calculada > 9 and jornada_calculada < 13:
                                        jornada = '3'
                                    else:
                                        jornada = '4'
                                except:
                                    jornada = '1'
                                Profesor_cupo.objects.create(profesorado=profesores_cupo, tipo=tipo, jornada=jornada,
                                                             nombre=gep[0])
                            except:
                                Profesor_cupo.objects.create(profesorado=profesores_cupo, nombre=gep[0])
                    if len(pxls.x_materiaomg) > 0:
                        eec, c = EtapaEscolarCupo.objects.get_or_create(cupo=cupo, nombre=pxls.etapa_escolar,
                                                                        clave_ex=pxls.x_etapa_escolar)
                        cc, c = CursoCupo.objects.get_or_create(cupo=cupo, nombre=pxls.curso, etapa_escolar=eec,
                                                                nombre_especifico=pxls.omc, clave_ex=pxls.x_curso)
                        if c:
                            curso = Curso.objects.get(ronda=po.ronda_centro, clave_ex=pxls.x_curso)
                            grupos = Grupo.objects.filter(cursos__in=[curso])
                            gee = Gauser_extra_estudios.objects.filter(grupo__in=grupos)
                            cc.num_alumnos = max(gee.count(), mn)
                            cc.save()
                        h, sc, m = pxls.horas_semana_min.rpartition(':')
                        try:
                            horas = int(h) + int(m) / 60
                        except:
                            return JsonResponse({'horas': pxls.horas_semana_min, 'h': h, 'm': m,
                                                 'etapa': pxls.x_etapa_escolar, 'x_materia': pxls.x_materiaomg})
                        if pxls.x_actividad == '1':
                            Materia_cupo.objects.get_or_create(cupo=cupo, curso_cupo=cc, clave_ex=pxls.x_materiaomg,
                                                               horas=horas, especialidad=ec, nombre=pxls.materia,
                                                               num_alumnos=cc.num_alumnos, max_num_alumnos=mn)
                        else:
                            if 'Apoyo' in pxls.actividad or 'ACNEE' in pxls.actividad:
                                nombre = '%s (%s)' % (pxls.actividad, pxls.materia)
                                Materia_cupo.objects.get_or_create(cupo=cupo, curso_cupo=cc, nombre=nombre[:119],
                                                                   horas=horas, clave_ex=pxls.x_actividad,
                                                                   especialidad=ec, min_num_alumnos=1,
                                                                   num_alumnos=3, max_num_alumnos=mn)
                            else:
                                Materia_cupo.objects.get_or_create(cupo=cupo, curso_cupo=cc, clave_ex=pxls.x_actividad,
                                                                   horas=horas, especialidad=ec, nombre=nombre[:119],
                                                                   max_num_alumnos=mn, num_alumnos=cc.num_alumnos)
                    elif pxls.x_actividad in ['2', '614']:  # Esto sucede en las tutorías
                        eec, c = EtapaEscolarCupo.objects.get_or_create(cupo=cupo, nombre=pxls.etapa_escolar,
                                                                        clave_ex=pxls.x_etapa_escolar)
                        cc, c = CursoCupo.objects.get_or_create(cupo=cupo, nombre=pxls.curso, etapa_escolar=eec,
                                                                nombre_especifico=pxls.omc, clave_ex=pxls.x_curso)
                        try:
                            Materia_cupo.objects.get(cupo=cupo, curso_cupo=cc, clave_ex=pxls.x_actividad,
                                                     especialidad=ec)
                        except:
                            t = 'Tutoría (%s)' % pxls.unidad
                            Materia_cupo.objects.create(cupo=cupo, curso_cupo=cc, nombre=t, horas=2, max_num_alumnos=mn,
                                                        clave_ex=pxls.x_actividad, especialidad=ec, num_alumnos=20)
                    elif pxls.x_actividad in ['547', '176', '528', '562', '507', '532', '531', '541', '530',
                                              '522', '525', '555', '605', '563', '527', '378', '529', '542']:
                        try:
                            Materia_cupo.objects.get(cupo=cupo, curso_cupo=None, clave_ex=pxls.x_actividad,
                                                     especialidad=ec)
                        except:
                            nombres = {'547': 'Jefatura de departamento', '530': 'Jefatura de estudios (ED)',
                                       '531': 'Jefatura de estudios adjunta (ED)', '532': 'Secretaría (ED)',
                                       '548': 'Jefatura de departamento', '529': 'Dirección (ED)'}
                            try:
                                nombre = nombres[pxls.x_actividad]
                            except:
                                nombre = pxls.actividad
                            Materia_cupo.objects.create(cupo=cupo, curso_cupo=None, nombre=nombre[:119],
                                                        horas=1, clave_ex=pxls.x_actividad, especialidad=ec,
                                                        min_num_alumnos=1, max_num_alumnos=100)

                logger.info('%s, add_cupo id=%s' % (g_e, cupo.id))
                html = render_to_string('cupo_accordion.html', {'cupo': cupo})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'copy_cupo' and g_e.has_permiso('copia_cupo_profesorado'):
            try:
                orig = Cupo.objects.get(id=request.POST['cupo'])
                if orig.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='l').count() < 1:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permiso para copiar el cupo'})
                cupo = Cupo.objects.create(ronda=orig.ronda, nombre='(copia) %s' % (orig.nombre))
                CupoPermisos.objects.create(cupo=cupo, gauser=g_e.gauser, permiso='plwx')
                # crea_departamentos(g_e.ronda)
                for e in orig.especialidadcupo_set.all():
                    e.pk = None
                    e.cupo = cupo
                    # try:
                    #     e.departamento = Departamento.objects.get(ronda=g_e.ronda, abreviatura=e.departamento.abreviatura)
                    # except:
                    #     e.departamento = None
                    #     crear_aviso(request, False, 'No se encuentra departamento para %s' % e.nombre)
                    e.save()
                for etapa in orig.etapaescolarcupo_set.all():
                    etapa.pk = None
                    etapa.cupo = cupo
                    etapa.save()
                for curso in orig.cursocupo_set.all():
                    if curso.etapa_escolar:
                        etapa = cupo.etapaescolarcupo_set.get(clave_ex=curso.etapa_escolar.clave_ex)
                    else:
                        etapa = None
                    curso.pk = None
                    curso.etapa_escolar = etapa
                    curso.cupo = cupo
                    curso.save()
                for m in orig.materia_cupo_set.all():
                    if m.curso_cupo:
                        curso = cupo.cursocupo_set.get(clave_ex=m.curso_cupo.clave_ex, nombre=m.curso_cupo.nombre)
                    else:
                        curso = None
                    m.pk = None
                    m.cupo = cupo
                    m.curso_cupo = curso
                    try:
                        especialidad = EspecialidadCupo.objects.get(cupo=cupo, nombre=m.especialidad.nombre)
                        m.especialidad = especialidad
                    except:
                        m.especialidad = None
                    try:
                        curso = Curso.objects.get(ronda=cupo.ronda, clave_ex=m.curso.clave_ex)
                        m.curso = curso
                    except:
                        if m.curso:
                            crear_aviso(request, False, 'No se encuentra curso para %s' % m.nombre)
                        m.curso = None
                    m.save()
                for f in orig.filtrocupo_set.all():
                    f.pk = None
                    f.cupo = cupo
                    f.save()
                for p in orig.profesores_cupo_set.all():
                    p_cs = p.profesor_cupo_set.all()
                    p.pk = None
                    p.cupo = cupo
                    try:
                        especialidad = EspecialidadCupo.objects.get(cupo=cupo, nombre=p.especialidad.nombre)
                        p.especialidad = especialidad
                    except:
                        p.especialidad = None
                    p.save()
                    for p_c in p_cs:
                        p_c.pk = None
                        p_c.profesorado = p
                        p_c.save()

                logger.info('%s, copy_cupo id=%s -> id=%s' % (g_e, orig.id, cupo.id))
                html = render_to_string('cupo_accordion.html', {'cupo': cupo})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'delete_cupo' and g_e.has_permiso('borra_cupo_profesorado'):
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                if cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0:
                    logger.info('%s, delete_cupo %s' % (g_e, cupo.id))
                    cupo.delete()
                    return JsonResponse({'ok': True})
                elif cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='x').count() > 0:
                    logger.info('%s, delete user access %s' % (g_e, cupo.id))
                    cupo.cupopermisos_set.filter(gauser=g_e.gauser).delete()
                    return JsonResponse({'ok': True})
                else:
                    msg = '%s, intento fallido de borrar el cupo %s' % (g_e, cupo.id)
                    logger.info(msg)
                    return JsonResponse({'ok': False, 'msg': msg})
            except:
                msg = '%s, error al intentar borrar el cupo %s' % (g_e, request.POST['cupo'])
                logger.info(msg)
                return JsonResponse({'ok': False, 'msg': msg})

        elif action == 'bloquea_cupo':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('bloquea_cupos')
                if con1 or con2:
                    bloquear = request.POST['bloquear']
                    logger.info('%s, bloquea_cupo %s %s' % (g_e, cupo.id, bloquear))
                    cupo.bloqueado = {'true': True, 'false': False}[bloquear]
                    if not cupo.bloqueado:
                        cupo.pub_rrhh = False
                    cupo.save()
                    aprrhh, msg = cupo.puede_activarse_pub_rrhh(g_e)
                    html = render_to_string('cupo_accordion_content_pubrrhh.html', {'aprrhh': aprrhh,
                                                                                    'cupo': cupo, 'msg': msg})
                    return JsonResponse({'ok': True, 'html': html, 'msg': msg})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'checkbox_rrhh':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                es_posible, msg = cupo.puede_activarse_pub_rrhh(g_e)
                if es_posible:
                    cupo.pub_rrhh = not cupo.pub_rrhh
                    cupo.save()
                    if cupo.pub_rrhh:
                        Cupo.objects.filter(ronda=cupo.ronda).exclude(id=cupo.id).update(pub_rrhh=False)
                    aprrhh, msg = cupo.puede_activarse_pub_rrhh(g_e)
                    html = render_to_string('cupo_accordion_content_pubrrhh.html', {'aprrhh': aprrhh,
                                                                                    'cupo': cupo})
                    logger.info('%s, publica RRHH cupo %s %s' % (g_e, cupo.id, cupo.pub_rrhh))
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'msg': msg})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'select_ronda_cupo':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                if g_e.has_permiso('cambia_ronda_cupos'):
                    cupo.ronda = Ronda.objects.get(id=request.POST['ronda'])
                    cupo.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'El único usuario con permisos es gauss'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'add_filtro':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('pdf_cupo')
                if con1 or con2:
                    logger.info('%s, add_filtro_cupo %s' % (g_e, cupo.id))
                    nombre = request.POST['nombre']
                    filtro = request.POST['filtro']
                    if len(filtro) > 0 and len(nombre) > 0:
                        f = FiltroCupo.objects.create(cupo=cupo, nombre=nombre, filtro=filtro)
                        return JsonResponse({'ok': True, 'filtro': render_to_string(
                            'cupo_accordion_content_filtro.html', {'filtro': f}),
                                             'cupo': cupo.id})
                    else:
                        return JsonResponse({'ok': False})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except:
                return JsonResponse({'ok': False})

        elif action == 'delete_filtro':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('pdf_cupo')
                if con1 or con2:
                    filtro = FiltroCupo.objects.get(cupo=cupo, id=request.POST['filtro'])
                    id = filtro.id
                    filtro.delete()
                    return JsonResponse({'ok': True, 'filtro': id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'change_nombre_cupo' and g_e.has_permiso('edita_cupos'):
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('pdf_cupo')
                if (con1 or con2) and not cupo.bloqueado:
                    logger.info('%s, change_nombre_cupo %s' % (g_e, cupo.id))
                    cupo.nombre = request.POST['nombre']
                    cupo.save()
                    return JsonResponse({'ok': True, 'nombre': cupo.nombre})
                else:
                    return JsonResponse({'ok': False})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'select_add_especialidad':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    ec, created = EspecialidadCupo.objects.get_or_create(cupo=cupo, nombre=request.POST['especialidad'],
                                                                         clave_ex=request.POST['especialidad'][:10])
                    if created:
                        pc, created = Profesores_cupo.objects.get_or_create(cupo=cupo, especialidad=ec)
                        if created:
                            Profesor_cupo.objects.create(profesorado=pc, nombre='Prof. Interino', tipo='INT')
                    html = render_to_string('cupo_accordion_content_especialidad.html', {'e': ec})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'edit_especialidades':

            cupo = Cupo.objects.get(id=request.POST['cupo'])
            con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
            con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
            if con1 or con2:
                html = render_to_string('cupo_accordion_content_especialidad_edit.html', {'cupo': cupo,
                                                                                          'CUERPOS': CUERPOS})
                return JsonResponse({'ok': True, 'html': html})
            else:
                return JsonResponse({'ok': False, 'm': 'No tienes permiso'})

            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    html = render_to_string('cupo_accordion_content_especialidad_edit.html', {'cupo': cupo,
                                                                                              'CUERPOS': CUERPOS})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        # elif action == 'edit_cursos':
        #     try:
        #         cupo = Cupo.objects.get(id=request.POST['cupo'])
        #         con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
        #         con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
        #         if con1 or con2:
        #             html = render_to_string('cupo_accordion_content_curso_edit.html', {'cupo': cupo})
        #             return JsonResponse({'ok': True, 'html': html})
        #         else:
        #             return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
        #     except Exception as msg:
        #         return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'change_campo_espec_edit':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    ec = EspecialidadCupo.objects.get(cupo=cupo, id=request.POST['espec'])
                    setattr(ec, request.POST['campo'], request.POST['valor'])
                    ec.save()
                    html = ''
                    if request.POST['campo'] == 'cod_cuerpo':
                        html = render_to_string('cupo_accordion_content_especialidad_edit_options.html', {'e': ec})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'change_nombre_curso':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    cc = CursoCupo.objects.get(cupo=cupo, id=request.POST['curso'])
                    cc.nombre = request.POST['texto']
                    cc.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'change_etapa_curso':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    cc = CursoCupo.objects.get(cupo=cupo, id=request.POST['curso'])
                    etapa = EtapaEscolarCupo.objects.get(cupo=cupo, id=request.POST['etapa'])
                    cc.etapa_escolar = etapa
                    cc.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'select_del_especialidad':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    especialidad = EspecialidadCupo.objects.get(cupo=cupo, id=request.POST['especialidad'])
                    # Profesores_cupo.object.filter(especialidad=especialidad).delete()
                    especialidad.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'select_add_curso':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    curso = Curso.objects.filter(clave_ex=request.POST['curso'], etapa_escolar__isnull=False).last()
                    if curso:
                        cc_ex = curso.clave_ex
                        cec_ex = curso.etapa_escolar.clave_ex
                        c_nombre = curso.nombre
                        ce_nombre = curso.etapa_escolar.nombre
                    else:
                        curso = Curso.objects.filter(clave_ex=request.POST['curso']).last()
                        cc_ex = curso.clave_ex
                        cec_ex = 'No etapa'
                        c_nombre = curso.nombre
                        ce_nombre = cec_ex

                    # return JsonResponse({'ok': True,})

                    try:
                        ee = EtapaEscolarCupo.objects.get(cupo=cupo, clave_ex=cec_ex)
                    except:
                        ee = EtapaEscolarCupo.objects.create(cupo=cupo, clave_ex=cec_ex, nombre=ce_nombre)
                    try:
                        cc = CursoCupo.objects.get(cupo=cupo, clave_ex=cc_ex)
                    except:
                        cc = CursoCupo.objects.create(cupo=cupo, nombre=c_nombre, etapa_escolar=ee, clave_ex=cc_ex)
                    for m in curso.materia_set.all():
                        try:
                            Materia_cupo.objects.get(cupo=cupo, clave_ex=m.clave_ex)
                        except:
                            Materia_cupo.objects.create(cupo=cupo, curso_cupo=cc, nombre=m.nombre, horas=m.horas,
                                                        clave_ex=m.clave_ex)
                    html = render_to_string('cupo_accordion_content_curso.html', {'c': cc})
                    return JsonResponse({'ok': True, 'html': html, 'curso': cc.nombre})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'select_copy_curso':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    cc_original = CursoCupo.objects.get(cupo=cupo, id=request.POST['curso'])
                    cc_nuevo = CursoCupo.objects.get(cupo=cupo, id=request.POST['curso'])
                    cc_nuevo.pk = None
                    cc_nuevo.clave_ex = pass_generator()
                    cc_nuevo.nombre = cc_nuevo.nombre + ' (copia)'
                    cc_nuevo.save()
                    for mc in cc_original.materia_cupo_set.all():
                        mc.pk = None
                        mc.curso_cupo = cc_nuevo
                        mc.save()
                    html = render_to_string('cupo_accordion_content_curso.html', {'c': cc_nuevo})
                    return JsonResponse({'ok': True, 'html': html, 'curso': cc_nuevo.nombre})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'select_add_new_curso':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    cnombre = request.POST['curso']
                    ce_nombre = 'Etapa cursos creados'
                    ee, c = EtapaEscolarCupo.objects.get_or_create(cupo=cupo, clave_ex='etapa_creada', nombre=ce_nombre)
                    cc, c = CursoCupo.objects.get_or_create(cupo=cupo, nombre=cnombre, etapa_escolar=ee,
                                                            clave_ex=cnombre[:14])
                    Materia_cupo.objects.get_or_create(cupo=cupo, curso_cupo=cc, nombre='Materia inventada', horas=4,
                                                       clave_ex='materia_creada')
                    html = render_to_string('cupo_accordion_content_curso.html', {'c': cc})
                    return JsonResponse({'ok': True, 'html': html, 'curso': cc.nombre})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'change_texto_nombre_curso':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    cc = CursoCupo.objects.get(cupo=cupo, id=request.POST['curso'])
                    cc.nombre = request.POST['nombre']
                    cc.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'select_del_curso':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    CursoCupo.objects.get(cupo=cupo, id=request.POST['curso']).delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'update_usuarios_invitados':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    invitado = Gauser_extra.objects.get(id=int(request.POST['invitado'][1:]))
                    cp, creado = CupoPermisos.objects.get_or_create(gauser=invitado.gauser, cupo=cupo, permiso='lw')
                    html_span = render_to_string('cupo_accordion_content_invitados.html', {'cupo': cupo, 'cp': cp})
                    return JsonResponse({'ok': True, 'cupo': cupo.id, 'html_span': html_span})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'borrar_invitado':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    cp = CupoPermisos.objects.get(id=int(request.POST['invitado']), cupo=cupo)
                    if 'p' not in cp.permiso:
                        cp.delete()
                        return JsonResponse({'ok': True, 'cupo': cupo.id, 'invitado': request.POST['invitado']})
                    else:
                        return JsonResponse({'ok': False, 'msg': 'No es posible borrar al propietario del cupo.'})
                else:
                    return JsonResponse({'ok': False, 'm': 'No tienes permiso'})
            except:
                return JsonResponse({'ok': False})

        elif action == 'update_departamento' and g_e.has_permiso('edita_cupos'):
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                if not cupo.bloqueado:
                    logger.info('%s, update_departamento %s' % (g_e, cupo.id))
                    especialidad = EspecialidadCupo.objects.get(cupo=cupo, id=request.POST['especialidad'])
                    departamento = Departamento.objects.get(ronda=cupo.ronda, id=request.POST['departamento'])
                    especialidad.departamento = departamento
                    especialidad.save()
                    return JsonResponse({'ok': True, 'nombre': cupo.nombre})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_max_min_cupo':  # and g_e.has_permiso('edita_cupos'):
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    if not cupo.bloqueado:
                        attr = request.POST['attr']
                        logger.info('%s, change_%s %s' % (g_e, attr, cupo.id))
                        setattr(cupo, attr, request.POST['valor'])
                        cupo.save()
                        return JsonResponse({'ok': True})
                    else:
                        return JsonResponse({'ok': False})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except:
                return JsonResponse({'ok': False})

        elif action == 'change_curso':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    if not request.POST['curso']:
                        materias_cupo = Materia_cupo.objects.filter(cupo=cupo, curso_cupo=None)
                        if not materias_cupo:
                            m = Materia_cupo.objects.create(cupo=cupo, min_num_alumnos=1, max_num_alumnos=100,
                                                            nombre="Actividad/Materia no asociada a ningún curso",
                                                            periodos=2)
                            materias_cupo = [m]
                        logger.info('%s, change_curso empty' % (g_e))
                    elif request.POST['curso'] == 'any_course':
                        materias_cupo = Materia_cupo.objects.filter(cupo=cupo)
                        logger.info('%s, change_curso any_course' % g_e)
                    else:
                        curso = CursoCupo.objects.get(id=request.POST['curso'], cupo=cupo)
                        materias_cupo = Materia_cupo.objects.filter(cupo=cupo, curso_cupo=curso)
                        if not materias_cupo:  # Por ejemplo en un cupo creado antes que un determinado curso
                            m = Materia_cupo.objects.create(cupo=cupo, min_num_alumnos=15, max_num_alumnos=35,
                                                            nombre="Actividad/Materia creada automáticamente",
                                                            periodos=4, curso_cupo=curso, horas=4)
                            materias_cupo = [m]
                        logger.info('%s, change_curso %s' % (g_e, curso.nombre))

                    especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                    materias = render_to_string('edit_cupo_materias.html',
                                                {'materias': materias_cupo, 'especialidades': especialidades,
                                                 's_c': True, 'CUERPOS': CUERPOS})
                    return JsonResponse({'ok': True, 'materias': materias})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_especialidad_global':

            cupo = Cupo.objects.get(id=request.POST['cupo'])
            con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
            con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
            if con1 or con2:
                if request.POST['especialidad']:
                    especialidad = EspecialidadCupo.objects.get(id=request.POST['especialidad'], cupo=cupo)
                    profesores_cupo = cupo_especialidad(cupo, especialidad).reparto_profes
                    materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=especialidad)
                    especialidad_nombre = especialidad.nombre
                    logger.info('%s, change_especialidad_global %s' % (g_e, especialidad_nombre))
                else:
                    materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=None)
                    profesores_cupo = None
                    especialidad_nombre = None
                    especialidad = None
                    logger.info('%s, change_especialidad_global sin especialidad' % (g_e))
                especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                materias = render_to_string('edit_cupo_materias.html',
                                            {'materias': materias_cupo, 'especialidades': especialidades,
                                             'especialidad': especialidad, 'CUERPOS': CUERPOS})
                return JsonResponse({'ok': True, 'materias': materias, 'profesores_cupo': profesores_cupo,
                                     'especialidad': especialidad_nombre})

            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    if request.POST['especialidad']:
                        especialidad = EspecialidadCupo.objects.get(id=request.POST['especialidad'], cupo=cupo)
                        profesores_cupo = cupo_especialidad(cupo, especialidad).reparto_profes
                        materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=especialidad)
                        especialidad_nombre = especialidad.nombre
                        logger.info('%s, change_especialidad_global %s' % (g_e, especialidad_nombre))
                    else:
                        materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=None)
                        profesores_cupo = None
                        especialidad_nombre = None
                        especialidad = None
                        logger.info('%s, change_especialidad_global sin especialidad' % (g_e))
                    especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                    materias = render_to_string('edit_cupo_materias.html',
                                                {'materias': materias_cupo, 'especialidades': especialidades,
                                                 'especialidad': especialidad, 'CUERPOS': CUERPOS})
                    return JsonResponse({'ok': True, 'materias': materias, 'profesores_cupo': profesores_cupo,
                                         'especialidad': especialidad_nombre})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'filtro_materia':
            q = request.POST['q']
            s_c = True
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    especialidad = None
                    if request.POST['especialidad'] == 'empty':
                        if not request.POST['curso']:
                            materias_cupo = Materia_cupo.objects.filter(cupo=cupo, curso=None, nombre__icontains=q)
                            s_c = False
                            logger.info('%s, filtro_materia no asociadas a curso' % (g_e))
                        elif request.POST['curso'] == 'any_course':
                            materias_cupo = Materia_cupo.objects.filter(cupo=cupo, nombre__icontains=q)
                            s_c = False
                            logger.info('%s, filtro_materia any_course' % g_e)
                        else:
                            curso = CursoCupo.objects.get(id=request.POST['curso'], cupo=cupo)
                            materias_cupo = Materia_cupo.objects.filter(cupo=cupo, curso_cupo=curso,
                                                                        nombre__icontains=q)
                            logger.info('%s, filtro_materia %s' % (g_e, curso.nombre))
                    else:
                        if request.POST['especialidad']:
                            especialidad_id = request.POST['especialidad']
                            especialidad = EspecialidadCupo.objects.get(id=especialidad_id, cupo=cupo)
                            materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=especialidad,
                                                                        nombre__icontains=q)
                            s_c = False
                            logger.info('%s, filtro_materia %s' % (g_e, especialidad.nombre))
                        else:
                            materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=None,
                                                                        nombre__icontains=q)
                            s_c = False
                            logger.info('%s, filtro_materia sin especialidad' % (g_e))
                    especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                    materias = render_to_string('edit_cupo_materias.html',
                                                {'materias': materias_cupo, 'especialidades': especialidades,
                                                 's_c': s_c, 'especialidad': especialidad, 'CUERPOS': CUERPOS})
                    return JsonResponse({'ok': True, 'materias': materias})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_nombre_materia':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                    logger.info('%s, cupo %s change_nombre_materia "%s" -> "%s"' % (
                        g_e, cupo.id, materia.nombre, request.POST['nombre']))
                    materia.nombre = request.POST['nombre']
                    materia.save()
                    return JsonResponse({'ok': True, 'nombre_materia': materia.nombre})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'duplicate_materia':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                    materia.pk = None
                    materia.nombre += ' (copia)'
                    materia.save()
                    especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                    materias = render_to_string('edit_cupo_materias.html',
                                                {'materias': [materia], 'duplicated': True, 'CUERPOS': CUERPOS,
                                                 'especialidades': especialidades, 'especialidad': None})
                    logger.info('%s, cupo %s duplicate_materia %s' % (g_e, cupo.id, materia.nombre))
                    return JsonResponse({'ok': True, 'materias': materias})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'delete_materia':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                    logger.info('%s, cupo %s delete_materia %s' % (g_e, cupo.id, materia.nombre))
                    materia.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_num_periodos':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                    logger.info('%s, cupo %s - %s, %s -> %s' % (
                        g_e, cupo.id, materia.nombre, materia.periodos, request.POST['periodos']))
                    materia.horas = float(request.POST['periodos'])
                    materia.periodos = int(materia.horas)
                    materia.save()
                    if materia.especialidad:
                        profesores_cupo = cupo_especialidad(cupo, materia.especialidad)
                        return JsonResponse({'ok': True, 'profesores_cupo': profesores_cupo.reparto_profes,
                                             'especialidad': materia.especialidad.nombre})
                    else:
                        return JsonResponse({'ok': True, 'especialidad': ''})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_especialidad_materia':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    try:
                        especialidad = EspecialidadCupo.objects.get(id=request.POST['especialidad'], cupo=cupo)
                    except:
                        especialidad = None
                    materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                    materia.especialidad = especialidad
                    materia.save()
                    logger.info('%s, cupo %s - %s -> %s' % (g_e, cupo.id, materia.nombre, materia.especialidad))
                    if materia.especialidad:
                        profesores_cupo = cupo_especialidad(cupo, materia.especialidad)
                        return JsonResponse({'materia': materia.id, 'profesores_cupo': profesores_cupo.reparto_profes,
                                             'especialidad': materia.especialidad.nombre, 'ok': True})
                    else:
                        return JsonResponse({'ok': True, 'especialidad': '', 'materia': materia.id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'mouseover_especialidad_materia':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    especialidad = EspecialidadCupo.objects.get(id=request.POST['especialidad'], cupo=cupo)
                    profesores_cupo = cupo_especialidad(cupo, especialidad)
                    return JsonResponse({'ok': True, 'profesores_cupo': profesores_cupo.reparto_profes,
                                         'especialidad': especialidad.nombre})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_num_alumnos':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                    logger.info('%s, cupo %s - %s change_num_alumnos %s -> %s' % (
                        g_e, cupo.id, materia.nombre, materia.num_alumnos, request.POST['alumnos']))
                    materia.num_alumnos = int(request.POST['alumnos'])
                    materia.save()
                    if materia.especialidad:
                        profesores_cupo = cupo_especialidad(cupo, materia.especialidad)
                        return JsonResponse({'ok': True, 'profesores_cupo': profesores_cupo.reparto_profes,
                                             'especialidad': materia.especialidad.nombre,
                                             'num_grupos': materia.num_grupos})
                    else:
                        return JsonResponse({'ok': True, 'especialidad': '', 'num_grupos': materia.num_grupos})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_max_num_alumnos':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                    logger.info('%s, en el cupo %s - %s max_num_alumnos %s -> %s' % (
                        g_e, cupo.id, materia.nombre, materia.max_num_alumnos, request.POST['alumnos']))
                    materia.max_num_alumnos = int(request.POST['alumnos'])
                    materia.save()
                    if materia.especialidad:
                        profesores_cupo = cupo_especialidad(cupo, materia.especialidad)
                        return JsonResponse({'ok': True, 'profesores_cupo': profesores_cupo.reparto_profes,
                                             'especialidad': materia.especialidad.nombre,
                                             'num_grupos': materia.num_grupos})
                    else:
                        return JsonResponse({'ok': True, 'especialidad': '', 'num_grupos': materia.num_grupos})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_min_num_alumnos':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                    logger.info('%s, cupo %s - %s change_min_num_alumnos %s -> %s' % (
                        g_e, cupo.id, materia.nombre, materia.min_num_alumnos, request.POST['alumnos']))
                    materia.min_num_alumnos = int(request.POST['alumnos'])
                    materia.save()
                    if materia.especialidad:
                        profesores_cupo = cupo_especialidad(cupo, materia.especialidad)
                        return JsonResponse({'ok': True, 'profesores_cupo': profesores_cupo.reparto_profes,
                                             'especialidad': materia.especialidad.nombre,
                                             'num_grupos': materia.num_grupos})
                    else:
                        return JsonResponse({'ok': True, 'especialidad': '', 'num_grupos': materia.num_grupos})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_num_total_alumnos_curso':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    curso = CursoCupo.objects.get(id=request.POST['curso_cupo'], cupo=cupo)
                    logger.info('%s, cupo %s - %s change_num_total_alumnos_curso %s -> %s' % (
                        g_e, cupo.id, curso.nombre, curso.num_alumnos, request.POST['num_alumnos']))
                    curso.num_alumnos = int(request.POST['num_alumnos'])
                    curso.save()
                    return JsonResponse({'ok': True, 'horas_media': curso.get_horas_media, 'curso': curso.id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_profesor_cupo':
            try:
                cupo = request.POST['cupo']
                campo = request.POST['campo']
                valor = request.POST['valor']
                p_c = Profesor_cupo.objects.get(id=request.POST['id'], profesorado__cupo__id=cupo)
                # if campo == 'bilingue' or campo == 'itinerante' or campo == 'noafin' or campo == 'vacante':
                if campo == 'bilingue' or campo == 'itinerante' or campo == 'noafin' or campo == 'sustituto':
                    valores = {'true': True, 'false': False}
                    valor = valores[valor]
                elif campo == 'borrar':
                    if Profesor_cupo.objects.filter(profesorado=p_c.profesorado).count() > 1:
                        id = p_c.id
                        p_c.delete()
                        return JsonResponse({'ok': True, 'action': 'borrar', 'id': id})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': 'No se pueden borrar todos los profesores'})
                elif campo == 'duplicar':
                    id = p_c.id
                    p_c.pk = None
                    p_c.save()
                    html = render_to_string('edit_cupo_materias_profesor.html', {'p': p_c, 'contador': 2})
                    return JsonResponse({'ok': True, 'action': 'duplicar', 'html': html, 'id': id})
                setattr(p_c, campo, valor)
                p_c.save()
                return JsonResponse({'ok': True, 'action': 'campos'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'update_jornhoras':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='w').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('edita_cupos')
                if con1 or con2:
                    especialidad = EspecialidadCupo.objects.get(id=request.POST['especialidad'], cupo=cupo)
                    setattr(especialidad, request.POST['jornada'], float(request.POST['valor']))
                    especialidad.save()
                    profesores_cupo = cupo_especialidad(cupo, especialidad)
                    return JsonResponse({'profesores_cupo': profesores_cupo.reparto_profes,
                                         'especialidad': especialidad.nombre, 'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        else:
            return JsonResponse({'ok': False, 'error': 'No tienes permiso para ejecutar lo solicitado'})

    else:
        return HttpResponse(status=400)


def clave_ex2int(curso):
    try:
        # print(int(curso.etapa_escolar.clave_ex))
        return int(curso.etapa_escolar.clave_ex)
    except:
        return 0


# @permiso_required('edita_cupos')
def edit_cupo(request, cupo_id):
    g_e = request.session['gauser_extra']
    cupo = Cupo.objects.get(id=cupo_id)

    if not cupo.bloqueado:
        if request.method == 'POST':
            dce = get_dce_cupo(g_e)
            if request.POST['action'] == 'genera_informe':
                c = render_to_string('cupo2pdf.html', {'cupo': cupo, 'dce': dce})
                genera_pdf(c, dce)
                nombre = slugify('cupo%s_%s' % (str(cupo.ronda.entidad.code), cupo.id))
                return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename=nombre + '.pdf',
                                    content_type='application/pdf')
                # pdfkit.from_string(c, dce.url_pdf, dce.get_opciones)
                # fich = open(dce.url_pdf, 'rb')
                # response = HttpResponse(fich, content_type='application/pdf')
                # nombre = 'cupo%s_%s' % (str(cupo.ronda.entidad.code), cupo.id)
                # response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(nombre)
                # return response
            elif request.POST['action'] == 'genera_informeRRHH':
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                interinos = Profesor_cupo.objects.filter(profesorado__cupo=cupo, tipo='INT')
                q1 = Q(profesorado__especialidad__cod_espec='')
                q2 = Q(profesorado__especialidad__cod_cuerpo='')
                con1 = interinos.filter(q1 | q2).count() > 0
                con2 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='l').count() > 0
                if not con1:
                    if con2:
                        dce = get_dce_cupo(g_e)
                        c = render_to_string('cupoRRHH2pdf.html', {'cupo': cupo, 'dce': dce})
                        genera_pdf(c, dce)
                        nombre = slugify('cupoRRHH%s_%s' % (str(cupo.ronda.entidad.code), cupo.id))
                        return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename=nombre + '.pdf',
                                            content_type='application/pdf')
                        # pdfkit.from_string(c, dce.url_pdf, dce.get_opciones)
                        # fich = open(dce.url_pdf, 'rb')
                        # response = HttpResponse(fich, content_type='application/pdf')
                        # nombre = 'cupoRRHH%s_%s' % (str(cupo.ronda.entidad.code), cupo.id)
                        # response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(nombre)
                        # return response
                    else:
                        crear_aviso(request, False, 'No tienes permiso para generar del archivo pdf solicitado')
                else:
                    m1 = '<h1>Aviso <i class="fa fa-warning"></i></h1>'
                    m2 = '<p>Hay especialidades en las que no se ha configurado el código del cuerpo o el código de la propia especialidad.</p>'
                    msg = m1 + m2
                    crear_aviso(request, False, msg)

        cursos = CursoCupo.objects.filter(cupo=cupo)
        cursos = sorted(cursos, key=lambda curso: clave_ex2int(curso))
        materias = Materia_cupo.objects.filter(curso_cupo=cursos[0], cupo=cupo)
        especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
        for especialidad in especialidades:
            cupo_especialidad(cupo, especialidad)
        # s_c stands for 'selected course' and in case of taking True value means edit_cupo doesn't have to show course
        return render(request, "edit_cupo.html", {'formname': 'edit_cupo_profesorado', 'cupo': cupo, 'curso': cursos[0],
                                                  'materias': materias, 'especialidades': especialidades, 's_c': True,
                                                  'cursos': cursos,
                                                  'iconos':
                                                      ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'Informe',
                                                        'title': 'Generar el documento con el cupo',
                                                        'permiso': 'pdf_cupo'},
                                                       {'tipo': 'button', 'nombre': 'file-text-o',
                                                        'title': 'Generar el documento con el cupo para RRHH',
                                                        'texto': 'Informe RRHH', 'permiso': 'pdf_cupo'},
                                                       {'tipo': 'button', 'nombre': 'arrow-left',
                                                        'texto': 'Listado de cupos',
                                                        'title': 'Volver al listado de cupos disponibles',
                                                        'permiso': 'libre'},
                                                       ),
                                                  })
    else:
        return redirect('/cupo/')


################################################################################

codes_conservatorios = [26002928, 26003076, 26003520]
codes_eois = [26003313, 26008724, 26003091]
codes_edir = [26008219, ]


def crea_plantilla_organica_manual(entidad, g_e):
    # entidad = Entidad.objects.get(code=code_centro)
    po = PlantillaOrganica.objects.create(g_e=g_e, ronda_centro=entidad.ronda, carga_completa=True)
    cargo_docente = Cargo.objects.get(entidad=po.ronda_centro.entidad, clave_cargo='g_docente')
    docentes = Gauser_extra.objects.filter(cargos__in=[cargo_docente])
    for p in puestos_especialidad(entidad):
        edb, c = EspecialidadDocenteBasica.objects.get_or_create(ronda=po.ronda_centro, puesto=p)
        gexs = docentes.filter(puesto=p)
        for gex in gexs:
            MiembroEDB.objects.get_or_create(edb=edb, g_e=gex)
    for docente in docentes:
        pd, c = PDocente.objects.get_or_create(po=po, g_e=docente)
        for apartado in po.estructura_po:
            for nombre_columna, contenido_columna in po.estructura_po[apartado].items():
                pdc, c = PDocenteCol.objects.get_or_create(pd=pd, codecol=contenido_columna['codecol'])
                pdc.nombre = nombre_columna
                pdc.periodos = 0
                pdc.save()


# @permiso_required('acceso_carga_masiva_horarios')
def plantilla_organica(request):
    g_e = request.session["gauser_extra"]
    # Hacer una recarga tras haber creado una plantilla orgánica:
    recargar = False
    if request.method == 'POST':
        if request.POST['action'] == 'carga_masiva_plantilla':
            if not g_e.has_permiso('carga_plantillas_organicas'):
                return render(request, "enlazar.html", {'page': '/', })
            file_masivo = request.FILES['file_masivo_xls']
            if 'excel' in file_masivo.content_type:
                CargaMasiva.objects.create(g_e=g_e, ronda=g_e.ronda, fichero=file_masivo,
                                           tipo='HORARIO_PERSONAL_CENTRO')
                try:
                    carga_masiva_from_excel.apply_async(expires=300)
                    crear_aviso(request, True, 'POexcel_automatica')
                    m1 = '<p>El archivo cargado puede tardar unos minutos en ser procesado.</p>'
                    m2 = '<p>En cuanto </p>'
                    crear_aviso(request, False, m1)
                except:
                    crear_aviso(request, False,
                                'El archivo cargado no se ha encolado. Ejecutar la carga manualmente.')
                recargar = True
            else:
                crear_aviso(request, False, 'El archivo cargado no tiene el formato adecuado.' +
                            '<br>Se requiere un archivo xls y ha cargado un archivo %s.' % file_masivo.content_type)

            # logger.info('Carga de archivo de tipo: ' + request.FILES['file_masivo_xls'].content_type)
            # CargaMasiva.objects.create(g_e=g_e, fichero=request.FILES['file_masivo_xls'], tipo='PLANTILLAXLS')
            # try:
            #     carga_masiva_from_file.apply_async(expires=300)
            #     crear_aviso(request, True, 'cmplantilla_organica')
            #     crear_aviso(request, False, 'El archivo cargado puede tardar unos minutos en ser procesado.')
            # except:
            #     crear_aviso(request, False,
            #                 'El archivo cargado no se ha encolado. Ejecutar la carga manualmente.')
        elif request.POST['action'] == 'excel_po':
            try:
                po = PlantillaOrganica.objects.get(id=request.POST['po'])
                ruta = '%s%s/%s' % (MEDIA_CUPO, slugify(po.ronda_centro.entidad.code), slugify(po.ronda_centro.nombre))
                if not os.path.exists(ruta):
                    os.makedirs(ruta)
                fichero_xls = 'PO_%s_%s.xls' % (
                    slugify(po.ronda_centro.entidad.name), po.creado.strftime('%Y-%d-%m-%H-%I'))
                wb = xlwt.Workbook()
                ws = wb.add_sheet('Plantilla Orgánica')
                estilo_ortogonal = xlwt.easyxf('align: rotation 90; font: bold on')
                estilo = xlwt.XFStyle()
                font = xlwt.Font()
                font.bold = True
                estilo.font = font
                ini_column_merged = 1
                fin_column_merged = 0
                ws.write(0, 0, 'Especialidad', estilo)
                ws.col(0).width = 9000
                for apartado in get_apartados(po):
                    fin_column_merged += apartado['colspan']
                    ws.write_merge(0, 0, ini_column_merged, fin_column_merged, apartado['nombre'], estilo)
                    ini_column_merged = fin_column_merged + 1
                ws.write_merge(0, 0, ini_column_merged, ini_column_merged + 2, 'Horas calculadas', estilo)

                ws.write(1, 0, ' ')
                ws.row(1).height = 3000
                for indx, columna in enumerate(get_columnas(po)):
                    ws.write(1, indx + 1, columna, estilo_ortogonal)
                    ws.col(indx + 1).width = 1100
                ws.write(1, indx + 2, 'Horas totales', estilo_ortogonal)
                ws.col(indx + 2).width = 1100
                ws.write(1, indx + 3, 'Horas básicas', estilo_ortogonal)
                ws.col(indx + 3).width = 1100
                ws.write(1, indx + 4, 'Plantilla orgánica', estilo_ortogonal)
                ws.col(indx + 4).width = 1100
                for indx, edb in enumerate(po.ronda_centro.especialidaddocentebasica_set.all()):
                    ws.write(indx + 2, 0, edb.puesto, estilo)
                    horas = get_columnas_edb(po, edb)
                    for c, columna in enumerate(horas['columnas']):
                        ws.write(indx + 2, c + 1, columna['periodos'])
                    ws.write(indx + 2, c + 2, horas['horas_totales'])
                    ws.write(indx + 2, c + 3, horas['horas_basicas'])
                    ws.write(indx + 2, c + 4, horas['horas_plantilla'], estilo)
                wb.save(ruta + fichero_xls)
                xlsfile = open(ruta + fichero_xls, 'rb')
                response = FileResponse(xlsfile, content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s' % fichero_xls
                return response
            except Exception as msg:
                crear_aviso(request, False, str(msg))
        elif request.POST['action'] == 'carga_plantilla_organica_centros':
            logger.info('Carga de archivo de tipo: ' + request.FILES['file_masivo_xls_casiopea'].content_type)
            fichero = request.FILES['file_masivo_xls_casiopea']
            f = fichero.read()
            book = xlrd.open_workbook(file_contents=f)
            sheet = book.sheet_by_index(0)
            cpoc = CargaPlantillaOrganicaCentros.objects.create(g_e=g_e, ejer=str(sheet.cell(1, 0).value))
            keys = {"CCENTRO": "", "ESP": "", "DESPEC": "", "TIPO": "", "TEORICAS": "", "OCUPADAS": ""}
            keys_index = {col_index: str(sheet.cell(0, col_index).value) for col_index in range(sheet.ncols)}

            for row_index in range(1, sheet.nrows):
                for col_index in range(sheet.ncols):
                    keys[keys_index[col_index]] = sheet.cell(row_index, col_index).value
                if keys['CCENTRO'] == '26800109C':  # 26800109C es el centro penitenciario
                    centro = Entidad.objects.get(code=26002941)  # Plus Ultra
                else:
                    centro = Entidad.objects.get(code=int(keys['CCENTRO'][:-1]))
                plazas, ocupadas = int(keys['TEORICAS']), int(keys['OCUPADAS'])
                if 'Ord' in keys['TIPO']:
                    tipo = 'ord'
                elif 'Com' in keys['TIPO']:
                    tipo = 'com'
                elif 'Bil' in keys['TIPO']:
                    tipo = 'bil'
                # elif 'Iti' in keys['TIPO']:
                #     tipo = 'iti'
                else:
                    tipo = 'iti'

                EspecialidadPlantilla.objects.create(cpoc=cpoc, centro=centro, code=str(int(keys['ESP'])), tipo=tipo,
                                                     nombre=keys['DESPEC'], plazas=plazas, ocupadas=ocupadas)
            crear_aviso(request, False, 'El archivo cargado puede tardar unos minutos en ser procesado.')
        elif request.POST['action'] == 'open_accordion' and request.is_ajax():
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['id'])
                html = render_to_string('plantilla_organica_accordion_content.html', {'po': po, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html, 'carga_completa': po.carga_completa})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        # elif request.POST['action'] == 'check_carga_completa' and request.is_ajax():
        #     try:
        #         po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['id'])
        #         if po.carga_completa:
        #             return JsonResponse({'ok': True})
        #         else:
        #             return JsonResponse({'ok': False})
        #     except Exception as msg:
        #         return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'carga_parcial_plantilla' and request.is_ajax():
            po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
            funcion = request.POST['funcion']
            eval('po.' + funcion + '()')
            return JsonResponse({'ok': True})
        elif request.POST['action'] == 'tdpdocente' and request.is_ajax():
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
                ge = Gauser_extra.objects.get(ronda=po.ronda_centro, id=request.POST['ge'])
                edb = EspecialidadDocenteBasica.objects.get(ronda=po.ronda_centro, id=request.POST['edb'])
                # departamento = Depentidad.objects.get(ronda=po.ronda_centro, id=request.POST['departamento'])
                pdcol = PDocenteCol.objects.get(pd__po=po, pd__g_e=ge, codecol=request.POST['codecol'])
                # Para evitar los caracteres no numéricos obtenidos del div contenteditable no basta con int():
                pdcol.periodos_added = int(
                    "".join(filter(str.isdigit, request.POST['valor']))) - pdcol.num_periodos_sesiones
                pdcol.save()
                data = get_columnas_docente(po, ge)
                html_edb = render_to_string('plantilla_organica_accordion_content_tbody_puesto.html',
                                            {'edb': edb, 'po': po})
                return JsonResponse({'ok': True, 'html_edb': html_edb,
                                     'horas_basicas': data['horas_basicas'], 'horas_totales': data['horas_totales']})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_grupos_excluidos' and request.is_ajax():
            try:
                po = PlantillaOrganica.objects.get(id=request.POST['po'], g_e=g_e)
                grupo = Grupo.objects.get(id=request.POST['grupo'])
                if request.POST['tipo'] == 'add':
                    GrupoExcluido.objects.get_or_create(po=po, grupo=grupo)
                else:
                    GrupoExcluido.objects.get(po=po, grupo=grupo).delete()
                docentes_id = SesionExtra.objects.filter(sesion__horario=po.horario, grupo=grupo).values_list(
                    'sesion__g_e', flat=True).distinct()
                for docente in Gauser_extra.objects.filter(id__in=docentes_id):
                    po.carga_pdocente(docente)
                departamentos_id = MiembroDepartamento.objects.filter(g_e__id__in=docentes_id).values_list(
                    'departamento', flat=True).distinct()
                departamentos = Depentidad.objects.filter(id__in=departamentos_id)
                data = []
                for departamento in departamentos:
                    data.append(get_columnas_departamento(po, departamento))
                html = render_to_string('plantilla_organica_accordion_content_gruposexcluidos.html', {'po': po})
                return JsonResponse({'ok': True, 'po': po.id, 'data': data, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'copiar_po':
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['id'])
                pxls = po.plantillaxls_set.all()
                pds = po.pdocente_set.all()
                po.pk = None
                po.save()
                for p in pxls:
                    p.pk = None
                    p.po = po
                    p.save()
                for pd in pds:
                    pdcols = pd.pdocentecol_set.all()
                    pd.pk = None
                    pd.po = po
                    pd.save()
                    for pdcol in pdcols:
                        pdcol.pk = None
                        pdcol.pd = pd
                        pdcol.save()
                html = render_to_string('plantilla_organica_accordion.html',
                                        {'buscadas': False, 'plantillas_o': [po], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_po':
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['id'])
                po.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_edb_th':
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
                # departamento = Depentidad.objects.get(id=request.POST['departamento'])
                # html = render_to_string('plantilla_organica_accordion_content_tbody_docente.html',
                #                         {'po': po, 'departamento': departamento})
                edb = EspecialidadDocenteBasica.objects.get(id=request.POST['edb'])
                html = render_to_string('plantilla_organica_accordion_content_tbody_docente.html',
                                        {'po': po, 'edb': edb})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'materias_docente':
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
                docente = Gauser_extra.objects.get(id=request.POST['docente'], ronda=po.ronda_centro)
                # horario = Horario.objects.get(ronda=docente.ronda, clave_ex=po.pk)
                horario = po.horario
                materias = []
                for se in SesionExtra.objects.filter(sesion__horario=horario, sesion__g_e=docente):
                    if se.materia:
                        cadena = '%s' % se.materia.id
                        for grupo in se.sesion.grupos():
                            cadena += '-%s' % grupo.id
                        materias.append(cadena)
                # Dict para contar los periodos asociados a cada materia:
                # https://stackoverflow.com/questions/23240969/python-count-repeated-elements-in-the-list
                periodos = {i: materias.count(i) for i in materias}
                materias_docente = []
                for data, periodos in periodos.items():
                    materia_id, grupos_id = data.split('-')[0], data.split('-')[1:]
                    materia = Materia.objects.get(id=materia_id)
                    grupos = Grupo.objects.filter(id__in=grupos_id)
                    materias_docente.append({'materia': materia, 'grupos': grupos, 'periodos': periodos})
                html = render_to_string('plantilla_organica_accordion_content_tbody_docente_materias.html',
                                        {'materias_docente': materias_docente})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'get_horario':
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
                docente = Gauser_extra.objects.get(id=request.POST['docente'], ronda=po.ronda_centro)
                # h = Horario.objects.get(ronda=docente.ronda, clave_ex=po.pk)
                h = po.horario
                # horario = h.get_horario(docente)
                horario = h.get_horario2(docente)
                sesiones = h.sesion_set.filter(g_e=docente)
                # tabla = render_to_string('plantilla_organica_horario_docente.html', {'horario': horario,
                #                                                                      'docente': docente})
                tabla = render_to_string('plantilla_organica_horario_docente.html', {'sesiones': sesiones,
                                                                                     'docente': docente})
                return JsonResponse({'ok': True, 'tabla': tabla, 'h': h.id, 'd': docente.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'actividades_grupos':
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
                x_actividades = request.POST.getlist('x_actividades[]')
                if len(x_actividades) == 0:
                    return JsonResponse({'ok': True, 'html': '', 'po': po.id})
                actividades = request.POST.getlist('actividades[]')
                html = render_to_string('plantilla_organica_accordion_content_estudio_actividades.html',
                                        {'po': po, 'actividades': actividades, 'x_actividades': x_actividades})
                return JsonResponse({'ok': True, 'html': html, 'po': po.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'get_horario_docente_actividades':
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
                docente = Gauser_extra.objects.get(id=request.POST['docente'], ronda=po.ronda_centro)
                x_actividades = request.POST.getlist('x_actividades[]')
                sextras_apoyo = SesionExtra.objects.filter(sesion__horario=po.horario,
                                                           actividad__clave_ex__in=x_actividades, sesion__g_e=docente)
                sesiones = Sesion.objects.filter(id__in=sextras_apoyo.values_list('sesion', flat=True)).distinct()
                tabla = render_to_string('plantilla_organica_horario_docente.html', {'sesiones': sesiones,
                                                                                     'docente': docente})
                return JsonResponse({'ok': True, 'tabla': tabla, 'po': po.id, 'd': docente.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'get_horario_grupo_actividades':
            po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
            grupo = Grupo.objects.get(id=request.POST['grupo'], ronda=po.ronda_centro)
            x_actividades = request.POST.getlist('x_actividades[]')
            sesex = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex__in=x_actividades,
                                               grupo=grupo)
            sesiones_ = Sesion.objects.filter(id__in=sesex.values_list('sesion', flat=True)).distinct()
            sesiones = {}
            for s in sesiones_:
                try:
                    sesiones['%s-%s-%s' % (s.dia, s.hora_inicio, s.hora_fin)].append(s)
                except:
                    sesiones['%s-%s-%s' % (s.dia, s.hora_inicio, s.hora_fin)] = []
                    sesiones['%s-%s-%s' % (s.dia, s.hora_inicio, s.hora_fin)].append(s)
            try:
                tabla_horario = render_to_string('plantilla_organica_horario_grupo.html',
                                                 {'sesiones': sesiones, 'grupo': grupo})
                return JsonResponse({'ok': True, 'tabla': tabla_horario, 'h': po.horario.id, 'g': grupo.id,
                                     'sesiones': len(sesiones), 'sesiones_': sesiones_.count(), 'sesex': sesex.count()})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'get_horario_curso_actividades':
            po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
            curso = Curso.objects.get(id=request.POST['curso'], ronda=po.ronda_centro)
            x_actividades = request.POST.getlist('x_actividades[]')
            sesex = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex__in=x_actividades,
                                               grupo__cursos__in=[curso])
            sesiones_ = Sesion.objects.filter(id__in=sesex.values_list('sesion', flat=True)).distinct()
            sesiones = {}
            for s in sesiones_:
                try:
                    sesiones['%s-%s-%s' % (s.dia, s.hora_inicio, s.hora_fin)].append(s)
                except:
                    sesiones['%s-%s-%s' % (s.dia, s.hora_inicio, s.hora_fin)] = []
                    sesiones['%s-%s-%s' % (s.dia, s.hora_inicio, s.hora_fin)].append(s)
            try:
                tabla_horario = render_to_string('plantilla_organica_horario_grupo.html',
                                                 {'sesiones': sesiones, 'curso': curso})
                return JsonResponse({'ok': True, 'tabla': tabla_horario, 'h': po.horario.id, 'c': curso.id,
                                     'sesiones': len(sesiones), 'sesiones_': sesiones_.count(), 'sesex': sesex.count()})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'cargar_po_no_racima':
            entidad = Entidad.objects.get(id=request.POST['centro_no_racima'])
            crea_plantilla_organica_manual(entidad, g_e)

    plantillas_o = PlantillaOrganica.objects.filter(g_e=g_e)
    centros_no_racima = [26002928, 26003076, 26003520, 26003313, 26008724, 26003091, 26008219]
    ejemplo_sesiones = Sesion.objects.filter(g_e__id=45740, horario__id=128)
    return render(request, "plantilla_organica.html",
                  {
                      'iconos': ({'tipo': 'button', 'nombre': 'cloud-upload', 'texto': 'Cargar datos Racima',
                                  'title': 'Cargar datos a partir de archivo obtenido de Racima',
                                  'permiso': 'carga_plantillas_organicas'},
                                 {'tipo': 'button', 'nombre': 'upload', 'texto': 'Cargar datos Casiopea',
                                  'title': 'Cargar datos a partir de archivo obtenido de Casiopea',
                                  'permiso': 'carga_datos_casiopea'}, {}),
                      'formname': 'plantilla_organica',
                      'recargar': recargar,
                      'plantillas_o': plantillas_o,
                      'g_e': g_e,
                      'centros_no_racima': Entidad.objects.filter(code__in=centros_no_racima),
                      # 'esdir': Entidad.objects.get(code=26008219),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'ejemplo_sesiones': ejemplo_sesiones,
                      'docente': g_e,
                  })

def get_cursos_escolares_cupo():
    inicio_rrhh_cupos = datetime(2022, 9, 1).date()
    hoy = datetime.today().date()
    cursos_escolares = {}
    for y in range(inicio_rrhh_cupos.year, hoy.year):
        curso = '%s-%s' % (y + 1, y + 2)  # El cupo se calcula para el curso que viene
        cursos_escolares[curso] = {'inicio': datetime(y, 9, 1).date(), 'fin': datetime(y + 1, 8, 31).date(), 'id': y}
    # Por ejemplo si hoy fuera 1 de febrero de 2025 -- datetime.date(2025, 2, 1), cursos_escolares sería:
    # {'2023-2024': {'inicio': datetime.date(2022, 9, 1), 'fin': datetime.date(2023, 8, 31), 'id': 2022},
    #  '2024-2025': {'inicio': datetime.date(2023, 9, 1), 'fin': datetime.date(2024, 8, 31), 'id': 2023},
    #  '2025-2026': {'inicio': datetime.date(2024, 9, 1), 'fin': datetime.date(2025, 8, 31), 'id': 2024}}
    return cursos_escolares
# @permiso_required('acceso_carga_masiva_horarios')
def rrhh_cupos(request):
    g_e = request.session["gauser_extra"]
    cursos_escolares = get_cursos_escolares_cupo()
    if request.method == 'POST':
        if request.POST['action'] == 'carga_masiva_plantilla':
            if not g_e.has_permiso('carga_plantillas_organicas'):
                pass
        elif request.POST['action'] == 'open_accordion' and request.is_ajax():
            try:
                y = int(request.POST['id'])
                curso = cursos_escolares['%s-%s' % (y + 1, y + 2)]
                cupos = Cupo.objects.filter(creado__lte=curso['fin'], creado__gte=curso['inicio'], bloqueado=True,
                                            pub_rrhh=True)
                html = render_to_string('rrhh_cupos_accordion_content.html', {'cupos': cupos, 'g_e': g_e, 'y': y})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'desplegar_solicitud' and request.is_ajax():
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                html = render_to_string('rrhh_cupos_accordion_content_solicitud.html', {'cupo': cupo})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif request.POST['action'] == 'genera_csvRRHH':
            y = int(request.POST['curso_actual'])
            curso = cursos_escolares['%s-%s' % (y + 1, y + 2)]
            cupos = Cupo.objects.filter(creado__lte=curso['fin'], creado__gte=curso['inicio'], bloqueado=True,
                                        pub_rrhh=True)
            csv_file = render_to_string('rrhh_cupos_accordion_content_solicitud_csv.csv', {'cupos': cupos})
            response = HttpResponse(csv_file, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=Solicitud_cupo_%s-%s.csv' % (y + 1, y + 2)
            return response
        elif request.POST['action'] == 'genera_csvRRHH_parcial':
            cupo_parcial = Cupo.objects.filter(id=request.POST['cupo_parcial'], bloqueado=True, pub_rrhh=True)
            try:
                curso = slugify(cupo_parcial[0].curso_escolar_cupo)
                centro = slugify(cupo_parcial[0].ronda.entidad.name)
            except:
                curso = 'curso_escolar'
                centro = 'centro_educativo'
            csv_file = render_to_string('rrhh_cupos_accordion_content_solicitud_csv.csv', {'cupos': cupo_parcial})
            response = HttpResponse(csv_file, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=Solicitud_cupo_%s-%s.csv' % (curso, centro)
            return response

    return render(request, "rrhh_cupos.html",
                  {
                      'iconos': ({'tipo': 'button', 'nombre': 'cloud-upload', 'texto': 'Cargar datos Racima',
                                  'title': 'Cargar datos a partir de archivo obtenido de Racima',
                                  'permiso': 'carga_plantillas_organicas'},
                                 {'tipo': 'button', 'nombre': 'upload', 'texto': 'Cargar datos Casiopea',
                                  'title': 'Cargar datos a partir de archivo obtenido de Casiopea',
                                  'permiso': 'carga_datos_casiopea'}, {}),
                      'formname': 'rrhh_cupos',
                      'cursos_escolares': cursos_escolares,
                      'g_e': g_e,
                  })


entidadesextra_tipos = ['C.E.O. - Centro de Educación Obligatoria',
                            'C.I.P.F.P. - Centro Integrado Público de Formación Profesional',
                            'E.S.D. - Escuela Superior de Diseño',
                            #'C.P.E.D. - Centro Privado Autorizado de Enseñanzas Deportivas',
                            #'C.P.E.I - Centro Privado de Educación Infantil',
                            'C.E.P.A. - Centro Público de Educación de Personas Adultas',
                            'C.E.E. - Centro de Educación Especial',
                            #'E.M.M. - Escuela Pública de Música',
                            #'E.I.P.C.M. - Escuela Municipal de Educación Infantil',
                            'I.E.S. - Instituto de Educación Secundaria',
                            #'E.P.M. - Escuela Privada de Música',
                            'C.R.A. - Colegio Rural Agrupado',
                            #'C.P.E.E. - Centro Privado de Educación Especial',
                            #'C.E.M. - Conservatorio Elemental de Música',
                            #'C.P.E.I.P. - Centro Privado de Educación Infantil y Primaria',
                            #'C.P.E.S. - Centro Privado de Educación Secundaria', 'E.I.P.C. - Escuela Infantil',
                            'C.E.I.P. - Colegio de Educación Infantil y Primaria',
                            #'C.P.D.E.E. - Centro Docente Privado Extranjero en España',
                            #'C.P.F.P.E. - Centro Privado de Formación Profesional Específica',
                            #'C.P.E.I.P.S. - Centro Privado de Educación Infantil Primaria y Secundaria',
                            'E.O.I. - Escuela Oficial de Idiomas', 'C.P.M. - Conservatorio Profesional de Música',
                            #'C.P.F.P. - Centro Privado de Formación Profesional',
                            'S.I.E.S. - Sección de Instituto de Educación Secundaria']
# @permiso_required('acceso_estadistica_cupos')
def estadistica_cupos(request):
    g_e = request.session['gauser_extra']
    cursos_escolares = get_cursos_escolares_cupo()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'open_accordion':
            try:
                estad = {}
                y = int(request.POST['id'])
                curso_escolar = cursos_escolares['%s-%s' % (y + 1, y + 2)]
                cupos = Cupo.objects.filter(creado__gte=curso_escolar['inicio'], creado__lte=curso_escolar['fin'])
                entidades = Entidad.objects.filter(entidadextra__tipo_centro__in=entidadesextra_tipos)
                estad['n_centros'] = entidades.count()
                estad['n_cupos'] = cupos.count()
                estad['n_borradores'] = cupos.filter(bloqueado=False).count()
                estad['n_bloqueados'] = cupos.filter(bloqueado=True).count()
                estad['n_pubrrhh'] = cupos.filter(pub_rrhh=True).count()
                estad['min_fecha'] = datetime.now().date()
                estad['max_fecha'] = datetime(1970, 1, 1).date()
                for cupo in cupos:
                    estad['min_fecha'] = cupo.creado if cupo.creado < estad['min_fecha'] else estad['min_fecha']
                    estad['max_fecha'] = cupo.modificado if cupo.modificado > estad['max_fecha'] else estad['max_fecha']
                html = render_to_string('estadistica_cupos_accordion_content.html', {'estad': estad,
                                                                                     'curso_escolar': curso_escolar,
                                                                                     'entidades': entidades})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'estadistica_entidad' and request.is_ajax():
            try:
                y = int(request.POST['id'])
                curso_escolar = cursos_escolares['%s-%s' % (y + 1, y + 2)]
                cupos = Cupo.objects.filter(creado__gte=curso_escolar['inicio'], creado__lte=curso_escolar['fin'])
                cupo = cupos.get(pub_rrhh=True, ronda__entidad__id=request.POST['entidad'])
                html = render_to_string('estadistica_cupos_accordion_content_tabla.html', {'cupo': cupo})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})
        elif action == 'genera_pdf':
            doc_cupos_estadistica = 'Configuración de estadística para los cupos'
            dce = get_dce(g_e.ronda.entidad, doc_cupos_estadistica)
            tablas = request.POST['textarea_listado_estadistica']
            c = render_to_string('estadistica_cupos_html2pdf.html', {'tablas': tablas, 'dce': dce})
            genera_pdf(c, dce)
            nombre = slugify('Informe_estadística_cupos')
            return FileResponse(open(dce.url_pdf, 'rb'), as_attachment=True, filename=nombre + '.pdf',
                                content_type='application/pdf')


    return render(request, "estadistica_cupos.html",
                  {
                      'formname': 'estadistica_cupos',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF', 'permiso': 'libre',
                            'title': 'Generar PDF a partir de la información mostrada en pantalla'},
                           ),
                      # 'entidades': Entidad.objects.filter(entidadextra__isnull=False),
                      'g_e': g_e,
                      'cursos_escolares': cursos_escolares,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


def comprueba_dnis(request):
    g_e = request.session["gauser_extra"]
    info = {'errores': [], 'duplicados': []}
    if g_e.gauser.username == 'gauss':
        from autenticar.models import Gauser
        from gauss.funciones import genera_nie
        info = {'errores': [], 'duplicados': [], 'gausers': []}
        gauser_all = Gauser.objects.all()
        gauser_all_dnis = gauser_all.values_list('dni', flat=True)
        gauser_extra_all = Gauser_extra.objects.all()
        for g in gauser_all:
            dni = genera_nie(g.dni)
            if g.dni != dni and dni:
                # info['errores'].append('%s-%s -> %s' % (g.get_full_name(), g.dni, dni))
                if dni in gauser_all_dnis:
                    try:
                        g_bueno = gauser_all.get(dni=dni)
                        # ges_buenos = list(gauser_extra_all.filter(gauser=g_bueno).values_list('ronda__id', 'ronda__nombre'))
                        # ges_a_mover = list(gauser_extra_all.filter(gauser=g).values_list('ronda__id', 'ronda__nombre'))
                        ges_buenos = gauser_extra_all.filter(gauser=g_bueno)
                        rondas_buenas = ges_buenos.values_list('ronda__id', flat=True)
                        ges_buenos_id = ges_buenos.values_list('id', flat=True)
                        ges_a_mover = gauser_extra_all.filter(gauser=g)
                        for ge_a_mover in ges_a_mover:
                            if ge_a_mover.ronda.id in rondas_buenas:
                                info['errores'].append(
                                    'Varios ges (%s - %s) en la misma ronda: (%s, %s) -- ges_buenos: %s %s' % (
                                        g.get_full_name(), g.dni, ge_a_mover.id, ge_a_mover.ronda.id,
                                        g_bueno.get_full_name(), list(ges_buenos.values_list('id', 'ronda_id'))))
                        info['duplicados'].append(
                            {'g_bueno': [g_bueno.id, g_bueno.last_name], 'ges_buenos': list(ges_buenos_id),
                             'ges_a_mover': list(ges_a_mover.values_list('id', flat=True))})
                        info['gausers'].append('g_bueno %s, g_mal %s' % (g_bueno.dni, g.dni))
                    except:
                        info['errores'].append('Varios gauser con dni %' % dni)
                    # gausers_duplicados = list(gauser_all.filter(dni=dni).values_list('id', 'last_name'))
                    # info['duplicados'].append({'g': [g.id, g.last_name], 'dup': gausers_duplicados})
    return JsonResponse(info)


def arregla_duplicados_antiguo(request):
    g_e = request.session["gauser_extra"]
    info = {'errores': [], 'duplicados': []}
    if g_e.gauser.username == 'gauss':
        from autenticar.models import Gauser
        from gauss.funciones import genera_nie, pass_generator
        gauser_all = Gauser.objects.all()
        gauser_all_dnis = gauser_all.values_list('dni', flat=True)
        gauser_extra_all = Gauser_extra.objects.all()
        for g in gauser_all:
            try:
                dni = genera_nie(g.dni)
                if g.dni != dni and dni:
                    if dni in gauser_all_dnis:
                        try:
                            g_bueno = gauser_all.get(dni=dni)
                            ges_buenos = gauser_extra_all.filter(gauser=g_bueno)
                            rondas_buenas = ges_buenos.values_list('ronda__id', flat=True)
                            ges_a_mover = gauser_extra_all.filter(gauser=g)
                            if ges_a_mover.count() == 0:
                                try:
                                    g.delete()
                                    info['duplicados'].append('Borrado Gauser sin GEs')
                                except:
                                    g.dni = ''
                                    g.username = pass_generator(size=12)
                                    g.first_name = 'Borrado'
                                    g.last_name = 'por dni duplicado'
                                    g.is_active = False
                                    g.save()
                                    info['errores'].append('Gauser borrado por duplicado %s' % str(g.id))
                            for ge_a_mover in ges_a_mover:
                                if ge_a_mover.ronda.id in rondas_buenas:
                                    ge_a_mover.delete()
                                else:
                                    ge_a_mover.gauser = g_bueno
                                    ge_a_mover.save()
                        except Exception as msg:
                            info['errores'].append('Varios gauser con dni %s -- %s' % (dni, str(msg)))
                    else:
                        g.dni = dni
                        g.save()
                        info['duplicados'].append('%s' % g.dni)
                else:
                    gs = gauser_all.filter(dni=dni)
                    num = gs.count()
                    if num > 1:
                        info['duplicados'].append('%s duplicado con dni %s' % (num, dni))
            except:
                info['errores'].append('Error con usuario %s' % g.id)
    return JsonResponse(info)


def arregla_duplicados(request):
    g_e = request.session["gauser_extra"]
    info = {'errores': [], 'duplicados': []}
    if g_e.gauser.username == 'gauss':
        from autenticar.models import Gauser
        from gauss.funciones import genera_nie, pass_generator
        gauser_all = Gauser.objects.filter(dni_duplicado=True)
        # gauser_all_dnis = gauser_all.values_list('dni', flat=True)
        gauser_extra_all = Gauser_extra.objects.all()
        for g in gauser_all:
            # try:
            if g.dni:
                gs = gauser_all.filter(dni=g.dni)
                num = gs.count()
                if num > 1:
                    ges = gauser_extra_all.filter(gauser=g)
                    info['duplicados'].append('%s duplicado con dni %s. ges=%s' % (num, g.dni, ges.count()))
                    if ges.count() == 0:
                        g.dni = ''
                        g.username = pass_generator(size=12)
                        g.is_active = False
                        g.first_name = 'Borrado'
                        g.last_name = 'por dni duplicado'
                        g.save()
                else:
                    g.dni_duplicado = False
                    g.save()
            # except:
            #     info['errores'].append('Error con usuario %s' % g.id)
    return JsonResponse(info)
