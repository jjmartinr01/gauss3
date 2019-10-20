# coding=utf-8
# Create your views here.
import os
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext
from django.template.loader import render_to_string
import simplejson as json
from django.db.models import Q
from autenticar.control_acceso import permiso_required
from autenticar.models import Gauser
from entidades.models import Subentidad, Gauser_extra
from documentos.forms import Ges_documentalForm, Contrato_gaussForm
from documentos.models import Ges_documental, Contrato_gauss, Permiso_Ges_documental, Etiqueta_documental
from gauss.funciones import html_to_pdf
from gauss.rutas import MEDIA_DOCUMENTOS, MEDIA_ANAGRAMAS, RUTA_BASE
from mensajes.models import Aviso
from mensajes.views import crear_aviso


@permiso_required('acceso_documentos')
def documentos(request):
    g_e = request.session['gauser_extra']
    form = Ges_documentalForm(g_e=g_e)
    if request.method == 'POST':
        if request.POST['action'] == 'guardar_documento':
            if 'fichero' in request.FILES:
                file_content = request.FILES['fichero'].content_type
            else:
                file_content = None
            ges_doc = Ges_documental(propietario=g_e, fich_name='No hay archivo asociado', content_type=file_content)
            form = Ges_documentalForm(request.POST, request.FILES, instance=ges_doc, g_e=g_e)
            if form.is_valid():
                ges_doc = form.save()
                Permiso_Ges_documental.objects.create(gauser=g_e.gauser, documento=ges_doc, permiso='x')
                ids = map(str, filter(None, request.POST['invitados'].split(',')))  # filter elimina elementos vacíos
                for invitado_id in ids:
                    g_id = invitado_id.split('_')
                    g = Gauser.objects.get(id=g_id[0])
                    Permiso_Ges_documental.objects.create(gauser=g, documento=ges_doc, permiso=g_id[1])
                crear_aviso(request, True, u'Documento guardado: %s' % (ges_doc.nombre))
                form = Ges_documentalForm(g_e=g_e)
            else:
                crear_aviso(request, False, form.errors)

        if request.POST['action'] == 'guardar_modificacion':
            if 'fichero' in request.FILES:
                file_content = request.FILES['fichero'].content_type
            else:
                file_content = None
            ges_doc = Ges_documental.objects.get(id=request.POST['id_documento'])
            form = Ges_documentalForm(request.POST, request.FILES, instance=ges_doc, g_e=ges_doc.propietario)
            if form.is_valid():
                ges_doc = form.save()
                ges_doc.file_content = file_content
                ges_doc.save()
                ids = map(str, filter(None, request.POST['invitados'].split(',')))  # filter elimina elementos vacíos
                for invitado_id in ids:
                    g_id = invitado_id.split('_')
                    g = Gauser.objects.get(id=g_id[0])
                    try:
                        p = Permiso_Ges_documental.objects.get(gauser=g, documento=ges_doc)
                        p.permiso = g_id[1]
                        p.save()
                    except:
                        Permiso_Ges_documental.objects.create(gauser=g, documento=ges_doc, permiso=g_id[1])
                crear_aviso(request, True, u'Documento modificado: %s' % (ges_doc.nombre))
                form = Ges_documentalForm(g_e=g_e)
            else:
                crear_aviso(request, False, form.errors)

        if request.POST['action'] == 'download_documento':
            documentos_id = request.POST['id_documento'].split(',')
            documentos = Ges_documental.objects.filter(id__in=documentos_id)
            fichero = documentos[0].fichero.read()
            response = HttpResponse(fichero, content_type=documentos[0].content_type)
            response['Content-Disposition'] = 'attachment; filename=' + documentos[0].fich_name
            return response

    return render(request, "documentos.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                                        'permiso': 'sube_archivos', 'title': 'Grabar el documento introducido'},
                                       {'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                                        'permiso': 'sube_archivos', 'title': 'Anadir un nuevo documento'},
                                       {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                                        'permiso': 'borra_cualquier_archivo',
                                        'title': 'Eliminar el documento seleccionado'},
                                       {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Lista', 'permiso': 'acceso_documentos',
                                        'title': 'Volver a mostrar la lista de documentos'},
                                       {'tipo': 'button', 'nombre': 'pencil', 'texto': 'Editar', 'permiso': 'edita_todos_archivos',
                                        'title': 'Editar el documento'},
                                       {'tipo': 'button', 'nombre': 'folder', 'texto': 'Nueva', 'permiso': 'crea_carpetas',
                                        'title': 'Crear una nueva carpeta/etiqueta'},
                                      ),
                                  'form': form,
                                  'carpetas': Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad),
                                  'formname': 'documentos',
                                  'carpeta_id': 'todas',  # Este identificador implica leer todas las carpetas
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                              })


