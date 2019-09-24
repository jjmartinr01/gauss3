from django.db import models
from django.utils.timezone import now, timedelta

from entidades.models import Gauser_extra, Ronda
# Create your models here.

class ConfiguraMoscosos(models.Model):
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE, blank=True, null=True)
    max_persona = models.IntegerField('Máximo número de días por persona', null=True, default=2)
    max_personas_day = models.IntegerField('Máximo número de personas por día', null=True, default=4)
    autoriza = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, blank=True, null=True)
    creado = models.DateTimeField("Fecha y hora en el que se graba la reserva", auto_now_add=True)

    def __str__(self):
        return u'%s - (%s)' % (self.ronda, self.max_persona)


class FechaNoPermitida(models.Model):
    cm = models.ForeignKey(ConfiguraMoscosos, on_delete=models.CASCADE, blank=True, null=True)
    fecha = models.DateField('Fecha no permitida', blank=True, null=True, default=now)

    def __str__(self):
        return u'%s - (%s)' % (self.fecha, self.cm)

class Moscoso(models.Model):
    ESTADO = (('ACE', 'Aceptado'), ('NAC', 'No aceptado'), ('PRO', 'En proceso'), ('PEN', 'Pendiente de valorar'))
    cm = models.ForeignKey(ConfiguraMoscosos, on_delete=models.CASCADE, blank=True, null=True)
    solicita = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, blank=True, null=True)
    fecha = models.DateField('Fecha y hora de entrada', blank=True, null=True, default=now)
    estado = models.CharField('Estado', max_length=3, default='PRO', choices=ESTADO)
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')
    creado = models.DateTimeField("Fecha y hora en el que se graba la reserva", auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'creado']

    # @property
    # def salida2(self):
    #     return self.entrada + timedelta(self.noches)

    # def save(self, *args, **kwargs):
    #     self.salida = self.entrada + timedelta(self.noches)
    #     super(Reserva, self).save(*args, **kwargs)

    def __str__(self):
        return u'%s - %s - (%s)' % (self.solicita, self.fecha, self.get_estado_display())
