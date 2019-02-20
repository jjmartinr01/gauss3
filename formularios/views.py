# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import zipfile
import simplejson as json
import pexpect
import os
import logging
import xlwt
from xlwt import Formula
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponse
from django.db.models import Q
import html2text
from django import forms
from django.forms import ModelForm
from django.shortcuts import render, redirect
from django.template.loader import render_to_string

from autenticar.control_acceso import permiso_required
from mensajes.models import Aviso
from mensajes.views import crear_aviso
from formularios.models import *
from gauss.rutas import *

# from entidades.models import Subentidad, Cargo
# from autenticar.models import Gauser_extra, Gauser
from entidades.models import Subentidad, Cargo, Gauser_extra
from autenticar.models import Gauser

from gauss.funciones import usuarios_de_gauss, pass_generator, html_to_pdf, paginar


class formularioForm(ModelForm):
    class Meta:
        model = Ginput
        # fields = ('destinatarios', 'asunto','mensaje')
        fields = ('tipo',)
        # widgets = {
        #     'asunto': forms.TextInput(attrs={'size': '100'}),
        #     'mensaje': forms.Textarea(attrs={'cols': 80, 'rows': 8}),
        #     # 'destinatarios': forms.SelectMultiple(attrs={'size': 30, 'id':'id_destinatarios'}),
        # }


@permiso_required('acceso_formularios')
def formularios(request):
    g_e = request.session["gauser_extra"]
    if 'gform' in request.GET:
        id_gform = int(request.GET['gform'])
    else:
        id_gform = None
    gforms = Gform.objects.filter(propietario__entidad=g_e.ronda.entidad)
    if request.method == 'POST':
        if request.POST['action'] == 'excel':
            gform = Gform.objects.get(id=request.POST['gform'], propietario__entidad=g_e.ronda.entidad)
            original_ginputs = gform.ginput_set.filter(ginput__isnull=True).order_by('row', 'col')
            ginputs = gform.ginput_set.filter(ginput__isnull=False).order_by('rellenador__gauser__last_name',
                                                                             'rellenador__gauser__first_name',
                                                                             'rellenador__id',
                                                                             'ginput__row', 'ginput__col')
            ruta = MEDIA_FORMULARIOS + str(g_e.ronda.entidad.code) + '/'
            if not os.path.exists(ruta):
                os.makedirs(ruta)
            fichero_xls = 'Formulario_GAUSS%s.xls' % (gform.id)
            wb = xlwt.Workbook()
            wf = wb.add_sheet('Cuestionario')
            wa = wb.add_sheet('Avisos')
            fila_excel_cuestionario = 0
            fila_excel_avisos = 0
            estilo = xlwt.XFStyle()
            font = xlwt.Font()
            font.bold = True
            estilo.font = font
            wf.write(fila_excel_cuestionario, 0, 'Nombre', style=estilo)
            wf.col(0).width = 8000  # Ancho de la columna para el nombre
            col = 1
            for gi in original_ginputs:
                wf.write(fila_excel_cuestionario, col, gi.label, style=estilo)
                if gi.tipo == 'gdate':
                    wf.col(col).width = max(len(gi.label) * 278, 2800)
                elif gi.tipo == 'gdatetime':
                    wf.col(col).width = max(len(gi.label) * 278, 16 * 278)
                else:
                    wf.col(col).width = len(gi.label) * 278  # Dejamos 278 de ancho por cada caracter
                col += 1

            rellenador = None
            for ginput in ginputs:
                if ginput.rellenador != rellenador:
                    rellenador = ginput.rellenador
                    col = 0
                    fila_excel_cuestionario += 1
                    wf.write(fila_excel_cuestionario, col, ginput.rellenador.gauser.get_full_name(), style=estilo)
                col += 1
                if ginput.tipo == 'gselect':
                    goptions_selected = ginput.goption_set.filter(selected=True).values_list('value', flat=True)
                    celda = ', '.join(goptions_selected)
                elif ginput.tipo == 'gfile':
                    celda = ginput.fich_name if ginput.archivo else ''
                elif ginput.tipo == 'gtext':
                    celda = ginput.gtext if ginput.gtext[:100] else ''
                elif ginput.tipo == 'gdate':
                    try:
                        celda = ginput.gdate.strftime('%d/%m/%Y')
                    except:
                        celda = ''
                elif ginput.tipo == 'gdatetime':
                    try:
                        celda = ginput.gdatetime.strftime('%d/%m/%Y %H:%M')
                    except:
                        celda = ''
                elif ginput.tipo == 'gchar':
                    celda = ginput.gchar if ginput.gchar else ''
                elif ginput.tipo == 'gint':
                    celda = ginput.gint if ginput.gint else ''
                elif ginput.tipo == 'gfloat':
                    celda = ginput.gfloat if ginput.gfloat else ''
                elif ginput.tipo == 'gbool':
                    celda = u'Sí' if ginput.gbool else u'No'
                wf.write(fila_excel_cuestionario, col, celda)

            # wf.write(fila_excel_cuestionario, 3, Formula("SUM(D2:D%s)" % (fila_excel_cuestionario)), style=estilo)

            wb.save(ruta + fichero_xls)

            xlsfile = open(ruta + '/' + fichero_xls)
            response = HttpResponse(xlsfile, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=%s' % (fichero_xls)
            return response

    return render(request, "formularios.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                                        'permiso': 'm67i10', 'title': 'Crear un nuevo formulario'},
                                       ),
                                  'formname': 'formularios',
                                  'gforms': gforms,
                                  'id_gform': id_gform,
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                              })


