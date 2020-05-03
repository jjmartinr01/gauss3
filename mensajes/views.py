# -*- coding: utf-8 -*-
from datetime import datetime
import zipfile
import simplejson as json
import pexpect
import os
import logging

from bs4 import BeautifulSoup
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponse
from django.db.models import Q
import html2text
from django import forms
from django.forms import ModelForm
from django.shortcuts import render
from django.template.loader import render_to_string

from autenticar.control_acceso import permiso_required
from mensajes.models import Mensaje, Aviso, Adjunto, Borrado, Importante, Leido, Etiqueta, Mensaje_cola
from mensajes.tasks import mail_mensajes_cola
from gauss.rutas import *
from gauss.funciones import usuarios_ronda

# from entidades.models import Subentidad
# from autenticar.models import Gauser_extra, Gauser
from entidades.models import Subentidad, Gauser_extra, Cargo, Entidad
from autenticar.models import Gauser

from gauss.funciones import usuarios_de_gauss, pass_generator, html_to_pdf, paginar


class AdjuntoForm(ModelForm):
    class Meta:
        model = Adjunto
        fields = ('propietario', 'fichero', 'content_type')
        widgets = {
        }

        # class MultipleChoiceField_destinatarios(forms.ModelMultipleChoiceField):
        # def label_from_instance(self, obj):
        # return "%s, %s" % (obj.gauser.last_name,obj.gauser.first_name)


class MensajeForm(ModelForm):
    class Meta:
        model = Mensaje
        # fields = ('destinatarios', 'asunto','mensaje')
        fields = ('asunto', 'mensaje')
        widgets = {
            'asunto': forms.TextInput(attrs={'size': '100'}),
            'mensaje': forms.Textarea(attrs={'cols': 80, 'rows': 8}),
            # 'destinatarios': forms.SelectMultiple(attrs={'size': 30, 'id':'id_destinatarios'}),
        }


def crea_mensaje_cola(mensaje):
    direcciones = list(mensaje.receptores.all().values_list('email', flat=True).distinct())
    direcciones = [d for d in direcciones if d]  # Para eliminar direcciones vacías o nulas

    dominios = list(set([a.split('@')[1] for a in direcciones]))
    dict_mails = {}
    for dominio in dominios:
        dict_mails[dominio] = [m for m in direcciones if dominio in m]

    dominios_grupo = 18  # Por cada dominio se abre una conexión smtp y el número máximo es  20, seleccionamos 18
    if len(dominios) > dominios_grupo:
        mails = []
        partes = range(dominios_grupo, len(dominios) + dominios_grupo, dominios_grupo)
        dominios = [dominios[a - dominios_grupo:a] for a in partes]
        # Por ejemplo, el array: [u'riojasalud.es', u'unirioja.es', u'knet.es', u'movistar.es', u'guardiacivil.es', u'ono.com', u'pormavi.es', u'terra.es', u'hotmail.com', u'copc.es', u'coaatrioja.org', u'logro-o.org', u'yahoo.es', u'orange.es', u'lear.com', u'telefonica.net', u'gaumentada.es', u'codesasl.com', u'mixmail.com', u'HOTMAIL.ES', u'monteclavijo.org', u'gmail.com', u'qubearquitectura.es', u'riojanadeasfaltos.com', u'yahoo.com', u'artadi.com', u'hotmail.es', u'riojatelecom.com']
        # Se convertiría en: [[u'riojasalud.es', u'unirioja.es', u'knet.es', u'movistar.es', u'guardiacivil.es', u'ono.com', u'pormavi.es', u'terra.es', u'hotmail.com', u'copc.es', u'coaatrioja.org', u'logro-o.org', u'yahoo.es', u'orange.es', u'lear.com', u'telefonica.net', u'gaumentada.es', u'codesasl.com'], [u'mixmail.com', u'HOTMAIL.ES', u'monteclavijo.org', u'gmail.com', u'qubearquitectura.es', u'riojanadeasfaltos.com', u'yahoo.com', u'artadi.com', u'hotmail.es', u'riojatelecom.com']]
        for dominio in dominios:
            mails_grupo_dominio = []
            for d in dominio:
                mails_grupo_dominio += dict_mails[d]
            mails.append(mails_grupo_dominio)
    else:
        mails = [direcciones]

    num_max_mails = 90  # El máximo número impuesto por Arsys es 100, pero lo reduzco a 90 por seguridad
    correos = []
    for mail in mails:
        if len(mail) > num_max_mails:
            partes = range(num_max_mails, len(mail) + num_max_mails, num_max_mails)
            correos += [mail[a - num_max_mails:a] for a in partes]
        else:
            correos.append(mail)
    for correo in correos:
        m = Mensaje_cola.objects.create(mensaje=mensaje, receptores=';'.join(correo), enviado=False)
    m.ultima_parte = True
    m.save()
    mail_mensajes_cola.delay()


