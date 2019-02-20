# -*- coding: utf-8 -*-

import os
import difflib
import simplejson as json
from django.forms import ModelForm

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from entidades.models import Entidad, Subentidad

from mensajes.models import Aviso
from mensajes.views import crear_aviso
from gauss.rutas import *
from gauss.funciones import usuarios_de_gauss
# from models import T_Banded, Template_web, T_Blog, Text_row, Cate_Blog, Post_Blog
from web.models import Enlace_web, Top_bar, Content_div, Row_web, Html_web, Legal_web, File_web, TIPOS_dict, Noticia_web, File_noticia_web
from django.urls import reverse
from django.http import HttpResponseRedirect
from datetime import datetime
from django.core.files import File
from django.views.decorators.csrf import csrf_exempt


def noticias_web(request):
    g_e = request.session['gauser_extra']
    mis_noticias = Noticia_web.objects.filter(autor=g_e)
    otras_noticias = Noticia_web.objects.filter(autor__ronda=g_e.ronda).exclude(id__in=mis_noticias)

    return render(request, "noticias_web.html",
                  {'otras_noticias': otras_noticias, 'mis_noticias': mis_noticias, 'formname': 'noticias_web'})


def noticias_web_ajax(request):
    if request.method == 'POST' and request.is_ajax():
        g_e = request.session['gauser_extra']
        action = request.POST['action']
        if action == 'add_noticia':
            noticia = Noticia_web.objects.create(autor=g_e, titulo='', texto='')
            html = render_to_string('noticias_web_accordion.html', {'noticia': noticia})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'select_subentidad':
            noticia = Noticia_web.objects.get(autor__ronda=g_e.ronda, id=request.POST['noticia'])
            noticia.subentidad = Subentidad.objects.get(entidad=g_e.ronda.entidad, id=request.POST['subentidad'])
            noticia.save()
            return JsonResponse({'ok': True})
        elif action == 'texto_noticia':
            noticia = Noticia_web.objects.get(autor__ronda=g_e.ronda, id=request.POST['noticia'])
            noticia.texto = request.POST['texto']
            noticia.save()
            return JsonResponse({'ok': True})
        elif action == 'titulo_noticia':
            noticia = Noticia_web.objects.get(autor__ronda=g_e.ronda, id=request.POST['noticia'])
            noticia.titulo = request.POST['titulo']
            noticia.save()
            return JsonResponse({'ok': True})
        elif action == 'open_accordion':
            noticia = Noticia_web.objects.get(autor__ronda=g_e.ronda, id=request.POST['noticia'])
            html = render_to_string('noticias_web_accordion_content.html', {'noticia': noticia, 'g_e': g_e})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'publicar_from':
            noticia = Noticia_web.objects.get(autor__ronda=g_e.ronda, id=request.POST['noticia'])
            noticia.publicar_from = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
            noticia.save()
            return JsonResponse({'ok': True})
        elif action == 'publicar_to':
            noticia = Noticia_web.objects.get(autor__ronda=g_e.ronda, id=request.POST['noticia'])
            noticia.publicar_to = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
            noticia.save()
            return JsonResponse({'ok': True})
        elif action == 'borrar_noticia':
            noticia = Noticia_web.objects.get(autor__ronda=g_e.ronda, id=request.POST['noticia'])
            id = noticia.id
            for f in noticia.file_noticia_web_set.all():
                f.fichero.delete()
                f.delete()
            noticia.delete()
            return JsonResponse({'ok': True, 'noticia': id})




@csrf_exempt
def upload_file_noticia_web(request):
    g_e = request.session['gauser_extra']
    n = request.GET['CKEditorFuncNum']
    fichero = request.FILES['upload']
    noticia_id = request.GET['CKEditor'].replace('texto_noticia', '')
    noticia = Noticia_web.objects.get(autor__entidad=g_e.ronda.entidad, id=noticia_id)
    f = File_noticia_web.objects.create(fichero=fichero, content_type=fichero.content_type, noticia=noticia)
    p = 'https://gaumentada.es%s' % f.fichero.url.replace('/', '\/')

    return HttpResponse(
        '<script type="text/javascript">window.parent.CKEDITOR.tools.callFunction("%s", "%s", "");</script>' % (n, p))


def noticias_web_json(request):
    entidad = Entidad.objects.get(id=request.GET['c'])
    noticias = Noticia_web.objects.filter(autor__entidad=entidad, autor__ronda=entidad.ronda)
    data = []
    for noticia in noticias:
        dict_noticia = {'id':noticia.id, 'autor': noticia.autor.gauser.get_full_name(), 'modified': noticia.modified,
                    'titulo': noticia.titulo, 'texto': noticia.texto, 'created': noticia.created,
                        'publicar_to': noticia.publicar_to, 'publicar_from': noticia.publicar_from,
                        'seccion_id': noticia.subentidad.id, 'seccion': noticia.subentidad.nombre}
        data.append(dict_noticia)
    return JsonResponse(data, safe=False)


class Content_divForm(ModelForm):
    class Meta:
        model = Content_div
        fields = ('large_columns', 'medium_columns', 'small_columns', 'on_click', 'caption', 'title',
                  'subtitle', 'header_post', 'texto', 'enlaces', 'tipo', 'modificadores', 'align', 'esquinas', 'panel')