@login_required()
def resultados_gform(request):
    g_e = request.session["gauser_extra"]
    try:
        gform = Gform.objects.get(id=request.GET['gform'], propietario=g_e)
    except:
        crear_aviso(request, False, "No tienes permiso para ver los resultados formulario/cuestionario solicitado")
        return redirect('/calendario/')
    original_ginputs = gform.ginput_set.filter(ginput__isnull=True).order_by('row', 'col')
    ginputs = gform.ginput_set.filter(ginput__isnull=False).order_by('rellenador__gauser__last_name',
                                                                     'rellenador__gauser__first_name', 'rellenador__id',
                                                                     'ginput__row', 'ginput__col')
    if request.method == 'POST':
        if request.POST['action'] == 'descarga_gfile':
            ginput = Ginput.objects.get(id=request.POST['id_ginput'], gform__propietario__entidad=g_e.ronda.entidad)
            fichero = ginput.archivo.read()
            response = HttpResponse(fichero, content_type=ginput.content_type_archivo)
            response['Content-Disposition'] = 'attachment; filename=%s' % ginput.fich_name
            return response
    return render(request, "resultados_gform.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Volver',
                                        'permiso': 'm67i10', 'title': 'Volver a la lista de formularios'},
                                       {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                                        'permiso': 'm67i10', 'title': 'Borrar las respuestas seleccionadas'},
                                       ),
                                  'formname': 'resultados_gform',
                                  'original_ginputs': original_ginputs,
                                  'ginputs': ginputs,
                                  'gform': gform,
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                              })


@login_required()
def ver_gform(request):
    g_e = request.session["gauser_extra"]
    try:
        gform = Gform.objects.get(id=request.GET['gform'], propietario=g_e)
    except:
        crear_aviso(request, False, "No tienes permiso para ver el formulario/cuestionario solicitado")
        return redirect('/calendario/')
    ginputs = gform.ginput_set.filter(gform=gform, ginput__isnull=True).order_by('row', 'col')
    return render(request, "ver_gform.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Volver',
                                        'permiso': 'm67i10', 'title': 'Volver a la lista de formularios'},
                                       ),
                                  'ginputs': ginputs,
                                  'gform': gform,
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                              })


def crea_ginputs_para_rellenador(gform, g_e):
    originales = gform.ginput_set.filter(ginput__isnull=True)
    creados = gform.ginput_set.filter(rellenador=g_e, ginput__in=originales).values_list('ginput__id', flat=True)
    for original in originales:
        if not original.id in creados:
            nueva = Ginput.objects.create(gform=original.gform, rellenador=g_e, tipo=original.tipo, ginput=original)
            nueva.cargos_permitidos.add(*original.cargos_permitidos.all())
            if original.tipo == 'gselect':
                goptions = original.goption_set.all()
                for goption in goptions:
                    Goption.objects.create(ginput=nueva, text=goption.text, value=goption.value)
    return True


