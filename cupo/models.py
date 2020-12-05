# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.db import models
from django.db.models import Q
from django.utils.timezone import now
from entidades.models import Subentidad, Entidad, Ronda, Cargo, Gauser_extra, Dependencia
from estudios.models import Materia, Curso, Grupo
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

    def crea_sesiones_docentes(self):
        campos_sd = ['po', 'docente', 'x_docente', 'departamento', 'x_departamento', 'dia', 'hora_inicio', 'hora_fin',
                     'hora_inicio_cadena', 'hora_fin_cadena', 'actividad', 'x_actividad', 'l_requnidad', 'docencia',
                     'minutos', 'x_dependencia', 'c_coddep', 'x_dependencia2', 'c_coddep2']
        campos_usd = ['unidad', 'x_unidad', 'materia', 'x_materiaomg', 'curso', 'x_curso', 'omc', 'grupo_materias',
                      'etapa', 'horas_semana_min', 'horas_semana_max']
        psxls = self.plantillaxls_set.all()
        for p in psxls:
            self.create_dependencia(p)
            self.create_curso(p)
            materia = self.create_materia(p)
            grupo = self.create_grupo(p)
            sd, c = SesionDocente.objects.get_or_create(po=self, x_docente=p.x_docente, dia=p.dia,
                                                        hora_inicio=p.hora_inicio)
            if c:
                for c_sd in campos_sd:
                    valor = getattr(p, c_sd)
                    setattr(sd, c_sd, valor)
                sd.save()
                usd = UnidadSesionDocente.objects.create(sd=sd)
                for c_usd in campos_usd:
                    valor = getattr(p, c_usd)
                    setattr(usd, c_usd, valor)
                usd.save()
            else:
                usd, c = UnidadSesionDocente.objects.get_or_create(sd=sd, x_unidad=p.x_unidad)
                if c:
                    for c_usd in campos_usd:
                        valor = getattr(p, c_usd)
                        setattr(usd, c_usd, valor)
                    usd.save()

    def create_dependencia(self, pxls):
        if pxls.x_dependencia == '-1':
            return Dependencia.objects.none()
        else:
            try:
                dependencia, c = Dependencia.objects.get_or_create(clave_ex=pxls.x_dependencia,
                                                                   entidad=self.ronda_centro.entidad)
                if c:
                    dependencia.nombre = pxls.c_coddep
                    dependencia.abrev = pxls.c_coddep
                    dependencia.observaciones = 'Creada el %s por %s' % (now(), self.g_e)
                    dependencia.es_aula = True
                    dependencia.save()
            except:
                dependencias = Dependencia.objects.filter(clave_ex=pxls.x_dependencia,
                                                          entidad=self.ronda_centro.entidad)
                dependencia = dependencias[0]
                dependencias.exclude(pk__in=[dependencia.pk]).delete()
                dependencia.nombre = pxls.c_coddep
                dependencia.abrev = pxls.c_coddep
                dependencia.observaciones = 'Creada el %s por %s' % (now(), self.g_e)
                dependencia.es_aula = True
                dependencia.save()
            return dependencia

    def create_dependencias(self):
        for pxls in self.plantillaxls_set.filter(~Q(x_dependencia='-1')):
            self.create_dependencia(pxls)

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
                materia.grupo_materias = pxls.grupo_materias
                materia.horas_semana_min = pxls.horas_semana_min
                materia.horas_semana_max = pxls.horas_semana_max
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
            materia.grupo_materias = pxls.grupo_materias
            materia.horas_semana_min = pxls.horas_semana_min
            materia.horas_semana_max = pxls.horas_semana_max
            materia.save()
        return materia

    def create_materias(self):
        for pxls in self.plantillaxls_set.all():
            self.create_materia(pxls)

    def create_grupo(self, pxls):
        try:
            grupo, c = Grupo.objects.get_or_create(clave_ex=pxls.x_unidad, ronda=self.ronda_centro)
            curso = self.create_curso(pxls)
            grupo.cursos.add(curso)
            if c:
                grupo.nombre = pxls.unidad
                grupo.observaciones = 'Creado el %s por %s' % (now(), self.g_e)
                grupo.aula = self.create_dependencia(pxls)
                grupo.save()
        except:
            grupos = Grupo.objects.filter(clave_ex=pxls.x_unidad, ronda=self.ronda_centro)
            grupo = grupos[0]
            grupos.exclude(pk__in=[grupo.pk]).delete()
            grupo.nombre = pxls.unidad
            grupo.observaciones = 'Creado el %s por %s' % (now(), self.g_e)
            grupo.aula = self.create_dependencia(pxls)
            curso = self.create_curso(pxls)
            grupo.cursos.add(curso)
            grupo.save()
        return grupo

    def create_grupos(self):
        for pxls in self.plantillaxls_set.all():
            self.create_grupo(pxls)

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
        orden = {'Griego': 2, 'Orientación': 20, 'Tecnología': 14, 'Matemáticas': 6, 'Educación Física': 13,
                 'Filosofía': 1, 'Geografía e Historia': 5, 'Inglés': 11, 'Formación y Orientación Laboral': 17,
                 'Lengua Castellana y Literatura': 4, 'Ciencias Naturales': 8, 'Latín': 3, 'Artes Plásticas': 9,
                 'Física y Química': 7, 'Música': 12, 'Economía': 15, 'Cultura Clásica': 16, 'Francés': 10}
        deps = []
        for pxls in self.plantillaxls_set.all():
            o = orden[pxls.departamento] if pxls.departamento in orden else 10000
            nuevo_dep = (o, pxls.x_departamento, pxls.departamento)
            if not nuevo_dep in deps:
                deps.append(nuevo_dep)
        return sorted(deps, key=lambda x: x[0])

    @property
    def docentes(self):
        return self.plantillaxls_set.all().values_list('departamento', 'x_departamento', 'docente',
                                                       'x_docente').distinct()

    @property
    def get_tramos_centro(self):
        return self.plantillaxls_set.all().order_by('dia', 'hora_inicio').values('dia', 'hora_inicio', 'hora_fin',
                                                                                 'hora_inicio_cadena',
                                                                                 'hora_fin_cadena').distinct()

    @property
    def get_tramos_docencia_centro(self):
        return self.plantillaxls_set.filter(x_actividad='1').order_by('dia', 'hora_inicio').values('dia', 'hora_inicio',
                                                                                                   'hora_fin',
                                                                                                   'hora_inicio_cadena',
                                                                                                   'hora_fin_cadena').distinct()

    def get_sesiones_docente(self, x_docente):
        return self.sesiondocente_set.filter(x_docente=x_docente).order_by('dia', 'hora_inicio')

    def get_sesiones_docencia_docente(self, x_docente):
        return self.sesiondocente_set.filter(x_docente=x_docente, x_actividad='1').order_by('dia', 'hora_inicio')

    # def get_periodos_docencia(self, x_docente):
    #     sds = self.sesiondocente_set.filter(x_docente=x_docente, x_actividad='1')
    #     for sd in sds:
    #         pass

    def get_materias_docente(self, x_docente):
        sds = self.sesiondocente_set.filter(x_docente=x_docente)
        materias = []
        for sd in sds:
            if sd.materia not in materias:
                materias.append(sd.materia)
        return materias

    def calcula_materias_docente(self, psxls):
        psxls_materias = psxls.filter(x_actividad='1').values_list('materia', 'omc', 'horas_semana_min', 'dia',
                                                                   'hora_fin')
        m = psxls_materias[0]
        try:
            materias = [[m[0].split('-')[1].strip(), m[1], int(m[2].split(':')[0]), m[3], m[4], 0]]
        except:
            materias = [[m[0], m[1], 0, m[3], m[4], 0]]
        for m in psxls_materias:
            try:
                m_trans = [m[0].split('-')[1].strip(), m[1], int(m[2].split(':')[0]), m[3], m[4]]
            except:
                m_trans = [m[0], m[1], 0, m[3], m[4]]
            incluida = False
            for materia in materias:
                if m_trans[3] == materia[3] and m_trans[4] == materia[4]:
                    incluida = True
                    if m_trans[1] not in materia[1]:
                        materia[1] = '%s/%s' % (materia[1], m_trans[1])
            if not incluida:
                materias.append(m_trans)
        sin_repetir = []
        todas = []
        for materia in materias:
            m = (materia[0], materia[1], materia[2])
            todas.append(m)
            if m not in sin_repetir:
                sin_repetir.append(m)
        analizadas = []
        for d in sin_repetir:
            if d[2] != 0:
                for i in range(int(len([m for m in todas if m == d]) / d[2])):
                    analizadas.append(d)
        return analizadas

    def calcula_sesiones_docente(self, psxls):
        # '222074 -> 1º E.S.O. (ADAPTACIÓN CURRICULAR EN GRUPO)'
        # '222075 -> 2º E.S.O. (ADAPTACIÓN CURRICULAR EN GRUPO)'
        # '101324 -> 2º E.S.O.'
        # '101325 -> 3º E.S.O.'
        sesiones = {}
        sesiones['pacg'] = psxls.filter(x_curso__in=['222074', '222075'], x_actividad='1')
        sesiones['pmar1'] = psxls.filter(materia__icontains='mbito', x_curso='101324', x_actividad='1')
        sesiones['pmar2'] = psxls.filter(materia__icontains='mbito', x_curso='101325', x_actividad='1')
        sesiones['refuerzo1'] = psxls.filter(materia__icontains='mbito', x_curso='170506', x_actividad='1')
        troncales = (Q(grupo_materias__icontains='tronca') | Q(grupo_materias__icontains='extranj') | Q(
            grupo_materias__icontains='obligator')) & Q(x_actividad='1')
        troneso = troncales & Q(etapa='da') & ~Q(x_curso__in=['222074', '222075']) & ~Q(materia__icontains='mbito')
        espads1 = Q(etapa='ka') & Q(x_actividad='1') & (Q(x_curso='222080') | Q(x_curso='222081'))
        espads2 = Q(etapa='ka') & Q(x_actividad='1') & (Q(x_curso='222082') | Q(x_curso='222083'))
        espa1 = Q(etapa='ja') & Q(x_actividad='1') & (Q(x_curso='222076') | Q(x_curso='222077'))
        espa2 = Q(etapa='ja') & Q(x_actividad='1') & (Q(x_curso='222078') | Q(x_curso='222079'))
        epan2 = Q(etapa='ma') & Q(x_actividad='1') & Q(x_curso='222071')
        # sesiones['iniciales'] = psxls.filter(etapa='ia')
        sesiones['iniciales1'] = psxls.filter(etapa='ia', x_actividad='1', x_curso='121469')
        sesiones['iniciales2'] = psxls.filter(etapa='ia', x_actividad='1', x_curso='121470')
        sesiones['espa1'] = psxls.filter(espa1)
        sesiones['espa2'] = psxls.filter(espa2)
        sesiones['espads1'] = psxls.filter(espads1)
        sesiones['espads2'] = psxls.filter(espads2)
        # sesiones['espad'] = psxls.filter(etapa='la')
        sesiones['epaofi'] = psxls.filter(etapa='ma', curso__icontains='ofim')
        sesiones['epainf'] = psxls.filter(etapa='ma', curso__icontains='inform')
        sesiones['epaing'] = psxls.filter(etapa='ma', curso__icontains='ingl')
        sesiones['epamec'] = psxls.filter(etapa='ma', curso__icontains='mecanog')
        sesiones['epan2'] = psxls.filter(epan2)
        sesiones['epainm'] = psxls.filter(etapa='ma', curso__icontains='nmigrantes')
        sesiones['epamay'] = psxls.filter(etapa='ma', curso__icontains='mayores de')
        sesiones['troneso'] = psxls.filter(troneso)
        sesiones['espeeso'] = psxls.filter(etapa='da', grupo_materias__icontains='espec', x_actividad='1')
        excluir = Q(x_curso__in=['222074', '222075']) | Q(materia__icontains='mbito')
        sesiones['libreso'] = psxls.filter(etapa='da', grupo_materias__icontains='libre conf',
                                           x_actividad='1').exclude(excluir)
        sesiones['tronbac'] = psxls.filter(Q(etapa='fa') & troncales)
        sesiones['espebac'] = psxls.filter(etapa='fa', grupo_materias__icontains='espec', x_actividad='1')
        sesiones['gm'] = psxls.filter(etapa='ga', x_actividad='1')
        sesiones['gs'] = psxls.filter(etapa='ha', x_actividad='1')
        sesiones['fpb'] = psxls.filter(etapa='ea', x_actividad='1')
        posibles_desdobles = (Q(x_actividad='539') | Q(x_actividad='400')) & Q(x_actividad='1') & Q(x_actividad='522')
        sesiones['desdobeso'] = psxls.filter(Q(etapa='da') & posibles_desdobles)
        sesiones['desdobbac'] = psxls.filter(Q(etapa='fa') & posibles_desdobles)
        sesiones['mayor55'] = psxls.filter(x_actividad='176')
        sesiones['cppaccffgs'] = psxls.filter(x_curso='222073', x_actividad='1')
        sesiones['tutorias'] = psxls.filter(Q(x_actividad='519') | Q(x_actividad='2') | Q(x_actividad='376'))
        sesiones['jefatura'] = psxls.filter(x_actividad='547')
        sesiones['relve'] = psxls.filter(x_actividad='1', grupo_materias__icontains='Rel. y Aten.')
        return sesiones

    def calcula_horas_docente(self, psxls):
        sesiones = self.calcula_sesiones_docente(psxls)
        horas = {}
        for key, queryset in sesiones.items():
            horas[key] = queryset.values_list('x_dependencia', 'dia', 'hora_inicio', 'hora_fin').distinct().count()
        return horas

    def calcula_pdocente(self, docente):
        orden = {'Griego': 2, 'Orientación': 20, 'Tecnología': 14, 'Matemáticas': 6, 'Educación Física': 13,
                 'Filosofía': 1, 'Geografía e Historia': 5, 'Inglés': 11, 'Formación y Orientación Laboral': 17,
                 'Lengua Castellana y Literatura': 4, 'Ciencias Naturales': 8, 'Latín': 3, 'Artes Plásticas': 9,
                 'Física y Química': 7, 'Música': 12, 'Economía': 15, 'Cultura Clásica': 16, 'Francés': 10}

        pd, c = PlantillaDocente.objects.get_or_create(po=self, x_docente=docente[3])
        if c:
            pd.departamento = docente[0]
            pd.x_departamento = docente[1]
            pd.docente = docente[2]
            pd.x_docente = docente[3]
        psXLS_docente = self.plantillaxls_set.filter(x_docente=docente[3], usar=True)
        horas = self.calcula_horas_docente(psXLS_docente)
        for key, num in horas.items():
            setattr(pd, key, num)
        if docente[0] in orden:
            pd.orden = orden[docente[0]]
        pd.save()
        return pd

    def calcula_pdocentes(self):
        for docente in self.docentes:
            self.calcula_pdocente(docente)

    def usar_unidad(self, unidad, usar):
        for pxls in self.plantillaxls_set.filter(unidad=unidad):
            pxls.usar = usar
            pxls.save()
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
    x_docente = models.CharField('Código del docente en Racima', max_length=11, blank=True, null=True)
    departamento = models.CharField('Nombre del departamento', max_length=116, blank=True, null=True)
    x_departamento = models.CharField('Código del departamento en Racima', max_length=10, blank=True, null=True)
    fecha_inicio = models.CharField('Fecha inicio contrato profesor', max_length=15, blank=True, null=True)
    fecha_fin = models.CharField('Fecha fin contrato profesor', max_length=15, blank=True, null=True)
    dia = models.CharField('Día de la semana expresado en número', max_length=3, blank=True, null=True)
    hora_inicio = models.CharField('Hora inicio periodo en minutos', max_length=15, blank=True, null=True)
    hora_fin = models.CharField('Hora fin periodo en minutos', max_length=15, blank=True, null=True)
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
    etapa = models.CharField('Etapa', max_length=4, blank=True, null=True, choices=ETAPAS)
    horas_semana_min = models.CharField('Horas mínimas de la materia por semana', max_length=10, blank=True, null=True)
    horas_semana_max = models.CharField('Horas máximas de la materia por semana', max_length=10, blank=True, null=True)
    usar = models.BooleanField('¿Usar este grupo para la calcular la plantilla orgánica', default=True)

    class Meta:
        verbose_name_plural = 'Sesiones obtenidas del XLS (PlantillaXLS)'
        ordering = ['etapa', 'curso', 'unidad']


