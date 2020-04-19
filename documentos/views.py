# coding=utf-8
# Create your views here.
import os
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.timezone import datetime
from django.template import RequestContext
from django.template.loader import render_to_string
import simplejson as json
from django.db.models import Q
from autenticar.control_acceso import permiso_required
from entidades.views import decode_selectgcs
from documentos.forms import Ges_documentalForm, Contrato_gaussForm
from documentos.models import Ges_documental, Contrato_gauss, Etiqueta_documental, Compartir_Ges_documental, Permiso_Ges_documental
from gauss.funciones import html_to_pdf
from gauss.rutas import MEDIA_DOCUMENTOS, MEDIA_ANAGRAMAS, RUTA_BASE
from mensajes.models import Aviso
from mensajes.views import crear_aviso


def documentos_ge(g_e):
    q = Q(subentidad__in=g_e.subentidades.all()) | Q(cargo__in=g_e.cargos.all()) | Q(gauser=g_e.gauser)
    docs_id = Compartir_Ges_documental.objects.filter(q).values_list('documento__id', flat=True)
    return Ges_documental.objects.filter(id__in=docs_id).distinct()

# @permiso_required('acceso_documentos')
def documentos(request):
    g_e = request.session['gauser_extra']
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'ver_formulario_subir' and g_e.has_permiso('sube_archivos'):
            try:
                etiquetas = Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad)
                html = render_to_string("documentos_fieldset_subir.html", {'etiquetas': etiquetas})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_crear_etiqueta' and g_e.has_permiso('crea_carpetas'):
            try:
                etiquetas = Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad)
                html = render_to_string("documentos_fieldset_etiqueta.html", {'etiquetas': etiquetas})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_editar_carpeta' and g_e.has_permiso('edita_carpetas'):
            try:
                etiquetas = Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad)
                e = Etiqueta_documental.objects.get(id=request.POST['etiqueta'])
                html = render_to_string("documentos_fieldset_etiqueta_editar.html",
                                        {'etiquetas': etiquetas, 'etiqueta': e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'modifica_etiqueta' and g_e.has_permiso('edita_carpetas'):
            try:
                nombre = request.POST['nombre']
                try:
                    Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, nombre__iexact=nombre)
                    return JsonResponse({'ok': False, 'mensaje': 'Ya existe una etiqueta/carpeta con ese nombre.'})
                except:
                    e = Etiqueta_documental.objects.get(id=request.POST['etiqueta'])
                    e.nombre = nombre
                    try:
                        e.padre = Etiqueta_documental.objects.get(id=request.POST['padre'])
                    except:
                        e.padre = None
                    e.save()
                    docs = documentos_ge(g_e)
                    html = render_to_string('documentos_table_tr.html', {'docs': docs, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_buscar':
            try:
                etiquetas = Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad)
                html = render_to_string("documentos_fieldset_buscar.html", {'etiquetas': etiquetas, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'crea_etiqueta' and g_e.has_permiso('crea_carpetas'):
            try:
                nombre = request.POST['nombre']
                try:
                    Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, nombre__iexact=nombre)
                    return JsonResponse({'ok': False, 'mensaje': 'Ya existe una etiqueta/carpeta con ese nombre.'})
                except:
                    if request.POST['padre']:
                        padre = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['padre'])
                        Etiqueta_documental.objects.create(entidad=g_e.ronda.entidad, padre=padre, nombre=nombre)
                    else:
                        Etiqueta_documental.objects.create(entidad=g_e.ronda.entidad, nombre=nombre)
                    return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borra_etiqueta' and g_e.has_permiso('borra_cualquier_carpeta'):
            try:
                Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['etiqueta']).delete()
                docs = documentos_ge(g_e)
                html = render_to_string('documentos_table_tr.html', {'docs': docs, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'busca_docs_manual':
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
                    etiqueta = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['etiqueta'])
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
                docs = documentos_ge(g_e)
                docs_search = docs.filter(q)
                html = render_to_string('documentos_table_tr.html', {'docs': docs_search, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_editar':
            try:
                doc = Ges_documental.objects.get(id=request.POST['doc'])
                if g_e.has_permiso('edita_todos_archivos') or 'w' in doc.permisos(g_e):
                    etiquetas = Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad)
                    payload = {'g_e': g_e, 'etiquetas': etiquetas, 'd': doc}
                    html = render_to_string("documentos_table_tr_archivo_edit.html", payload)
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_archivo':
            try:
                valor = request.POST['valor']
                campo = request.POST['campo']
                if request.POST['modelo'] == 'Ges_documental':
                    doc = Ges_documental.objects.get(id=request.POST['id'])
                    permisos_ge = doc.permisos(g_e)
                    if 'w' in permisos_ge or 'x' in permisos_ge:
                        if campo == 'etiqueta':
                            valor_campo = Etiqueta_documental.objects.get(id=valor, entidad=g_e.ronda.entidad)
                        else:
                            valor_campo = valor
                        setattr(doc, campo, valor_campo)
                        doc.save()
                        return JsonResponse({'ok': True})
                else:
                    cgd = Compartir_Ges_documental.objects.get(id=request.POST['id'])
                    doc = cgd.documento
                    if valor in doc.permisos(g_e):
                        cgd.permiso = valor
                        cgd.save()
                        return JsonResponse({'ok': True})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_documento':
            doc = Ges_documental.objects.get(id=request.POST['doc'])
            if 'x' in doc.permisos(g_e):
                try:
                    Compartir_Ges_documental.objects.filter(documento=doc, gauser=g_e.gauser).delete()
                    m = 'Se ha borrado tu acceso personal al archivo.<br>Si todavía lo ves es porque tienes acceso a él porque está compartido con un cargo que tienes asignado o una sección/departamento al que perteneces.'
                    return JsonResponse({'ok': True, 'mensaje': m})
                except:
                    m = 'Archivo no borrado. <br>Lo sigues viendo porque está compartido con un cargo que tienes asignado o una sección/departamento al que perteneces.'
                    return JsonResponse({'ok': True, 'mensaje': m})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No ha sido posible borrar el documento.'})
        elif request.POST['action'] == 'borrar_doc_completamente':
            doc = Ges_documental.objects.get(id=request.POST['doc'])
            if g_e.has_permiso('borra_cualquier_archivo'):
                Compartir_Ges_documental.objects.filter(documento=doc).delete()
                try:
                    os.remove(doc.fichero.path)
                    doc.delete()
                except:
                    doc.delete()
                return JsonResponse({'ok': True, 'mensaje': 'Documento borrado por completo.'})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para borrar el documento.'})
        elif request.POST['action'] == 'borrar_doc_completamente':
            doc = Ges_documental.objects.get(id=request.POST['doc'])
            if g_e.has_permiso('borra_cualquier_archivo'):
                Compartir_Ges_documental.objects.filter(documento=doc).delete()
                try:
                    os.remove(doc.fichero.path)
                    doc.delete()
                except:
                    doc.delete()
                return JsonResponse({'ok': True, 'mensaje': 'Documento borrado por completo.'})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para borrar el documento.'})
        elif request.POST['action'] == 'borrar_doc_completamente':
            doc = Ges_documental.objects.get(id=request.POST['doc'])
            if g_e.has_permiso('borra_cualquier_archivo'):
                Compartir_Ges_documental.objects.filter(documento=doc).delete()
                try:
                    os.remove(doc.fichero.path)
                    doc.delete()
                except:
                    doc.delete()
                return JsonResponse({'ok': True, 'mensaje': 'Documento borrado por completo.'})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para borrar el documento.'})
        elif request.POST['action'] == 'update_new_permiso':
            doc = Ges_documental.objects.get(id=request.POST['doc'])
            if 'w' in doc.permisos(g_e):
                ges, cs, ss = decode_selectgcs([request.POST['seleccionados']], g_e.ronda)
                for ge in ges:
                    Compartir_Ges_documental.objects.get_or_create(documento=doc, gauser=ge.gauser)
                for c in cs:
                    Compartir_Ges_documental.objects.get_or_create(documento=doc, cargo=c)
                for s in ss:
                    Compartir_Ges_documental.objects.get_or_create(documento=doc, subentidad=s)
                html = render_to_string("documentos_table_tr_archivo_edit_permisos.html", {'d': doc})
                return JsonResponse({'ok': True, 'html': html, 'doc': doc.id})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para compartir el archivo.'})
        elif request.POST['action'] == 'borrar_permiso_archivo':
            cgd = Compartir_Ges_documental.objects.get(id=request.POST['cgd'])
            doc = cgd.documento
            if 'w' in doc.permisos(g_e):
                cgd.delete()
                return JsonResponse({'ok': True, 'cgd': request.POST['cgd']})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para borrar compartido.'})
        elif request.POST['action'] == 'fieldset_archivo_editar_close':
            doc = Ges_documental.objects.get(id=request.POST['doc'])
            if 'w' in doc.permisos(g_e):
                html = render_to_string('documentos_table_tr_archivo.html', {'d': doc, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html, 'doc': doc.id})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para borrar compartido.'})
        else:
            return JsonResponse({'ok': False, 'mensaje': 'Solicitud incorrecta.'})

    elif request.method == 'POST':
        if request.POST['action'] == 'sube_archivo':
            n_files = int(request.POST['n_files'])
            if g_e.has_permiso('sube_archivos'):
                try:
                    for i in range(n_files):
                        fichero = request.FILES['fichero_xhr' + str(i)]
                        try:
                            etiqueta = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad,
                                                                       id=request.POST['etiqueta'])
                        except:
                            etiqueta, c = Etiqueta_documental.objects.get_or_create(entidad=g_e.ronda.entidad,
                                                                                    nombre='General')
                        doc = Ges_documental.objects.create(propietario=g_e, content_type=fichero.content_type,
                                                            etiqueta=etiqueta, nombre=fichero.name, fichero=fichero)
                        Compartir_Ges_documental.objects.create(gauser=g_e.gauser, documento=doc, permiso='rwx')
                        html = render_to_string('documentos_table_tr.html', {'docs': [doc], 'g_e': g_e})
                        return JsonResponse({'ok': True, 'html': html, 'mensaje': False})
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
            else:
                mensaje = 'No tienes permiso para cargar programaciones.'
                return JsonResponse({'ok': False, 'mensaje': mensaje})

        elif request.POST['action'] == 'descargar_doc':
            try:
                docs = documentos_ge(g_e)
                d = docs.get(id=request.POST['documento'])
                fichero = d.fichero.read()
                response = HttpResponse(fichero, content_type=d.content_type)
                response['Content-Disposition'] = 'attachment; filename=' + d.fich_name
                return response
            except:
                crear_aviso(request, False, 'Error. No se ha podido descargar el archivo.')

    # -----------
    for d in Ges_documental.objects.all():
        for sub in d.acceden.all():
            Compartir_Ges_documental.objects.get_or_create(subentidad=sub, documento=d)
        for car in d.cargos.all():
            Compartir_Ges_documental.objects.get_or_create(cargo=car, documento=d)
        for p in d.permiso_ges_documental_set.all():
            c, v = Compartir_Ges_documental.objects.get_or_create(gauser=p.gauser, documento=d)
            if 'x' in p.permiso:
                c.permiso = 'rwx'
            elif 'w' in p.permiso:
                c.permiso = 'rw'
            else:
                c.permiso = 'r'
            c.save()
    # -----------
    Etiqueta_documental.objects.get_or_create(entidad=g_e.ronda.entidad, nombre='General')
    return render(request, "documentos.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'permiso': 'sube_archivos', 'title': 'Anadir un nuevo documento'},
                           {'tipo': 'button', 'nombre': 'folder', 'texto': 'Nueva', 'permiso': 'crea_carpetas',
                            'title': 'Crear una nueva carpeta/etiqueta'},
                           {'tipo': 'button', 'nombre': 'search', 'texto': 'Buscar/Filtrar',
                            'permiso': 'libre',
                            'title': 'Busca/Filtra resultados entre los diferentes archivos'},
                           ),
                      'g_e': g_e,
                      'docs': documentos_ge(g_e),
                      'formname': 'documentos',
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


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
                crear_aviso(request, True,
                            u'Modificación del contrato de la entidad %s guardada.' % (g_e.ronda.entidad.name))
            else:
                crear_aviso(request, False, form.errors)

        if request.POST['action'] == 'subir_contrato' and g_e.has_permiso('puede_subir_contrato'):
            contrato.content_type = request.FILES['fichero'].content_type
            # contrato.save()
            # a = request.FILES['fichero'].content_type
            form = Contrato_gaussForm(request.POST, request.FILES, instance=contrato)
            if form.is_valid():
                contrato = form.save()
                crear_aviso(request, True,
                            u'Se ha subido el contrato escaneado de la entidad %s.' % (g_e.ronda.entidad.name))
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
