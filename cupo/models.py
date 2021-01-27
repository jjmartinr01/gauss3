# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.db import models
from django.db.models import Q
from django.utils.timezone import now

from entidades.views import get_entidad_general
from gauss.funciones import pass_generator
from autenticar.models import Gauser, Permiso
from entidades.models import Subentidad, Entidad, Ronda, Cargo, Gauser_extra, Dependencia, MiembroDepartamento
from entidades.models import Departamento as DepEntidad
from estudios.models import Materia, Curso, Grupo, EtapaEscolar
from horarios.models import Actividad, Horario, Sesion, SesionExtra
from mensajes.models import Aviso
from programaciones.models import Departamento, Especialidad_entidad
from math import ceil

logger = logging.getLogger('django')


class Cupo(models.Model):
    # entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la versión del cupo", max_length=150)
    max_completa = models.IntegerField("Máximo número de periodos lectivos con jornada completa", default=22)
    min_completa = models.IntegerField("Mínimo número de periodos lectivos con jornada completa", default=20)
    max_dostercios = models.IntegerField("Máximo número de periodos lectivos con 2/3 de jornada", default=14)
    min_dostercios = models.IntegerField("Mínimo número de periodos lectivos con 2/3 de jornada", default=13)
    max_media = models.IntegerField("Máximo número de periodos lectivos con media jornada", default=11)
    min_media = models.IntegerField("Mínimo número de periodos lectivos con media jornada", default=10)
    max_tercio = models.IntegerField("Máximo número de periodos lectivos con 1/3 de jornada", default=7)
    min_tercio = models.IntegerField("Mínimo número de periodos lectivos con 1/3 de jornada", default=6)
    bloqueado = models.BooleanField("¿Está bloqueado?", default=False)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'Cupos de profesorado'
        ordering = ['-creado']

    def __str__(self):
        return '%s %s (%s)' % (self.ronda.entidad.name, self.nombre, self.modificado)