@permiso_required('acceso_redactar_mensaje')
def redactar_mensaje(request):
    g_e = request.session['gauser_extra']
    return render(request, "redactar_mensaje.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'envelope-square', 'texto': 'Enviar',
                            'permiso': 'acceso_redactar_mensaje',
                            'title': 'Enviar mensaje a través del correo electrónico'},
                           {'tipo': 'button', 'nombre': 'telegram', 'texto': 'Enviar',
                            'permiso': 'acceso_redactar_mensaje',
                            'title': 'Enviar mensaje a través de Telegram'},
                           ),
                      # 'form1': form1,
                      'formname': 'redactar_mensaje',
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      # 'sub_accesibles': sub_accesibles,
                      # 'mensaje': mensaje,
                      # 'receptores': receptores,
                      # 'adjuntos': adjuntos,
                      # 'tipo_respuesta': tipo_respuesta,
                      # 'usa_mensaje': usa_mensaje,
                  })


def encolar_mensaje(emisor=None, receptores=[], asunto='', html='', texto='', etiqueta='', adjuntos=[]):
    """
    :param emisor: Objeto tipo Gauser_extra
    :param receptores: Conjunto de objetos tipo Gauser
    :param asunto: String
    :param html: String. Cuerpo del mensaje en html
    :param texto: String. Cuerpo del mensaje en texto plano
    :param etiqueta: String. Será convertida en objeto Etiqueta
    :param adjuntos: File. Objetos tipo file
    :return: Boolean. True el mensaje se ha encolado. False no se ha podido encolar el mensaje
    """
    try:
        mensaje = Mensaje.objects.create(emisor=emisor, fecha=datetime.now(), tipo='mail', asunto=asunto, mensaje=html,
                                         mensaje_texto=texto, borrador=False)
        mensaje.receptores.add(*receptores)
        mensaje.etiquetas.add(Etiqueta.objects.create(propietario=emisor, nombre=etiqueta))
        for fichero in adjuntos:
            adjunto = Adjunto.objects.create(propietario=emisor, fichero=fichero,
                                             content_type=fichero.content_type)
            mensaje.adjuntos.add(adjunto)
        crea_mensaje_cola(mensaje)
        return True
    except:
        return False


