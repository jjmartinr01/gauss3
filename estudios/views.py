# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import xlrd
from datetime import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.db.models import Q

from autenticar.control_acceso import permiso_required
from entidades.models import Subentidad, Gauser_extra, Ronda, CargaMasiva, Dependencia
from entidades.tasks import carga_masiva_from_excel
from estudios.models import Curso, Materia, ETAPAS, Grupo, Matricula
from gauss.funciones import usuarios_de_gauss, usuarios_ronda, human_readable_list, html_to_pdf
from gauss.rutas import MEDIA_PENDIENTES
from programaciones.models import Materia_programaciones
from mensajes.models import Aviso


# Create your views here.


@permiso_required('acceso_configura_cursos')
def configura_cursos(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'add_curso':
            try:
                curso = Curso.objects.create(nombre='Curso nuevo', ronda=g_e.ronda, etapa='', tipo='',
                                             nombre_especifico='', familia='')
                accordion = render_to_string('configura_cursos_formulario.html', {'curso': curso})
                return JsonResponse({'ok': True, 'accordion': accordion})
            except:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion':
            try:
                curso = Curso.objects.get(id=request.POST['id'], ronda=g_e.ronda)
                html = render_to_string('configura_cursos_formulario_content.html', {'curso': curso, 'etapas': ETAPAS})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'delete_curso':
            try:
                curso = Curso.objects.get(id=request.POST['curso'], ronda=g_e.ronda)
                curso.delete()
                return JsonResponse({'ok': True, 'mensaje': 'Curso borrado'})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_campo':
            # clases = {'Materia': Materia, 'Materia_programaciones': Materia_programaciones, 'Curso': Curso}
            # clase = clases[request.POST['object']]
            # objeto = clase.objects.get(id=request.POST['id'])
            # if objeto.entidad == g_e.ronda.entidad:
            #     setattr(objeto, request.POST['campo'], request.POST['value'])
            #     objeto.save()
            #     return JsonResponse({'ok': True, 'valor': request.POST['value']})
            try:
                clases = {'Materia': Materia, 'Materia_programaciones': Materia_programaciones, 'Curso': Curso}
                clase = clases[request.POST['object']]
                objeto = clase.objects.get(id=request.POST['id'])
                setattr(objeto, request.POST['campo'], request.POST['value'])
                objeto.save()
                return JsonResponse({'ok': True, 'valor': request.POST['value']})
                # La anterior asignación es peligrosa porque no se comprueba si la materia o curso es propiedad de la
                # entidad. Si el objeto fuera Curso se podría hacer lo siguiente:
                # if objeto.entidad == g_e.ronda.entidad:
                #     setattr(objeto, request.POST['campo'], request.POST['value'])
                #     objeto.save()
                #     return JsonResponse({'ok': True, 'valor': request.POST['value']})
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_materia_curso':
            try:
                curso = Curso.objects.get(id=request.POST['id_curso'], ronda=g_e.ronda)
                materia = Materia.objects.create(curso=curso, nombre="Materia creada nueva", clave_ex="Sin clave",
                                                 observaciones='Creada manualmente')
                Materia_programaciones.objects.create(materia=materia)
                html = render_to_string('configura_cursos_formulario_materia.html', {'materia': materia})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'borrar_materia':
            try:
                materia = Materia.objects.get(id=request.POST['id'])
                if materia.curso.ronda.entidad == g_e.ronda.entidad:
                    materia.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})
    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir curso', 'title': 'Crear un nuevo curso',
              'permiso': 'crea_cursos'},
             ),
        'formname': 'estudios_configura_cursos',
        'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today()),
        'cursos': Curso.objects.filter(ronda=g_e.ronda),
        'etapas': ETAPAS,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "configura_cursos.html", respuesta)


