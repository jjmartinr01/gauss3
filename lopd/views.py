# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth.decorators import login_required
from django.forms import ModelForm
from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext
from django.template.loader import render_to_string
from autenticar.control_acceso import permiso_required
from entidades.models import Cargo, Gauser_extra
from documentos.models import Ges_documental
from gauss.funciones import html_to_pdf
from gauss.rutas import MEDIA_LOPD, MEDIA_INCIDENCIAS_LOPD
from lopd.models import Estructura_lopd, Incidencia_lopd, Fichero_incidencia, TIPOS_INCIDENCIA, Soporte_lopd
from mensajes.models import Aviso
from mensajes.views import crear_aviso
from django.core.files import File


class Estructura_lopdForm(ModelForm):
    class Meta:
        model = Estructura_lopd
        fields = ('responsables_fichero', 'responsables_seguridad', 'delegados_proteccion',)


class Doc_seguridadForm(ModelForm):
    class Meta:
        model = Estructura_lopd
        fields = ('doc_seguridad',)


class Incidencia_lopdForm(ModelForm):
    class Meta:
        model = Incidencia_lopd
        fields = ('tipo', 'incidencia',)


class ResuelveIncidencia_lopdForm(ModelForm):
    class Meta:
        model = Incidencia_lopd
        fields = ('observaciones',)


class Soporte_lopdForm(ModelForm):
    class Meta:
        model = Soporte_lopd
        fields = ('nombre', 'lugar', 'observaciones')


@permiso_required('acceso_responsables_lopd')
def responsables_lopd(request):
    g_e = request.session["gauser_extra"]
    try:
        estructura_lopd = Estructura_lopd.objects.get(entidad=g_e.ronda.entidad)
    except:
        doc_seguridad = render_to_string('doc_seguridad_general.html', {}, request=request)
        estructura_lopd = Estructura_lopd.objects.create(entidad=g_e.ronda.entidad, doc_seguridad=doc_seguridad,
                                                         encargado_tratamiento="Sistemas de Gestión Aumentada (NIF: 18034131S)")
    if request.method == 'POST':
        crear_aviso(request, True, request.META['PATH_INFO'] + ' POST')
        form = Estructura_lopdForm(request.POST)
        if form.is_valid():
            form = Estructura_lopdForm(request.POST, instance=estructura_lopd)
            form.save()
            crear_aviso(request, False, u'<p>Estructura de LOPD modificada/guardada correctamente.</p>')
        else:
            crear_aviso(request, False, form.errors)
            form = Estructura_lopdForm(request.POST)
    else:
        crear_aviso(request, True, request.META['PATH_INFO'])
        form = Estructura_lopdForm(instance=estructura_lopd)

    # cargos_entidad = Cargo.objects.filter(entidad=g_e.ronda.entidad)
    # cargos = Gauser_extra.objects.filter(cargos__in = cargos_entidad)
    hoy = datetime.date.today()
    fecha_minima = datetime.datetime(hoy.year, hoy.month, hoy.day)
    cargos = Gauser_extra.objects.filter(ronda=g_e.ronda, gauser__nacimiento__lte=fecha_minima)
    return render(request, "responsables_lopd.html",
                              {
                                  'formname': 'estructura_lopd',
                                  'iconos':
                                      ({'nombre': 'check', 'texto': 'Aceptar',
                                        'title': 'Aceptar los cambios realizados', 'permiso': 'modifica_responsables_fichero'},),
                                  'form': form,
                                  'estructura_lopd': estructura_lopd,
                                  'cargos': cargos,
                                  'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                                 aceptado=False),
                              })


# --------------------------------------------------------------------------------#
@login_required()
def documento_seguridad(request):
    g_e = request.session["gauser_extra"]
    doc_seguridad = render_to_string('doc_seguridad_general.html', {}, request=request)
    try:
        estructura_lopd = Estructura_lopd.objects.get(entidad=g_e.ronda.entidad)
        estructura_lopd.doc_seguridad = doc_seguridad
        estructura_lopd.save()
    except:
        estructura_lopd = Estructura_lopd.objects.create(entidad=g_e.ronda.entidad, doc_seguridad=doc_seguridad,
                                                         encargado_tratamiento="Sistemas de Gestión Aumentada (NIF: 18034131S)")
    if request.method == 'POST':
        if request.POST['action'] == 'genera_pdf':
            crear_aviso(request, True, request.META['PATH_INFO'] + ' POST genera PDF del documento de seguridad')

            fichero = 'Documento_Seguridad_%s' % (g_e.ronda.entidad.id)
            fich = html_to_pdf(request, doc_seguridad, fichero=fichero, media=MEDIA_LOPD, title=u'Doc_Seguridad',
                               tipo='doc')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response

    return render(request, "documento_seguridad.html",
                              {
                                  'formname': 'documento_seguridad',
                                  'iconos':
                                      ({'nombre': 'file-pdf-o', 'texto': 'PDF',
                                        'title': 'Generar PDF del documento', 'permiso': 'm70'},),
                                  'estructura_lopd': estructura_lopd,
                                  'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                                 aceptado=False),
                              })


# --------------------------------------------------------------------------------#

