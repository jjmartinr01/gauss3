# coding=utf-8
# Create your views here.
import os
import pdfkit
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.timezone import datetime
from django.utils.text import slugify
from django.template import RequestContext
from django.template.loader import render_to_string
from django.core.paginator import Paginator
import simplejson as json
from django.db.models import Q
from autenticar.control_acceso import permiso_required
from autenticar.models import Gauser
from entidades.views import decode_selectgcs
from entidades.models import Subentidad, Cargo, DocConfEntidad
from documentos.forms import Ges_documentalForm, Contrato_gaussForm
from documentos.models import Ges_documental, Contrato_gauss, Etiqueta_documental, Compartir_Ges_documental, \
    TextoEvaluable
from gauss.funciones import usuarios_ronda
from gauss.rutas import MEDIA_DOCUMENTOS, MEDIA_ANAGRAMAS, RUTA_BASE
from mensajes.models import Aviso
from mensajes.views import crear_aviso, enviar_correo


def documentos_ge(request):
    g_e = request.session['gauser_extra']
    qa = Q(subentidad__in=g_e.subentidades.all()) | Q(cargo__in=g_e.cargos.all()) | Q(gauser=g_e.gauser)
    qb = qa & Q(documento__entidad=g_e.ronda.entidad)
    docs_id = Compartir_Ges_documental.objects.filter(qb).values_list('documento__id', flat=True)
    docs = Ges_documental.objects.filter(id__in=docs_id, borrado=False).distinct()
    try:
        inicio = datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date()
    except:
        inicio = datetime.strptime('1900-1-1', '%Y-%m-%d').date()
    try:
        fin = datetime.strptime(request.POST['fin'], '%Y-%m-%d').date()
    except:
        fin = datetime.now().date()
    try:
        texto = request.POST['texto']
    except:
        texto = ''

    try:
        etiqueta = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['etiqueta'])
        qb = Q(creado__gte=inicio) & Q(creado__lte=fin) & Q(nombre__icontains=texto) & Q(etiquetas__in=etiqueta.hijos)
    except:
        qb = Q(creado__gte=inicio) & Q(creado__lte=fin) & Q(nombre__icontains=texto)

    return docs.filter(qb)


