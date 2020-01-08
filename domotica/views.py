# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from datetime import datetime, timedelta
from django.utils import timezone

import requests
from django.db.models import Q, Sum
from django.core.files.base import ContentFile, File
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.utils import timezone

from entidades.models import Gauser_extra
from gauss.funciones import html_to_pdf, pass_generator, usuarios_ronda
from gauss.rutas import RUTA_MEDIA, MEDIA_VUT, RUTA_BASE
from autenticar.control_acceso import permiso_required
from mensajes.models import Aviso
from autenticar.models import Permiso, Gauser
from mensajes.views import encolar_mensaje, crear_aviso
from domotica.models import Grupo, Dispositivo, Secuencia, DispositivoSecuencia, GauserPermitidoGrupo, \
    GauserPermitidoDispositivo, EnlaceDomotica
from domotica.mqtt import client


# Create your views here.
from vut.models import Vivienda, DomoticaVUT
from vut.views import viviendas_autorizado


@permiso_required('acceso_grupos_domotica')
def grupos_domotica(request):
    g_e = request.session['gauser_extra']
    grupos = Grupo.objects.filter(propietario=g_e.gauser)
    return render(request, "grupos_domotica.html",
                  {
                      'formname': 'grupos_domotica',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nuevo grupo',
                            'permiso': 'crea_grupos_domotica', 'title': 'Crear un nuevo grupo para domótica'},
                           ),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'grupos': grupos,
                  })


@login_required()
def ajax_grupos_domotica(request):
    g_e = request.session["gauser_extra"]
    if request.is_ajax():
        if request.method == 'POST':
            if request.POST['action'] == 'add_grupo' and g_e.has_permiso('crea_grupos_domotica'):
                try:
                    grupo = Grupo.objects.create(nombre='Nuevo grupo/ubicación', propietario=g_e.gauser)
                    html = render_to_string('grupos_domotica_accordion.html', {'grupos': [grupo]})
                    return JsonResponse({'html': html, 'ok': True})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'open_accordion':
                try:
                    grupos_id = GauserPermitidoGrupo.objects.filter(gauser=g_e.gauser).values_list('grupo', flat=True)
                    grupos = Grupo.objects.filter(id__in=grupos_id)
                    grupo = grupos.get(id=request.POST['grupo'])
                    html = render_to_string('grupos_domotica_accordion_content.html', {'grupo': grupo, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html})
                except:
                    return JsonResponse({'ok': False})
            elif request.POST['action'] == 'delete_grupo':
                try:
                    grupo = Grupo.objects.get(id=request.POST['grupo'])
                    if grupo.propietario == g_e.gauser or g_e.has_permiso('borra_grupos_domotica'):
                        grupo.delete()
                        return JsonResponse({'ok': True, 'mensaje': "El grupo se ha borrado sin incidencias."})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar el grupo."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de borrar el grupo."})

            elif request.POST['action'] == 'update_campo':
                try:
                    grupo = Grupo.objects.get(id=request.POST['grupo'])
                    if grupo.propietario == g_e.gauser or g_e.has_permiso('edita_grupos_domotica'):
                        campo = request.POST['campo']
                        valor = request.POST['valor']
                        setattr(grupo, campo, valor)
                        grupo.save()
                        return JsonResponse({'ok': True, 'campo': campo, 'valor': valor})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el grupo."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el grupo."})
            elif request.POST['action'] == 'update_select':
                try:
                    grupo = Grupo.objects.get(id=request.POST['grupo'])
                    grupo_padre = Grupo.objects.get(id=request.POST['grupo_padre'])
                    q = grupo.propietario == g_e.gauser and grupo_padre.propietario == g_e.gauser
                    if q or g_e.has_permiso('edita_grupos_domotica'):
                        grupo.grupo_padre = grupo_padre
                        grupo.save()
                        return JsonResponse({'ok': True})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el grupo."})
                except:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el grupo."})


