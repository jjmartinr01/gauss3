# -*- coding: utf-8 -*-
import os

from django.db import models

from autenticar.models import Gauser
from entidades.models import Entidad
from gauss.funciones import pass_generator


class Categoria_objeto(models.Model):
    categoria = models.CharField('Categoría', max_length=100, blank=True, null=True)
    subcategoria = models.CharField('Subcategoría', max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return u'%s -> %s' % (self.categoria, self.subcategoria)

# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_fichero(instance, filename):
    nombre = filename.rpartition('.')
    instance.fich_name = filename
    fichero = pass_generator(size=30) + '.' + nombre[2]
    return '/'.join(['compraventa', str(instance.entidad.code), fichero])


class Foto_objeto(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero, blank=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]


    def __str__(self):
        return u'%s (%s)' % (self.fichero, self.entidad.name)


class Articulo(models.Model):
    FORMATOS = (
        ('FIJ', 'Producto con precio fijo'),
        ('SUB', 'Producto para ser subastado'),
        ('SER', 'Oferta de servicio o trabajo'),
        )
    ESTADOS = (
        ('DISPONIBLE', 'Está disponible'),
        ('RESERVADO', 'Está reservado para un posible comprador'),
        ('VENDIDO', 'Está vendido'),
        )
    vendedor = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre del objeto a vender", max_length=100, blank=True, null=True)
    # Varios objetos iguales vendidos por el mismo vendedor tendrán el mismo codigo:
    codigo = models.CharField("Código identificador del objeto", max_length=50, blank=True, null=True)
    precio = models.FloatField("Precio de la unidad", blank=True, null=True)
    precio_envio = models.FloatField("Precio por enviar", blank=True, null=True)
    formato = models.CharField("Formato", max_length=10, choices=FORMATOS)
    descripcion = models.TextField("Descripción del producto", blank=True, null=True)
    pago = models.TextField("Describe cómo se debe realizar el pago", blank=True, null=True)
    entrega = models.TextField("Describe cómo se realiza la entrega del objeto al comprador", blank=True, null=True)
    fotos = models.ManyToManyField(Foto_objeto, blank=True)
    categorias = models.ManyToManyField(Categoria_objeto, blank=True)
    estado = models.CharField("Estado del artículo", default='DISPONIBLE', max_length=15, choices=ESTADOS)
    reservado = models.BooleanField('¿Ya ha sido reservado?', blank=True, null=True)
    comprado = models.BooleanField('¿Ya ha sido comprado?', blank=True, null=True)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return u'%s' % (self.nombre)

class Comprador(models.Model):
    articulo = models.ForeignKey(Articulo, blank=True, null=True, on_delete=models.CASCADE)
    comprador = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    oferta = models.FloatField('Cantidad ofrecida', blank=True, null=True)
    observaciones = models.TextField('Observaciones realizadas del producto', blank=True, null=True)
    fecha_hora = models.DateTimeField('Fecha y hora de la oferta', auto_now_add=True)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return u'Compra: %s' % (self.articulo.nombre)

