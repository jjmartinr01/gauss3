# -*- coding: utf-8 -*-
from django.db import models

# from autenticar.models import Gauser_extra
from entidades.models import Cargo, Subentidad
# from entidades.models import Cargo, Subentidad, Gauser_extra
from entidades.models import Gauser_extra as GE
from gauss.funciones import pass_generator

class Gform(models.Model):
    propietario = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
    cargos_destino = models.ManyToManyField(Cargo, blank=True)
    subentidades_destino = models.ManyToManyField(Subentidad, blank=True)
    nombre = models.CharField('Nombre del formulario', max_length=150)
    activo = models.BooleanField('El formulario esta activo', default=False)
    anonimo = models.BooleanField('Las respuestas son anónimas?', default=False)
    fecha_max_rellenado = models.DateTimeField('Fecha máxima para el rellenado', max_length=50, blank=True, null=True)
    creado = models.DateTimeField('Fecha de creación', auto_now_add=True)

    @property
    def contestados2(self):
        num_preguntas = self.ginput_set.filter(ginput__isnull=True).count()
        #Resto 1 para no contar el "original" :
        return 0 if num_preguntas == 0 else self.ginput_set.all().count()/num_preguntas - 1

    @property
    def contestados(self):
        return self.ginput_set.filter(ginput__isnull=False).values_list('rellenador__id', flat=True).distinct().count()

    @property
    def num_preguntas(self):
        return self.ginput_set.filter(ginput__isnull=True).count()

    def __unicode__(self):
        n = self.ginput_set.all().count()
        activo = 'Formulario activo' if self.activo else 'Formulario desactivado'
        return u'%s - %s (%s con %s campos).' % (self.propietario.entidad.name, self.nombre, activo, n)



def guarda_archivo(instance, filename):
    nombre = filename.rpartition('.')
    instance.fich_name = filename.rpartition('/')[2]
    fichero = pass_generator(size=20) + '.' + nombre[2]
    return '/'.join(['formularios', str(instance.gform.propietario.entidad.code), fichero])

TIPOS = (('gchar', 'Texto con un máximo de 150 caracteres'), ('gselect', 'Seleccionar uno o varios valores'),
         ('gint', 'Número entero (sin decimales)'), ('gfloat', 'Número con decimales'), ('gbool', 'Respuesta Sí/No'),
         ('gdatetime', 'Fecha y hora (dd/mm/yyyy HH:mm)'), ('gdate', 'Fecha (dd/mm/yyyy)'),
         ('gtext', 'Texto de longitud ilimitada'), ('gfile', 'Archivo'))
class Ginput(models.Model):
    gform = models.ForeignKey(Gform, blank=True, null=True, on_delete=models.CASCADE)
    cargos_permitidos = models.ManyToManyField(Cargo, blank=True) #Cargos que tienen acceso a esta Ginput
    row = models.IntegerField("Número de fila", blank=True, null=True)
    col = models.IntegerField("Número de columna", blank=True, null=True)
    ancho = models.IntegerField("Número de columnas (anchura)", blank=True, null=True)
    rellenador = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
    tipo = models.CharField('Tipo de entrada', max_length=30, choices=TIPOS)
    label = models.CharField('Label', max_length=150)
    select = models.BooleanField('Es un select múltiple?', default=False)
    gchar = models.CharField('Texto con un máximo de 150 caracteres', max_length=150, blank=True, null=True)
    gint = models.IntegerField('Número entero (sin decimales)', blank=True, null=True)
    gfloat = models.FloatField('Número con decimales', max_length=50, blank=True, null=True)
    gdate = models.DateField('Fecha (dd/mm/yyyy)', max_length=50, blank=True, null=True)
    gdatetime = models.DateTimeField('Fecha y hora (dd/mm/yyyy HH:mm)', max_length=50, blank=True, null=True)
    gtext = models.TextField('Texto de longitud ilimitada', blank=True, null=True)
    gbool = models.BooleanField('Respuesta Sí/No', default=False)
    archivo = models.FileField('Archivo', blank=True, null=True, upload_to=guarda_archivo)
    content_type_archivo = models.CharField('Tipo de archivo', max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)
    ginput = models.ForeignKey('self', related_name='copia', blank=True, null=True, on_delete=models.CASCADE)
    def __unicode__(self):
        comentario = 'Original' if not self.ginput else self.rellenador.gauser.get_full_name()
        return u'%s, %s (Tipo: %s) - %s' % (self.gform.nombre, self.label, self.tipo, comentario)

class Goption(models.Model):
    ginput = models.ForeignKey(Ginput, blank=True, null=True, on_delete=models.CASCADE)
    text = models.CharField('Text', max_length=150)
    value = models.CharField('Value', max_length=50)
    selected = models.BooleanField('Selected', default=False)
    def __unicode__(self):
        return u'%s (%s) - Seleccionada: %s' % (self.text, self.value, self.selected)