def pagina_web_entidad(request):
    # g_e = request.session['gauser_extra']
    # a= request.META['HTTP_USER_AGENT']
    url = request.path.replace('/', '')

    try:
        entidad = Entidad.objects.get(dominio=url)
        if 'id' in request.GET:
            hw = Html_web.objects.get(entidad=entidad, id=request.GET['id'])
        else:
            hw = Html_web.objects.get(entidad=entidad, home=True)
        return render(request, "pagina1_web_entidad.html", {'hw': hw})
    except:
        dominios = Entidad.objects.filter(dominio__isnull=False).values_list('dominio', flat=True)
        posibles = []
        prob = []
        for dominio in dominios:
            if difflib.SequenceMatcher(None, dominio, url).ratio() > 0.8:
                posibles.append(dominio)
            else:
                prob.append(dominio + str(difflib.SequenceMatcher(None, dominio, url).ratio()))
        return render(request, "pagina1_web_no_existe.html", {'posibles': posibles})


@login_required()
def enlaces_web(request):
    g_e = request.session['gauser_extra']
    if request.method == 'GET':
        if 'q' in request.GET:
            texto = request.GET['q']
            g_e = request.session['gauser_extra']
            enlaces = Enlace_web.objects.filter(entidad=g_e.ronda.entidad)
            enlaces_contain_texto = enlaces.filter(Q(texto__icontains=texto) | Q(href__icontains=texto)).values_list(
                'id', 'texto', 'href')
            keys = ('id', 'texto', 'href')
            return HttpResponse(json.dumps([dict(zip(keys, row)) for row in enlaces_contain_texto]))
    if request.method == 'POST':
        action = request.POST['action']
        if request.is_ajax():
            respuesta = ['No', 'Sí']
            if action == 'cambia_descripcion':
                enlace = Enlace_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                enlace.descripcion = request.POST['descripcion']
                enlace.save()
                return HttpResponse(enlace.descripcion)
            elif action == 'cambia_enlace':
                enlace = Enlace_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                enlace.href = request.POST['href']
                enlace.texto = request.POST['texto']
                enlace.save()
                data = render_to_string('enlaces2_web_href_nombre_title.html', {'enlace_web': enlace})
                return HttpResponse(data)
            elif action == 'cambia_activo':
                enlace = Enlace_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                enlace.activo = not enlace.activo
                enlace.save()
                return HttpResponse(respuesta[enlace.activo])
            elif action == 'contenido_accordion':
                enlace = Enlace_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                sub = Enlace_web.objects.filter(padre=enlace, entidad=g_e.ronda.entidad)
                keys = ('id', 'text')
                subenlaces = json.dumps(
                    [dict(zip(keys, (row.id, "%s (%s)" % (row.texto, row.href)))) for row in sub])
                data = render_to_string('enlaces2_web_contenido_accordion.html',
                                        {'enlace_web': enlace, 'subenlaces': subenlaces})
                return HttpResponse(data)
            elif action == 'update_enlaces':
                data = []
                padre = Enlace_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                hijos = Enlace_web.objects.filter(padre=padre)
                for hijo in hijos:
                    hijo.padre = None
                    hijo.save()
                try:
                    enlaces = Enlace_web.objects.filter(id__in=request.POST['enlaces'].split(','), entidad=g_e.ronda.entidad)
                except:
                    enlaces = []
                for enlace in enlaces:
                    enlace.padre = padre
                    enlace.save()
                    padre.href = ''
                padre.save()
                data.append(render_to_string('enlaces2_web_href_nombre.html', {'enlace_web': padre}))
                data.append(render_to_string('enlaces2_web_href_nombre_title.html', {'enlace_web': padre}))
                return HttpResponse(json.dumps(data))
            elif action == 'enlace_externo':
                enlace = Enlace_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                enlace.externo = not enlace.externo
                enlace.save()
                return HttpResponse(enlace.externo)
            elif action == 'elige_web_enlace':
                texto = request.POST['q']
                hws = Html_web.objects.filter(Q(entidad=g_e.ronda.entidad), Q(nombre__icontains=texto))
                keys = ('id', 'text')
                return HttpResponse(json.dumps(
                    [dict(zip(keys, (hw.id, "%s (hw-%s)" % (hw.nombre, hw.id)))) for hw in hws]))
            elif action == 'cambia_orden':
                enlace = Enlace_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                enlace.orden = request.POST['orden']
                enlace.save()
                return HttpResponse(enlace.orden)
        if action == 'add_enlace':
            Enlace_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, texto='Nuevo enlace',
                                      href='https://nuevoenlace.html')
        if action == 'borra_enlace':
            Enlace_web.objects.get(entidad=g_e.ronda.entidad, id=request.POST['enlace_id']).delete()

    hws = Html_web.objects.filter(entidad=g_e.ronda.entidad)
    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'title': 'Aceptar los cambios realizados',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'plus', 'texto': 'Enlace', 'title': 'Añadir una nueva fila',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Lista webs', 'title': 'Mostrar la lista de webs',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar', 'title': 'Borrar enlace',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'pencil', 'texto': 'Editar', 'title': 'Editar la página web',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'eye', 'texto': 'Ver', 'title': 'Ver como queda la página web',
              'permiso': 'libre'},
             ),
        'formname': 'enlaces_web',
        'ews': Enlace_web.objects.filter(entidad=g_e.ronda.entidad).order_by('-id'),
        'hws': json.dumps([dict(zip(('id', 'text'), (hw.id, "%s (hw-%s)" % (hw.nombre, hw.id)))) for hw in hws]),
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "enlaces1_web.html", respuesta)


