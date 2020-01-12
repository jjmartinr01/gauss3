# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from entidades.models import Entidad, Ronda, Subentidad, Gauser_extra, Dependencia

# Create your models here.

ETAPAS = (('ba', 'Infantil'), ('ca', 'Primaria'), ('da', 'Secundaria'), ('ea', 'FP Básica'), ('fa', 'Bachillerato'),
          ('ga', 'FP Grado Medio'), ('ha', 'FP Grado Superior'))

class Curso(models.Model):
    # entidad = models.ForeignKey(Entidad, blank=True, null=True, related_name='estudios', on_delete=models.CASCADE)
    ronda = models.ForeignKey(Ronda, blank=True, null=True, related_name='estudios', on_delete=models.CASCADE)
    nombre = models.CharField("Curso", max_length=150)
    etapa = models.CharField("Nombre de la etapa", max_length=75, null=True, blank=True, choices=ETAPAS)
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
        try:
            return u'%s (%s)' % (self.nombre, self.ronda.entidad.name)
        except:
            return u'%s (%s)' % (self.nombre, self.entidad.name)


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
        return u'%s - %s - %s' % (self.nombre, ', '.join(cursos), self.ronda)


class Materia(models.Model):
    curso = models.ForeignKey(Curso, null=True, blank=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la materia", max_length=100, null=True, blank=True)
    abreviatura = models.CharField("Abreviatura de la materia", max_length=20, null=True, blank=True)
    horas = models.IntegerField("Número de horas a impartir por semana", null=True, blank=True)
    duracion = models.IntegerField('Horas totales previstas para impartir toda la materia', blank=True, null=True)
    observaciones = models.TextField("Observaciones", null=True, blank=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    @property
    def entidad(self):
        return self.curso.ronda.entidad

    class Meta:
        ordering = ['curso', 'nombre']

    def __str__(self):
        curso_nombre = self.curso.nombre if self.curso else 'No asignada a un curso'
        return u'%s - %s (%s horas)' % (self.nombre, curso_nombre, self.horas)


class Gauser_extra_estudios(models.Model):
    ge = models.OneToOneField(Gauser_extra, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, blank=True, null=True, on_delete=models.CASCADE)
    tutor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='estudios_tutor', on_delete=models.CASCADE)
    cotutor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='estudios_cotutor', on_delete=models.CASCADE)

    @property
    def materias(self):
        return Matricula.objects.filter(ge=self.ge).values_list('materia__clave_ex', 'materia__nombre', 'estado')

    def __str__(self):
        return u'%s - %s' % (self.ge, self.grupo)


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
        return u'%s - %s (%s)' % (self.ge, self.materia, self.estado)



def cursos2cursos():
    from horarios.models import Curso as HCurso
    from estudios.models import Curso as ECurso
    hcursos = HCurso.objects.all()
    for hc in hcursos:
        ECurso.objects.create(entidad=hc.entidad, ronda=hc.ronda, nombre=hc.nombre, etapa=hc.etapa, tipo=hc.tipo, nombre_especifico=hc.nombre_especifico,familia=hc.familia, observaciones=hc.observaciones, edad=hc.edad, clave_ex=hc.clave_ex)

def grupos2grupos():
    from horarios.models import Grupo as HGrupo
    from estudios.models import Grupo as EGrupo
    from estudios.models import Curso
    hgrupos = HGrupo.objects.all()
    for hg in hgrupos:
        eg = EGrupo.objects.create(ronda=hg.ronda, nombre=hg.nombre, observaciones=hg.observaciones,
                                   clave_ex=hg.clave_ex)
        hcursos = hg.cursos.all().values_list('clave_ex', flat=True)
        ecursos = Curso.objects.filter(clave_ex__in=hcursos, entidad=hg.entidad, ronda=hg.ronda)
        eg.cursos.add(*ecursos)

def materias2materias():
    from horarios.models import Materia as HMateria
    from estudios.models import Materia as EMateria
    from estudios.models import Curso
    hmaterias = HMateria.objects.all()
    for hm in hmaterias:
        try:
            ecurso = Curso.objects.get(clave_ex=hm.curso.clave_ex, entidad=hm.curso.ronda.entidad, ronda=hm.curso.ronda)
            EMateria.objects.create(curso=ecurso, nombre=hm.nombre, abreviatura=hm.abreviatura, horas=hm.horas,
                                         duracion=hm.duracion, observaciones=hm.observaciones, clave_ex=hm.clave_ex)
        except:
            pass

def Gauser_extra_horarios2Gauser_extra_estudios():
    from horarios.models import Gauser_extra_horarios
    from estudios.models import Gauser_extra_estudios
    from estudios.models import Grupo
    gehs = Gauser_extra_horarios.objects.all()
    for geh in gehs:
        try:
            egrupo = Grupo.objects.get(ronda=geh.ge.ronda, clave_ex=geh.grupo.clave_ex)
            Gauser_extra_estudios.objects.create(ge=geh.ge, grupo=egrupo, tutor=geh.tutor, cotutor=geh.cotutor)
        except:
            Gauser_extra_estudios.objects.create(ge=geh.ge, tutor=geh.tutor, cotutor=geh.cotutor)