# @login_required()
@permiso_required('acceso_redactar_mensaje')
def correo(request):
    g_e = request.session['gauser_extra']
    sub_accesibles = Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today())
    car_accesibles = Cargo.objects.filter(entidad=g_e.ronda.entidad)

    mensaje = None
    receptores = None
    tipo_respuesta = None
    adjuntos = None
    usa_mensaje = ''
    if request.method == 'GET':
        if 'm' in request.GET:
            # try:
            m = Mensaje.objects.get(id=request.GET['m'])
            socios_mensaje = list(m.receptores.all().values_list('id', flat=True))
            socios_mensaje.append(m.emisor.gauser.id)
            socios_mensaje = Gauser.objects.filter(id__in=socios_mensaje)

            if g_e.gauser not in socios_mensaje:
                mensaje = None
                crear_aviso(request, False, 'No eres ni emisor, ni receptor del mensaje indicado', link='/correo/')
            else:
                tipo_respuesta = request.GET['t']
                # socios_mensaje = socios_mensaje.values_list('id', 'last_name', 'first_name')
                keys = ('id', 'text')
                if tipo_respuesta == 'responder':
                    receptores = json.dumps([{'id': m.emisor.gauser.id, 'text': '%s, %s' % (
                        m.emisor.gauser.last_name, m.emisor.gauser.first_name)}])
                    mensaje = Mensaje(emisor=m.emisor, asunto='Re: ' + m.asunto,
                                      mensaje='<br><br>______<br><span class="wysiwyg-color-gray">' + m.mensaje + '</span>')
                elif tipo_respuesta == 'responder_todos':
                    receptores = json.dumps(
                        [dict(zip(keys, (row.id, "%s, %s" % (row.last_name, row.first_name)))) for row in
                         socios_mensaje])
                    mensaje = Mensaje(emisor=m.emisor, asunto='Re: ' + m.asunto,
                                      mensaje='<br><br>______<br><span class="wysiwyg-color-gray">' + m.mensaje + '</span>')
                elif tipo_respuesta == 'reenviar':
                    receptores = None
                    mensaje = Mensaje(emisor=m.emisor, asunto=m.asunto, mensaje=m.mensaje)
                    adjuntos = m.adjuntos.all()
                    # except:
                    # crear_aviso(request,False,'Solicitud incorrecta')

    form1 = MensajeForm(prefix="mensaje", instance=mensaje)

    if request.method == 'POST':
        if request.POST['action'] == 'mail':
            etiqueta = Etiqueta.objects.create(propietario=g_e, nombre='___' + pass_generator(size=15))
            if request.POST['usa_mensaje'] != '':
                mensaje = Mensaje.objects.get(id=request.POST['usa_mensaje'])
            else:
                mensaje = Mensaje(emisor=g_e, fecha=datetime.now(), tipo='mail')
            form1 = MensajeForm(request.POST, prefix="mensaje", instance=mensaje)
            if form1.is_valid():
                mensaje = form1.save()
                receptores = Gauser.objects.filter(id__in=request.POST['mensaje-receptores'].split(','))
                mensaje.receptores.add(*receptores)
                mensaje.etiquetas.add(etiqueta)
                crear_aviso(request, True, request.META['PATH_INFO'] + ' Manda correo ')
                for input_file, object_file in request.FILES.items():
                    for fichero in request.FILES.getlist(input_file):
                        adjunto = Adjunto.objects.create(propietario=g_e, fichero=fichero,
                                                         content_type=fichero.content_type)
                        mensaje.adjuntos.add(adjunto)
                if request.POST['tipo_respuesta'] == 'reenviar':
                    ids = map(int, filter(None, request.POST['adjuntos_reenviados'].split(',')))
                    adjuntos = Adjunto.objects.filter(id__in=ids)
                    mensaje.adjuntos.add(*adjuntos)
                form1 = MensajeForm(prefix="mensaje")
                # direcciones = list(
                #     mensaje.receptores.all().values_list('email', flat=True))  # receptores son tipo Gauser
                # if 'autoenvio' in request.POST:
                #     direcciones.append(g_e.gauser.email)
                # direcciones = ['jmar0269@gmail.com']
                # c = ['juanjo@cossio.net', 'hesterri@yahoo.com', 'mavimandado@yahoo.es', 'marmolillo69l@yahoo.es', 'rhornos@guardiacivil.es', 'susanavictoriano@hotmail.com', 'blancaeroero@hotmail.com', 'victor_romero_garces@hotmail.com', 'vit_log_hue@hotmail.com', 'rohoral@ono.com', 'urbiola.m.j@gmail.com', 'vlancha@unirioja.es', 'rferna3@gmail.com', 'gazapopadin@hotmail.com', 'notiene@gaumentada.es', 'leirearaiz@gmail.com', 'cararaiz@gmail.com', 'darkraksu@hotmail.com', 'rementeriamarta@gmail.com', 'jgarcia05@lear.com', 'amaiarodriguez29@hotmail.com', 'msmd1970@gmail.com', 'ailagaflorez@gmail.com', 'miguelferreronalda@gmail.com', 'albertoandres2010@gmail.com', 'reydelhimalaya@hotmail.com', 'feperezsaenz@gmail.com', 'leire@qubearquitectura.es', 'n.morenosaenz@hotmail.com', 'alforues@hotmail.com', 'suromero@movistar.es', 'juananletona@gmail.com', 'SOCEGIMA@HOTMAIL.ES', 'talleresjuanluis@yahoo.es', 'leranchi@gmail.com', 'leranchi@gmail.com', 'carolcasterad@gmail.com', 'pieguiluz@yahoo.es']
                # direcciones = ['rohoral@ono.com', 'joseramon@riojatelecom.com', 'jmontoyablanco@yahoo.es', 'cverdejoh@gmail.com', 'deblancas@gmail.com', 'irenua10@mixmail.com', 'r.fernandez@reflectia.eu', 'granvillanoluis@gmail.com', 'manuelatena@hotmail.es', 'louerdesmahave@telefonica.net', 'lupeortega@gmail.com', 'info@ivancastillo.es', 'raskimano@telefonica.net', 'imunoz0707@gmail.com', 'gerkande@hotmail.com', 'andri11991@hotmail.com', '129314@gmail.com', '129314@gmail.com', 'gabrielyanguas@hotmail.com', 'izangroniz@coaatrioja.org', 'urbiola.m.j@gmail.com', 'nocorreo@monteclavijo.org', 'nocorreo@monteclavijo.org', 'ljdiezg@gmail.com', 'mentxu.rdv@gmail.com', 'lara_chiqui@hotmail.com', 'migugal@gmail.com', 'puriapodaca@gmail.com', 'simonecheverriaipad@gmail.com', 'annalar72@gmail.com', 'leireinigogarrido@gmail.com', 'esterilbasol@gmail.com', 'javi.sppnle@gmail.com', 'inventada@pormavi.es', 'r.navaridas@knet.es', 'attrianafer@hotmail.es', 'adm.mctejada@gmail.com', 'jmar0269@gmail.com']
                crea_mensaje_cola(mensaje)
                crear_aviso(request, False, 'El envío puede tardar varios minutos. Recibirás un aviso cuando finalice.')

                #     nom = mensaje.emisor.alias if mensaje.emisor.alias else mensaje.emisor.gauser.get_full_name()
                #     texto_mensaje = render_to_string('template_correo.html', {'mensaje': mensaje, },
                #                                      request=request)
                #     # email = EmailMessage(mensaje.asunto, texto_mensaje.encode('utf-8'),
                #     # '%s <%s>' % (nom, mensaje.emisor.gauser.email), bcc=direcciones,
                #     #                      headers={'Reply-To': mensaje.emisor.gauser.email})
                #     email = EmailMessage(mensaje.asunto, texto_mensaje.encode('utf-8'),
                #                          '%s <gauss@gaumentada.es>' % (nom), bcc=direcciones,
                #                          headers={'Reply-To': mensaje.emisor.gauser.email})
                #     for adjunto in mensaje.adjuntos.all():
                #         email.attach_file(adjunto.fichero.url.replace('/media/adjuntos/', MEDIA_ADJUNTOS))
                #     email.content_subtype = "html"
                #     email.send()
                #     crear_aviso(request, False, 'Correo enviado correctamente.')
                # else:
                #     crear_aviso(request, False, form1.errors)

        if request.POST['action'] == 'telegram':
            etiqueta = Etiqueta.objects.create(propietario=g_e, nombre='___' + pass_generator(size=15))
            mensaje = Mensaje(emisor=g_e, fecha=datetime.now(), tipo='telegram')
            form1 = MensajeForm(request.POST, prefix="mensaje", instance=mensaje)
            if form1.is_valid():
                mensaje = form1.save()
                mensaje.etiquetas.add(etiqueta)
                for filename, fichero in request.FILES.iteritems():
                    adjunto = Adjunto.objects.create(propietario=g_e, fichero=fichero)
                    mensaje.adjuntos.add(adjunto)
                form1 = MensajeForm(prefix="mensaje")

                # Para crear un nuevo Telegram hay que borrar el directorio ~/.telegram

                # http://geekytheory.com/tutorial-raspberry-pi-uso-de-telegram-con-python/
                # http://pexpect.sourceforge.net/doc/
                # You can read everything up to the EOF without generating an exception by using the expect(pexpect.EOF).
                # In this case everything the child has output will be available in the before property.

                # Crea el contacto, abre la conexión y espera a que Telegram se haya inicializado
                contacto = "Juanjo_Martín"
                telegram = pexpect.spawn('/home/juanjo/Telegram/tg/telegram -k /home/juanjo/Telegram/tg/tg.pub')
                telegram.expect('0m> ')

                ruta_file_text = MEDIA_FILES + str(g_e.id) + 'prueba.txt'
                file_text = open(ruta_file_text, 'w')
                file_text.write(html2text.html2text(mensaje.mensaje).encode('utf8'))
                file_text.close()
                # send_text <peer> <text-file-name> - sends text file as plain messages
                telegram.sendline('send_text ' + contacto + ' ' + ruta_file_text)

                telegram.sendline('quit')

                os.remove(ruta_file_text)
                crear_aviso(request, False, 'Mensaje enviado correctamente.')
            else:
                crear_aviso(request, False, form1.errors)

    return render(request, "correo.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'send-o', 'texto': 'Telegram',
                            'permiso': 'enviar_actasssss', 'title': 'Enviar mensaje a través de Telegram'},
                           {'tipo': 'button2', 'nombre': 'envelope-o', 'nombre2': 'share',
                            'texto': 'Enviar',
                            'title': 'Enviar correo electrónico', 'permiso': 'acceso_redactar_mensaje'},
                           ),
                      'form1': form1,
                      'formname': 'correo',
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                      'sub_accesibles': sub_accesibles,
                      'car_accesibles': car_accesibles,
                      'mensaje': mensaje,
                      'receptores': receptores,
                      'adjuntos': adjuntos,
                      'tipo_respuesta': tipo_respuesta,
                      'usa_mensaje': usa_mensaje,
                  })