@login_required()
def departamentos_didacticos(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'add_curso':
            curso = Curso.objects.create(nombre='Curso nuevo', entidad=g_e.ronda.entidad, etapa='', tipo='',
                                         nombre_especifico='', familia='')
            accordion = render_to_string('configura_cursos_formulario.html', {'curso': curso})
            return HttpResponse(accordion)
        elif action == 'delete_curso':
            curso = Curso.objects.get(id=request.POST['curso'], entidad=g_e.ronda.entidad)
            curso.delete()
            return HttpResponse('Curso borrado')
        elif action == 'change_campo':
            curso = Curso.objects.get(id=request.POST['curso'], entidad=g_e.ronda.entidad)
            setattr(curso, request.POST['campo'], request.POST['value'])
            curso.save()
            return HttpResponse(request.POST['value'])

    respuesta = {
        'formname': 'estudios_departamentos_didacticos',
        'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today()),
        'cursos': Curso.objects.filter(entidad=g_e.ronda.entidad),
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "configura_cursos.html", respuesta)


@permiso_required('acceso_configura_grupos')
def configura_grupos(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'add_grupo':
            grupo = Grupo.objects.create(nombre='Grupo nuevo', ronda=g_e.ronda)
            accordion = render_to_string('configura_grupos_formulario.html', {'grupo': grupo})
            return HttpResponse(accordion)
        elif action == 'delete_grupo':
            grupo = Grupo.objects.get(id=request.POST['grupo'], ronda=g_e.ronda)
            grupo.delete()
            return HttpResponse('Grupo borrado')
        elif action == 'update_cursos':
            grupo = Grupo.objects.get(id=request.POST['grupo'], ronda=g_e.ronda)
            cursos = Curso.objects.filter(ronda=g_e.ronda, id__in=request.POST.getlist('cursos[]'))
            grupo.cursos.clear()
            grupo.cursos.add(*cursos)
            return JsonResponse({'ok': True})
        elif action == 'change_campo_texto':
            grupo = Grupo.objects.get(id=request.POST['grupo'], ronda=g_e.ronda)
            setattr(grupo, request.POST['campo'], request.POST['value'])
            grupo.save()
            return JsonResponse({'texto': request.POST['value'], 'ok': True})
        elif action == 'change_campo':
            grupo = Grupo.objects.get(id=request.POST['grupo'], ronda=g_e.ronda)
            if request.POST['campo'] == 'tutor':
                try:
                    grupo.tutor = Gauser_extra.objects.get(id=request.POST['value'], ronda=g_e.ronda)
                except:
                    grupo.tutor = None
            elif request.POST['campo'] == 'cotutor':
                try:
                    grupo.cotutor = Gauser_extra.objects.get(id=request.POST['value'], ronda=g_e.ronda)
                except:
                    grupo.cotutor = None
            elif request.POST['campo'] == 'ronda':
                grupo.ronda = Ronda.objects.get(id=request.POST['value'], entidad=g_e.ronda.entidad)
            elif request.POST['campo'] == 'curso':
                grupo.curso = Curso.objects.get(id=request.POST['value'], entidad=g_e.ronda.entidad)
            elif request.POST['campo'] == 'aula':
                grupo.aula = Dependencia.objects.get(id=request.POST['value'], entidad=g_e.ronda.entidad)
            grupo.save()
            return HttpResponse(request.POST['value'])
        elif action == 'open_accordion':
            grupo = Grupo.objects.get(id=request.POST['id'], ronda=g_e.ronda)
            rondas = Ronda.objects.filter(entidad=g_e.ronda.entidad)
            cursos = Curso.objects.filter(ronda=g_e.ronda)
            sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
            docentes = usuarios_ronda(g_e.ronda, subentidades=[sub_docentes])
            ds = Dependencia.objects.filter(entidad=g_e.ronda.entidad, es_aula=True)
            html = render_to_string('configura_grupos_formulario_content.html',
                                    {'grupo': grupo, 'dependencias': ds, 'cursos': cursos, 'docentes': docentes})
            return JsonResponse({'html': html, 'ok': True})

    respuesta = {
        'formname': 'configura_grupos',
        'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today()),
        'grupos': Grupo.objects.filter(ronda=g_e.ronda),
        'g_e': g_e,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "configura_grupos.html", respuesta)


@permiso_required('acceso_configura_pendientes')
def configura_materias_pendientes(request):
    g_e = request.session['gauser_extra']
    if request.method == 'GET' and request.is_ajax():
        action = request.GET['action']
        if action == 'select_profesor':
            items = []
            # items = [{'id': u.id, 'text': u.gauser.last_name} for u in usuarios_ronda(g_e.ronda, subentidades=False)]
            texto = request.GET['search']
            q = (Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)) & Q(
                subentidades__clave_ex='docente')
            for u in usuarios_ronda(g_e.ronda, subentidades=False).filter(q):
                items.append({'id': u.id, 'text': '%s, %s' % (u.gauser.last_name, u.gauser.first_name)})
            return JsonResponse({'ok': True, 'items': items})
    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'open_accordion':
            curso = Curso.objects.get(id=request.POST['id'], ronda=g_e.ronda)
            matriculas = Matricula.objects.filter(ge__ronda=g_e.ronda, estado='PE',
                                                  ge__gauser_extra_estudios__grupo__cursos=curso)
            html = render_to_string('configura_materias_pendientes_curso_content.html', {'matriculas': matriculas})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'select_profesor':
            try:
                matricula = Matricula.objects.get(ge__ronda=g_e.ronda, id=request.POST['matricula'])
                evaluador = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['profesor'],
                                                     subentidades__clave_ex='docente')
                matricula.evaluador = evaluador
                matricula.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
    elif request.method == 'POST':
        if request.POST['action'] == 'upload_file_matriculas':
            try:
                n_files = int(request.POST['n_files'])
                for i in range(n_files):
                    fichero = request.FILES['fichero_xhr' + str(i)]
                    if fichero.content_type == 'application/vnd.ms-excel':
                        CargaMasiva.objects.create(ronda=g_e.ronda, fichero=fichero, tipo='PENDIENTES')
                carga_masiva_from_excel.delay()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
    try:
        carga = CargaMasiva.objects.filter(ronda=g_e.ronda, tipo='PENDIENTES', cargado=True).latest('id')
    except:
        carga = CargaMasiva.objects.none()
    respuesta = {
        'formname': 'configura_materias_pendientes',
        'cursos': Curso.objects.filter(ronda=g_e.ronda),
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
        'carga': carga}
    return render(request, "configura_materias_pendientes.html", respuesta)


