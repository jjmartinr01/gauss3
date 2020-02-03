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
from autenticar.models import Gauser
from entidades.models import Subentidad, Gauser_extra, Cargo
from documentos.forms import Ges_documentalForm, Contrato_gaussForm
from documentos.models import Ges_documental, Contrato_gauss, Permiso_Ges_documental, Etiqueta_documental
from gauss.funciones import html_to_pdf
from gauss.rutas import MEDIA_DOCUMENTOS, MEDIA_ANAGRAMAS, RUTA_BASE
from mensajes.models import Aviso
from mensajes.views import crear_aviso


@permiso_required('acceso_documentos')
def documentos_antiguo(request):
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


# @permiso_required('acceso_documentos')
def documentos(request):
    g_e = request.session['gauser_extra']
    form = Ges_documentalForm(g_e=g_e)
    pgds = Permiso_Ges_documental.objects.filter(documento__propietario__ronda__entidad=g_e.ronda.entidad,
                                                 gauser=g_e.gauser).values_list('documento__id', flat=True)
    q = Q(acceden__in=g_e.subentidades.all()) | Q(cargos__in=g_e.cargos.all()) | Q(id__in=pgds) | Q(propietario=g_e)
    docs = Ges_documental.objects.filter(Q(propietario__ronda__entidad=g_e.ronda.entidad), q).distinct()
    etiquetas = Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad)
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'ver_formulario_subir' and g_e.has_permiso('sube_archivos'):
            try:
                html = render_to_string("documentos_fieldset_subir.html", {'etiquetas': etiquetas})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_crear_etiqueta' and g_e.has_permiso('crea_carpetas'):
            try:
                html = render_to_string("documentos_fieldset_etiqueta.html", {'etiquetas': etiquetas})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_buscar':
            try:
                html = render_to_string("documentos_fieldset_buscar.html", {'etiquetas': etiquetas, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'crea_etiqueta' and g_e.has_permiso('crea_carpetas'):
            try:
                nombre = request.POST['nombre']
                if request.POST['padre']:
                    padre = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['padre'])
                    Etiqueta_documental.objects.create(entidad=g_e.ronda.entidad, padre=padre, nombre=nombre)
                else:
                    Etiqueta_documental.objects.create(entidad=g_e.ronda.entidad, nombre=nombre)
                return JsonResponse({'ok': True})
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
                        nombre__icontains=texto) & Q(etiqueta=etiqueta)
                else:
                    q = Q(propietario__ronda__entidad=g_e.ronda.entidad) & Q(
                        creado__gte=inicio) & Q(creado__lte=fin) & Q(
                        nombre__icontains=texto)

                docs_search = docs.filter(q)
                html = render_to_string('documentos_table_tr.html', {'docs': docs_search, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_editar':
            try:
                doc = docs.get(id=request.POST['doc'])
                if g_e.has_permiso('edita_todos_archivos') or doc.permiso_w(g_e.gauser) or doc.permiso_x(g_e.gauser):
                    hoy = datetime.now().date()
                    subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gte=hoy)
                    cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad)
                    d = {'g_e': g_e, 'cargos': cargos, 'subentidades': subentidades, 'etiquetas': etiquetas, 'd': doc}
                    html = render_to_string("documentos_table_tr_archivo_edit.html", d)
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_archivo':
            try:
                doc = docs.get(id=request.POST['doc'])
                if g_e.has_permiso('edita_todos_archivos') or doc.permiso_w(g_e.gauser) or doc.permiso_x(g_e.gauser):
                    doc.nombre = request.POST['nombre']
                    doc.etiqueta = Etiqueta_documental.objects.get(id=request.POST['etiqueta'])
                    doc.cargos.clear()
                    doc.acceden.clear()
                    cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('cargos[]'))
                    subs = Subentidad.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('subs[]'))
                    doc.cargos.add(*cargos)
                    doc.acceden.add(*subs)
                    doc.save()
                    html = render_to_string('documentos_table_tr_archivo.html', {'d': doc, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_documento':
            doc = docs.get(id=request.POST['doc'])
            if doc.permiso_x(g_e.gauser) or doc.propietario == g_e or g_e.has_permiso('borra_cualquier_archivo'):
                Permiso_Ges_documental.objects.filter(documento=doc, gauser=g_e.gauser).delete()
                otros = Permiso_Ges_documental.objects.filter(documento=doc).count()
                if otros == 0:
                    doc.delete()
                return JsonResponse(
                    {'ok': True, 'mensaje': 'Documento borrado. Ahora pueden verlo %s personas' % otros})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No ha sido posible borrar el documento.'})
        elif request.POST['action'] == 'borrar_doc_completamente':
            doc = docs.get(id=request.POST['doc'])
            if g_e.has_permiso('borra_cualquier_archivo'):
                todos = Permiso_Ges_documental.objects.filter(documento=doc)
                todos.delete()
                doc.delete()
                return JsonResponse({'ok': True, 'mensaje': 'Documento borrado por completo.'})
            else:
                return JsonResponse({'ok': False, 'mensaje': 'No ha sido posible borrar el documento.'})
        else:
            return JsonResponse({'ok': False, 'mensaje': 'No tiene los permisos necesarios.'})

    elif request.method == 'POST':
        if request.POST['action'] == 'sube_archivo':
            n_files = int(request.POST['n_files'])
            if g_e.has_permiso('sube_archivos'):
                for i in range(n_files):
                    fichero = request.FILES['fichero_xhr' + str(i)]
                    etiqueta = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad,
                                                               id=request.POST['etiqueta'])
                    doc = Ges_documental.objects.create(propietario=g_e, content_type=fichero.content_type,
                                                        etiqueta=etiqueta, nombre=fichero.name, fichero=fichero)
                    p = Permiso_Ges_documental.objects.create(gauser=g_e.gauser, documento=doc, permiso='x')
                    html = render_to_string('documentos_table_tr.html', {'docs': [doc], 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html, 'mensaje': False})
                try:
                    for i in range(n_files):
                        fichero = request.FILES['fichero_xhr' + str(i)]
                        etiqueta = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad,
                                                                   id=request.POST['etiqueta'])
                        doc = Ges_documental.objects.create(propietario=g_e, content_type=fichero.content_type,
                                                            etiqueta=etiqueta, nombre=fichero.name, fichero=fichero)
                        p = Permiso_Ges_documental.objects.create(gauser=g_e.gauser, documento=doc, permiso='x')
                        html = render_to_string('documentos_table_tr.html', {'docs': [doc], 'g_e': g_e})
                        return JsonResponse({'ok': True, 'html': html, 'mensaje': False})
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
            else:
                mensaje = 'No tienes permiso para cargar programaciones.'
                return JsonResponse({'ok': False, 'mensaje': mensaje})

        elif request.POST['action'] == 'descargar_doc':
            try:
                d = docs.get(id=request.POST['documento'])
                fichero = d.fichero.read()
                response = HttpResponse(fichero, content_type=d.content_type)
                response['Content-Disposition'] = 'attachment; filename=' + d.fich_name
                return response
            except:
                crear_aviso(request, False, 'Error. No se ha podido descargar el archivo.')

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
                      'form': form,
                      'g_e': g_e,
                      'etiquetas': etiquetas,
                      'docs': docs,
                      'carpetas': Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad),
                      'formname': 'documentos',
                      'carpeta_id': 'todas',  # Este identificador implica leer todas las carpetas
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


