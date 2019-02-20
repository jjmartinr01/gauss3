# -*- coding: utf-8 -*-
from django.db import models

# from autenticar.models import Gauser_extra
# from entidades.models import Gauser_extra
from entidades.models import Gauser_extra as GE

TALLAS = (('6', 'Talla 6'),
          ('8', 'Talla 8'),
          ('10', 'Talla 10'),
          ('12', 'Talla 12'),
          ('14', 'Talla 14'),
          ('S', 'Talla S'),
          ('M', 'Talla M'),
          ('L', 'Talla L'),
          ('XL', 'Talla XL'),
          ('XXL', 'Talla XXL'),
          ('XXXL', 'Talla XXXL'))

TIPOS = (('polo_corta', 'Polo manga corta'),
         ('polo_larga', 'Polo manga larga'),
         ('neckerchief', 'Pañoleta'),
)

class Uniforme(models.Model):
    solicitante = models.ForeignKey(GE, on_delete=models.SET_NULL, related_name='solicitante50', blank=True, null=True)
    gauser_extra = models.ForeignKey(GE, on_delete=models.SET_NULL, related_name='g_e50', blank=True, null=True)
    talla = models.CharField("Talla del polo", max_length=10, choices=TALLAS, blank=True, null=True)
    tipo = models.CharField("Tipo", max_length=15, choices=TIPOS)
    pagado = models.NullBooleanField('¿Está pagado?', default=False)
    entregado = models.NullBooleanField('¿Está entregado?', default=False)
    campo1 = models.CharField("Campo 1", max_length=100, blank=True, null=True)
    campo2 = models.CharField("Campo 2", max_length=100, blank=True, null=True)
    campo3 = models.CharField("Campo 3", max_length=100, blank=True, null=True)
    observaciones = models.TextField('Observaciones', blank=True, null=True)
    fecha_pedido = models.DateField("Fecha del pedido", auto_now_add=True)

    def __unicode__(self):
        return u'%s (%s)' % (self.gauser_extra, self.talla)
