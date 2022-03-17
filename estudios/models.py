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

    @property
    def grupos(self):
        return Grupo.objects.filter(cursos__in=[self])

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
    ge = models.OneToOneField(Gauser_extra, on_delete=models.CASCADE)  # Alumno
    grupo = models.ForeignKey(Grupo, blank=True, null=True, on_delete=models.CASCADE)  # Grupo del alumno
    tutor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='estudios_tutor',
                              on_delete=models.CASCADE)
    cotutor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='estudios_cotutor',
                                on_delete=models.CASCADE)

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


#######################################################################################
############################# EVALUACIÓN LOMLOE #######################################
#######################################################################################

class PerfilSalida(models.Model):
    ETAPAS_PERFIL_SALIDA = (('00INF', 'Infantil'), ('10PRI', 'Primaria'), ('20ESO', 'Secundaria Obligatoria'),
                            ('30FPB', 'Ciclos Formativos de Grado Basico'),
                            ('35FPB', 'Ciclos Formativos de Grado Medio'),
                            ('40FPB', 'Ciclos Formativos de Grado Superior'),
                            ('50BAC', 'Bachillerato'),
                            ('INF', 'Infantil antinguo'), ('PRI', 'Primaria antinguo'),
                            ('SEC', 'Secundaria Obligatoria antinguo'),
                            ('BAC', 'Bachillerato antinguo'),
                            ('20SEC', 'Secundaria Obligatoria borrar'))
    ley = models.CharField('Ley asociada a definir el perfil de salida', blank=True, null=True, max_length=300)
    observaciones = models.TextField('Observaciones', blank=True, null=True)
    etapa = models.CharField('Etapa escolar', choices=ETAPAS_PERFIL_SALIDA, default='10PRI', max_length=5)

    class Meta:
        verbose_name_plural = 'Perfiles de salida'
        ordering = ['etapa',]

    def __str__(self):
        return '%s - %s' % (self.ley, self.get_etapa_display())


