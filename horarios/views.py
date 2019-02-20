# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import simplejson as json
from difflib import get_close_matches

import xlwt
from lxml import etree as ElementTree
from datetime import datetime, timedelta, time, date

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.files import File
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify

from autenticar.control_acceso import permiso_required
from gauss.funciones import usuarios_de_gauss, html_to_pdf
from gauss.rutas import MEDIA_ACTILLAS
from estudios.models import Curso, Grupo, Materia, Gauser_extra_estudios
from horarios.models import Horario, Tramo_horario, Actividad, Sesion, Falta_asistencia, Guardia
from entidades.models import *
from mensajes.models import Aviso
from mensajes.views import crear_aviso
from programaciones.models import Especialidad_entidad, Gauser_extra_programaciones, Departamento, \
    Especialidad_funcionario, crea_departamentos

logger = logging.getLogger('django')


@permiso_required(['acceso_actillas', 'acceso_actillas2'])
def actillas(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST':
        grupos = Grupo.objects.filter(id__in=request.POST.getlist('grupo'))
        fichero = 'actillaS_' + str(g_e.ronda.entidad.code) + '_' + slugify(datetime.now())
        c = render_to_string('actillas2pdf.html', {'grupos': grupos, })
        fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_ACTILLAS, title=u'Actilla de evaluación')
        response = HttpResponse(fich, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=' + fichero
        return response
    if g_e.has_permiso('genera_actillas') or g_e.has_permiso('genera_actillas2'):
        grupos = Grupo.objects.filter(ronda=g_e.ronda)
    else:
        grupos_id = Gauser_extra_estudios.objects.filter(Q(tutor=g_e) | Q(cotutor=g_e),
                                                         Q(grupo__ronda=g_e.ronda)).values_list('grupo__id', flat=True)
        grupos = Grupo.objects.filter(id__in=grupos_id).distinct()
    return render(request, "actillas.html",
                  {
                      'formname': 'actillas_evaluacion',
                      'grupos': grupos
                  })


@permiso_required('acceso_actividades_horarios')
def actividades_horarios(request):
    g_e = request.session["gauser_extra"]
    actividades = Actividad.objects.filter(entidad=g_e.ronda.entidad)

    if request.is_ajax():
        action = request.POST['action']
        if action == 'add_actividad':
            actividad = Actividad.objects.create(entidad=g_e.ronda.entidad, nombre="Nueva actividad para el horario",
                                                 observaciones="Creada el %s" % datetime.now())
            forloop = {'counter': Actividad.objects.filter(entidad=g_e.ronda.entidad).count()}
            html = render_to_string('actividad_horario_row.html', {'a': actividad, 'forloop': forloop})
            return JsonResponse({'actividad': html})
        if action == 'duplicate_actividad':
            try:
                actividad = Actividad.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id'])
                actividad.pk = None
                actividad.observaciones = "Creada el %s" % datetime.now()
                actividad.clave_ex = ''
                actividad.save()
                html = render_to_string('actividad_horario_row.html',
                                        {'a': actividad, 'duplicated': True, 'forloop': {'counter': 1}})
                return JsonResponse({'ok': True, 'actividad': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'delete_actividad':
            Actividad.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id']).delete()
            return JsonResponse({'id': request.POST['id']})
        elif action == 'ob_actividad':
            actividad = Actividad.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id'])
            actividad.observaciones = request.POST['obs']
            actividad.save()
            return JsonResponse({'ok': True})
        elif action == 'change_nombre_actividad':
            try:
                actividad = Actividad.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id'])
                actividad.nombre = request.POST['nombre']
                actividad.save()
                return JsonResponse({'ok': True, 'nombre': actividad.nombre})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_checkbox':
            try:
                actividad = Actividad.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id'])
                attr = request.POST['attr']
                valor = not getattr(actividad, attr)
                logger.info(u'%s, change_%s %s' % (g_e, attr, actividad.id))
                setattr(actividad, attr, valor)
                actividad.save()
                return JsonResponse({'ok': True, 'estado': valor})
            except:
                return JsonResponse({'ok': False})

    return render(request, "actividades_horarios.html", {'actividades': actividades})


@permiso_required('acceso_define_horarios')
def define_horario(request):
    g_e = request.session['gauser_extra']
    horarios = Horario.objects.filter(entidad=g_e.ronda.entidad, ronda=g_e.ronda.entidad.ronda)
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'add_horario':
            horario = Horario.objects.create(entidad=g_e.ronda.entidad, ronda=g_e.ronda, descripcion='Horario nuevo')
            inicio = time(9, 0)
            fin = time(10, 0)
            Tramo_horario.objects.create(horario=horario, nombre='Nuevo tramo', inicio=inicio, fin=fin)
            accordion = render_to_string('formulario_horario.html', {'horario': horario, })
            return HttpResponse(accordion)
        elif action == 'delete_horario':
            horario = Horario.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            predeterminado = Horario.objects.get(predeterminado=True, entidad=g_e.ronda.entidad)
            if horario.id == predeterminado.id:
                horario.delete()
                try:
                    predeterminado = Horario.objects.filter(entidad=g_e.ronda.entidad)[0]
                    predeterminado.predeterminado = True
                    predeterminado.save()
                    return HttpResponse(predeterminado.id)
                except:
                    return HttpResponse(0)
            else:
                horario.delete()
                return HttpResponse(predeterminado.id)
        elif action == 'delete_horario':
            horario = Horario.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            horario.delete()
            return HttpResponse(True)
        elif action == 'descripcion':
            horario = Horario.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            horario.descripcion = request.POST['descripcion']
            horario.save()
            return HttpResponse(horario.descripcion[:90])
        elif action == 'predeterminado':
            horario = Horario.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            horarios = Horario.objects.filter(entidad=g_e.ronda.entidad)
            for h in horarios:
                h.predeterminado = False
                h.save()
            horario.predeterminado = True
            horario.save()
            return HttpResponse(horario.id)
        elif action == 'dia':
            horario = Horario.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            check = True if request.POST['check'] == 'true' else False
            setattr(horario, request.POST['dia'], check)
            horario.save()
            return HttpResponse(check)
        elif action == 'add_tramo':
            horario = Horario.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            try:
                last_tramo = Tramo_horario.objects.filter(horario=horario).reverse()[0]
                inicio = time(last_tramo.fin.hour, last_tramo.fin.minute)
                fin = time(inicio.hour + 1, inicio.minute)
            except:
                inicio = time(9, 0)
                fin = time(10, 0)
            tramo = Tramo_horario.objects.create(horario=horario, nombre='Nuevo tramo', inicio=inicio, fin=fin)
            accordion = render_to_string('formulario_tramo.html', {'t': tramo})
            return HttpResponse(accordion)
        elif action == 'nombre_tramo':
            horario = Horario.objects.get(id=request.POST['horario'], entidad=g_e.ronda.entidad)
            tramo = Tramo_horario.objects.get(id=request.POST['tramo'], horario=horario)
            tramo.nombre = request.POST['nombre']
            tramo.save()
            return HttpResponse(tramo)
        elif action == 'inicio':
            horario = Horario.objects.get(id=request.POST['horario'], entidad=g_e.ronda.entidad)
            tramo = Tramo_horario.objects.get(id=request.POST['tramo'], horario=horario)
            tramo.inicio = request.POST['valor']
            tramo.save()
            return HttpResponse(tramo)
        elif action == 'fin':
            horario = Horario.objects.get(id=request.POST['horario'], entidad=g_e.ronda.entidad)
            tramo = Tramo_horario.objects.get(id=request.POST['tramo'], horario=horario)
            tramo.fin = request.POST['valor']
            tramo.save()
            return HttpResponse(tramo)
        elif action == 'delete_tramo':
            horario = Horario.objects.get(id=request.POST['horario'], entidad=g_e.ronda.entidad)
            tramo = Tramo_horario.objects.get(id=request.POST['tramo'], horario=horario)
            tramo.delete()
            return HttpResponse(True)
    return render(request, "define_horario.html", {
        'horarios': horarios.order_by('-id'),
        'formname': 'define_horario',
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    })


pixels_hora = 120
height_min = pixels_hora * 1
offset = 50


# @permiso_required('acceso_horarios_subentidades')
@login_required()
def horario_aulas(request):
    g_e = request.session["gauser_extra"]
    horarios = Horario.objects.filter(entidad=g_e.ronda.entidad, ronda=g_e.ronda)
    if horarios.count() == 0:
        crear_aviso(request, False, 'Para ver un horario, antes debes crearlo.')
        return redirect('/define_horario/')
    try:
        horario = Horario.objects.get(entidad=g_e.ronda.entidad, id=request.GET['h'], ronda=g_e.ronda)
    except:
        horario = Horario.objects.get(entidad=g_e.ronda.entidad, predeterminado=True, ronda=g_e.ronda)
    aulas = Dependencia.objects.filter(entidad=g_e.ronda.entidad, es_aula=True)
    try:
        aula = aulas.get(id=request.GET['a'])
    except:
        try:
            aula = aulas[0]
        except:
            return redirect('/define_horario/')
    try:
        sesiones = horario.sesion_set.filter(dependencia=aula).order_by('dia')
        sesiones_aula = []
        for s in sesiones:
            coincidencias = sesiones.filter(dia=s.dia, inicio=s.inicio)
            sesiones_aula.append(coincidencias)
    except:
        return redirect('/define_horario/')

    sesiones_aula = horario.sesion_set.filter(dependencia=aula)
    dias = sesiones_aula.values_list('dia', flat=True).order_by('dia').distinct()
    nombre_dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado',
                   7: 'Domingo'}
    horas_aula = horario.horas_aula(aula)
    sesiones = []
    for d in dias:
        sesiones_dia = sesiones_aula.filter(dia=d).order_by('inicio')
        info_dia = {'dia_num': d, 'dia_nombre': nombre_dias[d], 'sesiones_dia': []}
        for hora in horas_aula:
            sesiones_hora = sesiones_dia.filter(inicio=hora['inicio'])
            if sesiones_hora.count() > 0:
                info_dia['sesiones_dia'].append(sesiones_hora)
        sesiones.append(info_dia)

    respuesta = {
        'formname': 'horario_subentidad',
        'horario': horario,
        'sesiones': sesiones,
        'horas_aula': horas_aula,
        'aulas': aulas,
        'aula': aula,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "horario_aulas.html", respuesta)


# @permiso_required('acceso_horario_usuarios')
@login_required()
def horario_subentidad(request):
    # Las siguientes líneas indican si el usuario podrá hacer modificaciones en el horario:
    g_e = request.session["gauser_extra"]
    horarios = Horario.objects.filter(entidad=g_e.ronda.entidad, ronda=g_e.ronda)
    if horarios.count() == 0:
        logger.info(u'No existen horarios. Redireccionado para crear un horario.')
        crear_aviso(request, False, 'Para ver un horario, antes debes crearlo.')
        return redirect('/define_horario/')
    try:
        horario = horarios.get(id=request.GET['h'])
        logger.info(u'Ha solicitado el horario "%s"' % horario.descripcion[:90])
    except:
        try:
            horario = horarios.get(predeterminado=True)
            logger.info(u'Se autoselecciona el horario predeterminado')
        except ObjectDoesNotExist:
            horario = horarios[0]
            horario.predeterminado = True
            horario.save()
            logger.info(u'No existe horario predeterminado. Se crea uno.')
        except MultipleObjectsReturned:
            horarios.update(predeterminado=False)
            horario = horarios[0]
            horario.predeterminado = True
            horario.save()
            logger.info(u'Existen varios horarios predeterminados. Se reconvierten para dejar uno solo.')
    grupos = Grupo.objects.filter(ronda=g_e.ronda)
    grupos_id = horario.sesion_set.all().values_list('grupo__id', flat=True).distinct()
    grupos_horario = grupos.filter(id__in=grupos_id)
    try:
        grupo = grupos[0]
        try:
            grupos_horario[0]
        except:
            crear_aviso(request, False, 'No existen sesiones que incluyan grupos. Debes crear sesiones.')
            return redirect('/horario_ge/')
    except:
        crear_aviso(request, False, 'No existen grupos. Debes crearlos antes.')
        return redirect('/configura_grupos/')

    sesiones_grupo = horario.sesion_set.filter(grupo=grupo)
    dias = sesiones_grupo.values_list('dia', flat=True).order_by('dia').distinct()
    nombre_dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 7: 'Domingo'}
    horas_grupo = horario.horas_grupo(grupo)
    sesiones = []
    for d in dias:
        sesiones_dia = sesiones_grupo.filter(dia=d).order_by('inicio')
        info_dia = {'dia_num': d, 'dia_nombre': nombre_dias[d], 'sesiones_dia': []}
        for hora in horas_grupo:
            sesiones_hora = sesiones_dia.filter(inicio=hora['inicio'])
            if sesiones_hora.count() > 0:
                info_dia['sesiones_dia'].append(sesiones_hora)
        sesiones.append(info_dia)

    respuesta = {
        'formname': 'horario_grupos',
        'horario': horario,
        'grupos': grupos,
        'grupo': grupo,
        'sesiones': sesiones,
        'horas_grupo': horas_grupo,
        'horario_selected': horario,
        'horarios': horarios,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "horario_grupos.html", respuesta)


# @permiso_required('acceso_horario_usuarios')
@login_required()
def horario_ge(request):
    # Las siguientes líneas indican si el usuario podrá hacer modificaciones en el horario:
    g_e = request.session["gauser_extra"]
    horarios = Horario.objects.filter(ronda=g_e.ronda)
    if horarios.count() == 0:
        logger.info(u'No existen horarios. Redireccionado para crear un horario.')
        crear_aviso(request, False, 'Para ver un horario, antes debes crearlo.')
        return redirect('/define_horario/')
    try:
        horario = horarios.get(id=request.GET['h'])
        logger.info(u'Ha solicitado el horario "%s"' % horario.descripcion[:90])
    except:
        try:
            horario = horarios.get(predeterminado=True)
            logger.info(u'Se autoselecciona el horario predeterminado')
        except ObjectDoesNotExist:
            horario = horarios[0]
            horario.predeterminado = True
            horario.save()
            logger.info(u'No existe horario predeterminado. Se crea uno.')
        except MultipleObjectsReturned:
            horarios.update(predeterminado=False)
            horario = horarios[0]
            horario.predeterminado = True
            horario.save()
            logger.info(u'Existen varios horarios predeterminados. Se reconvierten para dejar uno solo.')
    g_es_id = horario.sesion_set.all().values_list('g_e__id', flat=True).distinct()
    g_es = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, id__in=g_es_id)
    try:
        ge = g_es.get(id=request.GET['u'])
    except:
        try:
            ge = g_es.get(id=g_e.id)
        except:
            ge = None if g_es.count() == 0 else g_es[0]

    sesiones_ge = horario.sesion_set.filter(g_e=ge)
    dias = sesiones_ge.values_list('dia', flat=True).order_by('dia').distinct()
    nombre_dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 7: 'Domingo'}
    horas_ge = horario.horas_ge(ge)
    sesiones = []
    for d in dias:
        sesiones_dia = sesiones_ge.filter(dia=d).order_by('inicio')
        info_dia = {'dia_num': d, 'dia_nombre': nombre_dias[d], 'sesiones_dia': []}
        for hora in horas_ge:
            sesiones_hora = sesiones_dia.filter(inicio=hora['inicio'])
            if sesiones_hora.count() > 0:
                info_dia['sesiones_dia'].append(sesiones_hora)
        sesiones.append(info_dia)

    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'user-plus', 'texto': 'Nuevo horario',
              'permiso': 'crea_horarios_usuarios', 'title': 'Crear horario para otro usuario'},
             {'tipo': 'button', 'nombre': 'calendar-plus-o', 'texto': 'Nueva sesión',
              'permiso': 'crea_sesiones_horario', 'title': 'Crear una nueva sesión en el calendario del usuario'},
             {'tipo': 'button', 'nombre': 'copy', 'texto': 'Copiar horario',
              'permiso': 'crea_horarios_usuarios', 'title': 'Copiar este calendario y asignarlo a otro usuario'},
             ),
        'formname': 'horario_ge',
        'horario': horario,
        'g_es': g_es,
        'gauser_extra': ge,
        'sesiones': sesiones,
        'horas_ge': horas_ge,
        'grupos': Grupo.objects.filter(ronda=g_e.ronda),
        'dependencias': Dependencia.objects.filter(entidad=g_e.ronda.entidad),
        # 'materias': Materia.objects.filter(curso__entidad=g_e.ronda.entidad),
        'actividades': Actividad.objects.filter(entidad=g_e.ronda.entidad),
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "horario_ge.html", respuesta)