@login_required()
def web_design(request):
    g_e = request.session['gauser_extra']
    html_webs = Html_web.objects.filter(entidad=g_e.ronda.entidad)
    if request.method == 'POST':
        action = request.POST['action']
        no_si = ['No', 'Sí']
        if action == 'guardar_web':
            create_template_banded(request)
            # enlace1 = Enlace_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, texto='Mi web',
            # href=g_e.ronda.entidad.web, activo=True)
            # enlace2 = Enlace_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, texto='Secciones',
            #                                     href=g_e.ronda.entidad.web, sub_enlaces='url1,opción 1;url2,opción 2;')
            # enlace3 = Enlace_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, texto='Tu web',
            #                                     href='http://www.tuweb.es')
            # top_bar = Top_bar.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, nombre='Nombre de la barra',
            #                                  href_nombre=g_e.ronda.entidad.web, tipo='fixed')
            # top_bar.buttons_web.add(enlace1, enlace2, enlace3)
            # texto = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut " \
            #         "labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris" \
            #         " nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate" \
            #         " velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non" \
            #         " proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
            # content_div1 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, title="Título de prueba",
            #                                           subtitle="Subtítulo", texto=texto, tipo='tipo_12t',
            #                                           large_columns=12, on_click='')
            # content_div2 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, title="Título prueba 2",
            #                                           subtitle="Subtítulo", texto=texto, tipo='tipo_4t4t4t',
            #                                           large_columns=12, on_click='')
            # row_web1 = Row_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, hr_after=True, orden=1)
            # row_web1.contents_div.add(content_div1)
            # row_web2 = Row_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, orden=2)
            # row_web2.contents_div.add(content_div2)
            # html_web = Html_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, nombre=request.POST['nombre'])
            # html_web.rows_web.add(row_web1, row_web2)
            # html_web.editores.add(g_e.gauser)
            # try:
            #     Legal_web.objects.get(entidad=g_e.ronda.entidad)
            # except:
            #     aviso_legal = render_to_string('aviso_legal.html', {}, request=request)
            #     privacidad = render_to_string('politica_privacidad.html', {}, request=request)
            #     Legal_web.objects.create(entidad=g_e.ronda.entidad, aviso_legal=aviso_legal, privacidad=privacidad)
        elif action == 'borrar_web':
            hw = Html_web.objects.get(id=request.POST['id_web'])
            tb = hw.top_bar
            if tb and Html_web.objects.filter(top_bar=tb).count() == 1:
                hw.top_bar = None
                tb.delete()
            for rw in hw.rows_web.all():
                for cd in rw.contents_div.all():
                    if cd.imagen:
                        file_web = cd.imagen
                        cd.imagen = None
                        file_web.delete()
                    cd.delete()
                rw.delete()
            if hw.html:
                os.remove(RUTA_BASE + hw.html.fichero.url)
                file_web = File_web.objects.get(id=hw.html.id)
                hw.html = None
                hw.save()
                file_web.delete()
            for file_web in hw.css.all():
                hw.css.remove(file_web)
                os.remove(RUTA_BASE + file_web.fichero.url)
                file_web.delete()
            for file_web in hw.js.all():
                hw.js.remove(file_web)
                os.remove(RUTA_BASE + file_web.fichero.url)
                file_web.delete()
            hw.delete()
        elif action == 'sube_fileweb':
            hw = Html_web.objects.get(id=request.POST['data1'])
            tipo = request.POST['data2']
            fichero = request.FILES['fichero_xhr']
            file_web = File_web.objects.create(entidad=g_e.ronda.entidad, fichero=fichero, content_type=fichero.content_type)
            render_html = 'web1_design_listFilesAjaxUpload.html'
            if tipo == 'html' and fichero.content_type == 'text/html':
                if hw.html:
                    os.remove(RUTA_BASE + hw.html.fichero.url)
                    file_web_borrar = hw.html
                    hw.html = file_web
                    hw.save()
                    file_web_borrar.delete()
                else:
                    hw.html = file_web
                    hw.save()
                data = render_to_string(render_html, {'archivos': [hw.html], 'hw': hw, 'field': 'html'})
            elif tipo == 'css' and fichero.content_type == 'text/css':
                hw.css.add(file_web)
                data = render_to_string(render_html, {'archivos': hw.css.all(), 'hw': hw, 'field': 'css'})
            elif tipo == 'js' and fichero.content_type == 'application/javascript':
                hw.js.add(file_web)
                data = render_to_string(render_html, {'archivos': hw.js.all(), 'hw': hw, 'field': 'js'})
            else:
                data = 'Fichero no aceptado ' + tipo + ' ' + fichero.content_type
                os.remove(RUTA_BASE + file_web.fichero.url)
                file_web.delete()
            return HttpResponse(data)
        elif action == 'lista_fileweb':
            hw = Html_web.objects.get(id=request.POST['hw'])
            render_html = 'web1_design_listFilesAjaxUpload.html'
            if request.POST['field'] == 'html':
                archivos = [hw.html] if hw.html else []
                data = render_to_string(render_html, {'archivos': archivos, 'hw': hw, 'field': 'html'})
            elif request.POST['field'] == 'css':
                data = render_to_string(render_html, {'archivos': hw.css.all(), 'hw': hw, 'field': 'css'})
            elif request.POST['field'] == 'js':
                data = render_to_string(render_html, {'archivos': hw.js.all(), 'hw': hw, 'field': 'js'})
            return HttpResponse(data)
        elif action == 'borrar_fileweb':
            hw = Html_web.objects.get(id=request.POST['hw'])
            file_web = File_web.objects.get(id=request.POST['id'])
            if request.POST['field'] == 'html':
                hw.html = None
                hw.save()
            elif request.POST['field'] == 'css':
                hw.css.remove(file_web)
            elif request.POST['field'] == 'js':
                hw.js.remove(file_web)
            os.remove(RUTA_BASE + file_web.fichero.url)
            file_web.delete()
        elif action == 'descarga_fileweb':
            file_web = File_web.objects.get(id=request.POST['file_web_id'])
            fichero = open(RUTA_BASE + file_web.fichero.url)
            response = HttpResponse(fichero, content_type=file_web.content_type)
            response['Content-Disposition'] = 'attachment; filename=' + file_web.fich_name
            return response
        elif action == 'actualiza_plantilla' and request.is_ajax():
            tipo = request.POST['tipo']
            data = render_to_string(tipo, {})
            return HttpResponse(data)
        elif action == 'abrir_accordion' and request.is_ajax():
            hw = Html_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            data = render_to_string('web1_design_accordion.html', {'html_web': hw})
            return HttpResponse(data)
        elif action == 'list_editores' and request.is_ajax():
            hw = Html_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            editores = hw.editores.all()
            data = []
            for editor in editores:
                data.append({'id': editor.id, 'text': '%s, %s' % (editor.last_name, editor.first_name)})
            return HttpResponse(json.dumps(data))
        elif action == 'cambia_nombre' and request.is_ajax():
            hw = Html_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            hw.nombre = json.loads(request.POST['nombre'])
            hw.editores.clear()
            editores = json.loads(request.POST['editores'])
            if editores:
                hw.editores.add(*editores.split(','))
            hw.save()
            data = render_to_string('web1_design_accordion.html', {'html_web': hw})
            return HttpResponse(data)
        elif action == 'cambia_tipo' and request.is_ajax():
            hw = Html_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            hw.tipo = request.POST['tipo']
            hw.save()
            return HttpResponse(TIPOS_dict[hw.tipo])
        elif action == 'cambia_home' and request.is_ajax():
            hws = Html_web.objects.filter(entidad=g_e.ronda.entidad)
            for hw in hws:
                hw.home = False
                hw.save()
            hw = Html_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            hw.home = not hw.home
            hw.save()
            return HttpResponse(no_si[hw.home])
        elif action == 'cambia_publicar' and request.is_ajax():
            hw = Html_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            hw.publicar = not hw.publicar
            hw.save()
            return HttpResponse(no_si[hw.publicar])
        elif action == 'ok_cambia_distribucion' and request.is_ajax():
            hw = Html_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
            col_izq, col_cen, col_der = request.POST['col_izq'], request.POST['col_cen'], request.POST['col_der']
            hw.col_izq, hw.col_cen, hw.col_der = col_izq, col_cen, col_der
            hw.save()
            return HttpResponse('%s-%s-%s' % (col_izq, col_cen, col_der))
        elif action == 'editores' and request.is_ajax():
            texto = request.POST['q']
            socios = usuarios_de_gauss(g_e.ronda.entidad)
            socios_contain_texto = socios.filter(
                Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)).values_list(
                'gauser__id',
                'gauser__last_name',
                'gauser__first_name')
            keys = ('id', 'text')
            return HttpResponse(
                json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in socios_contain_texto]))

    plantillas_disponibles = (("web2_banded_s.html", "Banded"),
                              ("web2_blog_s.html", "Blog"),
                              ("web2_feed_s.html", "Feed"),
                              ("web2_grid_s.html", "Grid"),
                              ("web2_orbit_home_s.html", "Orbit_home"),
                              ("web2_banner_home_s.html", "Banner home"),
                              ("web2_sidebar_s.html", "Sidebar"),
                              ("web2_contact_s.html", "Contact"),
                              ("web2_marketing_s.html", "Marketing"),
                              ("web2_realty_s.html", "Realty"),
                              ("web2_so_boxy_s.html", "So boxy"),
                              ("web2_store_s.html", "Store"),
                              ("web2_workspace_s.html", "Workspace"),
                              ("web2_marketing2_s.html", "Marketing 2"),
                              ("web2_product_s.html", "Product"),
                              ("web2_portfolio_s.html", "Portfolio"))
    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'title': 'Aceptar los cambios realizados',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir', 'title': 'Añadir una nueva página web',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Lista webs', 'title': 'Mostrar la lista de webs',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar', 'title': 'Borrar la página web',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'pencil', 'texto': 'Editar', 'title': 'Editar la página web',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'eye', 'texto': 'Ver', 'title': 'Ver como queda la página web',
              'permiso': 'libre'},
             ),
        'formname': 'desarrollo_web',
        'html_webs': html_webs,
        'plantillas_disponibles': plantillas_disponibles,
        'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"], aceptado=False),
    }
    return render(request, "web1_design.html", respuesta)


