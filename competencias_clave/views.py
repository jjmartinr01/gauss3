# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pdfkit
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render

# Create your views here.
from django.template.loader import render_to_string

from entidades.models import Gauser_extra
from gauss.funciones import get_dce
from horarios.models import Sesion, Horario, SesionExtra
from estudios.models import Grupo, Gauser_extra_estudios, Materia, Curso
from competencias_clave.models import CompetenciasMateria, CompetenciasMateriaAlumno
from mensajes.models import Aviso
from gauss.rutas import MEDIA_CC
from autenticar.control_acceso import permiso_required

logger = logging.getLogger('django')

@permiso_required('cc_valorar_mis_alumnos')
def cc_valorar_mis_alumnos(request):
    g_e = request.session["gauser_extra"]
    # Etapas afectas-> da:secundaria
    etapas = ['da']
    if request.method == 'GET':
        if 'm' in request.GET:
            id = request.GET['m']

    horario = Horario.objects.get(ronda=g_e.ronda, predeterminado=True)
    sesextras = SesionExtra.objects.filter(sesion__horario=horario, sesion__g_e=g_e, grupo__isnull=False)
    sesiones_ids = sesextras.values_list('sesion__id', flat=True)
    # sesiones = Sesion.objects.filter(horario=horario, g_e=g_e, grupo__isnull=False)
    sesiones = Sesion.objects.filter(id__in=sesiones_ids)
    materias_id = sesiones.values_list('materia__id', flat=True).distinct()
    materias = Materia.objects.filter(id__in=materias_id, curso__etapa__in=etapas)
    try:
        materia_seleccionada = materias.get(id=id)
    except:
        try:
            materia_seleccionada = materias[0]
        except:
            materia_seleccionada = None
    competenciasmateria, c = CompetenciasMateria.objects.get_or_create(ronda=g_e.ronda, materia=materia_seleccionada)

    # grupos_id_materia_seleccionada = sesiones.filter(materia=materia_seleccionada).values_list('grupo__id',
    #                                                                                            flat=True).distinct()
    grupos_id_materia_seleccionada = sesextras.filter(materia=materia_seleccionada).values_list('grupo__id', flat=True).distinct()
    grupos_materia_seleccionada = Grupo.objects.filter(id__in=grupos_id_materia_seleccionada)
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'mod_percentage':
            try:
                competenciasmateria = CompetenciasMateria.objects.get(id=request.POST['cm'])
                setattr(competenciasmateria, request.POST['cc'], int(request.POST['v']))
                competenciasmateria.save()
                t = competenciasmateria.total_percentage
                mensaje = False
                if (100 - t) < 0:
                    setattr(competenciasmateria, request.POST['cc'], int(request.POST['v']) + 100 - t)
                    competenciasmateria.save()
                    mensaje = True
                return JsonResponse({'ok': True, 'total': t, 'mensaje': mensaje,
                                     'valor': getattr(competenciasmateria, request.POST['cc'])})
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            alumnos = Gauser_extra_estudios.objects.filter(grupo__id=request.POST['id'])
            cm = CompetenciasMateria.objects.get(id=request.POST['cm'])
            for a in alumnos:
                CompetenciasMateriaAlumno.objects.get_or_create(profesor=g_e, alumno=a.ge, materia=cm)
            cmas = CompetenciasMateriaAlumno.objects.filter(profesor=g_e, materia=cm,
                                                            alumno__gauser_extra_estudios__grupo__id=request.POST['id'])
            html = render_to_string('cc_alumnos_grupo.html', {'cmas': cmas.order_by('alumno__gauser__last_name')})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'mod_valor':
            try:
                competenciasmateriaalumno = CompetenciasMateriaAlumno.objects.get(id=request.POST['cma'])
                setattr(competenciasmateriaalumno, request.POST['cc'], int(request.POST['v']))
                competenciasmateriaalumno.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'nota':
            try:
                nota = int(request.POST['nota'])
                ccs = ['ccl', 'cmct', 'cd', 'cpaa', 'csc', 'sie', 'cec']
                competenciasmateriaalumno = CompetenciasMateriaAlumno.objects.get(id=request.POST['cma'], profesor=g_e)
                for cc in ccs:
                    setattr(competenciasmateriaalumno, cc, nota)
                    competenciasmateriaalumno.save()
                return JsonResponse({'ok': True, 'nota': nota})
            except:
                return JsonResponse({'ok': False})
    elif request.method == 'POST':
        if request.POST['action'] == 'informe_pdf' and g_e.has_permiso('genera_informe_ccs'):
            doc_cc = 'Configuración de informes Competencias Clave'
            dce = get_dce(g_e.ronda.entidad, doc_cc)
            cmas = CompetenciasMateriaAlumno.objects.filter(profesor__ronda=g_e.ronda,
                                                            materia__materia__curso__etapa__in=etapas)
            ids = cmas.values_list('alumno', flat=True).distinct()
            alumnos = Gauser_extra.objects.filter(id__in=ids).order_by('gauser_extra_estudios__grupo')
            fichero = 'valoracionesCC_%s.pdf' % str(g_e.ronda.entidad.code)
            c = render_to_string('valoracionescc2pdf.html', {'alumnos': alumnos,})
            fich = pdfkit.from_string(c, False, dce.get_opciones)
            logger.info('%s, pdf_cc_valorar_mis_alumnos' % g_e)
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=%s' % fichero
            return response

    return render(request, "cc_valorar_mis_alumnos.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'Informe',
                            'title': 'Generar informe competencias clave',
                            'permiso': 'genera_informe_ccs'},
                           ),
                      'formname': 'cc_valorar_mis_alumnos',
                      'materias': materias,
                      'materia_seleccionada': materia_seleccionada,
                      'grupos_materia_seleccionada': grupos_materia_seleccionada,
                      'competenciasmateria': competenciasmateria
                  })


