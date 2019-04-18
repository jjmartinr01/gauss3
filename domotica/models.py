from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from autenticar.models import Gauser
from gauss.funciones import pass_generator

# Create your models here.


class Grupo(models.Model):
    propietario = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    grupo_padre = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL)
    nombre = models.CharField('Nombre del lugar', blank=True, null=True, max_length=250)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    def permiso(self, gauser):
        try:
            return GauserPermitidoGrupo.objects.get(gauser=gauser, grupo=self).permiso
        except:
            return None

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s (Padre: %s)' % (self.nombre, self.grupo_padre)

@receiver(post_save, sender=Grupo)
def delete_gauserpermitidogrupo(sender, instance, *args,**kwargs):
    GauserPermitidoGrupo.objects.get_or_create(gauser=instance.propietario, grupo=instance, permiso='VUEB')


class GauserPermitidoGrupo(models.Model):
    PERMISOS = (('VU', 'Ve el lugar/ubicación'), ('VUE', 'Puede usar y editar el lugar'),
                ('VUEB', 'Puede usar, editar y borrar el lugar'))
    gauser = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, blank=True, null=True, on_delete=models.CASCADE)
    permiso = models.CharField("Permiso", max_length=8, default='USAR')
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s -- %s (%s)' % (self.gauser, self.grupo, self.permiso)


class Dispositivo(models.Model):
    TIPO_DOMOTICA = (
    ('SELFLOCKING', 'Auto-bloqueo'), ('ONOFF', 'Interruptor'), ('TERMOSTATO', 'Control de temperatura'),
    ('TH', 'Control de temperatura y humedad'))
    propietario = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, blank=True, null=True, on_delete=models.SET_NULL)
    url1 = models.CharField('URL 1 comunicación con el dispositivo', blank=True, null=True, max_length=250, default='')
    url2 = models.CharField('URL 2 comunicación con el dispositivo', blank=True, null=True, max_length=250, default='')
    url3 = models.CharField('URL 3 comunicación con el dispositivo', blank=True, null=True, max_length=250, default='')
    nombre = models.CharField('Nombre dado al dispositivo', blank=True, null=True, max_length=250)
    texto = models.TextField('Texto a enviar', blank=True, null=True, default='')
    tipo = models.CharField('Tipo de dispositivo', max_length=15, default='SELFLOCKING', choices=TIPO_DOMOTICA)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    def permiso(self, gauser):
        try:
            return GauserPermitidoDispositivo.objects.get(gauser=gauser, dispositivo=self).permiso
        except:
            return None

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.get_tipo_display())

@receiver(post_save, sender=Dispositivo)
def delete_gauserpermitidodispositivo(sender, instance, *args,**kwargs):
    GauserPermitidoDispositivo.objects.get_or_create(gauser=instance.propietario, permiso='VUEB',
                                                     dispositivo=instance)


class GauserPermitidoDispositivo(models.Model):
    PERMISOS = (('VU', 'Puede usar el dispositivo'), ('VUE', 'Puede usar y editar el dispositivo'),
                ('VUEB', 'Puede usar, editar y borrar el dispositivo'))
    gauser = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    dispositivo = models.ForeignKey(Dispositivo, blank=True, null=True, on_delete=models.CASCADE)
    permiso = models.CharField("Permiso", max_length=8, default='USAR')
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s (%s)' % (self.gauser, self.permiso)

class Secuencia(models.Model):
    propietario = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre dado a la secuencia', blank=True, null=True, max_length=250)
    texto = models.TextField('Texto a enviar', blank=True, null=True)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.texto[:20])


class DispositivoSecuencia(models.Model):
    secuencia = models.ForeignKey(Secuencia, blank=True, null=True, on_delete=models.CASCADE)
    dispositivo = models.ForeignKey(Dispositivo, blank=True, null=True, on_delete=models.CASCADE)
    orden = models.IntegerField('Orden de ejecución', blank=True, null=True)
    retraso = models.IntegerField('Retraso (ms) de ejecución tras el dispositivo anterior', blank=True, null=True)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s (%s)' % (self.secuencia, self.dispositivo)

class GauserPermitidoSecuencia(models.Model):
    PERMISOS = (('VU', 'Puede usar la secuencia'), ('VUE', 'Puede usar y editar la secuencia'),
                ('VUEB', 'Puede usar, editar y borrar la secuencia'))
    gauser = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    secuencia = models.ForeignKey(Secuencia, blank=True, null=True, on_delete=models.CASCADE)
    permiso = models.CharField("Permiso", max_length=8, default='USAR')
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s (%s)' % (self.gauser, self.permiso)

# class Conjunto(models.Model):
    # propietario = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    # nombre = models.CharField('Nombre dado al conjunto de dispositivos', blank=True, null=True, max_length=250)
    # texto = models.TextField('Texto descriptivo', blank=True, null=True)
    # creado = models.DateField('Fecha de creación', auto_now_add=True)
    # modificado = models.DateField('Fecha de modificación', auto_now=True)
    #
    # class Meta:
    #     managed = False

    # def __str__(self):
    #     return u'%s (%s)' % (self.nombre, self.texto[:20])


# class DispositivoConjunto(models.Model):
    # conjunto = models.ForeignKey(Conjunto, blank=True, null=True, on_delete=models.CASCADE)
    # dispositivo = models.ForeignKey(Dispositivo, blank=True, null=True, on_delete=models.CASCADE)
    # orden = models.IntegerField('Orden de ejecución', blank=True, null=True)
    # creado = models.DateField('Fecha de creación', auto_now_add=True)
    # modificado = models.DateField('Fecha de modificación', auto_now=True)
    #
    # class Meta:
    #     managed = False

    # def __str__(self):
    #     return u'%s (%s)' % (self.conjunto, self.dispositivo)

# class GauserPermitidoConjunto(models.Model):
#     PERMISOS = (('VER', 'Puede usar el grupo '), ('EDITAR', 'Puede usar y editar el lugar'),
#                 ('BORRAR', 'Puede usar, editar y borrar el lugar'))
#     gauser = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
#     conjunto = models.ForeignKey(Lugar, blank=True, null=True, on_delete=models.CASCADE)
#     permiso = models.CharField("Permiso", max_length=8, default='USAR')
#     creado = models.DateField('Fecha de creación', auto_now_add=True)
#     modificado = models.DateField('Fecha de modificación', auto_now=True)
#
#     class Meta:
#         ordering = ['-creado']
#
#     def __str__(self):
#         return u'%s (%s)' % (self.gauser, self.permiso)

# class GauserPermitido(models.Model):
#     class Meta:
#         managed = False

def clave_secreta():
    return pass_generator(size=10)

class EnlaceDomotica(models.Model):
    propietario = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre identificativo de este enlace", max_length=120, blank=True, null=True)
    secret = models.CharField("Código secreto del enlace", max_length=20, default=clave_secreta)
    valido_desde = models.DateTimeField("Válido desde la fecha:", blank=True, null=True)
    valido_hasta = models.DateTimeField("Válido hasta la fecha:", blank=True, null=True)
    dispositivos = models.ManyToManyField(Dispositivo, blank=True)
    secuencias = models.ManyToManyField(Secuencia, blank=True)

    class Meta:
        ordering = ['valido_desde']

    def __str__(self):
        return u'%s (%s - %s)' % (self.propietario, self.valido_desde, self.valido_hasta)