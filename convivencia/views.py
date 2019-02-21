# -*- coding: utf-8 -*-
import logging
from datetime import date
import os
from os.path import normpath, basename

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.core.files import File
from django.db.models import Q
from django.utils import timezone
from django.core.files.base import ContentFile
import base64

from autenticar.control_acceso import permiso_required
from gauss.funciones import usuarios_de_gauss, html_to_pdf
from gauss.rutas import RUTA_BASE, MEDIA_ANAGRAMAS, MEDIA_CONVIVENCIA
from convivencia.models import *
from entidades.models import Subentidad
from mensajes.models import Aviso, Mensaje, Mensaje_cola, Borrado
from mensajes.views import crear_aviso, encolar_mensaje

logger = logging.getLogger('django')


@permiso_required('acceso_gestionar_conductas')
def gestionar_conductas(request):
    g_e = request.session['gauser_extra']
    try:
        configuracion = ConfiguraConvivencia.objects.get(entidad=g_e.ronda.entidad)
    except:
        configuracion = ConfiguraConvivencia.objects.create(entidad=g_e.ronda.entidad)
    respuesta = {
        'formname': 'gestionar_conductas',
        'conductas': Conducta.objects.filter(entidad=g_e.ronda.entidad).order_by('id'),
        'sanciones': Sancion.objects.filter(entidad=g_e.ronda.entidad).order_by('id'),
        'con': configuracion,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "gestionar_conductas.html", respuesta)