@login_required()
def horarios_ajax(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        action = request.POST['action']

        if action == 'add_sesion':
            tramo = Tramo_horario.objects.get(id=request.POST['tramo'])
            dia = request.POST['dia']
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            sesion = Sesion.objects.create(tramo_horario=tramo, dia=dia, g_e=ge)
            return JsonResponse({'id': sesion.id})
        elif action == 'cancel_sesion':
            sesion = Sesion.objects.get(id=request.POST['id'])
            if not sesion.dependencia and not sesion.materia and not sesion.subentidad and not sesion.actividad:
                sesion.delete()
                return JsonResponse({'id': False})
            try:
                d_nombre = sesion.dependencia.nombre
            except:
                d_nombre = ''
            try:
                s_nombre = sesion.subentidad.nombre
            except:
                s_nombre = ''
            try:
                m_nombre = sesion.materia.nombre
            except:
                m_nombre = ''
            try:
                a_nombre = sesion.actividad.nombre
            except:
                a_nombre = ''
            return JsonResponse({'dependencia': d_nombre, 'subentidad': s_nombre, 'materia': m_nombre, 'id': sesion.id,
                                 'actividad': a_nombre})
        elif action == 'ok_sesion':
            horario = Horario.objects.get(id=request.POST['horario'], entidad=g_e.ronda.entidad)
            ge = Gauser_extra.objects.get(id=request.POST['g_e'], entidad=g_e.ronda.entidad)
            try:
                h_inicio = request.POST['inicio'].split(':')
                inicio = time(int(h_inicio[0]), int(h_inicio[1]))
            except:
                inicio = time(10, 0)
            try:
                h_fin = request.POST['fin'].split(':')
                fin = time(int(h_fin[0]), int(h_fin[1]))
            except:
                fin = time(10, 0)
            try:
                dependencia = Dependencia.objects.get(id=request.POST['dependencia'], entidad=g_e.ronda.entidad)
            except:
                dependencia = None
            try:
                grupo = Grupo.objects.get(id=request.POST['grupo'], ronda=g_e.ronda)
            except:
                grupo = None
            try:
                materia = Materia.objects.get(id=request.POST['materia'], curso__ronda=g_e.ronda)
            except:
                materia = None
            try:
                actividad = Actividad.objects.get(id=request.POST['actividad'], entidad=g_e.ronda.entidad)
            except:
                actividad = None
            if request.POST['sesion'] == 'nueva':
                sesion = Sesion.objects.create(dependencia=dependencia, grupo=grupo, materia=materia,
                                               actividad=actividad, inicio=inicio, g_e=ge,
                                               fin=fin, dia=int(request.POST['dia']), horario=horario)
            else:
                sesion = Sesion.objects.get(id=request.POST['sesion'])
                sesion.inicio = inicio
                sesion.fin = fin
                sesion.dia = request.POST['dia']
                sesion.dependencia = dependencia
                sesion.grupo = grupo
                sesion.materia = materia
                sesion.actividad = actividad
                sesion.save()
            if not sesion.dependencia and not sesion.materia and not sesion.grupo and not sesion.actividad:
                sesion.delete()
                return JsonResponse({'ok': False})
            sesiones_ge = horario.sesion_set.filter(g_e=ge)
            dias = sesiones_ge.values_list('dia', flat=True).order_by('dia').distinct()
            nombre_dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado',
                           7: 'Domingo'}
            horas_ge = horario.horas_ge(ge)
            sesiones = []
            for d in dias:
                sesiones_dia = sesiones_ge.filter(dia=d).order_by('inicio')
                info_dia = {'dia_num': d, 'dia_nombre': nombre_dias[d], 'sesiones_dia': []}
                for hora in horas_ge:
                    sesiones_hora = sesiones_dia.filter(inicio=hora['inicio'])
                    if sesiones_hora.count() > 0:
                        info_dia['sesiones_dia'].append(sesiones_hora)
                sesiones.append(info_dia)
            html = render_to_string('horario_ge_content.html',
                                    {'horas_ge': horas_ge, 'sesiones': sesiones, 'gauser_extra': ge,
                                     'request': request})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'borrar_sesion' and g_e.has_permiso('borra_sesiones_horario'):
            Sesion.objects.get(id=request.POST['sesion'], horario__entidad=g_e.ronda.entidad).delete()
            return JsonResponse({'ok': True})
        elif action == 'editar_sesion':
            sesion = Sesion.objects.get(id=request.POST['sesion'])
            try:
                d = sesion.dependencia.id
            except:
                d = ''
            try:
                g = sesion.grupo.id
            except:
                g = ''
            try:
                m = sesion.materia.id
                m_text = sesion.materia.nombre
            except:
                m = ''
                m_text = ''
            try:
                a = sesion.actividad.id
            except:
                a = ''
            return JsonResponse({'dependencia': d, 'grupo': g, 'materia': m, 'id': sesion.id, 'actividad': a,
                                 'dia': sesion.dia, 'inicio': sesion.inicio.strftime('%H:%M'),
                                 'fin': sesion.fin.strftime('%H:%M'), 'materia_texto': m_text})
        elif action == 'mod_sesion':
            dependencia = Dependencia.objects.get(id=request.POST['dependencia'])
            subentidad = Subentidad.objects.get(id=request.POST['subentidad'])
            materia = Materia.objects.get(id=request.POST['materia'])
            sesion = Sesion.objects.get(id=request.POST['id'])
            sesion.dependencia = dependencia
            sesion.subentidad = subentidad
            sesion.materia = materia
            sesion.save()
            return JsonResponse({'dependencia': sesion.dependencia.nombre, 'subentidad': sesion.subentidad.nombre,
                                 'materia': sesion.materia.nombre, 'id': sesion.id,
                                 'actividad': sesion.actividad.nombre})
        elif action == 'copia_horario':
            destinatario = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['destinatario'])
            origen = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['origen'])
            horario = Horario.objects.get(entidad=g_e.ronda.entidad, id=request.POST['horario'])
            destinatario.sesion_set.filter(horario=horario).delete()
            sesiones = origen.sesion_set.filter(horario=horario)
            for s in sesiones:
                s.pk = None
                s.g_e = destinatario
                s.save()
            return JsonResponse({'ok': True})
        elif action == 'nuevo_horario_usuario':
            nuevo_ge = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['nuevo_ge'])
            horario = Horario.objects.get(entidad=g_e.ronda.entidad, id=request.POST['horario'])
            sesiones = nuevo_ge.sesion_set.filter(horario=horario)
            if sesiones.count() == 0:
                actividad, c = Actividad.objects.get_or_create(entidad=g_e.ronda.entidad, nombre='Actividad horario')
                hora = horario.horas.first()
                for d in horario.dias_con_sesion:
                    Sesion.objects.create(actividad=actividad, inicio=hora[0], g_e=nuevo_ge,
                                          fin=hora[1], dia=d, horario=horario)
            return JsonResponse({'ok': True})
        elif action == 'del_horario_usuario':
            horario = Horario.objects.get(entidad=g_e.ronda.entidad, id=request.POST['horario'])
            usuario = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['ge'])
            usuario.sesion_set.filter(horario=horario).delete()
            return JsonResponse({'ok': True})
        elif action == 'asistencia_sesion':
            dia = {'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3, 'viernes': 4, 'sabado': 5, 'domingo': 6}
            today = date.today()
            sesion = Sesion.objects.get(id=request.POST['id'])
            delta = timedelta(days=(dia[sesion.dia] - today.weekday()))
            fecha_falta = today + delta
            subentidad = sesion.subentidad
            ges = Gauser_extra.objects.filter(subentidades__in=[subentidad])
            weekday_fdatepicker = (fecha_falta.weekday() + 1) if (today.weekday() + 1) != 7 else 0
            disabled = range(weekday_fdatepicker) + range(weekday_fdatepicker + 1, 7)
            ge_faltas = Falta_asistencia.objects.filter(sesion=sesion, fecha_falta=fecha_falta).values_list('g_e__id',
                                                                                                            flat=True)
            texto = render_to_string('lista_ges.html', {'ges': ges, 'fecha_falta': fecha_falta, 'disabled': disabled,
                                                        'sesion': sesion, 'ge_faltas': ge_faltas})
            return HttpResponse(texto)
        elif action == 'change_fecha_alta':
            sesion = Sesion.objects.get(id=int(request.POST['sesion']), tramo_horario__horario__entidad=g_e.ronda.entidad)
            fecha_falta = datetime.strptime(request.POST['fecha_falta'], '%d/%m/%Y')
            ge_faltas = list(
                Falta_asistencia.objects.filter(sesion=sesion, fecha_falta=fecha_falta).values_list('g_e__id',
                                                                                                    flat=True))
            return JsonResponse(ge_faltas, safe=False)
        elif action == 'add_falta':
            fecha_falta = datetime.strptime(request.POST['fecha_falta'], '%d/%m/%Y')
            sesion = Sesion.objects.get(id=int(request.POST['sesion']), tramo_horario__horario__entidad=g_e.ronda.entidad)
            ge = Gauser_extra.objects.get(id=int(request.POST['ge']), entidad=g_e.ronda.entidad)
            Falta_asistencia.objects.get_or_create(fecha_falta=fecha_falta, sesion=sesion, g_e=ge)
            return HttpResponse(True)
        elif action == 'del_falta':
            fecha_falta = datetime.strptime(request.POST['fecha_falta'], '%d/%m/%Y')
            sesion = Sesion.objects.get(id=int(request.POST['sesion']), tramo_horario__horario__entidad=g_e.ronda.entidad)
            ge = Gauser_extra.objects.get(id=int(request.POST['ge']), entidad=g_e.ronda.entidad)
            Falta_asistencia.objects.get(fecha_falta=fecha_falta, sesion=sesion, g_e=ge).delete()
            return HttpResponse(True)
        elif action == 'alumnos_sesion':
            sesion = Sesion.objects.get(id=request.POST['id'])
            subentidad = sesion.subentidad
            ges = Gauser_extra.objects.filter(subentidades__in=[subentidad])
            texto = render_to_string('lista_asistentes.html', {'ges': ges, 'sesion': sesion})
            return HttpResponse(texto)
        elif action == 'add_asistente':
            sesion = Sesion.objects.get(id=int(request.POST['sesion']), tramo_horario__horario__entidad=g_e.ronda.entidad)
            ge = Gauser_extra.objects.get(id=int(request.POST['ge']), entidad=g_e.ronda.entidad)
            sesion.asistentes.add(ge)
            return HttpResponse(True)
        elif action == 'del_asistente':
            sesion = Sesion.objects.get(id=int(request.POST['sesion']), tramo_horario__horario__entidad=g_e.ronda.entidad)
            ge = Gauser_extra.objects.get(id=int(request.POST['ge']), entidad=g_e.ronda.entidad)
            sesion.asistentes.remove(ge)
            return HttpResponse(True)
        elif action == 'buscar_usuarios':
            texto = request.POST['q']
            unaccent_texto = texto.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú',
                                                                                                                   'u')
            q1 = Q(gauser__first_name__icontains=texto)
            q2 = Q(gauser__last_name__icontains=texto)
            q3 = Q(gauser__first_name__icontains=unaccent_texto)
            q4 = Q(gauser__last_name__icontains=unaccent_texto)
            qaf = Q(gauser__first_name__icontains=texto.replace('a', 'á', 1))
            qef = Q(gauser__first_name__icontains=texto.replace('e', 'é', 1))
            qif = Q(gauser__first_name__icontains=texto.replace('i', 'í', 1))
            qof = Q(gauser__first_name__icontains=texto.replace('o', 'ó', 1))
            quf = Q(gauser__first_name__icontains=texto.replace('u', 'ú', 1))
            qa = Q(gauser__last_name__icontains=texto.replace('a', 'á', 1))
            qe = Q(gauser__last_name__icontains=texto.replace('e', 'é', 1))
            qi = Q(gauser__last_name__icontains=texto.replace('i', 'í', 1))
            qo = Q(gauser__last_name__icontains=texto.replace('o', 'ó', 1))
            qu = Q(gauser__last_name__icontains=texto.replace('u', 'ú', 1))
            if g_e.has_permiso('crea_horarios_usuarios'):
                usuarios = usuarios_de_gauss(g_e.ronda.entidad)
            else:
                horario = Horario.objects.get(id=request.POST['horario'], entidad=g_e.ronda.entidad)
                sesiones = Sesion.objects.filter(tramo_horario__horario=horario)
                g_es_id = sesiones.values_list('g_e__id', flat=True)
                usuarios = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, id__in=g_es_id)

            q = q1 | q2 | q3 | q4 | qa | qe | qi | qo | qu | qaf | qef | qif | qof | quf
            usuarios_contain_texto = usuarios.filter(q).distinct().values_list('id',
                                                                               'gauser__last_name',
                                                                               'gauser__first_name',
                                                                               'cargos__cargo')
            keys = ('id', 'text')
            return HttpResponse(json.dumps(
                [dict(zip(keys, (row[0], '%s, %s (%s)' % (row[1], row[2], row[3])))) for row in
                 usuarios_contain_texto]))
        elif action == 'buscar_materias':
            texto = request.POST['q']
            unaccent_texto = texto.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú',
                                                                                                                   'u')
            grupo = Grupo.objects.get(ronda=g_e.ronda, id=request.POST['grupo'])
            materias = Materia.objects.filter(curso__in=grupo.cursos.all())
            q1 = Q(nombre__icontains=texto)
            q2 = Q(nombre__icontains=unaccent_texto)
            qa = Q(nombre__icontains=texto.replace('a', 'á', 1))
            qe = Q(nombre__icontains=texto.replace('e', 'é', 1))
            qi = Q(nombre__icontains=texto.replace('i', 'í', 1))
            qo = Q(nombre__icontains=texto.replace('o', 'ó', 1))
            qu = Q(nombre__icontains=texto.replace('u', 'ú', 1))
            q = q1 | q2 | qa | qe | qi | qo | qu
            materias_contain_texto = materias.filter(q).distinct().values_list('id',
                                                                               'nombre',
                                                                               'curso__nombre')
            keys = ('id', 'text')
            return HttpResponse(json.dumps(
                [dict(zip(keys, (row[0], '%s (%s)' % (row[1], row[2])))) for row in
                 materias_contain_texto]))

        elif action == 'carga_horario_usuario':
            ge = Gauser_extra.objects.get(id=request.POST['ge'], ronda=g_e.ronda)
            horario = Horario.objects.get(id=request.POST['horario'], ronda=g_e.ronda)
            sesiones_ge = horario.sesion_set.filter(g_e=ge)
            dias = sesiones_ge.values_list('dia', flat=True).order_by('dia').distinct()
            nombre_dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado',
                           7: 'Domingo'}
            horas_ge = horario.horas_ge(ge)
            sesiones = []
            for d in dias:
                sesiones_dia = sesiones_ge.filter(dia=d).order_by('inicio')
                info_dia = {'dia_num': d, 'dia_nombre': nombre_dias[d], 'sesiones_dia': []}
                for hora in horas_ge:
                    sesiones_hora = sesiones_dia.filter(inicio=hora['inicio'])
                    if sesiones_hora.count() > 0:
                        info_dia['sesiones_dia'].append(sesiones_hora)
                sesiones.append(info_dia)
            html = render_to_string('horario_ge_content.html',
                                    {'horas_ge': horas_ge, 'sesiones': sesiones, 'gauser_extra': ge,
                                     'request': request})
            return JsonResponse({'ok': True, 'html': html})

        elif action == 'carga_horario_aula':
            aula = Dependencia.objects.get(id=request.POST['aula'], entidad=g_e.ronda.entidad)
            horario = Horario.objects.get(id=request.POST['horario'], ronda=g_e.ronda)
            sesiones_aula = horario.sesion_set.filter(dependencia=aula)
            dias = sesiones_aula.values_list('dia', flat=True).order_by('dia').distinct()
            nombre_dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado',
                           7: 'Domingo'}
            horas_aula = horario.horas_aula(aula)
            sesiones = []
            for d in dias:
                sesiones_dia = sesiones_aula.filter(dia=d).order_by('inicio')
                info_dia = {'dia_num': d, 'dia_nombre': nombre_dias[d], 'sesiones_dia': []}
                for hora in horas_aula:
                    sesiones_hora = sesiones_dia.filter(inicio=hora['inicio'])
                    if sesiones_hora.count() > 0:
                        info_dia['sesiones_dia'].append(sesiones_hora)
                sesiones.append(info_dia)
            html = render_to_string('horario_aulas_content.html', {'horas_aula': horas_aula, 'sesiones': sesiones})
            return JsonResponse({'ok': True, 'html': html})

        elif action == 'carga_horario_grupo':
            grupo = Grupo.objects.get(id=request.POST['grupo'], ronda=g_e.ronda)
            horario = Horario.objects.get(id=request.POST['horario'], ronda=g_e.ronda)
            sesiones_grupo = horario.sesion_set.filter(grupo=grupo)
            dias = sesiones_grupo.values_list('dia', flat=True).order_by('dia').distinct()
            nombre_dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado',
                           7: 'Domingo'}
            horas_grupo = horario.horas_grupo(grupo)
            sesiones = []
            for d in dias:
                sesiones_dia = sesiones_grupo.filter(dia=d).order_by('inicio')
                info_dia = {'dia_num': d, 'dia_nombre': nombre_dias[d], 'sesiones_dia': []}
                for hora in horas_grupo:
                    sesiones_hora = sesiones_dia.filter(inicio=hora['inicio'])
                    if sesiones_hora.count() > 0:
                        info_dia['sesiones_dia'].append(sesiones_hora)
                sesiones.append(info_dia)
            html = render_to_string('horario_grupos_content.html', {'horas_grupo': horas_grupo, 'sesiones': sesiones})
            return JsonResponse({'ok': True, 'html': html})

        elif action == 'buscar_aulas_libres':
            horario = Horario.objects.get(id=request.POST['horario'], entidad=g_e.ronda.entidad)
            try:
                h_inicio = request.POST['inicio'].split(':')
                inicio = time(int(h_inicio[0]), int(h_inicio[1]))
            except:
                inicio = time(0, 0)
            try:
                h_fin = request.POST['fin'].split(':')
                fin = time(int(h_fin[0]), int(h_fin[1]))
            except:
                fin = time(23, 59)
            aulas = Dependencia.objects.filter(entidad=g_e.ronda.entidad, es_aula=True)
            id_aulas = aulas.values_list('id', flat=True)
            aulas_ocupadas = Sesion.objects.filter(horario=horario, inicio__lt=fin, fin__gt=inicio,
                                                   dia=request.POST['dia']).values_list('dependencia__id',
                                                                                        flat=True).distinct()
            libres = [a for a in id_aulas if a not in aulas_ocupadas]
            aulas_libres = aulas.filter(id__in=libres)
            html = render_to_string('listado_aulas_libres.html', {'aulas_libres': aulas_libres})
            return JsonResponse({'ok': True, 'html': html, 'inicio': inicio, 'fin': fin, 'nao': aulas_ocupadas.count(),
                                 'na': aulas.count(), 'libres': len(libres)})


