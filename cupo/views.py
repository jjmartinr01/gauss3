# -*- coding: utf-8 -*-
import logging
import datetime
import xlwt
import xlrd

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext

from autenticar.control_acceso import permiso_required
from cupo.templatetags.cupo_extras import get_columnas_docente, get_columnas_departamento
from gauss.funciones import html_to_pdf
from gauss.rutas import *
from django.http import HttpResponse
from django.db.models import Q
from django.template.loader import render_to_string

from horarios.models import SesionExtra, Horario, Sesion
from mensajes.models import Aviso
from mensajes.views import crear_aviso
from cupo.models import Cupo, Materia_cupo, Profesores_cupo, FiltroCupo, EspecialidadCupo, Profesor_cupo, GrupoExcluido, \
    CursoCupo, EtapaEscolarCupo, CupoPermisos
from cupo.models import PlantillaOrganica, PDocenteCol
from entidades.models import CargaMasiva, Gauser_extra, MiembroDepartamento
from entidades.models import Departamento as Depentidad
from estudios.models import Curso, Materia, Grupo, EtapaEscolar
from horarios.tasks import carga_masiva_from_file

from programaciones.models import Gauser_extra_programaciones, Departamento, crea_departamentos

logger = logging.getLogger('django')

# Algunos cuerpos contienen las mismas especialidades, por ejemplo 590 (profe secundaria) y 511 (catedrático secund.)
# Para el cupo únicamente importa la especialidad así que para evitar duplicidades en las especialidades
# se toman únicamente los siguientes cuerpos:
CUERPOS_CUPO = ('590', '591', '592', '593', '594', '595', '596')


# @permiso_required('acceso_cupo_profesorado')
def cupo(request):
    g_e = request.session['gauser_extra']

    # etapas = EtapaEscolar.objects.all()
    # materias = Materia_cupo.objects.all()
    # cupos = Cupo.objects.all()
    # for cupo in cupos:
    #     for etapa in etapas:
    #         EtapaEscolarCupo.objects.get_or_create(cupo=cupo, nombre=etapa.nombre, clave_ex=etapa.clave_ex)
    # for m in materias:
    #     try:
    #         etapa = EtapaEscolarCupo.objects.get(clave_ex=m.curso.etapa_escolar.clave_ex)
    #     except:
    #         etapa = None
    #     try:
    #         curso_nombre = m.curso.nombre
    #     except:
    #         curso_nombre = ''
    #     try:
    #         curso_tipo = m.curso.tipo
    #     except:
    #         curso_tipo = ''
    #     try:
    #         curso_nombre_esp = m.curso.nombre_especifico
    #     except:
    #         curso_nombre_esp = ''
    #     try:
    #         curso_clave_ex = m.curso.clave_ex
    #     except:
    #         curso_clave_ex = ''
    #     cc, c = CursoCupo.objects.get_or_create(cupo=m.cupo, nombre=curso_nombre, etapa_escolar=etapa,
    #                                     tipo=curso_tipo,
    #                                     nombre_especifico=curso_nombre_esp, clave_ex=curso_clave_ex)
    #     m.curso_cupo = cc
    #     m.save()

    if request.method == 'POST':
        if request.POST['action'] == 'genera_informe':
            cupo = Cupo.objects.get(id=request.POST['cupo'], ronda__entidad=g_e.ronda.entidad)
            fichero = 'cupo%s_%s' % (str(cupo.ronda.entidad.code), cupo.id)
            texto_html = render_to_string('cupo2pdf.html', {'cupo': cupo, 'MEDIA_ANAGRAMAS': MEDIA_ANAGRAMAS})
            ruta = MEDIA_CUPO + '%s/' % cupo.ronda.entidad.code
            fich = html_to_pdf(request, texto_html, fichero=fichero, media=ruta, title='Cupo de la Entidad')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            logger.info('%s, genera pdf del cupo %s' % (g_e, cupo.id))
            return response

    cupos_id = CupoPermisos.objects.filter(gauser=g_e.gauser).values_list('cupo__id', flat=True)
    cupos = Cupo.objects.filter(Q(ronda__entidad=g_e.ronda.entidad) | Q(id__in=cupos_id)).distinct()
    plantillas_o = PlantillaOrganica.objects.filter(g_e=g_e)
    return render(request, "cupo.html", {'formname': 'cupo_profesorado', 'cupos': cupos, 'plantillas_o': plantillas_o})


