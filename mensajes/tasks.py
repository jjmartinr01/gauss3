# -*- coding: utf-8 -*-
from celery import shared_task
from datetime import datetime
from time import sleep
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from gauss.rutas import MEDIA_ADJUNTOS
from mensajes.models import Mensaje_cola, Aviso

@shared_task
def mail_mensajes_cola():
    mensajes_cola = Mensaje_cola.objects.filter(enviado=False)

    for mensaje_cola in mensajes_cola:
        mensaje = mensaje_cola.mensaje
        direcciones = mensaje_cola.receptores.split(';')
        mensaje_cola.enviado = True
        mensaje_cola.save()

        nom = mensaje.emisor.alias if mensaje.emisor.alias else mensaje.emisor.gauser.get_full_name()
        html_mensaje = render_to_string('template_correo.html', {'mensaje': mensaje})
        if not mensaje.mensaje_texto: #Si no hay plain text lo creo a partir del mensaje html
            mensaje.mensaje_texto = strip_tags(mensaje.mensaje)
            mensaje.save()
        texto_mensaje = render_to_string('template_correoPlainText.html', {'mensaje': mensaje})
        # email = EmailMessage(mensaje.asunto, html_mensaje,
        #                      '%s <gauss@gaumentada.es>' % (nom), bcc=direcciones,
        #                      headers={'Reply-To': mensaje.emisor.gauser.email})
        emisor = '%s <gauss@gaumentada.es>' % (nom)
        email = EmailMultiAlternatives(mensaje.asunto.strip(), texto_mensaje,
                             emisor, bcc=direcciones,
                             headers={'Reply-To': mensaje.emisor.gauser.email})
        email.attach_alternative(html_mensaje, 'text/html')
        for adjunto in mensaje.adjuntos.all():
            email.attach_file(adjunto.fichero.url.replace('/media/adjuntos/', MEDIA_ADJUNTOS))
        # email.content_subtype = "html"
        email.send()
        fecha = datetime.now()
        texto = 'Correo enviado a %d destinatarios (id de Mesaje_cola: %s)' % (len(direcciones), mensaje_cola.id)
        Aviso.objects.create(usuario=mensaje.emisor, aviso=texto, fecha=fecha, aceptado=True, link='')
        # Creamos un aviso en caso de que se haya enviado por completo el mensaje, esto es cuando mensaje_cola.ultima_parte sea True
        if mensaje_cola.ultima_parte:
            fecha_string = fecha.strftime("%d-%m-%Y %H:%M:%S")
            num_mails = mensaje_cola.mensaje.receptores.all().count()
            t = '' if num_mails == 1 else 's'
            texto = 'Correo enviado correctamente a %d destinatario%s (%s)' %(num_mails, t, fecha_string)
            Aviso.objects.create(usuario=mensaje.emisor, aviso=texto, fecha=fecha, aceptado=False, link='')
        sleep(120)