class PlantillaDepartamento(models.Model):
    LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7),
              (115, 129, 8), (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13),
              (205, 219, 14), (220, 234, 15), (235, 249, 16), (250, 264, 17), (265, 279, 18), (280, 294, 19))
    RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7),
             (124, 139, 8), (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13),
             (220, 235, 14), (236, 251, 15), (252, 267, 16), (268, 283, 17), (284, 299, 18), (300, 235, 19))
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
    cppaccffgs = models.IntegerField('Horas curso preparación pruebas de acceso a CCFF', default=0)
    tutorias = models.IntegerField('Horas dedicadas a tutorías y FCTs', default=0)
    refuerzo1 = models.IntegerField('Horas de 1º de Refuerzo Curriculas', default=0)
    pacg = models.IntegerField('Horas de PACG', default=0)
    pmar1 = models.IntegerField('Horas de 1º de PMAR (2º ESO)', default=0)
    pmar2 = models.IntegerField('Horas de 2º de PMAR (3º ESO)', default=0)
    iniciales = models.IntegerField('Horas de Enseñanzas Iniciales', default=0)
    espa = models.IntegerField('Horas de Educación Secundaria para adultos', default=0)
    espads = models.IntegerField('Horas de Educación Secundaria para adultos a distancia semipresencial', default=0)
    espad = models.IntegerField('Horas de Educación Secundaria para adultos a distancia', default=0)
    epaofi = models.IntegerField('Horas de enseñanzas de adultos ofimática', default=0)
    epainf = models.IntegerField('Horas de enseñanzas de adultos informática', default=0)
    epaing = models.IntegerField('Horas de enseñanzas de adultos inglés', default=0)
    epamec = models.IntegerField('Horas de enseñanzas de adultos mecanografía', default=0)
    epan2 = models.IntegerField('Horas de preparación competencias N-2', default=0)
    epainm = models.IntegerField('Horas de alfabetización para inmigrantes', default=0)
    epamay = models.IntegerField('Horas de cursos de preparación para mayores de 18 y 25 años', default=0)
    orden = models.IntegerField('Orden de presentación', default=100)
    creado = models.DateTimeField("Fecha y hora de encolar el mensaje", auto_now_add=True)
    modificado = models.DateTimeField("Fecha y hora en la que se envió efectivamente el correo", auto_now=True)

    class Meta:
        verbose_name_plural = 'Plantilla por departamentos (PlantillaDepartamento)'
        ordering = ['orden']

    @property
    def horas_basicas(self):
        return self.troneso + self.espeeso + self.libreso + self.tronbac + self.espebac + self.gm + self.gs + self.fpb + self.desdobeso + self.desdobbac + self.jefatura

    @property
    def horas_totales(self):
        return self.horas_basicas + self.mayor55 + self.cppaccffgs + self.tutorias + self.refuerzo1 + self.pacg + self.pmar1 + self.pmar2

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