class EspecialidadCupo(models.Model):
    cupo = models.ForeignKey(Cupo, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la especialidad", max_length=150)
    departamento = models.ForeignKey(Departamento, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Especialidades en el cupo del profesorado'
        ordering = ['nombre']

    def __str__(self):
        return '%s %s (%s)' % (self.cupo.nombre, self.nombre, self.cupo.ronda.entidad.name)


class FiltroCupo(models.Model):
    cupo = models.ForeignKey(Cupo, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre del filtro", max_length=150)
    filtro = models.CharField("Texto de filtrado", max_length=50)

    class Meta:
        verbose_name_plural = 'Filtros aplicados al cupo'

    def __str__(self):
        return '%s %s (%s)' % (self.cupo.ronda.entidad.name, self.nombre, self.filtro)


class Materia_cupo(models.Model):
    cupo = models.ForeignKey(Cupo, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(EspecialidadCupo, blank=True, null=True, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la materia o actividad", max_length=100, null=True, blank=True)
    periodos = models.IntegerField("Número de periodos lectivos por semana", null=True, blank=True)
    num_alumnos = models.IntegerField("Nº de alumnos previstos", default=1)
    min_num_alumnos = models.IntegerField("Nº de alumnos mínimo por grupo", default=10)
    max_num_alumnos = models.IntegerField("Nº de alumnos máximo por grupo", default=30)

    @property
    def num_grupos(self):
        if self.num_alumnos >= self.min_num_alumnos:
            num_grupos = int(ceil(float(self.num_alumnos) / float(self.max_num_alumnos)))
        else:
            num_grupos = 0
        return num_grupos

    @property
    def total_periodos(self):
        return self.num_grupos * self.periodos

    class Meta:
        verbose_name_plural = 'Materias incluidas en el cupo'
        ordering = ['curso', 'nombre']

    def __str__(self):
        return '%s (%s) -- %s' % (self.nombre, self.curso, self.cupo)


class Profesores_cupo(models.Model):
    cupo = models.ForeignKey(Cupo, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(EspecialidadCupo, blank=True, null=True, on_delete=models.CASCADE)
    num_periodos = models.IntegerField("Nº de periodos lectivos para la especialidad", null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Profesores por especialidad asociados cupo'
        ordering = ['especialidad__departamento']

    @property
    def materias(self):
        return Materia_cupo.objects.filter(especialidad=self.especialidad, cupo=self.cupo)

    @property
    def reparto_profes(self):
        profes_completos = int(self.num_periodos / self.cupo.min_completa)
        periodos_sobrantes = self.num_periodos % self.cupo.min_completa
        profes_dostercios = int(periodos_sobrantes / self.cupo.min_dostercios)
        periodos_sobrantes = periodos_sobrantes % self.cupo.min_dostercios
        profes_media = int(periodos_sobrantes / self.cupo.min_media)
        periodos_sobrantes = periodos_sobrantes % self.cupo.min_media
        profes_tercio = int(periodos_sobrantes / self.cupo.min_tercio)
        periodos_sobrantes = periodos_sobrantes % self.cupo.min_tercio

        # if periodos_sobrantes >= self.cupo.min_dostercios:
        #     profes_dostercios = int(periodos_sobrantes / self.cupo.min_dostercios)
        #     periodos_sobrantes = periodos_sobrantes % self.cupo.min_dostercios
        # else:
        #     profes_dostercios = 0
        # if periodos_sobrantes >= self.cupo.min_media:
        #     profes_media = int(periodos_sobrantes / self.cupo.min_media)
        #     periodos_sobrantes = periodos_sobrantes % self.cupo.min_media
        # else:
        #     profes_media = 0
        # if periodos_sobrantes >= self.cupo.min_tercio:
        #     profes_tercio = int(periodos_sobrantes / self.cupo.min_tercio)
        #     periodos_sobrantes = periodos_sobrantes % self.cupo.min_tercio
        # else:
        #     profes_tercio = 0
        return {'profes_completos': profes_completos, 'profes_dostercios': profes_dostercios,
                'profes_media': profes_media, 'profes_tercio': profes_tercio, 'periodos_sobrantes': periodos_sobrantes,
                'num_periodos': self.num_periodos}

    def __str__(self):
        return 'Cupo: %s (%s) -- %s:%s' % (
            self.cupo.nombre, self.cupo.ronda.entidad.code, self.especialidad.nombre, self.num_periodos)


class Profesor_cupo(models.Model):
    TIPO_PROFESOR = (('DEF', 'Destino definitivo'), ('INT', 'Interino de cupo'), ('NONE', 'No necesario'))
    TIPO_JORNADA = (
        ('1', 'Jornada completa'), ('2', 'Jornada de 2/3'), ('3', 'Media jornada'), ('4', 'Jornada de 1/3'))
    profesorado = models.ForeignKey(Profesores_cupo, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre del profesor/a', max_length=300, blank=True, null=True)
    tipo = models.CharField('Tipo', choices=TIPO_PROFESOR, blank=True, null=True, max_length=10, default='DEF')
    jornada = models.CharField('Jornada', choices=TIPO_JORNADA, blank=True, null=True, max_length=10, default='1')
    bilingue = models.BooleanField('Es bilingüe?', default=False)
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')

    class Meta:
        verbose_name_plural = 'Profesores del cupo'
        ordering = ['profesorado__especialidad__departamento', 'tipo', 'jornada']

    def __str__(self):
        return '%s (%s) -- %s:%s' % (
            self.profesorado.cupo.nombre, self.profesorado.especialidad.nombre, self.nombre, self.get_jornada_display())


############################################################################################
####################### Plantilla Orgánica #################################################
############################################################################################
    # '222074 -> 1º E.S.O. (ADAPTACIÓN CURRICULAR EN GRUPO)'
    # '222075 -> 2º E.S.O. (ADAPTACIÓN CURRICULAR EN GRUPO)'
    # '101324 -> 2º E.S.O.'
    # '101325 -> 3º E.S.O.'
TC = {
    'I.E.S. - Instituto de Educación Secundaria': {
        'Educación Secundaria Obligatoria': {
            'Troncales': {
                'q': Q(actividad__clave_ex='1') & (Q(materia__grupo_materias__icontains='tronca') | Q(
                    materia__grupo_materias__icontains='extranj') | Q(
                    materia__grupo_materias__icontains='obligator')) & Q(
                    materia__curso__etapa_escolar__clave_ex='24') & ~Q(
                    materia__curso__clave_ex__in=['222074', '222075']) & ~Q(materia__nombre__icontains='mbito'),
                'horas_base': True,
                'codecol': 10005
            },
            'Específicas': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='espec'),
                'horas_base': True,
                'codecol': 10010
            },
            'Libre Conf. Aut.': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='libre conf') & ~Q(
                    materia__curso__clave_ex__in=['222074', '222075']) & ~Q(materia__nombre__icontains='mbito'),
                'horas_base': True,
                'codecol': 10015
            },
            'Rel./Val. Éticos': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='Rel. y Aten.'),
                'horas_base': True,
                'codecol': 10020
            },
            'Desdobles ESO': {
                'q': (Q(actividad__clave_ex='539') | Q(actividad__clave_ex='400') | Q(actividad__clave_ex='522')) & Q(
                    materia__curso__etapa_escolar__clave_ex='24'),
                'horas_base': True,
                'codecol': 10025
            },
        },
        'Bachillerato': {
            'Troncales': {
                'q': (Q(materia__grupo_materias__icontains='tronca') | Q(
                    materia__grupo_materias__icontains='extranj') | Q(
                    materia__grupo_materias__icontains='obligator')) & Q(
                    materia__curso__etapa_escolar__clave_ex='31') & Q(actividad__clave_ex='1'),
                'horas_base': True,
                'codecol': 10030
            },
            'Específicas': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='31') & Q(
                    materia__grupo_materias__icontains='espec'),
                'horas_base': True,
                'codecol': 10035
            },
            'Desdobles BACH': {
                'q': (Q(actividad__clave_ex='539') | Q(actividad__clave_ex='400') | Q(actividad__clave_ex='522')) & Q(
                    materia__curso__etapa_escolar__clave_ex='31'),
                'horas_base': True,
                'codecol': 10040
            },
        },
        'Formación Profesional': {
            'CFGM': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['1373', '23']),
                'horas_base': True,
                'codecol': 10045
            },
            'CFGS': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['2', '1375']),
                'horas_base': True,
                'codecol': 10050
            },
            'FPB': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='5504'),
                'horas_base': True,
                'codecol': 10055
            },
        },
        'Atención a la Diversidad y otras horas': {
            'PACG': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__clave_ex__in=['222074', '222075']),
                'horas_base': False,
                'codecol': 10060
            },
            'Refuerzo 1º ESO': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='170506'),
                'horas_base': False,
                'codecol': 10065
            },
            'PMAR1': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='101324'),
                'horas_base': False,
                'codecol': 10070
            },
            'PMAR2': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='101325'),
                'horas_base': False,
                'codecol': 10075
            },
            'Curso Prep. Acceso CCFF': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['3129', ]),
                'horas_base': False,
                'codecol': 10080
            },
            'Tutorías': {
                'q': Q(actividad__clave_ex='519') | Q(actividad__clave_ex='2') | Q(actividad__clave_ex='376'),
                'horas_base': True,
                'codecol': 10085
            },
            'Jefatura Depart./CCP': {
                'q': Q(actividad__clave_ex='547') | Q(actividad__clave_ex='545'),
                'horas_base': True,
                'codecol': 10090
            },
            'Mayor 55 años': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': False,
                'codecol': 10095
            },
        },
    },
    'S.I.E.S. - Sección de Instituto de Educación Secundaria': {
        'Educación Secundaria Obligatoria': {
            'Troncales': {
                'q': Q(actividad__clave_ex='1') & (Q(materia__grupo_materias__icontains='tronca') | Q(
                    materia__grupo_materias__icontains='extranj') | Q(
                    materia__grupo_materias__icontains='obligator')) & Q(
                    materia__curso__etapa_escolar__clave_ex='24') & ~Q(
                    materia__curso__clave_ex__in=['222074', '222075']) & ~Q(materia__nombre__icontains='mbito'),
                'horas_base': True,
                'codecol': 10005
            },
            'Específicas': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='espec'),
                'horas_base': True,
                'codecol': 10010
            },
            'Libre Conf. Aut.': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='libre conf') & ~Q(
                    materia__curso__clave_ex__in=['222074', '222075']) & ~Q(materia__nombre__icontains='mbito'),
                'horas_base': True,
                'codecol': 10015
            },
            'Rel./Val. Éticos': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='Rel. y Aten.'),
                'horas_base': True,
                'codecol': 10020
            },
            'Desdobles ESO': {
                'q': (Q(actividad__clave_ex='539') | Q(actividad__clave_ex='400') | Q(actividad__clave_ex='522')) & Q(
                    materia__curso__etapa_escolar__clave_ex='24'),
                'horas_base': True,
                'codecol': 10025
            },
        },
        'Bachillerato': {
            'Troncales': {
                'q': (Q(materia__grupo_materias__icontains='tronca') | Q(
                    materia__grupo_materias__icontains='extranj') | Q(
                    materia__grupo_materias__icontains='obligator')) & Q(
                    materia__curso__etapa_escolar__clave_ex='31') & Q(actividad__clave_ex='1'),
                'horas_base': True,
                'codecol': 10030
            },
            'Específicas': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='31') & Q(
                    materia__grupo_materias__icontains='espec'),
                'horas_base': True,
                'codecol': 10035
            },
            'Desdobles BACH': {
                'q': (Q(actividad__clave_ex='539') | Q(actividad__clave_ex='400') | Q(actividad__clave_ex='522')) & Q(
                    materia__curso__etapa_escolar__clave_ex='31'),
                'horas_base': True,
                'codecol': 10040
            },
        },
        'Formación Profesional': {
            'CFGM': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['1373', '23']),
                'horas_base': True,
                'codecol': 10045
            },
            'CFGS': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['2', '1375']),
                'horas_base': True,
                'codecol': 10050
            },
            'FPB': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='5504'),
                'horas_base': True,
                'codecol': 10055
            },
        },
        'Atención a la Diversidad y otras horas': {
            'PACG': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__clave_ex__in=['222074', '222075']),
                'horas_base': False,
                'codecol': 10060
            },
            'Refuerzo 1º ESO': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='170506'),
                'horas_base': False,
                'codecol': 10065
            },
            'PMAR1': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='101324'),
                'horas_base': False,
                'codecol': 10070
            },
            'PMAR2': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='101325'),
                'horas_base': False,
                'codecol': 10075
            },
            'Curso Prep. Acceso CCFF': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['3129', ]),
                'horas_base': False,
                'codecol': 10080
            },
            'Tutorías': {
                'q': Q(actividad__clave_ex='519') | Q(actividad__clave_ex='2') | Q(actividad__clave_ex='376'),
                'horas_base': True,
                'codecol': 10085
            },
            'Jefatura Depart./CCP': {
                'q': Q(actividad__clave_ex='547') | Q(actividad__clave_ex='545'),
                'horas_base': True,
                'codecol': 10090
            },
            'Mayor 55 años': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': False,
                'codecol': 10095
            },
        },
    },
    'C.E.P.A. - Centro Público de Educación de Personas Adultas': {
        'Educación Secundaria': {
            'ESPA Nivel I': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222076', '222077']),
                'horas_base': True,
                'codecol': 10100
            },
            'ESPA Nivel II': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222078', '222079']),
                'horas_base': True,
                'codecol': 10105
            },
            'ESPA Dist. Nivel I': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222080', '222081']),
                'horas_base': True,
                'codecol': 10110
            },
            'ESPA Dist. Nivel II': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222082', '222083']),
                'horas_base': True,
                'codecol': 10115
            },
        },
        'Enseñanzas Iniciales': {
            'Ens. Iniciales I': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3167') & Q(
                    materia__curso__clave_ex='121469'),
                'horas_base': True,
                'codecol': 10120
            },
            'Ens. Iniciales II': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3167') & Q(
                    materia__curso__clave_ex='121470'),
                'horas_base': True,
                'codecol': 10125
            },
        },
        'Educación no reglada': {
            'Competencias N-2': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__clave_ex='222071'),
                'horas_base': False,
                'codecol': 10130
            },
            'Alfab. Inmigrantes': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='nmigrantes'),
                'horas_base': False,
                'codecol': 10135
            },
            'Cursos de preparación': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='mayores de'),
                'horas_base': False,
                'codecol': 10140
            },
            'Ofimática': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='ofim'),
                'horas_base': False,
                'codecol': 10145
            },
            'Informática': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='inform'),
                'horas_base': False,
                'codecol': 10150
            },
            'Mecanografía': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='mecanog'),
                'horas_base': False,
                'codecol': 10155
            },
            'Inglés': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='ingl'),
                'horas_base': False,
                'codecol': 10160
            },
        },
        'Otras': {
            'Tutorías': {
                'q': Q(actividad__clave_ex='519') | Q(actividad__clave_ex='2') | Q(actividad__clave_ex='376'),
                'horas_base': True,
                'codecol': 10165
            },
            'Jefatura Depart./CCP': {
                'q': Q(actividad__clave_ex='547') | Q(actividad__clave_ex='545'),
                'horas_base': True,
                'codecol': 10170
            },
            'Mayor 55 años': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': False,
                'codecol': 10175
            },
        },
    },
}


