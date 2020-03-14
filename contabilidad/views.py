# -*- coding: utf-8 -*-
from datetime import date, timedelta
import os
import base64
import simplejson as json
import re
import string
import locale
import xlwt
from xlwt import Formula

from django.shortcuts import render, redirect
from django.core.files.base import ContentFile
from django.utils.timezone import datetime
from django.utils.text import slugify
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q, Sum
from django import forms
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string

# from autenticar.models import Gauser, Gauser_extra
# from entidades.models import Subentidad, Cargo
from autenticar.models import Gauser
from entidades.models import Subentidad, Cargo, Gauser_extra

from bancos.views import asocia_banco_ge, num_cuenta2iban
from gauss.rutas import *
from gauss.funciones import usuarios_de_gauss, pass_generator, usuarios_ronda
from contabilidad.models import Presupuesto, Partida, Asiento, Politica_cuotas, Remesa, File_contabilidad, \
    Remesa_emitida, OrdenAdeudo
from autenticar.control_acceso import permiso_required
from gauss.funciones import html_to_pdf
from mensajes.views import crear_aviso
from mensajes.models import Aviso
from django.urls import reverse
from django.http import HttpResponseRedirect

from vut.models import Vivienda

locale.setlocale(locale.LC_ALL, 'es_ES.utf8')


class PartidaForm(forms.ModelForm):
    class Meta:
        model = Partida
        exclude = ('presupuesto',)


class File_contabilidadForm(forms.ModelForm):
    class Meta:
        model = File_contabilidad
        fields = ('fichero',)


class AsientoForm(forms.ModelForm):  # Form accesible por usuario
    def __init__(self, *args, **kwargs):
        self.presupuesto = kwargs.pop("presupuesto")
        super(AsientoForm, self).__init__(*args, **kwargs)
        self.fields["partida"].queryset = Partida.objects.filter(presupuesto=self.presupuesto)

    class Meta:
        model = Asiento
        fields = ('concepto', 'nombre', 'cantidad', 'partida', 'escaneo')
        widgets = {  # 'concepto': forms.Textarea(attrs={'cols': 50, 'rows':4, 'class':'obligatorio'}),
            'concepto': forms.TextInput(attrs={'size': '100', 'class': 'obligatorio'}),
            # 'nombre': forms.TextInput(attrs={'class':'obligatorio','size':150}),
            'nombre': forms.Textarea(attrs={'cols': 100, 'rows': 1, 'class': 'obligatorio'}),
            'cantidad': forms.TextInput(attrs={'class': 'obligatorio', 'size': 15}),
        }


@permiso_required('acceso_presupuestos')
def presupuestos(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST':
        if request.POST['action'] == 'pdf_presupuesto':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            partidas = Partida.objects.filter(presupuesto=presupuesto)
            gastos = partidas.filter(tipo='GASTO').aggregate(gasto_total=Sum('cantidad'))
            ingresos = partidas.filter(tipo='INGRE').aggregate(ingreso_total=Sum('cantidad'))
            fichero = 'presupuesto_%s_%s' % (g_e.ronda.entidad.id, presupuesto.id)
            c = render_to_string('presupuesto2pdf.html',
                                 {'presupuesto': presupuesto, 'partidas': partidas, 'gastos': gastos,
                                  'ingresos': ingresos, 'MA': MEDIA_ANAGRAMAS},
                                 request=request)
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_PRESUPUESTO, title=u'Presupuesto')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response
        elif request.POST['action'] == 'add_presupuesto':
            describir = request.POST['describir']
            describir = 'No hay descripción para este presupesto.' if len(describir) < 5 else describir
            Presupuesto.objects.create(nombre=request.POST['nombre'], describir=describir, entidad=g_e.ronda.entidad)
        elif request.POST['action'] == 'mod_presupuesto':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            presupuesto.nombre = request.POST['nombre']
            presupuesto.describir = request.POST['describir']
            presupuesto.save()
        elif request.POST['action'] == 'borrar_presupuesto':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            if Partida.objects.filter(presupuesto=presupuesto).count() == 0:
                presupuesto.delete()
            else:
                crear_aviso(request, False, 'El presupuesto no se puede borrar porque contiene partidas')
        elif request.POST['action'] == 'copiar_presupuesto':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            p = Presupuesto.objects.create(entidad=g_e.ronda.entidad, nombre=presupuesto.nombre + ' (copia)',
                                           describir=presupuesto.describir)
            partidas = Partida.objects.filter(presupuesto=presupuesto)
            for partida in partidas:
                Partida.objects.create(presupuesto=p, tipo=partida.tipo, nombre=partida.nombre,
                                       cantidad=partida.cantidad)
        elif request.POST['action'] == 'archivar_presupuesto':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            presupuesto.archivado = True
            presupuesto.save()
        elif request.POST['action'] == 'abrir_presupuesto':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            presupuesto.archivado = False
            presupuesto.save()

    presupuestos = Presupuesto.objects.filter(entidad=g_e.ronda.entidad)
    return render(request, "presupuestos_list.html",
                  {
                      'formname': 'Presupuestos',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                            'title': 'Aceptar los cambios realizados', 'permiso': 'edita_presupuestos'},
                           {'tipo': 'button', 'nombre': 'plus', 'texto': 'Presupuesto',
                            'title': 'Crear un nuevo presupuesto',
                            'permiso': 'crea_presupuestos'},
                           {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Presupuestos',
                            'title': 'Mostrar la lista de presupuestos',
                            'permiso': 'edita_presupuestos'},),
                      'presupuestos': presupuestos,
                      'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                     aceptado=False),
                  })


