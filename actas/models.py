# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re
from django.db import models
from django.utils import timezone
from autenticar.models import Gauser
from entidades.models import Subentidad, Cargo, Entidad
from entidades.models import Gauser_extra as GE
from gauss.rutas import RUTA_MEDIA


def iniciales(s):  # Función para devolver las iniciales de una cadena
    s = s.split()
    iniciales = ''
    for e in s:
        if len(e) > 2: iniciales += e[0].upper()
    return iniciales


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_fichero(instance, filename):
    fichero = '%s/acta_%s.pdf' % (instance.convocatoria.entidad.code, instance.id)
    ruta = os.path.join("actas/", fichero)
    return ruta


class Convocatoria(models.Model):
    creador = models.ForeignKey(Gauser, blank=True, null=True, related_name='creador', on_delete=models.CASCADE)
    convoca = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Título de la convocatoria", max_length=300, blank=True, null=True)
    cargo_convocante = models.ForeignKey(Cargo, blank=True, null=True, on_delete=models.CASCADE)
    lugar = models.CharField('Lugar de la convocatoria', max_length=300, blank=True, null=True, default='')
    texto_convocatoria = models.TextField("Texto de la convocatoria", blank=True, null=True)
    convocados = models.ManyToManyField(Subentidad, blank=True)
    personas_convocadas = models.ManyToManyField(GE, blank=True)
    fecha_hora = models.DateTimeField("Fecha y hora de la convocatoria", blank=True, null=True, default=timezone.now)
    plantilla = models.BooleanField("Es una convocatoria de prueba de una configuración", default=False)
    basada_en = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='configura')
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)
    educa_pk = models.IntegerField("pk de la convocatoria en gauss_educa", blank=True, null=True)

    class Meta:
        ordering = ['-fecha_hora']

    def __unicode__(self):
        try:
            return u'%s (%s) -- %s' % (self.nombre, self.fecha_hora, self.entidad)
        except:
            return u'%s (%s)' % (self.nombre, self.fecha_hora)


class Punto_convocatoria(models.Model):
    convocatoria = models.ForeignKey(Convocatoria, blank=True, null=True, related_name='punto',
                                     on_delete=models.CASCADE)
    punto = models.TextField("Texto de la convocatoria", blank=True, null=True)

    class Meta:
        ordering = ['convocatoria']

    def __unicode__(self):
        return u'%s (%s)' % (self.convocatoria, self.punto[:100])


class Acta(models.Model):
    convocatoria = models.ForeignKey(Convocatoria, blank=True, null=True, on_delete=models.CASCADE)
    redacta = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Título del acta", max_length=300, blank=True, null=True)
    contenido_html = models.TextField("Texto del acta", blank=True, null=True)
    pdf = models.FileField("Fichero generado", upload_to=update_fichero, blank=True, null=True)
    pdf_escaneado = models.FileField("Subir el fichero escaneado", upload_to=update_fichero, blank=True, null=True)
    publicada = models.BooleanField("Publicar para lectura antes de aprobar", default=False)
    fecha_aprobacion = models.DateField("Fecha en la que se aprobó el acta", null=True, blank=True)
    asistentes = models.ManyToManyField(GE, blank=True, related_name='asistentes')
    num_last_page = models.IntegerField('Número de la última página', blank=True, null=True)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    @property
    def acta_anterior(self):
        if self.convocatoria.basada_en:
            convocatorias_anteriores = Convocatoria.objects.filter(fecha_hora__lt=self.convocatoria.fecha_hora,
                                                                   basada_en=self.convocatoria.basada_en)
            if convocatorias_anteriores.count() > 0:
                convocatoria_anterior = convocatorias_anteriores[0]
                return Acta.objects.get(convocatoria=convocatoria_anterior)
            else:
                return None
        else:
            return None

    @property
    def num_last_page_acta_anterior(self):
        if self.acta_anterior:
            return self.acta_anterior.num_last_page
        else:
            return 0

    @property
    def num_pages(self):
        # http://code.activestate.com/recipes/496837-count-pdf-pages/
        rxcountpages = re.compile(r"/Type\s*/Page([^s]|$)", re.MULTILINE | re.DOTALL)
        data = self.pdf.read()
        return len(rxcountpages.findall(data))

    class Meta:
        ordering = ['-convocatoria__fecha_hora']

    def __unicode__(self):
        try:
            return u'Acta de la convocatoria de %s (%s) - %s' % (
                self.convocatoria.nombre, self.convocatoria.fecha_hora, self.convocatoria.convocante.entidad.name)
        except:
            return u'Acta de la convocatoria de %s (%s)' % (
                self.convocatoria.nombre, self.convocatoria.fecha_hora)


class Acuerdo_acta(models.Model):
    acta = models.ForeignKey(Acta, blank=True, null=True, on_delete=models.CASCADE)
    acuerdo = models.TextField("Acuerdo", blank=True, null=True)

    class Meta:
        ordering = ['acta']

    def __unicode__(self):
        return u'%s (%s)' % (self.acta, self.acuerdo)
