# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from datetime import date
from django.db import models
from entidades.models import Gauser_extra
from autenticar.models import Gauser
from django.utils.text import slugify

from horarios.models import Sesion

# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
import string
import random


# Generador de contraseñas
def pass_generator(size=6, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for x in range(size))



class Informe_seguimiento(models.Model):
    usuario = models.ForeignKey(Gauser_extra, related_name='usuario_informe', blank=True, null=True, on_delete=models.CASCADE)
    solicitante = models.ForeignKey(Gauser_extra, related_name='solicitante_informe', blank=True, null=True, on_delete=models.CASCADE)
    fecha = models.DateField("Fecha de solicitud del informe", blank=True, null=True)
    deadline = models.DateField("Fecha límite para rellenar el informe", blank=True, null=True)
    texto_solicitud = models.CharField("Texto solicitud", max_length=400, blank=True, null=True)
    finalizado = models.BooleanField("Informe finalizado", default=False)
    usuarios_destino = models.ManyToManyField(Gauser_extra, related_name="usuarios_destino", blank=True)
    educa_pk = models.IntegerField('id de gauss_educa', blank=True, null=True, default=1)

    class Meta:
        ordering = ['-deadline', ]

    @property
    def esta_cerrado(self):
        return date.today() > self.deadline

    @property
    def num_usuarios_respondido(self):
        preguntas = Pregunta.objects.filter(informe=self)
        return len(set(Respuesta.objects.filter(pregunta__in=preguntas).values_list('usuario__id', flat=True)))

    def __str__(self):
        return u'%s - %s (%s) %s' % (
            self.usuario.gauser.get_full_name(), self.usuario.gauser_extra_estudios.grupo, self.fecha, self.id)


class PreguntaPub(models.Model):
    TIPO_PREGUNTA = (
        ('PER', 'Esta pregunta sólo quiero utilizarla yo y no quiero que sea pública.'),
        ('PUB', 'Esta pregunta quiero que sea pública para que otros compañeros puedan usarla.'),
    )
    autor = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    pregunta = models.CharField("Escribe una pregunta para tu informe", max_length=400, blank=True, null=True)
    tipo_pregunta = models.CharField("Tipo de pregunta", max_length=40, choices=TIPO_PREGUNTA, default='PER')

    def __str__(self):
        return u'%s' % (self.pregunta)


class Pregunta(models.Model):
    informe = models.ForeignKey(Informe_seguimiento, blank=True, null=True, on_delete=models.CASCADE)
    pregunta = models.CharField("Escribe una pregunta para tu informe", max_length=400, blank=True, null=True)

    @property
    def respuestas(self):
        return Respuesta.objects.filter(pregunta=self)

    def __str__(self):
        return u'%s' % (self.pregunta)