class PlantillaDocente(models.Model):
    LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7),
              (115, 129, 8), (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13),
              (205, 219, 14), (220, 234, 15), (235, 249, 16), (250, 264, 17), (265, 279, 18), (280, 294, 19))
    RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7),
             (124, 139, 8), (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13),
             (220, 235, 14), (236, 251, 15), (252, 267, 16), (268, 283, 17), (284, 299, 18), (300, 235, 19))
    po = models.ForeignKey(PlantillaOrganica, on_delete=models.CASCADE, blank=True, null=True)
    docente = models.CharField('Docente', max_length=100, blank=True, null=True)
    x_docente = models.CharField('Código en Racima del docente', max_length=10, blank=True, null=True)
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
    jefatura = models.IntegerField('Horas de jefatura de departamento', default=0)
    mayor55 = models.IntegerField('Desdobles autorizados Bachillerato', default=0)
    cppaccffgs = models.IntegerField('Horas curso preparación pruebas de acceso a CCFF', default=0)
    tutorias = models.IntegerField('Horas dedicadas a tutorías y FCTs', default=0)
    refuerzo1 = models.IntegerField('Horas de 1º de Refuerzo Curriculas', default=0)
    pacg = models.IntegerField('Horas de PACG', default=0)
    pmar1 = models.IntegerField('Horas de 1º de PMAR (2º ESO)', default=0)
    pmar2 = models.IntegerField('Horas de 2º de PMAR (3º ESO)', default=0)
    relve = models.IntegerField('Religión y Valores', default=0)
    iniciales = models.IntegerField('Horas de Enseñanzas Iniciales', default=0)
    iniciales1 = models.IntegerField('Horas de Enseñanzas Iniciales I', default=0)
    iniciales2 = models.IntegerField('Horas de Enseñanzas Iniciales II', default=0)
    espa = models.IntegerField('Horas de Educación Secundaria para adultos', default=0)
    espa1 = models.IntegerField('Horas de Educación Secundaria para adultos nivel I', default=0)
    espa2 = models.IntegerField('Horas de Educación Secundaria para adultos nivel II', default=0)
    espads = models.IntegerField('Horas de Educación Secundaria para adultos a distancia semipresencial', default=0)
    espads1 = models.IntegerField('Horas de Educ. Secund. para adultos a distancia semipresencial nivel I', default=0)
    espads2 = models.IntegerField('Horas de Educ. Secund. para adultos a distancia semipresencial nivel II', default=0)
    espad1 = models.IntegerField('Horas de Educación Secundaria para adultos a distancia nivel I', default=0)
    espad2 = models.IntegerField('Horas de Educación Secundaria para adultos a distancia nivel II', default=0)
    epaofi = models.IntegerField('Horas de enseñanzas de adultos ofimática', default=0)
    epainf = models.IntegerField('Horas de enseñanzas de adultos informática', default=0)
    epaing = models.IntegerField('Horas de enseñanzas de adultos inglés', default=0)
    epamec = models.IntegerField('Horas de enseñanzas de adultos mecanografía', default=0)
    epan2 = models.IntegerField('Horas de preparación competencias N-2', default=0)
    epainm = models.IntegerField('Horas de alfabetización para inmigrantes', default=0)
    epamay = models.IntegerField('Horas de cursos de preparación para mayores de 18 y 25 años', default=0)
    orden = models.IntegerField('Orden de presentación', default=100)
    creado = models.DateTimeField("Fecha y hora de encolar el mensaje", auto_now_add=True)
    modificado = models.DateTimeField("Fecha y hora en la que se envió efectivamente el correo", auto_now=True)

    @property
    def horas_basicas(self):
        hs1 = self.troneso + self.espeeso + self.libreso + self.tronbac + self.espebac + self.gm + self.gs + self.fpb + self.desdobeso + self.desdobbac + self.jefatura + self.relve
        hs2 = self.iniciales1 + self.iniciales2 + self.espa1 + self.espa2 + self.espads1 + self.espads2 + self.epaofi + self.epainf + self.epaing + self.epamec + self.epan2 + self.epainm + self.epamay
        return hs1 + hs2

    @property
    def horas_totales(self):
        hs1 = self.cppaccffgs + self.refuerzo1 + self.pacg + self.pmar1 + self.pmar2
        return self.horas_basicas + self.mayor55 + self.tutorias + hs1

    # @property
    # def plantilla_departamento(self):
    #     return self.po.plantilladepartamento_set.get(departamento=self.departamento)

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


