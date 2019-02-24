# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from entidades.models import Gauser_extra


# Create your models here.

class ExpedienteAbsentismo(models.Model):
    expedientado = models.ForeignKey(Gauser_extra, related_name="actuaciones", on_delete=models.CASCADE)
    matricula = models.BooleanField('Efectúo matrícula', default=True)
    # curso = models.CharField('Curso en el que se encuentra matriculado', default=' ', max_length=50)
    uce = models.CharField('Último curso escolar en el que estuvo matriculado', default=' ', max_length=50)
    etapa_uce = models.CharField('Etapa en el último curso escolar matriculado', default=' ', max_length=50)
    curso_uce = models.CharField('Último curso matriculado', default=' ', max_length=50)
    centro_uce = models.CharField('Último centro en el que estuvo matriculado', default=' ', max_length=50)
    localidad_uce = models.CharField('Localidad último centro matriculado', default=' ', max_length=50)
    director = models.CharField('Director del centro que firma el expediente', default=' ', max_length=70)
    presidente = models.CharField('Presidente comisión de absentismo', default=' ', max_length=70)
    creado = models.DateField("Fecha de creación", auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Expedientes de absentismo'
        ordering = ['expedientado__entidad', 'expedientado']

    def __str__(self):
        return u'%s (%s)' % (self.expedientado.gauser.get_full_name(), self.creado)


class Actuacion(models.Model):
    expediente = models.ForeignKey(ExpedienteAbsentismo, on_delete=models.CASCADE)
    realizada_por = models.ForeignKey(Gauser_extra, related_name="realizada_por", on_delete=models.CASCADE)
    # actuado = models.ForeignKey(Gauser_extra, related_name="actuaciones", on_delete=models.CASCADE)
    contacto = models.CharField("Nombre de la persona con la que se ha contactado", max_length=250, null=True,
                                blank=True)
    fecha = models.DateField("Fecha de la actuación", null=True, blank=True)
    faltas = models.IntegerField("Número de faltas de asistencia del alumno en el momento de la actuación", null=True,
                                 blank=True)
    observaciones = models.TextField("Observaciones/Notas de la actuación", null=True, blank=True)
    creado = models.DateField("Fecha de creación", auto_now_add=True)  # carga automaticamente la fecha al crearse

    @property
    def tutor(self):

        return
    class Meta:
        verbose_name_plural = 'Actuaciones de absentismo'
        ordering = ['expediente__expedientado', 'fecha']

    def __str__(self):
        return u'%s (%s)' % (self.expediente.expedientado.gauser.get_full_name(), self.fecha)
