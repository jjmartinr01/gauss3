# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.db import models
from django.db.models import Q
from django.utils.timezone import now
from entidades.models import Subentidad, Entidad, Ronda, Cargo, Gauser_extra
from estudios.models import Materia, Curso
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


class PlantillaOrganica(models.Model):
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, blank=True, null=True)
    ronda_centro = models.ForeignKey(Ronda, on_delete=models.CASCADE, blank=True, null=True)
    creado = models.DateTimeField("Fecha y hora de encolar el mensaje", auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Plantillas orgánicas'

    def create_curso(self, pxls):
        try:
            curso, c = Curso.objects.get_or_create(clave_ex=pxls.x_curso, ronda=self.ronda_centro)
            if c:
                curso.nombre = pxls.curso
                curso.observaciones = 'Creado el %s por %s' % (now(), self.g_e)
                curso.etapa = pxls.etapa
                curso.nombre_especifico = pxls.omc
                curso.save()
        except:
            cursos = Curso.objects.filter(clave_ex=pxls.x_curso, ronda=self.ronda_centro)
            curso = cursos[0]
            cursos.exclude(pk__in=[curso.pk]).delete()
            curso.observaciones = 'Borrado de duplicados el %s por %s' % (now(), self.g_e)
            curso.etapa = pxls.etapa
            curso.nombre_especifico = pxls.omc
            curso.save()
        return curso

    def create_cursos(self):
        for pxls in self.plantillaxls_set.all():
            self.create_curso(pxls)
        return True

    def create_materia(self, pxls):
        curso = self.create_curso(pxls)
        try:
            materia, c = Materia.objects.get_or_create(clave_ex=pxls.x_materiaomg, curso=curso)
            if c:
                nombre, dash, abreviatura = pxls.materia.rpartition('-')
                horas, sc, minutos = pxls.horas_semana_min.rpartition(':')
                materia.nombre = nombre.strip()
                materia.abreviatura = abreviatura.strip()
                materia.observaciones = 'Creada el %s por %s' % (now(), self.g_e)
                materia.horas = int(horas)
                materia.save()
        except:
            materias = Materia.objects.filter(clave_ex=pxls.x_materiaomg, curso=curso)
            materia = materias[0]
            materias.exclude(pk__in=[materia.pk]).delete()
            nombre, dash, abreviatura = pxls.materia.rpartition('-')
            horas, sc, minutos = pxls.horas_semana_min.rpartition(':')
            materia.nombre = nombre.strip()
            materia.abreviatura = abreviatura.strip()
            materia.observaciones += '<br>Borrado de duplicados el %s por %s' % (now(), self.g_e)
            materia.horas = int(horas)
            materia.save()
        return materia

    def create_materias(self):
        for pxls in self.plantillaxls_set.all():
            self.create_materia(pxls)

    @property
    def cursos(self):
        curs = {}
        for pxls in self.plantillaxls_set.all():
            if not pxls.curso in curs:
                if pxls.curso:
                    curs[pxls.curso] = [(pxls.unidad, pxls.usar, pxls.x_unidad)]
            else:
                if not (pxls.unidad, pxls.usar, pxls.x_unidad) in curs[pxls.curso]:
                    curs[pxls.curso].append((pxls.unidad, pxls.usar, pxls.x_unidad))
        return curs

    @property
    def unidades(self):
        grupos = []
        for pxls in self.plantillaxls_set.all():
            if not pxls.unidad in grupos:
                grupos.append((pxls.unidad, pxls.usar))
        return grupos

    @property
    def unidades_sin_usar(self):
        grupos = []
        for pxls in self.plantillaxls_set.all():
            if not pxls.unidad in grupos and not pxls.usar:
                grupos.append(pxls.unidad)
        return grupos

    @property
    def unidades_usadas(self):
        grupos = []
        for pxls in self.plantillaxls_set.all():
            if not pxls.unidad in grupos and pxls.usar:
                grupos.append(pxls.unidad)
        return grupos

    @property
    def departamentos(self):
        deps = []
        for pxls in self.plantillaxls_set.all():
            if not pxls.departamento in deps:
                deps.append(pxls.departamento)
        return deps

    def calcula_pds(self):
        orden = {'Griego': 2, 'Orientación': 20, 'Tecnología': 14, 'Matemáticas': 6, 'Educación Física': 13,
                 'Filosofía': 1, 'Geografía e Historia': 5, 'Inglés': 11, 'Formación y Orientación Laboral': 17,
                 'Lengua Castellana y Literatura': 4, 'Ciencias Naturales': 8, 'Latín': 3, 'Artes Plásticas': 9,
                 'Física y Química': 7, 'Música': 12, 'Economía': 15, 'Cultura Clásica': 16, 'Francés': 10}
        psXLS = self.plantillaxls_set.all()
        for departamento in self.departamentos:
            if departamento:
                pd, c = PlantillaDepartamento.objects.get_or_create(po=self, departamento=departamento)
                psXLS_departamento = psXLS.filter(departamento=departamento, usar=True)
                troncales = (Q(grupo_materias__icontains='tronca') | Q(grupo_materias__icontains='extranj') | Q(
                    grupo_materias__icontains='obligator')) & Q(x_actividad='1')
                libreconf = Q(grupo_materias__icontains='libre conf') & Q(x_actividad='1')
                espec = Q(grupo_materias__icontains='espec') & Q(x_actividad='1')
                posibles_desdobles = Q(x_actividad='539') | Q(x_actividad='400')
                pd.troneso = psXLS_departamento.filter(Q(etapa='da') & troncales).count()
                pd.espeeso = psXLS_departamento.filter(Q(etapa='da') & espec).count()
                pd.libreso = psXLS_departamento.filter(Q(etapa='da') & libreconf).count()
                pd.tronbac = psXLS_departamento.filter(Q(etapa='fa') & troncales).count()
                pd.espebac = psXLS_departamento.filter(Q(etapa='fa') & espec).count()
                pd.gm = psXLS_departamento.filter(etapa='ga').count()
                pd.gs = psXLS_departamento.filter(etapa='ha').count()
                pd.fpb = psXLS_departamento.filter(etapa='ea').count()
                pd.desdobeso = psXLS_departamento.filter(Q(etapa='da') & posibles_desdobles).count()
                pd.desdobbac = psXLS_departamento.filter(Q(etapa='fa') & posibles_desdobles).count()
                pd.mayor55 = psXLS_departamento.filter(x_actividad='176').count()
                if departamento in orden:
                    pd.orden = orden[departamento]
                pd.save()

    def usar_unidad(self, unidad, usar):
        for pxls in self.plantillaxls_set.filter(unidad=unidad):
            pxls.usar = usar
            pxls.save()
        return True


class PlantillaXLS(models.Model):
    ETAPAS = (('ba', 'Infantil'), ('ca', 'Primaria'), ('da', 'Secundaria'), ('ea', 'FP Básica'), ('fa', 'Bachillerato'),
              ('ga', 'FP Grado Medio'), ('ha', 'FP Grado Superior'), ('za', 'Etapa no identificada'))
    po = models.ForeignKey(PlantillaOrganica, on_delete=models.CASCADE, blank=True, null=True)
    year = models.CharField('Año', max_length=15, blank=True, null=True)
    centro = models.CharField('Nombre del centro', max_length=100, blank=True, null=True)
    docente = models.CharField('Nombre del docente', max_length=100, blank=True, null=True)
    x_docente = models.CharField('Código del docente en Racima', max_length=11, blank=True, null=True)
    departamento = models.CharField('Nombre del departamento', max_length=100, blank=True, null=True)
    x_departamento = models.CharField('Código del departamento en Racima', max_length=10, blank=True, null=True)
    fecha_inicio = models.CharField('Fecha inicio contrato profesor', max_length=15, blank=True, null=True)
    fecha_fin = models.CharField('Fecha fin contrato profesor', max_length=15, blank=True, null=True)
    dia = models.CharField('Día de la semana expresado en número', max_length=3, blank=True, null=True)
    hora_inicio = models.CharField('Hora inicio periodo en minutos', max_length=15, blank=True, null=True)
    hora_fin = models.CharField('Hora fin periodo en minutos', max_length=15, blank=True, null=True)
    hora_inicio_cadena = models.CharField('Hora inicio periodo en formato H:i', max_length=8, blank=True, null=True)
    hora_fin_cadena = models.CharField('Hora fin periodo en formato H:i', max_length=8, blank=True, null=True)
    actividad = models.CharField('Nombre de la actividad', max_length=100, blank=True, null=True)
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
    materia = models.CharField('Nombre de la materia', max_length=100, blank=True, null=True)
    x_materiaomg = models.CharField('Código de la materia en Racima', max_length=11, blank=True, null=True)
    curso = models.CharField('Nombre largo del curso', max_length=100, blank=True, null=True)
    x_curso = models.CharField('Código del curso en Racima', max_length=100, blank=True, null=True)
    omc = models.CharField('Nombre corto del curso', max_length=20, blank=True, null=True)
    grupo_materias = models.CharField('Tipo de materia', max_length=50, blank=True, null=True)
    etapa = models.CharField('Etapa', max_length=4, blank=True, null=True, choices=ETAPAS)
    horas_semana_min = models.CharField('Horas mínimas de la materia por semana', max_length=10, blank=True, null=True)
    horas_semana_max = models.CharField('Horas máximas de la materia por semana', max_length=10, blank=True, null=True)
    usar = models.BooleanField('¿Usar este grupo para la calcular la plantilla orgánica', default=True)

    class Meta:
        verbose_name_plural = 'Sesiones obtenidas del XLS (PlantillaXLS)'
        ordering = ['etapa', 'curso']

class PlantillaDepartamento(models.Model):
    LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7),
              (115, 129, 8), (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13),
              (205, 219, 14))
    RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7),
             (124, 139, 8), (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13),
             (220, 235, 14))
    po = models.ForeignKey(PlantillaOrganica, on_delete=models.CASCADE, blank=True, null=True)
    departamento = models.CharField('Departamento', max_length=100, blank=True, null=True)
    x_departamento = models.CharField('Código en Racima del departamento', max_length=10, blank=True, null=True)
    troneso = models.IntegerField('Horas de Troncales de ESO', blank=True, default=0)
    espeeso = models.IntegerField('Horas de Específicas de ESO', default=0)
    libreso = models.IntegerField('Horas de Libre Configuración Autonómica de ESO', default=0)
    tronbac = models.IntegerField('Horas de Troncales de Bachillerato', default=0)
    espebac = models.IntegerField('Horas de Específicas de Bachillerato', default=0)
    gm = models.IntegerField('Horas de Grado Medio', default=0)
    gs = models.IntegerField('Horas de Específicas de Bachillerato', default=0)
    fpb = models.IntegerField('Horas de Específicas de Bachillerato', default=0)
    desdobeso = models.IntegerField('Desdobles autorizados ESO', default=0)
    desdobbac = models.IntegerField('Desdobles autorizados Bachillerato', default=0)
    jefatura = models.IntegerField('Horas de jefatura de departamento', default=3)
    mayor55 = models.IntegerField('Desdobles autorizados Bachillerato', default=0)
    orden = models.IntegerField('Desdobles autorizados Bachillerato', default=100)
    creado = models.DateTimeField("Fecha y hora de encolar el mensaje", auto_now_add=True)
    modificado = models.DateTimeField("Fecha y hora en la que se envió efectivamente el correo", auto_now=True)

    class Meta:
        verbose_name_plural = 'Plantilla por departamentos (PlantillaDepartamento)'
        ordering = ['orden']

    @property
    def horas_basicas(self):
        return self.troneso + self.espeeso + self.libreso + self.tronbac + self.espebac + self.gm + self.gs + self.fpb + self.desdobeso + self.desdobbac + self.jefatura

    @property
    def plantilla_organica(self):
        po = 0
        horas_basicas = self.horas_basicas
        condicion = self.departamento == 'Música' or 'astellana' in self.departamento or 'Matem' in self.departamento
        plantillas = self.LCL_MU if condicion else self.RESTO
        for plantilla in plantillas:
            if horas_basicas >= plantilla[0] and horas_basicas <= plantilla[1]:
                po = plantilla[2]
        return po

# class PlantillaDepartamentoEspecialidad(models.Model):
#     pd = models.ForeignKey(PlantillaDepartamento, blank=True, null=True, on_delete=models.CASCADE)
#     gmpt = models.IntegerField('Horas de Grado Medio profesor Técnico', blank=True, null=True)
#     gmse = models.IntegerField('Horas de Grado Medio profesor de Secundaria', blank=True, null=True)
#     gspt = models.IntegerField('Horas de Grado Medio profesor Técnico', blank=True, null=True)
#     gsse = models.IntegerField('Horas de Grado Medio profesor de Secundaria', blank=True, null=True)