# @permiso_required('acceso_carga_masiva_horarios')
def carga_masiva_horarios(request):
    g_e = request.session["gauser_extra"]
    incidencias = {}
    if request.method == 'POST':
        ronda = request.session['gauser_extra'].ronda
        action = request.POST['action']
        if action == 'carga_masiva_racima_xml':
            logger.info(u'Carga de archivo de tipo: ' + request.FILES['file_masivo'].content_type)
            if 'xml' in request.FILES['file_masivo'].content_type:
                xml_file = ElementTree.XML(request.FILES['file_masivo'].read())  # ,parser)
                if xml_file.tag == 'SERVICIO':  # Si ocurre esto es el archivo de exportación de RACIMA
                    incidencias = xml_racima(xml_file, request)
                    if incidencias['especialidades']:
                        geps = Gauser_extra_programaciones.objects.filter(ge__ronda=g_e.ronda)
                        especialidades = Especialidad_entidad.objects.filter(ronda=g_e.ronda)
                        departamentos = Departamento.objects.filter(ronda=g_e.ronda)
                        incidencias['especialidades'] = render_to_string('incidencias_especialidades.html',
                                                                         {'geps': geps,
                                                                          'especialidades': especialidades,
                                                                          'departamentos': departamentos})
                elif xml_file.tag == 'HORARIO':  # Si ocurre esto es el archivo de exportación de PEÑALARA
                    xml_penalara(xml_file, request)
            else:
                crear_aviso(request, False, u'El archivo cargado no tiene el formato adecuado.')
        elif action == 'update_especialidad' and request.is_ajax():
            try:
                gep = Gauser_extra_programaciones.objects.get(ge__ronda=g_e.ronda, id=request.POST['gep'])
                especialidad = Especialidad_entidad.objects.get(ronda=g_e.ronda, id=request.POST['especialidad'])
                gep.especialidad = especialidad
                gep.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_departamento' and request.is_ajax():
            try:
                gep = Gauser_extra_programaciones.objects.get(ge__ronda=g_e.ronda, id=request.POST['gep'])
                departamento = Departamento.objects.get(ronda=g_e.ronda, id=request.POST['departamento'])
                gep.departamento = departamento
                gep.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})


    return render(request, "carga_masiva_horarios.html",
                  {
                      'iconos': ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                                  'title': 'Subir el archivo a GAUSS',
                                  'permiso': 'acceso_carga_masiva_horarios'}, {}),
                      'formname': 'carga_masiva',
                      'incidencias': incidencias,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