@login_required()
def rellena_gform(request):
    g_e = request.session["gauser_extra"]
    try:
        gforms = Gform.objects.filter(Q(propietario__entidad=g_e.ronda.entidad), Q(activo=True),
                                      Q(subentidades_destino__in=g_e.subentidades.all()) | Q(
                                              cargos_destino__in=g_e.cargos.all())).distinct()
        # Al poner el query set en un get se generan muchos resultados y da error. Por esto se ha separado:
        gform = gforms.get(id=request.GET['gform'])
        ge = Gauser_extra.objects.get(id=request.GET['ge'])
        if not (ge.edad < 18 and ge in g_e.unidad_familiar or ge == g_e):
            crear_aviso(request, False, "No tienes permiso para rellenar el cuestionario solicitado")
            return redirect('/calendario/')
    except:
        crear_aviso(request, False, "No tienes permiso para rellenar el cuestionario solicitado")
        return redirect('/calendario/')
    crea_ginputs_para_rellenador(gform, ge)
    # originales = gform.ginput_set.filter(ginput__isnull=True)
    # creados = gform.ginput_set.filter(rellenador=g_e, ginput__in=originales).values_list('ginput__id', flat=True)
    # for original in originales:
    #     if not original.id in creados:
    #         nueva = Ginput.objects.create(gform=original.gform, rellenador=g_e, tipo=original.tipo, ginput=original)
    #         nueva.cargos_permitidos.add(*original.cargos_permitidos.all())
    #         if original.tipo == 'gselect':
    #             goptions = original.goption_set.all()
    #             for goption in goptions:
    #                 Goption.objects.create(ginput=nueva, text=goption.text, value=goption.value)

    # if request.method == 'POST':
    #     if request.POST['action'] == 'bajar_adjunto':
    #         adjunto = Adjunto.objects.get(id=request.POST['id_adjunto'])
    #         fichero = adjunto.fichero.read()
    #         response = HttpResponse(fichero, content_type=adjunto.content_type)
    #         # response.set_cookie('fileDownload', value='true')  # Creo cookie para controlar la descarga (fileDownload.js)
    #         response['Content-Disposition'] = 'attachment; filename=' + adjunto.filename()
    #         return response

    return render(request, "rellena_gform.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                                        'permiso': 'm30i05', 'title': 'Enviar las respuestas'},
                                       ),  # El permiso m30i05 lo tienen todos los usuarios
                                  'ginputs': gform.ginput_set.filter(rellenador=ge).order_by('ginput__row',
                                                                                             'ginput__col'),
                                  'gform': gform,
                                  'ge': ge,
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                              })


@login_required()
def edita_gform(request):
    g_e = request.session["gauser_extra"]
    try:
        gform = Gform.objects.get(id=request.GET['gform'], propietario=g_e)
    except:
        crear_aviso(request, False, "No tienes permiso para editar este formulario/cuestionario")
        return redirect('/calendario/')
    if request.method == 'POST':
        if request.POST['action'] == 'bajar_adjunto':
            adjunto = Adjunto.objects.get(id=request.POST['id_adjunto'])
            fichero = adjunto.fichero.read()
            response = HttpResponse(fichero, content_type=adjunto.content_type)
            # response.set_cookie('fileDownload', value='true')  # Creo cookie para controlar la descarga (fileDownload.js)
            response['Content-Disposition'] = 'attachment; filename=' + adjunto.filename()
            return response
        if request.POST['action'] == 'mensajes_pdf':
            ids = map(int, filter(None, request.POST['id_mensajes'].split(',')))  # filter elimina los elementos vacíos
            mensajes = Mensaje.objects.filter(id__in=ids)
            fichero = 'Mensajes_%s' % (g_e.gauser.username)
            c = render_to_string('mensajes2pdf.html', {'mensajes': mensajes, 'MA': MEDIA_ANAGRAMAS},
                                 request=request)
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_MENSAJES, title=u'Mensajes/Correos')
            response = HttpResponse(fich, content_type='application/pdf')
            # response.set_cookie('fileDownload', value='true')  # Creo cookie para controlar la descarga (fileDownload.js)
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response
        if request.POST['action'] == 'adjuntos_zip':
            mensajes = Mensaje.objects.filter(id__in=[request.POST['id_mensajes']])
            fichero = MEDIA_TMP + "adjuntos_%s_%s.zip" % (g_e.gauser.username, mensajes[0].id)
            zip_file = zipfile.ZipFile(fichero, 'w')
            os.chdir(MEDIA_ADJUNTOS)  # Cambio el directorio de trabajo para llamar directamente a los archivos
            for mensaje in mensajes:
                for adjunto in mensaje.adjuntos.all():
                    zip_file.write(adjunto.filename())
            zip_file.close()
            fich = open(fichero)
            crear_aviso(request, True, u"Genera y descarga .zip con adjuntos")
            response = HttpResponse(fich, content_type='application/zip')
            # response.set_cookie('fileDownload', value='true')  # Creo cookie para controlar la descarga (fileDownload.js)
            response['Content-Disposition'] = 'attachment; filename=' + "adjuntos_%s_%s.zip" % (
                g_e.gauser.username, mensajes[0].id)
            return response

        if request.POST['action'] == 'borrar_mensajes':
            mensajes = Mensaje.objects.filter(pk__in=request.POST['id_mensajes'].split(','))
            for mensaje in mensajes:
                try:
                    Importante.objects.get(marcador=g_e, mensaje=mensaje).delete()
                except:
                    pass
                Borrado.objects.create(eraser=g_e, mensaje=mensaje)

    ginputs = gform.ginput_set.filter(gform=gform, ginput__isnull=True)
    gis = ''
    for ginput in ginputs:
        gis += render_to_string('insert_ginput.html', {'ginput': ginput})
    return render(request, "edita_gform.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'thumbs-o-up', 'texto': 'Hecho',
                                        'permiso': 'm67i10', 'title': 'Volver a la lista de formularios'},
                                       ),
                                  'cargos': Cargo.objects.filter(entidad=g_e.ronda.entidad),
                                  'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today()),
                                  'formname': 'edita_formulario',
                                  'form': formularioForm(),
                                  'tipos': TIPOS,
                                  'gis': gis,
                                  'gform': gform,
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                              })