@login_required()
def documentos_ajax(request):
    g_e = request.session['gauser_extra']
    data = None
    if request.is_ajax():
        if request.method == 'POST':
            if request.POST['action'] == 'contenido_documento':
                documento = Ges_documental.objects.get(id=json.loads(request.POST['id']))
                invitados = Permiso_Ges_documental.objects.filter(documento=documento)
                data = render_to_string('contenido_observaciones_documento.html',
                                        {'documento': documento, 'invitados': invitados},
                                        request=request)
            if request.POST['action'] == 'crear_formulario':
                form = Ges_documentalForm(g_e=g_e)
                data = render_to_string('add_documento.html', {'form': form},
                                        request=request)
            if request.POST['action'] == 'editar_documento':
                try:
                    documento = Ges_documental.objects.get(id=request.POST['id'])
                    invitados_permiso = Permiso_Ges_documental.objects.filter(documento=documento)
                    acceden = documento.acceden.all()
                    keys = ('id', 'text')
                    permisos = {'r': '(lectura)', 'w': '(lectura y escritura)', 'x': '(lectura, escritura y borrado)'}
                    invitados = json.dumps([dict(zip(keys, ("%s_%s" % (row.gauser.id, row.permiso), "%s, %s %s" % (
                        row.gauser.last_name, row.gauser.first_name, permisos[row.permiso])))) for row in
                                            invitados_permiso])
                    subentidades = json.dumps([dict(zip(keys, (row.id, "%s" % (row.nombre)))) for row in acceden])
                    p = Permiso_Ges_documental.objects.get(gauser=g_e.gauser, documento=documento)
                    if p.permiso != 'r':
                        form = Ges_documentalForm(g_e=g_e, instance=documento)
                        data = render_to_string('add_documento.html',
                                                {'form': form, 'invitados': invitados, 'subentidades': subentidades},
                                                request=request)
                except:
                    data = None
            if request.POST['action'] == 'documentos_carpeta':
                data = render_to_string('list_documentos.html', {'carpeta_id': request.POST['carpeta_id']},
                                        request=request)
            if request.POST['action'] == 'crear_carpeta':
                etiqueta = Etiqueta_documental.objects.create(entidad=g_e.ronda.entidad, nombre=request.POST['nombre'])
                carpeta = render_to_string('carpeta_nueva.html', {'carpeta': etiqueta})
                data = json.dumps({
                    'carpeta': carpeta,
                    'id': etiqueta.id,
                })
                return HttpResponse(data, content_type='application/json')
            if request.POST['action'] == 'modificar_carpeta':
                carpeta = Etiqueta_documental.objects.get(id=request.POST['id'])
                carpeta.nombre = request.POST['nombre']
                carpeta.save()
            if request.POST['action'] == 'borrar_carpeta':
                carpeta = Etiqueta_documental.objects.get(id=request.POST['id'])
                carpeta.delete()  # borra los documentos contenidos en la carpeta/etiqueta
            if request.POST['action'] == 'borrar_documento':
                documento = Ges_documental.objects.get(id=request.POST['id'])
                nombre = documento.nombre
                try:
                    p = Permiso_Ges_documental.objects.get(gauser=g_e.gauser, documento=documento)
                    if p.permiso == 'x' or g_e.has_permiso('borra_cualquier_archivo'):
                        documento.delete()
                        crear_aviso(request, True, 'Documento borrado de la base de datos.')
                        data = 'El documento "%s" ha sido borrado de la base de datos.' % (nombre)
                    elif p.permiso == 'w':
                        p.delete()
                        crear_aviso(request, True, 'Acceso a documento eliminado.')
                        data = 'El acceso al documento "%s" ha sido eliminado.' % (nombre)
                except:
                    crear_aviso(request, True, 'Intento fallido de eliminar un documento.')
                    data = 'No tienes permiso para eliminar el documento "%s".' % (nombre)

            return HttpResponse(data)

        if request.method == 'GET':
            if request.GET['action'] == 'invitados':
                texto = request.GET['q']
                socios = Gauser_extra.objects.filter(ronda=g_e.ronda)
                socios_contain_texto = socios.filter(
                    Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)).values_list(
                    'gauser__id',
                    'gauser__last_name',
                    'gauser__first_name')
                keys = ('id', 'text')
                r = [dict(zip(keys, ('%s_r' % row[0], '%s, %s (lectura)' % (row[1], row[2])))) for row in
                     socios_contain_texto]
                w = [dict(zip(keys, ('%s_w' % row[0], '%s, %s (lectura y escritura)' % (row[1], row[2])))) for row in
                     socios_contain_texto]
                x = [dict(zip(keys, ('%s_x' % row[0], '%s, %s (lectura, escritura y borrado)' % (row[1], row[2])))) for
                     row in socios_contain_texto]
                z = r + w + x
                return HttpResponse(json.dumps(z))

                # keys = ('id', 'text')
                # return HttpResponse(json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in socios_contain_texto]))