class PlantillaOrganica(models.Model):
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, blank=True, null=True)
    ronda_centro = models.ForeignKey(Ronda, on_delete=models.CASCADE, blank=True, null=True)
    horario = models.ForeignKey(Horario, on_delete=models.SET_NULL, blank=True, null=True)
    carga_completa = models.BooleanField('¿Se ha cargado completamente?', default=False)
    creado = models.DateTimeField("Fecha y hora creación de la PO", auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Plantillas orgánicas'
        ordering = ['-creado']

    ########################################################################
    ############ Cargamos dependencias:
    def carga_dependencia(self, data):
        try:
            dependencia, c = Dependencia.objects.get_or_create(clave_ex=data['x_dependencia'],
                                                               entidad=self.ronda_centro.entidad)
            if c:
                dependencia.nombre = data['c_coddep']
                dependencia.abrev = data['c_coddep']
                dependencia.es_aula = True
                dependencia.save()
        except:
            dependencias = Dependencia.objects.filter(clave_ex=data['x_dependencia'],
                                                      entidad=self.ronda_centro.entidad)
            dependencia = dependencias[0]
            dependencias.exclude(pk__in=[dependencia.pk]).delete()
            dependencia.nombre = data['c_coddep']
            dependencia.abrev = data['c_coddep']
            dependencia.es_aula = True
            dependencia.save()
        return dependencia

    def carga_dependencias(self):
        dependencias = self.plantillaxls_set.filter(~Q(x_dependencia='-1')).values('x_dependencia',
                                                                                   'c_coddep').distinct()
        for dependencia in dependencias:
            self.carga_dependencia(dependencia)


    ########################################################################
    ############ Cargamos etapas:
    def carga_etapas(self):
        etapas = self.plantillaxls_set.all().values('etapa_escolar', 'x_etapa_escolar').distinct()
        for etapa in etapas:
            EtapaEscolar.objects.get_or_create(nombre=etapa['etapa_escolar'], clave_ex=etapa['x_etapa_escolar'])

    ########################################################################
    ############ Cargamos cursos:
    def carga_curso(self, data):
        try:
            curso, c = Curso.objects.get_or_create(clave_ex=data['x_curso'], ronda=self.ronda_centro)
        except:
            cursos = Curso.objects.filter(clave_ex=data['x_curso'], ronda=self.ronda_centro)
            curso = cursos[0]
            cursos.exclude(pk__in=[curso.pk]).delete()
        curso.nombre = data['curso']
        curso.nombre_especifico = data['omc']
        try:
            curso.etapa_escolar = EtapaEscolar.objects.get(clave_ex=data['x_etapa_escolar'])
        except:
            LogCarga.objects.create(g_e=self.g_e, log='No encuentra etapa: %s' % data['x_etapa_escolar'])
        curso.save()
        return curso

    def carga_cursos(self):
        cursos = self.plantillaxls_set.all().values('x_curso', 'curso', 'omc', 'x_etapa_escolar')
        for curso in cursos:
            self.carga_curso(curso)
        return True

    ########################################################################
    ############ Cargamos grupos:
    def carga_grupo(self, data):
        try:
            grupo, c = Grupo.objects.get_or_create(clave_ex=data['x_unidad'], ronda=self.ronda_centro)
            if c:
                grupo.nombre = data['unidad']
                grupo.save()
        except:
            grupos = Grupo.objects.filter(clave_ex=data['x_unidad'], ronda=self.ronda_centro)
            grupo = grupos[0]
            grupos.exclude(pk__in=[grupo.pk]).delete()
            grupo.nombre = data['unidad']
            grupo.save()
        try:
            curso = Curso.objects.get(clave_ex=data['x_curso'], ronda=self.ronda_centro)
            grupo.cursos.add(curso)
        except:
            LogCarga.objects.create(g_e=self.g_e, log='Error al cargar el curso: %s' % data['x_curso'])
        return grupo

    def carga_grupos(self):
        grupos = self.plantillaxls_set.all().values('x_curso', 'x_unidad', 'unidad')
        for grupo in grupos:
            self.carga_grupo(grupo)

    ########################################################################
    ############ Cargamos materias:
    def carga_materia(self, data):
        try:
            curso = Curso.objects.get(clave_ex=data['x_curso'], ronda=self.ronda_centro)
        except:
            LogCarga.objects.create(g_e=self.g_e, log='Error carga de curso de la materia: %s' % data['x_materiaomg'])
            curso = None
        try:
            materia, c = Materia.objects.get_or_create(clave_ex=data['x_materiaomg'], curso=curso)
        except:
            materias = Materia.objects.filter(clave_ex=data['x_materiaomg'], curso=curso)
            materia = materias[0]
            materias.exclude(pk__in=[materia.pk]).delete()
        horas, sc, minutos = data['horas_semana_min'].rpartition(':')
        try:
            materia.horas = int(horas)
        except:
            LogCarga.objects.create(g_e=self.g_e, log='Error al cargar horas: %s' % horas)
        nombre, dash, abreviatura = data['materia'].rpartition('-')
        materia.nombre = nombre.strip()
        materia.abreviatura = abreviatura.strip()
        materia.grupo_materias = data['grupo_materias']
        materia.horas_semana_min = data['horas_semana_min']
        materia.horas_semana_max = data['horas_semana_max']
        materia.save()
        return materia

    def carga_materias(self):
        materias = self.plantillaxls_set.filter(x_actividad='1').values('horas_semana_max', 'horas_semana_min',
                                                                        'grupo_materias', 'x_materiaomg', 'x_curso',
                                                                        'materia').distinct()
        for materia in materias:
            self.carga_materia(materia)

    ########################################################################
    ############ Cargamos departamentos:
    def carga_departamentos(self):
        departamentos = self.plantillaxls_set.all().values('departamento', 'x_departamento').distinct()
        for d in departamentos:
            if d['x_departamento'] == '63':  # El 63 es el departamento de Actividades compl. y extraes.
                DepEntidad.objects.get_or_create(ronda=self.ronda_centro, nombre=d['departamento'],
                                                 clave_ex=d['x_departamento'], didactico=False)
            else:
                DepEntidad.objects.get_or_create(ronda=self.ronda_centro, nombre=d['departamento'],
                                                 clave_ex=d['x_departamento'])
        return True

    ########################################################################
    ############ Cargamos puestos <-> cargos:
    def carga_puestos(self):
        puestos = self.plantillaxls_set.all().values('puesto', 'x_puesto').distinct()
        for p in puestos:
            Cargo.objects.get_or_create(cargo=p['puesto'], clave_cargo=p['x_puesto'], borrable=False,
                                        entidad=self.ronda_centro.entidad)
        return True

    ########################################################################
    ############ Cargamos actividades:
    def carga_actividades(self):
        actividades = self.plantillaxls_set.all().values('actividad', 'x_actividad', 'l_requnidad',
                                                         'docencia').distinct()
        b = {'S': True, 'N': False, 's': True, 'n': False}
        for a in actividades:
            try:
                act, c = Actividad.objects.get_or_create(entidad=self.ronda_centro.entidad, clave_ex=a['x_actividad'])
                if c:
                    act.requiere_unidad=b[a['l_requnidad']]
                    act.nombre=a['actividad']
                    act.requiere_materia=b[a['docencia']]
                    act.save()
            except Exception as msg:
                log = 'Error cargar actividad %s. %s' % (a['x_actividad'], str(msg))
                LogCarga.objects.create(g_e=self.g_e, log=log)
                acts = Actividad.objects.filter(entidad=self.ronda_centro.entidad, clave_ex=a['x_actividad'])
                act = acts[0]
                acts.exclude(pk__in=[act.pk]).delete()
                act.requiere_unidad = b[a['l_requnidad']]
                act.nombre = a['actividad']
                act.requiere_materia = b[a['docencia']]
                act.save()
        return True

    ########################################################################
    ############ Cargamos docentes:
    def carga_cargo_g_docente(self):
        egeneral, errores = get_entidad_general()
        cargo_data = Cargo.objects.get(clave_cargo='g_docente', entidad=egeneral).export_data()
        cargo, c = Cargo.objects.get_or_create(entidad=self.ronda_centro.entidad, clave_cargo=cargo_data['clave_cargo'],
                                               borrable=False, cargo=cargo_data['cargo'])
        for code_nombre in cargo_data['permisos']:
            cargo.permisos.add(Permiso.objects.get(code_nombre=code_nombre))
        return cargo

    def get_gex_docente(self, gauser, clave_ex, x_puesto, x_departamento, cargo):
        gex, c = Gauser_extra.objects.get_or_create(gauser=gauser, ronda=self.ronda_centro)
        gex.clave_ex = clave_ex
        gex.activo = True
        gex.save()
        gex.cargos.add(cargo)
        try:
            puesto = Cargo.objects.get(clave_cargo=x_puesto, entidad=self.ronda_centro.entidad)
            gex.cargos.add(puesto)
        except:
            puesto = None
            LogCarga.objects.create(g_e=gex, log='No encuentra puesto: %s' % x_puesto)
        try:
            departamento = DepEntidad.objects.get(clave_ex=x_departamento, ronda=self.ronda_centro)
            midep, c = MiembroDepartamento.objects.get_or_create(departamento=departamento, g_e=gex)
            if puesto:
                midep.puesto = puesto.clave_cargo
                midep.save()
        except:
            LogCarga.objects.create(g_e=gex, log='No encuentra departamento: %s' % x_departamento)
        return gex

    def carga_docentes(self):
        ges = self.plantillaxls_set.all().values('docente', 'x_docente', 'dni', 'email', 'x_puesto',
                                                 'x_departamento').distinct()
        x_docentes = []
        docentes = []
        cargo = self.carga_cargo_g_docente()
        for ge in ges:
            if not ge['x_docente'] in x_docentes:
                x_docentes.append(ge['x_docente'])
                last_name, first_name = ge['docente'].split(', ')
                clave_ex, dni, x_puesto, x_departamento = ge['x_docente'], ge['dni'], ge['x_puesto'], ge['x_departamento']
                username, email = ge['email'].split('@')[0], ge['email']
                try:
                    gauser = Gauser.objects.get(dni=dni)
                    gauser.username = username
                    gauser.first_name = first_name
                    gauser.last_name = last_name
                    gauser.email = email
                    gauser.save()
                    gex = self.get_gex_docente(gauser, clave_ex, x_puesto, x_departamento, cargo)
                    docentes.append(gex)
                except Exception as msg:
                    log = 'Error: %s. dni %s - username %s' % (str(msg), dni, username)
                    LogCarga.objects.create(g_e=self.g_e, log=log)
                    # logger.warning('Error: %s. dni %s - username %s' % (str(msg), dni, username))
                    try:
                        gex = Gauser_extra.objects.get(clave_ex=clave_ex, ronda=self.ronda_centro)
                        log = 'Sin embargo existe usuario con clave_x: %s - %s' % (clave_ex, gex)
                        logger.warning(log)
                        LogCarga.objects.create(g_e=self.g_e, log=log)
                    except:
                        try:
                            gauser = Gauser.objects.get(email=email)
                            log = 'Sin embargo existe usuario con email: %s - %s' % (email, gauser)
                            logger.warning(log)
                            LogCarga.objects.create(g_e=self.g_e, log=log)
                        except:
                            try:
                                Gauser.objects.get(username=username)
                                log = 'Ya existe un usuario: %s' % username
                                logger.warning(log)
                                LogCarga.objects.create(g_e=self.g_e, log=log)
                            except:
                                gauser = Gauser.objects.create_user(username, email=email, last_login=now(),
                                                                    password=pass_generator(size=9))
                                log = 'Creado usuario: %s' % (gauser)
                                LogCarga.objects.create(g_e=self.g_e, log=log)
                                gauser.first_name = first_name[0:29]
                                gauser.last_name = last_name[0:29]
                                gauser.dni = dni
                                gauser.save()
                                gex = self.get_gex_docente(gauser, clave_ex, x_puesto, x_departamento, cargo)
                                docentes.append(gex)
        return docentes

    ########################################################################
    ############ Cargamos sesiones:

    def carga_sesiones_docentes(self):
        try:
            Horario.objects.get(entidad=self.ronda_centro.entidad, predeterminado=True)
            horario, c = Horario.objects.get_or_create(entidad=self.ronda_centro.entidad, ronda=self.ronda_centro,
                                                       clave_ex=self.pk)
        except:
            horario, c = Horario.objects.get_or_create(entidad=self.ronda_centro.entidad, ronda=self.ronda_centro,
                                                       clave_ex=self.pk, predeterminado=True)
        if c:
            horario.nombre = 'Horario creado por carga de datos de plantilla orgánica: %s' % self.pk
            horario.save()
        self.horario = horario
        self.save()
        sesiones = []
        psxls = self.plantillaxls_set.all()
        for p in psxls:
            g_e = Gauser_extra.objects.get(clave_ex=p.x_docente, ronda=self.ronda_centro)
            sesion, c = Sesion.objects.get_or_create(horario=horario, dia=int(float(p.dia)), g_e=g_e,
                                                     hora_inicio=int(float(p.hora_inicio)),
                                                     hora_fin=int(float(p.hora_fin)),
                                                     hora_inicio_cadena=p.hora_inicio_cadena,
                                                     hora_fin_cadena=p.hora_fin_cadena)
            try:
                grupo = Grupo.objects.get(clave_ex=p.x_unidad, ronda=self.ronda_centro)
            except:
                LogCarga.objects.create(g_e=self.g_e, log='Error al cargar el grupo %s' % p.x_unidad)
                grupo = None
            try:
                if p.x_dependencia != '-1':
                    dependencia = Dependencia.objects.get(clave_ex=p.x_dependencia, entidad=self.ronda_centro.entidad)
                else:
                    dependencia = None
            except:
                LogCarga.objects.create(g_e=self.g_e, log='Error al cargar la dependencia %s' % p.x_dependencia)
                dependencia = None
            try:
                if p.x_materiaomg:
                    materia = Materia.objects.get(clave_ex=p.x_materiaomg, curso__ronda=self.ronda_centro)
                else:
                    materia = None
            except:
                LogCarga.objects.create(g_e=self.g_e, log='Error al cargar la materia %s' % p.x_materiaomg)
                materia = None
            try:
                actividad = Actividad.objects.get(entidad=self.ronda_centro.entidad, clave_ex=p.x_actividad)
            except:
                LogCarga.objects.create(g_e=self.g_e, log='Error al cargar la actividad %s' % p.x_actividad)
                actividad = None
            SesionExtra.objects.get_or_create(sesion=sesion, grupo=grupo, dependencia=dependencia, materia=materia,
                                              actividad=actividad)
            sesiones.append(sesion)
        return sesiones

    ########################################################################
    ############ Estructura PO:
    @property
    def estructura_po(self):
        tipo_centro = self.ronda_centro.entidad.entidadextra.tipo_centro
        try:
            estructura = TC[tipo_centro]
        except:
            LogCarga.objects.create(g_e=self.g_e, log='No existe la estructura de: %s' % tipo_centro)
            estructura = list(TC.keys())[0] # Por defecto tomar la primera key del diccionario
        return estructura

    @property  # Anchura en porcentaje de cada parte de la tabla:
    def anchura_cols(self):
        departamentos_docentes = 25
        horas_calculadas = 8
        apartados = 100 - departamentos_docentes - horas_calculadas
        return (departamentos_docentes, apartados, horas_calculadas)

    ########################################################################
    ############ Cálculos para cada docente:

    def carga_pdocente(self, gex):
        grexc = self.grupoexcluido_set.all().values_list('grupo__id', flat=True)
        LogCarga.objects.create(g_e=gex, log=grexc.count())
        sextras = SesionExtra.objects.filter(sesion__horario=self.horario, sesion__g_e=gex)
        LogCarga.objects.create(g_e=gex, log=sextras.count())
        sextras = sextras.filter(~Q(grupo__id__in=grexc))
        LogCarga.objects.create(g_e=gex, log=sextras.count())
        pd, c = PDocente.objects.get_or_create(po=self, g_e=gex)
        for apartado in self.estructura_po:
            for nombre_columna, contenido_columna in self.estructura_po[apartado].items():
                pdc, c = PDocenteCol.objects.get_or_create(pd=pd, codecol=contenido_columna['codecol'])
                pdc.nombre = nombre_columna
                pdc.periodos = sextras.filter(contenido_columna['q']).values_list('sesion',
                                                                                  flat=True).distinct().count()
                pdc.save()

    def carga_pdocentes(self):
        cargo_docente = Cargo.objects.get(entidad=self.ronda_centro.entidad, clave_cargo='g_docente')
        docentes = Gauser_extra.objects.filter(cargos__in=[cargo_docente])
        for docente in docentes:
            self.carga_pdocente(docente)



    def usar_unidad(self, unidad, usar):
        for pxls in self.plantillaxls_set.filter(unidad=unidad):
            pxls.usar = usar
            pxls.save()
        return True

    def carga_plantilla_xls(self):
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga dependencias")
        self.carga_dependencias()
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga etapas")
        self.carga_etapas()
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga cursos")
        self.carga_cursos()
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga grupos")
        self.carga_grupos()
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga materias")
        self.carga_materias()
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga departamentos")
        self.carga_departamentos()
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga puestos")
        self.carga_puestos()
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga actividades")
        self.carga_actividades()
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga docentes")
        self.carga_docentes()
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga sesiones docentes")
        self.carga_sesiones_docentes()
        LogCarga.objects.create(g_e=self.g_e, log="Inicio carga pdocentes")
        self.carga_pdocentes()
        LogCarga.objects.create(g_e=self.g_e, log="Finalizada la carga de la plantilla")
        return True


class PlantillaXLS(models.Model):
    ETAPAS = (('ba', 'Infantil'), ('ca', 'Primaria'), ('da', 'Secundaria'), ('ea', 'FP Básica'), ('fa', 'Bachillerato'),
              ('ga', 'FP Grado Medio'), ('ha', 'FP Grado Superior'), ('ia', 'Enseñanzas Iniciales de Personas Adultas'),
              ('ja', 'Educación Secundaria de Personas Adultas'),
              ('ka', 'Educación Secundaria de Personas Adultas a Distancia Semipresencial'),
              ('la', 'Educación Secundaria de Personas Adultas a Distancia'), ('ma', 'Educación para Personas Adultas'),
              ('na', 'Preparación Pruebas de Acceso a CCFF'), ('za', 'Etapa no identificada'))
    po = models.ForeignKey(PlantillaOrganica, on_delete=models.CASCADE, blank=True, null=True)
    year = models.CharField('Año', max_length=15, blank=True, null=True)
    centro = models.CharField('Nombre del centro', max_length=110, blank=True, null=True)
    docente = models.CharField('Nombre del docente', max_length=115, blank=True, null=True)
    x_docente = models.CharField('Código del docente en Racima', max_length=12, blank=True, null=True)
    dni = models.CharField('DNI del docente', max_length=11, blank=True, null=True)
    email = models.CharField('email del docente', max_length=150, blank=True, null=True)
    puesto = models.CharField('Puesto del docente', max_length=150, blank=True, null=True)
    x_puesto = models.CharField('Código del puesto del docente', max_length=11, blank=True, null=True)

    etapa_escolar = models.CharField('Etapa escolar', max_length=150, blank=True, null=True)
    x_etapa_escolar = models.CharField('Código de la etapa escolar', max_length=11, blank=True, null=True)

    departamento = models.CharField('Nombre del departamento', max_length=116, blank=True, null=True)
    x_departamento = models.CharField('Código del departamento en Racima', max_length=10, blank=True, null=True)

    fecha_inicio = models.CharField('Fecha inicio contrato profesor', max_length=15, blank=True, null=True)
    fecha_fin = models.CharField('Fecha fin contrato profesor', max_length=15, blank=True, null=True)

    x_sesion = models.CharField('Código de la sesión', max_length=15, blank=True, null=True)
    dia = models.CharField('Día de la semana expresado en número', max_length=3, blank=True, null=True)
    hora_inicio = models.CharField('Hora inicio periodo en minutos', max_length=15, blank=True, null=True)
    inicio = models.IntegerField('Hora inicio periodo en minutos', default=0)
    hora_fin = models.CharField('Hora fin periodo en minutos', max_length=15, blank=True, null=True)
    fin = models.IntegerField('Hora inicio periodo en minutos', default=0)
    hora_inicio_cadena = models.CharField('Hora inicio periodo en formato H:i', max_length=8, blank=True, null=True)
    hora_fin_cadena = models.CharField('Hora fin periodo en formato H:i', max_length=8, blank=True, null=True)

    actividad = models.CharField('Nombre de la actividad', max_length=117, blank=True, null=True)
    x_actividad = models.CharField('Código de la actividad en Racima', max_length=20, blank=True, null=True)
    l_requnidad = models.CharField('¿La actividad requiere unidad/grupo?', max_length=2, blank=True, null=True)
    docencia = models.CharField('¿Es hora de docencia?', max_length=2, blank=True, null=True)

    minutos = models.CharField('Duración del periodo en minutos', max_length=15, blank=True, null=True)

    x_dependencia = models.CharField('Código de la dependencia en Racima', max_length=10, blank=True, null=True)
    c_coddep = models.CharField('Nombre corto de la dependencia', max_length=30, blank=True, null=True)
    x_dependencia2 = models.CharField('Código de la dependencia2 en Racima', max_length=10, blank=True, null=True)
    c_coddep2 = models.CharField('Nombre corto de la dependencia2', max_length=30, blank=True, null=True)

    unidad = models.CharField('Nombre del grupo', max_length=20, blank=True, null=True)
    x_unidad = models.CharField('Código del grupo en Racima', max_length=11, blank=True, null=True)
    materia = models.CharField('Nombre de la materia', max_length=118, blank=True, null=True)
    x_materiaomg = models.CharField('Código de la materia en Racima', max_length=11, blank=True, null=True)
    curso = models.CharField('Nombre largo del curso', max_length=119, blank=True, null=True)
    x_curso = models.CharField('Código del curso en Racima', max_length=120, blank=True, null=True)
    omc = models.CharField('Nombre corto del curso', max_length=20, blank=True, null=True)
    grupo_materias = models.CharField('Tipo de materia', max_length=50, blank=True, null=True)

    # etapa = models.CharField('Etapa', max_length=4, blank=True, null=True, choices=ETAPAS)

    horas_semana_min = models.CharField('Horas mínimas de la materia por semana', max_length=10, blank=True, null=True)
    horas_semana_max = models.CharField('Horas máximas de la materia por semana', max_length=10, blank=True, null=True)
    usar = models.BooleanField('¿Usar este grupo para la calcular la plantilla orgánica', default=True)

    class Meta:
        verbose_name_plural = 'Sesiones obtenidas del XLS (PlantillaXLS)'
        ordering = ['x_etapa_escolar', 'curso', 'unidad']


class PDocente(models.Model):
    LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7),
              (115, 129, 8), (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13),
              (205, 219, 14), (220, 234, 15), (235, 249, 16), (250, 264, 17), (265, 279, 18), (280, 294, 19))
    RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7),
             (124, 139, 8), (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13),
             (220, 235, 14), (236, 251, 15), (252, 267, 16), (268, 283, 17), (284, 299, 18), (300, 235, 19))
    po = models.ForeignKey(PlantillaOrganica, on_delete=models.CASCADE, blank=True, null=True)
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, blank=True, null=True)

    @property
    def horas_totales(self):
        return sum(self.pdocentecol_set.all().values_list('periodos', flat=True))


    def __str__(self):
        return '%s - %s' % (self.po, self.g_e)


class PDocenteCol(models.Model):
    pd = models.ForeignKey(PDocente, on_delete=models.CASCADE)
    codecol = models.IntegerField('Código de identificación de la columna', default=0)
    nombre = models.CharField('Nombre de la columna', max_length=50)
    periodos = models.IntegerField('Horas impartidas', default=0)

    def __str__(self):
        return '%s - %s - (%s)' % (self.pd, self.nombre, self.periodos)

class GrupoExcluido(models.Model):
    po = models.ForeignKey(PlantillaOrganica, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)

    class Meta:
        ordering = ['po', 'grupo']

    def __str__(self):
        return '%s - %s' % (self.po, self.grupo)


class LogCarga(models.Model):
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    log = models.TextField('Texto del log', default='')
    creado = models.DateTimeField("Fecha y hora del log", auto_now_add=True)

    def __str__(self):
        return '%s - %s - %s...' % (self.creado, self.g_e, self.log[:190])