class CompetenciaClave(models.Model):
    ps = models.ForeignKey(PerfilSalida, on_delete=models.CASCADE, blank=True, null=True)
    orden = models.IntegerField('Número de competencia clave', default=0)
    competencia = models.CharField('Competencia clave', blank=True, null=True, max_length=350)
    siglas = models.CharField('Siglas Competencia clave', blank=True, null=True, max_length=6)
    texto = models.TextField('Descripción de la competencia clave', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Competencias Clave'
        ordering = ['ps', 'orden']

    def __str__(self):
        return '%s - (%s) %s' % (self.ps, self.siglas, self.competencia)


class DescriptorOperativo(models.Model):
    cc = models.ForeignKey(CompetenciaClave, on_delete=models.CASCADE, blank=True, null=True)
    clave = models.CharField('Clave del descriptor', blank=True, null=True, max_length=9)
    texto = models.TextField('Descripción del descriptor operativo', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Descriptores'
        ordering = ['cc', 'clave']

    def __str__(self):
        return '(%s) %s' % (self.cc, self.texto[:100])


# CURSOS_LOMLOE = (('000I0', 'Primer Ciclo Infantil - 0 años'), ('001I1', 'Primer Ciclo Infantil - 1 año'),
#                  ('002I2', 'Primer Ciclo Infantil - 2 años'), ('003I3', 'Segundo Ciclo Infantil - 3 años'),
#                  ('004I4', 'Segundo Ciclo Infantil - 4 años'), ('005I5', 'Segundo Ciclo Infantil - 5 años'),
#                  ('006P1', 'Primer Ciclo Primaria - 1er Curso'), ('007P2', 'Primer Ciclo Primaria - 2o Curso'),
#                  ('008P3', 'Segundo Ciclo Primaria - 3er Curso'), ('009P4', 'Segundo Ciclo Primaria - 4o Curso'),
#                  ('010P5', 'Tercer Ciclo Primaria - 5o Curso'), ('011P6', 'Tercer Ciclo Primaria - 6o Curso'),
#                  ('012E1', '1º de ESO'), ('017E2', '2º de ESO'), ('021E3', '3º de ESO'), ('026E4', '4º de ESO'),
#                  ('031B1C', '1º Bachillerato de Ciencias y Tecnología'),
#                  ('036B2C', '2º Bachillerato de Ciencias y Tecnología'),
#                  ('041B1H', '1º Bachillerato de Humanidades y Ciencias Sociales'),
#                  ('046B2H', '2º Bachillerato de Humanidades y Ciencias Sociales'),
#                  ('051B1A', '1º Bachillerato de Artes'),
#                  ('056B2A', '2º Bachillerato de Artes'),
#                  ('061B1G', '1º Bachillerato General'),
#                  ('066B2G', '2º Bachillerato General'))


class AreaMateria(models.Model):
    CURSOS_LOMLOE = (('00INF0', 'Primer Ciclo Infantil - 0 años'), ('00INF1', 'Primer Ciclo Infantil - 1 año'),
                     ('00INF2', 'Primer Ciclo Infantil - 2 años'), ('00INF3', 'Segundo Ciclo Infantil - 3 años'),
                     ('00INF4', 'Segundo Ciclo Infantil - 4 años'), ('00INF5', 'Segundo Ciclo Infantil - 5 años'),
                     ('10PRI1', 'Primer Ciclo Primaria - 1er Curso'), ('10PRI2', 'Primer Ciclo Primaria - 2o Curso'),
                     ('10PRI3', 'Segundo Ciclo Primaria - 3er Curso'), ('10PRI4', 'Segundo Ciclo Primaria - 4o Curso'),
                     ('10PRI5', 'Tercer Ciclo Primaria - 5o Curso'), ('10PRI6', 'Tercer Ciclo Primaria - 6o Curso'),
                     ('20ESO1', '1º de ESO'), ('20ESO2', '2º de ESO'), ('20ESO3', '3º de ESO'), ('20ESO4', '4º de ESO'),
                     ('50BAC1C', '1º Bachillerato de Ciencias y Tecnología'),
                     ('50BAC2C', '2º Bachillerato de Ciencias y Tecnología'),
                     ('50BAC1H', '1º Bachillerato de Humanidades y Ciencias Sociales'),
                     ('50BAC2H', '2º Bachillerato de Humanidades y Ciencias Sociales'),
                     ('50BAC1A', '1º Bachillerato de Artes'),
                     ('50BAC2A', '2º Bachillerato de Artes'),
                     ('50BAC1G', '1º Bachillerato General'),
                     ('50BAC2G', '2º Bachillerato General'))
    ps = models.ForeignKey(PerfilSalida, on_delete=models.CASCADE, blank=True, null=True)
    nombre = models.CharField('Nombre del Área/Materia', blank=True, null=True, max_length=350)
    texto = models.TextField('Descripción del Área/Materia', blank=True, null=True)
    # curso = models.CharField('Curso', choices=CURSOS_LOMLOE, max_length=8, blank=True, null=True)
    # periodos = models.FloatField('Número de periodos u horas semanales', default=3, blank=True, null=True)
    prueba = models.IntegerField('a', default=3, blank=True, null=True)
    class Meta:
        verbose_name_plural = 'Áreas/Materias'
        # ordering = ['ps', 'curso']
        ordering = ['ps', ]

    @property
    def num_ces(self):
        return self.competenciaespecifica_set.all().count()

    @property
    def num_cevs(self):
        n = 0
        for ce in self.competenciaespecifica_set.all():
            n += ce.criterioevaluacion_set.all().count()
        return n

    @property
    def cevs(self):
        criterios = []
        for ce in self.competenciaespecifica_set.all():
            for cev in ce.criterioevaluacion_set.all():
                criterios.append(cev)
        return criterios

    def __str__(self):
        return '%s - %s' % (self.nombre, self.texto[:100])


class CompetenciaEspecifica(models.Model):
    am = models.ForeignKey(AreaMateria, on_delete=models.CASCADE, blank=True, null=True)
    orden = models.IntegerField('Número de competencia específica', default=0)
    nombre = models.TextField('Nombre de la competencia específica', blank=True, null=True)
    texto = models.TextField('Descripción de la competencia específica', blank=True, null=True)
    dos = models.ManyToManyField(DescriptorOperativo, blank=True)

    class Meta:
        verbose_name_plural = 'Competencias Específicas'
        ordering = ['orden', ]

    def __str__(self):
        n = self.nombre if self.nombre else 'Sin nombre'
        a = self.am.nombre if self.am else 'No área/materia'
        return '%s.- (%s) - %s' % (self.orden, a, n)
        # if self.am:
        #     return '%s.- (%s) - %s' % (self.orden, self.am.nombre, self.nombre[:50])
        # else:
        #     return '%s.- (%s) - %s' % (self.orden, 'No área/Materia', self.nombre[:50])


class CriterioEvaluacion(models.Model):
    CICLOS = (('PRI1', 'Primer Ciclo Primaria'), ('PRI2', 'Segundo Ciclo Primaria'), ('PRI3', 'Tercer Ciclo Primaria'),
              ('SEC1', '1º - 3º de ESO'), ('SEC2', '4º de ESO'), ('SEC3', '1º - 4º de ESO'), ('SEC4', '1º - 2º de ESO'),
              ('SEC5', '3º - 4º de ESO'), ('BAC', 'Bachillerato'), ('ESO1', '1º de ESO'),
              ('ESO2', '2º de ESO'), ('ESO3', '3º de ESO'),
              ('BA1C', '1º Bachillerato de Ciencias y Tecnología'),
              ('BA2C', '2º Bachillerato de Ciencias y Tecnología'),
              ('BA1H', '1º Bachillerato de Humanidades y Ciencias Sociales'),
              ('BA2H', '2º Bachillerato de Humanidades y Ciencias Sociales'),
              ('BA1A', '1º Bachillerato de Artes'),
              ('BA2A', '2º Bachillerato de Artes'),
              ('BA1G', '1º Bachillerato General'),
              ('BA2G', '2º Bachillerato General'))
    ce = models.ForeignKey(CompetenciaEspecifica, on_delete=models.CASCADE, blank=True, null=True)
    ciclo = models.CharField('Ciclo', choices=CICLOS, default='PRI1', max_length=5)
    materia = models.CharField('Nombre específico de la materia (opocional)', max_length=205, blank=True, null=True)
    orden = models.IntegerField('Número del criterio de evaluación', default=0)
    texto = models.TextField('Descripción del criterio de evaluación', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Criterios de Evaluación'
        ordering = ['orden', ]

    def __str__(self):
        if self.materia:
            return '%s (%s) - %s: %s' % (self.ce, self.get_ciclo_display(), self.materia, self.texto[:50])
        else:
            return '%s (%s) - %s' % (self.ce, self.get_ciclo_display(), self.texto[:50])