@login_required()
def derechos_arco(request):
    g_e = request.session["gauser_extra"]
    doc_seguridad = render_to_string('doc_seguridad_general.html', {}, request=request)
    try:
        estructura_lopd = Estructura_lopd.objects.get(entidad=g_e.ronda.entidad)
        estructura_lopd.doc_seguridad = doc_seguridad
        estructura_lopd.save()
    except:
        estructura_lopd = Estructura_lopd.objects.create(entidad=g_e.ronda.entidad, doc_seguridad=doc_seguridad,
                                                         encargado_tratamiento="Sistemas de Gestión Aumentada (NIF: 18034131S)")
    if request.method == 'POST':
        if request.POST['action'] == 'aceptar':
            tipo = request.POST['derecho']
            tipos_incidencia = dict(TIPOS_INCIDENCIA)
            texto_html = {
                'DEAC': render_to_string('derecho_acceso.html', {'estructura_lopd': estructura_lopd, },
                                         request=request),
                'DERE': render_to_string('derecho_rectificacion.html',
                                         {'estructura_lopd': estructura_lopd,
                                          'datos_rectificar': request.POST['datos_rectificar']},
                                         request=request),
                'DECA': render_to_string('derecho_cancelacion.html', {'estructura_lopd': estructura_lopd, },
                                         request=request),
                'DEOP': render_to_string('derecho_oposicion.html', {'estructura_lopd': estructura_lopd, },
                                         request=request)}
            crear_aviso(request, True, request.META['PATH_INFO'] + ' Ejerce derecho de ' + tipo)
            incidencia = Incidencia_lopd.objects.create(emisor_incidencia=g_e, tipo=tipo, incidencia=texto_html[tipo])
            for input_file, object_file in request.FILES.items():
                for fichero in request.FILES.getlist(input_file):
                    archivo = Fichero_incidencia.objects.create(propietario=g_e, fichero=fichero)
                    incidencia.ficheros.add(archivo)

            fichero = 'Incidencia_%s' % (incidencia.id)
            attach = ''
            for archivo in incidencia.ficheros.all():
                attach += MEDIA_INCIDENCIAS_LOPD + str(g_e.ronda.entidad.code) + '/' + archivo.filename() + ' '
            fich = html_to_pdf(request, texto_html[tipo], fichero=fichero,
                               media=MEDIA_INCIDENCIAS_LOPD + str(g_e.ronda.entidad.code) + '/',
                               title=u'Incidencia LOPD generada por %s' % (g_e.gauser.get_full_name()),
                               attach=attach)

            doc = Ges_documental.objects.create(propietario=g_e, nombre='Incidencia: %s' % (tipos_incidencia[tipo]),
                                                texto=texto_html[tipo], fichero=File(fich),
                                                content_type='application/pdf')
            cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad, nivel__in=[1, 2])
            doc.cargos.add(*cargos)
            fich.close()

    return render(request, "derechos_arco.html",
                              {
                                  'formname': 'derechos_arco',
                                  'iconos':
                                      ({'nombre': 'check', 'texto': 'Aceptar',
                                        'title': 'Enviar la solicitud a los interesados', 'permiso': 'm70i20'},),
                                  'estructura_lopd': estructura_lopd,
                                  'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                                 aceptado=False),
                              })


# --------------------------------------------------------------------------------#

@login_required()
def incidencias_lopd(request):
    g_e = request.session["gauser_extra"]
    incidencias = Incidencia_lopd.objects.filter(emisor_incidencia__ronda=g_e.ronda, resuelta=False).order_by(
        '-fecha_emite')
    incidencias_solved = Incidencia_lopd.objects.filter(emisor_incidencia__ronda=g_e.ronda, resuelta=True).order_by(
        '-fecha_emite')
    estructura_lopd = Estructura_lopd.objects.filter(entidad=g_e.ronda.entidad)
    form_emitir = Incidencia_lopdForm()
    form_resolver = ResuelveIncidencia_lopdForm()
    if request.method == 'POST':
        if request.POST['action'] == 'graba_incidencia':
            incidencia = Incidencia_lopd(emisor_incidencia=g_e)
            form = Incidencia_lopdForm(request.POST, instance=incidencia)
            if form.is_valid():
                form.save()
                crear_aviso(request, True, request.META['PATH_INFO'] + ' Se graba una nueva incidencia LOPD')
            else:
                crear_aviso(request, False, form.errors)

        if request.POST['action'] == 'resuelve_incidencia':
            incidencia = Incidencia_lopd.objects.get(id=request.POST['id_incidencia'])
            form = ResuelveIncidencia_lopdForm(request.POST, instance=incidencia)
            if form.is_valid():
                form.save()
                incidencia.resuelta = True
                incidencia.resolvedor = g_e
                incidencia.fecha_resuelve = datetime.date.today()
                incidencia.save()
                crear_aviso(request, True, request.META['PATH_INFO'] + ' Se graba una nueva incidencia LOPD')
            else:
                crear_aviso(request, False, form.errors)

        if request.POST['action'] == 'mostrar_incidencia':
            if request.is_ajax():
                incidencia = Incidencia_lopd.objects.get(id=request.POST['id_incidencia'])
                return HttpResponse(incidencia.incidencia)

    return render(request, "incidencias_lopd.html",
                              {
                                  'formname': 'documento_seguridad',
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                                        'permiso': 'm70', 'title': 'Guardar los cambios realizados'},
                                       {'tipo': 'button', 'nombre': 'plus', 'texto': 'Anadir',
                                        'permiso': 'm70', 'title': 'Añadir una nueva incidencia LOPD'},
                                       {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                                        'permiso': 'resuelve_incidencias_lopd',
                                        'title': 'Eliminar la incidencia seleccionada'},
                                       {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Lista', 'permiso': 'm70',
                                        'title': 'Volver a mostrar la lista de incidencias'},
                                      ),
                                  'form_emitir': form_emitir,
                                  'estructura_lopd': estructura_lopd,
                                  'form_resolver': form_resolver,
                                  'incidencias': incidencias,
                                  'incidencias_solved': incidencias_solved,
                                  'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                                 aceptado=False),
                              })


