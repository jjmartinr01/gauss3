# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import pdfkit
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils.text import slugify
from entidades.models import Gauser_extra, Subentidad, Cargo
from gauss.funciones import usuarios_de_gauss, get_dce
from gauss.rutas import *
from absentismo.models import Actuacion, ExpedienteAbsentismo
from django.http import HttpResponse
from datetime import datetime, date
from django.template.loader import render_to_string
from mensajes.views import crear_aviso
from autenticar.control_acceso import permiso_required
from mensajes.models import Aviso

logger = logging.getLogger('django')


# @permiso_required('acceso_absentismo')
def gestionar_absentismo(request):
    g_e = request.session['gauser_extra']
    expedientes = ExpedienteAbsentismo.objects.filter(expedientado__ronda=g_e.ronda)[:10]

    if request.method == 'POST':
        if request.POST['action'] == 'pdf_absentismo' and g_e.has_permiso('crea_informe_absentismo'):
            doc_abs = 'Configuración de informes de absentismo'
            dce = get_dce(g_e.ronda.entidad, doc_abs)
            expediente = ExpedienteAbsentismo.objects.get(expedientado__ronda=g_e.ronda,
                                                          id=request.POST['expediente_id'])
            c = render_to_string('absentismo2pdf.html', {'expediente': expediente, 'MEDIA_ANAGRAMAS': MEDIA_ANAGRAMAS})
            fich = pdfkit.from_string(c, False, dce.get_opciones)
            logger.info('%s, pdf_absentismo %s' % (g_e, expediente.id))
            response = HttpResponse(fich, content_type='application/pdf')
            alumno = slugify(expediente.expedientado.gauser.get_full_name())
            response['Content-Disposition'] = 'attachment; filename=expediente_absentismo_%s.pdf' % alumno
            return response

    return render(request, "absentismo.html",
                  {
                      'formname': 'absentismo',
                      'expedientes': expedientes,
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def ajax_absentismo(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        logger.info('%s, %s' % (g_e, request.POST['action']))
        if request.POST['action'] == 'buscar_actuado':
            texto = request.POST['q']
            sub_alumnos = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='alumnos')
            usuarios = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_alumnos])
            filtrados = usuarios.filter(Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto))
            options = []
            for u in filtrados:
                options.append({'id': u.id, 'text': u.gauser.get_full_name() + ' (' + u.gauser_extra_estudios.grupo.nombre + ')'})
            return JsonResponse(options, safe=False)
        elif request.POST['action'] == 'get_expedientado':
            expedientado = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['expedientado'])
            expediente, creado = ExpedienteAbsentismo.objects.get_or_create(expedientado=expedientado)
            if creado:
                exs = ExpedienteAbsentismo.objects.filter(director__iregex=r'[a-z]+', presidente__iregex=r'[a-z]+',
                                                          expedientado__ronda=g_e.ronda)
                if exs.count() > 0:
                    expediente.director, expediente.presidente = exs[0].director, exs[0].presidente
                else:
                    expediente.director, expediente.presidente = ' ', ' '
            expediente.save()
            n_actuaciones = expediente.actuacion_set.all().count()
            if n_actuaciones == 0:
                return JsonResponse(
                    {'ok': False, 'user': expedientado.gauser.get_full_name(), 'user_id': expedientado.id})
            else:
                data = render_to_string('absentismo_accordion.html', {'expediente': expediente})
                return JsonResponse({'html': data, 'ok': True})
        elif request.POST['action'] == 'create_actuacion' and g_e.has_permiso('crea_actuacion_absentismo'):
            expediente = ExpedienteAbsentismo.objects.get(expedientado__ronda=g_e.ronda,
                                                          expedientado__id=request.POST['expedientado'])
            Actuacion.objects.create(expediente=expediente, contacto=' ', fecha=date.today(), faltas=12,
                                     observaciones='Esta actuación ha sido creada por defecto por GAUSS. El número de faltas, la persona de contacto y las observaciones las tienes que modicar para adecuarlas a tu situación.',
                                     realizada_por=g_e)
            data = render_to_string('absentismo_accordion.html', {'expediente': expediente})
            return JsonResponse({'html': data, 'ok': True})
        elif request.POST['action'] == 'open_accordion':
            # sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
            # docentes = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_docentes])
            cargo = Cargo.objects.get(entidad=g_e.ronda.entidad, clave_cargo='g_docente')
            docentes = Gauser_extra.objects.filter(ronda=g_e.ronda, cargos__in=[cargo])

            expediente = ExpedienteAbsentismo.objects.get(expedientado__ronda=g_e.ronda, id=request.POST['expediente'])
            data = render_to_string('absentismo_accordion_content.html',
                                    {'expediente': expediente, 'g_e': g_e, 'docentes': docentes})
            return HttpResponse(data)
        elif request.POST['action'] == 'add_actuacion_absentismo' and g_e.has_permiso('crea_actuacion_absentismo'):
            expediente = ExpedienteAbsentismo.objects.get(expedientado__ronda=g_e.ronda, id=request.POST['expediente'])
            actuacion = Actuacion.objects.create(expediente=expediente, contacto=' ', fecha=date.today(), faltas=80,
                                                 observaciones='Estas son las observaciones de la actuación',
                                                 realizada_por=g_e)
            n_actuaciones = expediente.actuacion_set.all().count()
            html = render_to_string('absentismo_accordion_content_actuacion.html', {'actuacion': actuacion, 'g_e': g_e})
            return JsonResponse({'html': html, 'n_actuaciones': n_actuaciones})
        elif request.POST['action'] == 'delete_actuacion':
            ok = False
            try:
                actuacion = Actuacion.objects.get(expediente__expedientado__ronda=g_e.ronda,
                                                  id=request.POST['actuacion'])
                expediente = actuacion.expediente
                if g_e.has_permiso('borra_actuacion_absentismo') or actuacion.realizada_por == g_e:
                    actuacion.delete()
                    ok = True
                n_actuaciones = expediente.actuacion_set.all().count()
                expediente_id = expediente.id
                if n_actuaciones == 0:
                    expediente.delete()
                return JsonResponse({'expediente': expediente_id, 'n_actuaciones': n_actuaciones, 'ok': ok})
            except:
                return JsonResponse({'ok': ok})
        elif request.POST['action'] == 'update_tutor':
            try:
                expediente = ExpedienteAbsentismo.objects.get(expedientado__ronda=g_e.ronda,
                                                              id=request.POST['expediente'])
                tutor = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['tutor'])
                expediente.expedientado.gauser_extra_estudios.tutor = tutor
                expediente.expedientado.gauser_extra_estudios.save()
                return HttpResponse(True)
            except:
                return HttpResponse(False)
        elif request.POST['action'] == 'update_configura':
            ok = False
            try:
                expediente = ExpedienteAbsentismo.objects.get(expedientado__ronda=g_e.ronda,
                                                              id=request.POST['expediente'])
                setattr(expediente, request.POST['campo'], request.POST['valor'])
                if g_e.has_permiso('configura_expediente_absentismo'):
                    expediente.save()
                    ok = True
                return HttpResponse(ok)
            except:
                return HttpResponse(False)
        elif request.POST['action'] == 'update_configura_matricula':
            ok = False
            try:
                expediente = ExpedienteAbsentismo.objects.get(expedientado__ronda=g_e.ronda,
                                                              id=request.POST['expediente'])
                expediente.matricula = not expediente.matricula
                if g_e.has_permiso('configura_expediente_absentismo'):
                    expediente.save()
                    ok = True
                return JsonResponse(
                    {'ok': ok, 'texto': ['No', 'Sí'][expediente.matricula], 'expediente': expediente.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_observaciones':
            ok = False
            try:
                actuacion = Actuacion.objects.get(expediente__expedientado__ronda=g_e.ronda,
                                                  id=request.POST['actuacion'])
                actuacion.observaciones = request.POST['texto']
                if g_e.has_permiso('edita_actuacion_absentismo') or actuacion.realizada_por == g_e:
                    actuacion.save()
                    ok = True
                return HttpResponse(ok)
            except:
                return HttpResponse(False)
        elif request.POST['action'] == 'update_fecha':
            ok = False
            try:
                actuacion = Actuacion.objects.get(expediente__expedientado__ronda=g_e.ronda,
                                                  id=request.POST['actuacion'])
                actuacion.fecha = datetime.strptime(request.POST['fecha'], '%d-%m-%Y')
                if g_e.has_permiso('edita_actuacion_absentismo') or actuacion.realizada_por == g_e:
                    actuacion.save()
                    ok = True
                return HttpResponse(ok)
            except:
                return HttpResponse(False)
        elif request.POST['action'] == 'update_faltas':
            ok = True
            try:
                actuacion = Actuacion.objects.get(expediente__expedientado__ronda=g_e.ronda,
                                                  id=request.POST['actuacion'])
                actuacion.faltas = int(request.POST['faltas'])
                if g_e.has_permiso('edita_actuacion_absentismo') or actuacion.realizada_por == g_e:
                    actuacion.save()
                    ok = True
                return HttpResponse(ok)
            except:
                return HttpResponse(False)
        elif request.POST['action'] == 'update_contacto':
            ok = False
            try:
                actuacion = Actuacion.objects.get(expediente__expedientado__ronda=g_e.ronda,
                                                  id=request.POST['actuacion'])
                actuacion.contacto = request.POST['contacto']
                if g_e.has_permiso('edita_actuacion_absentismo') or actuacion.realizada_por == g_e:
                    actuacion.save()
                    ok = True
                    error = ''
                else:
                    error = 'Esta actuación no es tuya y no tienes permiso para modificar el contacto'
                return JsonResponse({'ok': ok, 'error': error})
            except Exception as e:
                return JsonResponse({'ok': False, 'error': repr(e)})
        else:
            logger.info('%s, acción no permitida' % (g_e))
            return HttpResponse(False)

    else:
        return HttpResponse(status=400)
