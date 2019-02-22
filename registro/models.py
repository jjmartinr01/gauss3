# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime
from django.db import models
import os
from autenticar.models import Gauser
from entidades.models import Entidad


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_fichero(instance, filename):
    instance.fich_name = filename
    ext = filename.partition('.')[2]
    ahora = datetime.now()
    fichero = 'fichero_registro_%s.%s' % (ahora.strftime('%Y%m%d%H%M%f'), ext)
    return os.path.join("registros/", str(instance.entidad.code), fichero)


class Fichero(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero, blank=True)
    fich_name = models.CharField('Nombre del fichero', max_length=200, blank=True, null=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)

    def __unicode__(self):
        return u'%s' % (self.fichero)


class Registro(models.Model):
    TIPOS = (
        ('ENT', 'Entrada'),
        ('SAL', 'Salida'),
    )
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    registrador = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    emisor = models.CharField("Emisor", max_length=300)
    receptor = models.CharField("Receptor", max_length=300)
    tipo = models.CharField("Tipo de registro", max_length=30, choices=TIPOS, blank=True)
    num_id = models.IntegerField("Número de registro en el Entidad")
    ficheros = models.ManyToManyField(Fichero, related_name="adjuntos", blank=True)
    fecha = models.DateField("Fecha del envío o recepción")
    asunto = models.CharField("Asunto", max_length=500)
    texto = models.TextField("Texto explicativo del registro", blank=True)

    def __str__(self):
        return u'%s (%s) - %s' % (self.entidad.name, self.fecha, self.asunto)
