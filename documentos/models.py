# -*- coding: utf-8 -*-
import os

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.db.models import Q

# from autenticar.models import Gauser_extra, Gauser
from entidades.models import Subentidad, Entidad, Cargo
from entidades.models import Gauser_extra as GE
from autenticar.models import Gauser
# from entidades.models import Subentidad, Entidad, Cargo, Gauser_extra

from gauss.funciones import pass_generator
from gauss.rutas import RUTA_BASE


class Etiqueta_documental(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    nombre = models.CharField("Carpeta/Etiqueta", max_length=300, null=True, blank=True)
    padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    @property
    def hijos(self):
        lista = [self]
        try:
            for e in Etiqueta_documental.objects.filter(padre=self):
                lista = lista + e.hijos
            return lista
        except:
            return lista

    @property
    def etiquetas(self):
        lista = [self.nombre]
        try:
            lista = lista + self.padre.etiquetas
            return lista
        except:
            return lista

    @property
    def etiquetas_text(self):
        return '/'.join(reversed(self.etiquetas))

    class Meta:
        verbose_name_plural = "Etiquetas/Carpetas para los Documentos"

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.entidad.name)


def update_fichero_documental(instance, filename):
    nombre = filename.partition('.')
    instance.fich_name = filename.rpartition('/')[2].replace(' ', '_')
    nombre = pass_generator(size=20) + '.' + nombre[2]
    return '/'.join(['documentos', str(instance.propietario.ronda.entidad.code), nombre])


def update_fichero_contrato(instance, filename):
    nombre = filename.partition('.')
    nombre = 'Contrato_' + str(instance.entidad.id) + '.' + nombre[2]
    return '/'.join(['documentos', str(instance.entidad.code), nombre])


class Ges_documental(models.Model):
    propietario = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True, related_name='ge20')
    etiqueta = models.ForeignKey(Etiqueta_documental, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre del documento", max_length=240)
    acceden = models.ManyToManyField(Subentidad, blank=True)
    cargos = models.ManyToManyField(Cargo, blank=True)
    key_words = models.CharField("Palabras clave", max_length=250, blank=True, null=True)
    texto = models.TextField("Texto del documento o resumen", blank=True, null=True)
    fichero = models.FileField("Fichero con documento", upload_to=update_fichero_documental, blank=True, null=True)
    fich_name = models.CharField("Nombre del fichero", max_length=100, blank=True, null=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    def permisos(self, g_e):
        q1 = Q(subentidad__in=g_e.subentidades.all()) | Q(cargo__in=g_e.cargos.all()) | Q(gauser=g_e.gauser)
        q2 = Q(documento=self)
        return ''.join(Compartir_Ges_documental.objects.filter(q1, q2).values_list('permiso', flat=True))

    class Meta:
        ordering = ['-creado']
        verbose_name_plural = "Documentos (Gestión Documental)"

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.creado)


@receiver(pre_delete, sender=Ges_documental)
def fichero_del_pre_delete(sender, **kwargs):
    try:
        archivo = RUTA_BASE + kwargs['instance'].fichero.url
        # archivo = kwargs['instance'].fichero.path
        if os.path.isfile(archivo):
            os.remove(archivo)
    except:
        pass


PERMISOS = (('r', 'lectura'),
            ('rw', 'lectura y escritura'),
            ('rwx', 'lectura, escritura y borrado'),)


class Permiso_Ges_documental(models.Model):
    gauser = models.ForeignKey(Gauser, on_delete=models.CASCADE)
    documento = models.ForeignKey(Ges_documental, on_delete=models.CASCADE)
    permiso = models.CharField('Permiso sobre el documento', max_length=15, choices=PERMISOS)

    def __str__(self):
        return u'%s (%s)' % (self.documento.nombre, self.gauser.get_full_name())


class Compartir_Ges_documental(models.Model):
    documento = models.ForeignKey(Ges_documental, on_delete=models.CASCADE, null=True, blank=True)
    subentidad = models.ForeignKey(Subentidad, on_delete=models.CASCADE, blank=True, null=True)
    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE, blank=True, null=True)
    gauser = models.ForeignKey(Gauser, on_delete=models.CASCADE, null=True, blank=True)
    permiso = models.CharField('Permiso sobre el documento', max_length=15, choices=PERMISOS, default='r')

    def __str__(self):
        return u'%s (%s)' % (self.documento.nombre, self.permiso)


class Contrato_gauss(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    firma_gauss = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True, related_name='firma_gauss21')
    firma_entidad = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name='firma_entidad2')
    texto = models.TextField("Texto del contrato")
    fichero = models.FileField("Contrato firmado", upload_to=update_fichero_contrato, blank=True, null=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = "Contratos con entidades"

    def __str__(self):
        return u'%s (%s)' % (self.entidad, self.modificado)