# @permiso_required('acceso_evaluar_materias')
def evaluar_materias(request):
    g_e = request.session['gauser_extra']
    if g_e.has_permiso('evalua_cualquier_materia'):
        matriculas = Matricula.objects.filter(ge__ronda=g_e.ronda, estado='PE')
    else:
        if g_e.gauser_extra_programaciones.jefe:
            matriculas = Matricula.objects.filter(ge__ronda=g_e.ronda, estado='PE',
                                                  evaluador__gauser_extra_programaciones__departamento=g_e.gauser_extra_programaciones.departamento)
        else:
            matriculas = Matricula.objects.filter(ge__ronda=g_e.ronda, estado='PE', evaluador=g_e)
    materias_evalua_id = matriculas.values_list('materia__id')
    materias_evalua = Materia.objects.filter(id__in=materias_evalua_id)

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'open_accordion':
            curso = Curso.objects.get(id=request.POST['id'], ronda=g_e.ronda)
            if g_e.has_permiso('evalua_cualquier_materia'):
                matriculas = Matricula.objects.filter(ge__ronda=g_e.ronda, estado='PE',
                                                      ge__gauser_extra_estudios__grupo__cursos=curso)
            else:
                if g_e.gauser_extra_programaciones.jefe:
                    matriculas = Matricula.objects.filter(ge__ronda=g_e.ronda, estado='PE',
                                                          ge__gauser_extra_estudios__grupo__cursos=curso,
                                                          evaluador__gauser_extra_programaciones__departamento=g_e.gauser_extra_programaciones.departamento)
                else:
                    matriculas = Matricula.objects.filter(ge__ronda=g_e.ronda, estado='PE',
                                                          ge__gauser_extra_estudios__grupo__cursos=curso,
                                                          evaluador=g_e)
            html = render_to_string('evaluar_materias_curso_content.html', {'matriculas': matriculas, 'g_e': g_e})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'change_nota':
            try:
                matricula = Matricula.objects.get(ge__ronda=g_e.ronda, id=request.POST['matricula'])
                setattr(matricula, request.POST['nota'], int(request.POST['valor']))
                matricula.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
    elif request.method == 'POST' and not request.is_ajax():
        if request.POST['action'] == 'cartas_examen':
            fichero = 'carta%s_%s' % (g_e.ronda.entidad.code, g_e.id)
            fecha = datetime.strptime(request.POST['fecha_examen'], '%Y-%m-%d')
            mats = Materia.objects.filter(id__in=request.POST.getlist('materias_seleccionadas'), curso__ronda=g_e.ronda)
            ms = Matricula.objects.filter(materia__in=mats, ge__ronda=g_e.ronda, estado='PE')
            mats_text_array = ['%s (%s)' % (m[0], m[1]) for m in mats.values_list('nombre', 'curso__nombre')]
            materias = human_readable_list(mats_text_array)
            alumnos_id = ms.filter(ge__ronda=g_e.ronda).values_list('ge__id')
            alumnos = Gauser_extra.objects.filter(id__in=alumnos_id).distinct()
            texto_html = render_to_string('carta_pendientes2pdf.html', {'materias': materias, 'alumnos': alumnos,
                                                                        'fecha': fecha, 'evaluador': g_e, 'ms': ms,
                                                                        'hora': request.POST['hora_examen'],
                                                                        'lugar': request.POST['lugar_examen'],
                                                                        'obs': request.POST['observaciones']})
            ruta = MEDIA_PENDIENTES + '%s/' % g_e.ronda.entidad.code
            fich = html_to_pdf(request, texto_html, fichero=fichero, media=ruta, title='Carta tutores legales')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response
    respuesta = {
        'formname': 'evaluar_materias',
        'cursos': Curso.objects.filter(ronda=g_e.ronda),
        'materias_evalua': materias_evalua,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)}
    return render(request, "evaluar_materias.html", respuesta)

