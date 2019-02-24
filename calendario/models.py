# -*- coding: utf-8 -*-
from django.db import models
from actas.models import Convocatoria

# from autenticar.models import Gauser, Gauser_extra
# from entidades.models import Subentidad, Entidad, Ronda

from autenticar.models import Gauser
from entidades.models import Subentidad, Entidad, Ronda, Gauser_extra

# from entidades.models import Gauser_extra as GE

# class Valarm(models.Model):
#     action = models.CharField('ACTION', max_length=10, default='EMAIL', editable=False)
#     summary = models.CharField('SUMMARY', max_length=150, blank=True, null=True)
#     description = models.TextField('DESCRIPTION', blank=True, null=True)
#     trigger1 = models.DateTimeField('TRIGGER', blank=True, null=True)
#     trigger2 = models.DurationField('Cuanto tiempo antes del evento se debe avisar', blank=True, null=True)


# http://www.kanzaki.com/docs/ical/

propietarios_id = [19, 640, 67, 2699, 75, 76, 77, 15, 81, 12128, 107, 52, 53, 11770, 58, 14607, 93]

propietarios = [(15, u' Javier', u'Anero Tejada'), (19, u' M Lourdes', u'Atares Bescos'),
 (52, u' M Aurora', u'Garc\xeda Fern\xe1ndez de Larrea'), (53, u' Federico Jos\xe9', u'Garc\xeda Garc\xeda'),
 (58, u' Milagros', u'G\xf3mez Crist\xf3bal'), (67, u' Alex\xe1nder', u'Iturbe Laskurain'),
 (75, u' Fabi\xe1n', u'Mart\xedn Herce'), (76, u'Miguel \xc1ngel', u'Mart\xedn N\xfa\xf1ez'),
 (77, u' Juan Jos\xe9', u'Mart\xedn Romero'), (81, u' Sergio', u'Mata Tob\xeda'),
 (93, u' Ignacio', u'P\xe9rez L\xf3pez de Luzuriaga'), (107, u' Sara', u'Sacrist\xe1n Tob\xedas'),
 (640, u'Mar\xeda Blanca', u'Lara Serna'), (2699, u' Natividad', u'Narvarte Sanz'),
 (11770, u' Marta Isabel', u'Arribas Camargo'), (12128, u' Diego', u'Guerrero Vivar'),
 (14607, u'Mar\xeda Montserrat', u'Benito S\xe1nchez')]

propietarios_asocia = [(3355, u' Javier', u'Anero Tejada'), (3357, u' M Lourdes', u'Atares Bescos'),
 (3386, u' M Aurora', u'Garc\xeda Fern\xe1ndez de Larrea'), (3387, u' Federico Jos\xe9', u'Garc\xeda Garc\xeda'),
 (3392, u' Milagros', u'G\xf3mez Crist\xf3bal'), (3402, u' Alex\xe1nder', u'Iturbe Laskurain'),
 (3412, u' Fabi\xe1n', u'Mart\xedn Herce'), (3413, u'Miguel \xc1ngel', u'Mart\xedn N\xfa\xf1ez'),
 (72, u' Juan Jos\xe9', u'Mart\xedn Romero'), (3419, u' Sergio', u'Mata Tob\xeda'),
 (3432, u' Ignacio', u'P\xe9rez L\xf3pez de Luzuriaga'), (3445, u' Sara', u'Sacrist\xe1n Tob\xedas'),
 (5983, u'Mar\xeda Blanca', u'Lara Serna'), (3422, u' Natividad', u'Narvarte Sanz'),
 (3356, u' Marta Isabel', u'Arribas Camargo'), (3395, u' Diego', u'Guerrero Vivar'),
 (5979, u'Mar\xeda Montserrat', u'Benito S\xe1nchez')]

STATUS = (('CONFIRMED', 'Confirmado'), ('TENTATIVE', 'Tentativa'), ('CANCELLED', 'Cancelado'))
TRANS = (('TRANSPARENT', 'Evento transparente en el tiempo'), ('OPAQUE', 'Opaco en el tiempo'))
FREQ = (('MINUTELY', 'Cada minuto'), ('HOURLY', 'Cada hora'), ('DAILY', 'Diariamente'), ('WEEKLY', 'Semanalmente'),
        ('MONTHLY', 'Mensualmente'), ('YEARLY', 'Anualmente'))


class Vevent(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    invitados = models.ManyToManyField(Gauser, blank=True, related_name='invitados')
    subentidades = models.ManyToManyField(Subentidad, blank=True)
    propietarios = models.ManyToManyField(Gauser, blank=True, related_name='propietarios')
    dtstart = models.DateTimeField('DTSTART')
    dtend = models.DateTimeField('DTEND', blank=True, null=True)
    # dtstamp = models.DateTimeField('DTSTAMP', blank=True, null=True)
    uid = models.CharField('UID', max_length=100, blank=True, null=True)
    created = models.DateField('CREATED', auto_now_add=True)
    summary = models.CharField('SUMMARY', max_length=150)
    description = models.TextField('DESCRIPTION', blank=True, null=True)
    modified = models.DateField('LAST-MODIFIED', auto_now=True)
    location = models.CharField('LOCATION', max_length=100, blank=True, null=True)
    sequence = models.IntegerField('SEQUENCE', blank=True, null=True)
    trans = models.CharField('TRANSPARENCY', max_length=15, choices=TRANS, default='TRANSPARENT')
    # RRULE infomation:
    freq = models.CharField('FREQ (rrule)', max_length=10, choices=FREQ, blank=True, null=True)
    count = models.IntegerField('COUNT (rrule)', blank=True, null=True)
    interval = models.IntegerField('INTERVAL (rrule)', blank=True, null=True)
    until = models.DateTimeField('UNTIL (rrule)', blank=True, null=True)
    # La especificación permite definir varias alarmas. Deberíamos entonces crear una clase Valarm y aquí
    # un ManyToMany
    action_alarm = models.CharField('ACTION (alarm)', max_length=10, default='EMAIL', editable=False)
    summary_alarm = models.CharField('SUMMARY (alarm)', max_length=150, blank=True, null=True)
    description_alarm = models.TextField('DESCRIPTION (alarm)', blank=True, null=True)
    trigger1_alarm = models.DateTimeField('TRIGGER (alarm)', blank=True, null=True)
    trigger2_alarm = models.DurationField('Cuanto tiempo antes del evento se debe avisar', blank=True, null=True)

    def __str__(self):
        return u'%s (%s)' % (self.summary, self.dtstart)


class Calendar(models.Model):
    gauser = models.ForeignKey(Gauser, on_delete=models.CASCADE)
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    calname = models.CharField('Nombre del calendario', max_length=150)
    vevents = models.ManyToManyField(Vevent, blank=True)

    def __str__(self):
        return u'Calendario de: %s (%s)' % (self.gauser.get_full_name(), self.calname)
