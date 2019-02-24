# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from entidades.models import Gauser_extra


class Reparacion(models.Model):
    REPARACIONES = (
        ('inf', 'Informática'),
        ('ele', 'Electricidad'),
        ('fon', 'Fontanería'),
        ('car', 'Carpintería'),
        ('alb', 'Albañilería'),
        ('gen', 'Reparación general'),
    )
    detecta = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    lugar = models.CharField("Lugar", max_length=75, blank=True, null=True)
    tipo = models.CharField("Tipo", max_length=10, choices=REPARACIONES, default='inf')
    describir_problema = models.TextField("Descripción", max_length=300, null=True, blank=True)
    fecha_comunicado = models.DateField("Fecha de comunicación", auto_now_add=True, null=True)
    reparador = models.ForeignKey(Gauser_extra, related_name="reparador", null=True, blank=True, on_delete=models.CASCADE)
    resuelta = models.BooleanField("Incidencia resuelta", default=False)
    fecha_solucion = models.DateField("Fecha de resolución", auto_now=True, null=True)
    describir_solucion = models.TextField("Descripción de la solución", max_length=300, blank=True, null=True)
    borrar = models.BooleanField("Indica si en la próxima recarga debe borrarse", default=True)
    comunicado_a_reparador = models.BooleanField("Indica si se ha enviado un mensaje al reparador", default=False)

    class Meta:
        verbose_name_plural = "reparaciones"
        ordering = ['-fecha_comunicado', 'resuelta']

    def __str__(self):
        return u'Incidencia en %s %s-%s. Comunicada por %s' % (
            self.lugar, self.tipo, self.fecha_comunicado, self.detecta)