@permiso_required('acceso_inventario_soportes')
def inventario_soportes(request):
    g_e = request.session['gauser_extra']
    form = Soporte_lopdForm()
    if request.method == 'POST':
        if request.POST['action'] == 'guardar_soporte':
            soporte = Soporte_lopd(entidad=g_e.ronda.entidad)
            form = Soporte_lopdForm(request.POST, instance=soporte)
            if form.is_valid():
                soporte = form.save()
                crear_aviso(request, True, u'Soporte guardado: %s' % (soporte.nombre))
            else:
                crear_aviso(request, False, form.errors)

        if request.POST['action'] == 'borrar_soporte':
            soportes_id = request.POST['id_soporte'].split(',')
            soportes = Soporte_lopd.objects.filter(id__in=soportes_id)
            for soporte in soportes:
                if g_e.has_cargos([1, 2]):
                    soporte.delete()
                    crear_aviso(request, True, u'Se borra soporte: %s' % (soporte.nombre))
                else:
                    crear_aviso(request, False,
                                u'No tienes permisos para borrar el soporte: %s.' % (soporte.nombre))

    soportes = Soporte_lopd.objects.filter(entidad=g_e.ronda.entidad).order_by('-creado')
    return render(request, "soportes_lopd.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                                        'permiso': 'modifica_inventario_soportes', 'title': 'Grabar el soporte introducido'},
                                       {'tipo': 'button', 'nombre': 'plus', 'texto': 'Anadir',
                                        'permiso': 'modifica_inventario_soportes', 'title': 'Anadir un nuevo soporte'},
                                       {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                                        'permiso': 'modifica_inventario_soportes',
                                        'title': 'Eliminar el soporte seleccionado'},
                                       {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Lista', 'permiso': 'modifica_inventario_soportes',
                                        'title': 'Volver a mostrar la lista de soportes'},
                                      ),
                                  'form': form,
                                  'formname': 'soportes',
                                  'soportes': soportes,
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                              })


def confidencialidad(request):
    g_e = request.session["gauser_extra"]
    doc_seguridad = render_to_string('doc_seguridad_general.html', {}, request=request)
    try:
        estructura_lopd = Estructura_lopd.objects.get(entidad=g_e.ronda.entidad)
        estructura_lopd.doc_seguridad = doc_seguridad
        estructura_lopd.save()
    except:
        estructura_lopd = Estructura_lopd.objects.create(entidad=g_e.ronda.entidad, doc_seguridad=doc_seguridad,
                                                         encargado_tratamiento="Sistemas de Gestión Aumentada (NIF: 18034131S)")
    if request.method == 'POST':
        if request.POST['action'] == 'aceptar':
            tipo = request.POST['contrato']
            texto_html = {
                'CONF': render_to_string('confidencialidad_personal.html', {'estructura_lopd': estructura_lopd, },
                                         request=request)}
            crear_aviso(request, True, request.META['PATH_INFO'] + ' Firma contrato de confidencialidad')

            fichero = 'Contrato_%s_%s' % (tipo, g_e.gauser.username)
            fich = html_to_pdf(request, texto_html[tipo], fichero=fichero,
                               media=MEDIA_LOPD + str(g_e.ronda.entidad.code) + '/',
                               title=u'Firma de confidencialidad de %s' % (g_e.gauser.get_full_name()))

            doc = Ges_documental.objects.create(propietario=g_e,
                                                nombre='Contrato de confidencialidad de %s' % (
                                                g_e.gauser.get_full_name()),
                                                texto=texto_html[tipo], fichero=File(fich),
                                                content_type='application/pdf')
            cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad, nivel__in=[1, 2])
            doc.cargos.add(*cargos)
            fich.close()

    return render(request, "contratos_confidencialidad.html",
                              {
                                  'formname': 'confidencialidad',
                                  'iconos':
                                      ({'nombre': 'check', 'texto': 'Aceptar',
                                        'title': 'Enviar la solicitud a los interesados', 'permiso': 'm70i20'},),
                                  'estructura_lopd': estructura_lopd,
                                  'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                                                 aceptado=False),
                              })

