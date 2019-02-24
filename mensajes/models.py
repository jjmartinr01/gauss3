# -*- coding: utf-8 -*-
from django.db import models

# from autenticar.models import Gauser, Gauser_extra
from entidades.models import Entidad, Ronda
from entidades.models import Gauser_extra as GE
from autenticar.models import Gauser
# from entidades.models import Entidad, Ronda, Gauser_extra

from datetime import datetime
import os

# Las siguientes líneas son para eliminar las etiquetas html (html tags) del mensaje:
# from HTMLParser import HTMLParser  #Esto es para python2. En python3:
from html.parser import HTMLParser


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ' '.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_fichero(instance, filename):
    nombre = filename.partition('.')
    ahora = datetime.now()
    fichero = str(instance.propietario.id) + '_' + nombre[0].replace(' ', '_') + '_' + str(ahora.day) + '-' + str(
        ahora.month) + '-' + str(ahora.year) + '.' + nombre[2]
    return os.path.join("adjuntos/", fichero)


class Adjunto(models.Model):
    propietario = models.ForeignKey(GE, on_delete=models.SET_NULL, related_name='ge', blank=True, null=True)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero, blank=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)

    class Meta:
        app_label = 'mensajes'

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def __str__(self):
        return u'%s (%s)' % (self.fichero, self.propietario.gauser.get_full_name())


class Etiqueta(models.Model):
    propietario = models.ForeignKey(GE, on_delete=models.SET_NULL, related_name='ge1', blank=True, null=True)
    nombre = models.CharField("Etiqueta", max_length=500)

    class Meta:
        app_label = 'mensajes'

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.propietario.gauser.get_full_name())


class Mensaje(models.Model):
    emisor = models.ForeignKey(GE, on_delete=models.SET_NULL, related_name='ge2', blank=True, null=True)
    receptores = models.ManyToManyField(Gauser, related_name="receptores")
    adjuntos = models.ManyToManyField(Adjunto, related_name="adjuntos", blank=True)
    etiquetas = models.ManyToManyField(Etiqueta, related_name="etiquetas", blank=True)
    fecha = models.DateTimeField("Fecha y hora de envío")
    asunto = models.CharField("Asunto", max_length=500, null=True, blank=True)
    mensaje = models.TextField("Texto del Mensaje (html)")
    mensaje_texto = models.TextField("Texto del mensaje (plain/text)", null=True, blank=True)
    tipo = models.CharField("Tipo", max_length=30, null=True, blank=True)
    borrador = models.BooleanField('Es un borrador', default=True)

    class Meta:
        app_label = 'mensajes'

    def men_ini(self):  #Devuelve los primeros caracteres del mensaje
        ncar = 85
        sin_tags = strip_tags(self.mensaje)
        if len(sin_tags) > 85:
            return sin_tags[:ncar] + '...'
        else:
            return sin_tags

    def __str__(self):
        return u'Enviado por %s (%s) - %s' % (self.emisor.gauser.get_full_name(), self.fecha, self.asunto)


class Borrado(models.Model):
    eraser = models.ForeignKey(GE, on_delete=models.SET_NULL, related_name='ge3', blank=True, null=True)
    mensaje = models.ForeignKey(Mensaje, related_name="mensaje_borrado", on_delete=models.CASCADE)

    class Meta:
        app_label = 'mensajes'

    def __str__(self):
        return u'Borrado por %s (%s) - %s' % (
        self.eraser.gauser.get_full_name(), self.mensaje.fecha, self.mensaje.asunto)


class Leido(models.Model):
    lector = models.ForeignKey(GE, on_delete=models.SET_NULL, related_name='ge4', blank=True, null=True)
    mensaje = models.ForeignKey(Mensaje, related_name="mensaje_leido", on_delete=models.CASCADE)

    class Meta:
        app_label = 'mensajes'

    def __str__(self):
        return u'Leído por %s (%s) - %s' % (self.lector.gauser.get_full_name(), self.mensaje.fecha, self.mensaje.asunto)


class Importante(models.Model):
    marcador = models.ForeignKey(GE, on_delete=models.SET_NULL, related_name='ge5', blank=True, null=True)
    mensaje = models.ForeignKey(Mensaje, related_name="mensaje_importante", on_delete=models.CASCADE)

    class Meta:
        app_label = 'mensajes'

    def __str__(self):
        return u'Marcado como importante por %s (%s) - %s' % (
        self.marcador.gauser.get_full_name(), self.mensaje.fecha, self.mensaje.asunto)


class Aviso(models.Model):
    usuario = models.ForeignKey(GE, on_delete=models.SET_NULL, related_name='ge6', blank=True, null=True)
    aviso = models.TextField("Mensaje de aviso")
    ip = models.CharField("Dirección IP en la que estaba el usuario", max_length=50, null=True, blank=True)
    link = models.CharField("Redireccionamiento", max_length=100, null=True, blank=True)
    fecha = models.DateTimeField("Fecha y hora en la que se generó el aviso")
    aceptado = models.BooleanField("¿Ha sido aceptado/OK?", default=False)

    class Meta:
        app_label = 'mensajes'

    def __str__(self):
        return u'%s (%s)--%s' % (self.aviso, self.fecha, self.usuario)


class Mensaje_cola(models.Model):
    mensaje = models.ForeignKey(Mensaje, blank=True, null=True, on_delete=models.CASCADE)
    receptores = models.TextField("Direcciones de correo separadas por un punto y coma")
    enviado = models.BooleanField("El mensaje ha sido enviado?", default=False)
    ultima_parte = models.BooleanField("Última parte del mensaje encolado?", default=False)
    creado = models.DateTimeField("Fecha y hora de encolar el mensaje", auto_now_add=True)
    modificado = models.DateTimeField("Fecha y hora en la que se envió efectivamente el correo", auto_now=True)
    class Meta:
        ordering = ['creado', 'id']
        app_label = 'mensajes'
    def __str__(self):
        return u'%s (%s - %s)' % (self.mensaje.asunto, self.creado, self.modificado)