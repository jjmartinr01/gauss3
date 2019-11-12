# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django import forms
from django.forms import ModelForm
from entidades.models import Gauser_extra, Subentidad
from gauss.funciones import html_to_pdf, usuarios_de_gauss
from gauss.rutas import *
from tutorados.models import Pregunta, Informe_seguimiento, Respuesta, Fichero_tarea, Informe_tareas, Tarea_propuesta
from autenticar.control_acceso import permiso_required
from django.http import HttpResponse, JsonResponse
from datetime import datetime, date, timedelta
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
import simplejson as json
from mensajes.views import crear_aviso, encolar_mensaje
from mensajes.models import Aviso
from zipfile import ZipFile
from django.utils.text import slugify

logger = logging.getLogger('django')

preguntas_base = ['¿Realiza las tareas y ejercicios encomendados con regularidad?',
                  '¿Cómo es su comportamiento en clase?',
                  '¿Cómo es su relación con compañeros y profesores?',
                  '¿Cuál es su forma de actuar con respecto a la puntualidad y asistencia a clase?',
                  'Aspectos en los que ha tenido más dificultades y le han impedido superar la asignatura',
                  '¿Qué notas va sacando en vuestra asignatura?']


@permiso_required('acceso_informes_usuarios')
def informes_seguimiento(request):
    g_e = request.session['gauser_extra']
    informes_solicitados = Informe_seguimiento.objects.filter(solicitante=g_e, usuario__entidad=g_e.ronda.entidad).distinct()
    informes_a_rellenar = Informe_seguimiento.objects.filter(Q(usuarios_destino__in=[g_e]),
                                                             Q(deadline__gte=date.today()),
                                                             ~Q(id__in=informes_solicitados)).distinct()

    if request.method == 'POST':
        if request.POST['action'] == 'pdf_informe_seguimiento':
            informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe_id'])
            if informe.solicitante == g_e or g_e.has_permiso('ve_informes_seguimiento'):
                fichero = 'informe_informe_seguimiento_%s_%s' % (g_e.ronda.entidad.code, informe.id)
                c = render_to_string('informe_seguimiento2pdf.html', {
                    'informe': informe,
                    'MEDIA_ANAGRAMAS': MEDIA_ANAGRAMAS,
                }, request=request)
                ruta = MEDIA_INFORMES + '%s/' % g_e.ronda.entidad.code
                fich = html_to_pdf(request, c, media=ruta, fichero=fichero,
                                   title=u'Expediente de informe_seguimiento')
                logger.info(u'%s, pdf_informe_seguimiento %s' % (g_e, informe.id))
                response = HttpResponse(fich, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=informe_informe_seguimiento_%s_%s.pdf' % (
                    slugify(informe.usuario.gauser.get_full_name()), str(informe.id))
                return response

    return render(request, "informes_seguimiento.html",
                  {
                      'formname': 'informe_seguimiento',
                      'informes_solicitados': informes_solicitados,
                      'informes_a_rellenar': informes_a_rellenar,
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)
                  })