@login_required()
def enviados(request):
    g_e = request.session["gauser_extra"]
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
    borrados = Borrado.objects.filter(eraser=g_e).values_list('mensaje__id', flat=True)
    mensajes = Mensaje.objects.filter(Q(emisor=g_e) & ~Q(pk__in=borrados)).order_by('-fecha')
    pagination = paginar(mensajes.count(), request.session['num_items_page'], c=1)
    return render(request, "enviados.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                            'permiso': 'acceso_mensajes_enviados', 'title': 'Borrar los mensajes seleccionados'},
                           ),
                      'mensajes': mensajes[:request.session['num_items_page']],
                      'formname': 'enviados',
                      'importantes': Importante.objects.filter(mensaje__in=mensajes).values_list(
                          'mensaje__id',
                          flat=True),
                      'pagination': pagination,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@login_required()
def recibidos(request):
    g_e = request.session["gauser_extra"]
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
            fich = open(fichero, 'rb')
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

        if request.POST['action'] == 'responder_mensaje':
            mensaje = Mensaje.objects.get(pk=request.POST['id_mensajes'])
            respuesta = Mensaje.objects.create(emisor=g_e, fecha=datetime.now(),
                                               asunto='Respuesta a: %s' % (mensaje.asunto),
                                               mensaje=request.POST['mensaje'])
            etiquetas = mensaje.etiquetas.all().filter(nombre__startswith='___')
            if etiquetas.count() > 0:
                respuesta.etiquetas.add(etiquetas[0])
            respuesta.receptores.add(mensaje.emisor.gauser)
            for filename, fichero in request.FILES.iteritems():
                adjunto = Adjunto.objects.create(propietario=g_e, fichero=fichero)
                respuesta.adjuntos.add(adjunto)
            try:
                crea_mensaje_cola(respuesta)
                crear_aviso(request, False, 'El envío puede tardar varios minutos. Recibirás un aviso cuando finalice.')
            except:
                crear_aviso(request, False, 'No se ha podido enviar el correo')

    borrados = Borrado.objects.filter(eraser=g_e).values_list('mensaje__id', flat=True)
    mensajes = Mensaje.objects.filter(Q(receptores__in=[g_e.gauser]) & ~Q(pk__in=borrados)).order_by('-fecha')
    pagination = paginar(mensajes.count(), request.session['num_items_page'], c=1)
    return render(request, "recibidos.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
                            'permiso': 'acceso_mensajes_recibidos', 'title': 'Borrar los mensajes seleccionados'},
                           ),
                      'mensajes': mensajes[:request.session['num_items_page']],
                      'formname': 'recibidos',
                      'importantes': Importante.objects.filter(mensaje__in=mensajes,
                                                               marcador=g_e).values_list('mensaje__id',
                                                                                         flat=True),
                      'leidos': Leido.objects.filter(mensaje__in=mensajes, lector=g_e).values_list(
                          'mensaje__id', flat=True),
                      'pagination': pagination,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)
                  })