@login_required()
def edita_web(request, id):
    g_e = request.session['gauser_extra']
    hw = Html_web.objects.get(entidad=g_e.ronda.entidad, id=id, editores__in=[g_e.gauser])
    if request.method == 'POST':
        if request.POST['action'] == 'guardar_modificaciones':
            cd = Content_div.objects.get(id=request.POST['content_div'], entidad=g_e.ronda.entidad)
            cd = Content_divForm(request.POST, instance=cd)
            if cd.is_valid():
                cd.save()
            else:
                crear_aviso(request, False, cd.errors)
        if request.POST['action'] == 'link_html_web':
            enlace = Enlace_web.objects.get(entidad=g_e.ronda.entidad, id=request.POST['enlace'])
    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'title': 'Aceptar los cambios realizados',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'plus', 'texto': 'TopBar',
              'title': 'Añadir TopBar: Barra con menús y sub-menús', 'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'sort-asc', 'texto': 'Barra superior',
              'title': 'Añadir una barra de enlaces en la parte superior de la web', 'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Lista webs', 'title': 'Mostrar la lista de webs',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'link', 'texto': 'Enlaces', 'title': 'Añadir/Borrar enlaces',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'pencil', 'texto': 'Editar', 'title': 'Editar la página web',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'eye', 'texto': 'Ver', 'title': 'Ver como queda la página web',
              'permiso': 'libre'},
             ),
        'formname': 'edita_web',
        'hw': hw,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
    }
    return render(request, "edita1_web.html", respuesta)