@login_required()
def contrato_gauss(request):
    g_e = request.session['gauser_extra']
    try:
        contrato = Contrato_gauss.objects.get(entidad=g_e.ronda.entidad)
    except:
        Gn = g_e.ronda.entidad.get__general_name__display()
        La_entidad = 'La %s' % (Gn) if g_e.ronda.entidad.general_name < 100 else 'El %s' % (Gn)
        la_entidad = 'la %s' % (Gn) if g_e.ronda.entidad.general_name < 100 else 'el %s' % (Gn)
        a_la_entidad = 'a la %s' % (Gn) if g_e.ronda.entidad.general_name < 100 else 'al %s' % (Gn)
        de_la_entidad = 'de la %s' % (Gn) if g_e.ronda.entidad.general_name < 100 else 'del %s' % (Gn)

        texto = render_to_string("texto_contrato_gauss.html", {'Gn': Gn, 'La_entidad': La_entidad,
                                                               'la_entidad': la_entidad, 'de_la_entidad': de_la_entidad,
                                                               'a_la_entidad': a_la_entidad})
        contrato = Contrato_gauss.objects.create(entidad=g_e.ronda.entidad, firma_entidad=g_e, texto=texto)
    if request.method == 'POST':
        if request.POST['action'] == 'guardar_modificaciones' and g_e.has_permiso('guarda_modificaciones_contrato'):
            form = Contrato_gaussForm(request.POST, instance=contrato)
            if form.is_valid():
                contrato = form.save()
                crear_aviso(request, True, u'Modificación del contrato de la entidad %s guardada.' % (g_e.ronda.entidad.name))
            else:
                crear_aviso(request, False, form.errors)

        if request.POST['action'] == 'subir_contrato' and g_e.has_permiso('puede_subir_contrato'):
            contrato.content_type = request.FILES['fichero'].content_type
            # contrato.save()
            # a = request.FILES['fichero'].content_type
            form = Contrato_gaussForm(request.POST, request.FILES, instance=contrato)
            if form.is_valid():
                contrato = form.save()
                crear_aviso(request, True, u'Se ha subido el contrato escaneado de la entidad %s.' % (g_e.ronda.entidad.name))
            else:
                crear_aviso(request, False, form.errors)

        if request.POST['action'] == 'bajar_contrato':
            contrato = Contrato_gauss.objects.get(entidad=g_e.ronda.entidad)
            try:
                fichero = contrato.fichero.read()
                response = HttpResponse(fichero, content_type=contrato.content_type)
                response['Content-Disposition'] = 'attachment; filename=Contrato_gauss.' + \
                                                  contrato.fichero.url.split('.')[-1]
                return response
            except:
                crear_aviso(request, False, u'Todavía no se ha subido un archivo con el contrato escaneado.')

        if request.POST['action'] == 'obtener_pdf':
            contrato = Contrato_gauss.objects.get(entidad=g_e.ronda.entidad)

            fichero = 'Contrato_GAUSS_sin_firmar'
            c = render_to_string('contrato_gauss2pdf.html', {'contrato': contrato, 'MA': MEDIA_ANAGRAMAS},
                                 request=request)
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_DOCUMENTOS, title=u'Contrato GAUSS')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response

    form = Contrato_gaussForm(instance=contrato)
    return render(request, "contrato_gauss.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF',
                                        'permiso': 'descarga_contrato_pdf', 'title': 'Obtener PDF del contrato'},
                                       {'tipo': 'button', 'nombre': 'upload', 'texto': 'Subir',
                                        'permiso': 'puede_subir_contrato',
                                        'title': 'Subir el contrato escaneado con firmas'},
                                       {'tipo': 'button', 'nombre': 'download', 'texto': 'Descargar',
                                        'permiso': 'puede_descargar_contrato',
                                        'title': 'Descargar el contrato escaneado con firmas'},
                                       {'tipo': 'button', 'nombre': 'check', 'texto': 'Guardar',
                                        'permiso': 'guarda_modificaciones_contrato',
                                        'title': 'Guardar modificaciones del contrato'},
                                      ),
                                  'form': form,
                                  'formname': 'contrato_gauss',
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                              })


def presentaciones(request):
    if request.method == 'GET':
        if request.GET['id'] == 'xhtsl45':
            return render(request, "presentacion_funcion_directiva_1_3.html")
        else:
            return render(request, "no_enlace.html")
    else:
        return render(request, "no_enlace.html")