def cupo_especialidad(cupo, especialidad):
    materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=especialidad)
    profesores_cupo = Profesores_cupo.objects.get(cupo=cupo, especialidad=especialidad)
    # profesores_cupo, created = Profesores_cupo.objects.get_or_create(cupo=cupo, especialidad=especialidad)
    # if created:
    #     geps = Gauser_extra_programaciones.objects.filter(ge__ronda=cupo.ronda, puesto=especialidad.nombre)
    #     for gep in geps:
    #         Profesor_cupo.objects.create(profesorado=profesores_cupo, nombre=gep.ge.gauser.get_full_name())
    profesores_cupo.num_horas = sum([m.total_periodos for m in materias_cupo])
    profesores_cupo.save()
    return profesores_cupo


# def crear_profesores_cupo(cupo):
#     p_cs = Profesores_cupo.objects.filter(cupo=cupo)
#     for p_c in p_cs:
#         geps = Gauser_extra_programaciones.objects.filter(ge__ronda=cupo.ronda, puesto=p_c.especialidad.nombre)
#         if geps.count() == 0:
#             Profesor_cupo.objects.create(profesorado=p_c, nombre='Profesor Interino', tipo='NONE')
#         for gep in geps:
#             Profesor_cupo.objects.create(profesorado=p_c, nombre=gep.ge.gauser.get_full_name())
#     return True


