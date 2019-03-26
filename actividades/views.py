# -*- coding: utf-8 -*-
import os
from datetime import datetime, date, timedelta
from django.core import serializers
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q, F
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
import simplejson as json
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from horarios.models import Tramo_horario
from estudios.models import  Grupo, Gauser_extra_estudios
from entidades.models import Entidad, Gauser_extra, Subentidad
# from autenticar.models import Gauser_extra, Perfil
from gauss.funciones import html_to_pdf, pass_generator, usuarios_de_gauss
from actividades.models import Actividad, File_actividad
from gauss.rutas import *
from mensajes.views import crear_aviso
from mensajes.models import Aviso
from calendario.models import Vevent


def actividades2slides(request):
    entidad = Entidad.objects.get(id=request.GET['c'])
    acs = Actividad.objects.filter(organizador__ronda__entidad=entidad, organizador__ronda=entidad.ronda,
                                   slideable=True)
    actividades_ids = acs.values_list('id', flat=True)
    file_actividades = File_actividad.objects.filter(actividad__id__in=actividades_ids)
    num_actividades_con_files = file_actividades.values_list('actividad__id', flat=True).distinct().count()
    num_slides = acs.count() - num_actividades_con_files + file_actividades.count()

    # actividades=[]
    # for actividad in acs:
    #     a={'id': actividad.id, 'title': actividad.actividad_title, 'inicio': actividad.fecha_inicio.strftime("%d-%m-%Y"),
    #        'desc': actividad.description[:50], 'grupos': "-".join(actividad.nombre_grupos_incluidos), 'ficheros':[]}
    #     for fichero in actividad.file_actividad_set.all():
    #         a['ficheros'].append({'id': fichero.id, 'url': fichero.fichero.url})
    #     actividades.append(a)

    return render(request, "actividades2slides.html",
                  {
                      'formname': 'Extraescolares',
                      # 'actividades': json.dumps(actividades),
                      'actividades': acs,
                      'num_slides': num_slides
                  })


def actividades_xml(request):
    entidad = Entidad.objects.get(id=request.GET['c'])
    actividades = Actividad.objects.filter(organizador__ronda__entidad=entidad, organizador__ronda=entidad.ronda)
    # response = render_to_string('actividades2xml.html', {'actividades': actividades})
    response = render(request, 'actividades2xml.html', {'actividades': actividades})
    response['Content-Type'] = 'application/xml;'
    return response


def actividades_json(request):
    entidad = Entidad.objects.get(id=request.GET['c'])
    actividades = Actividad.objects.filter(organizador__ronda__entidad=entidad, organizador__ronda=entidad.ronda)
    data = []
    for actividad in actividades:
        dict_act = {'organizador': actividad.organizador.gauser.get_full_name(), 'colaboradores': [],
                    'description': actividad.description, 'fecha_inicio': actividad.fecha_inicio.strftime("%d-%m-%Y"),
                    'fecha_fin': actividad.fecha_fin.strftime("%d-%m-%Y"), 'tramos_horarios': [], 'ficheros': [],
                    'actividad_title': actividad.actividad_title}
        for colaborador in actividad.colaboradores.all():
            dict_act['colaboradores'].append(colaborador.gauser.get_full_name())
        for tramo in actividad.tramos_horarios.all():
            dict_act['tramos_horarios'].append(tramo.tramo)
        for fichero in actividad.file_actividad_set.all():
            dict_act['ficheros'].append(fichero.fichero.url)
        data.append(dict_act)
    return JsonResponse(data, safe=False)