# @permiso_required('acceso_configura_domotica')
def configura_domotica(request):
    g_e = request.session['gauser_extra']
    # gauser_permitido = GauserPermitido.objects.filter(gauser=g_e.gauser)
    # dispositivos_permitidos = gauser_permitido.values_list('dispositivo__id', flat=True)
    # secuencias_permitidas = gauser_permitido.values_list('secuencia__id', flat=True)
    # conjuntos_permitidos = gauser_permitido.values_list('conjunto__id', flat=True)
    # dispositivos = Dispositivo.objects.filter(Q(propietario=g_e.gauser) | Q(id__in=dispositivos_permitidos))
    # secuencias = Secuencia.objects.filter(Q(propietario=g_e.gauser) | Q(id__in=secuencias_permitidas))
    # conjuntos = Conjunto.objects.filter(Q(propietario=g_e.gauser) | Q(id__in=conjuntos_permitidos))

    # if request.method == 'POST':
    #     action = request.POST['action']
    #     if action == 'libro_contabilidad_vut':
    #         permiso = Permiso.objects.get(code_nombre='genera_libro_registro_policia')
    #         grupo = Grupo.objects.get(id=request.POST['id_grupo'])
    #         if has_permiso_on_grupo(g_e, grupo, permiso):
    #             fecha_anterior_limite = datetime.today().date() - timedelta(1100)
    #             viajeros = Viajero.objects.filter(reserva__grupo=grupo,
    #                                               reserva__entrada__gte=fecha_anterior_limite)
    #             c = render_to_string('libro_registro_policia.html',
    #                                  {'grupo': grupo, 'viajeros': viajeros, 'ruta_base': RUTA_BASE})
    #             ruta = '%s%s/%s/' % (MEDIA_VUT, grupo.gpropietario.id, grupo.id)
    #             fich = html_to_pdf(request, c, fichero='libro_registros', media=ruta,
    #                                title=u'Libro de registro de viajeros', tipo='sin_cabecera')
    #             response = HttpResponse(fich, content_type='application/pdf')
    #             response['Content-Disposition'] = 'attachment; filename=Libro_registro_viajeros.pdf'
    #             return response
    #     elif action == 'download_file_asiento':
    #         asiento = AsientoVUT.objects.get(id=request.POST['asiento'])
    #         permiso = Permiso.objects.get(code_nombre='edita_asiento_vut')
    #         a = AutorizadoContabilidadVut.objects.filter(contabilidad=asiento.partida.contabilidad,
    #                                                      autorizado=g_e.gauser, permisos__in=[permiso]).count()
    #         if asiento.partida.contabilidad.propietario == g_e.gauser or a > 0:
    #             fich = open(RUTA_BASE + asiento.fichero.url)
    #             response = HttpResponse(fich, content_type=asiento.content_type)
    #             response['Content-Disposition'] = 'attachment; filename=' + asiento.fich_name
    #             return response

    grupos_id = GauserPermitidoGrupo.objects.filter(gauser=g_e.gauser).values_list('grupo', flat=True)
    return render(request, "domotica.html",
                  {
                      'formname': 'domotica',
                      # 'iconos':
                      #     ({'tipo': 'button', 'nombre': 'plus', 'permiso': 'crea_dispositivos_domotica',
                      #       'texto': 'Nuevo dispositivo', 'title': 'Crear un nuevo dispositivo domótico'},
                      #      ),
                      'grupos': Grupo.objects.filter(id__in=grupos_id),
                      'configuraciones_enlace': EnlaceDomotica.objects.filter(propietario=g_e.gauser),
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)
                  })


def pulsador_domotico(d):
    if d.plataforma == 'IFTTT':
        try:
            s = requests.Session()
            s.verify = False
            p = s.post(d.ifttt, timeout=5)
            return {'ok': True, 'response': p.status_code}
        except:
            return {'ok': False}
    elif d.plataforma == 'ESPURNA':
        if d.tipo == 'SELFLOCKING':
            topic = '{0}/relay/0/set'.format(d.mqtt_topic)
            client.publish(topic, 1)
        elif d.tipo == 'ONOFF':
            topic = '{0}/relay/0/set'.format(d.mqtt_topic)
            client.publish(topic, 2)
        else:
            return {'ok': False, 'mensaje': 'No detecta tipo'}
        # client.disconnect()
        return {'ok': True}
    else:
        return {'ok': False, 'mensaje': 'No detecta plataforma'}