@login_required()
def responder_mensaje(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']
        mensaje = Mensaje.objects.get(id=request.POST['id'])
        data = render_to_string('responder_mensaje.html', {'mensaje': mensaje, },
                                request=request)
        return HttpResponse(data)
    else:
        return HttpResponse(status=400)


@login_required()
def mensaje_importante(request):
    if request.is_ajax():
        marcador = request.session['gauser_extra']
        mensaje = Mensaje.objects.get(id=request.POST['id'])
        if request.POST['importante'] == '1':
            Importante.objects.create(marcador=marcador, mensaje=mensaje)
        elif request.POST['importante'] == '0':
            Importante.objects.get(marcador=marcador, mensaje=mensaje).delete()
        return HttpResponse()
    else:
        return HttpResponse(status=400)


@login_required()
def crear_aviso(request, aceptado, mensaje, link=""):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    fecha = datetime.now()
    m = False
    if not aceptado:
        try:
            Aviso.objects.get(usuario=request.session['gauser_extra'], aviso=mensaje, aceptado=aceptado, link=link)
        except:
            m = Aviso(usuario=request.session['gauser_extra'], aviso=mensaje, ip=ip, fecha=fecha, aceptado=aceptado,
                      link=link)
            m.save()
    else:
        logger = logging.getLogger(__name__)
        logger.info(
            u"%s, %s, %s, %s, %s" % (request.session['gauser_extra'], request.path, request.method, ip, mensaje))
    return m


@login_required()
def borrar_avisos(request):
    if request.is_ajax():
        avisos = Aviso.objects.filter(usuario=request.session['gauser_extra'], aceptado=False)
        for aviso in avisos:
            aviso.aceptado = True
            aviso.save()
            link = aviso.link
        return HttpResponse(link)
    else:
        return HttpResponse(status=400)


@login_required()
def get_avisos(request):
    if request.is_ajax():
        avisos = Aviso.objects.filter(usuario=request.session['gauser_extra'], aceptado=False)
        data = render_to_string('avisos.html', {'avisos': avisos})
        return HttpResponse(data)
    else:
        return HttpResponse(status=400)


@login_required()
def ajax_mensajes(request):
    # from django.core import serializers
    # if request.is_ajax(): # No se puede emplear is_ajax() porque la peticion del archivo no es reconocida como ajax
    g_e = request.session['gauser_extra']
    if request.method == 'POST':
        if request.POST['action'] == 'ver_mensaje':
            mensaje = Mensaje.objects.get(pk=request.POST['id'])
            try:
                Leido.objects.get(lector=request.session['gauser_extra'], mensaje=mensaje)
            except:
                Leido.objects.create(lector=request.session['gauser_extra'], mensaje=mensaje)
            data = render_to_string('reveal_contenido_correo.html',
                                    {'mensaje': mensaje, 'formname': request.POST['formname'],
                                     'tipo': request.POST['tipo'], 'numero': int(request.POST['numero']),
                                     'numero_max': int(request.POST['numero_max'])})
            # return HttpResponse(serializers.serialize('json', mensaje))
            # return HttpResponse((serializers.serialize('json', mensaje), serializers.serialize('json', mensaje[0].adjuntos.all())))
            return HttpResponse(data)
        if request.POST['action'] == 'borrar_mensajes':
            ids = map(int,
                      filter(None, request.POST['ids'].split(',')))  # El filter es para eliminar los elementos vacíos
            mensajes = Mensaje.objects.filter(id__in=ids)
            for mensaje in mensajes:
                Borrado.objects.create(eraser=g_e, mensaje=mensaje)
            return HttpResponse()

        if request.POST['action'] == 'pagination_enviados':
            id = int(request.POST['id'])
            paso = int(request.session['num_items_page'])
            inicio = (id - 1) * paso
            fin = id * paso
            borrados = Borrado.objects.filter(eraser=g_e).values_list('mensaje__id', flat=True)
            mensajes = Mensaje.objects.filter(Q(emisor=g_e) & ~Q(pk__in=borrados)).order_by('-fecha')
            data = render_to_string("list_enviados.html",
                                    {
                                        'mensajes': mensajes[inicio:fin],
                                        'importantes': Importante.objects.filter(mensaje__in=mensajes).values_list(
                                            'mensaje__id',
                                            flat=True),
                                        'pagination': paginar(mensajes.count(), paso, c=id),
                                    }, request=request)

            return HttpResponse(data)

        if request.POST['action'] == 'pagination_recibidos':
            id = int(request.POST['id'])
            paso = int(request.session['num_items_page'])
            inicio = (id - 1) * paso
            fin = id * paso
            borrados = Borrado.objects.filter(eraser=g_e).values_list('mensaje__id', flat=True)
            mensajes = Mensaje.objects.filter(Q(receptores__in=[g_e.gauser]) & ~Q(pk__in=borrados)).order_by('-fecha')
            data = render_to_string("list_recibidos.html",
                                    {
                                        'mensajes': mensajes[inicio:fin],
                                        'importantes': Importante.objects.filter(mensaje__in=mensajes).values_list(
                                            'mensaje__id', flat=True),
                                        'leidos': Leido.objects.filter(mensaje__in=mensajes, lector=g_e).values_list(
                                            'mensaje__id', flat=True),
                                        'pagination': paginar(mensajes.count(), paso, c=id),
                                    }, request=request)

            return HttpResponse(data)

        if request.POST['action'] == 'receptores_subentidad':
            datos = request.POST['subentidad'].split('___')
            subentidad = Subentidad.objects.filter(id=datos[1], fecha_expira__gt=datetime.today())
            g_es = usuarios_de_gauss(g_e.ronda.entidad, subentidades=subentidad)
            g_es = g_es.filter(activo=True)
            if datos[0] == 'padres':
                tutores_id = g_es.values_list('tutor1', 'tutor2')
                g_es = Gauser_extra.objects.filter(id__in=[e for l in tutores_id for e in l]).distinct()
            receptores = g_es.values_list('gauser__id', 'gauser__last_name', 'gauser__first_name')
            keys = ('id', 'text')
            # from django.core import serializers
            # data = serializers.serialize('json', socios2, fields=('gauser__first_name', 'id'))
            return HttpResponse(
                json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in receptores]))

    if request.method == 'GET':
        if request.GET['action'] == 'receptores':
            texto = request.GET['q']
            socios = usuarios_ronda(g_e.ronda)
            socios_contain_texto = socios.filter(
                Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)).values_list(
                'gauser__id',
                'gauser__last_name',
                'gauser__first_name')
            keys = ('id', 'text')
            return HttpResponse(
                json.dumps([dict(zip(keys, (row[0], '%s, %s' % (row[1], row[2])))) for row in socios_contain_texto]))

            # else:
            # return HttpResponse(status=400)