def gestionar_conductas_ajax(request):
    if request.method == 'POST' and request.is_ajax():
        g_e = request.session['gauser_extra']
        action = request.POST['action']
        if action == 'add_sancion':
            sancion = Sancion.objects.create(sancion='Texto de la sanción', entidad=g_e.ronda.entidad, tipo='CNC')
            accordion = render_to_string('accordion_sancion.html', {'sancion': sancion})
            return HttpResponse(accordion)
        elif action == 'open_accordion_s':
            sancion = Sancion.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad)
            data = render_to_string("formulario_sancion.html",
                                    {'sancion': sancion, 'gauser_extra': g_e, 'cargos': cargos})
            return HttpResponse(data)
        elif action == 'del_sancion':
            try:
                sancion = Sancion.objects.get(id=request.POST['sancion'], entidad=g_e.ronda.entidad)
                sancion_id = sancion.id
                sancion.delete()
                return JsonResponse({'ok': True, 'sancion': sancion_id})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_texto_sancion':
            try:
                sancion = Sancion.objects.get(id=request.POST['sancion'], entidad=g_e.ronda.entidad)
                sancion.sancion = request.POST['texto']
                sancion.save()
                texto = sancion.sancion if len(sancion.sancion) < 40 else sancion.sancion[:40] + '...'
                return JsonResponse({'ok': True, 'sancion': sancion.id, 'texto': texto})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_tipo_sancion':
            try:
                sancion = Sancion.objects.get(id=request.POST['sancion'], entidad=g_e.ronda.entidad)
                sancion.tipo = request.POST['tipo']
                sancion.save()
                tipo = sancion.get_tipo_display()  # if len(sancion.get_tipo_display()) < 40 else sancion.get_tipo_display()[:40] + '...'
                return JsonResponse({'ok': True, 'sancion': sancion.id, 'tipo': tipo})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_texto_norma_s':
            try:
                sancion = Sancion.objects.get(id=request.POST['sancion'], entidad=g_e.ronda.entidad)
                sancion.norma = request.POST['texto']
                sancion.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_cargos_s':
            try:
                cargos = Cargo.objects.filter(id__in=request.POST.getlist('cargos[0][]'))
                sancion = Sancion.objects.get(id=request.POST['sancion'], entidad=g_e.ronda.entidad)
                sancion.cargos.clear()
                sancion.cargos.add(*cargos)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'conlleva_expulsion':
            try:
                sancion = Sancion.objects.get(id=request.POST['sancion'], entidad=g_e.ronda.entidad)
                sancion.expulsion = not sancion.expulsion
                sancion.save()
                return JsonResponse({'ok': True, 'texto': ['No', 'Sí'][sancion.expulsion], 'sancion': sancion.id})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_permiso_sancion':
            try:
                sancion = Sancion.objects.get(id=request.POST['sancion'], entidad=g_e.ronda.entidad)
                permiso = Permiso.objects.get(code_nombre=request.POST['permiso'])
                sancion.permiso = permiso
                sancion.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'add_conducta':
            conducta = Conducta.objects.create(conducta='Texto de la conducta', entidad=g_e.ronda.entidad, tipo='CNC')
            accordion = render_to_string('accordion_conducta.html', {'conducta': conducta})
            return HttpResponse(accordion)
        elif action == 'open_accordion_c':
            conducta = Conducta.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            sanciones = Sancion.objects.filter(entidad=g_e.ronda.entidad)
            cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad)
            data = render_to_string("formulario_conducta.html",
                                    {'sanciones': sanciones, 'gauser_extra': g_e, 'cargos': cargos,
                                     'conducta': conducta})
            return HttpResponse(data)
        elif action == 'del_conducta':
            try:
                conducta = Conducta.objects.get(id=request.POST['conducta'], entidad=g_e.ronda.entidad)
                conducta_id = conducta.id
                conducta.delete()
                return JsonResponse({'ok': True, 'conducta': conducta_id})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_texto_conducta':
            try:
                conducta = Conducta.objects.get(id=request.POST['conducta'], entidad=g_e.ronda.entidad)
                conducta.conducta = request.POST['texto']
                conducta.save()
                texto = conducta.conducta if len(conducta.conducta) < 40 else conducta.conducta[:40] + '...'
                return JsonResponse({'ok': True, 'conducta': conducta.id, 'texto': texto})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_tipo_conducta':
            try:
                conducta = Conducta.objects.get(id=request.POST['conducta'], entidad=g_e.ronda.entidad)
                conducta.tipo = request.POST['tipo']
                conducta.save()
                tipo = conducta.get_tipo_display()  # if len(conducta.get_tipo_display()) < 40 else conducta.get_tipo_display()[:40] + '...'
                return JsonResponse({'ok': True, 'conducta': conducta.id, 'tipo': tipo})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_prescribe_c':
            try:
                conducta = Conducta.objects.get(id=request.POST['conducta'], entidad=g_e.ronda.entidad)
                conducta.prescribe = int(request.POST['dias'])
                conducta.save()
                return JsonResponse({'ok': True, 'conducta': conducta.id, 'dias': conducta.prescribe})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_texto_norma_c':
            try:
                conducta = Conducta.objects.get(id=request.POST['conducta'], entidad=g_e.ronda.entidad)
                conducta.norma = request.POST['texto']
                conducta.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_cargos_c':
            try:
                cargos = Cargo.objects.filter(id__in=request.POST.getlist('cargos[0][]'))
                conducta = Conducta.objects.get(id=request.POST['conducta'], entidad=g_e.ronda.entidad)
                conducta.cargos.clear()
                conducta.cargos.add(*cargos)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        # elif action == 'change_sanciones_conductas':
        #     try:
        #         sanciones = Sancion.objects.filter(id__in=request.POST.getlist('sanciones[0][]'))
        #         conducta = Conducta.objects.get(id=request.POST['conducta'], entidad=g_e.ronda.entidad)
        #         conducta.sanciones.clear()
        #         conducta.sanciones.add(*sanciones)
        #         return JsonResponse({'ok': True})
        #     except:
        #         return JsonResponse({'ok': False})
        elif action == 'change_configuracion':
            try:
                configuracion = ConfiguraConvivencia.objects.get(entidad=g_e.ronda.entidad)
                setattr(configuracion, request.POST['campo'], request.POST['valor'])
                configuracion.save()
                return JsonResponse({'ok': True, 'valor': getattr(configuracion, request.POST['campo'])})
            except:
                return JsonResponse({'ok': False})