@permiso_required('cc_valorar_cualquier_alumno')
def cc_valorar_cualquier_alumno(request):
    g_e = request.session["gauser_extra"]
    # Etapas afectas-> da:secundaria
    etapas = ['da']
    if request.method == 'GET':
        if 'm' in request.GET:
            id = request.GET['m']
        if 'u' in request.GET:
            u = request.GET['u']

    horario = Horario.objects.get(entidad=g_e.ronda.entidad, predeterminado=True)
    profesores_id = Sesion.objects.filter(horario=horario, materia__curso__etapa__in=etapas).values_list('g_e__id',
                                                                                                         flat=True)
    profesores = Gauser_extra.objects.filter(id__in=profesores_id)
    try:
        profesor = profesores.get(id=u, ronda=g_e.ronda)
    except:
        profesor = g_e
    sesiones = Sesion.objects.filter(horario=horario, g_e=profesor, grupo__isnull=False)
    materias_id = sesiones.values_list('materia__id', flat=True).distinct()
    materias = Materia.objects.filter(id__in=materias_id, curso__etapa__in=etapas)
    try:
        materia_seleccionada = materias.get(id=id)
    except:
        try:
            materia_seleccionada = materias[0]
        except:
            materia_seleccionada = None
    competenciasmateria, c = CompetenciasMateria.objects.get_or_create(ronda=g_e.ronda, materia=materia_seleccionada)
    grupos_id_materia_seleccionada = sesiones.filter(materia=materia_seleccionada).values_list('grupo__id',
                                                                                               flat=True).distinct()
    grupos_materia_seleccionada = Grupo.objects.filter(id__in=grupos_id_materia_seleccionada)
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'mod_percentage':
            try:
                competenciasmateria = CompetenciasMateria.objects.get(id=request.POST['cm'])
                setattr(competenciasmateria, request.POST['cc'], int(request.POST['v']))
                competenciasmateria.save()
                t = competenciasmateria.total_percentage
                mensaje = False
                if (100 - t) < 0:
                    setattr(competenciasmateria, request.POST['cc'], int(request.POST['v']) + 100 - t)
                    competenciasmateria.save()
                    mensaje = True
                return JsonResponse({'ok': True, 'total': t, 'mensaje': mensaje,
                                     'valor': getattr(competenciasmateria, request.POST['cc'])})
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            try:
                profesor = profesores.get(id=request.POST['profesor'], ronda=g_e.ronda)
            except:
                profesor = g_e
            alumnos = Gauser_extra_estudios.objects.filter(grupo__id=request.POST['id'])
            cm = CompetenciasMateria.objects.get(id=request.POST['cm'])
            for a in alumnos:
                CompetenciasMateriaAlumno.objects.get_or_create(profesor=profesor, alumno=a.ge, materia=cm)
            cmas = CompetenciasMateriaAlumno.objects.filter(profesor=profesor, materia=cm,
                                                            alumno__gauser_extra_estudios__grupo__id=request.POST['id'])
            html = render_to_string('cc_alumnos_grupo.html', {'cmas': cmas.order_by('alumno__gauser__last_name')})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'mod_valor':
            try:
                competenciasmateriaalumno = CompetenciasMateriaAlumno.objects.get(id=request.POST['cma'])
                setattr(competenciasmateriaalumno, request.POST['cc'], int(request.POST['v']))
                competenciasmateriaalumno.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'nota':
            try:
                nota = int(request.POST['nota'])
                ccs = ['ccl', 'cmct', 'cd', 'cpaa', 'csc', 'sie', 'cec']
                competenciasmateriaalumno = CompetenciasMateriaAlumno.objects.get(id=request.POST['cma'])
                for cc in ccs:
                    setattr(competenciasmateriaalumno, cc, nota)
                    competenciasmateriaalumno.save()
                return JsonResponse({'ok': True, 'nota': nota})
            except:
                return JsonResponse({'ok': False})
    elif request.method == 'POST':
        if request.POST['action'] == 'informe_pdf' and g_e.has_permiso('genera_informe_ccs'):
            doc_cc = 'Configuración de informes Competencias Clave'
            dce = get_dce(g_e.ronda.entidad, doc_cc)
            cmas = CompetenciasMateriaAlumno.objects.filter(profesor__ronda=g_e.ronda,
                                                            materia__materia__curso__etapa__in=etapas)
            ids = cmas.values_list('alumno', flat=True).distinct()
            alumnos = Gauser_extra.objects.filter(id__in=ids).order_by('gauser_extra_estudios__grupo')
            fichero = 'valoracionesCC_%s.pdf' % str(g_e.ronda.entidad.code)
            c = render_to_string('valoracionescc2pdf.html', {'alumnos': alumnos, 'profesores': profesores})
            fich = pdfkit.from_string(c, False, dce.get_opciones)
            logger.info('%s, pdf_cc_valorar_cualquier_alumno' % g_e)
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero
            return response

    return render(request, "cc_valorar_cualquier_alumno.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'Informe',
                            'title': 'Generar informe competencias clave',
                            'permiso': 'genera_informe_ccs'},
                           ),
                      'formname': 'cc_valorar_cualquier_alumno',
                      'profesores': profesores,
                      'profesor': profesor,
                      'materias': materias,
                      'materia_seleccionada': materia_seleccionada,
                      'grupos_materia_seleccionada': grupos_materia_seleccionada,
                      'competenciasmateria': competenciasmateria
                  })



