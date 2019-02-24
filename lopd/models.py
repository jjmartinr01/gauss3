# -*- coding: utf-8 -*-
import os

from django.db import models
import unicodedata

# from autenticar.models import Gauser, Gauser_extra
from entidades.models import Subentidad, Entidad
from entidades.models import Gauser_extra as GE
from autenticar.models import Gauser
# from entidades.models import Subentidad, Entidad, Gauser_extra


# def update_fichero_documental(instance, filename):
#     nombre = filename.partition('.')
#     instance.fich_name = filename.replace(' ', '_')
#     nombre = pass_generator(size=20) + '.' + nombre[2]
#     return '/'.join(['documentos', str(instance.propietario.entidad.code), nombre])
#
# def update_fichero_contrato(instance, filename):
#     nombre = filename.partition('.')
#     nombre = 'Contrato_' + str(instance.entidad.id) + '.' + nombre[2]
#     return '/'.join(['documentos', str(instance.entidad.code), nombre])



class Estructura_lopd(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    encargado_tratamiento = models.CharField('Encargado del Tratamiento', max_length=300, blank=True, null=True)
    responsables_fichero = models.ManyToManyField(Gauser, blank=True, related_name='responsable_fichero')
    responsables_seguridad = models.ManyToManyField(Gauser, blank=True, related_name='responsable_seguridad')
    delegados_proteccion = models.ManyToManyField(Gauser, blank=True, related_name='delegados_proteccion')
    doc_seguridad = models.TextField('Contenido html del documento de seguridad', blank=True, null=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'Estructuras LOPD'
    def __str__(self):
        return u'%s' % (self.entidad.name)



def update_fichero_incidencias(instance, filename):
    instance.fich_name = filename
    nombre = (instance.propietario.gauser.username + '-' + filename).replace(' ', '_')
    nombre = ''.join((c for c in unicodedata.normalize('NFD', nombre) if unicodedata.category(c) != 'Mn'))
    return '/'.join(['incidencias_lopd', str(instance.propietario.entidad.code), nombre])


class Fichero_incidencia(models.Model):
    propietario = models.ForeignKey(GE, on_delete=models.SET_NULL, related_name='propietario_fichero30', blank=True, null=True)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero_incidencias, blank=True)
    fich_name = models.CharField("Nombre del fichero", max_length=100, blank=True, null=True)

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def nombre_fichero(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def __str__(self):
        return u'%s (%s)' % (self.fichero, self.propietario.gauser.get_full_name())

TIPOS_INCIDENCIA =(('IDAU', 'Identificación y autenticación de usuarios'),
                   ('DEAC', 'Derechos de acceso a datos'),
                   ('DERE', 'Derechos de rectificación de datos'),
                   ('DECA', 'Derechos de cancelación de datos'),
                   ('DEOP', 'Derechos de oposición al uso de datos'),
                   ('GESO', 'Gestión de soportes'),
                   ('PRCO', 'Procedimientos de copias de seguridad'),
                   ('OTRA', 'Otro tipo no recogido'))

class Incidencia_lopd(models.Model):
    emisor_incidencia = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True, related_name='emisor_incidencia30')
    tipo = models.CharField('Tipo de incidencia', max_length=10, choices= TIPOS_INCIDENCIA)
    incidencia = models.TextField('Descripción de la incidencia', blank=True, null=True)
    ficheros = models.ManyToManyField(Fichero_incidencia, related_name="ficheros", blank=True)
    fecha_emite = models.DateField('Fecha de notificación de la incidencia', auto_now_add=True)
    resuelta = models.BooleanField('¿La incidencia está resuelta?', default=False)
    resolvedor = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True, related_name='resolvedor30')
    fecha_resuelve = models.DateField('Fecha en la que se resuelve la incidencia', blank=True, null=True)
    observaciones = models.TextField('Observaciones en relación a la solución de la incidencia', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Incidencias relacionadas con la LOPD'
    def __str__(self):
        return u'%s - %s (%s)' % (self.emisor_incidencia.entidad.name, self.get_tipo_display(), self.fecha_emite)

class Soporte_lopd(models.Model):
    entidad = models.ForeignKey(Entidad,blank=True,null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre", max_length=300,blank=True,null=True)
    lugar = models.CharField("Lugar en el que se encuentra", max_length=300,blank=True,null=True)
    observaciones = models.TextField("Observaciones", blank=True,null=True)
    creado = models.DateField("Fecha de creación", auto_now=True)

    def __str__(self):
        return u'%s' % (self.entidad.name)