# @login_required()
def gestionar_actividades(request):
    g_e = request.session['gauser_extra']

    def actividades_list():
        actividades_existentes = Actividad.objects.filter(organizador__ronda=g_e.ronda)
        if actividades_existentes.count() > 0:
            p = 5
            previo = datetime.now() - timedelta(days=1)
            posterior = datetime.now() + timedelta(days=p)
            actividades = actividades_existentes.filter(fecha_hora_fin__gt=previo).order_by('fecha_hora_inicio')[:10]
            while actividades.count() == 0:
                p += 1
                posterior = datetime.now() + timedelta(days=p)
                actividades = actividades_existentes.filter(fecha_hora_inicio__lt=posterior, fecha_hora_fin__gt=previo).order_by(
                    'fecha_hora_inicio').reverse()
                if p == 10:
                    actividades = actividades_existentes.order_by('-fecha_hora_inicio')[:3]
        else:
            actividades = None
        return actividades

    def pdf_actividades(actividad):
        if actividad == 'todas' and g_e.has_permiso('crea_informe_actividades'):
            fecha_inicio = datetime.strptime(request.POST['search_fecha_inicio'], '%d-%m-%Y')
            fecha_fin = datetime.strptime(request.POST['search_fecha_fin'], '%d-%m-%Y')
            actividades = Actividad.objects.filter(organizador__ronda__entidad=g_e.ronda.entidad,
                                                   fecha_inicio__gte=fecha_inicio,
                                                   fecha_fin__lte=fecha_fin).order_by(
                'fecha_inicio')
            fichero = 'memoria_extraescolares_' + str(g_e.ronda.entidad.code) + '.pdf'
            profesores = []
            sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
            docentes = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_docentes])

            for docente in docentes:
                organizaciones_actividad = actividades.filter(organizador=docente).distinct()
                colaboraciones_actividad = actividades.filter(colaboradores__in=[docente]).distinct()
                duracion_mayor_un_dia = actividades.filter(Q(colaboradores__in=[docente]) | Q(organizador=docente),
                                                           ~Q(fecha_inicio=F('fecha_fin'))).distinct()
                profesores.append({'docente': docente.gauser.get_full_name(),
                                   'organizaciones_actividad': organizaciones_actividad,
                                   'colaboraciones_actividad': colaboraciones_actividad,
                                   'duracion_mayor_un_dia': duracion_mayor_un_dia})
        else:
            actividades = Actividad.objects.filter(pk=actividad)
            fichero = 'actividad_%s_%s.pdf' % (g_e.ronda.entidad.code, actividad)
            profesores = []
        c = render_to_string('actividades2pdf.html', {'actividades': actividades, 'profesores': profesores},
                             request=request)
        fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_DOCUMENTOS,
                           title=u'Listado de actividades actividades')
        response = HttpResponse(fich, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=' + fichero
        return response

    if request.method == 'POST':
        if request.POST['action'] == 'pdf_actividades':
            response = pdf_actividades(request.POST['id_actividad'])
            return response
        elif request.POST['action'] == 'FileUpload':
            return HttpResponse(True)
    else:
        if 'pdf' in request.GET:
            response = pdf_actividades(request.GET['act'])
            return response
        actividades = actividades_list()
    sin_aprobar = Actividad.objects.filter(organizador__ronda__entidad=g_e.ronda.entidad, aprobada=False,
                                           organizador__ronda=g_e.ronda).count()
    return render(request, "actividades.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nueva',
                            'title': 'Crear una nueva actividad extraescolar', 'permiso': 'crea_actividad'},
                           {'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF',
                            'title': 'Generar PDF de todas las actividades',
                            'permiso': 'crea_informe_actividades'},
                           {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Ver todas',
                            'title': 'Ver todas las actividades', 'permiso': 'crea_actividad'},
                           ),
                      'formname': 'Extraescolares',
                      'actividades': actividades,
                      'sin_aprobar': sin_aprobar,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


def crea_evento_actividad(g_e, actividad):
    description = render_to_string('actividad_event_description.html', {'actividad': actividad})
    evento = Vevent.objects.create(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id),
                                   description=description, dtstart=actividad.fecha_hora_inicio,
                                   dtend=actividad.fecha_hora_fin, summary=actividad.actividad_title)
    evento.propietarios.add(g_e.gauser)
    evento.subentidades.add(*Subentidad.objects.filter(entidad=g_e.ronda.entidad))
    return evento