@permiso_required('configura_ccs')
def cc_configuracion(request):
    g_e = request.session["gauser_extra"]
    # Etapas afectas-> da:secundaria
    etapas = ['da']
    materias = Materia.objects.filter(curso__ronda=g_e.ronda)
    for materia in materias:
        CompetenciasMateria.objects.get_or_create(materia=materia, ronda=g_e.ronda)
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'mod_percentage':
            try:
                competenciasmateria = CompetenciasMateria.objects.get(id=request.POST['materia'])
                setattr(competenciasmateria, request.POST['cc'], int(request.POST['valor']))
                competenciasmateria.save()
                t = competenciasmateria.total_percentage
                mensaje = False
                if (100 - t) < 0:
                    setattr(competenciasmateria, request.POST['cc'], int(request.POST['valor']) + 100 - t)
                    competenciasmateria.save()
                    mensaje = True
                valor = getattr(competenciasmateria, request.POST['cc'])
                return JsonResponse({'ok': True, 'total': t, 'mensaje': mensaje, 'cm': competenciasmateria.id,
                                     'valor': valor, 'cc': request.POST['cc']})
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            curso = Curso.objects.get(id=request.POST['id'], ronda=g_e.ronda)
            materias = CompetenciasMateria.objects.filter(materia__curso=curso)
            html = render_to_string('cc_configuracion_curso_content.html', {'materias': materias})
            return JsonResponse({'ok': True, 'html': html})
            alumnos = Gauser_extra_estudios.objects.filter(grupo__id=request.POST['id'])
            cm = CompetenciasMateria.objects.get(id=request.POST['cm'])
            for a in alumnos:
                CompetenciasMateriaAlumno.objects.get_or_create(profesor=g_e, alumno=a.ge, materia=cm)
            cmas = CompetenciasMateriaAlumno.objects.filter(profesor=g_e, materia=cm,
                                                            alumno__gauser_extra_estudios__grupo__id=request.POST['id'])
            html = render_to_string('cc_alumnos_grupo.html', {'cmas': cmas.order_by('alumno__gauser__last_name')})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'mod_valor':
            try:
                competenciasmateriaalumno = CompetenciasMateriaAlumno.objects.get(id=request.POST['cma'])
                setattr(competenciasmateriaalumno, request.POST['cc'], int(request.POST['v']))
                competenciasmateriaalumno.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'nota':
            try:
                nota = int(request.POST['nota'])
                ccs = ['ccl', 'cmct', 'cd', 'cpaa', 'csc', 'sie', 'cec']
                competenciasmateriaalumno = CompetenciasMateriaAlumno.objects.get(id=request.POST['cma'], profesor=g_e)
                for cc in ccs:
                    setattr(competenciasmateriaalumno, cc, nota)
                    competenciasmateriaalumno.save()
                return JsonResponse({'ok': True, 'nota': nota})
            except:
                return JsonResponse({'ok': False})
    elif request.method == 'POST':
        if request.POST['action'] == 'informe_pdf' and g_e.has_permiso('genera_informe_ccs'):
            doc_cc = 'Configuración de informes Competencias Clave'
            dce = get_dce(g_e.ronda.entidad, doc_cc)
            cmas = CompetenciasMateriaAlumno.objects.filter(profesor__ronda=g_e.ronda,
                                                            materia__materia__curso__etapa__in=etapas)
            ids = cmas.values_list('alumno', flat=True).distinct()
            alumnos = Gauser_extra.objects.filter(id__in=ids).order_by('gauser_extra_estudios__grupo')
            fichero = 'valoracionesCC_%s.pdf' % str(g_e.ronda.entidad.code)
            c = render_to_string('valoracionescc2pdf.html', {'alumnos': alumnos, })
            fich = pdfkit.from_string(c, False, dce.get_opciones)
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero
            return response

    respuesta = {
        'formname': 'configura_materias_pendientes',
        'cursos': Curso.objects.filter(ronda=g_e.ronda, etapa='da'),
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)}
    return render(request, "cc_configuracion.html", respuesta)
    # return render(request, "cc_valorar_mis_alumnos.html",
    #               {
    #                   'iconos':
    #                       ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'Informe',
    #                         'title': 'Generar informe competencias clave',
    #                         'permiso': 'genera_informe_ccs'},
    #                        ),
    #                   'formname': 'cc_valorar_mis_alumnos',
    #                   'materias': materias,
    #                   'materia_seleccionada': materia_seleccionada,
    #                   'grupos_materia_seleccionada': grupos_materia_seleccionada,
    #                   'competenciasmateria': competenciasmateria
    #               })
