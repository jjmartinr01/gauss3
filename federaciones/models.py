from django.db import models
from django.utils.text import slugify
import os
import random
# from gauss.funciones import pass_generator
from autenticar.models import Gauser
from entidades.models import Entidad


# Generador de contraseñas
def pass_generator(size=15, chars='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz123456789'):
    return ''.join(random.choice(chars) for x in range(size))


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_con(instance, filename):
    ext = filename.rpartition('.')[2]
    file_nombre = pass_generator(10)
    try:
        federacion = instance.federacion.entidad.code
    except:
        federacion = instance.entidad.code
    return 'federaciones/%s/%s.%s' % (federacion, file_nombre, ext)


class Federacion(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='federaciones')
    nombre = models.CharField('Nombre adicional', max_length=300, blank=True, null=True, default='')
    condiciones_fedaracion = models.TextField('Condiciones marcadas por la Federación', blank=True, default='')
    condiciones_fedaracion_file = models.FileField('Archivo federación', blank=True, null=True, upload_to=update_con)
    code_inscribir = models.CharField('Código de inscripción', default=pass_generator, max_length=15)

    class Meta:
        verbose_name_plural = "Federaciones"
        ordering = ['entidad']

    def __str__(self):
        return u'%s -- %s' % (self.entidad.name, self.nombre)


class Federado(models.Model):
    # Cuando una entidad se federa, es decir pertenece a una entidad superior, se crea automáticamente una
    # Subentidad llamada con el nombre de la entidad "federacion". En esta subentidad se podrán introducir
    # aquellos usuarios que se deseen y serán vistos por la Federación asociada a "federacion"
    federacion = models.ForeignKey(Federacion, on_delete=models.CASCADE, related_name='entidades_federadas')
    acepta_federacion = models.BooleanField('Relación con la entidad aceptada por la federación', default=False)
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE, related_name='entidades_federadas')
    condiciones_entidad = models.TextField('Condiciones marcadas por la Entidad federada', blank=True, default='')
    condiciones_entidad_file = models.FileField('Archivo entidad', blank=True, null=True, upload_to=update_con)
    acepta_entidad = models.BooleanField('Relación con la federación aceptada por la entidad', default=False)
    pnum = models.BooleanField('Federación puede ver el número de usuarios de entidad', default=False)
    piban = models.BooleanField('Federación puede ver el IBAN de la entidad', default=False)
    pfed = models.BooleanField('Federación puede ver a los federados en entidad', default=False)
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    # "modificado" se utiliza para comprobar cuando fue la última vez que se guardo un objeto "Federado", si ese
    # momento fuera superior a 7 días y, tanto "acepta_federacion", como "acepta_entidad" no fueran True se borrará
    # el susodicho objeto "Federado". Por tanto, el objeto "Federado" solo puede existir por un tiempo prolongado si
    # es aceptado por las dos partes.

    class Meta:
        verbose_name_plural = "Entidades federadas"
        ordering = ['federacion']

    def __str__(self):
        return u'%s -- %s' % (self.federacion, self.entidad.name)


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_fichero(instance, filename):
    ext = filename.rpartition('.')[2]
    file_nombre = pass_generator(10)
    try:
        federacion = instance.federacion.entidad.code
    except:
        federacion = instance.entidad.code
    return 'federaciones/%s/%s.%s' % (federacion, file_nombre, ext)

class Fichero(models.Model):
    federacion = models.ForeignKey(Federacion, on_delete=models.CASCADE)
    is_carpeta = models.BooleanField('Es una carpeta/directorio', default=False)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='parents', on_delete=models.CASCADE)
    fichero = models.FileField('Fichero federación', blank=True, null=True, upload_to=update_fichero)
    content_type = models.CharField('Content Type del fichero', max_length=50, blank=True, null=True)
    observaciones = models.TextField('Observaciones', default='', blank=True, null=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)
    creado = models.DateField('Fecha de creación', auto_now_add=True)

    class Meta:
        verbose_name_plural = "Ficheros de la federación"
        ordering = ['federacion', 'is_carpeta']

    def __str__(self):
        return u'%s -- %s' % (self.federacion, self.content_type)

class GauserFichero(models.Model):
    PER=(('r', 'Lectura'), ('w', 'Lectura y escritura') )
    fichero = models.ForeignKey(Fichero, on_delete=models.CASCADE)
    gauser = models.ForeignKey(Gauser, related_name='usuarios', on_delete=models.CASCADE)
    pread = models.BooleanField('Permiso para leer el fichero', default=True)
    pwrite = models.BooleanField('Permiso para editar/borrar el fichero', default=False)
    pshare = models.BooleanField('Permiso para compartir el fichero', default=False)

    class Meta:
        verbose_name_plural = "Usuarios con permisos"
        ordering = ['fichero__federacion']

    def __str__(self):
        return u'r:%s, w:%s, s:%s, %s -- %s' % (self.pread, self.pwrite, self.pshare, self.gauser, self.fichero)