@login_required()
def ajax_informe_seguimiento(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        logger.info(u'%s, %s' % (g_e, request.POST['action']))
        if request.POST['action'] == 'buscar_usuarios_destino':
            q = request.POST['q'].split()
            Q_total = Q(gauser__isnull=False)
            for texto in q:
                Q_parcial = Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)
                Q_total = Q_total & Q_parcial
            sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
            usuarios = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_docentes])
            filtrados = usuarios.filter(Q_total)
            options = []
            for u in filtrados:
                options.append(
                    {'id': u.id, 'text': u.gauser.get_full_name()})
            return JsonResponse(options, safe=False)
        elif request.POST['action'] == 'buscar_usuario':
            q = request.POST['q'].split()
            Q_total = Q(gauser__isnull=False)
            for texto in q:
                Q_parcial = Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)
                Q_total = Q_total & Q_parcial & ~Q(id__in=request.POST.getlist('ges_informes_abiertos[]'))
            sub_alumnos = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='alumnos')
            usuarios = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_alumnos])
            filtrados = usuarios.filter(Q_total)
            options = []
            for u in filtrados:
                try:
                    grupo_nombre = u.gauser_extra_estudios.grupo.nombre
                except:
                    grupo_nombre = 'Sin grupo asignado'
                options.append(
                    {'id': u.id, 'text': u.gauser.get_full_name() + ' (' + grupo_nombre + ')'})
            return JsonResponse(options, safe=False)
        elif request.POST['action'] == 'get_informes_usuario':
            usuario = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['usuario'])
            informes = Informe_seguimiento.objects.filter(Q(usuario=usuario),
                                                          ~Q(id__in=request.POST.getlist('ges_informes_cerrados[]')))
            # data = render_to_string('informes_seguimiento_accordion.html', {'informes': informes, 'g_e': g_e})
            # return JsonResponse({'html': data, 'ok': True, 'usuario_nombre': usuario.gauser.get_full_name()})

            # usuario = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['usuario'])
            # informes = Informe_tareas.objects.filter(Q(usuario=usuario),
            #                                          ~Q(id__in=request.POST.getlist('ges_informes_cerrados[]')))
            crea_informe = False
            ge_informes = []
            for i in informes:
                if g_e in i.usuarios_destino.all() or g_e.has_permiso('ve_informes_seguimiento'):
                    ge_informes.append(i)
            if (g_e in usuario.gauser_extra_estudios.grupo.tutores) or (
                        g_e in usuario.gauser_extra_estudios.grupo.cotutores) or g_e.has_permiso(
                'solicita_informes_seguimiento'):
                crea_informe = True
            if len(ge_informes) > 0:
                data = render_to_string('informes_seguimiento_accordion.html', {'informes': ge_informes, 'g_e': g_e})
            else:
                data = False
            return JsonResponse({'html': data, 'ok': True, 'usuario_nombre': usuario.gauser.get_full_name(),
                                 'crea_informe': crea_informe})
        elif request.POST['action'] == 'solicitar_informe':
            usuario = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['usuario_id'])
            if (g_e in usuario.gauser_extra_estudios.grupo.tutores) or g_e.has_permiso(
                    'solicita_informes_seguimiento') or (g_e in usuario.gauser_extra_estudios.grupo.cotutores):
                try:
                    informe = Informe_seguimiento.objects.get(usuario=usuario, deadline__gte=date.today())
                    html = False
                except:
                    texto_solicitud = 'Hola, voy a tener una reunión para hablar de {0}. Por favor, responde a ' \
                                      'las siguientes preguntas'.format(usuario.gauser.get_full_name())
                    deadline = date.today() + timedelta(days=7)
                    informe = Informe_seguimiento.objects.create(usuario=usuario, solicitante=g_e, deadline=deadline,
                                                                 texto_solicitud=texto_solicitud,
                                                                 fecha=datetime.today())
                    try:
                        grupo = usuario.gauser_extra_estudios.grupo
                        ges = set(grupo.sesion_set.all().values_list('g_e', flat=True))
                        informe.usuarios_destino.add(*ges)
                    except:
                        pass
                    html = render_to_string('informes_seguimiento_accordion.html', {'informes': [informe], 'g_e': g_e})
                return JsonResponse({'html': html, 'ok': True, 'informe': informe.id})
            else:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
            docentes = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_docentes])
            informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
            data = render_to_string('informe_seguimiento_accordion_content.html',
                                    {'informe': informe, 'g_e': g_e, 'docentes': docentes, 'preguntas': preguntas_base})
            return HttpResponse(data)
        elif request.POST['action'] == 'deadline':
            try:
                informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
                informe.deadline = datetime.strptime(request.POST['deadline'], '%d/%m/%Y').date()
                informe.save()
                estado = 'closed' if informe.deadline < date.today() else 'open'
                return JsonResponse({'ok': True, 'estado': estado, 'inf': informe.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'del_informe_seguimiento':
            try:
                informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
                informe.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'del_participacion_informe_seguimiento':
            try:
                informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
                informe.usuarios_destino.remove(g_e)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'texto_solicitud':
            try:
                informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
                informe.texto_solicitud = request.POST['texto']
                informe.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'mod_usuarios_destino' and g_e.has_permiso('solicita_informes_seguimiento'):
            informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
            usuarios = Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('usuarios[]'))
            informe.usuarios_destino.clear()
            informe.usuarios_destino.add(*usuarios)
            return JsonResponse({'ok': True, 'n': informe.usuarios_destino.all().count()})
        elif request.POST['action'] == 'aviso_informe_seguimiento':
            informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
            asunto = render_to_string('informe_seguimiento_mail_asunto.html', {'informe': informe})
            texto = render_to_string('informe_seguimiento_mail.html', {'informe': informe})
            receptores = []
            for ge in informe.usuarios_destino.all():
                if ge.respuesta_set.filter(pregunta__informe=informe).count() != informe.pregunta_set.all().count():
                    Aviso.objects.create(usuario=ge, aviso=texto, fecha=datetime.now(), aceptado=False,
                                         link='/informes_seguimiento')
                    receptores.append(ge.gauser)
            encolar_mensaje(emisor=g_e, receptores=receptores, asunto=asunto, html=texto)
            return JsonResponse({'ok': True})
        elif request.POST['action'] == 'add_pregunta_informe' and g_e.has_permiso('solicita_informes_seguimiento'):
            informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
            n = request.POST['n']
            if n == 'nueva':
                p = Pregunta.objects.create(informe=informe, pregunta='')
            else:
                p = Pregunta.objects.create(informe=informe, pregunta=preguntas_base[int(n)])
            html = render_to_string('informe_seguimiento_accordion_content_pregunta.html', {'pregunta': p, 'g_e': g_e})
            return JsonResponse({'ok': True, 'html': html})
        elif request.POST['action'] == 'delete_pregunta':
            ok = False
            try:
                pregunta = Pregunta.objects.get(informe__usuario__ronda=g_e.ronda, id=request.POST['pregunta'])
                pregunta_id = pregunta.id
                informe = pregunta.informe
                if g_e.has_permiso('borra_preguntas_informes_seguimiento') or pregunta.informe.solicitante == g_e:
                    pregunta.delete()
                    ok = True
                n_preguntas = informe.pregunta_set.all().count()
                return JsonResponse({'pregunta': pregunta_id, 'n_preguntas': n_preguntas, 'ok': ok})
            except:
                return JsonResponse({'ok': ok})
        elif request.POST['action'] == 'pregunta':
            try:
                informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
                pregunta = Pregunta.objects.get(informe=informe, id=request.POST['pregunta'])
                pregunta.pregunta = request.POST['texto']
                pregunta.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'respuesta_a_pregunta':
            try:
                informe = Informe_seguimiento.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
                responde = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge'])
                pregunta = Pregunta.objects.get(informe=informe, id=request.POST['pregunta'])
                try:
                    respuesta, c = Respuesta.objects.get_or_create(informe=informe, usuario=responde, pregunta=pregunta)
                except:
                    Respuesta.objects.filter(informe=informe, usuario=responde, pregunta=pregunta).delete()
                    respuesta = Respuesta.objects.create(informe=informe, usuario=responde, pregunta=pregunta)
                respuesta.respuesta = request.POST['respuesta']
                respuesta.save()
                return JsonResponse({'ok': True, 'n': informe.num_usuarios_respondido})
            except:
                return JsonResponse({'ok': False})
        else:
            logger.info(u'%s, acción no permitida' % (g_e))
            return HttpResponse(False)

    else:
        return HttpResponse(status=400)


# ########################################################################
# INFORMES CON TRABAJOS

@permiso_required('acceso_informes_tareas')
def informes_tareas(request):
    g_e = request.session['gauser_extra']
    informes_solicitados = Informe_tareas.objects.filter(solicitante=g_e, usuario__entidad=g_e.ronda.entidad).distinct()
    informes_a_rellenar = Informe_tareas.objects.filter(Q(usuario__entidad=g_e.ronda.entidad), Q(usuarios_destino__in=[g_e]),
                                                        Q(deadline__gte=date.today()),
                                                        ~Q(id__in=informes_solicitados)).distinct()

    if request.method == 'POST':
        if request.POST['action'] == 'pdf_informe_tareas':
            informe = Informe_tareas.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe_id'])
            ficheros_list = Fichero_tarea.objects.filter(tarea__informe=informe)
            if informe.solicitante == g_e or g_e.has_permiso('ve_informes_tareas'):
                fichero = 'informe_informe_tareas_%s_%s' % (g_e.ronda.entidad.code, informe.id)
                c = render_to_string('informe_tareas2pdf.html', {
                    'informe': informe,
                    'ficheros_list': ficheros_list,
                    'MEDIA_ANAGRAMAS': MEDIA_ANAGRAMAS,
                }, request=request)

                ruta = MEDIA_INFORMES + '%s/' % g_e.ronda.entidad.code
                # attach = ''
                # for archivo in ficheros_list:
                #     attach += RUTA_BASE + archivo.fichero.url + ' '
                # logger.info(attach)
                # fich = html_to_pdf(request, c, media=ruta, fichero=fichero,
                #                    title=u'Expediente de informe_tareas', attach=attach)
                fich = html_to_pdf(request, c, media=ruta, fichero=fichero, title=u'Expediente de informe_tareas')
                if ficheros_list.count() > 0:
                    ruta_zip = ruta + 'informe_informe_tareas_%s_%s.zip' % (g_e.ronda.entidad.code, informe.id)
                    with ZipFile(ruta_zip, 'w') as zipObj:
                        # Add multiple files to the zip
                        informe_pdf = ruta + fichero + '.pdf'
                        zipObj.write(informe_pdf, os.path.basename(informe_pdf))
                        for f in ficheros_list:
                            zipObj.write(f.fichero.path, os.path.basename(f.fichero.path))
                    fich = open(ruta_zip, 'rb')
                    logger.info(u'%s, pdf_informe_tareas %s' % (g_e, informe.id))
                    response = HttpResponse(fich, content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=informe_informe_tareas_%s_%s.zip' % (
                        slugify(informe.usuario.gauser.get_full_name()), str(informe.id))
                    return response
                else:
                    logger.info('%s, pdf_informe_tareas %s' % (g_e, informe.id))
                    response = HttpResponse(fich, content_type='application/pdf')
                    response['Content-Disposition'] = 'attachment; filename=informe_informe_tareas_%s_%s.pdf' % (
                        slugify(informe.usuario.gauser.get_full_name()), str(informe.id))
                    return response

    return render(request, "informes_tareas.html",
                  {
                      'formname': 'informe_tareas',
                      'informes_solicitados': informes_solicitados,
                      'informes_a_rellenar': informes_a_rellenar,
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)
                  })