def enviar_correo(etiqueta=Etiqueta.objects.none(), asunto=None, texto_html=None, receptores=Gauser.objects.none(),
                  emisor=None, entidad=Entidad.objects.none()):
    if not receptores:
        return False, 'No hay definidos destinatarios'
    if not emisor:
        if not entidad:
            return False, 'No hay definido ni un emisor, ni la entidad de emisión'
        else:
            try:
                emisor = Gauser_extra.objects.get(ronda=entidad.ronda, gauser__username='gauss')
            except:
                return False, 'No ha sido posible definir un emisor'
    if texto_html:
        soup = BeautifulSoup(texto_html, 'html.parser')
        texto = soup.get_text()
    else:
        return False, 'El mensaje no contiene texto'
    if not etiqueta or type(etiqueta) != Etiqueta:
        etiqueta = Etiqueta.objects.create(nombre=pass_generator(9, 'abcdefghijkmnopqrs0123456789'), propietario=emisor)
    if not asunto:
        asunto = 'Mensaje de %s' % (emisor.gauser.get_full_name())
    mensaje = Mensaje.objects.create(emisor=emisor, fecha=datetime.now(), asunto=asunto, mensaje=texto_html,
                                     mensaje_texto=texto)
    mensaje.etiquetas.add(etiqueta)
    try:
        mensaje.receptores.add(*receptores)
    except:
        return False, 'Los receptores deben ser del tipo Gauser'
    crea_mensaje_cola(mensaje)
    return True, 'Enviado correctamente'