@login_required()
def ajax_webs(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        action = request.POST['action']
        if request.method == 'POST':
            texto = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut " \
                    "labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris" \
                    " nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate" \
                    " velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non" \
                    " proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
            # Acciones relativas a la edición de filas. Un cambio en la fila recargará todas las filas
            if action == 'add_row':
                tipo = request.POST['tipo']
                html_web = Html_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                orden = html_web.rows_web.filter(tipo=tipo).count() + 1
                content_div = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, title="Título de fila",
                                                         subtitle="Subtítulo de fila", texto=texto, tipo='tipo_12t',
                                                         large_columns=12, orden=1, on_click='')
                row_web = Row_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, hr_after=True, orden=orden,
                                                 tipo=tipo)
                row_web.contents_div.add(content_div)
                html_web.rows_web.add(row_web)
                data = {}
                data['rows'] = render_to_string('edita3_rows_editables.html', {'hw': html_web})
                return HttpResponse(json.dumps(data))
            elif action == 'delete_row':
                html_web = Html_web.objects.get(rows_web__in=[request.POST['id']], entidad=g_e.ronda.entidad)
                row = Row_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                tipo_row = row.tipo
                cds = row.contents_div.all()
                for cd in cds:
                    if cd.imagen:
                        os.remove(RUTA_BASE + cd.imagen.fichero.url)
                        file_web = cd.imagen
                        cd.imagen = None
                        file_web.delete()
                    cd.delete()
                html_web.rows_web.remove(row)
                row.delete()
                rows = html_web.rows_web.filter(tipo=tipo_row).order_by('orden')
                orden = 1
                for row in rows:
                    row.orden = orden
                    row.save()
                    orden += 1
                data = {}
                data['rows'] = render_to_string('edita3_rows_editables.html', {'hw': html_web})
                return HttpResponse(json.dumps(data))
            elif action == 'hr_before':
                html_web = Html_web.objects.get(rows_web__in=[request.POST['id']], entidad=g_e.ronda.entidad)
                row = Row_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                row.hr_before = not row.hr_before
                row.save()
                data = {}
                data['rows'] = render_to_string('edita3_rows_editables.html', {'hw': html_web})
                return HttpResponse(json.dumps(data))
            elif action == 'hr_after':
                html_web = Html_web.objects.get(rows_web__in=[request.POST['id']], entidad=g_e.ronda.entidad)
                row = Row_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                row.hr_after = not row.hr_after
                row.save()
                data = {}
                data['rows'] = render_to_string('edita3_rows_editables.html', {'hw': html_web})
                return HttpResponse(json.dumps(data))
            elif action == 'move_row_down':
                html_web = Html_web.objects.get(rows_web__in=[request.POST['id']], entidad=g_e.ronda.entidad)
                tipo_row = request.POST['tipo']
                rws = html_web.rows_web.filter(tipo=tipo_row)
                rw = rws.get(id=request.POST['id'])
                rw_next = rws.get(orden=(rw.orden + 1), tipo=tipo_row)
                data = {}
                # if rw_next.tipo == 'PIE' and not rw.tipo == 'PIE':
                # data['mensaje'] = 'No se puede mover debajo de una fila marcada como "pie de página".'
                # else:
                rw.orden, rw_next.orden = rw_next.orden, rw.orden
                rw.save()
                rw_next.save()
                data['rows'] = render_to_string('edita3_rows_editables.html', {'hw': html_web})
                return HttpResponse(json.dumps(data))
            elif action == 'move_row_up':
                html_web = Html_web.objects.get(rows_web__in=[request.POST['id']], entidad=g_e.ronda.entidad)
                tipo_row = request.POST['tipo']
                rws = html_web.rows_web.filter(tipo=tipo_row)
                rw = rws.get(id=request.POST['id'])
                rw_before = rws.get(orden=(rw.orden - 1), tipo=tipo_row)
                data = {}
                # if rw_before.tipo == 'CABECERA' and not rw.tipo == 'CABECERA':
                # data['mensaje'] = 'No se puede mover encima de una fila marcada como "cabecera".'
                # else:
                rw.orden, rw_before.orden = rw_before.orden, rw.orden
                rw.save()
                rw_before.save()
                data['rows'] = render_to_string('edita3_rows_editables.html', {'hw': html_web})
                return HttpResponse(json.dumps(data))
            elif action == 'convierte_row':
                html_web = Html_web.objects.get(rows_web__in=[request.POST['id']], entidad=g_e.ronda.entidad)
                row_web = html_web.rows_web.get(id=request.POST['id'])
                tipo_original = row_web.tipo
                tipo_final = request.POST['tipo']
                orden = html_web.rows_web.filter(tipo=tipo_final).count() + 1
                row_web.tipo, row_web.orden = tipo_final, orden
                row_web.save()
                rows = html_web.rows_web.filter(tipo=tipo_original).order_by('orden')
                orden = 1
                for row in rows:
                    row.orden = orden
                    row.save()
                    orden += 1
                data = {}
                data['rows'] = render_to_string('edita3_rows_editables.html', {'hw': html_web})
                return HttpResponse(json.dumps(data))
            elif action == 'mail_row':
                html_web = Html_web.objects.get(rows_web__in=[request.POST['id']])
                row_web = Row_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                cds = row_web.contents_div.all()
                for cd in cds:
                    if cd.imagen:
                        os.remove(RUTA_BASE + cd.imagen.fichero.url)
                        file_web = cd.imagen
                        cd.imagen = None
                        file_web.delete()
                    cd.delete()

                content_div = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser,
                                                         title="Contacta con nosotros", subtitle='', texto='',
                                                         tipo='tipo_form_mail', large_columns=12, orden=1, on_click='')
                row_web.contents_div.add(content_div)
                data = {}
                data['rows'] = render_to_string('edita3_rows_editables.html', {'hw': html_web})
                return HttpResponse(json.dumps(data))
            elif action == 'tipo_gauss':
                html_web = Html_web.objects.get(rows_web__in=[request.POST['id']])
                row_web = Row_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                cds = row_web.contents_div.all()
                for cd in cds:
                    if cd.imagen:
                        os.remove(RUTA_BASE + cd.imagen.fichero.url)
                        file_web = cd.imagen
                        cd.imagen = None
                        file_web.delete()
                    cd.delete()

                content_div = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser,
                                                         title="", subtitle='', texto='',
                                                         tipo='tipo_gauss', large_columns=12, orden=1, on_click='')
                row_web.contents_div.add(content_div)
                data = {}
                data['rows'] = render_to_string('edita3_rows_editables.html', {'hw': html_web})
                return HttpResponse(json.dumps(data))

            # Acciones relativas a la edición de los contenidos de una fila (contents_div)
            elif action == 'add_cd':
                html_web = Html_web.objects.get(rows_web__in=[request.POST['id']])
                row = Row_web.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                orden = row.contents_div.all().count() + 1
                content_div = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, title="Título",
                                                         subtitle="Subtítulo", texto=texto, tipo='tipo_12t',
                                                         large_columns=6, orden=orden, on_click='')
                row.contents_div.add(content_div)
                data = {}
                data['rows'] = render_to_string('edita3_rows_editables.html', {'hw': html_web})
                return HttpResponse(json.dumps(data))
            elif action == 'edita_cd':
                cd = Content_div.objects.get(id=request.POST['id'], entidad=g_e.ronda.entidad)
                row = Row_web.objects.get(contents_div__in=[request.POST['id']], entidad=g_e.ronda.entidad)
                enlaces = Enlace_web.objects.filter(entidad=g_e.ronda.entidad)
                data = render_to_string('edita2_formulario.html',
                                        {'row': row, 'cd': cd, 'enlaces': enlaces, 'g_e': g_e})
                return HttpResponse(json.dumps(data))
            elif action == 'delete_cd':
                row_web = Row_web.objects.get(contents_div__in=[request.POST['id']], entidad=g_e.ronda.entidad)
                cds = row_web.contents_div.all()
                cd = cds.get(id=request.POST['id'])
                cds_gt = row_web.contents_div.filter(orden__gt=cd.orden)
                if cd.imagen:
                    os.remove(RUTA_BASE + cd.imagen.fichero.url)
                    file_web = cd.imagen
                    cd.imagen = None
                    file_web.delete()
                cd.delete()
                for cd in cds_gt:
                    cd.orden = cd.orden - 1
                    cd.save()
                data = render_to_string('edita4_row_editable.html', {'row': row_web})
                return HttpResponse(json.dumps(data))
            elif action == 'move_cd_right':
                row_web = Row_web.objects.get(contents_div__in=[request.POST['id']], entidad=g_e.ronda.entidad)
                cds = row_web.contents_div.all()
                cd = cds.get(id=request.POST['id'])
                cd_next = cds.get(orden=(cd.orden + 1))
                cd.orden, cd_next.orden = cd_next.orden, cd.orden
                cd.save()
                cd_next.save()
                data = render_to_string('edita4_row_editable.html', {'row': row_web})
                return HttpResponse(json.dumps(data))
            elif action == 'move_cd_left':
                row_web = Row_web.objects.get(contents_div__in=[request.POST['id']], entidad=g_e.ronda.entidad)
                cds = row_web.contents_div.all()
                cd = cds.get(id=request.POST['id'])
                cd_before = cds.get(orden=(cd.orden - 1))
                cd.orden, cd_before.orden = cd_before.orden, cd.orden
                cd.save()
                cd_before.save()
                data = render_to_string('edita4_row_editable.html', {'row': row_web})
                return HttpResponse(json.dumps(data))
            elif action == 'url_file_web':
                cd = Content_div.objects.get(id=request.POST['cd'])
                return HttpResponse(cd.imagen.fichero.url)