# @permiso_required('acceso_documentos')
def documentos(request):
    for d in Ges_documental.objects.all():
        try:
            d.etiquetas.add(d.etiqueta)
        except:
            pass
        try:
            d.entidad = d.propietario.ronda.entidad
            d.save()
        except:
            pass
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        if request.POST['action'] == 'ver_formulario_subir' and g_e.has_permiso('sube_archivos'):
            try:
                etiquetas = Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad)
                html = render_to_string("documentos_fieldset_subir.html", {'etiquetas': etiquetas})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'sube_archivo':
            n_files = int(request.POST['n_files'])
            if g_e.has_permiso('sube_archivos'):
                try:
                    docs = []
                    for i in range(n_files):
                        fichero = request.FILES['fichero_xhr' + str(i)]
                        doc = Ges_documental.objects.create(propietario=g_e, content_type=fichero.content_type,
                                                            nombre=fichero.name, fichero=fichero)
                        # etiquetas = Etiqueta_documental.objects.filter(id__in=request.POST['etiquetas'].split(','),
                        #                                                entidad=g_e.ronda.entidad)
                        # doc.etiquetas.add(*etiquetas)
                        Compartir_Ges_documental.objects.create(gauser=g_e.gauser, documento=doc, permiso='rwx')
                        docs.append(doc)
                    html = render_to_string('documentos_table_tr.html', {'docs': docs, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html, 'mensaje': False})
                except:
                    return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error.'})
            else:
                mensaje = 'No tienes permiso para subir archivos.'
                return JsonResponse({'ok': False, 'mensaje': mensaje})
        elif request.POST['action'] == 'borrar_documento':
            try:
                doc = Ges_documental.objects.get(id=request.POST['doc'], borrado=False)
                if 'x' in doc.permisos(g_e):
                    try:
                        doc.compartir_ges_documental_set.filter(gauser=g_e.gauser).delete()
                        if Compartir_Ges_documental.objects.filter(documento=doc).count() == 0:
                            doc.borrado = True
                            doc.save()
                        m = 'Se ha borrado tu acceso personal al archivo.<br>Si todavía lo vieras es porque está compartido con un cargo que tienes asignado o una sección a la que perteneces.'
                        return JsonResponse({'ok': True, 'mensaje': m})
                    except:
                        m = 'Archivo no borrado. <br>Lo sigues viendo porque está compartido con un cargo que tienes asignado o una sección a la que perteneces.'
                        return JsonResponse({'ok': True, 'mensaje': m})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para borrar el documento.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_doc_completamente':
            try:
                doc = Ges_documental.objects.get(id=request.POST['doc'], borrado=False)
                if doc.propietario.ronda.entidad == g_e.ronda.entidad:
                    if g_e.has_permiso('borra_cualquier_archivo'):
                        doc.borrado = True
                        doc.save()
                        cgds = doc.compartir_ges_documental_set.all()
                        ss = Subentidad.objects.filter(id__in=set(cgds.values_list('subentidad__id', flat=True)))
                        cs = Cargo.objects.filter(id__in=set(cgds.values_list('cargo__id', flat=True)))
                        interesados = usuarios_ronda(g_e.ronda, subentidades=ss, cargos=cs)
                        q1 = Q(id__in=interesados.values_list('gauser__id', flat=True))
                        q2 = Q(id__in=set(cgds.values_list('gauser__id', flat=True)))
                        receptores = Gauser.objects.filter(q1, q2)
                        asunto = 'Se ha eliminado el archivo %s' % (doc.nombre)
                        texto = render_to_string('documentos_correo_archivo_borrado.html', {'doc': doc, 'emisor': g_e})
                        ok, m = enviar_correo(asunto=asunto, texto_html=texto, emisor=g_e, receptores=receptores)
                        if not ok:
                            aviso = '<br>Sin embargo, no se ha podido informar a los afectados.<br>(<i>%s</i>)' % m
                            crear_aviso(request, True, aviso)
                        else:
                            aviso = ''
                        mensaje = 'Durante los próximos 30 días puede ser recuperado por el administrador del sistema.'
                        return JsonResponse({'ok': True, 'mensaje': mensaje + aviso})
                    else:
                        return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para borrar el documento.'})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No borrado. El archivo no pertenece a esta entidad.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'descargar_doc':
            try:
                docs = documentos_ge(request)
                d = docs.get(id=request.POST['documento'])
                nombre, dot, ext = d.fich_name.rpartition('.')  # slugify(d.fich_name.rpartition('.')[0])
                response = HttpResponse(d.fichero, content_type=d.content_type)
                response['Content-Disposition'] = 'attachment; filename=%s.%s' % (slugify(d.nombre), ext)
                return response
            except:
                crear_aviso(request, False, 'Error. No se ha podido descargar el archivo.')
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
                    docs = documentos_ge(request)
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
                    e = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, nombre__iexact=nombre)
                    return JsonResponse({'ok': False, 'mensaje': 'Ya existe una etiqueta/carpeta con ese nombre.',
                                         'id_etiqueta': e.id, 'texto_etiqueta': e.etiquetas_text})
                except:
                    if request.POST['padre']:
                        padre = Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['padre'])
                        e = Etiqueta_documental.objects.create(entidad=g_e.ronda.entidad, padre=padre, nombre=nombre)
                    else:
                        e = Etiqueta_documental.objects.create(entidad=g_e.ronda.entidad, nombre=nombre)
                    return JsonResponse({'ok': True, 'id_etiqueta': e.id, 'texto_etiqueta': e.etiquetas_text})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borra_etiqueta' and g_e.has_permiso('borra_cualquier_carpeta'):
            try:
                Etiqueta_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['etiqueta']).delete()
                docs = documentos_ge(request)
                html = render_to_string('documentos_table_tr.html', {'docs': docs, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_page':
            try:
                docs = documentos_ge(request)
                paginator = Paginator(docs, 15)
                buscar = {'0': False, '1': True}[request.POST['buscar']]
                docs_paginados = paginator.page(int(request.POST['page']))
                html = render_to_string('documentos_table.html', {'docs': docs_paginados, 'g_e': g_e, 'buscar': buscar})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        # elif request.POST['action'] == 'busca_docs_manual':
        #     try:
        #         buscar
        #         docs_search = documentos_ge(request)
        #         html = render_to_string('documentos_table_tr.html', {'docs': docs_search, 'g_e': g_e, 'buscar': True})
        #         return JsonResponse({'ok': True, 'html': html})
        #     except:
        #         return JsonResponse({'ok': False})
        elif request.POST['action'] == 'ver_formulario_editar':
            try:
                doc = Ges_documental.objects.get(id=request.POST['doc'], borrado=False)
                if g_e.has_permiso('edita_todos_archivos') or 'w' in doc.permisos(g_e):
                    etiquetas = Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad)
                    payload = {'g_e': g_e, 'etiquetas': etiquetas, 'd': doc}
                    # html = render_to_string("documentos_table_tr_archivo_edit.html", payload)
                    html = render_to_string("documentos_fieldset_edit.html", payload)
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_nombre_archivo':
            try:
                doc = Ges_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id'], borrado=False)
                permisos_ge = doc.permisos(g_e)
                if 'w' in permisos_ge or 'x' in permisos_ge or g_e.has_permiso('edita_todos_archivos'):
                    doc.nombre = request.POST['nombre']
                    doc.save()
                    return JsonResponse({'ok': True})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha producido un error'})
        elif request.POST['action'] == 'update_etiquetas_archivo':
            # doc = Ges_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['doc'], borrado=False)
            # permisos_ge = doc.permisos(g_e)
            # if 'w' in permisos_ge or 'x' in permisos_ge or g_e.has_permiso('edita_carpetas'):
            #     etiqueta = Etiqueta_documental.objects.get(id=request.POST['etiqueta'], entidad=g_e.ronda.entidad)
            #     doc.etiquetas.add(etiqueta)
            #     html = render_to_string('documentos_list_etiquetas.html',
            #                             {'etiquetas': doc.etiquetas.all(), 'd': doc, 'g_e': g_e})
            #     return JsonResponse({'ok': True, 'html': html})
            try:
                doc = Ges_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id'], borrado=False)
                permisos_ge = doc.permisos(g_e)
                if 'w' in permisos_ge or 'x' in permisos_ge or g_e.has_permiso('edita_carpetas'):
                    etiqueta = Etiqueta_documental.objects.get(id=request.POST['etiqueta'], entidad=g_e.ronda.entidad)
                    doc.etiquetas.add(etiqueta)
                    html = render_to_string('documentos_list_etiquetas.html',
                                            {'etiquetas': doc.etiquetas.all(), 'd': doc, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_permiso_archivo':
            try:
                cgd = Compartir_Ges_documental.objects.get(documento__entidad=g_e.ronda.entidad, id=request.POST['id'],
                                                           documento__borrado=False)
                permisos_ge = cgd.documento.permisos(g_e)
                if 'w' in permisos_ge or 'x' in permisos_ge or g_e.has_permiso('edita_todos_archivos'):
                    cgd.permiso = request.POST['permiso']
                    cgd.save()
                    html_tr = render_to_string("documentos_table_tr_archivo_compartidocon.html", {'d': cgd.documento})
                    return JsonResponse({'ok': True, 'html_tr': html_tr, 'doc': cgd.documento.id})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'desasigna_etiquetas_archivo':
            try:
                doc = Ges_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['doc'], borrado=False)
                permisos_ge = doc.permisos(g_e)
                if 'w' in permisos_ge or 'x' in permisos_ge or g_e.has_permiso('edita_todos_archivos'):
                    etiqueta = Etiqueta_documental.objects.get(id=request.POST['etiqueta'], entidad=g_e.ronda.entidad)
                    doc.etiquetas.remove(etiqueta)
                    html = render_to_string('documentos_list_etiquetas.html',
                                            {'etiquetas': doc.etiquetas.all(), 'd': doc, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
            except:
                return JsonResponse({'ok': False})
        # elif request.POST['action'] == 'update_archivo':
        #     html = ''
        #     try:
        #         valor = request.POST['valor']
        #         campo = request.POST['campo']
        #         if request.POST['modelo'] == 'Ges_documental':
        #             doc = Ges_documental.objects.get(entidad=g_e.ronda.entidad, id=request.POST['id'], borrado=False)
        #             permisos_ge = doc.permisos(g_e)
        #             if 'w' in permisos_ge or 'x' in permisos_ge:
        #                 if campo == 'etiquetas':
        #                     etiqueta = Etiqueta_documental.objects.get(id=valor, entidad=g_e.ronda.entidad)
        #                     doc.etiquetas.add(etiqueta)
        #                     html = render_to_string('documentos_list_etiquetas.html',
        #                                             {'etiquetas': doc.etiquetas.all()})
        #                 else:
        #                     setattr(doc, campo, valor)
        #                     doc.save()
        #                 return JsonResponse({'ok': True, 'html': html, 'campo': campo})
        #             else:
        #                 return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
        #         else:
        #             cgd = Compartir_Ges_documental.objects.get(id=request.POST['id'])
        #             doc = cgd.documento
        #             if valor in doc.permisos(g_e):
        #                 cgd.permiso = valor
        #                 cgd.save()
        #                 return JsonResponse({'ok': True, 'campo': campo})
        #             else:
        #                 return JsonResponse({'ok': False, 'mensaje': 'No tienes los permisos necesarios.'})
        #     except:
        #         return JsonResponse({'ok': False})


        elif request.POST['action'] == 'update_new_permiso':
            try:
                doc = Ges_documental.objects.get(id=request.POST['doc'], borrado=False)
                if 'w' in doc.permisos(g_e) or g_e.has_permiso('edita_todos_archivos'):
                    ges, cs, ss = decode_selectgcs([request.POST['seleccionados']], g_e.ronda)
                    for ge in ges:
                        Compartir_Ges_documental.objects.get_or_create(documento=doc, gauser=ge.gauser)
                    for c in cs:
                        Compartir_Ges_documental.objects.get_or_create(documento=doc, cargo=c)
                    for s in ss:
                        Compartir_Ges_documental.objects.get_or_create(documento=doc, subentidad=s)
                    html = render_to_string("documentos_fieldset_edit_permisos.html", {'d': doc, 'g_e': g_e})
                    html_tr = render_to_string("documentos_table_tr_archivo_compartidocon.html", {'d': doc})
                    return JsonResponse({'ok': True, 'html': html, 'doc': doc.id, 'html_tr': html_tr})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para compartir el archivo.'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'No existe el archivo solicitado.'})
        elif request.POST['action'] == 'borrar_permiso_archivo':
            try:
                cgd = Compartir_Ges_documental.objects.get(id=request.POST['cgd'])
                doc = cgd.documento
                if 'w' in doc.permisos(g_e) or g_e.has_permiso('edita_todos_archivos'):
                    cgd.delete()
                    return JsonResponse({'ok': True, 'cgd': request.POST['cgd']})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para borrar compartido.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'fieldset_archivo_editar_close':
            try:
                doc = Ges_documental.objects.get(id=request.POST['doc'], borrado=False)
                if 'w' in doc.permisos(g_e) or g_e.has_permiso('edita_todos_archivos'):
                    html = render_to_string('documentos_table_tr_archivo.html', {'d': doc, 'g_e': g_e})
                    return JsonResponse({'ok': True, 'html': html, 'doc': doc.id})
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No tienes permisos para editar el archivo.'})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'get_etiquetas':
            try:
                etiquetas = Etiqueta_documental.objects.filter(entidad=g_e.ronda.entidad)
                html = render_to_string("documentos_fieldset_subir_select_etiquetas.html", {'etiquetas': etiquetas})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        else:
            return JsonResponse({'ok': False, 'mensaje': 'Solicitud incorrecta.'})


    # -----------
    # for d in Ges_documental.objects.all():
    #     for sub in d.acceden.all():
    #         Compartir_Ges_documental.objects.get_or_create(subentidad=sub, documento=d)
    #     for car in d.cargos.all():
    #         Compartir_Ges_documental.objects.get_or_create(cargo=car, documento=d)
    #     for p in d.permiso_ges_documental_set.all():
    #         c, v = Compartir_Ges_documental.objects.get_or_create(gauser=p.gauser, documento=d)
    #         if 'x' in p.permiso:
    #             c.permiso = 'rwx'
    #         elif 'w' in p.permiso:
    #             c.permiso = 'rw'
    #         else:
    #             c.permiso = 'r'
    #         c.save()
    # -----------
    Etiqueta_documental.objects.get_or_create(entidad=g_e.ronda.entidad, nombre='General')
    paginator = Paginator(documentos_ge(request), 15)
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
                      'docs': paginator.page(1),
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
            dce = DocConfEntidad.objects.get(entidad=g_e.ronda.entidad, predeterminado=True)
            contrato = Contrato_gauss.objects.get(entidad=g_e.ronda.entidad)
            fichero = 'Contrato_GAUSS_sin_firmar'
            c = render_to_string('contrato_gauss2pdf.html', {'contrato': contrato, 'MA': MEDIA_ANAGRAMAS},
                                 request=request)
            fich = pdfkit.from_string(c, False, dce.get_opciones)
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


####################################################################################
############################# TEXTOS EVALUABLES ####################################
####################################################################################

# @permiso_required('acceso_plantillas_te')
def plantillas_te(request):
    g_e = request.session["gauser_extra"]
    if request.method == 'POST' and request.is_ajax():
        if request.POST['action'] == 'crea_plantilla_te':
            if g_e.has_permiso('crea_plantillas_te') or True:  # El permiso da igual
                p = TextoEvaluable.objects.create(propietario=g_e, title="Nueva plantilla", plantilla=True)
                html = render_to_string('plantillas_te_accordion.html',
                                        {'buscadas': False, 'plantillas_te': [p], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            else:
                JsonResponse({'ok': False})
        elif request.POST['action'] == 'open_accordion':
            try:
                p = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad,
                                                           id=request.POST['id'])
                v = p.variantepii_set.all()[0]
                html = render_to_string('plantillas_te_accordion_content.html', {'p_te': p, 'g_e': g_e, 'variante': v})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_texto':
            try:
                p_te = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad,
                                                              id=request.POST['id'])
                setattr(p_te, request.POST['campo'], request.POST['valor'])
                p_te.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'update_texto_variante':
            try:
                id = request.POST['id']
                vp_te = VariantePII.objects.get(plantilla__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                setattr(vp_te, request.POST['campo'], request.POST['valor'])
                vp_te.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'copiar_variante':
            try:
                id = request.POST['id']
                vp_te = VariantePII.objects.get(plantilla__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                nombre = vp_te.nombre + ' (copia)'
                variante = VariantePII.objects.create(plantilla=vp_te.plantilla, nombre=nombre, texto=vp_te.texto)
                html = render_to_string('plantillas_te_accordion_content_variante.html',
                                        {'p_te': vp_te.plantilla, 'variante': variante})
                return JsonResponse({'ok': True, 'html': html, 'p_te': vp_te.plantilla.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'select_variante':
            try:
                id = request.POST['id']
                variante = VariantePII.objects.get(plantilla__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                html = render_to_string('plantillas_te_accordion_content_variante.html',
                                        {'p_te': variante.plantilla, 'variante': variante, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html, 'p_te': variante.plantilla.id})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'copiar_p_te':
            try:
                p_te = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad,
                                                              id=request.POST['id'])
                variantes = p_te.variantepii_set.all()
                p_te.pk = None
                p_te.asunto = p_te.asunto + ' (Copia)'
                p_te.save()
                for v in variantes:
                    v.pk = None
                    v.plantilla = p_te
                    v.save()
                html = render_to_string('plantillas_te_accordion.html',
                                        {'buscadas': False, 'plantillas_te': [p_te], 'g_e': g_e, 'nueva': True})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_p_te':
            try:
                p_te = PlantillaInformeInspeccion.objects.get(creador__ronda__entidad=g_e.ronda.entidad,
                                                              id=request.POST['id'])
                if g_e.has_permiso('borra_cualquier_plantilla_te') or g_e.gauser == p_te.creador.gauser:
                    p_te.delete()  # Borrar la plantilla y todas sus variantes
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'borrar_variante':
            try:
                id = request.POST['id']
                variante = VariantePII.objects.get(plantilla__creador__ronda__entidad=g_e.ronda.entidad, id=id)
                p_te = variante.plantilla
                if g_e.has_permiso('borra_cualquier_plantilla_te') or g_e.gauser == variante.plantilla.creador.gauser:
                    if p_te.variantepii_set.all().count() > 1:
                        variante.delete()  # Borrar la variante
                    else:
                        return JsonResponse({'ok': False,
                                             'mensaje': 'No es posible el borrado. Al menos debe haber un modelo de informe.'})
                html = render_to_string('plantillas_te_accordion_content_variante.html',
                                        {'p_te': p_te, 'variante': p_te.variantepii_set.all()[0]})
                return JsonResponse({'ok': True, 'html': html, 'p_te': variante.plantilla.id})
            except:
                return JsonResponse(
                    {'ok': False, 'mensaje': 'Se ha producido un error y no se ha podido hacer borrado'})

        elif request.POST['action'] == 'busca_plantillas_te':
            # try:
            try:
                inicio = datetime.strptime(request.POST['id_fecha_inicio'], '%d-%m-%Y')
            except:
                inicio = datetime.strptime('01-01-2000', '%d-%m-%Y')
            try:
                fin = datetime.strptime(request.POST['id_fecha_fin'], '%d-%m-%Y')
            except:
                fin = datetime.strptime('01-01-3000', '%d-%m-%Y')
            texto = request.POST['texto'] if request.POST['texto'] else ''
            q_variante = Q(nombre__icontains=texto) | Q(texto__icontains=texto)
            ids = VariantePII.objects.filter(q_variante).distinct().values_list('plantilla__id', flat=True)
            q_varios = Q(destinatario__icontains=texto) | Q(asunto__icontains=texto) | Q(id__in=ids)
            q_inicio = Q(modificado__gte=inicio)
            q_fin = Q(modificado__lte=fin)
            q_entidad = Q(creador__ronda__entidad=g_e.ronda.entidad)
            piis_base = PlantillaInformeInspeccion.objects.filter(q_entidad & q_inicio & q_fin)
            piis = piis_base.filter(q_varios)
            # if request.POST['tipo_busqueda']:
            #     p = PlantillaInformeInspeccion.objects.get(id=request.POST['tipo_busqueda'])
            #     ies = ies.filter(variante__plantilla=p)
            html = render_to_string('plantillas_te_accordion.html',
                                    {'plantillas_te': piis, 'g_e': g_e, 'buscadas': True})
            return JsonResponse({'ok': True, 'html': html, 'ids': ids.count()})
        # except:
        #     return JsonResponse({'ok': False})

    plantillas = PlantillaInformeInspeccion.objects.filter(creador__ronda__entidad=g_e.ronda.entidad)
    logger.info('Entra en ' + request.META['PATH_INFO'])
    if 'ge' in request.GET:
        pass
    return render(request, "plantillas_te.html", {
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
              'title': 'Crear una nueva plantilla de Texto Evaluable',
              'permiso': 'acceso_plantillas_te'},
             ),
        'g_e': g_e, 'plantillas_te': plantillas,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    })


####################################################################################
####################################################################################
####################################################################################

def presentaciones(request):
    if request.method == 'GET':
        if request.GET['id'] == 'xhtsl45':
            return render(request, "presentacion_funcion_directiva_1_3.html")
        else:
            return render(request, "no_enlace.html")
    else:
        return render(request, "no_enlace.html")
