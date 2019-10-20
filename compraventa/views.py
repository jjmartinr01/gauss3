# -*- coding: utf-8 -*-
import csv
import os
from datetime import datetime, date, timedelta
import simplejson as json

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q
from django.forms import ModelForm
from django.template.loader import render_to_string
from django.http import HttpResponse

# from autenticar.models import Gauser_extra, Enlace
from autenticar.models import Enlace
from entidades.models import Gauser_extra

from mensajes.models import Mensaje, Aviso
from mensajes.views import crear_aviso, crea_mensaje_cola
from gauss.rutas import *
from gauss.funciones import pass_generator
from compraventa.models import Categoria_objeto, Articulo, Foto_objeto, Comprador

from autenticar.views import CaptchaForm


class Articulo_Form(ModelForm):
    class Meta:
        model = Articulo
        fields = (
            'nombre', 'precio', 'precio_envio', 'formato', 'descripcion', 'pago', 'entrega', 'estado')


@login_required()
def comprar_y_vender(request):
    g_e = request.session['gauser_extra']

    if request.method == 'POST':
        if request.POST['action'] == 'introduce_articulo':
            codigo = pass_generator(size=35)
            articulo = Articulo(vendedor=g_e.gauser, entidad=g_e.ronda.entidad, estado='DISPONIBLE',
                                codigo=codigo)
        elif request.POST['action'] == 'modifica_articulo':
            articulo = Articulo.objects.get(id=request.POST['id_articulo'])
        form = Articulo_Form(request.POST, instance=articulo)
        if form.is_valid():
            articulo = form.save()
            articulo.categorias.clear()
            if request.POST['categorias']:
                id_categorias = list(filter(None, request.POST['categorias'].split(',')))
                categorias = Categoria_objeto.objects.filter(id__in=id_categorias)
                articulo.categorias.add(*categorias)
            articulo.fotos.clear()
            if request.POST['fotos_existentes']:
                id_fotos = list(filter(None, request.POST['fotos_existentes'].split(',')))
                fotos_existentes = Foto_objeto.objects.filter(id__in=id_fotos)
                articulo.fotos.add(*fotos_existentes)
            for input_file, object_file in request.FILES.items():
                for fichero in request.FILES.getlist(input_file):
                    if fichero.content_type in ['image/png', 'image/gif', 'image/jpeg']:
                        foto = Foto_objeto.objects.create(entidad=g_e.ronda.entidad, fichero=fichero,
                                                          content_type=fichero.content_type)
                        articulo.fotos.add(foto)
                        foto_url = RUTA_BASE + foto.fichero.url
                        os.system('convert %s -resize 400x %s' % (foto_url, foto_url))
                    else:
                        crear_aviso(request, False,
                                    u'Tipo de imagen: %s, no permitido (sólo jpeg, png y gif)' % (
                                        fichero.content_type))
        else:
            crear_aviso(request, False, form.errors)

    articulos = Articulo.objects.filter(~Q(estado='VENDIDO'), Q(entidad=g_e.ronda.entidad))
    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'title': 'Aceptar los cambios realizados',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir', 'title': 'Añadir un nuevo artículo o servicio',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Artículos', 'title': 'Mostrar la lista de artículos',
              'permiso': 'libre'},
             ),
        'formname': 'compraventa',
        'articulos': articulos,
        'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"], aceptado=False),
    }
    return render(request, "compra_y_venta.html", respuesta)


def estado_articulo(request):
    try:
        codigo = request.GET['id']
        enlaces = Enlace.objects.filter(code=codigo)
        if enlaces[0].deadline >= date.today():
            estado = request.GET['estado']
            articulo = Articulo.objects.get(codigo=codigo)
            articulo.estado = estado
            articulo.save()
            return HttpResponse('Se ha establecido en GAUSS que "%s": %s' %(articulo.nombre, articulo.get_estado_display()))
        else:
            return HttpResponse("El enlace que has seguido está caducado. No se lleva a cabo lo solicitado.")
    except:
        return render(request, "autenticar.html", {'tipo': 'acceso'})