class SesionDocente(models.Model):
    po = models.ForeignKey(PlantillaOrganica, on_delete=models.CASCADE, blank=True, null=True)
    docente = models.CharField('Nombre del docente', max_length=115, blank=True, null=True)
    x_docente = models.CharField('Código del docente en Racima', max_length=11, blank=True, null=True)
    departamento = models.CharField('Nombre del departamento', max_length=116, blank=True, null=True)
    x_departamento = models.CharField('Código del departamento en Racima', max_length=10, blank=True, null=True)
    dia = models.CharField('Día de la semana expresado en número', max_length=3, blank=True, null=True)
    hora_inicio = models.CharField('Hora inicio periodo en minutos', max_length=15, blank=True, null=True)
    hora_fin = models.CharField('Hora fin periodo en minutos', max_length=15, blank=True, null=True)
    hora_inicio_cadena = models.CharField('Hora inicio periodo en formato H:i', max_length=8, blank=True, null=True)
    hora_fin_cadena = models.CharField('Hora fin periodo en formato H:i', max_length=8, blank=True, null=True)
    actividad = models.CharField('Nombre de la actividad', max_length=117, blank=True, null=True)
    x_actividad = models.CharField('Código de la actividad en Racima', max_length=20, blank=True, null=True)
    l_requnidad = models.CharField('¿La actividad requiere unidad/grupo?', max_length=2, blank=True, null=True)
    docencia = models.CharField('¿Es hora de docencia?', max_length=2, blank=True, null=True)
    minutos = models.CharField('Duración del periodo en minutos', max_length=15, blank=True, null=True)
    dependencia = models.ForeignKey(Dependencia, blank=True, null=True, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, blank=True, null=True, on_delete=models.CASCADE)
    # x_dependencia = models.CharField('Código de la dependencia en Racima', max_length=10, blank=True, null=True)
    # c_coddep = models.CharField('Nombre corto de la dependencia', max_length=30, blank=True, null=True)
    # x_dependencia2 = models.CharField('Código de la dependencia2 en Racima', max_length=10, blank=True, null=True)
    # c_coddep2 = models.CharField('Nombre corto de la dependencia2', max_length=30, blank=True, null=True)
    usar = models.BooleanField('¿Usar este grupo para la calcular la plantilla orgánica', default=True)

    class Meta:
        verbose_name_plural = 'Sesiones de Docentes'
        ordering = ['po', 'x_actividad']

    @property
    def unidades(self):
        us = []
        if self.x_actividad == '1':
            for usd in self.unidadsesiondocente_set.all():
                if not usd.grupo in us:
                    us.append(usd.grupo)
        return us

    @property
    def s_unidades(self):
        us = [grupo.nombre for grupo in self.unidades]
        return '/'.join(us)

    def s_materia(self):  # String Materia
        if self.x_actividad == '1':
            m = []
            for usd in self.unidadsesiondocente_set.all():
                abv, horas = usd.materia.split('-')[1].strip(), usd.horas_semana_min.split(':')[0]
                m.append('%s %s %sh' % (abv, self.s_unidades, horas))
            return set(m)
        else:
            return set()