def get_coincidente(texto, lista_ids_textos):  # Devuelve el id del gauser_extra coincidente
    lista_textos = [n[1] for n in lista_ids_textos]
    try:
        m = get_close_matches(texto, lista_textos, 1)[0]
        for n in lista_ids_textos:
            if n[1] == m:
                return n[0]
        return None
    except:
        return None


def get_coincidentes(texto, lista_ids_textos):  # Devuelve el id del gauser_extra coincidente
    coincidencias = []
    lista_textos = [n[1] for n in lista_ids_textos]
    try:
        ms = get_close_matches(texto, lista_textos)
        for n in lista_ids_textos:
            for m in ms:
                if n[1] == m:
                    coincidencias.append(n[0])
        return coincidencias
    except:
        return None


def xml_racima(xml_file, request):
    incidencias = {'especialidades': False}
    g_e = request.session['gauser_extra']
    horario = Horario.objects.create(entidad=g_e.ronda.entidad, ronda=g_e.ronda,
                                     descripcion=u'Creado a través del xml obtenido de racima %s' % datetime.now())
    horarios = Horario.objects.filter(entidad=g_e.ronda.entidad)
    for h in horarios:
        h.predeterminado = False
        h.save()
    horario.predeterminado = True
    horario.save()
    # for elemento in racima.xpath(".//grupo_datos[@seq='CURSOS_DEL_CENTRO']/grupo_datos"):
    for elemento in xml_file.findall(".//grupo_datos[@seq='CURSOS_DEL_CENTRO']/grupo_datos"):
        nombre = elemento.find('dato[@nombre_dato="D_OFERTAMATRIG"]').text
        curso_codigo = elemento.find('dato[@nombre_dato="X_OFERTAMATRIG"]').text
        try:
            curso = Curso.objects.get(clave_ex=curso_codigo, ronda=g_e.ronda)
            curso.nombre = nombre
            curso.observaciones += u'<br>Actualizado el %s' % datetime.now()
            curso.save()
            logger.info(u'Se actualiza el curso: %s' % curso)
        except:
            observaciones = u'Creado el %s' % datetime.now()
            Curso.objects.create(nombre=nombre, clave_ex=curso_codigo, observaciones=observaciones, ronda=g_e.ronda)
            logger.info(u'Se ha creado el curso %s, con código %s' % (nombre, curso_codigo))
    # for elemento in xml_file.xpath(".//grupo_datos[@seq='MATERIAS']/grupo_datos"):
    for elemento in xml_file.findall(".//grupo_datos[@seq='MATERIAS']/grupo_datos"):
        nombre = elemento.find('dato[@nombre_dato="D_MATERIAC"]').text
        materia_codigo = elemento.find('dato[@nombre_dato="X_MATERIAOMG"]').text
        curso_codigo = elemento.find('dato[@nombre_dato="X_OFERTAMATRIG"]').text
        try:
            curso = Curso.objects.get(clave_ex=curso_codigo, ronda=g_e.ronda)
        except:
            observaciones = u'Creado el %s. Por no existir y tener asociada la materia %s' % (
                datetime.now(), materia_codigo)
            curso = Curso.objects.create(clave_ex=curso_codigo, ronda=g_e.ronda, observaciones=observaciones,
                                         nombre='Curso inventado')
        try:
            horas = int(elemento.find('dato[@nombre_dato="N_HORASMIN"]').text) / 60
        except:
            horas = 0
        try:
            duracion = int(elemento.find('dato[@nombre_dato="N_HORAS"]').text)
        except:
            duracion = 0

        materias = Materia.objects.filter(curso__clave_ex=curso_codigo, clave_ex=materia_codigo,
                                          curso__ronda=g_e.ronda)
        if materias.count() == 0:
            try:
                observaciones = u'Creada el %s' % datetime.now()
                Materia.objects.create(curso=curso, nombre=nombre, clave_ex=materia_codigo, observaciones=observaciones,
                                       horas=horas, duracion=duracion)
                logger.info(u'Se ha creado la materia %s, con código %s' % (nombre, materia_codigo))
            except:
                logger.warning(u'No se ha creado la materia %s. No existe curso %s' % (nombre, materia_codigo))
                crear_aviso(request, False,
                            u'La materia %s, asignada al curso %s no ha podido ser creada ya que dicho curso no existe.' % (
                                nombre, curso_codigo))
        elif materias.count() > 1:
            materia = materias[0]
            materias.exclude(pk__in=[materia.pk]).delete()
            materia.curso = curso
            materia.nombre = nombre
            materia.horas = horas
            materia.duracion = duracion
            materia.observaciones += u'<br>Actualizada el %s' % datetime.now()
            materia.save()
            logger.info(u'Se actualiza la materia: %s' % nombre)
        else:
            materia = materias[0]
            materia.curso = curso
            materia.nombre = nombre
            materia.horas = horas
            materia.duracion = duracion
            materia.observaciones += u'<br>Actualizada el %s' % datetime.now()
            materia.save()
            logger.info(u'Se actualiza la materia: %s' % nombre)

        # try:
        #     materia = Materia.objects.get(curso__clave_ex=curso_codigo, clave_ex=materia_codigo,
        #                                   curso__ronda=g_e.ronda)
        #     materia.curso = curso
        #     materia.nombre = nombre
        #     materia.horas = horas
        #     materia.duracion = duracion
        #     materia.observaciones += u'<br>Actualizada el %s' % datetime.now()
        #     materia.save()
        #     logger.info(u'Se actualiza la materia: %s' % nombre)
        # except:
        #     try:
        #         observaciones = u'Creada el %s' % datetime.now()
        #         Materia.objects.create(curso=curso, nombre=nombre, clave_ex=materia_codigo, observaciones=observaciones,
        #                                horas=horas, duracion=duracion)
        #         logger.info(u'Se ha creado la materia %s, con código %s' % (nombre, materia_codigo))
        #     except:
        #         logger.warning(u'No se ha creado la materia %s. No existe curso %s' % (nombre, materia_codigo))
        #         crear_aviso(request, False,
        #                     u'La materia %s, asignada al curso %s no ha podido ser creada ya que dicho curso no existe.' % (
        #                         nombre, curso_codigo))


    # for elemento in xml_file.xpath(".//grupo_datos[@seq='ACTIVIDADES']/grupo_datos"):
    for elemento in xml_file.findall(".//grupo_datos[@seq='ACTIVIDADES']/grupo_datos"):
        nombre = elemento.find('dato[@nombre_dato="D_ACTIVIDAD"]').text
        actividad_codigo = elemento.find('dato[@nombre_dato="X_ACTIVIDAD"]').text
        try:
            actividad = Actividad.objects.get(clave_ex=actividad_codigo, entidad=g_e.ronda.entidad)
            actividad.nombre = nombre
            actividad.observaciones += u'<br>Actualizada el %s' % datetime.now()
            actividad.save()
            logger.info(u'Se actualiza la actividad: %s' % nombre)
        except:
            observaciones = u'Creada el %s' % datetime.now()
            Actividad.objects.create(nombre=nombre, clave_ex=actividad_codigo, observaciones=observaciones,
                                     entidad=g_e.ronda.entidad)
            logger.info(u'Se ha creado la actividad "%s", con código %s' % (nombre, actividad_codigo))
    # for elemento in xml_file.xpath(".//grupo_datos[@seq='DEPENDENCIAS']/grupo_datos"):
    for elemento in xml_file.findall(".//grupo_datos[@seq='DEPENDENCIAS']/grupo_datos"):
        nombre = elemento.find('dato[@nombre_dato="D_DEPENDENCIA"]').text
        dependencia_codigo = elemento.find('dato[@nombre_dato="X_DEPENDENCIA"]').text
        abrev = elemento.find('dato[@nombre_dato="C_DEPENDENCIA"]').text

        dependencias = Dependencia.objects.filter(entidad=g_e.ronda.entidad, clave_ex=dependencia_codigo)
        if dependencias.count() == 0:
            observaciones = u'Creada el %s' % datetime.now()
            dependencia = Dependencia.objects.create(entidad=g_e.ronda.entidad, nombre=nombre, abrev=abrev,
                                                     clave_ex=dependencia_codigo, observaciones=observaciones)
            logger.info(u'Se ha creado la dependencia "%s", con código %s' % (nombre, dependencia_codigo))
        elif dependencias.count() > 1:
            dependencia = dependencias[0]
            dependencias.exclude(pk__in=[dependencia.pk]).delete()
            dependencia.nombre = nombre
            dependencia.abrev = abrev
            dependencia.observaciones += u'<br>Actualizada el %s' % datetime.now()
            dependencia.save()
            logger.info(u'Se actualiza la dependencia: %s' % nombre)
        else:
            dependencia = dependencias[0]
            dependencia.nombre = nombre
            dependencia.abrev = abrev
            dependencia.observaciones += u'<br>Actualizada el %s' % datetime.now()
            dependencia.save()
            logger.info(u'Se actualiza la dependencia: %s' % nombre)


        # try:
        #     dependencia = Dependencia.objects.get(entidad=g_e.ronda.entidad, clave_ex=dependencia_codigo)
        #     dependencia.nombre = nombre
        #     dependencia.abrev = abrev
        #     materia.observaciones += u'<br>Actualizada el %s' % datetime.now()
        #     dependencia.save()
        #     logger.info(u'Se actualiza la dependencia: %s' % nombre)
        # except:
        #     observaciones = u'Creada el %s' % datetime.now()
        #     Dependencia.objects.create(entidad=g_e.ronda.entidad, nombre=nombre, clave_ex=dependencia_codigo, abrev=abrev,
        #                                observaciones=observaciones)
        #     logger.info(u'Se ha creado la dependencia "%s", con código %s' % (nombre, dependencia_codigo))

    # for elemento in xml_file.xpath(".//grupo_datos[@seq='JORNADAS_ESCOLARES']/grupo_datos"):
    # for elemento in xml_file.findall(".//grupo_datos[@seq='JORNADAS_ESCOLARES']/grupo_datos"):
    #     jornada = elemento.find('dato[@nombre_dato="C_NOMBRE"]').text
    #     jornada_codigo = elemento.find('dato[@nombre_dato="X_PLAJORESCCEN"]').text
    #     try:
    #         jor_existe = Jornada_escolar.objects.get(entidad=g_e_entidad, curso_escolar=g_e_entidad.curso_escolar,
    #                                                  clave_ex=jornada_codigo)
    #         jor_existe.nombre = jornada
    #         jor_existe.save()
    #     except:
    #         Jornada_escolar.objects.create(entidad=g_e_entidad,
    #                                        curso_escolar=g_e_entidad.curso_escolar,
    #                                        nombre=jornada, clave_ex=jornada_codigo)
    #         crear_aviso(request, False, u'Se añade una nueva jornada escolar: ' + jornada)

    # for elemento in xml_file.xpath(".//grupo_datos[@seq='TRAMOS_HORARIOS']/grupo_datos"):
    for elemento in xml_file.findall(".//grupo_datos[@seq='TRAMOS_HORARIOS']/grupo_datos"):
        nombre = elemento.find('dato[@nombre_dato="T_HORCEN"]').text
        tramo_codigo = elemento.find('dato[@nombre_dato="X_TRAMO"]').text
        inicio = int(elemento.find('dato[@nombre_dato="N_INICIO"]').text)
        h_inicio = str(inicio / 60) + ':' + str(inicio % 60)
        fin = int(elemento.find('dato[@nombre_dato="N_FIN"]').text)
        h_fin = str(fin / 60) + ':' + str(fin % 60)
        # jornada_codigo = elemento.find('dato[@nombre_dato="X_PLAJORESCCEN"]').text
        # jornada = Jornada_escolar.objects.get(entidad=g_e_entidad,
        #                                       curso_escolar=g_e_entidad.curso_escolar,
        #                                       clave_ex=jornada_codigo)
        try:
            tramo = Tramo_horario.objects.get(horario=horario, clave_ex=tramo_codigo)
            tramo.nombre = nombre
            tramo.inicio = h_inicio
            tramo.fin = h_fin
            tramo.save()
            logger.info(u'Se actualiza el tramo horario: %s' % nombre)
        except:
            Tramo_horario.objects.create(horario=horario, nombre=nombre,
                                         clave_ex=tramo_codigo, inicio=h_inicio, fin=h_fin)
            logger.info(u'Se ha creado el tramo horario "%s", con código %s' % (nombre, tramo_codigo))

    grupos = Grupo.objects.filter(ronda=g_e.ronda)
    grupos_nombre = [(g.id, g.nombre) for g in grupos]
    # for elemento in xml_file.xpath(".//grupo_datos[@seq='UNIDADES']/grupo_datos"):
    for elemento in xml_file.findall(".//grupo_datos[@seq='UNIDADES']/grupo_datos"):
        nombre = elemento.find('dato[@nombre_dato="T_NOMBRE"]').text
        grupo_codigo = elemento.find('dato[@nombre_dato="X_UNIDAD"]').text
        curso_codigo = elemento.find('dato[@nombre_dato="X_OFERTAMATRIG"]').text
        curso = Curso.objects.get(clave_ex=curso_codigo, ronda=g_e.ronda)
        # Este es el cargado de grupos como objetos tipo Grupo:
        try:
            grupo = Grupo.objects.get(ronda=g_e.ronda, clave_ex=grupo_codigo)
            grupo.nombre = nombre
            grupo.cursos.add(curso)
            if not curso.nombre in grupo.observaciones:
                grupo.observaciones += ', ' + curso.nombre
            grupo.save()
            logger.info(u'Se actualiza el grupo (Grupo): %s' % nombre)
        except:
            grupo_id = get_coincidente(nombre, grupos_nombre)
            if grupo_id:
                try:
                    grupo = Grupo.objects.get(ronda=g_e.ronda, id=grupo_id, clave_ex__isnull=True)
                    grupo.clave_ex = grupo_codigo
                    grupo.cursos.add(curso)
                    if grupo.observaciones:
                        if not curso.nombre in grupo.observaciones:
                            grupo.observaciones += ', ' + curso.nombre
                    else:
                        grupo.observaciones = u'No creada por el xml de Racima'
                    grupo.save()
                    logger.info(u'Se actualiza el grupo (Grupo): %s' % nombre)
                except:
                    observaciones = u'Creado el %s a través del xml de Racima (mixto)' % datetime.now()
                    grupo = Grupo.objects.create(ronda=g_e.ronda, nombre=nombre, clave_ex=grupo_codigo,
                                                 observaciones=observaciones)
                    grupo.cursos.add(curso)
                    logger.warning(u'Se ha creado el grupo "%s", con código %s' % (nombre, grupo_codigo))
            else:
                observaciones = u'Creado el %s a través del xml de Racima' % datetime.now()
                grupo = Grupo.objects.create(ronda=g_e.ronda, nombre=nombre, clave_ex=grupo_codigo,
                                             observaciones=observaciones)
                grupo.cursos.add(curso)
                logger.warning(u'Se ha creado el grupo "%s", con código %s' % (nombre, grupo_codigo))

    sub_docentes = Subentidad.objects.filter(Q(entidad=g_e.ronda.entidad), Q(fecha_expira__gt=datetime.today()),
                                             Q(nombre__icontains='docente') | Q(nombre__icontains='profesor') | Q(
                                                 nombre__icontains='maestro'))
    docentes = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, subentidades__in=sub_docentes, ronda=g_e.ronda)
    nombres_docentes = [(d.id, d.gauser.get_full_name()) for d in docentes]
    for elemento in xml_file.findall(".//grupo_datos[@seq='EMPLEADOS']/grupo_datos"):
        profesor_nombre = elemento.find('dato[@nombre_dato="NOMBRE"]').text
        profesor_apellido1 = elemento.find('dato[@nombre_dato="APELLIDO1"]').text
        profesor_apellido2 = elemento.find('dato[@nombre_dato="APELLIDO2"]').text
        nombre_docente = profesor_nombre + ' ' + profesor_apellido1 + ' ' + profesor_apellido2
        espec = elemento.find('dato[@nombre_dato="D_PUESTO"]').text
        if espec == u"Pedagogía Terapeutica":
            espec = u"Pedagogía Terapéutica"
        profesor_codigo = elemento.find('dato[@nombre_dato="X_EMPLEADO"]').text
        crea_departamentos(g_e.ronda)
        especialidades = Especialidad_entidad.objects.filter(especialidad__nombre__icontains=espec, ronda=g_e.ronda)
        if especialidades.count() == 0:
            esp_funcionario = Especialidad_funcionario.objects.filter(Q(nombre__icontains=espec), ~Q(cuerpo__nombre__icontains="catedr"))
            if esp_funcionario.count() == 0:
                especialidad = None
                crear_aviso(request, False, u'No se ha encontrado la especialidad asociada a: %s' % (espec))
            else:
                especialidad = Especialidad_entidad.objects.create(especialidad=esp_funcionario[0], ronda=g_e.ronda)
        else:
            especialidad = especialidades[0]
        try:
            gauser_extra = Gauser_extra.objects.get(clave_ex=profesor_codigo, ronda=g_e.ronda)
            logger.info(u'Se identifica al gauser_extra: %s' % gauser_extra.gauser.get_full_name())
        except:
            gauser_extra_id = get_coincidente(nombre_docente, nombres_docentes)
            if gauser_extra_id:
                gauser_extra = Gauser_extra.objects.get(ronda=g_e.ronda, id=gauser_extra_id)
                gauser_extra.clave_ex = profesor_codigo
                gauser_extra.save()
                logger.info(u'Se actualiza el docente %s con la clave_ex %s' % (
                    gauser_extra.gauser.get_full_name(), profesor_codigo))
            else:
                logger.warning(u'Docente %s %s no encontrado' % (profesor_nombre, nombre_docente))
                crear_aviso(request, False, u'No se encuentra un gauser_extra de (%s %s) que cumpla condiciones' % (
                    profesor_nombre, nombre_docente))
        if gauser_extra:
            gep = Gauser_extra_programaciones.objects.get_or_create(ge=gauser_extra)
            gep[0].especialidad = especialidad
            try:
                departamento = Departamento.objects.get(nombre__icontains=espec)
                gep[0].departamento = departamento
            except:
                if not gep[0].departamento:
                    logger.warning(u'Docente %s sin departamento %s' % (nombre_docente, espec))
                else:
                    logger.warning(u'Docente %s con departamento ya asignado' % (nombre_docente))

            # if especialidades.count() == 1:
            #     gep[0].especialidad = especialidades[0]
            #     try:
            #         departamento = Departamento.objects.get(nombre=espec)
            #         gep[0].departamento = departamento
            #     except:
            #         logger.warning(u'Docente %s sin departamento %s' % (nombre_docente, espec))
            # elif especialidades.count() == 0:
            #     incidencias['especialidades'] = True
            #     logger.warning(u'Docente %s sin especialidad %s' % (nombre_docente, espec))
            #     crear_aviso(request, False, u'Es necesario asignar la especialidad %s a %s' % (espec, nombre_docente))
            # else:
            #     try:
            #         departamento = Departamento.objects.get(nombre=espec)
            #         gep[0].departamento = departamento
            #     except:
            #         logger.warning(u'Docente %s sin departamento %s' % (nombre_docente, espec))
            #     incidencias['especialidades'] = True
            #     logger.warning(u'Docente %s sin especialidad %s, existen coincidencias' % (nombre_docente, espec))
            incidencias['especialidades'] = True
            gep[0].puesto = espec
            gep[0].save()
    if incidencias:
        crear_aviso(request, False, u'Se han producido incidencias en la asignación de especialidades al profesorado')
    return incidencias


