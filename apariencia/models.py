# -*- coding: utf-8 -*-
from django.db import models

# from autenticar.models import Gauser, Gauser_extra
# from entidades.models import Entidad, Ronda
from autenticar.models import Gauser
from entidades.models import Entidad, Ronda, Gauser_extra

from datetime import datetime
import os


class Apariencia(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    code_texto = models.CharField("Código identificador del texto", max_length=100, blank=True, null=True)
    texto_default = models.CharField("Texto por defecto", max_length=300, blank=True, null=True)
    texto = models.CharField("Texto", max_length=300, blank=True, null=True)
    lugar = models.CharField("Lugar en el que está este texto", max_length=200, blank=True, null=True)
    acceso = models.BooleanField("Tiene acceso a esta apariencia?", default=True)

    def __unicode__(self):
        return u'%s ---> %s (%s)' % (self.code_texto, self.texto, self.entidad.code)


class Apariencia_default(models.Model):
    code_texto = models.CharField("Código identificador del texto", max_length=100, blank=True, null=True)
    texto = models.CharField("Texto", max_length=300, blank=True, null=True)
    lugar = models.CharField("Lugar en el que está este texto", max_length=200, blank=True, null=True)

    def __unicode__(self):
        return u'%s ---> %s' % (self.code_texto, self.texto)