@login_required()
def ajax_compraventa(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        if request.method == 'GET':
            if request.GET['action'] == 'select_categorias':
                texto = request.GET['q']
                categorias = Categoria_objeto.objects.filter(
                    Q(categoria__icontains=texto) | Q(subcategoria__icontains=texto)).values_list('id', 'categoria',
                                                                                                  'subcategoria')
                keys = ('id', 'categoria', 'subcategoria')
                # from django.core import serializers
                # data = serializers.serialize('json', socios2, fields=('gauser__first_name', 'id'))
                return HttpResponse(json.dumps([dict(zip(keys, row)) for row in categorias]))
        if request.method == 'POST':
            action = request.POST['action']
            if action == 'precio_fijo' or action == 'subasta' or action == 'servicio':
                articulo = Articulo.objects.get(id=request.POST['id_articulo'])
                if action == 'precio_fijo':
                    comprador = Comprador.objects.create(comprador=g_e.gauser, entidad=g_e.ronda.entidad, articulo=articulo,
                                                         observaciones=request.POST['mensaje_comprador'],
                                                         oferta=request.POST['oferta'].replace(',', '.'))
                    deadline = date.today() + timedelta(days=7)
                    code = articulo.codigo
                    Enlace.objects.create(usuario=g_e.gauser, code=code, deadline=deadline, enlace='/estado_articulo/')
                    texto_mensaje = render_to_string('correo_para_vendedor.html', {'comprador': comprador},
                                                     request=request)
                    texto_mensaje_PT = render_to_string('correo_para_vendedorPlainText.html', {'comprador': comprador},
                                                        request=request)
                    if action == 'precio_fijo':
                        asunto = u'Compra del artículo %s' % (articulo.nombre)
                    if action == 'subasta':
                        asunto = u'Oferta en subasta del artículo %s' % (articulo.nombre)
                    if action == 'servicio':
                        asunto = u'Solicitud del servicio %s' % (articulo.nombre)
                    gauss = Gauser_extra.objects.get(gauser__username='gauss', ronda=g_e.ronda)
                    m = Mensaje.objects.create(emisor=gauss, fecha=datetime.now(), asunto=asunto, mensaje=texto_mensaje,
                                               tipo='mail', mensaje_texto=texto_mensaje_PT)
                    m.receptores.add(articulo.vendedor)
                    crea_mensaje_cola(m)
                    texto_mensaje = render_to_string('correo_para_comprador.html', {'comprador': comprador},
                                                     request=request)
                    texto_mensaje_PT = render_to_string('correo_para_compradorPlainText.html', {'comprador': comprador},
                                                        request=request)
                    m = Mensaje.objects.create(emisor=gauss, fecha=datetime.now(), asunto=asunto, mensaje=texto_mensaje,
                                               tipo='mail', mensaje_texto=texto_mensaje_PT)
                    m.receptores.add(comprador.comprador)
                    crea_mensaje_cola(m)
                    return HttpResponse('')

            elif request.POST['action'] == 'introduce_articulo':
                form = Articulo_Form()
                data = render_to_string('form_introduce_articulo.html', {'form': form})
                return HttpResponse(data)

            elif request.POST['action'] == 'modifica_articulo':
                articulo = Articulo.objects.get(id=request.POST['id'])
                form = Articulo_Form(instance=articulo)
                keys = ('id', 'text')
                categorias = json.dumps(
                    [dict(zip(keys, (row.id, "%s (%s)" % (row.subcategoria, row.categoria)))) for row in
                     articulo.categorias.all()])
                fotos = articulo.fotos.all()
                data = render_to_string('form_introduce_articulo.html',
                                        {'form': form, 'categorias': categorias, 'fotos': fotos})
                return HttpResponse(data)

            elif request.POST['action'] == 'select_articulo_servicio':
                articulo = Articulo.objects.get(id=request.POST['id'])
                captcha = CaptchaForm()
                data = render_to_string('select_articulo_servicio.html',
                                        {'articulo': articulo, 'formname': 'compraventa', 'captcha': captcha},
                                        request=request)
                return HttpResponse(data)


def crea_categorias(request):
    csv_file = open('/home/juanjo/django/gauss_asocia/compraventa/categorias.csv', "rb")
    fichero = csv.reader(csv_file, delimiter=';')
    for row in fichero:
        c = 0
        for col in row:
            if c == 0:
                categoria = unicode(col, 'utf-8')
            else:
                Categoria_objeto.objects.create(categoria=categoria, subcategoria=unicode(col, 'utf-8'))
            c += 1
    csv_file.close()
    return HttpResponse('Terminado')
