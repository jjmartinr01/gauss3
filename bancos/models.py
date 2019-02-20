# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


# Create your models here.

class Banco(models.Model):
    nombre = models.CharField("Nombre del banco", max_length=350, null=True, blank=True)
    nif = models.CharField("NIF", max_length=25, null=True, blank=True)
    codigo = models.CharField("Código de cuatro dígitos", max_length=10, null=True, blank=True)
    tipo = models.CharField("Tipo de entidad bancaria", max_length=100, null=True, blank=True)
    bic = models.CharField("BIC/SWIFT", max_length=15, null=True, blank=True)
    address = models.CharField("Dirección", max_length=250, null=True, blank=True)
    cp = models.CharField("Código postal", max_length=15, null=True, blank=True)
    pais = models.CharField("País", max_length=150, null=True, blank=True)
    tel = models.CharField("Teléfono", max_length=15, null=True, blank=True)
    fax = models.CharField("Fax", max_length=15, null=True, blank=True)
    web = models.CharField("Página web", max_length=50, null=True, blank=True)

    def __unicode__(self):
        return u'%s (%s)' % (self.nombre, self.nif)