@permiso_required('acceso_gastos_ingresos')
def presupuesto(request, id=False):
    if id:
        g_e = request.session["gauser_extra"]
        try:
            presupuesto = Presupuesto.objects.get(entidad=g_e.ronda.entidad, id=id)
        except:
            return HttpResponseRedirect(reverse('presupuestos'))
    else:
        return HttpResponseRedirect(reverse('presupuestos'))

    partidas = Partida.objects.filter(presupuesto=presupuesto)

    if request.method == 'POST':
        if request.POST['action'] == 'pdf_presupuesto':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            partidas = Partida.objects.filter(presupuesto=presupuesto)
            gastos = partidas.filter(tipo='GASTO').aggregate(gasto_total=Sum('cantidad'))
            ingresos = partidas.filter(tipo='INGRE').aggregate(ingreso_total=Sum('cantidad'))

            fichero = 'presupuesto_%s_%s' % (g_e.ronda.entidad.id, g_e.ronda.id)
            c = render_to_string('presupuesto2pdf.html',
                                 {'presupuesto': presupuesto, 'partidas': partidas, 'gastos': gastos,
                                  'ingresos': ingresos, 'MA': MEDIA_ANAGRAMAS},
                                 request=request)
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_PRESUPUESTO, title=u'Presupuesto')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response

    gastos = partidas.filter(tipo='GASTO').aggregate(gasto_total=Sum('cantidad'))
    ingresos = partidas.filter(tipo='INGRE').aggregate(ingreso_total=Sum('cantidad'))
    return render(request, "presupuesto.html",
                  {
                      'formname': 'Presupuesto',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                            'title': 'Aceptar los cambios realizados', 'permiso': 'edita_presupuestos'},
                           {'tipo': 'button', 'nombre': 'plus', 'texto': 'Partida',
                            'title': 'Añadir nueva partida al presupuesto',
                            'permiso': 'edita_presupuestos'},
                           {'tipo': 'button', 'nombre': 'pencil', 'texto': 'Editar',
                            'title': 'Editar la partida para su modificación',
                            'permiso': 'edita_presupuestos'},
                           {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                            'title': 'Borrar la partida seleccionada', 'permiso': 'edita_presupuestos'},
                           {'tipo': 'button', 'nombre': 'file-text-o', 'texto': 'PDF',
                            'title': 'Generar documento pdf del presupuesto',
                            'permiso': 'edita_presupuestos'}),
                      'presupuesto': presupuesto,
                      'partidas': partidas,
                      'gastos': gastos,
                      'ingresos': ingresos,
                      'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                     aceptado=False),
                  })