# @permiso_required('acceso_define_materias')
# def define_materia(request):
#     g_e = request.session['gauser_extra']
#     if request.method == 'POST' and request.is_ajax():
#         action = request.POST['action']
#         if action == 'add_materia':
#             try:
#                 cursos = Curso.objects.filter(entidad=g_e.ronda.entidad)
#                 materia = Materia.objects.create(nombre='Materia nueva', abreviatura='', horas=3, duracion=30,
#                                                  curso=cursos[0])
#                 accordion = render_to_string('formulario_materia.html', {'materia': materia, 'cursos': cursos})
#                 return HttpResponse(accordion)
#             except:
#                 return HttpResponse('Es necesario tener al menos un curso creado')
#         elif action == 'delete_materia':
#             materia = Materia.objects.get(id=request.POST['materia'], curso__entidad=g_e.ronda.entidad)
#             materia.delete()
#             return HttpResponse('Materia borrada')
#         elif action == 'change_curso':
#             materia = Materia.objects.get(id=request.POST['materia'], curso__entidad=g_e.ronda.entidad)
#             materia.curso = Curso.objects.get(id=request.POST['curso'], entidad=g_e.ronda.entidad)
#             materia.save()
#             return HttpResponse(materia.curso)
#         elif action == 'change_campo':
#             materia = Materia.objects.get(id=request.POST['materia'], curso__entidad=g_e.ronda.entidad)
#             setattr(materia, request.POST['campo'], request.POST['value'])
#             materia.save()
#             return HttpResponse(request.POST['value'])
#
#     respuesta = {
#         'formname': 'define_materia',
#         'materias': Materia.objects.filter(curso__entidad=g_e.ronda.entidad),
#         'cursos': Curso.objects.filter(entidad=g_e.ronda.entidad),
#         'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
#     }
#     return render(request, "define_materia.html", respuesta)
