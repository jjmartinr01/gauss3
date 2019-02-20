# -*- coding: utf-8 -*-
from PIL import Image
from entidades.models import Entidad, Gauser_extra, Subentidad
from django.db import models

from gauss.funciones import usuarios_de_gauss
from horarios.models import Tramo_horario
from estudios.models import Grupo
from datetime import datetime
import os
from django.db.models.signals import post_save


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_fichero2(instance, filename):
    ahora = datetime.now()
    fichero = 'actividades' + '_' + str(instance.entidad.code) + '_' + str(ahora.year) + '-' + str(
        ahora.month) + '-' + str(ahora.day) + '_' + str(ahora.hour) + ':' + str(ahora.minute) + ':' + str(
        ahora.second) + '.' + filename.partition('.')[2]
    return os.path.join("files/", fichero)


class Actividad(models.Model):
    organizador = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)  # organizador
    actividad_title = models.CharField('Nombre de la actividad', max_length=200)
    description = models.TextField("Descripción de la actividad", blank=True, null=True)
    fecha_inicio = models.DateField("Fecha de inicio de la actividad", blank=True, null=True)
    fecha_fin = models.DateField("Fecha de finalización de la actividad", blank=True, null=True)
    fecha_hora_inicio = models.DateTimeField("Fecha y hora de inicio de la actividad", blank=True, null=True)
    fecha_hora_fin = models.DateTimeField("Fecha y hora de finalización de la actividad", blank=True, null=True)
    tramos_horarios = models.ManyToManyField(Tramo_horario, blank=True)
    colaboradores = models.ManyToManyField(Gauser_extra, related_name="colaboradores", blank=True)
    alumnos_incluidos = models.ManyToManyField(Gauser_extra, related_name="alumnos_incluidos", blank=True)
    fichero_description = models.CharField('Explicación del contenido del fichero', max_length=200, blank=True,
                                           null=True)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero2, blank=True)
    aprobada = models.BooleanField("Aprobada por el Consejo Escolar", default=False)
    fecha_aprobacion = models.DateField("Fecha de aprobación por el Consejo Escolar", null=True, blank=True)
    slideable = models.BooleanField("Se proyecta en actividades2slides", default=True)

    def alumnos(self, grupo):  # Devuelve el nombre de los alumnos de un determinado grupo
        return self.alumnos_incluidos.filter(grupo=grupo)

    @property
    def grupos_incluidos(self):
        grupos = []
        for a in self.alumnos_incluidos.all():
            g = a.gauser_extra_estudios.grupo
            if g and g not in grupos:
                grupos.append(g)
        return grupos

    @property
    def nombre_grupos_incluidos(self):
        # grs = Grupo.objects.filter(id__in=self.alumnos_incluidos.all().values_list('grupo__id', flat=True)).distinct()
        # return list(set(grs.values_list('nombre', flat=True)))
        return [g.nombre for g in self.grupos_incluidos]

    @property
    def grupos_actividad(self):
        sub_alumnos = Subentidad.objects.get(entidad=self.organizador.entidad, clave_ex='alumnos')
        alumnos_entidad = usuarios_de_gauss(self.organizador.entidad, subentidades=[sub_alumnos])
        grupos_entidad = alumnos_entidad.order_by('grupo__nombre').values_list('grupo__nombre', flat=True).distinct()
        grupos_incluidos = self.nombre_grupos_incluidos
        grupos_alumnos = []
        for g in grupos_incluidos:
            alumnos = alumnos_entidad.filter(grupo__nombre__icontains=g)
            grupos_alumnos.append({'grupo': g, 'alumnos': alumnos})
        return {'grupos_entidad': grupos_entidad, 'grupos_incluidos': grupos_incluidos,
                'grupos_alumnos': grupos_alumnos}

    class Meta:
        ordering = ['fecha_hora_inicio', 'fecha_hora_fin']

    def __unicode__(self):
        return u'Actividad del %s (%s) -- %s' % (self.organizador.entidad.name, self.fecha_inicio, self.actividad_title)


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_fichero(instance, filename):
    nombre = filename.rpartition('.')
    instance.fich_name = filename.rpartition('/')[2]
    fichero = instance.code + '.' + nombre[2]
    return '/'.join(['actividades', str(instance.actividad.organizador.entidad.code), fichero])


class File_actividad(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE)
    code = models.CharField("Código del archivo que coincide con el nombre", max_length=50, blank=True, null=True)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero, blank=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """
            REQUIRES:
                1.	'from PIL import Image'

            DOES:
                1.	check to see if the image needs to be resized
                2.	check how to resize the image based on its aspect ratio
                3.	resize the image accordingly

            ABOUT:
                based loosely on djangosnippet #688
                http://www.djangosnippets.org/snippets/688/

            VERSIONS I'M WORKING WITH:
                Django 1.0
                Python 2.5.1

            BY:
                Tanner Netterville
                tanner@cabedge.com
        """

        super(File_actividad, self).save()

        filename = str(self.fichero.path)
        try:
            nw = 850
            nh = 567
            image = Image.open(filename)
            pw, ph = image.size
            pr = float(pw) / float(ph)
            nr = float(nw) / float(nh)

            if pr > nr:
                # photo aspect is wider than destination ratio
                tw = int(round(nh * pr))
                image = image.resize((tw, nh), Image.ANTIALIAS)
                l = int(round((tw - nw) / 2.0))
                image = image.crop((l, 0, l + nw, nh))
            elif pr < nr:
                # photo aspect is taller than destination ratio
                th = int(round(nw / pr))
                image = image.resize((nw, th), Image.ANTIALIAS)
                t = int(round((th - nh) / 2.0))
                print((0, t, nw, t + nh))
                image = image.crop((0, t, nw, t + nh))
            else:
                # photo aspect matches the destination ratio
                image = image.resize((nw, nh), Image.ANTIALIAS)

            image.save(filename)
        except:
            pass

    def __unicode__(self):
        return u'%s (%s - %s)' % (self.fichero, self.fich_name, self.actividad.actividad_title)


def si_fecha_aprobacion(sender, instance, **kwargs):
    if instance.fecha_aprobacion and instance.aprobada == False:
        instance.aprobada = True
        instance.save()


# Este es el manejador de señales que creará un UserProfile cuando se detecte la señal de crear un usuario:
post_save.connect(si_fecha_aprobacion, sender=Actividad)