# @permiso_required('acceso_informes_tareas')
def ajax_informe_tareas(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        logger.info(u'%s, %s' % (g_e, request.POST['action']))
        if request.POST['action'] == 'buscar_usuarios_destino':
            q = request.POST['q'].split()
            Q_total = Q(gauser__isnull=False)
            for texto in q:
                Q_parcial = Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)
                Q_total = Q_total & Q_parcial
            sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
            usuarios = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_docentes])
            filtrados = usuarios.filter(Q_total)
            options = []
            for u in filtrados:
                options.append(
                    {'id': u.id, 'text': u.gauser.get_full_name()})
            return JsonResponse(options, safe=False)
        elif request.POST['action'] == 'buscar_usuario':
            q = request.POST['q'].split()
            Q_total = Q(gauser__isnull=False)
            for texto in q:
                Q_parcial = Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)
                Q_total = Q_total & Q_parcial & ~Q(id__in=request.POST.getlist('ges_informes_abiertos[]'))
            sub_alumnos = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='alumnos')
            usuarios = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_alumnos])
            filtrados = usuarios.filter(Q_total)
            options = []
            for u in filtrados:
                try:
                    grupo_nombre = u.gauser_extra_estudios.grupo.nombre
                except:
                    grupo_nombre = 'Sin grupo asignado'
                options.append(
                    {'id': u.id, 'text': u.gauser.get_full_name() + ' (' + grupo_nombre + ')'})
            return JsonResponse(options, safe=False)
        elif request.POST['action'] == 'get_informes_usuario':
            usuario = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['usuario'])
            informes = Informe_tareas.objects.filter(Q(usuario=usuario),
                                                     ~Q(id__in=request.POST.getlist('ges_informes_cerrados[]')))
            crea_informe = False
            ge_informes = []
            for i in informes:
                if g_e in i.usuarios_destino.all() or g_e.has_permiso('ve_informes_tareas'):
                    ge_informes.append(i)
            if (g_e in usuario.gauser_extra_estudios.grupo.tutores) or (
                        g_e in usuario.gauser_extra_estudios.grupo.cotutores) or g_e.has_permiso(
                'solicita_informes_tareas'):
                crea_informe = True
            if len(ge_informes) > 0:
                data = render_to_string('informes_tareas_accordion.html', {'informes': ge_informes, 'g_e': g_e})
            else:
                data = False
            return JsonResponse({'html': data, 'ok': True, 'usuario_nombre': usuario.gauser.get_full_name(),
                                 'crea_informe': crea_informe})

        elif request.POST['action'] == 'solicitar_informe':
            usuario = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['usuario_id'])
            if (g_e in usuario.gauser_extra_estudios.grupo.tutores) or g_e.has_permiso('solicita_informes_tareas') or (
                        g_e in usuario.gauser_extra_estudios.grupo.cotutores):
                try:
                    informe = Informe_tareas.objects.get(usuario=usuario, deadline__gte=date.today())
                    html = False
                except:
                    t = 'el alumno' if usuario.gauser.sexo == 'H' else 'la alumna'
                    texto_solicitud = 'Hola, {0} {1} ... '.format(t, usuario.gauser.get_full_name())
                    deadline = date.today() + timedelta(days=7)
                    informe = Informe_tareas.objects.create(usuario=usuario, solicitante=g_e, fecha=datetime.today(),
                                                            texto_solicitud=texto_solicitud, deadline=deadline)
                    try:
                        grupo = usuario.gauser_extra_estudios.grupo
                        ges = set(grupo.sesion_set.all().values_list('g_e', flat=True))
                        informe.usuarios_destino.add(*ges)
                    except:
                        pass
                    html = render_to_string('informes_tareas_accordion.html', {'informes': [informe], 'g_e': g_e})
                return JsonResponse({'html': html, 'ok': True, 'informe': informe.id})
            else:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            informe = Informe_tareas.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
            data = render_to_string('informe_tareas_accordion_content.html', {'informe': informe, 'g_e': g_e})
            return HttpResponse(data)
        elif request.POST['action'] == 'deadline':
            try:
                informe = Informe_tareas.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
                informe.deadline = datetime.strptime(request.POST['deadline'], '%d/%m/%Y').date()
                informe.save()
                estado = 'closed' if informe.deadline < date.today() else 'open'
                return JsonResponse({'ok': True, 'estado': estado, 'inf': informe.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'del_informe_tareas':
            try:
                informe = Informe_tareas.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
                informe.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'texto_solicitud':
            try:
                informe = Informe_tareas.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
                informe.texto_solicitud = request.POST['texto']
                informe.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'mod_usuarios_destino' and g_e.has_permiso('solicita_informes_tareas'):
            informe = Informe_tareas.objects.get(usuario__entidad=g_e.ronda.entidad,
                                                 usuario__ronda=g_e.ronda, id=request.POST['informe'])
            usuarios = Gauser_extra.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('usuarios[]'))
            informe.usuarios_destino.clear()
            informe.usuarios_destino.add(*usuarios)
            return JsonResponse({'ok': True, 'n': informe.usuarios_destino.all().count()})
        elif request.POST['action'] == 'aviso_informe_tareas':
            informe = Informe_tareas.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
            asunto = render_to_string('informe_tareas_mail_asunto.html', {'informe': informe})
            texto = render_to_string('informe_tareas_mail.html', {'informe': informe})
            receptores = []
            for ge in informe.usuarios_destino.all():
                if ge.tarea_propuesta_set.filter(informe=informe).count() == 0:
                    Aviso.objects.create(usuario=ge, aviso=texto, fecha=datetime.now(), aceptado=False,
                                         link='/informes_tareas')
                    receptores.append(ge.gauser)
            encolar_mensaje(emisor=g_e, receptores=receptores, asunto=asunto, html=texto)
            return JsonResponse({'ok': True})
        elif request.POST['action'] == 'update_texto_tarea':
            try:
                informe = Informe_tareas.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
                tarea, c = Tarea_propuesta.objects.get_or_create(usuario=g_e, informe=informe)
                if c:
                    tarea.fecha = datetime.today()
                tarea.texto_tarea = request.POST['texto']
                tarea.save()
                return JsonResponse({'ok': True, 'respuestas': informe.tarea_propuesta_set.all().count()})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'remove_file':
            file_tarea = Fichero_tarea.objects.get(id=request.POST['id'])
            os.remove(RUTA_BASE + file_tarea.fichero.url)
            file_tarea.delete()
            return JsonResponse({'ok': True, 'id': request.POST['id']})
    elif request.POST['action'] == 'upload_fichero_tarea':
        informe = Informe_tareas.objects.get(usuario__ronda=g_e.ronda, id=request.POST['informe'])
        tarea = Tarea_propuesta.objects.get(usuario=g_e, informe=informe)
        n_files = int(request.POST['n_files'])
        ficheros = []
        for i in range(n_files):
            fichero = request.FILES['fichero_xhr' + str(i)]
            fichero_tarea = Fichero_tarea.objects.create(tarea=tarea, fichero=fichero,
                                                         content_type=fichero.content_type)
            ficheros.append(
                {'file_name': fichero_tarea.fich_name, 'url': fichero_tarea.fichero.url, 'id': fichero_tarea.id})
        return JsonResponse({'ficheros': ficheros})
    else:
        return HttpResponse(status=400)