@login_required()
def presupuesto_ajax(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        if request.POST['action'] == 'presupuesto_data':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            data = {'nombre': presupuesto.nombre, 'describir': presupuesto.describir}
            return HttpResponse(json.dumps(data))
        elif request.POST['action'] == 'add_partida':
            form = PartidaForm()
            html = render_to_string("add_partida.html", {'form': form, }, request=request)
            return HttpResponse(html)
        elif request.POST['action'] == 'mod_partida':
            partida = Partida.objects.get(id=request.POST['id'])
            form = PartidaForm(instance=partida)
            html = render_to_string("mod_partida.html", {'form': form, }, request=request)
            return HttpResponse(html)
        elif request.POST['action'] == 'del_partida':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            Partida.objects.get(id=request.POST['id']).delete()
            partidas = Partida.objects.filter(presupuesto=presupuesto)
            gastos = partidas.filter(tipo='GASTO').aggregate(gasto_total=Sum('cantidad'))
            ingresos = partidas.filter(tipo='INGRE').aggregate(ingreso_total=Sum('cantidad'))
            html = render_to_string("list_partidas.html",
                                    {'partidas': partidas, 'gastos': gastos, 'ingresos': ingresos, },
                                    request=request)
            return HttpResponse(html)
        elif request.POST['action'] == 'save_partida_added':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            Partida.objects.create(presupuesto=presupuesto, tipo=request.POST['tipo'],
                                   nombre=request.POST['nombre'], cantidad=request.POST['cantidad'])
            partidas = Partida.objects.filter(presupuesto=presupuesto)
            gastos = partidas.filter(tipo='GASTO').aggregate(gasto_total=Sum('cantidad'))
            ingresos = partidas.filter(tipo='INGRE').aggregate(ingreso_total=Sum('cantidad'))
            html = render_to_string("list_partidas.html",
                                    {'partidas': partidas, 'gastos': gastos, 'ingresos': ingresos, },
                                    request=request)
            return HttpResponse(html)
        elif request.POST['action'] == 'save_partida_modified':
            presupuesto = Presupuesto.objects.get(id=request.POST['id_presupuesto'], entidad=g_e.ronda.entidad)
            partida = Partida.objects.filter(id=request.POST['partida_id'])
            partida.update(presupuesto=presupuesto, tipo=request.POST['tipo'], nombre=request.POST['nombre'],
                           cantidad=request.POST['cantidad'])
            # Con update no hace falta save(), pero sin save() no se actualiza la fecha de modificación:
            partida[0].save()
            partidas = Partida.objects.filter(presupuesto=presupuesto)
            gastos = partidas.filter(tipo='GASTO').aggregate(gasto_total=Sum('cantidad'))
            ingresos = partidas.filter(tipo='INGRE').aggregate(ingreso_total=Sum('cantidad'))
            html = render_to_string("list_partidas.html",
                                    {'partidas': partidas, 'gastos': gastos, 'ingresos': ingresos, },
                                    request=request)
            return HttpResponse(html)


@permiso_required('acceso_gastos_ingresos')
def gastos_ingresos(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST':
        presupuestos = None
        presupuesto = Presupuesto.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id_presupuesto'])
        asientos = Asiento.objects.filter(partida__presupuesto=presupuesto)
        partidas_gastos = Partida.objects.filter(presupuesto=presupuesto, tipo='GASTO')
        partidas_ingresos = Partida.objects.filter(presupuesto=presupuesto, tipo='INGRE')
        if request.POST['action'] == 'pdf_gastos_ingresos':
            gi_gastos = []
            for partida in partidas_gastos:
                asientos_partida = Asiento.objects.filter(partida=partida)
                total_partida = asientos_partida.aggregate(total=Sum('cantidad'))
                gi_gastos.append([partida, asientos_partida, total_partida['total']])
            gi_ingresos = []
            for partida in partidas_ingresos:
                asientos_partida = Asiento.objects.filter(partida=partida)
                total_partida = asientos_partida.aggregate(total=Sum('cantidad'))
                gi_ingresos.append([partida, asientos_partida, total_partida['total']])
            fichero = 'gastos_ingresos_%s_%s' % (g_e.ronda.entidad.id, g_e.ronda.id)
            c = render_to_string('gastos_ingresos2pdf.html', {
                'MA': MEDIA_ANAGRAMAS,
                'gi_ingresos': gi_ingresos,
                'gi_gastos': gi_gastos,
                'g_total': asientos.filter(partida__tipo='GASTO').aggregate(total=Sum('cantidad'))['total'],
                'i_total': asientos.filter(partida__tipo='INGRE').aggregate(total=Sum('cantidad'))['total'],
                'pg_total': partidas_gastos.aggregate(total=Sum('cantidad'))['total'],
                'pi_total': partidas_ingresos.aggregate(total=Sum('cantidad'))['total'],
            }, request=request)
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_PRESUPUESTO, title=u'Gastos e Ingresos')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response

        if request.POST['action'] == 'bajar_justificante':
            asiento = Asiento.objects.get(id=request.POST['asiento_id'])
            url_file = asiento.escaneo.fichero.url
            fichero = url_file.replace('/media/contabilidad/', MEDIA_CONTABILIDAD)
            response = HttpResponse(open(fichero, 'rb'))
            response['Content-Disposition'] = 'attachment; filename=' + asiento.escaneo.fich_name
            return response
    else:
        presupuestos = Presupuesto.objects.filter(entidad=g_e.ronda.entidad, archivado=False)
        if len(presupuestos) != 1:
            presupuesto = None
            data = ''
        else:
            presupuesto = presupuestos[0]
            asientos = Asiento.objects.filter(partida__presupuesto=presupuesto)
            data = render_to_string("list_asientos.html", {
                'gi_ingresos': asientos.filter(partida__tipo='INGRE').reverse().order_by('modificado'),
                'gi_gastos': asientos.filter(partida__tipo='GASTO').reverse().order_by('modificado'),
                'g_total': asientos.filter(partida__tipo='GASTO').aggregate(total=Sum('cantidad'))['total'],
                'i_total': asientos.filter(partida__tipo='INGRE').aggregate(total=Sum('cantidad'))['total'],
            }, request=request)

    iconos = ({'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Ingresos/Gastos', 'permiso': 'edita_gastos_ingresos',
               'title': 'Mostrar la lista de gastos e ingresos'},
              {'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'title': 'Guardar los cambios realizados',
               'permiso': 'edita_gastos_ingresos'},
              {'tipo': 'button', 'nombre': 'plus', 'texto': 'Gasto/Ingreso', 'title': 'Añadir nuevo gasto o ingreso',
               'permiso': 'edita_gastos_ingresos'},
              {'tipo': 'button', 'nombre': 'pencil', 'texto': 'Editar',
               'title': 'Editar el gasto/ingreso para su modificación', 'permiso': 'edita_gastos_ingresos'},
              {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
               'title': 'Borrar el ingreso o gasto seleccionado', 'permiso': 'edita_gastos_ingresos'},
              {'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF', 'permiso': 'pdf_gastos_ingresos',
               'title': 'Generar documento pdf con los gastos e ingresos registrados'})
    return render(request, "gastos_ingresos.html",
                  {
                      'formname': 'Ingreso_gasto',
                      'iconos': iconos,
                      'data': data,
                      'presupuesto': presupuesto,
                      'presupuestos': presupuestos,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def gastos_ingresos_ajax(request):
    if request.is_ajax():
        g_e = request.session["gauser_extra"]
        presupuesto = Presupuesto.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id_presupuesto'])
        if request.POST['action'] == 'muestra_presupuesto':
            asientos = Asiento.objects.filter(partida__presupuesto=presupuesto)
            gi_gastos = asientos.filter(partida__tipo='GASTO').reverse().order_by('modificado')
            gi_ingresos = asientos.filter(partida__tipo='INGRE').reverse().order_by('modificado')
            data = render_to_string("list_asientos.html", {
                'gi_ingresos': gi_ingresos,
                'gi_gastos': gi_gastos,
                'g_total': asientos.filter(partida__tipo='GASTO').aggregate(total=Sum('cantidad'))['total'],
                'i_total': asientos.filter(partida__tipo='INGRE').aggregate(total=Sum('cantidad'))['total'],
            }, request=request)
            return HttpResponse(data)
        elif request.POST['action'] == 'borrar_asientos':
            id_asientos = json.loads(request.POST['id_asientos'])
            asientos = Asiento.objects.filter(id__in=id_asientos)
            for asiento in asientos:
                file_contabilidad = asiento.escaneo
                asiento.delete()
                if file_contabilidad:
                    os.remove(RUTA_BASE + file_contabilidad.fichero.url)
                    file_contabilidad.delete()
            data = json.dumps({'borrados': id_asientos})
            return HttpResponse(data)
        elif request.POST['action'] == 'add_gasto_ingreso':
            form1 = AsientoForm(presupuesto=presupuesto)
            form2 = File_contabilidadForm()
            data = render_to_string("add_gasto_ingreso.html", {'form1': form1, 'form2': form2},
                                    request=request)
            return HttpResponse(data)
        elif request.POST['action'] == 'mod_gasto_ingreso':
            asiento = Asiento.objects.get(id=request.POST['id'])
            form1 = AsientoForm(instance=asiento, presupuesto=asiento.partida.presupuesto)
            form2 = File_contabilidadForm(instance=asiento.escaneo)
            data = render_to_string("add_gasto_ingreso.html", {'form1': form1, 'form2': form2},
                                    request=request)
            return HttpResponse(data)
        elif request.POST['action'] == 'save_added_gasto_ingreso':
            if 'fichero' in request.FILES:
                fichero = request.FILES['fichero']
                file_contabilidad = File_contabilidad.objects.create(entidad=g_e.ronda.entidad, fichero=fichero,
                                                                     content_type=fichero.content_type)
            else:
                file_contabilidad = None
            partida = Partida.objects.get(id=request.POST['partida'])
            Asiento.objects.create(escaneo=file_contabilidad, partida=partida,
                                   nombre=request.POST['nombre'], concepto=request.POST['concepto'],
                                   cantidad=request.POST['cantidad'])
            asientos = Asiento.objects.filter(partida__presupuesto=presupuesto)
            gi_gastos = asientos.filter(partida__tipo='GASTO').reverse().order_by('modificado')
            gi_ingresos = asientos.filter(partida__tipo='INGRE').reverse().order_by('modificado')
            data = render_to_string("list_asientos.html", {
                'gi_ingresos': gi_ingresos,
                'gi_gastos': gi_gastos,
                'g_total': asientos.filter(partida__tipo='GASTO').aggregate(total=Sum('cantidad'))['total'],
                'i_total': asientos.filter(partida__tipo='INGRE').aggregate(total=Sum('cantidad'))['total'],
            }, request=request)
            return HttpResponse(data)
        elif request.POST['action'] == 'save_mod_gasto_ingreso':
            asiento = Asiento.objects.filter(id=request.POST['asiento_id'],
                                             partida__presupuesto__entidad=g_e.ronda.entidad)
            data = {'partida': request.POST['partida'], 'concepto': request.POST['concepto'],
                    'nombre': request.POST['nombre'], 'cantidad': request.POST['cantidad']}
            if 'fichero' in request.FILES:
                file_contabilidad_antiguo = asiento[0].escaneo
                fichero = request.FILES['fichero']
                file_contabilidad = File_contabilidad.objects.create(entidad=g_e.ronda.entidad, fichero=fichero,
                                                                     content_type=fichero.content_type)
                data['escaneo'] = file_contabilidad
                asiento.update(**data)
                if file_contabilidad_antiguo:
                    os.remove(RUTA_BASE + file_contabilidad_antiguo.fichero.url)
                    file_contabilidad_antiguo.delete()
            else:
                # Para usar update asiento debe ser una queryset, es decir es necesario utilizar filter (no get)
                asiento.update(**data)
            # Con update no hace falta save(), pero sin save() no se actualiza la fecha de modificación:
            asiento[0].save()
            asientos = Asiento.objects.filter(partida__presupuesto=presupuesto)
            gi_gastos = asientos.filter(partida__tipo='GASTO').reverse().order_by('modificado')
            gi_ingresos = asientos.filter(partida__tipo='INGRE').reverse().order_by('modificado')
            data = render_to_string("list_asientos.html", {
                'gi_ingresos': gi_ingresos,
                'gi_gastos': gi_gastos,
                'g_total': asientos.filter(partida__tipo='GASTO').aggregate(total=Sum('cantidad'))['total'],
                'i_total': asientos.filter(partida__tipo='INGRE').aggregate(total=Sum('cantidad'))['total'],
            }, request=request)
            return HttpResponse(data)


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#

class Politica_cuotasForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.entidad = kwargs.pop("entidad")
        super(Politica_cuotasForm, self).__init__(*args, **kwargs)
        self.fields["cargo"].queryset = Cargo.objects.filter(entidad=self.entidad)

    class Meta:
        model = Politica_cuotas
        exclude = ('entidad', 'exentos')


# @permiso_required('acceso_politica_cuotas')
def politica_cuotas(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        if request.POST['action'] == 'pdf_politicas_cuotas':
            politicas = Politica_cuotas.objects.filter(entidad=g_e.ronda.entidad)
            fichero = 'Politica_cuotas_%s_%s' % (g_e.ronda.entidad.id, g_e.ronda.id)
            c = render_to_string('politica_cuotas2pdf.html', {'politicas': politicas, 'MA': MEDIA_ANAGRAMAS},
                                 request=request)
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_CONTABILIDAD, title=u'Políticas de cuotas')
            response = HttpResponse(fich, content_type='application/pdf')
            response.set_cookie('fileDownload',
                                value='true')  # Creo cookie para controlar la descarga (fileDownload.js)
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response

        if request.POST['action'] == 'borrar_politica_cuotas':
            ids = request.POST['id_politica_cuotas']
            Politica_cuotas.objects.get(id=request.POST['id_politica_cuotas']).delete()

        if request.POST['action'] == 'mod_politica':
            politica = Politica_cuotas.objects.get(id=request.POST['id_politica_cuotas'])
            form = Politica_cuotasForm(request.POST, instance=politica, entidad=g_e.ronda.entidad)
            if form.is_valid():
                politica = form.save()
                politica.exentos.clear()
                try:
                    exentos_id = Gauser_extra.objects.filter(id__in=request.POST.getlist('exentos'),
                                                             ronda=g_e.ronda).values_list('gauser__id', flat=True)
                    exentos = Gauser.objects.filter(id__in=exentos_id)
                    politica.exentos.add(*exentos)
                except:
                    pass
            else:
                crear_aviso(request, False, form.errors)
            # return JsonResponse({'ge': request.POST.getlist('exentos'), 'g':list(exentos_id)})

        if request.POST['action'] == 'crea_politica_cuota':
            politica_cuota = Politica_cuotas(entidad=g_e.ronda.entidad)
            form = Politica_cuotasForm(request.POST, instance=politica_cuota, entidad=g_e.ronda.entidad)
            if form.is_valid():
                politica = form.save()
                try:
                    exentos = Gauser.objects.filter(id__in=request.POST['exentos'].split(','))
                    politica.exentos.add(*exentos)
                except:
                    pass
            else:
                crear_aviso(request, False, form.errors)

        if request.POST['action'] == 'descarga_remesa':
            remesa_emitida = Remesa_emitida.objects.get(id=request.POST['id_remesa_emitida'])
            ruta = MEDIA_CONTABILIDAD + str(g_e.ronda.entidad.code) + '/'
            grupo = remesa_emitida.grupo
            fichero = '%s.xml' % (grupo)
            xmlfile = open(ruta + '/' + fichero, 'rb')
            response = HttpResponse(xmlfile, content_type='application/xml')
            response['Content-Disposition'] = 'attachment; filename=Remesas_%s-%s-%s.xml' % (
                remesa_emitida.creado.year, remesa_emitida.creado.month, remesa_emitida.creado.day)
            return response

        if request.POST['action'] == 'descarga_excel':
            remesa_emitida = Remesa_emitida.objects.get(id=request.POST['id_remesa_emitida'])
            ruta = MEDIA_CONTABILIDAD + str(g_e.ronda.entidad.code) + '/'
            grupo = remesa_emitida.grupo
            fichero = '%s.xls' % (grupo)
            xlsfile = open(ruta + '/' + fichero, 'rb')
            response = HttpResponse(xlsfile, content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename=Remesas_%s-%s-%s.xls' % (
                remesa_emitida.creado.year, remesa_emitida.creado.month, remesa_emitida.creado.day)
            return response

    try:
        pext = Politica_cuotas.objects.get(entidad=g_e.ronda.entidad, tipo='extraord', seqtp='OOFF')
    except:
        pext = Politica_cuotas.objects.create(entidad=g_e.ronda.entidad, tipo='extraord', tipo_cobro='ANU',
                                              concepto='Remesa extraordinaria', seqtp='OOFF')
    politicas = Politica_cuotas.objects.filter(entidad=g_e.ronda.entidad).exclude(id=pext.id)
    return render(request, "politica_cuotas.html",
                  {
                      'formname': 'Politica_cuotas',
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                            'title': 'Aceptar los cambios realizados', 'permiso': 'edita_politica_cuotas'},
                           {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Cuotas',
                            'title': 'Ver la lista de cuotas creadas', 'permiso': 'edita_politica_cuotas'},
                           {'tipo': 'button', 'nombre': 'plus', 'texto': 'Política',
                            'title': 'Añadir una nueva política de cuotas', 'permiso': 'crea_politica_cuotas'},
                           {'tipo': 'button', 'nombre': 'pencil', 'texto': 'Editar',
                            'title': 'Editar la política de cuotas para su modificación',
                            'permiso': 'edita_politica_cuotas'},
                           {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                            'title': 'Borrar la política de cuotas seleccionada', 'permiso': 'borra_politica_cuotas'},
                           {'tipo': 'button', 'nombre': 'money', 'texto': 'Remesas', 'permiso': 'crea_remesas',
                            'title': 'Genera remesas de la política de cuotas seleccionada'},
                           {'tipo': 'button', 'nombre': 'file-text-o', 'texto': 'PDF',
                            'permiso': 'pdf_gastos_ingresos',
                            'title': 'Genera documento PDF con las políticas de cuotas'}),
                      'politicas': politicas,
                      'pext': pext,
                      # 'remesas_emitidas': remesas_emitidas,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def ajax_politica_cuotas(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        if request.method == 'POST':
            if request.POST['action'] == 'contenido_politica_cuotas':
                politica = Politica_cuotas.objects.get(id=request.POST['id'])
                data = render_to_string('contenido_politica_cuotas.html', {'politica': politica})
                return HttpResponse(data)
            if request.POST['action'] == 'mod_politica':
                politica = Politica_cuotas.objects.get(id=request.POST['id'])
                p_id = politica.id
                # keys = ('id', 'text')
                # exentos = json.dumps([dict(zip(keys, (row.id, "%s, %s" % (row.last_name, row.first_name)))) for row in
                #                       politica.exentos.all()])
                exentos = Gauser_extra.objects.filter(ronda=g_e.ronda, gauser__in=politica.exentos.all())
                form = Politica_cuotasForm(instance=politica, entidad=g_e.ronda.entidad)
                html = render_to_string("form_politica_cuoutas.html", {'form': form, 'exentos': exentos, 'p_id': p_id})
                return JsonResponse({'html': html, 'ok': True})
            if request.POST['action'] == 'crear_politica_cuota':
                form = Politica_cuotasForm(entidad=g_e.ronda.entidad)
                data = render_to_string("form_politica_cuoutas.html", {'form': form, },
                                        request=request)
                return HttpResponse(data)
            if request.POST['action'] == 'borrar_remesa_emitida':
                remesa = Remesa_emitida.objects.get(id=request.POST['id'])
                remesa.visible = False
                remesa.save()
                remesas_emitidas = Remesa_emitida.objects.filter(visible=True, politica=remesa.politica)[:3]
                data = render_to_string("remesas_emitidas.html",
                                        {'remesas_emitidas': remesas_emitidas, 'politica': remesa.politica},
                                        request=request)
                return HttpResponse(data)
            if request.POST['action'] == 'cargar_no_exentos':
                politica = Politica_cuotas.objects.get(id=request.POST['id'])
                num = int(request.POST['num'])
                data = render_to_string("no_exentos.html", {'numero': num, 'politica': politica})
                return HttpResponse(data)
            if request.POST['action'] == 'cargar_exentos':
                politica = Politica_cuotas.objects.get(id=request.POST['id'])
                num = int(request.POST['num'])
                data = render_to_string("exentos.html", {'numero': num, 'politica': politica})
                return HttpResponse(data)
            if request.POST['action'] == 'generar_remesas':
                # Para validar el xml generado
                # http://www.mobilefish.com/services/sepa_xml_validation/sepa_xml_validation.php
                politica = Politica_cuotas.objects.get(id=request.POST['id'])
                if politica.tipo == 'extraord':
                    usuarios = usuarios_ronda(g_e.ronda).filter(id__in=request.POST.getlist('usuarios[]'))
                    politica.concepto = request.POST['concepto']
                    politica.cuota = request.POST['cuota']
                    politica.save()
                else:
                    # exentos_id = politica.exentos.all().values_list('id', flat=True)
                    # usuarios = usuarios_de_gauss(g_e.ronda.entidad, cargos=[politica.cargo]).exclude(
                    #     gauser__id__in=exentos_id)
                    usuarios = politica.destinatarios
                grupo = pass_generator(size=15, chars=string.ascii_letters + string.digits)
                remesa_emitida = Remesa_emitida.objects.create(grupo=grupo, politica=politica)
                # array_coutas identifica los enteros y floats almacenados en cuota
                # que pueden estar separados por espacios, comas, ... o cualquier secuencia de caracteres:
                importes = politica.array_cuotas
                # Proporciona una secuencia de importes añadiendo el último valor lo suficientemente grande como para
                # asegurar que el número elementos sobre los que se aplica la cuota es superado.
                # Por ejemplo si importes es [30,20,15], después de ser procesado con array_cutoas
                # sería [30,20,15,15,15,15,15,15,15,15,15,15,15,15,...,15,15,15,15,15] con el 15 prolongado mil veces

                usuarios_id = []
                n = 0

                ruta = MEDIA_CONTABILIDAD + str(g_e.ronda.entidad.code) + '/'
                if not os.path.exists(ruta):
                    os.makedirs(ruta)
                fichero_xls = '%s.xls' % (grupo)
                wb = xlwt.Workbook()
                wr = wb.add_sheet('Remesas')
                wa = wb.add_sheet('Avisos')
                fila_excel_remesas = 0
                fila_excel_avisos = 0
                estilo = xlwt.XFStyle()
                font = xlwt.Font()
                font.bold = True
                estilo.font = font
                wr.write(fila_excel_remesas, 0, 'Destinatario cobro (dbtrnm)', style=estilo)
                wr.write(fila_excel_remesas, 1, 'Concepto (rmtinf)', style=estilo)
                wr.write(fila_excel_remesas, 2, 'Cuenta bancaria (dbtriban)', style=estilo)
                wr.write(fila_excel_remesas, 3, 'Couta (instdamt)', style=estilo)

                for usuario in usuarios:
                    n += 1
                    if usuario.id not in usuarios_id:
                        if politica.tipo == 'hermanos':
                            familiares = usuario.unidad_familiar
                            deudores = familiares.filter(id__in=usuarios)
                            # if deudores.count() > 1:
                            #     concepto = 'Familia %s' % deudores[0].gauser.last_name
                            # else:
                            #     concepto = deudores[0].gauser.get_full_name()
                            usuarios_id += list(deudores.values_list('id', flat=True))
                            n_cs = familiares.values_list('num_cuenta_bancaria', flat=True)
                            deudores_str = ', '.join(deudores.values_list('gauser__first_name', flat=True))
                        elif politica.tipo == 'fija':
                            deudores = [usuario]
                            usuarios_id += [usuario.id]
                            n_cs = [usuario.num_cuenta_bancaria]
                            deudores_str = '%s ' % (usuario.gauser.get_full_name())
                            # concepto = 'Cuota %s' % usuario.ronda.entidad.name
                        elif politica.tipo == 'vut':
                            # viviendas = Vivienda.objects.filter(propietarios__in=[usuario.gauser],
                            #                                     entidad=usuario.ronda.entidad)
                            viviendas = Vivienda.objects.filter(gpropietario=usuario.gauser, borrada=False,
                                                                entidad=usuario.ronda.entidad)
                            deudores = [usuario] * viviendas.count()
                            usuarios_id += [usuario.id]
                            n_cs = [usuario.num_cuenta_bancaria]
                            deudores_str = '%s viviendas gestionadas por %s' % (viviendas.count(),
                                                                                usuario.gauser.get_full_name())
                            # concepto = 'Cuota %s' % usuario.ronda.entidad.name
                        elif politica.tipo == 'extraord':
                            deudores = [usuario]
                            usuarios_id += [usuario.id]
                            n_cs = [usuario.num_cuenta_bancaria]
                            deudores_str = '%s ' % (usuario.gauser.get_full_name())
                        else:
                            deudores = []
                            usuarios_id += [usuario.id]
                            n_cs = []
                            deudores_str = ''
                            # concepto = ''
                        importe = sum(importes[:len(deudores)])
                        if importe > 0:
                            try:
                                cuenta_banca = [n_c.replace(' ', '') for n_c in n_cs if len(str(n_c)) > 18][0]
                                usuario.num_cuenta_bancaria = num_cuenta2iban(cuenta_banca)
                                usuario.save()
                                asocia_banco_ge(usuario)
                                try:
                                    if politica.tipo_cobro == 'MEN':
                                        rmtinf = '%s - Cobro %s, mes de %s (%s)' % (politica.concepto,
                                                                                    politica.get_tipo_cobro_display(),
                                                                                    date.today().strftime('%B'),
                                                                                    deudores_str)
                                    elif politica.tipo_cobro == 'ANU':
                                        rmtinf = '%s - Cobro %s, realizado en %s (%s)' % (politica.concepto,
                                                                                          politica.get_tipo_cobro_display(),
                                                                                          date.today().strftime('%B'),
                                                                                          deudores_str)
                                    else:
                                        rmtinf = '%s - Pago solicitado en %s (%s)' % (politica.concepto,
                                                                                      date.today().strftime('%B'),
                                                                                      deudores_str)
                                    try:
                                        orden_adeudo = OrdenAdeudo.objects.get(politica=politica, gauser=usuario.gauser)
                                        dtofsgntr = orden_adeudo.creado
                                    except:
                                        dtofsgntr = date(2013, 10, 10)
                                    r = Remesa.objects.create(emitida=remesa_emitida,
                                                              banco=usuario.banco, dtofsgntr=dtofsgntr,
                                                              ge=usuario,
                                                              dbtriban=usuario.num_cuenta_bancaria,
                                                              rmtinf=rmtinf[:139], instdamt=importe, counter=n)
                                    fila_excel_remesas += 1
                                    wr.write(fila_excel_remesas, 0, r.dbtrnm)
                                    wr.write(fila_excel_remesas, 1, r.rmtinf)
                                    wr.write(fila_excel_remesas, 2, r.dbtriban)
                                    wr.write(fila_excel_remesas, 3, r.instdamt)
                                except Exception as e:
                                    fila_excel_avisos += 1
                                    aviso = 'No se ha podido crear la remesa para %s' % (
                                        deudores[0].gauser.get_full_name())
                                    wa.write(fila_excel_avisos, 0, aviso)
                                    wa.write(fila_excel_avisos, 5, str(e))
                            except:
                                if politica.tipo == 'hermanos':
                                    for deudor in deudores:
                                        fila_excel_avisos += 1
                                        aviso = 'Falta número de cuenta bancaria en usuario %s. No se crea remesa.' % (
                                            deudor.gauser.get_full_name())
                                        wa.write(fila_excel_avisos, 0, aviso)

                fila_excel_remesas += 1
                wr.write(fila_excel_remesas, 3, Formula("SUM(D2:D%s)" % (fila_excel_remesas)), style=estilo)
                wr.col(0).width = 10000
                wr.col(1).width = 15000
                wr.col(2).width = 8000
                wr.col(3).width = 5000
                wb.save(ruta + fichero_xls)
                hoy = date.today()
                remesas = Remesa.objects.filter(emitida=remesa_emitida)
                remesa_emitida.ctrlsum = remesas.aggregate(total=Sum('instdamt'))['total']
                remesa_emitida.nboftxs = remesas.count()
                remesa_emitida.reqdcolltndt = hoy + timedelta(days=4)
                remesa_emitida.save()
                xml = render_to_string("xml_gauss.xml", {'remesa_emitida': remesa_emitida})
                # xml = xml.replace('ñ','n').replace('Ñ','N')
                fichero = '%s.xml' % (grupo)
                xmlfile = open(ruta + '/' + fichero, "w+")
                xmlfile.write(xml)
                xmlfile.close()
                data = render_to_string("remesas_emitidas.html", {'politica': politica})
                return HttpResponse(data)

        if request.method == 'GET':
            if request.GET['action'] == 'exentos':
                g_e = request.session['gauser_extra']
                texto = request.GET['q']
                cargo = request.GET['cargo']
                if cargo:
                    usuarios = Gauser_extra.objects.filter(ronda=g_e.ronda, cargos__in=[cargo])
                else:
                    usuarios = Gauser_extra.objects.filter(ronda=g_e.ronda)
                usuarios_contain_texto = usuarios.filter(
                    Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)).values_list(
                    'gauser__id', 'gauser__last_name', 'gauser__first_name', 'subentidades__nombre')
                keys = ('id', 'text')
                return HttpResponse(json.dumps(
                    [dict(zip(keys, (row[0], '%s, %s (%s)' % (row[1], row[2], row[3])))) for row in
                     usuarios_contain_texto]))


# @login_required()
# def mod_politica(request):
# if request.is_ajax():
# g_e = request.session['gauser_extra']
# politica = Politica_cuotas.objects.get(id=request.POST['id'])
# form = Politica_cuotasForm(instance=politica)
# html = render_to_string("form_politica_cuoutas.html", {'form': form},
# request=request)
# return HttpResponse(html)


# @login_required()
# def crear_politica_cuota(request):
# if request.is_ajax():
# g_e = request.session['gauser_extra']
# form = Politica_cuotasForm()
# html = render_to_string("form_politica_cuoutas.html", {'form': form, },
#                                 request=request)
#         return HttpResponse(html)


@login_required()
def lista_socios(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        politica = Politica_cuotas.objects.get(id=request.POST['id'])
        # Dependiendo de los perfiles del emisor tendrá unos socios u otros:
        socios = {}
        socios_grupo = usuarios_de_gauss(g_e.ronda.entidad)
        # socios_grupo = Gauser_extra.objects.filter( entidad = g_e.ronda.entidad, ronda = g_e.ronda ).exclude(gauser__username = 'gauss')
        perfil_elegido = politica.perfil

        educandos = socios_grupo.filter(perfiles__in=[perfil_elegido])
        subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad, perfil=perfil_elegido,
                                                 fecha_expira__gt=date.today())
        for subentidad in subentidades:
            educandos_rama = educandos.filter(subentidades__in=[subentidad]).distinct()
            if len(educandos_rama) > 0:
                socios[subentidad.nombre] = educandos_rama

        # if perfil_elegido.id == 70:
        #     educandos = socios_grupo.filter(perfiles__id__in=[70])
        #     subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad, perfil_id=70)
        #     for subentidad in subentidades:
        #         educandos_rama = educandos.filter(subentidades__in=[subentidad]).distinct()
        #         if len(educandos_rama) > 0:
        #             socios[subentidad.nombre] = educandos_rama
        # elif perfil_elegido.id == 75:
        #     socios['Voluntarios'] = socios_grupo.filter(perfiles__id__in=[75])
        # elif perfil_elegido.id == 80:
        #     educandos = socios_grupo.filter(perfiles__id__in=[70])
        #     subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad, perfil__in=[45, 50, 55, 60, 65])
        #     for subentidad in subentidades:
        #         perfil = subentidad.perfil
        #         educandos_rama = educandos.filter(perfiles__in=[perfil, ]).distinct()
        #         padres_id = list(
        #             set(itertools.chain.from_iterable(educandos_rama.values_list('tutor1__id', 'tutor2__id'))))
        #         socios['Padres y Madres de ' + subentidad.nombre] = Gauser_extra.objects.filter(
        #             id__in=padres_id).distinct()
        # elif perfil_elegido.id == 85:
        #     socios['Socios adultos'] = socios_grupo.filter(perfiles__id__in=[85])

        socios_exentos = politica.exentos.all().values_list('id', flat=True)
        html = render_to_string("list_exentos.html",
                                {'socios': socios, 'socios_exentos': socios_exentos, 'politica': politica, },
                                request=request)
        return HttpResponse(html)

        # ---------------------------------------------------------------------------------------------------#
        # ---------------------------------------------------------------------------------------------------#

        # def crea_asientos(request):
        #
        #   csv_file  = open('/home/juanjo/django/gauss_asocia/asientos.csv', "rb")
        #   fichero = csv.reader(csv_file, delimiter=';')
        #   #Iniciamos un forloop para recorrer todas las filas del archivo (no la primera que contiene nombre de los campos)
        #   for row in fichero:
        #     fila = []
        #     for col in row:
        #       fila.append(unicode(col,'utf-8'))
        #     partida = Partida.objects.get(id=fila[1])
        #     concepto = fila[4]
        #     nombre = fila[2]
        #     cantidad = fila[3]
        #     creado = datetime.strptime(fila[0], '%d/%m/%Y')
        #     Asiento.objects.create(partida=partida, nombre=nombre, cantidad=cantidad, creado=creado, concepto=concepto, modificado=creado)
        #   csv_file.close()


def comprueba_ordenes_adeudo(g_e):
    if g_e.num_cuenta_bancaria:
        familia = g_e.unidad_familiar
        politicas = Politica_cuotas.objects.filter(entidad=g_e.ronda.entidad)
        cargos_familia = [c for c in Cargo.objects.filter(id__in=familia.values_list('cargos__id', flat=True))]
        q1 = Q(tipo='hermanos') & Q(cargo__in=cargos_familia)
        q2 = Q(cargo__in=g_e.cargos.all())
        pols = politicas.filter(q1 | q2)
        for p in pols:
            OrdenAdeudo.objects.get_or_create(gauser=g_e.gauser, politica=p)
        q = Q(gauser=g_e.gauser) & Q(politica__entidad=g_e.ronda.entidad) & Q(fecha_firma__isnull=True)
        return OrdenAdeudo.objects.filter(q)
    else:
        return OrdenAdeudo.objects.none()


@permiso_required('acceso_ordenes_adeudo')
def ordenes_adeudo(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        orden = OrdenAdeudo.objects.get(id=request.POST['orden_id'], politica__entidad=g_e.ronda.entidad,
                                        firma__isnull=False)
        fichero = 'orden_adeudo_directo_SEPA'
        c = render_to_string('orden_adeudo2pdf.html', {'orden': orden})
        fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_CONTABILIDAD, title='Orden de adeudo directo SEPA')
        response = HttpResponse(fich, content_type='application/pdf')
        nombre = slugify('%s_%s' % (orden.politica.concepto, orden.gauser.get_full_name()))
        response['Content-Disposition'] = 'attachment; filename=' + nombre + '.pdf'
        return response
    ordenes_firmadas = OrdenAdeudo.objects.filter(fecha_firma__isnull=False, politica__entidad=g_e.ronda.entidad)
    return render(request, "ordenes_adeudo.html",
                  {
                      'formname': 'ordenes_adeudo',
                      'ordenes_firmadas': ordenes_firmadas
                  })


@login_required()
def firmar_orden_adeudo(request, id_oa):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'guarda_firma':
            try:
                orden_adeudo = OrdenAdeudo.objects.get(id=request.POST['orden_adeudo'], gauser=g_e.gauser)
                firma_data = request.POST['firma']
                format, imgstr = firma_data.split(';base64,')
                ext = format.split('/')[-1]
                orden_adeudo.firma = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
                orden_adeudo.fecha_firma = date.today()
                orden_adeudo.save()
                crear_aviso(request, False, 'Orden de adeudo firmada correctamente.')
                return JsonResponse({'ok': True})
            except:
                crear_aviso(request, False, 'Se ha producido un error en tu solicitud.')
                return JsonResponse({'ok': False})
    try:
        orden_firma = OrdenAdeudo.objects.get(gauser=g_e.gauser, politica__entidad=g_e.ronda.entidad,
                                              fecha_firma__isnull=True, id=id_oa)
    except:
        crear_aviso(request, False, 'Se ha producido un error en tu solicitud.')
        return redirect('/mis_ordenes_adeudo/')
    return render(request, "firmar_orden_adeudo.html",
                  {
                      'formname': 'firmar_orden_adeudo',
                      'orden_firma': orden_firma
                  })


@login_required()
def mis_ordenes_adeudo(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        orden = OrdenAdeudo.objects.get(id=request.POST['orden_id'], politica__entidad=g_e.ronda.entidad,
                                        firma__isnull=False, gauser=g_e.gauser)
        fichero = 'orden_adeudo_directo_SEPA'
        c = render_to_string('orden_adeudo2pdf.html', {'orden': orden})
        fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_CONTABILIDAD, title='Orden de adeudo directo SEPA')
        response = HttpResponse(fich, content_type='application/pdf')
        nombre = slugify('%s_%s' % (orden.politica.concepto, orden.gauser.get_full_name()))
        response['Content-Disposition'] = 'attachment; filename=' + nombre + '.pdf'
        return response
    mis_ordenes_firmadas = OrdenAdeudo.objects.filter(gauser=g_e.gauser, fecha_firma__isnull=False,
                                                      politica__entidad=g_e.ronda.entidad)
    mis_ordenes_pendientes = comprueba_ordenes_adeudo(g_e)
    return render(request, "mis_ordenes_adeudo.html",
                  {
                      'formname': 'mis_ordenes_adeudo',
                      'mis_ordenes_firmadas': mis_ordenes_firmadas,
                      'mis_ordenes_pendientes': mis_ordenes_pendientes,
                      'g_e': g_e
                  })