############################################################################################
############################################################################################
############################################################################################

# @permiso_required('acceso_guardias_horarios')
def sancionar_conductas(request):
    g_e = request.session['gauser_extra']
    inf_actual = None
    if request.method == 'POST' and not request.is_ajax():
        if request.POST['action'] == 'genera_pdf':
            informe = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad,
                                                      id=request.POST['inf_actual'])
            coherente, mensaje = informe.is_coherente
            if coherente:
                if informe.fichero:
                    os.remove(informe.fichero.path)
                listar_conductas, informes, expulsiones = False, None, None
                if 'listar_conductas' in request.POST:
                    listar_conductas = True
                    informes = Informe_sancionador.objects.filter(sancionado=informe.sancionado)
                    sanciones_expulsion = Sancion.objects.filter(entidad=g_e.ronda.entidad, expulsion=True)
                    expulsiones = informes.filter(sanciones__in=sanciones_expulsion)
                # Código para enviar correo
                asunto = render_to_string('informe_sancionador_mail_asunto.html', {'informe': informe})
                texto = render_to_string('informe_sancionador_mail.html', {'informe': informe})
                permisos = ['recibe_mensajes_aviso_informes_sancionadores']
                cargos = Cargo.objects.filter(permisos__code_nombre__in=permisos, entidad=g_e.ronda.entidad).distinct()
                try:
                    tutor = informe.sancionado.gauser_extra_estudios.tutor.id
                    q = Q(permisos__code_nombre__in=permisos) | Q(cargos__in=cargos) | Q(id=tutor)
                except:
                    q = Q(permisos__code_nombre__in=permisos) | Q(cargos__in=cargos)
                receptores = Gauser_extra.objects.filter(Q(activo=True), Q(ronda=g_e.ronda), q).values_list(
                    'gauser__id', flat=True).distinct()
                try:
                    # Comprobamos si un mensaje igual se ha mandado ya
                    Mensaje.objects.get(emisor=g_e, asunto=asunto, mensaje=texto)
                except:
                    mc = Mensaje_cola.objects.filter(mensaje__emisor=g_e, mensaje__asunto=asunto, enviado=False)
                    if mc.count() > 0:
                        mc[0].mensaje.delete()
                        mc.delete()
                    encolar_mensaje(emisor=g_e, receptores=receptores, asunto=asunto, html=texto,
                                   etiqueta='is%s' % informe.id)
                # Fin de código para enviar correo
                texto_html = render_to_string('is2pdf.html', {'informe': informe, 'MEDIA_ANAGRAMAS': MEDIA_ANAGRAMAS,
                                                              'listar_conductas': listar_conductas,
                                                              'expulsiones': expulsiones, 'informes': informes})
                ruta = MEDIA_CONVIVENCIA + '%s/' % g_e.ronda.entidad.code
                fich = html_to_pdf(request, texto_html, fichero='IS', media=ruta, title=u'Informe sancionador')
                informe.texto_html = texto_html
                nombre = 'convivencia/%s/%s_%s.pdf' % (
                    g_e.ronda.entidad.code, slugify(informe.sancionado.gauser.get_full_name()),
                    timezone.localtime(informe.created).strftime('%d-%m-%Y_%H%M'))
                informe.fichero.save(nombre, File(fich))
                fich.close()
                informe.save()
                filename = informe.fichero.name.split('/')[-1]
                response = HttpResponse(informe.fichero, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename=%s' % filename
                return response
            else:
                inf_actual = informe
                crear_aviso(request, False, '<ul>%s</ul>' % mensaje)
        if request.POST['action'] == 'descargar_informe':
            informe = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad,
                                                      id=request.POST['inf_descargar'])
            filename = informe.fichero.name.split('/')[-1]
            response = HttpResponse(informe.fichero, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=%s' % filename
            return response

    informes = Informe_sancionador.objects.filter(Q(sancionador=g_e), ~Q(fichero=''))
    informes_como_tutor = Informe_sancionador.objects.filter(Q(sancionado__gauser_extra_estudios__tutor=g_e),
                                                             ~Q(fichero='')).exclude(id__in=informes)
    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'Generar',
              'title': 'Generar informe sancionador', 'permiso': 'genera_informe_sancionador'},),
        'formname': 'gestionar_conductas',
        'conductas': Conducta.objects.filter(entidad=g_e.ronda.entidad),
        'sanciones': Sancion.objects.filter(entidad=g_e.ronda.entidad),
        'informes': informes,
        'informes_como_tutor': informes_como_tutor,
        'inf_actual': inf_actual,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "sancionar_conductas.html", respuesta)