def ajax_cupo(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        action = request.POST['action']
        if action == 'add_cupo' and g_e.has_permiso('crea_cupos'):
            try:
                crea_departamentos(g_e.ronda)
                nombre = '%s - Cupo creado el %s' % (g_e.ronda.entidad.name, datetime.datetime.now())
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
                                Profesor_cupo.objects.create(profesorado=profesores_cupo,
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
                ds = Departamento.objects.filter(ronda=cupo.ronda)
                html = render_to_string('formulario_cupo.html', {'cupo': cupo, 'request': request, 'departamentos': ds})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif action == 'crea_cupo_from_po' and g_e.has_permiso('crea_cupos'):
            try:
                po = PlantillaOrganica.objects.get(id=request.POST['po'], g_e=g_e)
                nombre = '%s - Cupo creado el %s' % (po.ronda_centro.entidad.name, datetime.datetime.now())
                cupo = Cupo.objects.create(ronda=po.ronda_centro, nombre=nombre)
                CupoPermisos.objects.create(cupo=cupo, gauser=g_e.gauser, permiso='plwx')
                # Crea filtros automáticos:
                # filtros = [('Materias Bilingües', 'bilingüe'), ('Reducciones por bilingüismo', 'cción biling'),
                #            ('Tutorías', 'Tutor'), ('Jefaturas de departamento', 'jefatur'),
                #            ('Reducciones mayores de 55 años', '55')]
                filtros = [('Tutorías', 'Tutor'), ('Jefaturas de departamento', 'jefatura'),
                           ('Reducciones mayores de 55 años', '55')]
                for filtro in filtros:
                    FiltroCupo.objects.create(cupo=cupo, nombre=filtro[0], filtro=filtro[1])
                # Especialidades, Etapas, Cursos, ...
                for pxls in po.plantillaxls_set.all():
                    if len(pxls.x_materiaomg) > 0:
                        try:
                            EspecialidadCupo.objects.get(cupo=cupo, clave_ex=pxls.x_puesto)
                        except:
                            ec = EspecialidadCupo.objects.create(cupo=cupo, departamento=None, nombre=pxls.puesto,
                                                                 clave_ex=pxls.x_puesto)
                            profesores_cupo = Profesores_cupo.objects.create(cupo=cupo, especialidad=ec)
                            geps = po.plantillaxls_set.filter(x_puesto=pxls.x_puesto).values_list('docente', flat=True)
                            for gep in list(set(geps)):
                                Profesor_cupo.objects.create(profesorado=profesores_cupo, nombre=gep)
                        try:
                            Materia_cupo.objects.get(clave_ex=pxls.x_materiaomg)
                        except:
                            ec, c = EtapaEscolarCupo.objects.get_or_create(cupo=cupo, nombre=pxls.etapa_escolar,
                                                                           clave_ex=pxls.x_etapa_escolar)
                            cc, c = CursoCupo.objects.get_or_create(cupo=cupo, nombre=pxls.curso, etapa_escolar=ec,
                                                                    nombre_especifico=pxls.omc, clave_ex=pxls.x_curso)
                            h, sc, m = pxls.horas_semana_min.rpartition(':')
                            try:
                                horas = int(h) + int(m) / 60
                            except:
                                return JsonResponse({'horas': pxls.horas_semana_min, 'h': h, 'm': m,
                                                     'etapa': pxls.x_etapa_escolar, 'x_materia': pxls.x_materiaomg})
                            Materia_cupo.objects.create(cupo=cupo, curso_cupo=cc, nombre=pxls.materia, horas=horas,
                                                        clave_ex=pxls.x_materiaomg)

                logger.info('%s, add_cupo id=%s' % (g_e, cupo.id))
                # ds = Departamento.objects.filter(ronda=cupo.ronda)
                # html = render_to_string('formulario_cupo.html', {'cupo': cupo, 'request': request, 'departamentos': ds})
                html = render_to_string('formulario_cupo.html', {'cupo': cupo, 'request': request})
                return JsonResponse({'ok': True, 'html': html})
            except Exception as msg:
                return JsonResponse({'ok': False, 'msg': str(msg)})

        elif action == 'copy_cupo' and g_e.has_permiso('copia_cupo_profesorado'):
            orig = Cupo.objects.get(id=request.POST['cupo'])
            if orig.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='l').count() < 1:
                return JsonResponse({'ok': False, 'msg': 'No tienes permiso para copiar el cupo'})
            cupo = Cupo.objects.create(ronda=g_e.ronda, nombre='(copia) %s' % (orig.nombre),
                                       max_completa=orig.max_completa, min_completa=orig.min_completa,
                                       max_dostercios=orig.max_dostercios, min_dostercios=orig.min_dostercios,
                                       max_media=orig.max_media, min_media=orig.min_media,
                                       max_tercio=orig.max_tercio, min_tercio=orig.min_tercio)
            CupoPermisos.objects.create(cupo=cupo, gauser=g_e.gauser, permiso='plwx')
            crea_departamentos(g_e.ronda)
            for e in orig.especialidadcupo_set.all():
                e.pk = None
                e.cupo = cupo
                try:
                    e.departamento = Departamento.objects.get(ronda=g_e.ronda, abreviatura=e.departamento.abreviatura)
                except:
                    e.departamento = None
                    crear_aviso(request, False, 'No se encuentra departamento para %s' % e.nombre)
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
                    curso = cupo.cursocupo_set.get(clave_ex=m.curso_cupo.clave_ex)
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
            ds = Departamento.objects.filter(ronda=g_e.ronda)
            html = render_to_string('formulario_cupo.html', {'cupo': cupo, 'request': request, 'departamentos': ds})
            return JsonResponse({'ok': True, 'html': html})

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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('bloquea_cupos')
                if con1 or con2:
                    bloquear = request.POST['bloquear']
                    logger.info('%s, bloquea_cupo %s %s' % (g_e, cupo.id, bloquear))
                    cupo.bloqueado = {'true': True, 'false': False}[bloquear]
                    cupo.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except:
                return JsonResponse({'ok': False})

        elif action == 'add_filtro':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('pdf_cupo')
                if con1 or con2:
                    logger.info('%s, add_filtro_cupo %s' % (g_e, cupo.id))
                    nombre = request.POST['nombre']
                    filtro = request.POST['filtro']
                    if len(filtro) > 0 and len(nombre) > 0:
                        f = FiltroCupo.objects.create(cupo=cupo, nombre=nombre, filtro=filtro)
                        return JsonResponse({'ok': True, 'filtro': render_to_string('filtro_cupo.html', {'filtro': f}),
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('pdf_cupo')
                if con1 or con2:
                    filtro = FiltroCupo.objects.get(cupo__ronda__entidad=g_e.ronda.entidad, cupo=cupo,
                                                    id=request.POST['filtro'])
                    id = filtro.id
                    filtro.delete()
                    return JsonResponse({'ok': True, 'filtro': id})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except:
                return JsonResponse({'ok': False})

        elif action == 'change_nombre_cupo' and g_e.has_permiso('edita_cupos'):
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                if not cupo.bloqueado:
                    logger.info('%s, change_nombre_cupo %s' % (g_e, cupo.id))
                    cupo.nombre = request.POST['nombre']
                    cupo.save()
                    return JsonResponse({'ok': True, 'nombre': cupo.nombre})
                else:
                    return JsonResponse({'ok': False})
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                                                            periodos=4, curso_cupo=curso)
                            materias_cupo = [m]
                        logger.info('%s, change_curso %s' % (g_e, curso.nombre))

                    especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                    materias = render_to_string('edit_cupo_materias.html',
                                                {'materias': materias_cupo, 'especialidades': especialidades,
                                                 's_c': True})
                    return JsonResponse({'ok': True, 'materias': materias})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_especialidad_global':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                                                 'especialidad': especialidad})
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                                                 's_c': s_c,
                                                 'especialidad': especialidad})
                    return JsonResponse({'ok': True, 'materias': materias})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_nombre_materia':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
                con2 = (cupo.ronda.entidad == g_e.ronda.entidad)
                if con1 or con2:
                    materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                    materia.pk = None
                    materia.nombre += ' (copia)'
                    materia.save()
                    especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                    especialidad = materia.especialidad
                    materias = render_to_string('edit_cupo_materias.html',
                                                {'materias': [materia], 'duplicated': True,
                                                 'especialidades': especialidades, 'especialidad': especialidad})
                    logger.info('%s, cupo %s duplicate_materia %s' % (g_e, cupo.id, materia.nombre))
                    return JsonResponse({'ok': True, 'materias': materias})
                else:
                    return JsonResponse({'ok': False, 'msg': 'No tienes permisos suficientes'})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'delete_materia':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'])
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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
                con1 = cupo.cupopermisos_set.filter(gauser=g_e.gauser, permiso__icontains='p').count() > 0
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

        elif action == 'change_profesor_cupo':
            try:
                cupo = request.POST['cupo']
                campo = request.POST['campo']
                valor = request.POST['valor']
                p_c = Profesor_cupo.objects.get(id=request.POST['id'], profesorado__cupo__id=cupo)
                if campo == 'bilingue':
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

        else:
            return JsonResponse({'ok': False, 'error': 'No tienes permiso para ejecutar lo solicitado'})
    else:
        return HttpResponse(status=400)