class UnidadSesionDocente(models.Model):
    ETAPAS = (('ba', 'Infantil'), ('ca', 'Primaria'), ('da', 'Secundaria'), ('ea', 'FP Básica'), ('fa', 'Bachillerato'),
              ('ga', 'FP Grado Medio'), ('ha', 'FP Grado Superior'), ('ia', 'Enseñanzas Iniciales de Personas Adultas'),
              ('ja', 'Educación Secundaria de Personas Adultas'),
              ('ka', 'Educación Secundaria de Personas Adultas a Distancia Semipresencial'),
              ('la', 'Educación Secundaria de Personas Adultas a Distancia'), ('ma', 'Educación para Personas Adultas'),
              ('na', 'Preparación Pruebas de Acceso a CCFF'), ('za', 'Etapa no identificada'))
    sd = models.ForeignKey(SesionDocente, on_delete=models.CASCADE, blank=True, null=True)
    grupo = models.ForeignKey(Grupo, blank=True, null=True, on_delete=models.CASCADE)
    # unidad = models.CharField('Nombre del grupo', max_length=20, blank=True, null=True)
    # x_unidad = models.CharField('Código del grupo en Racima', max_length=11, blank=True, null=True)
    # materia = models.CharField('Nombre de la materia', max_length=118, blank=True, null=True)
    # x_materiaomg = models.CharField('Código de la materia en Racima', max_length=11, blank=True, null=True)
    # curso = models.CharField('Nombre largo del curso', max_length=119, blank=True, null=True)
    # x_curso = models.CharField('Código del curso en Racima', max_length=120, blank=True, null=True)
    # omc = models.CharField('Nombre corto del curso', max_length=20, blank=True, null=True)
    # grupo_materias = models.CharField('Tipo de materia', max_length=50, blank=True, null=True)
    # etapa = models.CharField('Etapa', max_length=4, blank=True, null=True, choices=ETAPAS)
    # horas_semana_min = models.CharField('Horas mínimas de la materia por semana', max_length=10, blank=True, null=True)
    # horas_semana_max = models.CharField('Horas máximas de la materia por semana', max_length=10, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Unidades asociadas a una Sesión Docente'
        ordering = ['sd', 'grupo']