def xml_penalara(xml_file, request):
    g_e = request.session["gauser_extra"]
    horario = Horario.objects.get(entidad=g_e.ronda.entidad, predeterminado=True)
    dias = {'L': 1, 'M': 2, 'X': 3, 'J': 4, 'V': 5, 'S': 6, 'D': 7}

    for sesion in xml_file.findall('.//SESION'):
        clave_docente = sesion.find('DOCENTE').text
        try:
            docente = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, ronda=g_e.ronda, clave_ex=clave_docente)
        except:
            crear_aviso(request, False, u'No se encuentra el docente con clave: %s' % clave_docente)
            logger.info(u'No se encuentra el docente con clave: %s' % clave_docente)
            docente = None

        dia = dias[sesion.find('DIA').text]

        clave_tramo_horario = sesion.find('INTERVALO').text
        try:
            tramo_horario = Tramo_horario.objects.get(horario=horario, clave_ex=clave_tramo_horario)
        except:
            crear_aviso(request, False, u'No se encuentra el tramo horario con clave: %s' % clave_tramo_horario)
            logger.info(u'No se encuentra el tramo horario con clave: %s' % clave_tramo_horario)
            tramo_horario = None

        clave_materia = sesion.find('MATERIA').text
        if clave_materia:
            try:
                materia = Materia.objects.get(clave_ex=clave_materia, curso__ronda=g_e.ronda)
            except:
                if '#' in clave_materia:
                    crear_aviso(request, True,
                                u'Encontrada materia con #. Se buscará la actividad equivalente de código %s' % (
                                    clave_materia))
                else:
                    crear_aviso(request, False, u'No se encuentra la materia con clave: %s. Clave del grupo: %s' % (
                        materia, sesion.find('GRUPO').text))
                materia = None
        else:
            materia = None

        grupo_c = sesion.find('GRUPO').text
        if grupo_c:
            if '-' in grupo_c:  # Si no tiene '-' es porque es un grupo no definido en RACIMA. Por ejemplo 1COMP, 2COMP, ...
                grupo_c = grupo_c.split('-')
                try:
                    grupo = Grupo.objects.get(Q(ronda=g_e.ronda), Q(clave_ex=grupo_c[1]) | Q(nombre=grupo_c[1]))
                except:
                    crear_aviso(request, False, u'No se encuentra el grupo con clave: ' + grupo_c[1])
                    grupo = None
                try:
                    curso = Curso.objects.get(ronda=g_e.ronda, clave_ex=grupo_c[0])
                    grupo.cursos.add(curso)
                    grupo.save()
                except:
                    crear_aviso(request, False, u'No se encuentra el curso con clave: ' + grupo_c[0])
            else:
                try:
                    grupo = Grupo.objects.get(ronda=g_e.ronda, clave_ex=grupo_c, nombre=grupo_c)
                except:
                    grupo = Grupo.objects.create(ronda=g_e.ronda, clave_ex=grupo_c, nombre=grupo_c)
                    crear_aviso(request, False, u'Se ha creado un grupo nuevo: ' + grupo_c)
        else:
            grupo = None

        dependencia = sesion.find('AULA').text
        if dependencia:
            try:
                dependencia = Dependencia.objects.get(entidad=g_e.ronda.entidad, clave_ex=dependencia)
            except:
                crear_aviso(request, False, u'Se crea el aula: ' + dependencia)
                dependencia = Dependencia.objects.create(entidad=g_e.ronda.entidad, nombre=dependencia, clave_ex=dependencia)

        actividad = sesion.find('TAREA').text
        materia_sostenido = sesion.find('MATERIA').text
        if actividad:
            try:
                actividad = Actividad.objects.get(clave_ex=actividad, entidad=g_e.ronda.entidad)
            except:
                try:
                    if '#' in materia_sostenido:
                        materia_sostenido = materia_sostenido.replace('#', '')
                        crear_aviso(request, False, u'Tratando de encontrar la actividad: ' + materia_sostenido)
                        actividad = Actividad.objects.get(clave_ex=materia_sostenido, entidad=g_e.ronda.entidad)
                    else:
                        crear_aviso(request, False, u'Se crea la actividad: ' + actividad)
                        actividad = Actividad.objects.create(nombre=actividad, clave_ex=actividad, entidad=g_e.ronda.entidad)
                except:
                    crear_aviso(request, False, u'Se crea la actividad: ' + actividad)
                    actividad = Actividad.objects.create(nombre=actividad, clave_ex=actividad, entidad=g_e.ronda.entidad)

        if docente:
            Sesion.objects.create(nombre=tramo_horario.nombre, inicio=tramo_horario.inicio, fin=tramo_horario.fin,
                                  g_e=docente, dia=dia, materia=materia, grupo=grupo, dependencia=dependencia,
                                  actividad=actividad, horario=horario)