def clave_ex2int(curso):
    try:
        print(int(curso.etapa_escolar.clave_ex))
        return int(curso.etapa_escolar.clave_ex)
    except:
        return 0


# @permiso_required('edita_cupos')
def edit_cupo(request, cupo_id):
    g_e = request.session['gauser_extra']
    cupo = Cupo.objects.get(id=cupo_id)

    if not cupo.bloqueado:
        if request.method == 'POST':
            if request.POST['action'] == 'genera_informe':
                fichero = 'cupo%s_%s' % (str(cupo.ronda.entidad.code), cupo.id)
                texto_html = render_to_string('cupo2pdf.html', {'cupo': cupo, 'MEDIA_ANAGRAMAS': MEDIA_ANAGRAMAS})
                ruta = MEDIA_CUPO + '%s/' % cupo.ronda.entidad.code
                fich = html_to_pdf(request, texto_html, fichero=fichero, media=ruta, title='Cupo de la Entidad')
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
                return response

        # cursos = Curso.objects.filter(ronda=cupo.ronda)
        cursos = CursoCupo.objects.filter(cupo=cupo)
        cursos = sorted(cursos, key=lambda curso: clave_ex2int(curso))
        materias = Materia_cupo.objects.filter(curso_cupo=cursos[0], cupo=cupo)
        especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
        # s_c stands for 'selected course' and in case of taking True value means edit_cupo doesn't have to show course
        return render(request, "edit_cupo.html", {'formname': 'cupo', 'cupo': cupo, 'curso': cursos[0],
                                                  'materias': materias, 'especialidades': especialidades, 's_c': True,
                                                  'cursos': cursos,
                                                  'iconos':
                                                      ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'Informe',
                                                        'title': 'Generar el documento con el cupo',
                                                        'permiso': 'pdf_cupo'},
                                                       {'tipo': 'button', 'nombre': 'arrow-left',
                                                        'texto': 'Listado de cupos',
                                                        'title': 'Volver al listado de cupos disponibles',
                                                        'permiso': 'libre'},
                                                       ),
                                                  })
    else:
        return redirect('/cupo/')