def sancionar_conductas_ajax(request):
    if request.method == 'POST' and request.is_ajax():
        g_e = request.session['gauser_extra']
        sub_alumnos = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='alumnos')
        action = request.POST['action']
        if action == 'buscar_usuarios':
            texto = request.POST['q']
            usuarios = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_alumnos])
            filtrados = usuarios.filter(Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto))
            options = []
            for u in filtrados:
                options.append(
                    {'id': u.id, 'text': u.gauser.get_full_name() + ' (' + u.gauser_extra_estudios.grupo.nombre + ')'})
            return JsonResponse(options, safe=False)
        elif action == 'seleccionar_usuario':
            try:
                sancionado = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, ronda=g_e.ronda,
                                                      id=request.POST['user'])
                Informe_sancionador.objects.filter(sancionado=sancionado, fichero='').delete()
                sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
                docentes = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_docentes])
                inf_actual = Informe_sancionador.objects.create(sancionado=sancionado, sancionador=g_e,
                                                                fecha_incidente=date.today())
                html = render_to_string('sancionar_conductas_datos_sancionado.html',
                                        {'inf_actual': inf_actual, 'docentes': docentes, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'cargar_informe':
            try:
                sub_docentes = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='docente')
                docentes = usuarios_de_gauss(g_e.ronda.entidad, subentidades=[sub_docentes])
                inf_actual = Informe_sancionador.objects.get(id=request.POST['informe'], sancionado__ronda=g_e.ronda)
                html = render_to_string('sancionar_conductas_datos_sancionado.html',
                                        {'inf_actual': inf_actual, 'docentes': docentes, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif action == 'check_conductas':
            try:
                informe = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad,
                                                          id=request.POST['inf_actual'])
                conductas_borrar = informe.conductas.filter(tipo=request.POST['tipo'])
                informe.conductas.remove(*conductas_borrar)
                conductas = Conducta.objects.filter(entidad=g_e.ronda.entidad,
                                                    id__in=request.POST.getlist('conductas[]'))
                informe.conductas.add(*conductas)
                sanciones_id = conductas.values_list('tipo', flat=True)
                return JsonResponse({'ok': True, 'sanciones': list(set(sanciones_id))})
            except:
                return JsonResponse({'ok': False})
        elif action == 'check_sanciones':
            try:
                informe = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad,
                                                          id=request.POST['inf_actual'])
                sanciones_borrar = informe.sanciones.filter(tipo=request.POST['tipo'])
                informe.sanciones.remove(*sanciones_borrar)
                sanciones = Sancion.objects.filter(entidad=g_e.ronda.entidad,
                                                   id__in=request.POST.getlist('sanciones[]'))
                informe.sanciones.add(*sanciones)
                expulsion = informe.sanciones.filter(expulsion=True).count() > 0
                return JsonResponse({'ok': True, 'expulsion': expulsion})
            except:
                return JsonResponse({'ok': False})
        elif action == 'describe_conducta':
            try:
                informe = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad,
                                                          id=request.POST['inf_actual'])
                informe.texto_motivo = request.POST['texto']
                informe.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'describe_sancion':
            try:
                informe = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad,
                                                          id=request.POST['inf_actual'])
                informe.texto_sancion = request.POST['texto']
                informe.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_tutor':
            try:
                inf_actual = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad,
                                                             id=request.POST['inf_actual'])
                tutor = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['tutor'])
                sancionado = inf_actual.sancionado
                sancionado.gauser_extra_estudios.tutor = tutor
                sancionado.gauser_extra_estudios.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_sancionador':
            try:
                inf_actual = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad,
                                                             id=request.POST['inf_actual'])
                sancionador = Gauser_extra.objects.get(entidad=g_e.ronda.entidad, id=request.POST['sancionador'])
                inf_actual.sanciones.clear()
                inf_actual.sancionador = sancionador
                inf_actual.save()
                inf_actual.fechaexpulsion_set.all().delete()
                sanciones_cnc = Sancion.objects.filter(tipo='CNC', entidad=g_e.ronda.entidad)
                sanciones_gpc = Sancion.objects.filter(tipo='GPC', entidad=g_e.ronda.entidad)
                lista_sanciones_cnc = render_to_string("lista_de_sanciones.html",
                                                       {'sanciones': sanciones_cnc, 'sancionador': sancionador,
                                                        'inf_actual': inf_actual})
                lista_sanciones_gpc = render_to_string("lista_de_sanciones.html",
                                                       {'sanciones': sanciones_gpc, 'sancionador': sancionador,
                                                        'inf_actual': inf_actual})
                return JsonResponse({'ok': True, 'cnc': lista_sanciones_cnc, 'gpc': lista_sanciones_gpc})
            except:
                return JsonResponse({'ok': False})
        elif action == 'fecha_informe':
            try:
                informe = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad,
                                                          id=request.POST['informe'])
                informe.fecha_incidente = datetime.strptime(request.POST['valor'], '%d/%m/%Y')
                informe.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'fechas_expulsion':
            try:
                informe = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad,
                                                          id=request.POST['informe'])
                informe.fechaexpulsion_set.all().delete()
                for fecha in request.POST.getlist('fechas[]'):
                    FechaExpulsion.objects.create(informe=informe, fecha=datetime.strptime(fecha, '%d/%m/%Y'))
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        # elif action == 'fecha_fin':
        #     try:
        #         informe = Informe_sancionador.objects.get(sancionado__entidad=g_e.ronda.entidad, id=request.POST['informe'])
        #         informe.fecha_fin = datetime.strptime(request.POST['valor'], '%d/%m/%Y')
        #         informe.save()
        #         return JsonResponse({'ok': True})
        #     except:
        #         return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_informe':
            informe = Informe_sancionador.objects.get(id=request.POST['informe'], sancionado__entidad=g_e.ronda.entidad)
            if informe.sancionador == g_e or g_e.has_permiso('borra_informes_sancionadores'):
                informe.fichero.delete()
                informe.delete()
                return JsonResponse({'ok': True})
            else:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion_s':
            informe = Informe_sancionador.objects.get(id=request.POST['informe'], sancionado__entidad=g_e.ronda.entidad)
            sanciones = Sancion.objects.filter(tipo=request.POST['tipo'], entidad=g_e.ronda.entidad)
            sancionador = Gauser_extra.objects.get(id=request.POST['sancionador'], entidad=g_e.ronda.entidad)
            data = render_to_string("lista_de_sanciones.html",
                                    {'sanciones': sanciones, 'sancionador': sancionador, 'inf_actual': informe})
            return HttpResponse(data)
        elif action == 'open_accordion_c':
            informe = Informe_sancionador.objects.get(id=request.POST['informe'], sancionado__entidad=g_e.ronda.entidad)
            conductas = Conducta.objects.filter(tipo=request.POST['tipo'], entidad=g_e.ronda.entidad)
            data = render_to_string("lista_de_conductas.html", {'conductas': conductas, 'inf_actual': informe})
            return HttpResponse(data)


@permiso_required('acceso_guardias_horarios')
def expediente_sancionador(request):
    pass