@login_required()
def edita_ginput(request):
    g_e = request.session["gauser_extra"]
    try:
        ginput = Ginput.objects.get(id=request.GET['ginput'], gform__propietario=g_e)
    except:
        crear_aviso(request, False, "No tienes permiso para editar ese campo del formulario/cuestionario")
        return redirect('/calendario/')
    if request.method == 'POST':
        if request.POST['action'] == 'bajar_adjunto':
            adjunto = Adjunto.objects.get(id=request.POST['id_adjunto'])
            fichero = adjunto.fichero.read()
            response = HttpResponse(fichero, content_type=adjunto.content_type)
            # response.set_cookie('fileDownload', value='true')  # Creo cookie para controlar la descarga (fileDownload.js)
            response['Content-Disposition'] = 'attachment; filename=' + adjunto.filename()
            return response

    return render(request, "edita_ginput.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Volver',
                                        'permiso': 'm67i10', 'title': 'Volver al formulario'},
                                       {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Eliminar',
                                        'permiso': 'm67i10', 'title': 'Borrar este campo del formulario'},
                                       ),
                                  'cargos': Cargo.objects.filter(entidad=g_e.ronda.entidad),
                                  'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today()),
                                  'formname': 'edita_formulario',
                                  'ginput': ginput,
                                  'tipos': TIPOS,
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                              })