@login_required()
def ajax_configura_domotica(request):
    g_e = request.session["gauser_extra"]
    if request.is_ajax():
        if request.POST['action'] == 'open_accordion':
            try:
                grupos_id = GauserPermitidoGrupo.objects.filter(gauser=g_e.gauser).values_list('grupo', flat=True)
                grupos = Grupo.objects.filter(id__in=grupos_id)
                grupo = grupos.get(id=request.POST['grupo'])
                gdispositivos = GauserPermitidoDispositivo.objects.filter(dispositivo__grupo=grupo, gauser=g_e.gauser)
                if g_e.gauser.username == 'gauss':
                    viviendas = Vivienda.objects.filter(entidad=g_e.ronda.entidad, borrada=False)
                else:
                    viviendas_posibles = viviendas_autorizado(g_e)
                html = render_to_string('domotica_accordion_content.html',
                                        {'gdispositivos': gdispositivos, 'grupo': grupo, 'g_e': g_e,
                                         'grupos': grupos, 'viviendas_posibles': viviendas_posibles})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'add_dispositivo_domotica':
            try:
                if g_e.has_permiso('crea_dispositivos_domotica'):
                    grupos_id = GauserPermitidoGrupo.objects.filter(gauser=g_e.gauser).values_list('grupo', flat=True)
                    grupos = Grupo.objects.filter(id__in=grupos_id)
                    grupo = grupos.get(id=request.POST['grupo'])
                    d = Dispositivo.objects.create(propietario=g_e.gauser, nombre='Nombre del dispositivo', grupo=grupo)
                    gdispositivo = GauserPermitidoDispositivo.objects.get(gauser=g_e.gauser, dispositivo=d)
                    html = render_to_string('domotica_accordion_content_dispositivo.html',
                                            {'g_e': g_e, 'gdispositivo': gdispositivo, 'grupos': grupos})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'delete_dispositivo_domotica':
            try:
                d = Dispositivo.objects.get(id=request.POST['dispositivo'])
                if d.permiso(g_e.gauser) == 'BORRAR' or g_e.has_permiso('borra_dispositivos_domotica'):
                    d.delete()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_campo':
            try:
                d = Dispositivo.objects.get(id=request.POST['dispositivo'])
                if 'E' in d.permiso(g_e.gauser) or g_e.has_permiso('edita_dispositivos_domotica'):
                    campo = request.POST['campo']
                    valor = request.POST['valor']
                    setattr(d, campo, valor)
                    d.save()
                    return JsonResponse({'ok': True, 'campo': campo, 'valor': valor})
                else:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
            except:
                return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
        elif request.POST['action'] == 'update_plataforma':
            try:
                d = Dispositivo.objects.get(id=request.POST['dispositivo'])
                if 'E' in d.permiso(g_e.gauser) or g_e.has_permiso('edita_dispositivos_domotica'):
                    d.plataforma = request.POST['valor']
                    d.save()
                    return JsonResponse({'ok': True, 'campo': 'plataforma', 'valor': request.POST['valor']})
                else:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
            except:
                return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
        elif request.POST['action'] == 'update_tipo_dispositivo':
            try:
                d = Dispositivo.objects.get(id=request.POST['dispositivo'])
                if 'E' in d.permiso(g_e.gauser) or g_e.has_permiso('edita_dispositivos_domotica'):
                    d.tipo = request.POST['valor']
                    d.save()
                    return JsonResponse({'ok': True, 'campo': 'tipo', 'valor': request.POST['valor']})
                else:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
            except:
                return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
        elif request.POST['action'] == 'update_grupo_dispositivo':
            try:
                d = Dispositivo.objects.get(id=request.POST['dispositivo'])
                if 'E' in d.permiso(g_e.gauser) or g_e.has_permiso('edita_dispositivos_domotica'):
                    grupo = Grupo.objects.get(id=request.POST['valor'])
                    d.grupo = grupo
                    d.save()
                    return JsonResponse({'ok': True, 'valor': request.POST['valor']})
                else:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
            except:
                return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar el dispositivo."})
        elif request.POST['action'] == 'pulsador_domotico':
            d = Dispositivo.objects.get(id=request.POST['dispositivo'])
            respuesta = pulsador_domotico(d)
            return JsonResponse(respuesta)
            if d.plataforma == 'IFTTT':
                try:
                    s = requests.Session()
                    s.verify = False
                    p = s.post(d.ifttt, timeout=5)
                    return JsonResponse({'ok': True, 'response': p.status_code})
                except:
                    return JsonResponse({'ok': False})
            elif d.plataforma == 'ESPURNA':
                if d.tipo == 'SELFLOCKING':
                    topic = '{0}/relay/0/set'.format(d.mqtt_topic)
                    client.publish(topic, 1)
                elif d.tipo == 'ONOFF':
                    topic = '{0}/relay/0/set'.format(d.mqtt_topic)
                    client.publish(topic, 2)
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No detecta tipo'})
                # client.disconnect()
                return JsonResponse({'ok': True})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No detecta plataforma'})
        elif request.POST['action'] == 'copiar_dispositivo':
            try:
                if g_e.gauser.username == 'gauss':
                    viviendas = Vivienda.objects.filter(entidad=g_e.ronda.entidad, borrada=False)
                else:
                    viviendas = viviendas_autorizado(g_e)
                vivienda = viviendas.get(id=request.POST['vivienda'])
                dispositivo = Dispositivo.objects.get(id=request.POST['id'])
                dv, c = DomoticaVUT.objects.get_or_create(vivienda=vivienda, dispositivo=dispositivo)
                dv.propietario = g_e.gauser
                dv.url = dispositivo.ifttt
                dv.nombre = dispositivo.nombre
                dv.texto = dispositivo.texto
                dv.tipo = dispositivo.tipo
                dv.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'add_enlace_domotica':
            enlace = EnlaceDomotica.objects.create(propietario=g_e.gauser, nombre='', valido_desde=timezone.now(),
                                                   valido_hasta=timezone.now())
            html = render_to_string('enlace_accordion.html', {'enlace': enlace})
            return JsonResponse({'ok': True, 'html': html})
        elif request.POST['action'] == 'open_accordion_enlace':
            try:
                enlace = EnlaceDomotica.objects.get(id=request.POST['enlace'], propietario=g_e.gauser)
                gdispositivos = GauserPermitidoDispositivo.objects.filter(gauser=g_e.gauser).order_by('dispositivo__grupo')
                html = render_to_string('enlace_accordion_content.html',
                                        {'enlace': enlace, 'gdispositivos': gdispositivos })
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'enlace_dispositivos':
            try:
                enlace = EnlaceDomotica.objects.get(id=request.POST['id'], propietario=g_e.gauser)
                enlace.dispositivos.clear()
                enlace.dispositivos.add(*request.POST.getlist('valor[]'))
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'enlace_nombre':
            try:
                enlace = EnlaceDomotica.objects.get(id=request.POST['id'], propietario=g_e.gauser)
                enlace.nombre = request.POST['valor']
                enlace.save()
                return JsonResponse({'ok': True, 'nombre': enlace.nombre})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'enlace_valido_hasta':
            try:
                enlace = EnlaceDomotica.objects.get(id=request.POST['id'], propietario=g_e.gauser)
                enlace.valido_hasta = timezone.make_aware(datetime.strptime(request.POST['valor'], '%H:%M %d-%m-%Y'))
                enlace.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'enlace_valido_desde':
            try:
                enlace = EnlaceDomotica.objects.get(id=request.POST['id'], propietario=g_e.gauser)
                enlace.valido_desde = timezone.make_aware(datetime.strptime(request.POST['valor'], '%H:%M %d-%m-%Y'))
                enlace.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'del_enlace':
            try:
                enlace = EnlaceDomotica.objects.get(id=request.POST['id'], propietario=g_e.gauser)
                enlace.delete()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})


def lnk(request):
    ahora = timezone.make_aware(datetime.today())
    if request.method == 'GET':
        try:
            secret = request.GET['s']
            enlace = EnlaceDomotica.objects.get(secret=secret)
            if enlace.valido_desde > ahora:
                return render(request, "enlace_domotica_error.html", {'tipo': 'temprano'})
            elif enlace.valido_hasta < ahora:
                return render(request, "enlace_domotica_error.html", {'tipo': 'pasado'})
            else:
                return render(request, "enlace_domotica.html",
                              {
                                  'formname': 'enlace_domotica',
                                  'enlace': enlace
                              })
        except:
            return render(request, "enlace_domotica_error.html", {'tipo': 'noexiste'})
    elif request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'boton_domotico':
            try:
                enlace = EnlaceDomotica.objects.get(secret=request.POST['secret'])
                dispositivo = Dispositivo.objects.get(id=request.POST['id'])
                if dispositivo in enlace.dispositivos.all():
                    respuesta = pulsador_domotico(dispositivo)
                    return JsonResponse(respuesta)
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'Error dispositivo'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Error getting object'})

    return JsonResponse({'ok': False})