class Respuesta(models.Model):
    informe = models.ForeignKey(Informe_seguimiento, related_name='informe', blank=True, null=True, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    pregunta = models.ForeignKey(Pregunta, related_name='respuesta_informe', null=True, blank=True, on_delete=models.CASCADE)
    respuesta = models.TextField("Respuesta a pregunta", null=True, blank=True)

    class Meta:
        ordering = ['id', ]

    def __str__(self):
        return u'Inf: %s, Pre: %s... - Res: %s... (%s)' % (
            self.informe.id, self.pregunta.pregunta[:20], self.respuesta[:20], self.usuario.gauser.get_full_name())

def update_fichero_seguimiento(instance, filename):
    split_filename = filename.partition('.')
    f0 = slugify("-".join(instance.respuesta.usuario.gauser.get_full_name()))
    nombre = '{0:03d}_{1}.{2}'.format(instance.respuesta.informe.id, f0, split_filename[2])
    instance.fich_name = nombre
    entidad = instance.respuesta.informe.solicitante.ronda.entidad
    return '/'.join(['ficheros_seguimiento', str(entidad.code), slugify(entidad.ronda.nombre), nombre])

class Fichero_seguimiento(models.Model):
    respuesta = models.OneToOneField(Respuesta, blank=True, null=True, on_delete=models.CASCADE)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero_seguimiento, blank=True)
    content_type = models.CharField("Content Type", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def nombre_fichero(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def __str__(self):
        return u'%s (%s)' % (self.fichero, self.respuesta.usuario.gauser.get_full_name())





def update_fichero_tareas(instance, filename):
    split_filename = filename.partition('.')
    f0 = slugify("-".join(instance.tarea.materias_usuario) + '_' + split_filename[0])
    nombre = '{0:03d}_{1}.{2}'.format(instance.tarea.informe.id, f0, split_filename[2])
    instance.fich_name = nombre
    entidad = instance.tarea.informe.solicitante.ronda.entidad
    return '/'.join(['ficheros_tareas', str(entidad.code), slugify(entidad.ronda.nombre), nombre])


class Informe_tareas(models.Model):
    solicitante = models.ForeignKey(Gauser_extra, related_name='solicitante', blank=True, null=True, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Gauser_extra, related_name='usuario_tarea', blank=True, null=True, on_delete=models.CASCADE)
    texto_solicitud = models.TextField("Observaciones del informe con tareas")
    fecha = models.DateField("Fecha de solicitud del tarea")
    deadline = models.DateField("Fecha límite para la propuesta del tarea")
    usuarios_destino = models.ManyToManyField(Gauser_extra, related_name="destinatarios", blank=True)

    @property
    def esta_cerrado(self):
        return date.today() > self.deadline

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return u'%s - %s (%s) %s' % (
            self.usuario.gauser.get_full_name(), self.usuario.gauser_extra_estudios.grupo, self.deadline, self.id)


class Tarea_propuesta(models.Model):
    informe = models.ForeignKey(Informe_tareas, blank=True, null=True, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    fecha = models.DateField("Fecha en la que el usuario propone la tarea", blank=True, null=True)
    texto_tarea = models.TextField("Texto de tarea")

    @property
    def materias_usuario(self):
        grupo = self.informe.usuario.gauser_extra_estudios.grupo
        return set(Sesion.objects.filter(grupo=grupo, horario__predeterminado=True, g_e=self.usuario, materia__isnull=False).values_list(
            'materia__nombre', flat=True))

    def __str__(self):
        return u'%s (%s) %s' % (
            self.usuario.gauser.get_full_name(), self.fecha, self.id)


class Fichero_tarea(models.Model):
    tarea = models.ForeignKey(Tarea_propuesta, blank=True, null=True, on_delete=models.CASCADE)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero_tareas, blank=True)
    content_type = models.CharField("Content Type", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def nombre_fichero(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def __str__(self):
        return u'%s (%s)' % (self.fichero, self.tarea.usuario.gauser.get_full_name())

# DEPARTAMENTOS = (
#     ("3", "Actividades Complementarias y Extraescolares"), ("6", "Artes Plásticas"), ("9", "Cultura Clásica"),
#     ("12", "Ciencias Naturales"), ("15", "Economía"), ("18", "Educación Física"), ("21", "Filosofía"),
#     ("24", "Física y Química"), ("27", "Formación y Orientación Laboral"), ("30", "Francés"),
#     ("33", "Geografía e Historia"), ("36", "Griego"), ("39", "Inglés"), ("42", "Latín"),
#     ("45", "Lengua Castellana y Literatura"), ("48", "Matemáticas"), ("51", "Música"), ("54", "Orientación"),
#     ("57", "Tecnología"), ("60", "Administración y gestión"), ("63", "Electricidad y electrónica"),
#     ("66", "Cualquier departamento"), ("69", "Alemán"))
#
# CURSOS = (("250010", "1º E.S.O."), ("250020", "1º E.S.O. (REFUERZO EDUCATIVO)"), ("250030", "2º E.S.O."),
#           ("250035", "2º E.S.O. (REFUERZO EDUCATIVO)"), ("250025", "2º E.S.O. (REFUERZO EDUCATIVO)"),
#           ("250040", "2º E.S.O. (ADAPTACIÓN CURRICULAR EN GRUPO)"), ("250050", "3º E.S.O."),
#           ("250060", "3º de E.S.O. (DIVERSIFICACIÓN)"), ("250070", "4º E.S.O."),
#           ("250080", "4º de E.S.O. (DIVERSIFICACIÓN)"))
#
#
# class AspectoEducativo(models.Model):
#     centro = models.ForeignKey(Entidad, blank=True, null=True, related_name="aspecto_centro", on_delete=models.CASCADE)
#     # Si el estudio está vacío o es "Ningún curso en particular" (id=10), el objetivo será considerado válido para
#     # cualquier etapa:
#     estudio = models.ForeignKey(Estudio, blank=True, null=True, related_name="aspecto_estudio", on_delete=models.CASCADE)
#     materia = models.ForeignKey(Materia, null=True, blank=True, related_name="aspecto_materia", on_delete=models.CASCADE)
#     aspecto = models.TextField("Aspecto educativo a mejorar")
#
#     class Meta:
#         ordering = ['materia']
#
#     def __str__(self):
#         d = self.materia.nombre if self.materia else 'Para cualquier materia'
#         c = self.estudio.curso if self.estudio.id != 10 else 'Para cualquier curso'
#         return u'%s - %s (%s) %s' % (self.centro.name, self.aspecto, d, c)
#
# class ValoraAspecto(models.Model):
#     profesor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name="valora_aspecto_profesor", on_delete=models.CASCADE)
#     usuario = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name="valora_aspecto_usuario", on_delete=models.CASCADE)
#     aspecto = models.ForeignKey(AspectoEducativo, blank=True, null=True, related_name="valora_aspecto_objetivo", on_delete=models.CASCADE)
#     necesita_mejorar = models.BooleanField("Necesita mejorar?", default=False)
#     def __str__(self):
#         nc = ['No necesita mejorar', 'Necesita mejorar']
#         return u'%s - %s (%s)' % (self.usuario.gauser.get_full_name(), self.aspecto.aspecto, nc[self.necesita_mejorar])
#
#
# class Objetivos(models.Model):
#     TIPOS_VALORABLES = (('0', 'Nada/Poco/Bastante/Mucho'), ('1', 'Nunca/A veces/Habitualmente/Siempre'),
#                         ('2', 'No conseguido/Parcialmente conseguido/Casi conseguido/Completamente conseguido'))
#     centro = models.ForeignKey(Entidad, blank=True, null=True, related_name="centro", on_delete=models.CASCADE)
#     # Si el estudio está vacío o es "Ningún curso en particular" (id=10), el objetivo será considerado válido para
#     # cualquier etapa:
#     estudio = models.ForeignKey(Estudio, blank=True, null=True, related_name="objetivos_estudio", on_delete=models.CASCADE)
#     materia = models.ForeignKey(Materia, null=True, blank=True, related_name="objetivos_materia", on_delete=models.CASCADE)
#     objetivo = models.TextField("Objetivo educativo")
#     valorable = models.CharField('Objetivo valorable según: ', max_length=20, choices=TIPOS_VALORABLES)
#
#     class Meta:
#         ordering = ['materia']
#
#     def __str__(self):
#         d = self.materia.nombre if self.materia else 'Para cualquier materia'
#         c = self.estudio.curso if self.estudio.id != 10 else 'Para cualquier curso'
#         return u'%s - %s (%s) %s' % (self.centro.name, self.objetivo, d, c)
#
#
# class ValoraObjetivo(models.Model):
#     VALORES = (('00', 'Nada'), ('01', 'Poco'), ('02', 'Bastante'), ('03', 'Mucho'),
#                ('10', 'Nunca'), ('11', 'A veces'), ('12', 'Habitualmente'), ('13', 'Siempre'),
#                ('20', 'No conseguido'), ('21', 'Parcialmente conseguido'), ('22', 'Casi conseguido'),
#                ('23', 'Completamente conseguido'))
#     profesor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name="valora_objetivo_profesor", on_delete=models.CASCADE)
#     usuario = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name="valora_objetivo_usuario", on_delete=models.CASCADE)
#     objetivo = models.ForeignKey(Objetivos, blank=True, null=True, related_name="valora_objetivo_objetivo", on_delete=models.CASCADE)
#     valoracion = models.CharField("Valoración del objetivo", max_length=10, choices=VALORES, blank=True, null=True)
#     def __str__(self):
#         return u'%s - %s (%s)' % (self.usuario.gauser.get_full_name(), self.objetivo.objetivo, self.valoracion)
#
#
# class ObservacionesTrabajos(models.Model):
#     profesor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name="observaciones_trabajos_profesor", on_delete=models.CASCADE)
#     usuario = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name="observaciones_trabajos_usuario", on_delete=models.CASCADE)
#     observaciones = models.TextField("Observaciones para el usuario", null=True, blank=True)
#     trabajos = models.ManyToManyField(Tarea_propuesta, blank=True)
#
#
# class InformeFinal(models.Model):
#     ADAPTACIONES = (('SIN', 'No ha tenido adaptación curricular'),
#                     ('NOSIG', 'Ha tenido adaptación curricular no significativa'),
#                     ('SIG', 'Ha tenido adaptación curricular significativa'), )
#     PROGRAMAS = (('NP', 'No está matriculado/a en un programa especial'),
#                  ('PRC1', 'Matriculado en el Programa de Refuerzo Curricular de primer curso'),
#                  ('PRC2', 'Matriculado en el Programa de Refuerzo Curricular de segundo curso'),
#                  ('PMAR1', 'Matriculado en el Programa de Mejora del Aprendizaje y del Rendimiento de primer curso'),
#                  ('PMAR2', 'Matriculado en el Programa de Mejora del Aprendizaje y del Rendimiento de segundo curso'),
#                  ('PDIV1', 'Matriculado en el Programa de Diversificación Curricular primer curso (3º ESO)'),
#                  ('PDIV2', 'Matriculado en el Programa de Diversificación Curricular segundo curso (4º ESO)'),
#                  ('PACG', 'Matriculado en el Programa de Adaptación Curricular en Grupo'),
#                  ('COMP', 'Matriculado en el programa de Compensatoria'),)
#     profesor = models.ForeignKey(Gauser_extra, related_name='informe_final_profesor', on_delete=models.CASCADE)
#     usuario = models.ForeignKey(Gauser_extra, related_name='informe_final_usuario', on_delete=models.CASCADE)
#     materia = models.ForeignKey(Materia, related_name='informe_final_materia', on_delete=models.CASCADE)
#     nota = models.CharField("Calificación obtenida en la materia", max_length=4, blank=True, null=True)
#     adaptacion = models.CharField('Adaptación curricular', max_length=10, choices=ADAPTACIONES, default=ADAPTACIONES[0][0])
#     programa = models.CharField('Programa en el que está matriculado', max_length=10, choices=PROGRAMAS)
#     pt = models.BooleanField('¿Ha tenido refuerzo con profesor de pedagogía terapéutica?', default=False)
#     extraordinaria = models.BooleanField('¿El usuario va a convocatoria extraordinaria?', default=True)
#     observaciones = models.TextField("Observaciones para el usuario", blank=True, null=True)
#     creado = models.DateTimeField('Fecha y hora de creación', auto_now_add=True, null=True)
#     modificado = models.DateTimeField('Fecha y hora de modificación', auto_now=True, null=True)
#
#     def __str__(self):
#         return u'%s - %s' % (self.usuario.gauser.get_full_name(), self.usuario.grupo)
#