# @permiso_required('acceso_guardias_horarios')
def guardias_horario(request):
    g_e = request.session['gauser_extra']
    ronda = request.session['ronda']
    if request.method == 'POST':
        if request.POST['action'] == 'download_tarea':
            try:
                guardia = Guardia.objects.get(id=request.POST['guardia_id'], ge__ronda=g_e.ronda)
                response = HttpResponse(File(guardia.tarea), guardia.content_type)
                response['Content-Disposition'] = 'attachment; filename=' + guardia.tarea.url.split('/')[-1]
                return response
            except:
                pass

    horario = Horario.objects.get(entidad=g_e.ronda.entidad, ronda=g_e.ronda, predeterminado=True)
    if 'd' in request.GET:
        fecha = datetime.strptime(request.GET['d'], '%d%m%Y').date()
    else:
        fecha = date.today()
    # dias = ('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo')
    # dia = dias[fecha.weekday()]
    guardias = Guardia.objects.filter(fecha=fecha, sesion__horario=horario)
    id_usuarios = Sesion.objects.filter(horario=horario).values_list('g_e__id')
    usuarios = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, id__in=id_usuarios).distinct()
    tramos = Sesion.objects.filter(horario=horario).values_list('horario', 'inicio', 'fin').distinct().order_by(
        'inicio')

    return render(request, "guardias_horario.html",
                  {
                      'formname': 'guardias_horario',
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'horario': horario,
                      'guardias': guardias,
                      'dia': fecha.isoweekday(),
                      'fecha': fecha,
                      'usuarios': usuarios,
                      'horario_guardias': horario.horario_guardias(fecha.isoweekday())
                  })


