# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime
import os

import unicodedata
from django.db import models
from autenticar.models import Permiso
from entidades.models import Entidad, Cargo, Gauser_extra
from django.template.defaultfilters import slugify
from django.utils import timezone


def update_fichero(instance, filename):
    # instance.fich_name = filename
    nombre = 'IS%s_%s.pdf' %(instance.sancionado.id, instance.id)
    return '/'.join(['convivencia', str(instance.sancionado.entidad.code), nombre])


TIPOS = (
    ('CNC', 'Contrarias a las normas de convivencia'),
    ('GPC', 'Gravemente perjudicales para la convivencia'),
    ('ROF', 'Contrarias a las normas del centro educativo'),
)


class ConfiguraConvivencia(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    caduca_cnc = models.IntegerField('Número de meses en los que caduca una conducta contraria', default=3)
    caduca_gpc = models.IntegerField('Número de meses en los que caduca una conducta grave', default=6)
    caduca_rof = models.IntegerField('Número de meses en los que caduca una conducta del ROF', default=3)
    expulsar_cnc = models.IntegerField('Número de conductas contrarias para habilitar expulsión', default=5)
    expulsar_gpc = models.IntegerField('Número de conductas graves para habilitar expulsión', default=1)
    expulsar_rof = models.IntegerField('Número de conductas ROF para habilitar expulsión', default=5)
    expulsar_inf = models.IntegerField('Número de informes sancionadores para habilitar expulsión', default=3)
    expediente_cnc = models.IntegerField('Número de conductas contrarias para habilitar expediente', default=17)
    expediente_inf = models.IntegerField('Número de informes sancionadores para habilitar expediente', default=12)

    def __str__(self):
        return u'%s -> caduca_cnc: %s - caduca_gpc: %s - caduca_rof: %s - expulsar_cnc: %s - expulsar_gpc: %s -' \
               u' expulsar_rof: %s - expulsar_inf: %s - expediente_cnc: %s - expediente_inf: %s - ' % (
                   self.entidad, self.caduca_cnc, self.caduca_gpc, self.caduca_rof, self.expulsar_cnc,
                   self.expulsar_gpc, self.expulsar_rof, self.expulsar_inf, self.expediente_cnc, self.expediente_inf)


class Sancion(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    norma = models.CharField('Normativa en la que se apoya', max_length=200, blank=True)
    sancion = models.TextField('Redacción de la sanción')
    tipo = models.CharField('Sanción aplicada a conducta:', max_length=30, choices=TIPOS, blank=True)
    expulsion = models.BooleanField('La sanción conlleva expulsión?', default=False)
    cargos = models.ManyToManyField(Cargo) #Este campo se puede eliminar. A partir de ahora se basa en permiso
    permiso = models.ForeignKey(Permiso, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Sanciones'
        ordering = ['tipo', 'id']

    def __str__(self):
        return u'%s (%s)' % (self.sancion, self.entidad.name)


class Conducta(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    norma = models.CharField('Normativa en la que se apoya', max_length=200, blank=True)
    conducta = models.TextField('Redacción de la conducta')
    tipo = models.CharField('Tipo de conducta', max_length=30, choices=TIPOS, blank=True)
    prescribe = models.IntegerField('Número de días que tarda en prescribir la conducta', default=90)

    class Meta:
        verbose_name_plural = 'Conductas sancionables'
        ordering = ['tipo', 'id']

    def __str__(self):
        return u'%s (%s)' % (self.conducta, self.entidad.name)


class Informe_sancionador(models.Model):
    sancionado = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    sancionador = models.ForeignKey(Gauser_extra, related_name='sancionador', on_delete=models.CASCADE)
    fecha = models.DateField('Fecha de la conducta-sanción', null=True, blank=True)
    conductas = models.ManyToManyField(Conducta, blank=True)
    sanciones = models.ManyToManyField(Sancion, blank=True)
    texto_motivo = models.TextField('Motivo de la sanción', null=True, blank=True, default='')
    texto_sancion = models.TextField('Concreción de la sanción', null=True, blank=True, default='')
    fichero = models.FileField("Fichero informe sancionador", blank=True)
    texto_html = models.TextField('Código html generador del pdf', null=True, blank=True)
    fecha_inicio = models.DateField('Fecha de inicio de la expulsión', null=True, blank=True)
    fecha_fin = models.DateField('Fecha de fin de la expulsión', null=True, blank=True)
    created = models.DateTimeField(null=True, blank=True)
    fecha_incidente = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        return super(Informe_sancionador, self).save(*args, **kwargs)

    @property
    def expulsion(self):
        return self.sanciones.filter(expulsion=True).count() > 0

    @property
    def is_coherente(self):
        c = False
        mensaje= ''
        t_conductas = self.conductas.all().values_list('tipo', flat=True)
        t_sanciones = self.sanciones.all().values_list('tipo', flat=True)

        for t_c in t_conductas:
            if t_c == 'CNC' or t_c == 'ROF':
                c = True if 'CNC' in t_sanciones else False
                if not c:
                    mensaje += '<li>Al seleccionar una conducta contraria, se debe asignar una sanción del mismo tipo.</li>'
            if t_c == 'GPC':
                c = True if 'GPC' in t_sanciones else False
                if not c:
                    mensaje += '<li>Al seleccionar una conducta grave, se debe asignar una sanción del mismo tipo.</li>'
        for t_s in t_sanciones:
            if t_s == 'CNC' or t_s == 'ROF':
                c = True if ('CNC' in t_conductas or 'ROF' in t_conductas) else False
                if not c:
                    mensaje += '<li>Al asignar una sanción contraria, se debe seleccionar una conducta del mismo tipo.</li>'
            if t_s == 'GPC':
                c = True if 'GPC' in t_conductas else False
                if not c:
                    mensaje += '<li>Al asignar una sanción grave, se debe seleccionar una conducta del mismo tipo.</li>'
        if t_conductas.all().count() == 0 or t_sanciones.all().count() == 0:
            mensaje += '<li>Debes seleccionar al menos una conducta y una sanción de las existentes en la lista.</li>'
        return c, mensaje

    class Meta:
        verbose_name_plural = 'Informes sancionadores (Informe_sancionador)'
        ordering = ['fecha_incidente']

    def __str__(self):
        return 'Informe sancionador a %s. Entidad: %s (%s)' % (
            self.sancionado, self.sancionado.ronda.entidad.name, self.sancionador)

class FechaExpulsion(models.Model):
    informe = models.ForeignKey(Informe_sancionador, on_delete=models.CASCADE)
    fecha = models.DateField('Día en el que el usuario está expulsado', null=True, blank=True)

    def __str__(self):
        return u'Informe sancionador a %s expulsado el día %s' % (self.informe.sancionado, self.fecha)

class Expulsar(models.Model):
    expulsado = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    expulsa = models.ForeignKey(Gauser_extra, related_name='redactor_sancion', on_delete=models.CASCADE)
    fecha = models.DateField('Fecha de emisión de la expulsión')
    fecha_inicio = models.DateField('Fecha de emisión de la expulsión')
    fecha_fin = models.DateField('Fecha de emisión de la expulsión')
    texto_adicional = models.TextField('Texto a adjuntar en la sanción', null=True, blank=True)
    texto_html = models.TextField('Código html generador del pdf', null=True, blank=True)
    # fichero = models.CharField('fichero (pdf)', max_length=200)
    # fichero = models.ForeignKey(ConvivenciaFile, related_name="informe_expulsar", blank=True, on_delete=models.CASCADE)
    fichero = models.FileField("Fichero de la expulsión", upload_to=update_fichero, blank=True)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'Expulsiones'

    def __str__(self):
        return 'Informe de expulsión a %s. Entidad: %s (%s)' % (
            self.expulsado, self.expulsado.ronda.entidad.name, self.expulsa)