@login_required()
def sube_archivos_web(request):
    g_e = request.session['gauser_extra']
    action = request.POST['action']
    if action == 'imagen_web':
        cd = Content_div.objects.get(id=request.POST['data1'])
        fichero = request.FILES['fichero_xhr']
        file_web = File_web.objects.create(entidad=g_e.ronda.entidad, fichero=fichero, content_type=fichero.content_type)
        if fichero.content_type in 'image/jpeg, image/png, image/gif':
            try:
                os.remove(RUTA_BASE + cd.imagen.fichero.url)
                file_web_borrar = cd.imagen
                cd.imagen = file_web
                cd.save()
                file_web_borrar.delete()
            except:
                cd.imagen = file_web
                cd.save()
        else:
            os.remove(RUTA_BASE + file_web.fichero.url)
            file_web.delete()
        return HttpResponse(cd.imagen.fichero.url)


@login_required()
def create_template_banded(request):
    g_e = request.session['gauser_extra']
    texto = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut " \
            "labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris" \
            " nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate" \
            " velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non" \
            " proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
    enlace1 = Enlace_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, texto='Enlace1', activo=True,
                                        href='http://www.enlace1.es', externo=True)
    enlace2 = Enlace_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, texto='Enlace2', activo=True,
                                        href='http://www.enlace2.es', externo=True)
    enlace3 = Enlace_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, texto='Enlace3', activo=True,
                                        href='http://www.enlace3.es', externo=True)
    enlace4 = Enlace_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, texto='Enlace4', activo=True,
                                        href='http://www.enlace4.es', externo=True)
    with open(RUTA_STATIC_WEB + 'banded_logo.gif') as f:
        logo = File(f)
        logo_web = File_web.objects.create(entidad=g_e.ronda.entidad, fichero=logo)
    with open(RUTA_STATIC_WEB + 'banded1000x400.gif') as f:
        imagen_principal = File(f)
        imagen_principal_web = File_web.objects.create(entidad=g_e.ronda.entidad, fichero=imagen_principal)
    with open(RUTA_STATIC_WEB + 'banded400x300_1.gif') as f:
        imagen1 = File(f)
        imagen1_web = File_web.objects.create(entidad=g_e.ronda.entidad, fichero=imagen1)
    with open(RUTA_STATIC_WEB + 'banded400x300_2.gif') as f:
        imagen2 = File(f)
        imagen2_web = File_web.objects.create(entidad=g_e.ronda.entidad, fichero=imagen2)

    c_d11 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, large_columns=3, imagen=logo_web,
                                       tipo='tipo_12i', orden=1)
    c_d12 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, large_columns=9, orden=2,
                                       tipo='tipo_links_button_h')
    c_d12.enlaces.add(enlace1, enlace2, enlace3, enlace4)
    row1 = Row_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, orden=1, tipo='CABECERA')
    row1.contents_div.add(c_d11, c_d12)

    c_d21 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, large_columns=12,
                                       imagen=imagen_principal_web, tipo='tipo_12i', orden=1)
    row2 = Row_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, orden=2, tipo='CABECERA', hr_after=True)
    row2.contents_div.add(c_d21)

    c_d31 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, large_columns=4, imagen=imagen1_web,
                                       tipo='tipo_12i', orden=1)
    c_d32 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, large_columns=8, orden=2,
                                       tipo='tipo_6t6t', title='Sección de contenidos 1', texto=texto)
    row3 = Row_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, orden=1, tipo='NORMAL')
    row3.contents_div.add(c_d31, c_d32)

    c_d41 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, large_columns=8, orden=1,
                                       tipo='tipo_6t6t', title='Sección de contenidos 2', texto=texto)
    c_d42 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, large_columns=4, imagen=imagen2_web,
                                       tipo='tipo_12i', orden=2)
    row4 = Row_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, orden=2, tipo='NORMAL')
    row4.contents_div.add(c_d41, c_d42)

    c_d51 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, large_columns=5, orden=1,
                                       tipo='tipo_12t', texto='Copyright %s' % g_e.ronda.entidad.name)
    c_d52 = Content_div.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, large_columns=7,
                                       tipo='tipo_links_tab_h', orden=2)
    c_d52.enlaces.add(enlace1, enlace2, enlace3, enlace4)
    row5 = Row_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, orden=1, tipo='PIE')
    row5.contents_div.add(c_d51, c_d52)

    html_web = Html_web.objects.create(entidad=g_e.ronda.entidad, autor=g_e.gauser, nombre=request.POST['nombre'])
    html_web.rows_web.add(row1, row2, row3, row4, row5)
    html_web.editores.add(g_e.gauser)

    return html_web


    # class Row_web(models.Model):
    # TIPOS_R = (('NORMAL', 'Fila central'), ('CABECERA', 'Fila en cabecera de página'), ('PIE', 'Fila en pie de página'),
    # ('IZQUIERDA', 'Fila en lateral izquierdo'), ('DERECHA', 'Fila en lateral derecho'))
    # entidad = models.ForeignKey(Entidad, blank=True, null=True)
    # autor = models.ForeignKey(Gauser, blank=True, null=True)
    # contents_div = models.ManyToManyField(Content_div, blank=True, null=True)
    # hr_before = models.BooleanField("Colocar una línea de separación antes del contenido", default=False)
    # hr_after = models.BooleanField("Colocar una línea de separación después del contenido", default=False)
    # orden = models.IntegerField("Número de orden dentro del Html_web", max_length=10, blank=True, null=True)
    # tipo = models.CharField("Tipo de fila", max_length=20, choices=TIPOS_R, default='NORMAL')


    # class Content_div(models.Model):
    # NUM_COL = [[a, a] for a in range(1, 13)]
    # TIPO = (('tipo_12t', 'Texto dispuesto en una columna'),
    #         ('tipo_6t6t', 'Texto dispuesto en dos columnas'),
    #         ('tipo_tipo_4t4t4t', 'Texto dispuesto en tres columnas'),
    #         ('tipo_12i', 'Imagen'),
    #         ('tipo_links_tab_h', 'Lista de enlaces horizontal'),
    #         ('tipo_links_button_h', 'Lista de enlaces a través de botones horizontal'),
    #         ('tipo_links_tab_v', 'Lista de enlaces vertical'),
    #         ('tipo_links_button_v', 'Lista de enlaces a través de botones vertical'),
    #         ('tipo_form_mail', 'Formulario de contacto a través de mail'),
    #         ('tipo_title_links', 'Cabecera: Título, subtítulo y enlaces'),
    #         ('tipo_image_links', 'Cabecera: Título, subtítulo y enlaces'),
    #         ('tipo_footer', 'Pie de página'),
    #         ('tipo_gauss', 'Login y password a tipo_gauss'),
    # )
    # entidad = models.ForeignKey(Entidad, blank=True, null=True)
    # autor = models.ForeignKey(Gauser, blank=True, null=True)
    # modificadores = models.TextField('Personas que han modificado este contenido', blank=True, null=True)
    # large_columns = models.IntegerField("Número de columnas ocupadas en pantallas grandes", choices=NUM_COL, blank=True,
    #                                     null=True)
    # medium_columns = models.IntegerField("Número de columnas ocupadas en pantallas grandes", choices=NUM_COL,
    #                                      blank=True, null=True)
    # small_columns = models.IntegerField("Número de columnas ocupadas en pantallas grandes", choices=NUM_COL, blank=True,
    #                                     null=True)
    # on_click = models.TextField('Javascript a ejecutar cuando se haga click sobre él', null=True, blank=True)
    # imagen = models.ForeignKey(File_web, blank=True, null=True)
    # caption = models.CharField("Texto pie de foto", max_length=300, blank=True, null=True)
    # title = models.CharField("Título del contenedor", max_length=300, blank=True, null=True)
    # subtitle = models.CharField("Subtítulo del contenedor", max_length=300, blank=True, null=True)
    # header_post = models.BooleanField('Este content_div es la cabecera de un post?', default=False)
    # texto = models.TextField("Texto del párrafo", blank=True, null=True)
    # enlaces = models.ManyToManyField(Enlace_web, blank=True, null=True)
    # tipo = models.CharField("Tipo de content_div", blank=True, null=True, choices=TIPO, max_length=20)
    # orden = models.IntegerField("Número de orden dentro del Row_web", max_length=10, blank=True, null=True)
    # creado = models.DateTimeField('Fecha y hora de creación', auto_now_add=True, null=True)