# @permiso_required('acceso_guardias_horarios')
def guardias_ajax(request):
    DIAS_SEMANA = ('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo')
    g_e = request.session['gauser_extra']
    action = request.POST['action']
    if request.is_ajax():
        if action == 'add_guardia2':
            observaciones = ' - ' + request.POST['observaciones']
            ge = Gauser_extra.objects.get(id=request.POST['g_e'], entidad=g_e.ronda.entidad)
            horario = Horario.objects.get(id=request.POST['horario'])
            inicio = time(int(request.POST['inicio_hora']), int(request.POST['inicio_minutos']))
            fin = time(int(request.POST['fin_hora']), int(request.POST['fin_minutos']))
            fecha = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
            dia = fecha.isoweekday()
            sesiones = Sesion.objects.filter(horario=horario, inicio=inicio, fin=fin, g_e=ge, dia=dia)
            if sesiones.count() > 0:
                try:
                    grupos = ', '.join(set(sesiones.values_list('grupo__nombre', flat=True)))
                except:
                    grupos = 'Sin grupo de alumnos'
                try:
                    dependencias = ', '.join(set(sesiones.values_list('dependencia__nombre', flat=True)))
                except:
                    dependencias = ''
                usuario = '<br><span style="color:#dc322f">' + ge.gauser.get_full_name() + '</span>'
                obs = '%s - %s - %s - %s' % (usuario, dependencias, grupos, observaciones)
                guardia = Guardia.objects.create(ge=ge, sesion=sesiones[0], fecha=fecha, observaciones=obs)
                texto = render_to_string('guardias_horario_content.html', {'g': guardia, 'request': request})
                return JsonResponse({'texto': texto, 'ok': True})
            else:
                return JsonResponse({'ok': False, 'usuario': ge.gauser.get_full_name()})
        elif action == 'del_guardia':
            try:
                guardia = Guardia.objects.get(id=request.POST['guardia'], ge__entidad=g_e.ronda.entidad)
                if guardia.tarea:
                    os.remove(RUTA_BASE + guardia.tarea.url)
                guardia.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
    else:
        if action == 'add_guardia':
            observaciones = ' - ' + request.POST['observaciones']
            ge = Gauser_extra.objects.get(id=request.POST['g_e'], entidad=g_e.ronda.entidad)
            horario = Horario.objects.get(id=request.POST['horario'])
            inicio = time(int(request.POST['inicio_hora']), int(request.POST['inicio_minutos']))
            fin = time(int(request.POST['fin_hora']), int(request.POST['fin_minutos']))
            fecha = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
            dia = fecha.isoweekday()
            sesiones = Sesion.objects.filter(horario=horario, inicio=inicio, fin=fin, g_e=ge, dia=dia)
            if sesiones.count() > 0:
                try:
                    grupos = ', '.join(set(sesiones.values_list('grupo__nombre', flat=True)))
                except:
                    grupos = 'Sin grupo de alumnos'
                try:
                    dependencias = ', '.join(set(sesiones.values_list('dependencia__nombre', flat=True)))
                except:
                    dependencias = ''
                usuario = '<br><span style="color:#dc322f">' + ge.gauser.get_full_name() + '</span>'
                obs = '%s - %s - %s - %s' % (usuario, dependencias, grupos, observaciones)
                guardia = Guardia.objects.create(ge=ge, sesion=sesiones[0], fecha=fecha, observaciones=obs)
                try:
                    guardia.tarea = request.FILES['fichero_xhr0']
                    guardia.content_type = request.FILES['fichero_xhr0'].content_type
                    guardia.save()
                except:
                    pass
                texto = render_to_string('guardias_horario_content.html', {'g': guardia, 'request': request})
                return JsonResponse({'texto': texto, 'ok': True})
            else:
                return JsonResponse({'ok': False, 'usuario': ge.gauser.get_full_name()})


