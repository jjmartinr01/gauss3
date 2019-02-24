# -*- coding: utf-8 -*-
from django.db import models
from entidades.models import Entidad
from autenticar.models import Gauser
import os


class Item(models.Model):
    entidad = models.ForeignKey(Entidad)
    nombre = models.CharField("Texto identificativo", max_length=70)
    codigo = models.CharField("Código de barras/QR asociado", max_length=70)
    descripcion = models.TextField("Descripción")
    lugar = models.CharField("Lugar de almacenaje", max_length=70)
    prestado_a = models.ForeignKey(Gauser, blank=True, null=True) #Persona a quién se ha prestado
    prestado_fecha = models.DateField('Fecha de prestado')
    creado = models.DateField('Fecha de creación',auto_now_add=True) #carga automaticamente la fecha al crearse
    modificado = models.DateField('Fecha de modificación',auto_now=True) #carga automaticamente la fecha al modificarse
    def __str__(self):
      return u'Tipo: %s (%s) -- %s' % (self.nombre, self.entidad.name, self.creado)