# # @permiso_required('acceso_documentos')
# def documentos2222222(request):
#     g_e = request.session['gauser_extra']
#     form = Ges_documentalForm(g_e=g_e)
#     pgds = Permiso_Ges_documental.objects.filter(gauser=g_e.gauser,
#                                                  documento__propietario__ronda__entidad=g_e.ronda.entidad)
#     etiquetas = Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad)
#     if request.method == 'POST' and request.is_ajax():
#         if request.POST['action'] == 'ver_formulario_subir' and g_e.has_permiso('sube_archivos'):
#             try:
#                 html = render_to_string("documentos_fieldset_subir.html", {'etiquetas': etiquetas})
#                 return JsonResponse({'ok': True, 'html': html})
#             except:
#                 return JsonResponse({'ok': False})
#         elif request.POST['action'] == 'ver_formulario_crear_etiqueta' and g_e.has_permiso('crea_carpetas'):
#             try:
#                 html = render_to_string("documentos_fieldset_etiqueta.html", {'etiquetas': etiquetas})
#                 return JsonResponse({'ok': True, 'html': html})
#             except:
#                 return JsonResponse({'ok': False})
#         elif request.POST['action'] == 'ver_formulario_buscar':
#             try:
#                 html = render_to_string("documentos_fieldset_buscar.html", {'etiquetas': etiquetas, 'g_e': g_e})
#                 return JsonResponse({'ok': True, 'html': html})
#             except:
#                 return JsonResponse({'ok': False})
#         elif request.POST['action'] == 'crea_etiqueta' and g_e.has_permiso('crea_carpetas'):
#             try:
#                 nombre = request.POST['nombre']
#                 if request.POST['padre']:
#                     padre = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['padre'])
#                     Etiqueta_documental.objects.create(entidad=g_e.ronda.entidad, padre=padre, nombre=nombre)
#                 else:
#                     Etiqueta_documental.objects.create(entidad=g_e.ronda.entidad, nombre=nombre)
#                 return JsonResponse({'ok': True})
#             except:
#                 return JsonResponse({'ok': False})
#         elif request.POST['action'] == 'busca_docs_manual':
#             try:
#                 try:
#                     inicio = datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date()
#                 except:
#                     inicio = datetime.strptime('1900-1-1', '%Y-%m-%d').date()
#                 try:
#                     fin = datetime.strptime(request.POST['fin'], '%Y-%m-%d').date()
#                 except:
#                     fin = datetime.now().date()
#                 texto = request.POST['texto']
#                 try:
#                     etiqueta = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['etiqueta'])
#                 except:
#                     etiqueta = None
#                 if etiqueta:
#                     q = Q(documento__propietario__ronda__entidad=g_e.ronda.entidad) & Q(
#                         documento__creado__gte=inicio) & Q(documento__creado__lte=fin) & Q(
#                         documento__nombre__icontains=texto) & Q(documento__etiqueta=etiqueta)
#                 else:
#                     q = Q(documento__propietario__ronda__entidad=g_e.ronda.entidad) & Q(
#                         documento__creado__gte=inicio) & Q(documento__creado__lte=fin) & Q(
#                         documento__nombre__icontains=texto)
#
#                 pgds = Permiso_Ges_documental.objects.filter(Q(gauser=g_e.gauser), q)
#                 html = render_to_string('documentos_table_tr.html', {'pgds': pgds, 'g_e': g_e})
#                 return JsonResponse({'ok': True, 'html': html})
#             except:
#                 return JsonResponse({'ok': False})
#         elif request.POST['action'] == 'ver_formulario_editar':
#             try:
#                 pgd = pgds.get(id=request.POST['doc'])
#                 if g_e.has_permiso('edita_todos_archivos') or pgd.permiso == 'w' or pgd.permiso == 'x':
#                     hoy = datetime.now().date()
#                     subentidades = Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gte=hoy)
#                     cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad)
#                     d = {'g_e': g_e, 'cargos': cargos, 'subentidades': subentidades, 'etiquetas': etiquetas, 'p': pgd}
#                     html = render_to_string("documentos_table_tr_archivo_edit.html", d)
#                     return JsonResponse({'ok': True, 'html': html})
#                 else:
#                     return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
#             except:
#                 return JsonResponse({'ok': False})
#         elif request.POST['action'] == 'update_archivo':
#             try:
#                 pgd = pgds.get(id=request.POST['pgd'])
#                 documento = pgd.documento
#                 if g_e.has_permiso('edita_todos_archivos') or pgd.permiso == 'w' or pgd.permiso == 'x':
#                     documento.nombre = request.POST['nombre']
#                     documento.etiqueta = Etiqueta_documental.objects.get(id=request.POST['etiqueta'])
#                     documento.cargos.clear()
#                     documento.acceden.clear()
#                     cargos = Cargo.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('cargos[]'))
#                     subs = Subentidad.objects.filter(entidad=g_e.ronda.entidad, id__in=request.POST.getlist('subs[]'))
#                     documento.cargos.add(*cargos)
#                     documento.acceden.add(*subs)
#                     documento.save()
#                     html = render_to_string('documentos_table_tr_archivo.html', {'p': pgd, 'g_e': g_e})
#                     return JsonResponse({'ok': True, 'html': html})
#                 else:
#                     return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
#             except:
#                 return JsonResponse({'ok': False})
#         elif request.POST['action'] == 'borrar_documento':
#             d = pgds.get(id=request.POST['pgd'])
#             documento = d.documento
#             if d.permiso == 'x' or documento.propietario == g_e or g_e.has_permiso('borra_cualquier_archivo'):
#                 d.delete()
#                 otros = Permiso_Ges_documental.objects.filter(documento=documento).count()
#                 if otros == 0:
#                     documento.delete()
#                 return JsonResponse(
#                     {'ok': True, 'mensaje': 'Documento borrado. Ahora pueden verlo %s personas' % otros})
#             else:
#                 return JsonResponse({'ok': False, 'mensaje': 'No ha sido posible borrar el documento.'})
#         elif request.POST['action'] == 'borrar_doc_completamente':
#             d = pgds.get(id=request.POST['pgd'])
#             documento = d.documento
#             if g_e.has_permiso('borra_cualquier_archivo'):
#                 todos = Permiso_Ges_documental.objects.filter(documento=documento)
#                 todos.delete()
#                 documento.delete()
#                 return JsonResponse({'ok': True, 'mensaje': 'Documento borrado por completo.'})
#             else:
#                 return JsonResponse({'ok': False, 'mensaje': 'No ha sido posible borrar el documento.'})
#         else:
#             return JsonResponse({'ok': False, 'mensaje': 'No tiene los permisos necesarios.'})
#
#     elif request.method == 'POST':
#         if request.POST['action'] == 'sube_archivo':
#             n_files = int(request.POST['n_files'])
#             if g_e.has_permiso('sube_archivos'):
#                 try:
#                     for i in range(n_files):
#                         fichero = request.FILES['fichero_xhr' + str(i)]
#                         etiqueta = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad,
#                                                                    id=request.POST['etiqueta'])
#                         doc = Ges_documental.objects.create(propietario=g_e, content_type=fichero.content_type,
#                                                             etiqueta=etiqueta, nombre=fichero.name, fichero=fichero)
#                         p = Permiso_Ges_documental.objects.create(gauser=g_e.gauser, documento=doc, permiso='x')
#                         html = render_to_string('documentos_table_tr.html', {'pgds': [p], 'g_e': g_e})
#                         return JsonResponse({'ok': True, 'html': html, 'mensaje': False})
#                 except:
#                     return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
#             else:
#                 mensaje = 'No tienes permiso para cargar programaciones.'
#                 return JsonResponse({'ok': False, 'mensaje': mensaje})
#
#         elif request.POST['action'] == 'descargar_doc':
#             try:
#                 d = pgds.get(id=request.POST['documento'])
#                 fichero = d.documento.fichero.read()
#                 response = HttpResponse(fichero, content_type=d.documento.content_type)
#                 response['Content-Disposition'] = 'attachment; filename=' + d.documento.nombre
#                 return response
#             except:
#                 crear_aviso(request, False, 'Error. No se ha podido descargar el archivo.')
#
#     return render(request, "documentos.html",
#                   {
#                       'iconos':
#                           ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
#                             'permiso': 'sube_archivos', 'title': 'Anadir un nuevo documento'},
#                            {'tipo': 'button', 'nombre': 'folder', 'texto': 'Nueva', 'permiso': 'crea_carpetas',
#                             'title': 'Crear una nueva carpeta/etiqueta'},
#                            {'tipo': 'button', 'nombre': 'search', 'texto': 'Buscar/Filtrar',
#                             'permiso': 'libre',
#                             'title': 'Busca/Filtra resultados entre los diferentes archivos'},
#                            ),
#                       'form': form,
#                       'g_e': g_e,
#                       'etiquetas': etiquetas,
#                       'pgds': pgds,
#                       'carpetas': Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad),
#                       'formname': 'documentos',
#                       'carpeta_id': 'todas',  # Este identificador implica leer todas las carpetas
#                       'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
#                   })
#
#
# @login_required()
# def documentos_ajax(request):
#     g_e = request.session['gauser_extra']
#     data = None
#     if request.is_ajax():
#         if request.method == 'POST':
#             if request.POST['action'] == 'contenido_documento':
#                 documento = Ges_documental.objects.get(id=json.loads(request.POST['id']))
#                 invitados = Permiso_Ges_documental.objects.filter(documento=documento)
#                 data = render_to_string('contenido_observaciones_documento.html',
#                                         {'documento': documento, 'invitados': invitados},
#                                         request=request)
#             if request.POST['action'] == 'crear_formulario':
#                 form = Ges_documentalForm(g_e=g_e)
#                 data = render_to_string('add_documento.html', {'form': form},
#                                         request=request)
#             if request.POST['action'] == 'editar_documento':
#                 try:
#                     documento = Ges_documental.objects.get(id=request.POST['id'])
#                     invitados_permiso = Permiso_Ges_documental.objects.filter(documento=documento)
#                     acceden = documento.acceden.all()
#                     keys = ('id', 'text')
#                     permisos = {'r': '(lectura)', 'w': '(lectura y escritura)', 'x': '(lectura, escritura y borrado)'}
#                     invitados = json.dumps([dict(zip(keys, ("%s_%s" % (row.gauser.id, row.permiso), "%s, %s %s" % (
#                         row.gauser.last_name, row.gauser.first_name, permisos[row.permiso])))) for row in
#                                             invitados_permiso])
#                     subentidades = json.dumps([dict(zip(keys, (row.id, "%s" % (row.nombre)))) for row in acceden])
#                     p = Permiso_Ges_documental.objects.get(gauser=g_e.gauser, documento=documento)
#                     if p.permiso != 'r':
#                         form = Ges_documentalForm(g_e=g_e, instance=documento)
#                         data = render_to_string('add_documento.html',
#                                                 {'form': form, 'invitados': invitados, 'subentidades': subentidades},
#                                                 request=request)
#                 except:
#                     data = None
#             if request.POST['action'] == 'documentos_carpeta':
#                 data = render_to_string('documentos_table.html', {'carpeta_id': request.POST['carpeta_id']},
#                                         request=request)
#             if request.POST['action'] == 'crear_carpeta':
#                 etiqueta = Etiqueta_documental.objects.create(entidad=g_e.ronda.entidad, nombre=request.POST['nombre'])
#                 carpeta = render_to_string('carpeta_nueva.html', {'carpeta': etiqueta})
#                 data = json.dumps({
#                     'carpeta': carpeta,
#                     'id': etiqueta.id,
#                 })
#                 return HttpResponse(data, content_type='application/json')
#             if request.POST['action'] == 'modificar_carpeta':
#                 carpeta = Etiqueta_documental.objects.get(id=request.POST['id'])
#                 carpeta.nombre = request.POST['nombre']
#                 carpeta.save()
#             if request.POST['action'] == 'borrar_carpeta':
#                 carpeta = Etiqueta_documental.objects.get(id=request.POST['id'])
#                 carpeta.delete()  # borra los documentos contenidos en la carpeta/etiqueta
#             if request.POST['action'] == 'borrar_documento':
#                 documento = Ges_documental.objects.get(id=request.POST['id'])
#                 nombre = documento.nombre
#                 try:
#                     p = Permiso_Ges_documental.objects.get(gauser=g_e.gauser, documento=documento)
#                     if p.permiso == 'x' or g_e.has_permiso('borra_cualquier_archivo'):
#                         documento.delete()
#                         crear_aviso(request, True, 'Documento borrado de la base de datos.')
#                         data = 'El documento "%s" ha sido borrado de la base de datos.' % (nombre)
#                     elif p.permiso == 'w':
#                         p.delete()
#                         crear_aviso(request, True, 'Acceso a documento eliminado.')
#                         data = 'El acceso al documento "%s" ha sido eliminado.' % (nombre)
#                 except:
#                     crear_aviso(request, True, 'Intento fallido de eliminar un documento.')
#                     data = 'No tienes permiso para eliminar el documento "%s".' % (nombre)
#
#             return HttpResponse(data)
#
#         if request.method == 'GET':
#             if request.GET['action'] == 'invitados':
#                 texto = request.GET['q']
#                 socios = Gauser_extra.objects.filter(ronda=g_e.ronda)
#                 socios_contain_texto = socios.filter(
#                     Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)).values_list(
#                     'gauser__id',
#                     'gauser__last_name',
#                     'gauser__first_name')
#                 keys = ('id', 'text')
#                 r = [dict(zip(keys, ('%s_r' % row[0], '%s, %s (lectura)' % (row[1], row[2])))) for row in
#                      socios_contain_texto]
#                 w = [dict(zip(keys, ('%s_w' % row[0], '%s, %s (lectura y escritura)' % (row[1], row[2])))) for row in
#                      socios_contain_texto]
#                 x = [dict(zip(keys, ('%s_x' % row[0], '%s, %s (lectura, escritura y borrado)' % (row[1], row[2])))) for
#                      row in socios_contain_texto]
#                 z = r + w + x
#                 return HttpResponse(json.dumps(z))
#
#                 # keys = ('id', 'text')
#                 # return HttpResponse(json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in socios_contain_texto]))


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