# @permiso_required('acceso_guardias_horarios')
def alumnos_horarios(request):
    g_e = request.session['gauser_extra']
    ronda = request.session['ronda']
    horario = Horario.objects.get(entidad=g_e.ronda.entidad, ronda=ronda, predeterminado=True)
    grupos = Grupo.objects.filter(ronda=ronda)
    alumnos = Gauser_extra_estudios.objects.filter(grupo__in=grupos)
    tutores_id = alumnos.values_list('tutor__id', flat=True).distinct()
    tutores = Gauser_extra.objects.filter(id__in=tutores_id)
    cotutores_id = alumnos.values_list('cotutor__id', flat=True).distinct()
    cotutores = Gauser_extra.objects.filter(id__in=cotutores_id)
    try:
        alumno = Gauser_extra_estudios.objects.get(id=request.GET['g'], ge__ronda=g_e.ronda)
    except:
        alumno = alumnos[0]
    grupo = grupos.get(id=alumno.grupo.id)

    sesiones_grupo = horario.sesion_set.filter(grupo=grupo)
    dias = sesiones_grupo.values_list('dia', flat=True).order_by('dia').distinct()
    nombre_dias = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 7: 'Domingo'}
    horas_grupo = horario.horas_grupo(grupo)
    sesiones = []
    for d in dias:
        sesiones_dia = sesiones_grupo.filter(dia=d).order_by('inicio')
        info_dia = {'dia_num': d, 'dia_nombre': nombre_dias[d], 'sesiones_dia': []}
        for hora in horas_grupo:
            sesiones_hora = sesiones_dia.filter(inicio=hora['inicio'])
            if sesiones_hora.count() > 0:
                info_dia['sesiones_dia'].append(sesiones_hora)
        sesiones.append(info_dia)

    # sesiones = horario.sesion_set.filter(grupo=grupo).order_by('dia')
    #
    # try:
    #     hora_inicio = sesiones.order_by('inicio').values_list('inicio', flat=True)[0]
    # except:
    #     hora_inicio = None
    return render(request, "alumnos_horarios.html",
                  {
                      'formname': 'horario_subentidad',
                      'sesiones': sesiones,
                      'horario': horario,
                      'horas_grupo': horas_grupo,
                      'alumnos': alumnos,
                      'alumno': alumno,
                      'grupos': grupos,
                      'tutores': tutores,
                      'cotutores': cotutores,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


def alumnos_horarios_ajax(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        action = request.POST['action']
        if action == 'grupo_alumno':
            try:
                geh = Gauser_extra_estudios.objects.get(id=request.POST['alumno'], ge__ronda=g_e.ronda)
                grupo = Grupo.objects.get(id=request.POST['grupo'], ronda=g_e.ronda)
                geh.grupo = grupo
                geh.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        if action == 'tutor_alumno':
            try:
                geh = Gauser_extra_estudios.objects.get(id=request.POST['alumno'], ge__ronda=g_e.ronda)
                tutor = Gauser_extra.objects.get(id=request.POST['tutor'], ronda=g_e.ronda)
                geh.tutor = tutor
                geh.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        if action == 'cotutor_alumno':
            try:
                geh = Gauser_extra_estudios.objects.get(id=request.POST['alumno'], ge__ronda=g_e.ronda)
                cotutor = Gauser_extra.objects.get(id=request.POST['cotutor'], ronda=g_e.ronda)
                geh.cotutor = cotutor
                geh.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
