# from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from entidades.models import Entidad
from autenticar.models import Gauser
from gauss.funciones import pass_generator


class Etiqueta_domotica(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    nombre = models.CharField("Carpeta/Etiqueta", max_length=300, null=True, blank=True)
    padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    @property
    def hijos(self):
        lista = [self]
        try:
            for e in Etiqueta_domotica.objects.filter(padre=self):
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
def delete_gauserpermitidogrupo(sender, instance, *args, **kwargs):
    GauserPermitidoGrupo.objects.get_or_create(gauser=instance.propietario, grupo=instance, permiso='VUEB')


class GauserPermitidoGrupo(models.Model):
    PERMISOS = (('VU', 'Ve el grupo'), ('VUE', 'Puede usar y editar el grupo'),
                ('VUEB', 'Puede usar, editar y borrar el grupo'))
    gauser = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, blank=True, null=True, on_delete=models.CASCADE)
    permiso = models.CharField("Permiso", max_length=8, default='VU')
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s -- %s (%s)' % (self.gauser, self.grupo, self.permiso)


def mqtt_id_generator():
    generado = pass_generator(size=10, chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return 'ID%s' % generado


def mqtt_topic_generator():
    generado = pass_generator(size=10, chars='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return 'DOMOTICA/%s' % generado


class Dispositivo(models.Model):
    TIPO_DOMOTICA = (
        ('SELFLOCKING', 'Auto-bloqueo'), ('ONOFF', 'Interruptor'), ('TERMOSTATO', 'Control de temperatura'),
        ('TH', 'Control de temperatura y humedad'))
    QOS = ((0, 'At most once'), (1, 'At least once'), (2, 'Exactly once'))
    APP = (('ESPURNA', 'Espurna'), ('IFTTT', 'IFTTT'))
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, blank=True, null=True)
    propietario = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    plataforma = models.CharField('Plataforma utilizada', default='ESPURNA', choices=APP, max_length=15)
    mqtt_broker = models.CharField('MQTT broker', default='localhost', max_length=100)
    mqtt_port = models.IntegerField('MQTT port', default=1883)
    mqtt_user = models.CharField('MQTT user', default='gaumentada', max_length=50)
    mqtt_pass = models.CharField('MQTT password', default='gaumentada', max_length=50)
    mqtt_id = models.CharField('MQTT client ID', default=mqtt_id_generator, max_length=50)
    mqtt_qos = models.IntegerField('MQTT QoS', default=2, choices=QOS)
    mqtt_keepalive = models.IntegerField('MQTT keep alive', default=600)
    mqtt_topic = models.CharField('MQTT root topic', default=mqtt_topic_generator, max_length=50)
    grupo = models.ForeignKey(Grupo, blank=True, null=True, on_delete=models.SET_NULL)
    etiqueta =models.ForeignKey(Etiqueta_domotica, blank=True, null=True, on_delete=models.SET_NULL)
    ifttt = models.CharField('IFTTT webhook al dispositivo', blank=True, null=True, max_length=250, default='')
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
def delete_gauserpermitidodispositivo(sender, instance, *args, **kwargs):
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
    creado = models.DateTimeField('Fecha de creación', auto_now_add=True)
    modificado = models.DateTimeField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['valido_desde']

    def __str__(self):
        return u'%s (%s - %s)' % (self.propietario, self.valido_desde, self.valido_hasta)


class UsuarioEnlaceDomotica(models.Model):
    enlace_domotica = models.ForeignKey(EnlaceDomotica, blank=True, null=True, on_delete=models.CASCADE)
    creador = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre del usuario", max_length=120, blank=True, null=True)
    secret = models.CharField("Código secreto del enlace", max_length=20, default=clave_secreta)
    # validez = JSONField(blank=True, null=True)
    creado = models.DateTimeField('Fecha de creación', auto_now_add=True)
    modificado = models.DateTimeField('Fecha de modificación', auto_now=True)

    @property
    def accesible(self):
        ahora = timezone.localtime()
        if ahora > self.enlace_domotica.valido_desde and ahora < self.enlace_domotica.valido_hasta:
            valor = False
            for v in self.validez['dias']:
                h_inicio = timezone.datetime.strptime(v['h_inicio'], '%H:%M').time()
                h_fin = timezone.datetime.strptime(v['h_fin'], '%H:%M').time()
                if int(v['dia']) == ahora.weekday() and ahora.time() > h_inicio and ahora.time() < h_fin:
                    valor = True
            return valor
        else:
            return False

    class Meta:
        ordering = ['modificado']

    def __str__(self):
        return u'%s (%s)' % (self.enlace_domotica, self.nombre)


validez = {'fh_inicio': '20190601 18:30', 'fh_fin': '20190701 18:30',
           'dias': [{'dia': '1', 'h_inicio': '18:30', 'h_fin': '20:30'},
                    {'dia': '1', 'h_inicio': '11:30', 'h_fin': '13:30'},
                    {'dia':'3', 'h_inicio':'18:30', 'h_fin':'20:30'}]}