# @permiso_required('acceso_carga_masiva_horarios')
def plantilla_organica(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST':
        if request.POST['action'] == 'carga_masiva_plantilla':
            logger.info('Carga de archivo de tipo: ' + request.FILES['file_masivo_xls'].content_type)
            CargaMasiva.objects.create(g_e=g_e, fichero=request.FILES['file_masivo_xls'], tipo='PLANTILLAXLS')
            carga_masiva_from_file.delay()
            crear_aviso(request, False, 'El archivo cargado puede tardar unos minutos en ser procesado.')
        elif request.POST['action'] == 'genera_xls':
            wboriginal = xlrd.open_workbook("/home/juanjo/Descargas/borrar/plantilla_organica.xls")
            shsec = wboriginal.sheet_by_index(0)
            shdiv = wboriginal.sheet_by_index(1)
            shcon = wboriginal.sheet_by_index(2)
            shcra = wboriginal.sheet_by_index(3)
            wbgenerado = xlwt.Workbook()
            shsecgen = wbgenerado.add_sheet('IES CIEPF HOJA 1', cell_overwrite_ok=True)
            shdivgen = wbgenerado.add_sheet('A. Diversidad HOJA 2', cell_overwrite_ok=True)
            shcongen = wbgenerado.add_sheet('CONSERVATORIOS', cell_overwrite_ok=True)
            shcragen = wbgenerado.add_sheet('CRA', cell_overwrite_ok=True)
            for r in range(shsec.nrows):
                for c in range(shsec.ncols):
                    shsecgen.write(r, c, shsec.cell(r, c).value)
            logger.info('Carga de archivo de tipo: ' + request.FILES['file_masivo_xls'].content_type)
            CargaMasiva.objects.create(g_e=g_e, fichero=request.FILES['file_masivo_xls'], tipo='PLANTILLAXLS')
            carga_masiva_from_file.delay()
            crear_aviso(request, False, 'El archivo cargado puede tardar unos minutos en ser procesado.')
        elif request.POST['action'] == 'open_accordion' and request.is_ajax():
            po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['id'])
            html = render_to_string('plantilla_organica_accordion_content.html', {'po': po, 'g_e': g_e})
            return JsonResponse({'ok': True, 'html': html})
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['id'])
                html = render_to_string('plantilla_organica_accordion_content.html', {'po': po, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'carga_parcial_plantilla' and request.is_ajax():
            po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
            funcion = request.POST['funcion']
            eval('po.' + funcion + '()')
            return JsonResponse({'ok': True})
        elif request.POST['action'] == 'tdpdocente' and request.is_ajax():
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
                ge = Gauser_extra.objects.get(ronda=po.ronda_centro, id=request.POST['ge'])
                departamento = Depentidad.objects.get(ronda=po.ronda_centro, id=request.POST['departamento'])
                pdcol = PDocenteCol.objects.get(pd__po=po, pd__g_e=ge, codecol=request.POST['codecol'])
                # Para evitar los caracteres no numéricos obtenidos del div contenteditable no basta con int():
                pdcol.periodos = int("".join(filter(str.isdigit, request.POST['valor'])))
                pdcol.save()
                data = get_columnas_docente(po, ge)
                html_departamento = render_to_string('plantilla_organica_accordion_content_tbody_departamento.html',
                                                     {'departamento': departamento, 'po': po})
                return JsonResponse({'ok': True, 'html_departamento': html_departamento,
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
        elif request.POST['action'] == 'update_dep_th':
            try:
                po = PlantillaOrganica.objects.get(g_e=g_e, id=request.POST['po'])
                departamento = Depentidad.objects.get(id=request.POST['departamento'])
                html = render_to_string('plantilla_organica_accordion_content_tbody_docente.html',
                                        {'po': po, 'departamento': departamento})
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
                horario = h.get_horario(docente)
                tabla = render_to_string('plantilla_organica_horario_docente.html', {'horario': horario,
                                                                                     'docente': docente})
                return JsonResponse({'ok': True, 'tabla': tabla, 'h': h.id, 'd': docente.id})
            except:
                return JsonResponse({'ok': False})

    plantillas_o = PlantillaOrganica.objects.filter(g_e=g_e)
    return render(request, "plantilla_organica.html",
                  {
                      'iconos': ({'tipo': 'button', 'nombre': 'cloud-upload', 'texto': 'Cargar datos',
                                  'title': 'Cargar datos a partir de archivo obtenido de Racima',
                                  'permiso': 'libre'}, {}),
                      'formname': 'plantilla_organica',
                      'plantillas_o': plantillas_o,
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })
