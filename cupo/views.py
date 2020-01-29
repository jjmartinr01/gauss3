# -*- coding: utf-8 -*-
import logging
import datetime

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext

from autenticar.control_acceso import permiso_required
from gauss.funciones import html_to_pdf
from gauss.rutas import *
from django.http import HttpResponse

from mensajes.models import Aviso
from mensajes.views import crear_aviso
from cupo.models import Cupo, Materia_cupo, Profesores_cupo, FiltroCupo, EspecialidadCupo, Profesor_cupo
from entidades.models import Subentidad
from estudios.models import Curso, Materia
from django.template.loader import render_to_string

from programaciones.models import Gauser_extra_programaciones, Departamento, crea_departamentos

logger = logging.getLogger('django')

# Algunos cuerpos contienen las mismas especialidades, por ejemplo 590 (profe secundaria) y 511 (catedrático secund.)
# Para el cupo únicamente importa la especialidad así que para evitar duplicidades en las especialidades
# se toman únicamente los siguientes cuerpos:
CUERPOS_CUPO = ('590', '591', '592', '593', '594', '595', '596')


# @permiso_required('acceso_cupo_profesorado')
def cupo(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        if request.POST['action'] == 'genera_informe':
            cupo = Cupo.objects.get(id=request.POST['cupo'], ronda__entidad=g_e.ronda.entidad)
            fichero = 'cupo%s_%s' % (str(cupo.ronda.entidad.code), cupo.id)
            texto_html = render_to_string('cupo2pdf.html', {'cupo': cupo, 'MEDIA_ANAGRAMAS': MEDIA_ANAGRAMAS})
            ruta = MEDIA_CUPO + '%s/' % cupo.ronda.entidad.code
            fich = html_to_pdf(request, texto_html, fichero=fichero, media=ruta, title=u'Cupo de la Entidad')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            logger.info(u'%s, genera pdf del cupo %s' % (g_e, cupo.id))
            return response

    cupos = Cupo.objects.filter(ronda__entidad=g_e.ronda.entidad)
    return render(request, "cupo.html", {'formname': 'cupo_profesorado', 'cupos': cupos})


def cupo_especialidad(cupo, especialidad):
    materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=especialidad)
    profesores_cupo, created = Profesores_cupo.objects.get_or_create(cupo=cupo, especialidad=especialidad)
    if created:
        geps = Gauser_extra_programaciones.objects.filter(ge__ronda=cupo.ronda, puesto=especialidad.nombre)
        for gep in geps:
            Profesor_cupo.objects.create(profesorado=profesores_cupo, nombre=gep.ge.gauser.get_full_name())
    profesores_cupo.num_periodos = sum([m.total_periodos for m in materias_cupo])
    profesores_cupo.save()
    return profesores_cupo

def crear_profesores_cupo(cupo):
    p_cs = Profesores_cupo.objects.filter(cupo=cupo)
    for p_c in p_cs:
        geps = Gauser_extra_programaciones.objects.filter(ge__ronda=cupo.ronda, puesto=p_c.especialidad.nombre)
        if geps.count() == 0:
            Profesor_cupo.objects.create(profesorado=p_c, nombre='Profesor Interino', tipo='NONE')
        for gep in geps:
            Profesor_cupo.objects.create(profesorado=p_c, nombre=gep.ge.gauser.get_full_name())
    return True

def ajax_cupo(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        action = request.POST['action']
        if action == 'add_cupo' and g_e.has_permiso('crea_cupos'):
            try:
                crea_departamentos(g_e.ronda)
                cupo = Cupo.objects.create(ronda=g_e.ronda, nombre='Cupo creado el %s' % (datetime.datetime.now()))
                geps = Gauser_extra_programaciones.objects.filter(ge__ronda=g_e.ronda).order_by('puesto')
                for pd in geps.values_list('puesto', 'departamento__id').distinct():
                    if pd[0]:
                        ec, c = EspecialidadCupo.objects.get_or_create(cupo=cupo, nombre=pd[0])
                        if c and pd[1]:
                            departamento = Departamento.objects.get(ronda=g_e.ronda, id=pd[1])
                            ec.departamento = departamento
                            ec.save()
                materias = Materia.objects.filter(curso__ronda=g_e.ronda)
                for m in materias:
                    try:
                        c = Curso.objects.get(ronda=g_e.ronda, nombre=m.curso.nombre)
                    except:
                        c = None
                    try:
                        horas = m.horas
                    except:
                        horas = 0
                    Materia_cupo.objects.create(cupo=cupo, curso=c, nombre=m.nombre, periodos=horas)
                logger.info(u'%s, add_cupo id=%s' % (g_e, cupo.id))
                ds = Departamento.objects.filter(ronda=g_e.ronda)
                html = render_to_string('formulario_cupo.html', {'cupo': cupo, 'request': request, 'departamentos': ds})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

        elif action == 'copy_cupo' and g_e.has_permiso('copia_cupo_profesorado'):
            orig = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
            cupo = Cupo.objects.create(ronda=g_e.ronda, nombre='(copia) %s' % (orig.nombre),
                                       max_completa=orig.max_completa, min_completa=orig.min_completa,
                                       max_dostercios=orig.max_dostercios, min_dostercios=orig.min_dostercios,
                                       max_media=orig.max_media, min_media=orig.min_media,
                                       max_tercio=orig.max_tercio, min_tercio=orig.min_tercio)
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
            for m in orig.materia_cupo_set.all():
                m.pk = None
                m.cupo = cupo
                try:
                    especialidad = EspecialidadCupo.objects.get(cupo=cupo, nombre=m.especialidad.nombre)
                    m.especialidad = especialidad
                except:
                    m.especialidad = None
                try:
                    curso = Curso.objects.get(ronda=g_e.ronda, clave_ex=m.curso.clave_ex)
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

            logger.info(u'%s, copy_cupo id=%s -> id=%s' % (g_e, orig.id, cupo.id))
            ds = Departamento.objects.filter(ronda=g_e.ronda)
            html = render_to_string('formulario_cupo.html', {'cupo': cupo, 'request': request, 'departamentos': ds})
            return JsonResponse({'ok': True, 'html': html})

        elif action == 'delete_cupo' and g_e.has_permiso('borra_cupo_profesorado'):
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                logger.info(u'%s, delete_cupo %s' % (g_e, cupo.id))
                cupo.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})

        elif action == 'bloquea_cupo' and g_e.has_permiso('bloquea_cupos'):
            try:
                bloquear = request.POST['bloquear']
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                logger.info(u'%s, bloquea_cupo %s %s' % (g_e, cupo.id, bloquear))
                cupo.bloqueado = {'true': True, 'false': False}[bloquear]
                cupo.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})

        elif action == 'add_filtro' and g_e.has_permiso('pdf_cupo'):
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                logger.info(u'%s, add_filtro_cupo %s' % (g_e, cupo.id))
                nombre = request.POST['nombre']
                filtro = request.POST['filtro']
                if len(filtro) > 0 and len(nombre) > 0:
                    f = FiltroCupo.objects.create(cupo=cupo, nombre=nombre, filtro=filtro)
                    return JsonResponse({'ok': True, 'filtro': render_to_string('filtro_cupo.html', {'filtro': f}),
                                         'cupo': cupo.id})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})

        elif action == 'delete_filtro' and g_e.has_permiso('pdf_cupo'):
            try:
                filtro = FiltroCupo.objects.get(cupo__ronda__entidad=g_e.ronda.entidad, cupo=request.POST['cupo'],
                                                id=request.POST['filtro'])
                id = filtro.id
                filtro.delete()
                return JsonResponse({'ok': True, 'filtro': id})
            except:
                return JsonResponse({'ok': False})

        elif action == 'change_nombre_cupo' and g_e.has_permiso('edita_cupos'):
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                if not cupo.bloqueado:
                    logger.info(u'%s, change_nombre_cupo %s' % (g_e, cupo.id))
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
                    logger.info(u'%s, update_departamento %s' % (g_e, cupo.id))
                    especialidad = EspecialidadCupo.objects.get(cupo=cupo, id=request.POST['especialidad'])
                    departamento = Departamento.objects.get(ronda=g_e.ronda, id=request.POST['departamento'])
                    especialidad.departamento = departamento
                    especialidad.save()
                    return JsonResponse({'ok': True, 'nombre': cupo.nombre})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_max_min_cupo':  # and g_e.has_permiso('edita_cupos'):
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                if not cupo.bloqueado:
                    attr = request.POST['attr']
                    logger.info(u'%s, change_%s %s' % (g_e, attr, cupo.id))
                    setattr(cupo, attr, request.POST['valor'])
                    cupo.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})

        elif action == 'change_curso':
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                if not request.POST['curso']:
                    materias_cupo = Materia_cupo.objects.filter(cupo=cupo, curso=None)
                    if not materias_cupo:
                        m = Materia_cupo.objects.create(cupo=cupo, min_num_alumnos=1, max_num_alumnos=100,
                                                        nombre="Actividad/Materia no asociada a ningún curso",
                                                        periodos=2)
                        materias_cupo = [m]
                    logger.info(u'%s, change_curso empty' % (g_e))
                elif request.POST['curso'] == 'any_course':
                    materias_cupo = Materia_cupo.objects.filter(cupo=cupo)
                    logger.info(u'%s, change_curso any_course' % g_e)
                else:
                    curso = Curso.objects.get(id=request.POST['curso'], ronda=cupo.ronda)
                    materias_cupo = Materia_cupo.objects.filter(cupo=cupo, curso=curso)
                    if not materias_cupo:  # Por ejemplo en un cupo creado antes que un determinado curso
                        m = Materia_cupo.objects.create(cupo=cupo, min_num_alumnos=15, max_num_alumnos=35,
                                                        nombre="Actividad/Materia creada automáticamente",
                                                        periodos=4, curso=curso)
                        materias_cupo = [m]
                    logger.info(u'%s, change_curso %s' % (g_e, curso.nombre))

                especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                materias = render_to_string('edit_cupo_materias.html',
                                            {'materias': materias_cupo, 'especialidades': especialidades, 's_c': True})
                return JsonResponse({'ok': True, 'materias': materias})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_especialidad_global':
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                if request.POST['especialidad']:
                    especialidad = EspecialidadCupo.objects.get(id=request.POST['especialidad'], cupo=cupo)
                    profesores_cupo = cupo_especialidad(cupo, especialidad).reparto_profes
                    materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=especialidad)
                    especialidad_nombre = especialidad.nombre
                    logger.info(u'%s, change_especialidad_global %s' % (g_e, especialidad_nombre))
                else:
                    materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=None)
                    profesores_cupo = None
                    especialidad_nombre = None
                    especialidad = None
                    logger.info(u'%s, change_especialidad_global sin especialidad' % (g_e))
                especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                materias = render_to_string('edit_cupo_materias.html',
                                            {'materias': materias_cupo, 'especialidades': especialidades,
                                             'especialidad': especialidad})
                return JsonResponse({'ok': True, 'materias': materias, 'profesores_cupo': profesores_cupo,
                                     'especialidad': especialidad_nombre})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'filtro_materia':
            q = request.POST['q']
            s_c = True
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                especialidad = None
                if request.POST['especialidad'] == 'empty':
                    if not request.POST['curso']:
                        materias_cupo = Materia_cupo.objects.filter(cupo=cupo, curso=None, nombre__icontains=q)
                        s_c = False
                        logger.info(u'%s, filtro_materia no asociadas a curso' % (g_e))
                    elif request.POST['curso'] == 'any_course':
                        materias_cupo = Materia_cupo.objects.filter(cupo=cupo, nombre__icontains=q)
                        s_c = False
                        logger.info(u'%s, filtro_materia any_course' % g_e)
                    else:
                        curso = Curso.objects.get(id=request.POST['curso'], entidad=g_e.ronda.entidad)
                        materias_cupo = Materia_cupo.objects.filter(cupo=cupo, curso=curso, nombre__icontains=q)
                        logger.info(u'%s, filtro_materia %s' % (g_e, curso.nombre))
                else:
                    if request.POST['especialidad']:
                        especialidad_id = request.POST['especialidad']
                        especialidad = EspecialidadCupo.objects.get(id=especialidad_id, cupo=cupo)
                        materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=especialidad,
                                                                    nombre__icontains=q)
                        s_c = False
                        logger.info(u'%s, filtro_materia %s' % (g_e, especialidad.nombre))
                    else:
                        materias_cupo = Materia_cupo.objects.filter(cupo=cupo, especialidad=None, nombre__icontains=q)
                        s_c = False
                        logger.info(u'%s, filtro_materia sin especialidad' % (g_e))
                especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                materias = render_to_string('edit_cupo_materias.html',
                                            {'materias': materias_cupo, 'especialidades': especialidades, 's_c': s_c,
                                             'especialidad': especialidad})
                return JsonResponse({'ok': True, 'materias': materias})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_nombre_materia':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'], ronda__entidad=g_e.ronda.entidad)
                materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                logger.info(u'%s, cupo %s change_nombre_materia "%s" -> "%s"' % (
                    g_e, cupo.id, materia.nombre, request.POST['nombre']))
                materia.nombre = request.POST['nombre']
                materia.save()
                return JsonResponse({'ok': True, 'nombre_materia': materia.nombre})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'duplicate_materia':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'], ronda__entidad=g_e.ronda.entidad)
                materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                materia.pk = None
                materia.nombre += ' (copia)'
                materia.save()
                especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
                especialidad = materia.especialidad
                materias = render_to_string('edit_cupo_materias.html',
                                            {'materias': [materia], 'duplicated': True,
                                             'especialidades': especialidades, 'especialidad': especialidad})
                logger.info(u'%s, cupo %s duplicate_materia %s' % (g_e, cupo.id, materia.nombre))
                return JsonResponse({'ok': True, 'materias': materias})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'delete_materia':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'], ronda__entidad=g_e.ronda.entidad)
                materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                logger.info(u'%s, cupo %s delete_materia %s' % (g_e, cupo.id, materia.nombre))
                materia.delete()
                return JsonResponse({'ok': True})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_num_periodos':
            try:
                cupo = Cupo.objects.get(id=request.POST['cupo'], ronda__entidad=g_e.ronda.entidad)
                materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                logger.info(u'%s, cupo %s - %s, %s -> %s' % (
                    g_e, cupo.id, materia.nombre, materia.periodos, request.POST['periodos']))
                materia.periodos = request.POST['periodos']
                materia.save()
                if materia.especialidad:
                    profesores_cupo = cupo_especialidad(cupo, materia.especialidad)
                    return JsonResponse({'ok': True, 'profesores_cupo': profesores_cupo.reparto_profes,
                                         'especialidad': materia.especialidad.nombre})
                else:
                    return JsonResponse({'ok': True, 'especialidad': ''})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_especialidad_materia':
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                try:
                    especialidad = EspecialidadCupo.objects.get(id=request.POST['especialidad'], cupo=cupo)
                except:
                    especialidad = None
                materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                materia.especialidad = especialidad
                materia.save()
                logger.info(u'%s, cupo %s - %s -> %s' % (g_e, cupo.id, materia.nombre, materia.especialidad))
                if materia.especialidad:
                    profesores_cupo = cupo_especialidad(cupo, materia.especialidad)
                    return JsonResponse({'materia': materia.id, 'profesores_cupo': profesores_cupo.reparto_profes,
                                         'especialidad': materia.especialidad.nombre, 'ok': True})
                else:
                    return JsonResponse({'ok': True, 'especialidad': '', 'materia': materia.id})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'mouseover_especialidad_materia':
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                especialidad = EspecialidadCupo.objects.get(id=request.POST['especialidad'], cupo=cupo)
                profesores_cupo = cupo_especialidad(cupo, especialidad)
                return JsonResponse({'ok': True, 'profesores_cupo': profesores_cupo.reparto_profes,
                                     'especialidad': especialidad.nombre})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_num_alumnos':
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                logger.info(u'%s, cupo %s - %s change_num_alumnos %s -> %s' % (
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
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_max_num_alumnos':
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                logger.info(u'%s, en el cupo %s - %s max_num_alumnos %s -> %s' % (
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
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_min_num_alumnos':
            try:
                cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=request.POST['cupo'])
                materia = Materia_cupo.objects.get(id=request.POST['materia'], cupo=cupo)
                logger.info(u'%s, cupo %s - %s change_min_num_alumnos %s -> %s' % (
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
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})

        elif action == 'change_profesor_cupo':
            try:
                campo = request.POST['campo']
                valor = request.POST['valor']
                p_c = Profesor_cupo.objects.get(id=request.POST['id'], profesorado__cupo__ronda__entidad=g_e.ronda.entidad)
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


# @permiso_required('edita_cupos')
def edit_cupo(request, cupo_id):
    g_e = request.session['gauser_extra']
    cupo = Cupo.objects.get(ronda__entidad=g_e.ronda.entidad, id=cupo_id)
    if not cupo.bloqueado:
        if request.method == 'POST':
            if request.POST['action'] == 'genera_informe':
                fichero = 'cupo%s_%s' % (str(cupo.ronda.entidad.code), cupo.id)
                texto_html = render_to_string('cupo2pdf.html', {'cupo': cupo, 'MEDIA_ANAGRAMAS': MEDIA_ANAGRAMAS})
                ruta = MEDIA_CUPO + '%s/' % cupo.ronda.entidad.code
                fich = html_to_pdf(request, texto_html, fichero=fichero, media=ruta, title=u'Cupo de la Entidad')
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
                return response

        cursos = Curso.objects.filter(ronda=cupo.ronda)
        materias = Materia_cupo.objects.filter(curso=cursos[0], cupo=cupo)
        especialidades = EspecialidadCupo.objects.filter(cupo=cupo)
        # s_c stands for 'selected course' and in case of taking True value means edit_cupo doesn't have to show course
        return render(request, "edit_cupo.html", {'formname': 'cupo', 'cupo': cupo, 'curso': cursos[0],
                                                  'materias': materias, 'especialidades': especialidades, 's_c': True,
                                                  'cursos': cursos,
                                                  'iconos':
                                                      ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'Informe',
                                                        'title': 'Generar el documento con el cupo',
                                                        'permiso': 'pdf_cupo'},),
                                                  })
    else:
        return redirect('/cupo/')
