# -*- coding: utf-8 -*-
import re
import os
from django.db import models

from autenticar.models import Gauser
from entidades.models import Entidad, Subentidad, Ronda, Cargo, Gauser_extra

from bancos.models import Banco
from gauss.funciones import pass_generator




def update_file(instance, filename):
    nombre = filename.partition('.')
    nombre = '%s.%s' % (pass_generator(size=10), nombre[2])
    return os.path.join('contabilidad/', nombre)

def update_fichero(instance, filename):
    nombre = filename.rpartition('.')
    instance.fich_name = filename
    fichero = pass_generator(size=20) + '.' + nombre[2]
    return '/'.join(['contabilidad', str(instance.entidad.code), fichero])

class File_contabilidad(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero, blank=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Ficheros de contabilidad"

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def __str__(self):
        return u'%s (%s)' % (self.fichero, self.entidad.name)

class Presupuesto(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    # ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)
    nombre = models.CharField('Nombre del presupuesto', max_length=300, blank=True, null=True)
    describir = models.TextField('Descripción del presupuesto (opcional)', null=True, blank=True)
    archivado = models.BooleanField('Está archivado?', default=False)
    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'Presupuesto de la entidad %s (%s)' % (self.entidad.name, self.modificado)


class Partida(models.Model):
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE)
    tipo = models.CharField('Tipo de partida', max_length=6, choices=(('GASTO', 'Gasto'), ('INGRE', 'Ingreso')))
    nombre = models.CharField('Nombre de la partida', max_length=150)
    cantidad = models.FloatField('Cantidad monetaria (euros)')
    creado = models.DateField('Fecha de creación', auto_now_add=True)  #carga automaticamente la fecha al crearse
    modificado = models.DateField('Fecha de modificación',
                                  auto_now=True)  #carga automaticamente la fecha al modificarse

    def __str__(self):
        #return u'%s - Partida de %s (%s)' % (self.presupuesto.id, self.get_tipo_display(),self.nombre)
        return u'%s (%s)' % (self.nombre, self.get_tipo_display())


class Asiento(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE)
    concepto = models.CharField('Concepto', max_length=100)
    nombre = models.CharField('Pequeña descripción', max_length=250, null=True, blank=True)
    cantidad = models.FloatField('Cantidad monetaria (euros)')
    escaneo = models.ForeignKey(File_contabilidad, blank=True, null=True, related_name='escaneo', on_delete=models.CASCADE)
    creado = models.DateField('Fecha de creación', auto_now_add=True)  #carga automaticamente la fecha al crearse
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    def filename(self):
        return os.path.basename(self.escaneo.name)

    def fileextension(self):
        fileName, fileExtension = os.path.splitext(self.escaneo.name)
        return fileExtension

    def __str__(self):
        return u'%s - %s (%s)' % (self.partida.presupuesto.id, self.concepto, self.cantidad)

###################################################################################################
################################ CUOTAS ###########################################################
###################################################################################################


class Politica_cuotas(models.Model):
    TIPOS_CUOTA = (('fija', 'Cuota fija'), ('hermanos', 'Cuota condicionada al número de hermanos'),
                   ('vut', 'Cuota asociada al número de VUT'),
                   ('domotica', 'Cuota asociada al número de controles domóticos'))
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    tipo = models.CharField('Tipo de cuota', max_length=10, choices=TIPOS_CUOTA, default='fija')
    cargo = models.ForeignKey(Cargo, null=True, blank=True, on_delete=models.CASCADE)
    tipo_cobro = models.CharField('Tipo de cobro', max_length=6, choices=(('MEN', 'Mensual'), ('ANU', 'Anual')))
    cuota = models.CharField('Cuotas separadas por comas', blank=True, null=True, max_length=200)
    cantidad = models.FloatField('Cantidad monetaria (euros)', blank=True, null=True)
    concepto = models.CharField('Concepto', max_length=100)
    exentos = models.ManyToManyField(Gauser, blank=True, help_text='&nbsp;</span><span style="display:none;">')
    descuentos = models.TextField('Descuentos', null=True, blank=True)
    dia = models.IntegerField('Día del mes que se pasa la couta', null=True, blank=True)
    mes = models.IntegerField('Mes de cobro (en caso de couta anual)', null=True, blank=True)
    creado = models.DateField('Fecha de creación', auto_now_add=True)  #carga automaticamente la fecha al crearse
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['-modificado']
        verbose_name_plural = "Políticas de cuotas"

    @property
    def array_cuotas(self):
        if not self.cuota:
            self.cuota = '0'
            self.save()
        importes = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", self.cuota)))
        return importes + [importes[-1]] * 1000

    @property
    def no_exentos(self):
        importes = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", self.cuota)))
        return importes + [importes[-1]] * 1000


    def __str__(self):
        return u'%s - %s (%s)' % (self.entidad.name, self.cargo, self.cantidad)


class Remesa_emitida(models.Model):
    politica = models.ForeignKey(Politica_cuotas, on_delete=models.CASCADE)
    grupo = models.CharField('Cadena que identifica unívocamente un grupo', max_length=40)
    reqdcolltndt = models.DateField('Requested Collection Date', max_length=40, blank=True, null=True)
    ctrlsum = models.FloatField('Control sum', max_length=40, blank=True, null=True)
    nboftxs = models.IntegerField('Number of transactions', blank=True, null=True)
    visible = models.BooleanField('Es visible?', default=True)
    creado = models.DateTimeField('Fecha de creación', auto_now_add=True)

    class Meta:
        ordering = ['-creado']
        verbose_name_plural = "Remesas emitidas"

    def __str__(self):
        return u'%s - %s (%s)' % (self.politica.entidad.name, self.politica.cargo.cargo, self.grupo)

class Remesa(models.Model):
    emitida = models.ForeignKey(Remesa_emitida, on_delete=models.CASCADE)
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE)
    dtofsgntr = models.DateField('Fecha deudor firma mandato')
    dbtrnm = models.CharField('Nombre del deudor', max_length=70)
    dbtriban = models.CharField('IBAN del deudor', max_length=30)
    rmtinf = models.CharField('Información del acreedor al deudor (concepto)', max_length=140)
    instdamt = models.FloatField(
        'Cantidad de dinero')  # string formating: '%.2f' % 1.234 -> limitar el número de decimales
    counter = models.IntegerField('Identificación única de remesa')
    creado = models.DateTimeField('Fecha de creación', auto_now_add=True)

    class Meta:
        verbose_name_plural = "Remesas individuales"

    def __str__(self):
        return u'%s - %s - %s' % (self.emitida.politica.entidad.name, self.rmtinf, self.dbtrnm)


