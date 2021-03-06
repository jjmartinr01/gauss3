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
from entidades.views import decode_selectgcs
from gauss.funciones import html_to_pdf, pass_generator, usuarios_ronda
from gauss.rutas import RUTA_MEDIA, MEDIA_VUT, RUTA_BASE
from autenticar.control_acceso import permiso_required
from mensajes.models import Aviso
from autenticar.models import Permiso, Gauser
from mensajes.views import encolar_mensaje, crear_aviso
from domotica.models import *
from domotica.mqtt import client
from vut.models import Vivienda, DomoticaVUT
from vut.views import viviendas_autorizado


# @permiso_required('acceso_dispositivos')
def dispositivos(request):
    g_e = request.session['gauser_extra']
    Etiqueta_domotica.objects.get_or_create(entidad=g_e.ronda.entidad, nombre='General')
    gpds = GauserPermitidoDispositivo.objects.filter(dispositivo__entidad=g_e.ronda.entidad,
                                                     gauser=g_e.gauser).values_list('dispositivo__id', flat=True)
    q = Q(id__in=gpds) | Q(propietario=g_e.gauser)
    disps = Dispositivo.objects.filter(Q(entidad=g_e.ronda.entidad), q).distinct()
    etiquetas = Etiqueta_domotica.objects.filter(entidad=g_e.ronda.entidad)
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'ver_formulario_crear' and g_e.has_permiso('crea_dispositivos_domotica'):
            try:
                d = Dispositivo(propietario=g_e.gauser, nombre='Nombre del dispositivo', texto='Texto descripción')
                html = render_to_string('dispositivos_fieldset_crear.html', {'g_e': g_e, 'etiquetas': etiquetas,
                                                                             'dispositivo': d})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'crea_dispositivo' and g_e.has_permiso('crea_dispositivos_domotica'):
            try:
                try:
                    etiqueta = Etiqueta_domotica.objects.get(entidad=g_e.ronda.entidad,
                                                             id=request.POST['select_etiqueta'])
                except:
                    etiqueta = Etiqueta_domotica.objects.get(entidad=g_e.ronda.entidad, nombre='General')
                d = Dispositivo.objects.create(entidad=g_e.ronda.entidad, propietario=g_e.gauser, etiqueta=etiqueta,
                                               plataforma=request.POST['plataforma'], texto=request.POST['texto'],
                                               mqtt_port=request.POST['mqtt_port'], nombre=request.POST['nombre'],
                                               mqtt_id=request.POST['mqtt_id'], mqtt_topic=request.POST['mqtt_topic'],
                                               ifttt=request.POST['ifttt'], mqtt_broker=request.POST['mqtt_broker'],
                                               tipo=request.POST['tipo'])
                html = render_to_string('dispositivos_table_tr.html', {'disps': [d], 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_crear_etiqueta' and g_e.has_permiso('crea_carpetas'):
            try:
                html = render_to_string("dispositivos_fieldset_etiqueta.html", {'etiquetas': etiquetas})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_editar_carpeta' and g_e.has_permiso('edita_carpetas'):
            try:
                e = Etiqueta_domotica.objects.get(id=request.POST['etiqueta'])
                html = render_to_string("dispositivos_fieldset_etiqueta_editar.html",
                                        {'etiquetas': etiquetas, 'etiqueta': e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'modifica_etiqueta' and g_e.has_permiso('edita_carpetas'):
            try:
                nombre = request.POST['nombre']
                try:
                    Etiqueta_domotica.objects.get(entidad=g_e.ronda.entidad, nombre__iexact=nombre)
                    return JsonResponse({'ok': False, 'mensaje': 'Ya existe una etiqueta/carpeta con ese nombre.'})
                except:
                    e = Etiqueta_domotica.objects.get(id=request.POST['etiqueta'])
                    e.nombre = nombre
                    try:
                        e.padre = Etiqueta_domotica.objects.get(id=request.POST['padre'])
                    except:
                        e.padre = None
                    e.save()
                    html = render_to_string('dispositivos_table_tr.html', {'disps': disps, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_buscar':
            try:
                html = render_to_string("dispositivos_fieldset_buscar.html", {'etiquetas': etiquetas, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'crea_etiqueta' and g_e.has_permiso('crea_carpetas'):
            try:
                nombre = request.POST['nombre']
                try:
                    Etiqueta_domotica.objects.get(entidad=g_e.ronda.entidad, nombre__iexact=nombre)
                    return JsonResponse({'ok': False, 'mensaje': 'Ya existe una etiqueta/carpeta con ese nombre.'})
                except:
                    if request.POST['padre']:
                        padre = Etiqueta_domotica.objects.get(entidad=g_e.ronda.entidad, id=request.POST['padre'])
                        Etiqueta_domotica.objects.create(entidad=g_e.ronda.entidad, padre=padre, nombre=nombre)
                    else:
                        Etiqueta_domotica.objects.create(entidad=g_e.ronda.entidad, nombre=nombre)
                    return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borra_etiqueta' and g_e.has_permiso('borra_cualquier_carpeta'):
            try:
                Etiqueta_domotica.objects.get(entidad=g_e.ronda.entidad, id=request.POST['etiqueta']).delete()
                html = render_to_string('dispositivos_table_tr.html', {'disps': disps, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'busca_disps_manual':
            try:
                try:
                    inicio = datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date()
                except:
                    inicio = datetime.strptime('1900-1-1', '%Y-%m-%d').date()
                try:
                    fin = datetime.strptime(request.POST['fin'], '%Y-%m-%d').date()
                except:
                    fin = datetime.now().date()
                texto = request.POST['texto']
                try:
                    etiqueta = Etiqueta_domotica.objects.get(entidad=g_e.ronda.entidad, id=request.POST['etiqueta'])
                except:
                    etiqueta = None
                if etiqueta:
                    q = Q(propietario__ronda__entidad=g_e.ronda.entidad) & Q(
                        creado__gte=inicio) & Q(creado__lte=fin) & Q(
                        nombre__icontains=texto) & Q(etiqueta__in=etiqueta.hijos)
                else:
                    q = Q(propietario__ronda__entidad=g_e.ronda.entidad) & Q(
                        creado__gte=inicio) & Q(creado__lte=fin) & Q(
                        nombre__icontains=texto)

                disps_search = disps.filter(q)
                html = render_to_string('dispositivos_table_tr.html', {'disps': disps_search, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_editar':
            try:
                disp = disps.get(id=request.POST['disp'])
                if g_e.has_permiso('edita_todos_archivos') or disp.permiso_w(g_e.gauser) or disp.permiso_x(g_e.gauser):
                    hoy = datetime.now().date()
                    subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gte=hoy)
                    cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad)
                    d = {'g_e': g_e, 'cargos': cargos, 'subentidades': subentidades, 'etiquetas': etiquetas, 'd': disp}
                    html = render_to_string("dispositivos_table_tr_device_edit.html", d)
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_archivo':
            try:
                disp = disps.get(id=request.POST['disp'])
                if g_e.has_permiso('edita_todos_archivos') or disp.permiso_w(g_e.gauser) or disp.permiso_x(g_e.gauser):
                    disp.nombre = request.POST['nombre']
                    disp.etiqueta = Etiqueta_domotica.objects.get(id=request.POST['etiqueta'])
                    disp.cargos.clear()
                    disp.acceden.clear()
                    cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('cargos[]'))
                    subs = Subentidad.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('subs[]'))
                    disp.cargos.add(*cargos)
                    disp.acceden.add(*subs)
                    disp.save()
                    html = render_to_string('dispositivos_table_tr_device.html', {'d': disp, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_dispositivo':
            disp = disps.get(id=request.POST['disp'])
            if disp.permiso_x(g_e.gauser) or disp.propietario == g_e or g_e.has_permiso('borra_cualquier_archivo'):
                GauserPermitidoDispositivo.objects.filter(dispositivo=disp, gauser=g_e.gauser).delete()
                otros = GauserPermitidoDispositivo.objects.filter(dispositivo=disp).count()
                if otros == 0:
                    disp.delete()
                return JsonResponse(
                    {'ok': True, 'mensaje': 'Dispositivo borrado. Ahora pueden verlo %s personas' % otros})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No ha sido posible borrar el dispositivo.'})
        elif request.POST['action'] == 'borrar_disp_completamente':
            disp = disps.get(id=request.POST['disp'])
            if g_e.has_permiso('borra_cualquier_archivo'):
                todos = GauserPermitidoDispositivo.objects.filter(dispositivo=disp)
                todos.delete()
                disp.delete()
                return JsonResponse({'ok': True, 'mensaje': 'Dispositivo borrado por completo.'})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No ha sido posible borrar el dispositivo.'})
        else:
            return JsonResponse({'ok': False, 'mensaje': 'No tiene los permisos necesarios.'})

    elif request.method == 'POST':
        if request.POST['action'] == 'crea_dispositivo43254432':
            n_files = int(request.POST['n_files'])
            if g_e.has_permiso('crea_dispositivos_domotica'):
                try:
                    for i in range(n_files):
                        fichero = request.FILES['fichero_xhr' + str(i)]
                        try:
                            etiqueta = Etiqueta_domotica.objects.get(entidad=g_e.ronda.entidad,
                                                                     id=request.POST['etiqueta'])
                        except:
                            etiqueta, c = Etiqueta_domotica.objects.get_or_create(entidad=g_e.ronda.entidad,
                                                                                  nombre='General')
                        disp = Dispositivo.objects.create(propietario=g_e, content_type=fichero.content_type,
                                                          etiqueta=etiqueta, nombre=fichero.name, fichero=fichero)
                        GauserPermitidoDispositivo.objects.create(gauser=g_e.gauser, dispositivo=disp, permiso='x')
                        html = render_to_string('dispositivos_table_tr.html', {'disps': [disp], 'g_e': g_e})
                        return JsonResponse({'ok': True, 'html': html, 'mensaje': False})
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
            else:
                mensaje = 'No tienes permiso para cargar programaciones.'
                return JsonResponse({'ok': False, 'mensaje': mensaje})

        elif request.POST['action'] == 'descargar_disp':
            try:
                d = disps.get(id=request.POST['dispositivo'])
                fichero = d.fichero.read()
                response = HttpResponse(fichero, content_type=d.content_type)
                response['Content-Disposition'] = 'attachment; filename=' + d.fich_name
                return response
            except:
                crear_aviso(request, False, 'Error. No se ha podido descargar el archivo.')

    return render(request, "dispositivos.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'permiso': 'crea_dispositivos_domotica', 'title': 'Anadir un nuevo dispositivo'},
                           {'tipo': 'button', 'nombre': 'folder', 'texto': 'Nueva', 'permiso': 'crea_carpetas',
                            'title': 'Crear una nueva carpeta/etiqueta'},
                           {'tipo': 'button', 'nombre': 'search', 'texto': 'Buscar/Filtrar',
                            'permiso': 'libre',
                            'title': 'Busca/Filtra resultados entre los diferentes archivos'},
                           ),
                      'g_e': g_e,
                      'etiquetas': etiquetas,
                      'disps': disps,
                      'carpetas': Etiqueta_domotica.objects.filter(entidad=g_e.ronda.entidad),
                      'formname': 'dispositivos',
                      'carpeta_id': 'todas',  # Este identificador implica leer todas las carpetas
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


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
            elif request.POST['action'] == 'update_usuarios_autorizados':
                try:
                    grupo = Grupo.objects.get(id=request.POST['grupo'])
                    operacion = request.POST['operacion']
                    if operacion == 'add':
                        autorizado = Gauser_extra.objects.get(id=request.POST['autorizado'][1:]).gauser
                    elif operacion == 'delete' or operacion == 'change_permiso':
                        gpg = GauserPermitidoGrupo.objects.get(id=request.POST['autorizado'])
                        autorizado = gpg.gauser
                    else:
                        autorizado = None
                    # Condiciones con las que tendría permiso para editar el grupo y añadir autorizados:
                    c1 = grupo.gauserpermitidogrupo_set.filter(gauser=g_e.gauser, permiso__icontains='VUE').count() > 0
                    c2 = g_e.has_permiso('edita_grupos_domotica')
                    c3 = grupo.propietario == g_e.gauser
                    if (c1 or c2 or c3) and request.POST['operacion'] == 'add':
                        GauserPermitidoGrupo.objects.get_or_create(gauser=autorizado, grupo=grupo)
                    elif (c1 or c2 or c3) and request.POST['operacion'] == 'delete':
                        gpg.delete()
                    elif (c1 or c2 or c3) and request.POST['operacion'] == 'change_permiso':
                        gpg.permiso = request.POST['permiso']
                        gpg.save()
                    html = render_to_string('grupos_domotica_accordion_content_autorizados.html', {'grupo': grupo})
                    return JsonResponse({'ok': True, 'html': html, 'permiso': c1 or c2 or c3})
                except:
                    return JsonResponse({'ok': False})

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
                    viviendas_posibles = Vivienda.objects.filter(borrada=False)
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
                    viviendas = Vivienda.objects.filter(borrada=False)
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
                gdispositivos = GauserPermitidoDispositivo.objects.filter(gauser=g_e.gauser).order_by(
                    'dispositivo__grupo')
                html = render_to_string('enlace_accordion_content.html',
                                        {'enlace': enlace, 'gdispositivos': gdispositivos})
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