@login_required()
def formulario_ajax(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']

        if request.POST['action'] == 'del_gform':
            gform = Gform.objects.get(pk=request.POST['id'], propietario__entidad=g_e.ronda.entidad)
            if gform.activo == False:
                gform.delete()
            gforms = Gform.objects.filter(propietario__entidad=g_e.ronda.entidad)
            data = render_to_string('formularios_accordion.html', {'gforms': gforms})
            return HttpResponse(data)
        elif request.POST['action'] == 'add_gform':
            subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today())
            cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad)
            gform = Gform.objects.create(propietario=g_e, nombre='Nuevo formulario')
            gform.subentidades_destino.add(*subentidades)
            gform.cargos_destino.add(*cargos)
            gforms = Gform.objects.filter(propietario__entidad=g_e.ronda.entidad)
            data = render_to_string('formularios_accordion.html', {'gforms': gforms})
            return HttpResponse(data)
        elif request.POST['action'] == 'mod_gform_nombre':
            gform = Gform.objects.get(id=request.POST['id'], propietario__entidad=g_e.ronda.entidad)
            gform.nombre = request.POST['nombre']
            gform.save()
            return HttpResponse(True)
        elif request.POST['action'] == 'mod_fecha_max_rellenado':
            gform = Gform.objects.get(id=request.POST['id'], propietario__entidad=g_e.ronda.entidad)
            try:
                gform.fecha_max_rellenado = datetime.strptime(request.POST['fecha_max'], '%d/%m/%Y %H:%M')
                gform.save()
                data = json.dumps({'ok': True})
            except:
                gform.fecha_max_rellenado = datetime.now() + timedelta(days=30)
                gform.save()
                data = json.dumps({'ok': False, 'title': 'Error',
                                   'texto': u'La fecha debe ir en formato dd/mm/YYYY HH:MM. <br>Por ejemplo: 23/05/2018 08:56'})
            return HttpResponse(data)
        elif request.POST['action'] == 'asegura_fecha_max_rellenado':
            gform = Gform.objects.get(id=request.POST['id'], propietario__entidad=g_e.ronda.entidad)
            if not gform.fecha_max_rellenado:
                gform.fecha_max_rellenado = datetime.now() + timedelta(days=30)
                gform.save()
                data = json.dumps({'ok': False, 'fecha':gform.fecha_max_rellenado.strftime('%d/%m/%Y %H:%M')})
            else:
                data = json.dumps({'ok': True})
            return HttpResponse(data)
        elif request.POST['action'] == 'mod_gform_activo':
            gform = Gform.objects.get(id=request.POST['id'], propietario__entidad=g_e.ronda.entidad)
            data = ['No', 'Sí']
            gform.activo = not gform.activo
            gform.save()
            return HttpResponse(data[gform.activo])
        elif request.POST['action'] == 'mod_gform_cargos_destino':
            gform = Gform.objects.get(id=request.POST['id'], propietario__entidad=g_e.ronda.entidad)
            gform.cargos_destino.clear()
            cargos = json.loads(request.POST['seleccionados'])
            gform.cargos_destino.add(*Cargo.objects.filter(entidad=g_e.ronda.entidad, id__in=cargos))
            return HttpResponse(True)
        elif request.POST['action'] == 'mod_gform_subentidades_destino':
            gform = Gform.objects.get(id=request.POST['id'], propietario__entidad=g_e.ronda.entidad)
            gform.subentidades_destino.clear()
            subentidades = json.loads(request.POST['seleccionadas'])
            gform.subentidades_destino.add(*Subentidad.objects.filter(entidad=g_e.ronda.entidad, id__in=subentidades, fecha_expira__gt=datetime.today()))
            return HttpResponse(True)
        elif request.POST['action'] == 'update_gform':
            ginputs = json.loads(request.POST['ginputs'])
            for gi in ginputs:
                ginput = Ginput.objects.get(id=gi['id'], gform__propietario__entidad=g_e.ronda.entidad)
                ginput.row = gi['y']
                ginput.col = gi['x']
                ginput.ancho = gi['width']
                ginput.save()
            return HttpResponse(True)
        elif request.POST['action'] == 'insert_ginput':
            gform = Gform.objects.get(pk=request.POST['id'], propietario__entidad=g_e.ronda.entidad)
            ginput = Ginput.objects.create(gform=gform, tipo=request.POST['tipo'], label='Nombre de este campo')
            if ginput.tipo == 'gselect':
                for i in range(4):
                    Goption.objects.create(ginput=ginput, value=str(i), text='Opción %s' % i)
            data = render_to_string('insert_ginput.html', {'ginput': ginput}, request=request)
            return HttpResponse(data)
        elif request.POST['action'] == 'mod_ginput_label':
            ginput = Ginput.objects.get(id=request.POST['id'], gform__propietario__entidad=g_e.ronda.entidad)
            ginput.label = request.POST['label']
            ginput.save()
            return HttpResponse(True)
        elif request.POST['action'] == 'mod_ginput_multiple':
            ginput = Ginput.objects.get(id=request.POST['id'], gform__propietario__entidad=g_e.ronda.entidad)
            data = ['No', 'Sí']
            ginput.select = not ginput.select
            ginput.save()
            return HttpResponse(data[ginput.select])
        elif request.POST['action'] == 'del_ginput':
            Ginput.objects.get(id=request.POST['id'], gform__propietario__entidad=g_e.ronda.entidad).delete()
            return HttpResponse(True)
        elif request.POST['action'] == 'mod_goption_text':
            goption = Goption.objects.get(id=request.POST['id'], ginput__gform__propietario__entidad=g_e.ronda.entidad)
            goption.text = request.POST['text']
            goption.save()
            return HttpResponse(True)
        elif request.POST['action'] == 'mod_goption_value':
            goption = Goption.objects.get(id=request.POST['id'], ginput__gform__propietario__entidad=g_e.ronda.entidad)
            goption.value = request.POST['value']
            goption.save()
            return HttpResponse(True)
        elif request.POST['action'] == 'del_goption':
            goption = Goption.objects.get(id=request.POST['id'], ginput__gform__propietario__entidad=g_e.ronda.entidad)
            ginput = goption.ginput
            goption.delete()
            goptions = render_to_string('edita_goption.html', {'ginput': ginput})
            return HttpResponse(goptions)
        elif request.POST['action'] == 'add_goption':
            ginput = Ginput.objects.get(id=request.POST['id'], gform__propietario__entidad=g_e.ronda.entidad)
            Goption.objects.create(ginput=ginput, value='nuevo_valor', text='Nueva opción')
            goptions = render_to_string('edita_goption.html', {'ginput': ginput})
            return HttpResponse(goptions)
        elif request.POST['action'] == 'mod_cargos_permitidos':
            ginput = Ginput.objects.get(id=request.POST['id'], gform__propietario__entidad=g_e.ronda.entidad)
            ginput.cargos_permitidos.clear()
            cargos = json.loads(request.POST['seleccionados'])
            ginput.cargos_permitidos.add(*Cargo.objects.filter(entidad=g_e.ronda.entidad, id__in=cargos))
            return HttpResponse(True)
        elif request.POST['action'] == 'del_alert':  # Para que no aparezca el mensaje de ayuda sobre edición de ginputs
            request.session['del_alert'] = 1
            return HttpResponse(True)
        elif request.POST['action'] == 'save_gfile':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not ((ge.edad < 18 and ge in g_e.unidad_familiar) or (ge == g_e)): return HttpResponse('No tienes permiso')
            id_ginput = request.POST['id_ginput']
            ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
            try:
                fichero = ginput.archivo.url
                os.remove(RUTA_BASE + fichero)
                ginput.archivo = None
                ginput.content_type_archivo = ''
                ginput.fich_name = ''
                ginput.save()
            except:
                pass
            fichero = request.FILES['ginput' + id_ginput]
            ginput.archivo = fichero
            ginput.content_type_archivo = fichero.content_type
            ginput.save()
            return HttpResponse(True)
        elif request.POST['action'] == 'delete_gfile':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not (ge.edad < 18 and ge in g_e.unidad_familiar or ge == g_e): return HttpResponse('No tienes permiso')
            id_ginput = request.POST['id']
            ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
            fichero = ginput.archivo.url
            os.remove(RUTA_BASE + fichero)
            ginput.archivo = None
            ginput.content_type_archivo = ''
            ginput.fich_name = ''
            ginput.save()
            return HttpResponse(True)
        elif request.POST['action'] == 'save_gint':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not (ge.edad < 18 and ge in g_e.unidad_familiar or ge == g_e): return HttpResponse('No tienes permiso')
            id_ginput = request.POST['id']
            ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
            try:
                ginput.gint = int(request.POST['valor'])
                ginput.save()
                return HttpResponse(True)
            except:
                return HttpResponse('El valor introducido debe ser un número entero (sin letras ni decimales)')
        elif request.POST['action'] == 'save_gchar':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not (ge.edad < 18 and ge in g_e.unidad_familiar or ge == g_e): return HttpResponse('No tienes permiso')
            id_ginput = request.POST['id']
            ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
            try:
                ginput.gchar = request.POST['valor']
                ginput.save()
                return HttpResponse(True)
            except:
                return HttpResponse('El valor introducido debe ser un cadena de caracteres alfanuméricos')
        elif request.POST['action'] == 'save_gbool':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not (ge.edad < 18 and ge in g_e.unidad_familiar or ge == g_e): return HttpResponse('No tienes permiso')
            id_ginput = request.POST['id']
            ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
            ginput.gbool = not ginput.gbool
            ginput.save()
            return HttpResponse(True)
        elif request.POST['action'] == 'save_gfloat':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not (ge.edad < 18 and ge in g_e.unidad_familiar or ge == g_e): return HttpResponse('No tienes permiso')
            id_ginput = request.POST['id']
            ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
            try:
                ginput.gfloat = float(request.POST['valor'])
                ginput.save()
                return HttpResponse(True)
            except:
                texto_error = 'El valor introducido debe ser un número. Para separar decimales utiliza el punto (".") en lugar de la coma (",")'
                return HttpResponse(texto_error)
        elif request.POST['action'] == 'save_gdate':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not (ge.edad < 18 and ge in g_e.unidad_familiar or ge == g_e): return HttpResponse('No tienes permiso')
            id_ginput = request.POST['id']
            ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
            try:
                ginput.gdate = datetime.strptime(request.POST['valor'], '%d/%m/%Y')
                ginput.save()
                return HttpResponse(True)
            except:
                fecha = datetime.now().date().strftime('%d/%m/%Y')
                texto_error = 'La fecha debe tener el formato: dd/mm/yyyy, por ejemplo:<br>%s' % fecha
                return HttpResponse(texto_error)
        elif request.POST['action'] == 'save_gdatetime':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not (ge.edad < 18 and ge in g_e.unidad_familiar or ge == g_e): return HttpResponse('No tienes permiso')
            id_ginput = request.POST['id']
            ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
            try:
                ginput.gdatetime = datetime.strptime(request.POST['valor'], '%d/%m/%Y %H:%M')
                ginput.save()
                return HttpResponse(True)
            except:
                fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
                texto_error = 'La fecha debe tener el formato: dd/mm/yyyy HH:mm, por ejemplo:<br>%s' % fecha
                return HttpResponse(texto_error)
        elif request.POST['action'] == 'save_gtext':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not (ge.edad < 18 and ge in g_e.unidad_familiar or not ge == g_e): return HttpResponse('Error')
            id_ginput = request.POST['id']
            ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
            try:
                ginput.gtext = request.POST['valor']
                ginput.save()
                return HttpResponse(True)
            except:
                return HttpResponse('El valor introducido debe ser un texto de caracteres alfanuméricos')
        elif request.POST['action'] == 'save_gselect':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not (ge.edad < 18 and ge in g_e.unidad_familiar or ge == g_e): return HttpResponse('No tienes permiso')
            id_ginput = request.POST['id']
            ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
            try:
                ginput.gse = request.POST['valor']
                ginput.save()
                return HttpResponse(True)
            except:
                return HttpResponse('El valor introducido debe ser un cadena de caracteres alfanuméricos')
        elif request.POST['action'] == 'save_goption':
            ge = Gauser_extra.objects.get(id=request.POST['ge'])
            if not (ge.edad < 18 and ge in g_e.unidad_familiar or ge == g_e): return HttpResponse('No tienes permiso')
            try:
                id_ginput = request.POST['id']
                ginput = Ginput.objects.get(id=id_ginput, gform__propietario__entidad=g_e.ronda.entidad)
                for goption in ginput.goption_set.all():
                    goption.selected = False
                    goption.save()
                ids = json.loads(request.POST['selected'])
                ids = ids if isinstance(ids, list) else [ids]
                goptions = Goption.objects.filter(id__in=ids)
                for goption in goptions:
                    goption.selected = True
                    goption.save()
                return HttpResponse(True)
            except:
                return HttpResponse('Se ha producido un error en la recepción de los datos.')
        elif request.POST['action'] == 'delete_ginputs':
            gform = Gform.objects.get(pk=request.POST['gform'], propietario__entidad=g_e.ronda.entidad)
            rellenadores = Gauser_extra.objects.filter(id__in=json.loads(request.POST['ids']))
            ginputs = gform.ginput_set.filter(rellenador__in=rellenadores)
            for ginput in ginputs:
                try:
                    if ginput.archivo:
                        fichero = ginput.archivo.url
                        os.remove(RUTA_BASE + fichero)
                    ginput.delete()
                except:
                    HttpResponse('Error durante el borrado del campo %s' % ginput.ginput.label)
            return HttpResponse(True)
            # try:
            #     ginput.gse = request.POST['valor']
            #     ginput.save()
            #     return HttpResponse(True)
            # except:
            #     return HttpResponse('El valor introducido debe ser un cadena de caracteres alfanuméricos')