@login_required()
def ajax_actividades(request):
    g_e = request.session["gauser_extra"]
    if request.is_ajax():
        if request.method == 'POST':
            if request.POST['action'] == 'remove_file':
                file_actividad = File_actividad.objects.get(code=request.POST['file_code'])
                os.remove(RUTA_BASE + file_actividad.fichero.url)
                file_actividad.delete()
                return HttpResponse(request.POST['file_code'])

            elif request.POST['action'] == 'open_accordion':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                html = render_to_string('actividad_accordion_content.html', {'actividad': actividad, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})

            elif request.POST['action'] == 'delete_actividad':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                mensaje = ''
                try:
                    evento = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id))
                    evento.delete()
                    mensaje += 'Se ha borrado el evento del calendario relacionado con la actividad.'
                except:
                    mensaje += '<i class="fa fa-warning"></i> No se ha podido localizar el evento del calendario ' \
                               'relacionado con la actividad.'
                files_actividad = actividad.file_actividad_set.all()
                if actividad.organizador == g_e or g_e.has_permiso('borra_actividad'):
                    for file_actividad in files_actividad:
                        os.remove(RUTA_BASE + file_actividad.fichero.url)
                        mensaje += '<br>Borrado el archivo %s' % (file_actividad.fichero.url)
                        file_actividad.delete()
                    mensaje += '<br>Se ha borrado la actividad.'
                    actividad.delete()
                return JsonResponse({'mensaje': mensaje, 'ok': True})
            elif request.POST['action'] == 'add_actividad':
                try:
                    actividad = Actividad.objects.create(organizador=g_e, actividad_title='Nueva actividad',
                                                         description='Este es un resumen de la actividad',
                                                         fecha_hora_inicio=datetime.now(), fecha_hora_fin=datetime.now())
                    crea_evento_actividad(g_e, actividad)
                    html = render_to_string('actividad_accordion.html', {'actividades': [actividad]})
                    return JsonResponse({'html': html, 'ok': True})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'get_actividad':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                return HttpResponse(render_to_string('actividad_accordion.html', {'actividades': [actividad]}))
            elif request.POST['action'] == 'aceptar_fecha_aprobacion_general':
                try:
                    actividades = Actividad.objects.filter(organizador__ronda__entidad=g_e.ronda.entidad, aprobada=False,
                                                           organizador__ronda=g_e.ronda)
                    fecha = datetime.strptime(request.POST['fecha'], '%d-%m-%Y')
                    for actividad in actividades:
                        actividad.aprobada = True
                        actividad.fecha_aprobacion = fecha
                        actividad.save()
                    return JsonResponse({'success': True})
                except:
                    return JsonResponse({'success': False})
            elif request.POST['action'] == 'update_fecha_aprobacion':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                try:
                    fecha = datetime.strptime(request.POST['fecha'], '%d-%m-%Y')
                    actividad.fecha_aprobacion = fecha
                    actividad.save()
                    return HttpResponse(True)
                except:
                    return HttpResponse(False)
            elif request.POST['action'] == 'update_fecha_inicio':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                try:
                    fecha = datetime.strptime(request.POST['fecha'], '%d-%m-%Y %H:%M')
                    actividad.fecha_hora_inicio = fecha
                    actividad.save()
                    try:
                        evento = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id))
                    except:
                        evento = crea_evento_actividad(g_e, actividad)
                    evento.dtstart = actividad.fecha_hora_inicio
                    evento.save()
                    return HttpResponse(True)
                except:
                    return HttpResponse(False)
            elif request.POST['action'] == 'update_fecha_fin':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                try:
                    fecha = datetime.strptime(request.POST['fecha'], '%d-%m-%Y %H:%M')
                    actividad.fecha_hora_fin = fecha
                    actividad.save()
                    try:
                        evento = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id))
                    except:
                        evento = crea_evento_actividad(g_e, actividad)
                    evento.dtend = actividad.fecha_hora_fin
                    evento.save()
                    return HttpResponse(True)
                except:
                    return HttpResponse(False)
            elif request.POST['action'] == 'update_actividad_title':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                try:
                    actividad.actividad_title = request.POST['actividad_title']
                    actividad.save()
                    try:
                        evento = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id))
                    except:
                        evento = crea_evento_actividad(g_e, actividad)
                    evento.summary = actividad.actividad_title
                    evento.save()
                    return JsonResponse({'success': True, 'actividad_title': actividad.actividad_title})
                except:
                    return JsonResponse({'success': False})
            elif request.POST['action'] == 'update_organizador':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                try:
                    organizador = Gauser_extra.objects.get(id=request.POST['organizador'], entidad=g_e.ronda.entidad)
                    actividad.organizador = organizador
                    actividad.save()
                    try:
                        evento = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id))
                    except:
                        evento = crea_evento_actividad(g_e, actividad)
                    description = render_to_string('actividad_event_description.html', {'actividad': actividad})
                    evento.propietarios.clear()
                    evento.propietarios.add(actividad.organizador.gauser)
                    evento.description = description
                    evento.save()
                    return HttpResponse(True)
                except:
                    return HttpResponse(False)
            elif request.POST['action'] == 'update_colaboradores':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                try:
                    if 'added[]' in request.POST:
                        ges = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('added[]'))
                        actividad.colaboradores.add(*ges)
                    if 'removed[]' in request.POST:
                        ges = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('removed[]'))
                        actividad.colaboradores.remove(*ges)
                    try:
                        evento = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id))
                    except:
                        evento = crea_evento_actividad(g_e, actividad)
                    description = render_to_string('actividad_event_description.html', {'actividad': actividad})
                    evento.description = description
                    evento.save()
                    return HttpResponse(True)
                except:
                    return HttpResponse(False)
            elif request.POST['action'] == 'update_tramos_horarios':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                try:
                    tramo = Tramo_horario.objects.get(horario__ronda__entidad=g_e.ronda.entidad, id=request.POST['tramo_horario'])
                    if request.POST['operation'] == 'added':
                        actividad.tramos_horarios.add(tramo)
                    else:
                        actividad.tramos_horarios.remove(tramo)
                    try:
                        fin = actividad.tramos_horarios.all().order_by('fin').last().fin
                    except:
                        fin = \
                            Tramo_horario.objects.filter(horario__ronda=g_e.ronda).order_by('fin').last().fin
                    try:
                        inicio = actividad.tramos_horarios.all().earliest('inicio').inicio
                    except:
                        inicio = \
                            Tramo_horario.objects.filter(horario__ronda=g_e.ronda).order_by(
                                'inicio')[0].inicio
                    try:
                        evento = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id))
                    except:
                        evento = crea_evento_actividad(g_e, actividad)
                    evento.dtend = datetime.combine(actividad.fecha_fin, fin)
                    evento.dtstart = datetime.combine(actividad.fecha_inicio, inicio)
                    evento.save()
                    return HttpResponse(True)
                except:
                    return HttpResponse(False)
            elif request.POST['action'] == 'todos_ninguno':
                try:
                    alumnos_id = request.POST.getlist('alumnos_id[]')
                    alumnos = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, id__in=alumnos_id)
                    actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                    if request.POST['operation'] == 'select_ninguno':
                        actividad.alumnos_incluidos.remove(*alumnos)
                    else:
                        actividad.alumnos_incluidos.add(*alumnos)
                    return JsonResponse({'ok': True})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'update_alumnos_incluidos':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                ge = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['alumno'])
                if request.POST['operation'] == 'added':
                    actividad.alumnos_incluidos.add(ge)
                else:
                    actividad.alumnos_incluidos.remove(ge)
                try:
                    evento = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id))
                except:
                    evento = crea_evento_actividad(g_e, actividad)
                description = render_to_string('actividad_event_description.html', {'actividad': actividad})
                evento.description = description
                evento.save()
                return HttpResponse(True)
            elif request.POST['action'] == 'update_grupos':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                grupo = Grupo.objects.get(ronda=g_e.ronda, id=request.POST['grupo'])
                alumnos = Gauser_extra_estudios.objects.filter(grupo=grupo).values_list('ge__id', flat=True)
                if request.POST['operation'] == 'added':
                    actividad.alumnos_incluidos.add(*alumnos)
                    html = render_to_string('actividad_accordion_content_grupo_alumno.html',
                                            {'grupo': grupo, 'actividad': actividad})
                    data = {'grupo': 'En este caso, esta variable no se utiliza', 'html': html}
                else:
                    actividad.alumnos_incluidos.remove(*alumnos)
                    data = {'grupo': grupo.id, 'html': False}
                try:
                    evento = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id))
                except:
                    evento = crea_evento_actividad(g_e, actividad)
                description = render_to_string('actividad_event_description.html', {'actividad': actividad})
                evento.description = description
                evento.save()
                return JsonResponse(data)
            elif request.POST['action'] == 'update_texto_actividad':
                actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
                actividad.description = request.POST['texto']
                actividad.save()
                try:
                    evento = Vevent.objects.get(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id))
                except:
                    evento = crea_evento_actividad(g_e, actividad)
                description = render_to_string('actividad_event_description.html', {'actividad': actividad})
                evento.description = description
                evento.save()
                return HttpResponse(True)
            elif request.POST['action'] == 'busca_actividades':
                fecha_inicio = datetime.strptime(request.POST['id_fecha_inicio'], '%d-%m-%Y')
                fecha_fin = datetime.strptime(request.POST['id_fecha_fin'], '%d-%m-%Y')
                texto = request.POST['texto']
                actividades = Actividad.objects.filter(Q(organizador__ronda=g_e.ronda),
                                                       Q(description__icontains=texto) | Q(
                                                           organizador__gauser__first_name__icontains=texto) | Q(
                                                           organizador__gauser__last_name__icontains=texto) | Q(
                                                           actividad_title__icontains=texto),
                                                       Q(fecha_hora_inicio__gt=fecha_inicio),
                                                       Q(fecha_hora_fin__lt=fecha_fin))
                if actividades.count() > 0:
                    html = render_to_string('actividad_accordion.html', {'actividades': actividades, 'check': True})
                else:
                    html = '<h3 style="color:red">No se han encontrado resultados</h3>'
                return JsonResponse({'html': html, 'ok': True})
            elif request.POST['action'] == 'paginar_actividades':
                try:
                    actividades = Actividad.objects.filter(organizador__ronda=g_e.ronda)
                    paginator = Paginator(actividades, 25)
                    actividades_page = paginator.page(int(request.POST['page']))
                    html = render_to_string('actividad_accordion.html', {'actividades': actividades_page, 'pag': True})
                    return JsonResponse({'ok': True, 'html': html})
                except:
                    return JsonResponse({'ok': False})
        elif request.method == 'GET':
            if request.GET['action'] == 'busca_profesor':
                texto = request.GET['q']
                sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
                usuarios = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_docentes])
                usuarios_contain_texto = usuarios.filter(
                    Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)).values_list('id',
                                                                                                                'gauser__last_name',
                                                                                                                'gauser__first_name')
                keys = ('id', 'last_name', 'first_name')
                return HttpResponse(json.dumps([dict(zip(keys, row)) for row in usuarios_contain_texto]))
            elif request.GET['action'] == 'buscar_extraescolares':
                fecha_inicio = datetime.strptime(request.GET['id_fecha_inicio'], '%d-%m-%Y')
                fecha_fin = datetime.strptime(request.GET['id_fecha_fin'], '%d-%m-%Y')
                texto = request.GET['q']
                actividades = Actividad.objects.filter(Q(organizador__ronda__entidad=g_e.ronda.entidad),
                                                       Q(organizador__ronda=g_e.ronda),
                                                       Q(description__icontains=texto) | Q(
                                                           organizador__gauser__last_name__icontains=texto) | Q(
                                                           actividad_title__icontains=texto),
                                                       Q(fecha_inicio__gt=fecha_inicio),
                                                       Q(fecha_fin__lt=fecha_fin)).values_list('id', 'actividad_title')
                pass
                # fecha_inicio = datetime.strptime(request.GET['search_fecha_inicio'], '%d-%m-%Y')
                # fecha_fin = datetime.strptime(request.GET['search_fecha_fin'], '%d-%m-%Y')
                # texto = request.GET['q']
                # actividades = Actividad.objects.filter(Q(organizador__ronda__entidad=g_e.ronda.entidad),
                #                                        Q(organizador__ronda=g_e.ronda),
                #                                        Q(description__icontains=texto) | Q(
                #                                            organizador__gauser__last_name__icontains=texto) | Q(
                #                                            actividad_title__icontains=texto),
                #                                        Q(fecha_inicio__gt=fecha_inicio),
                #                                        Q(fecha_fin__lt=fecha_fin)).values_list('id', 'actividad_title')
                # keys = ('id', 'text')
                # return HttpResponse(json.dumps([dict(zip(keys, row)) for row in actividades]))
    else:
        if request.POST['action'] == 'upload_fichero_extraescolar':
            actividad = Actividad.objects.get(id=request.POST['actividad'], organizador__ronda__entidad=g_e.ronda.entidad)
            n_files = int(request.POST['n_files'])
            ficheros = []
            for i in range(n_files):
                fichero = request.FILES['fichero_xhr' + str(i)]
                code = pass_generator(20)
                file_actividad = File_actividad.objects.create(actividad=actividad, fichero=fichero,
                                                               content_type=fichero.content_type, code=code)
                # http: // www.imagemagick.org / discourse - server / viewtopic.php?t = 28069
                # If
                # test = 1, then
                # landscape.If
                # test = 0, then
                # portrait or square
                # CODE: SELECT
                # ALL
                # test = `convert
                # image - format
                # "%[fx:(w/h>1)?1:0]"
                # info:`
                # if [ $test -eq 1]; then
                # convert
                # image - resize
                # 800
                # x
                # result
                # else
                # convert
                # image - resize
                # x800
                # result
                # fi

                ficheros.append(
                    {'file_name': file_actividad.fich_name, 'url': file_actividad.fichero.url, 'code': code})
            return JsonResponse({'ficheros': ficheros})
