# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from entidades.models import Entidad, Ronda, Subentidad, Gauser_extra, Dependencia

# Create your models here.
class EtapaEscolar(models.Model):
    nombre = models.CharField('Nombre de la etapa escolar', max_length=250)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    class Meta:
        ordering = ['clave_ex', 'nombre']

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.clave_ex)


# ETAPAS = (('ba', 'Infantil'), ('ca', 'Primaria'), ('da', 'Secundaria'), ('ea', 'FP Básica'), ('fa', 'Bachillerato'),
#           ('ga', 'FP Grado Medio'), ('ha', 'FP Grado Superior'))
ETAPAS = (('ba', 'Infantil'), ('ca', 'Primaria'), ('da', 'Secundaria'), ('ea', 'FP Básica'), ('fa', 'Bachillerato'),
              ('ga', 'FP Grado Medio'), ('ha', 'FP Grado Superior'), ('ia', 'Enseñanzas Iniciales de Personas Adultas'),
              ('ja', 'Educación Secundaria de Personas Adultas'),
              ('ka', 'Educación Secundaria de Personas Adultas a Distancia Semipresencial'),
              ('la', 'Educación Secundaria de Personas Adultas a Distancia'), ('ma', 'Educación para Personas Adultas'),
              ('na', 'Preparación Pruebas de Acceso a CCFF'), ('za', 'Etapa no identificada'))

class Curso(models.Model):
    # entidad = models.ForeignKey(Entidad, blank=True, null=True, related_name='estudios', on_delete=models.CASCADE)
    ronda = models.ForeignKey(Ronda, blank=True, null=True, related_name='estudios', on_delete=models.CASCADE)
    nombre = models.CharField("Curso", max_length=150)
    etapa = models.CharField("Nombre de la etapa", max_length=75, null=True, blank=True, choices=ETAPAS)
    etapa_escolar = models.ForeignKey(EtapaEscolar, blank=True, null=True, on_delete=models.CASCADE)
    tipo = models.CharField("Tipo de estudio", max_length=75, null=True, blank=True)
    nombre_especifico = models.CharField("Nombre específico", max_length=150, null=True, blank=True)
    familia = models.CharField("Departamento", max_length=150, null=True, blank=True)
    observaciones = models.TextField("Observaciones", null=True, blank=True)
    # grupos = models.ManyToManyField(Subentidad, blank=True, related_name='estudios')
    edad = models.IntegerField("Edad con la que puede iniciarse este curso", blank=True, null=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    class Meta:
        ordering = ['etapa', 'tipo', 'nombre']

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.ronda.entidad.name)


# Ligar un Grupo a un curso es problemático porque alumnos de un grupo pueden pertenecer a varios cursos. Por ejemplo
# los alumnos del grupo 1Bach A pueden pertenecer a los cursos de Ciencias y de Artes
class Grupo(models.Model):
    ronda = models.ForeignKey(Ronda, blank=True, null=True, related_name='estudios_grupo', on_delete=models.CASCADE)
    cursos = models.ManyToManyField(Curso, blank=True)
    aula = models.ForeignKey(Dependencia, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre", max_length=100)
    observaciones = models.TextField("Observaciones", null=True, blank=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    @property
    def entidad(self):
        return self.ronda.entidad

    @property
    def tutores(self):
        tutores_id = Gauser_extra_estudios.objects.filter(grupo__id=self.id).values_list('tutor__id')
        return Gauser_extra.objects.filter(id__in=tutores_id).distinct()

    @property
    def cotutores(self):
        cotutores_id = Gauser_extra_estudios.objects.filter(grupo__id=self.id).values_list('cotutor__id')
        return Gauser_extra.objects.filter(id__in=cotutores_id).distinct()

    @property
    def gausers_extra_horarios(self):
        return Gauser_extra_estudios.objects.filter(grupo__id=self.id)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        cursos = self.cursos.all().values_list('nombre', flat=True)
        return '%s - %s - %s' % (self.nombre, ', '.join(cursos), self.ronda)


class Materia(models.Model):
    curso = models.ForeignKey(Curso, null=True, blank=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la materia", max_length=120, null=True, blank=True)
    abreviatura = models.CharField("Abreviatura de la materia", max_length=20, null=True, blank=True)
    horas = models.IntegerField("Número de horas a impartir por semana", null=True, blank=True)
    # horasf = models.FloatField("Número de horas lectivas por semana", null=True, blank=True)
    duracion = models.IntegerField('Horas totales previstas para impartir toda la materia', blank=True, null=True)
    observaciones = models.TextField("Observaciones", null=True, blank=True)
    grupo_materias = models.CharField('Tipo de materia', max_length=50, blank=True, null=True)
    horas_semana_min = models.CharField('Horas mínimas de la materia por semana', max_length=10, blank=True, null=True)
    horas_semana_max = models.CharField('Horas máximas de la materia por semana', max_length=10, blank=True, null=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    @property
    def entidad(self):
        return self.curso.ronda.entidad

    class Meta:
        ordering = ['curso', 'nombre']

    def __str__(self):
        curso_nombre = self.curso.nombre if self.curso else 'No asignada a un curso'
        return '%s - %s (%s horas)' % (self.nombre, curso_nombre, self.horas)


class Gauser_extra_estudios(models.Model):
    ge = models.OneToOneField(Gauser_extra, on_delete=models.CASCADE) # Alumno
    grupo = models.ForeignKey(Grupo, blank=True, null=True, on_delete=models.CASCADE) # Grupo del alumno
    tutor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='estudios_tutor', on_delete=models.CASCADE)
    cotutor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='estudios_cotutor', on_delete=models.CASCADE)

    @property
    def materias(self):
        return Matricula.objects.filter(ge=self.ge).values_list('materia__clave_ex', 'materia__nombre', 'estado')

    def __str__(self):
        return '%s - %s' % (self.ge, self.grupo)


class Matricula(models.Model):
    ESTADOS = (('AP', 'Aprobada años anteriores'), ('CV', 'Convalidada'), ('MA', 'Matriculada'), ('PE', 'Pendiente'))
    ge = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, related_name='alumno')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    estado = models.CharField("Estado de la materia", max_length=75, null=True, blank=True, choices=ESTADOS)
    evaluador = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, related_name='profe', blank=True, null=True)
    nota1 = models.IntegerField("Calificación 1", blank=True, null=True, default=1)
    nota2 = models.IntegerField("Calificación 2", blank=True, null=True, default=1)
    nota3 = models.IntegerField("Calificación 3", blank=True, null=True, default=1)

    class Meta:
        ordering = ['ge__gauser_extra_estudios__grupo', 'ge__gauser__last_name']

    def __str__(self):
        return '%s - %s (%s)' % (self.ge, self.materia, self.estado)
