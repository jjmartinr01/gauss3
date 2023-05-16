# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.db import models
from django.db.models import Q
from django.utils.timezone import now

from gauss.constantes import CARGOS_CENTROS
from cupo.habilitar_permisos import Miembro_Equipo_Directivo
from gauss.funciones import pass_generator, genera_nie, usuarios_ronda
from autenticar.models import Gauser, Permiso, Menu_default
from entidades.models import Subentidad, Entidad, Ronda, Cargo, Gauser_extra, Dependencia, MiembroDepartamento, Menu, \
    EspecialidadDocenteBasica, MiembroEDB
from entidades.models import Departamento as DepEntidad
from entidades.menus_entidades import Menus_Centro_Educativo, TiposCentro
from estudios.models import Materia, Curso, Grupo, EtapaEscolar
from horarios.models import Actividad, Horario, Sesion, SesionExtra
from mensajes.models import Aviso
from programaciones.models import Departamento, Especialidad_entidad
from math import ceil
from cupo.tipos_centro import TC

logger = logging.getLogger('django')


class Cupo(models.Model):
    ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la versión del cupo", max_length=150)
    bloqueado = models.BooleanField("¿Está bloqueado?", default=False)
    pub_rrhh = models.BooleanField("¿Se publica para RRHH?", default=False)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'Cupos de profesorado'
        ordering = ['-creado']

    def puede_activarse_pub_rrhh(self, g_e):
        cargo_inspector = Cargo.objects.get(entidad=self.ronda.entidad, clave_cargo='g_inspector_educacion')
        gauser_inspectores = usuarios_ronda(self.ronda, cargos=[cargo_inspector]).values_list('gauser__id', flat=True)
        con1 = g_e.gauser.id in gauser_inspectores
        con2 = (self.ronda.entidad == g_e.ronda.entidad) and g_e.has_permiso('publica_cupo_para_rrhh')
        if con1 or con2:
            interinos = Profesor_cupo.objects.filter(profesorado__cupo=self, tipo='INT')
            q1 = Q(profesorado__especialidad__cod_espec='')
            q2 = Q(profesorado__especialidad__cod_cuerpo='')
            if interinos.filter(q1 | q2).count() == 0:
                if self.bloqueado:
                    return True, 'Se cumplen todas las condiciones.'
                else:
                    return False, 'El cupo debe estar bloqueado para activar la publicación.'
            else:
                msg = 'No es posible la publicación. Hay especialidades en las que no se ha configurado el código del cuerpo o el código de la propia especialidad.'
                return False, msg
        else:
            return False, 'No tiene permisos suficientes. con1: %s, con2: %s' % (con1, con2)
    @property
    def es_posible_pdf_rrhh(self):
        return self.bloqueado and self.pub_rrhh
    @property
    def solicitud_interinos(self):
        return Profesor_cupo.objects.filter(profesorado__cupo=self, tipo='INT')
    @property
    def curso_escolar_cupo(self):
        y = self.ronda.fin.year
        return "%s/%s" % (y, y + 1)

    def __str__(self):
        return '%s %s (%s)' % (self.ronda.entidad.name, self.nombre, self.modificado)


class CupoPermisos(models.Model):
    PERMISOS = (('plwx', 'Propietario'), ('l', 'Lectura'), ('lw', 'Escritura'), ('lwx', 'Escritura y borrado'))
    cupo = models.ForeignKey(Cupo, on_delete=models.CASCADE)
    gauser = models.ForeignKey(Gauser, on_delete=models.CASCADE)
    permiso = models.CharField('Tipo de permiso', default='l', max_length=5, choices=PERMISOS)

    def __str__(self):
        return '%s %s (%s)' % (self.cupo, self.gauser, self.get_permiso_display())


class EspecialidadCupo(models.Model):
    cupo = models.ForeignKey(Cupo, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la especialidad", max_length=150)
    # departamento = models.ForeignKey(Departamento, blank=True, null=True, on_delete=models.CASCADE)
    cod_espec = models.CharField("Código de especialidad", max_length=15, blank=True, null=True, default='')
    cod_cuerpo = models.CharField("Código del cuerpo", max_length=15, blank=True, null=True, default='')
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
    dep = models.CharField('Departamento', max_length=310, blank=True, null=True, default='')
    x_dep = models.CharField('Departamento clave', max_length=9, blank=True, null=True, default='')
    max_completa = models.FloatField("Máximo número de periodos lectivos con jornada completa", default=20)
    min_completa = models.FloatField("Mínimo número de periodos lectivos con jornada completa", default=18)
    max_dostercios = models.FloatField("Máximo número de periodos lectivos con 2/3 de jornada", default=13)
    min_dostercios = models.FloatField("Mínimo número de periodos lectivos con 2/3 de jornada", default=12)
    max_media = models.FloatField("Máximo número de periodos lectivos con media jornada", default=10)
    min_media = models.FloatField("Mínimo número de periodos lectivos con media jornada", default=9)
    max_tercio = models.FloatField("Máximo número de periodos lectivos con 1/3 de jornada", default=7)
    min_tercio = models.FloatField("Mínimo número de periodos lectivos con 1/3 de jornada", default=6)
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')

    class Meta:
        verbose_name_plural = 'Especialidades en el cupo del profesorado'
        ordering = ['x_dep', 'nombre']

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


class EtapaEscolarCupo(models.Model):
    cupo = models.ForeignKey(Cupo, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre de la etapa escolar', max_length=250)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
    orden = models.IntegerField('Orden', default=1)

    class Meta:
        ordering = ['clave_ex', 'nombre']

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.clave_ex)


class CursoCupo(models.Model):
    cupo = models.ForeignKey(Cupo, on_delete=models.CASCADE)
    nombre = models.CharField("Curso", max_length=150)
    etapa_escolar = models.ForeignKey(EtapaEscolarCupo, blank=True, null=True, on_delete=models.CASCADE)
    tipo = models.CharField("Tipo de estudio", max_length=75, null=True, blank=True)
    nombre_especifico = models.CharField("Nombre específico", max_length=150, null=True, blank=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
    num_alumnos = models.IntegerField("Número de alumnos previsto en este curso", default=20)
    orden = models.IntegerField('Orden', default=1)

    @property
    def get_horas_media(self):
        horas = 0
        for materia in self.materia_cupo_set.all():
            horas += materia.horas * materia.num_alumnos
        try:
            return horas / self.num_alumnos
        except:
            return 0

    class Meta:
        ordering = ['etapa_escolar__clave_ex', 'tipo', 'nombre']

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.cupo.ronda.entidad.name)


class Materia_cupo(models.Model):
    cupo = models.ForeignKey(Cupo, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(EspecialidadCupo, blank=True, null=True, on_delete=models.SET_NULL)
    curso = models.ForeignKey(Curso, blank=True, null=True, on_delete=models.CASCADE)
    curso_cupo = models.ForeignKey(CursoCupo, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la materia o actividad", max_length=120, null=True, blank=True)
    periodos = models.IntegerField("Número de periodos lectivos por semana", null=True, blank=True)
    horas = models.FloatField("Número de horas lectivas por semana", null=True, blank=True)
    num_alumnos = models.IntegerField("Nº de alumnos previstos", default=1)
    min_num_alumnos = models.IntegerField("Nº de alumnos mínimo por grupo", default=10)
    max_num_alumnos = models.IntegerField("Nº de alumnos máximo por grupo", default=30)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    @property
    def num_grupos(self):
        if self.num_alumnos >= self.min_num_alumnos:
            num_grupos = int(ceil(float(self.num_alumnos) / float(self.max_num_alumnos)))
        else:
            num_grupos = 0
        return num_grupos

    @property
    def total_periodos(self):
        return self.num_grupos * self.horas

    class Meta:
        verbose_name_plural = 'Materias incluidas en el cupo'
        ordering = ['curso', 'nombre']

    def __str__(self):
        return '%s (%s) -- %s' % (self.nombre, self.curso_cupo, self.cupo)


class Profesores_cupo(models.Model):
    cupo = models.ForeignKey(Cupo, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(EspecialidadCupo, blank=True, null=True, on_delete=models.CASCADE)
    num_periodos = models.IntegerField("Nº de periodos lectivos para la especialidad", null=True, blank=True)
    num_horas = models.FloatField("Nº de horas lectivas para la especialidad", default=0)

    class Meta:
        verbose_name_plural = 'Profesores por especialidad asociados cupo'
        ordering = ['especialidad__x_dep', 'especialidad__nombre']

    @property
    def materias(self):
        return Materia_cupo.objects.filter(especialidad=self.especialidad, cupo=self.cupo)

    @property
    def reparto_profes(self):
        for jornada in ['min_completa', 'min_dostercios', 'min_media', 'min_tercio']:
            if not getattr(self.especialidad, jornada) > 0:
                setattr(self.especialidad, jornada, 1)
                self.especialidad.save()
        profes_completos = int(self.num_horas / self.especialidad.min_completa)
        periodos_sobrantes = self.num_horas % self.especialidad.min_completa
        profes_dostercios = int(periodos_sobrantes / self.especialidad.min_dostercios)
        periodos_sobrantes = periodos_sobrantes % self.especialidad.min_dostercios
        profes_media = int(periodos_sobrantes / self.especialidad.min_media)
        periodos_sobrantes = periodos_sobrantes % self.especialidad.min_media
        profes_tercio = int(periodos_sobrantes / self.especialidad.min_tercio)
        # Limitamos el número de periodos sobrantes a dos decimales:
        periodos_sobrantes = round(periodos_sobrantes % self.especialidad.min_tercio, 2)
        # periodos_sobrantes = '{:.2f}'.format(periodos_sobrantes % self.especialidad.min_tercio)

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
                'num_periodos': self.num_horas}

    def __str__(self):
        return 'Cupo: %s (%s) -- %s:%s' % (
            self.cupo.nombre, self.cupo.ronda.entidad.code, self.especialidad.nombre, self.num_horas)


class Profesor_cupo(models.Model):
    TIPO_PROFESOR = (('DEF', 'Destino definitivo'), ('INT', 'Docente Interino'), ('NONE', 'No necesario'))
    TIPO_JORNADA = (
        ('1', 'Jornada completa'), ('2', 'Jornada de 2/3'), ('3', 'Media jornada'), ('4', 'Jornada de 1/3'))
    profesorado = models.ForeignKey(Profesores_cupo, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre del profesor/a', max_length=300, blank=True, null=True)
    tipo = models.CharField('Tipo', choices=TIPO_PROFESOR, blank=True, null=True, max_length=10, default='DEF')
    jornada = models.CharField('Jornada', choices=TIPO_JORNADA, blank=True, null=True, max_length=10, default='1')
    bilingue = models.BooleanField('Es bilingüe?', default=False)
    itinerante = models.BooleanField('Es itinerante?', default=False)
    noafin = models.BooleanField('Es no afín?', default=False)
    vacante = models.BooleanField('Es una vacante?', default=False)
    sustituto = models.BooleanField('Es sustituto de otro docente?', default=False)
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')
    observaciones_ocultas = models.TextField('Observaciones ocultas', blank=True, null=True, default='')

    @property
    def observaciones_sin_newlines(self):
        return self.observaciones.replace('\n', ' ## ')

    @property
    def observaciones_ocultas_sin_newlines(self):
        return self.observaciones_ocultas.replace('\n', ' ## ')
    class Meta:
        verbose_name_plural = 'Profesores del cupo'
        ordering = ['profesorado__especialidad__dep', 'tipo', 'jornada']

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

class CargaPlantillaOrganicaCentros(models.Model):
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, blank=True, null=True)
    ejer = models.CharField('Ejercicio. Se corresponde con el año.', max_length=6)
    creado = models.DateTimeField("Fecha y hora creación de la carga", auto_now_add=True)

    def __str__(self):
        return '%s (%s)' % (self.g_e, self.creado)


class EspecialidadPlantilla(models.Model):
    TIPOS = (('com', 'Compartida'), ('ord', 'Ordinaria'), ('iti', 'Itinerante'), ('bil', 'Bilingüe'))
    cpoc = models.ForeignKey(CargaPlantillaOrganicaCentros, on_delete=models.CASCADE)
    centro = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    code = models.CharField('Código cuerpo y especialidad', max_length=8)
    tipo = models.CharField('Tipo de plaza', choices=TIPOS, max_length=4, default='ord')
    nombre = models.CharField('Nombre de la especialidad', blank=True, null=True, max_length=65)
    plazas = models.IntegerField('Número de plazas existentes')
    ocupadas = models.IntegerField('Número de plazas ocupadas')

    @property
    def vacantes(self):
        return self.plazas - self.ocupadas

    @property
    def cod_cuerpo(self):
        return self.code[:3]

    @property
    def cod_especialidad(self):
        return self.code[3:]

    @property
    def jornadas_incompletas(self):
        return self.code[3:]

    class Meta:
        verbose_name_plural = 'Especialidades en Plantilla Orgánica'
        ordering = ['-cpoc__creado']

    def __str__(self):
        return '%s - %s - %s (%s, %s)' % (self.centro, self.code, self.nombre, self.plazas, self.ocupadas)


class PlantillaOrganica(models.Model):
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, blank=True, null=True)
    ronda_centro = models.ForeignKey(Ronda, on_delete=models.CASCADE, blank=True, null=True)
    horario = models.ForeignKey(Horario, on_delete=models.SET_NULL, blank=True, null=True)
    carga_completa = models.BooleanField('¿Se ha cargado completamente?', default=False)
    minutos_periodo = models.IntegerField('Minutos de duración de clase docente', default=50)
    creado = models.DateTimeField("Fecha y hora creación de la PO", auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Plantillas orgánicas'
        ordering = ['-creado']

    def clave_ex2clave_ex(self, cadena):
        try:
            return str(int(float(cadena.replace(',', '.'))))
        except:
            return ''

    ########################################################################
    ############ Cargamos dependencias:
    def carga_dependencia(self, data):
        x_dependencia = self.clave_ex2clave_ex(data['x_dependencia'])
        try:
            dependencia, c = Dependencia.objects.get_or_create(clave_ex=x_dependencia,
                                                               entidad=self.ronda_centro.entidad)
            if c:
                dependencia.nombre = data['c_coddep']
                dependencia.abrev = data['c_coddep']
                dependencia.es_aula = True
                dependencia.save()
        except:
            dependencias = Dependencia.objects.filter(clave_ex=x_dependencia,
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
            x_etapa_escolar = self.clave_ex2clave_ex(etapa['x_etapa_escolar'])
            EtapaEscolar.objects.get_or_create(nombre=etapa['etapa_escolar'], clave_ex=x_etapa_escolar)

    ########################################################################
    ############ Cargamos cursos:
    def carga_curso(self, data):
        x_curso = self.clave_ex2clave_ex(data['x_curso'])
        try:
            # curso, c = Curso.objects.get_or_create(clave_ex=x_curso, ronda=self.ronda_centro)
            curso = Curso.objects.get(clave_ex=x_curso, ronda=self.ronda_centro)
        except:
            cursos = Curso.objects.filter(clave_ex=x_curso, ronda=self.ronda_centro)
            if cursos.count() > 0:
                curso = cursos[0]
                # cursos.exclude(pk__in=[curso.pk]).delete()
            else:
                curso = Curso.objects.create(clave_ex=x_curso, ronda=self.ronda_centro)
        curso.nombre = data['curso']
        curso.nombre_especifico = data['omc']
        x_etapa_escolar = self.clave_ex2clave_ex(data['x_etapa_escolar'])
        try:
            curso.etapa_escolar = EtapaEscolar.objects.get(clave_ex=x_etapa_escolar)
        except:
            LogCarga.objects.create(g_e=self.g_e, log='No encuentra etapa: %s' % data['x_etapa_escolar'])
        curso.save()
        return curso

    def carga_cursos(self):
        cursos = self.plantillaxls_set.all().values('x_curso', 'curso', 'omc', 'x_etapa_escolar')
        for curso in cursos:
            self.carga_curso(curso)
        # Curso.objects.filter(ronda=self.ronda_centro, clave_ex='').delete()
        return True

    ########################################################################
    ############ Cargamos grupos:
    def carga_grupo(self, data):
        x_unidad = self.clave_ex2clave_ex(data['x_unidad'])
        try:
            # grupo, c = Grupo.objects.get_or_create(clave_ex=x_unidad, ronda=self.ronda_centro)
            grupo = Grupo.objects.get(clave_ex=x_unidad, ronda=self.ronda_centro)
            # if c:
            #     grupo.nombre = data['unidad']
            #     grupo.save()
        except:
            grupos = Grupo.objects.filter(clave_ex=x_unidad, ronda=self.ronda_centro)
            if grupos.count() > 0:
                grupo = grupos[0]
                # grupos.exclude(pk__in=[grupo.pk]).delete()
            else:
                grupo = Grupo.objects.create(clave_ex=x_unidad, ronda=self.ronda_centro)
        grupo.nombre = data['unidad']
        grupo.save()
        try:
            x_curso = self.clave_ex2clave_ex(data['x_curso'])
            curso = Curso.objects.get(clave_ex=x_curso, ronda=self.ronda_centro)
            grupo.cursos.add(curso)
        except:
            LogCarga.objects.create(g_e=self.g_e, log='Error al cargar el curso: %s' % data['x_curso'])
        return grupo

    def carga_grupos(self):
        grupos = self.plantillaxls_set.all().values('x_curso', 'x_unidad', 'unidad')
        for grupo in grupos:
            self.carga_grupo(grupo)
        # Grupo.objects.filter(ronda=self.ronda_centro, clave_ex='').delete()

    ########################################################################
    ############ Cargamos materias:
    def carga_materia(self, data):
        x_curso = self.clave_ex2clave_ex(data['x_curso'])
        x_materiaomg = self.clave_ex2clave_ex(data['x_materiaomg'])
        try:
            curso = Curso.objects.get(clave_ex=x_curso, ronda=self.ronda_centro)
        except:
            LogCarga.objects.create(g_e=self.g_e, log='Error carga de curso de la materia: %s' % data['x_materiaomg'])
            curso = None
        try:
            # materia, c = Materia.objects.get_or_create(clave_ex=x_materiaomg, curso=curso)
            materia = Materia.objects.get(clave_ex=x_materiaomg, curso=curso)
        except:
            materias = Materia.objects.filter(clave_ex=x_materiaomg, curso=curso)
            if materias.count() > 0:
                materia = materias[0]
                # materias.exclude(pk__in=[materia.pk]).delete()
            else:
                materia = Materia.objects.create(clave_ex=x_materiaomg, curso=curso)
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
        # Materia.objects.filter(curso__ronda=self.ronda_centro, clave_ex='').delete()

    ########################################################################
    ############ Cargamos departamentos:
    def carga_departamentos(self):
        tipo_centro = self.ronda_centro.entidad.entidadextra.tipo_centro
        if 'C.E.I.P.' in tipo_centro or 'C.R.A.' in tipo_centro:
            departamentos = self.plantillaxls_set.all().values('puesto', 'x_puesto').distinct()
            for d in departamentos:
                x_puesto = self.clave_ex2clave_ex(d['x_puesto'])
                DepEntidad.objects.get_or_create(ronda=self.ronda_centro, nombre=d['puesto'], clave_ex=x_puesto)
        else:
            departamentos = self.plantillaxls_set.all().values('departamento', 'x_departamento').distinct()
            for d in departamentos:
                x_departamento = self.clave_ex2clave_ex(d['x_departamento'])
                if x_departamento == '63':  # El 63 es el departamento de Actividades compl. y extraes.
                    DepEntidad.objects.get_or_create(ronda=self.ronda_centro, nombre=d['departamento'],
                                                     clave_ex=x_departamento, didactico=False)
                else:
                    DepEntidad.objects.get_or_create(ronda=self.ronda_centro, nombre=d['departamento'],
                                                     clave_ex=x_departamento)

        return True

    ########################################################################
    ############ Cargamos puestos <-> cargos:
    def carga_puestos(self):
        puestos = self.plantillaxls_set.all().values('puesto', 'x_puesto').distinct()
        for p in puestos:
            # Cargo.objects.get_or_create(cargo=p['puesto'], clave_cargo=p['x_puesto'], borrable=False,
            #                             entidad=self.ronda_centro.entidad)
            # edb, c = EspecialidadDocenteBasica.objects.get_or_create(ronda=self.ronda_centro, clave_ex=p['x_puesto'])
            # edb.puesto = p['puesto']
            # Decido no guardar x_puesto ya que genera varias especialidades iguales debido a diferencias de
            # x_puesto entre maestros, catedráticos y profesores
            edb, c = EspecialidadDocenteBasica.objects.get_or_create(ronda=self.ronda_centro, puesto=p['puesto'])
            # edb.save()
        return True

    ########################################################################
    ############ Cargamos actividades:
    def carga_actividades(self):
        actividades = self.plantillaxls_set.all().values('actividad', 'x_actividad', 'l_requnidad',
                                                         'docencia').distinct()
        b = {'S': True, 'N': False, 's': True, 'n': False}
        for a in actividades:
            x_actividad = self.clave_ex2clave_ex(a['x_actividad'])
            try:
                # act, c = Actividad.objects.get_or_create(entidad=self.ronda_centro.entidad, clave_ex=x_actividad)
                # if c:
                #     act.requiere_unidad = b[a['l_requnidad']]
                #     act.nombre = a['actividad']
                #     act.requiere_materia = b[a['docencia']]
                #     act.save()
                act = Actividad.objects.get(entidad=self.ronda_centro.entidad, clave_ex=x_actividad)
            except Exception as msg:
                log = 'Error cargar actividad %s. %s' % (a['x_actividad'], str(msg))
                LogCarga.objects.create(g_e=self.g_e, log=log)
                acts = Actividad.objects.filter(entidad=self.ronda_centro.entidad, clave_ex=x_actividad)
                if acts.count() > 0:
                    act = acts[0]
                    acts.exclude(pk__in=[act.pk]).delete()
                else:
                    act = Actividad.objects.create(entidad=self.ronda_centro.entidad, clave_ex=x_actividad)
            act.requiere_unidad = b[a['l_requnidad']]
            act.nombre = a['actividad']
            act.requiere_materia = b[a['docencia']]
            act.save()
        return True

    ########################################################################
    ############ Creamos cargos en el centro:
    def crea_cargos_entidad(self):
        e = self.ronda_centro.entidad
        # Se comprueba que todos los cargos de un centro están creados. Si no es así se crean:
        for c in CARGOS_CENTROS:
            cargo, creado = Cargo.objects.get_or_create(entidad=e, borrable=False, clave_cargo=c['clave_cargo'])
            if creado:
                cargo.cargo = c['cargo']
                cargo.nivel = c['nivel']
                cargo.save()
                for code_nombre in c['permisos']:
                    try:
                        cargo.permisos.add(Permiso.objects.get(code_nombre=code_nombre))
                    except Exception as msg:
                        log = '<br>Permiso: %s -- %s' % (code_nombre, str(msg))
                        LogCarga.objects.create(g_e=self.g_e, log=log)
        return True

    def get_gex_docente(self, gauser, clave_ex, puesto, x_puesto, x_departamento, cargo):
        try:
            gex, c = Gauser_extra.objects.get_or_create(gauser=gauser, ronda=self.ronda_centro)
            gex.clave_ex = clave_ex
            gex.activo = True
            gex.puesto = puesto
            gex.save()
            edb, c = EspecialidadDocenteBasica.objects.get_or_create(ronda=self.ronda_centro, puesto=puesto)
            MiembroEDB.objects.get_or_create(edb=edb, g_e=gex)
            gex.cargos.add(cargo)
            # try:
            #     puesto = Cargo.objects.get(clave_cargo=x_puesto, entidad=self.ronda_centro.entidad)
            #     gex.cargos.add(puesto)
            # except:
            #     puesto = None
            #     LogCarga.objects.create(g_e=gex, log='No encuentra puesto: %s' % x_puesto)
            try:
                tipo_centro = self.ronda_centro.entidad.entidadextra.tipo_centro
                if 'C.E.I.P.' in tipo_centro or 'C.R.A.' in tipo_centro:
                    departamento = DepEntidad.objects.get(clave_ex=x_puesto, ronda=self.ronda_centro)
                else:
                    departamento = DepEntidad.objects.get(clave_ex=x_departamento, ronda=self.ronda_centro)
                midep, c = MiembroDepartamento.objects.get_or_create(departamento=departamento, g_e=gex)
                if puesto:
                    midep.puesto = puesto.clave_cargo
                    midep.save()
            except:
                LogCarga.objects.create(g_e=gex, log='No encuentra departamento: %s' % x_departamento)
            return gex
        except Exception as msg:
            LogCarga.objects.create(g_e=self.g_e, log=str(msg))
            return None

    def carga_docentes(self):
        ges = self.plantillaxls_set.all().values('docente', 'x_docente', 'dni', 'email', 'puesto', 'x_puesto',
                                                 'x_departamento').distinct()
        x_docentes = []
        docentes = []
        cargo = Cargo.objects.get(entidad=self.ronda_centro.entidad, clave_cargo='g_docente')
        for ge in ges:
            if not ge['x_docente'] in x_docentes:
                x_docentes.append(ge['x_docente'])
                last_name, first_name = ge['docente'].split(', ')
                clave_ex, dni, puesto, x_puesto, x_departamento, email = ge['x_docente'], genera_nie(ge['dni']), ge[
                    'puesto'], ge['x_puesto'], ge['x_departamento'], ge['email']
                try:
                    gauser = Gauser.objects.get(dni=dni)
                except Exception as msg:
                    log = 'Error: %s. dni %s - email %s' % (str(msg), dni, email)
                    LogCarga.objects.create(g_e=self.g_e, log=log)
                    try:
                        gex = Gauser_extra.objects.get(clave_ex=clave_ex, ronda=self.ronda_centro)
                        gauser = gex.gauser
                        gauser.set_password(pass_generator(size=9))
                        log = 'Sin embargo existe g_e con clave_x: %s - %s' % (clave_ex, gex)
                        logger.warning(log)
                        LogCarga.objects.create(g_e=self.g_e, log=log)
                    except:
                        gauser = Gauser.objects.create_user(pass_generator(size=9), email=email, last_login=now(),
                                                            password=pass_generator(size=9))
                        log = 'Creado usuario: %s' % (gauser)
                        LogCarga.objects.create(g_e=self.g_e, log=log)
                        # try:
                        # gauser = Gauser.objects.get(email=email)
                        # gauser.set_password(pass_generator(size=9))
                        # log = 'Sin embargo existe usuario con email: %s - %s' % (email, gauser)
                        # logger.warning(log)
                        # LogCarga.objects.create(g_e=self.g_e, log=log)
                        # except:
                        # gauser = Gauser.objects.create_user(pass_generator(size=9), email=email, last_login=now(),
                        #                                         password=pass_generator(size=9))
                        # log = 'Creado usuario: %s' % (gauser)
                        # LogCarga.objects.create(g_e=self.g_e, log=log)
                try:
                    gauser.dni = dni
                    gauser.first_name = first_name[0:29]
                    gauser.last_name = last_name[0:29]
                    gauser.email = email
                    gauser.save()
                    gex = self.get_gex_docente(gauser, clave_ex, puesto, x_puesto, x_departamento, cargo)
                    if gex:
                        docentes.append(gex)
                except Exception as msg:
                    LogCarga.objects.create(g_e=self.g_e, log=str(msg))
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
            try:
                g_e = Gauser_extra.objects.get(clave_ex=p.x_docente, ronda=self.ronda_centro)
                if p.localidad:
                    localidad = p.localidad
                else:
                    localidad = self.ronda_centro.entidad.localidad
                sesion, c = Sesion.objects.get_or_create(horario=horario, dia=int(float(p.dia)), g_e=g_e,
                                                         hora_inicio=int(float(p.hora_inicio)),
                                                         hora_fin=int(float(p.hora_fin)),
                                                         hora_inicio_cadena=p.hora_inicio_cadena,
                                                         hora_fin_cadena=p.hora_fin_cadena,
                                                         localidad=localidad)
                try:
                    grupo = Grupo.objects.get(clave_ex=p.x_unidad, ronda=self.ronda_centro)
                except:
                    LogCarga.objects.create(g_e=self.g_e, log='Error al cargar el grupo %s' % p.x_unidad)
                    grupo = None
                try:
                    if p.x_dependencia != '-1':
                        dependencia = Dependencia.objects.get(clave_ex=p.x_dependencia,
                                                              entidad=self.ronda_centro.entidad)
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
            except Exception as msg:
                print(p.x_docente, self.ronda_centro)
                print(str(msg))
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
            estructura = list(TC.keys())[0]  # Por defecto tomar la primera key del diccionario
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
        try:
            grexc = self.grupoexcluido_set.all().values_list('grupo__id', flat=True)
            # LogCarga.objects.create(g_e=gex, log='%s grupos excluidos en carga_pdocente %s' % (grexc.count(), gex))
            sextras = SesionExtra.objects.filter(sesion__horario=self.horario, sesion__g_e=gex)
            # LogCarga.objects.create(g_e=gex, log=sextras.count())
            sextras = sextras.filter(~Q(grupo__id__in=grexc))
            # LogCarga.objects.create(g_e=gex, log=sextras.count())
            pd, c = PDocente.objects.get_or_create(po=self, g_e=gex)
            if c:
                pd.calcula_minutos_periodo()
            sesiones_utilizadas = []
            for apartado in self.estructura_po:
                for nombre_columna, contenido_columna in self.estructura_po[apartado].items():
                    sesiones_id = sextras.filter(~Q(sesion_id__in=sesiones_utilizadas),
                                                 contenido_columna['q']).values_list('sesion__id', flat=True)
                    sesiones_utilizadas += list(sesiones_id)
                    sesiones = Sesion.objects.filter(id__in=sesiones_id)
                    for localidad in pd.localidades:
                        pdc, c = PDocenteCol.objects.get_or_create(pd=pd, periodos_base=contenido_columna['horas_base'],
                                                                   codecol=contenido_columna['codecol'],
                                                                   localidad=localidad, nombre=nombre_columna)
                        pdc.sesiones.add(*sesiones.filter(localidad=localidad))
                        LogCarga.objects.create(g_e=gex, log='Added sesiones a PDocenteCol')
                        pdc.save()
        except Exception as msg:
            LogCarga.objects.create(g_e=gex, log=str(msg))

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

    def habilitar_miembros_equipo_directivo(self):
        if self.ronda_centro.entidad.entidadextra.tipo_centro in TiposCentro:
            for menu in Menus_Centro_Educativo:
                md = Menu_default.objects.get(code_menu=menu[0])
                try:
                    Menu.objects.get(entidad=self.ronda_centro.entidad, menu_default=md)
                except:
                    Menu.objects.create(entidad=self.ronda_centro.entidad, menu_default=md, texto_menu=menu[1],
                                        pos=menu[2])
        permisos = Permiso.objects.filter(code_nombre__in=Miembro_Equipo_Directivo)
        # La siguiente línea es para eliminar los posibles cargos que se crearon con esa clave anteriormente y
        # que ya no tienen razón de ser:
        Cargo.objects.filter(entidad=self.ronda_centro.entidad, clave_cargo='202006011113').delete()
        try:
            miembro_equipo_directivo = Cargo.objects.get(entidad=self.ronda_centro.entidad,
                                                         clave_cargo='g_miembro_equipo_directivo')
        except:
            miembro_equipo_directivo = Cargo.objects.create(entidad=self.ronda_centro.entidad, borrable=False,
                                                            cargo='Miembro del Equipo Directivo',
                                                            clave_cargo='g_miembro_equipo_directivo')
            miembro_equipo_directivo.permisos.add(*permisos)
        for pxls in self.plantillaxls_set.filter(x_actividad__in=['529', '530', '532']):
            try:
                gex = Gauser_extra.objects.get(ronda=self.ronda_centro, clave_ex=pxls.x_docente)
                gex.cargos.add(miembro_equipo_directivo)
            except:
                pass

    def carga_plantilla_xls(self):
        self.crea_cargos_entidad()
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
        LogCarga.objects.create(g_e=self.g_e, log="Inicio habilitar miembros equipo directivo")
        self.habilitar_miembros_equipo_directivo()
        LogCarga.objects.create(g_e=self.g_e, log="Finalizada la carga de la plantilla")
        return True

    def __str__(self):
        return 'PO: %s - %s' % (self.ronda_centro, self.g_e)


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
    localidad = models.CharField('Localidad asociada al grupo', max_length=48, blank=True, null=True)
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

    def __str__(self):
        return '%s - x_docente: %s - x_puesto: %s - x_unidad: %s' % (self.po, self.x_docente,
                                                                     self.x_puesto, self.x_unidad)


class PDocente(models.Model):
    LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7),
              (115, 129, 8), (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13),
              (205, 219, 14), (220, 234, 15), (235, 249, 16), (250, 264, 17), (265, 279, 18), (280, 294, 19))
    RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7),
             (124, 139, 8), (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13),
             (220, 235, 14), (236, 251, 15), (252, 267, 16), (268, 283, 17), (284, 299, 18), (300, 235, 19))
    po = models.ForeignKey(PlantillaOrganica, on_delete=models.CASCADE, blank=True, null=True)
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, blank=True, null=True)
    minutos_periodo = models.IntegerField('Número de minutos de trabajo por cada periodo', default=55)

    @property
    def num_periodos_docencia_basicos(self):
        return sum(self.pdocentecol_set.filter(periodos_base=True).values_list('periodos', flat=True))

    @property
    def num_periodos_docencia(self):
        return sum(self.pdocentecol_set.all().values_list('periodos', flat=True))

    @property
    def num_minutos_docencia(self):
        minutos = 0
        for pdcol in self.pdocentecol_set.all():
            minutos += pdcol.minutos
        return minutos
        # Debería coincidir con self.num_periodos_docencia * self.minutos_periodo

    @property  # Para comprobar si coincide el cálculo anterior
    def comprobar_num_minutos_docencia(self):
        return self.num_minutos_docencia - self.num_periodos_docencia * self.minutos_periodo

    @property
    def localidades(self):
        ls = set(Sesion.objects.filter(horario=self.po.horario, g_e=self.g_e).values_list('localidad', flat=True))
        if len(ls) == 0:
            return [self.po.ronda_centro.entidad.localidad]
        else:
            return [l for l in ls if l]

    def calcula_minutos_periodo(self):
        tipo_centro = self.g_e.ronda.entidad.entidadextra.tipo_centro
        if 'C.E.P.A' in tipo_centro:
            self.minutos_periodo = 45
        elif 'C.E.I.P.' in tipo_centro or 'C.R.A.' in tipo_centro:
            self.minutos_periodo = 60
        elif self.g_e.jornada_contratada in ['23:00', '24:00', '25:00', '16:40', '8:20']:
            self.minutos_periodo = 60
        else:
            minutos = 0
            for s in Sesion.objects.filter(g_e=self.g_e, horario=self.po.horario):
                if s.minutos > minutos:
                    minutos = s.minutos
            if minutos == 30:
                self.minutos_periodo = 60
            else:
                self.minutos_periodo = minutos
        self.save()
        return self.minutos_periodo

    def __str__(self):
        return '%s - %s' % (self.po, self.g_e)


class PDocenteCol(models.Model):
    pd = models.ForeignKey(PDocente, on_delete=models.CASCADE)
    codecol = models.IntegerField('Código de identificación de la columna', default=0)
    nombre = models.CharField('Nombre de la columna', max_length=50)
    periodos = models.IntegerField('Periodos en horario impartidos', default=0)
    sesiones = models.ManyToManyField(Sesion, blank=True)
    periodos_base = models.BooleanField('¿Son periodos básicos contados para plantilla?', default=True)
    periodos_added = models.IntegerField('Periodos en pantalla', default=0)
    localidad = models.CharField('Localidad asociada al grupo', max_length=48, blank=True, null=True)

    @property
    def minutos_sesiones(self):  # Minutos duranción de las sesiones almacenadas
        return sum([h[1] - h[0] for h in self.sesiones.all().values_list('hora_inicio', 'hora_fin')])

    @property
    def num_periodos_sesiones(
            self):  # Número de peridos (por sesiones) en función de los minutos asignados a un periodo
        return int(self.minutos_sesiones / self.pd.minutos_periodo)

    @property
    def minutos(self):  # Minutos duranción de las sesiones almacenadas más los periodos añadidos
        return self.minutos_sesiones + self.periodos_added * self.pd.minutos_periodo

    @property
    def num_periodos(self):  # Número de periodos en función de los minutos asignados a un periodo
        return int(self.minutos / self.pd.minutos_periodo)

    class Meta:
        ordering = ['codecol', ]

    def save(self, *args, **kwargs):
        if self.pk:
            self.periodos = self.num_periodos
        super(PDocenteCol, self).save(*args, **kwargs)

    def __str__(self):
        return '%s - %s - (%s periodos y %s minutos)' % (self.pd, self.nombre, self.num_periodos, self.minutos)


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


ESPECS = {'0590': [{'especialidad': '001', 'nombre': 'FILOSOFIA'}, {'especialidad': '002', 'nombre': 'GRIEGO'},
                   {'especialidad': '003', 'nombre': 'LATIN'},
                   {'especialidad': '004', 'nombre': 'LENGUA CASTELLANA Y LITERATURA'},
                   {'especialidad': '005', 'nombre': 'GEOGRAFIA E HISTORIA'},
                   {'especialidad': '006', 'nombre': 'MATEMATICAS'},
                   {'especialidad': '007', 'nombre': 'FISICA Y QUIMICA'},
                   {'especialidad': '008', 'nombre': 'BIOLOGIA Y GEOLOGIA'},
                   {'especialidad': '009', 'nombre': 'DIBUJO'}, {'especialidad': '010', 'nombre': 'FRANCES'},
                   {'especialidad': '011', 'nombre': 'INGLES'}, {'especialidad': '012', 'nombre': 'ALEMAN'},
                   {'especialidad': '013', 'nombre': 'ITALIANO'},
                   {'especialidad': '014', 'nombre': 'LENGUA Y LITERATURA CATALANAS (ISLAS BALEARES)'},
                   {'especialidad': '015', 'nombre': 'PORTUGUES'}, {'especialidad': '016', 'nombre': 'MUSICA'},
                   {'especialidad': '017', 'nombre': 'EDUCACION FISICA'},
                   {'especialidad': '018', 'nombre': 'ORIENTACIÓN EDUCATIVA'},
                   {'especialidad': '019', 'nombre': 'TECNOLOGIA'},
                   {'especialidad': '039', 'nombre': 'TECNOLOGIA MINERA'},
                   {'especialidad': '051', 'nombre': 'LENGUA CATALANA Y LITERATURA'},
                   {'especialidad': '052', 'nombre': 'LENGUA Y LITERATURA VASCA'},
                   {'especialidad': '053', 'nombre': 'LENGUA Y LITERATURA GALLEGA'},
                   {'especialidad': '055', 'nombre': 'EDUCADORES (C.E.I.S.)'},
                   {'especialidad': '056', 'nombre': 'LENGUA Y LITERATURA VALENCIANA'},
                   {'especialidad': '057', 'nombre': 'LENGUA Y LITERATURA VASCA (NAVARRA)'},
                   {'especialidad': '058', 'nombre': 'APOYO AL AREA DE LENGUA Y CIENCIAS SOCIALES'},
                   {'especialidad': '059', 'nombre': 'APOYO AL AREA DE CIENCIAS O TECNOLOGIA'},
                   {'especialidad': '061', 'nombre': 'ECONOMIA'}, {'especialidad': '062', 'nombre': 'LENGUA ARANESA'},
                   {'especialidad': '101', 'nombre': 'ADMINISTRACION DE EMPRESAS'},
                   {'especialidad': '102', 'nombre': 'ANALISIS Y QUIMICA INDUSTRIAL'},
                   {'especialidad': '103', 'nombre': 'ASESORIA Y PROCESOS DE IMAGEN PERSONAL'},
                   {'especialidad': '104', 'nombre': 'CONSTRUCCIONES CIVILES Y EDIFICACION'},
                   {'especialidad': '105', 'nombre': 'FORMACION Y ORIENTACION LABORAL'},
                   {'especialidad': '106', 'nombre': 'HOSTELERIA Y TURISMO'},
                   {'especialidad': '107', 'nombre': 'INFORMATICA'},
                   {'especialidad': '108', 'nombre': 'INTERVENCION SOCIOCOMUNITARIA'},
                   {'especialidad': '109', 'nombre': 'NAVEGACION E INSTALACIONES MARINAS'},
                   {'especialidad': '110', 'nombre': 'ORGANIZACION Y GESTION COMERCIAL'},
                   {'especialidad': '111', 'nombre': 'ORGANIZACION Y PROCESOS DE MANTENIMIENTO DE VEHICULOS'},
                   {'especialidad': '112', 'nombre': 'ORGANIZACION Y PROYECTOS DE FABRICACION MECANICA'},
                   {'especialidad': '113', 'nombre': 'ORGANIZACION Y PROYECTOS DE SISTEMAS ENERGETICOS'},
                   {'especialidad': '114', 'nombre': 'PROCESOS DE CULTIVO ACUICOLA'},
                   {'especialidad': '115', 'nombre': 'PROCESOS DE PRODUCCION AGRARIA'},
                   {'especialidad': '116', 'nombre': 'PROCESOS EN LA INDUSTRIA ALIMENTARIA'},
                   {'especialidad': '117', 'nombre': 'PROCESOS DIAGNOSTICOS CLINICOS Y PRODUCTOS ORTOPROTESICOS'},
                   {'especialidad': '118', 'nombre': 'PROCESOS SANITARIOS'},
                   {'especialidad': '119', 'nombre': 'PROCESOS Y MEDIOS DE COMUNICACION'},
                   {'especialidad': '120', 'nombre': 'PROCESOS Y PRODUCTOS DE TEXTIL, CONFECCION Y PIEL'},
                   {'especialidad': '121', 'nombre': 'PROCESOS Y PRODUCTOS DE VIDRIO Y CERAMICA'},
                   {'especialidad': '122', 'nombre': 'PROCESOS Y PRODUCTOS EN ARTES GRAFICAS'},
                   {'especialidad': '123', 'nombre': 'PROCESOS Y PRODUCTOS EN MADERA Y MUEBLE'},
                   {'especialidad': '124', 'nombre': 'SISTEMAS ELECTRONICOS'},
                   {'especialidad': '125', 'nombre': 'SISTEMAS ELECTROTECNICOS Y AUTOMATICOS'},
                   {'especialidad': '201', 'nombre': 'COCINA Y PASTELERIA'},
                   {'especialidad': '203', 'nombre': 'ESTETICA'},
                   {'especialidad': '204', 'nombre': 'FABRICACION E INSTALACION DE CARPINTERIA Y MUEBLE'},
                   {'especialidad': '205', 'nombre': 'INSTALACION Y MANTENIMIENTO DE EQUIPOS TERMICOS Y DE FLUIDOS'},
                   {'especialidad': '206', 'nombre': 'INSTALACIONES ELECTROTECNICAS'},
                   {'especialidad': '207', 'nombre': 'INSTALACIONES Y EQUIPOS DE CRIA Y CULTIVO'},
                   {'especialidad': '208', 'nombre': 'LABORATORIO'},
                   {'especialidad': '209', 'nombre': 'MANTENIMIENTO DE VEHICULOS'},
                   {'especialidad': '210', 'nombre': 'MAQUINAS, SERVICIOS Y PRODUCCION'},
                   {'especialidad': '211', 'nombre': 'MECANIZADO Y MANTENIMIENTO DE MAQUINAS'},
                   {'especialidad': '212', 'nombre': 'OFICINA DE PROYECTOS DE CONSTRUCCION'},
                   {'especialidad': '213', 'nombre': 'OFICINA DE PROYECTOS DE FABRICACION MECANICA'},
                   {'especialidad': '214', 'nombre': 'OPERACIONES Y EQUIPOS DE ELABORACION DE PRODUCTOS ALIMENTARIOS'},
                   {'especialidad': '215', 'nombre': 'OPERACIONES DE PROCESOS'},
                   {'especialidad': '216', 'nombre': 'OPERACIONES Y EQUIPOS DE PRODUCCION AGRARIA'},
                   {'especialidad': '217', 'nombre': 'PATRONAJE Y CONFECCION'},
                   {'especialidad': '218', 'nombre': 'PELUQUERIA'},
                   {'especialidad': '219', 'nombre': 'PROCEDIMIENTOS DE DIAGNOSTICO CLINICO Y ORTOPROTESICO'},
                   {'especialidad': '220', 'nombre': 'PROCEDIMIENTOS SANITARIOS Y ASISTENCIALES'},
                   {'especialidad': '221', 'nombre': 'PROCESOS COMERCIALES'},
                   {'especialidad': '222', 'nombre': 'PROCESOS DE GESTION ADMINISTRATIVA'},
                   {'especialidad': '223', 'nombre': 'PRODUCCION EN ARTES GRAFICAS'},
                   {'especialidad': '224', 'nombre': 'PRODUCCION TEXTIL Y TRATAMIENTOS FISICO-QUIMICOS'},
                   {'especialidad': '225', 'nombre': 'SERVICIOS A LA COMUNIDAD'},
                   {'especialidad': '226', 'nombre': 'SERVICIOS DE RESTAURACION'},
                   {'especialidad': '227', 'nombre': 'SISTEMAS Y APLICACIONES INFORMATICAS'},
                   {'especialidad': '228', 'nombre': 'SOLDADURA'},
                   {'especialidad': '229', 'nombre': 'TECNICAS Y PROCEDIMIENTOS DE IMAGEN Y SONIDO'},
                   {'especialidad': '231', 'nombre': 'EQUIPOS ELECTRONICOS'},
                   {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'},
                   {'especialidad': '803', 'nombre': 'CULTURA CLASICA'},
                   {'especialidad': '810', 'nombre': 'AMBITO DE COMUNICACION: FRANCES'},
                   {'especialidad': '811', 'nombre': 'AMBITO DE COMUNICACION: INGLES'},
                   {'especialidad': '812', 'nombre': 'AMBITO DE COMUNICACION: LENGUA CASTELLANA'},
                   {'especialidad': '813', 'nombre': 'AMBITO DE COMUNICACION: EUSKERA'},
                   {'especialidad': '814', 'nombre': 'AMBITO DE CONOCIMIENTO SOCIAL'},
                   {'especialidad': '815', 'nombre': 'AMBITO CIENTIFICO-TECNOLOGICO'},
                   {'especialidad': '905', 'nombre': 'CIENCIAS DE LA NATURALEZA'}],
          '0591': [{'especialidad': '016', 'nombre': 'PRACTICAS DE MINERIA'},
                   {'especialidad': '021', 'nombre': 'TALLER DE VIDRIO Y CERAMICA'},
                   {'especialidad': '025', 'nombre': 'ACTIVIDADES (C.E.I.S.)'},
                   {'especialidad': '026', 'nombre': 'APOYO AL AREA PRACTICA'},
                   {'especialidad': '201', 'nombre': 'COCINA Y PASTELERIA'},
                   {'especialidad': '202', 'nombre': 'EQUIPOS ELECTRONICOS'},
                   {'especialidad': '203', 'nombre': 'ESTETICA'},
                   {'especialidad': '204', 'nombre': 'FABRICACION E INSTALACION DE CARPINTERIA Y MUEBLE'},
                   {'especialidad': '205', 'nombre': 'INSTALACION Y MANTENIMIENTO DE EQUIPOS TERMICOS Y DE FLUIDOS'},
                   {'especialidad': '206', 'nombre': 'INSTALACIONES ELECTROTECNICAS'},
                   {'especialidad': '207', 'nombre': 'INSTALACIONES Y EQUIPOS DE CRIA Y CULTIVO'},
                   {'especialidad': '208', 'nombre': 'LABORATORIO'},
                   {'especialidad': '209', 'nombre': 'MANTENIMIENTO DE VEHICULOS'},
                   {'especialidad': '210', 'nombre': 'MAQUINAS, SERVICIOS Y PRODUCCION'},
                   {'especialidad': '211', 'nombre': 'MECANIZADO Y MANTENIMIENTO DE MAQUINAS'},
                   {'especialidad': '212', 'nombre': 'OFICINA DE PROYECTOS DE CONSTRUCCION'},
                   {'especialidad': '213', 'nombre': 'OFICINA DE PROYECTOS DE FABRICACION MECANICA'},
                   {'especialidad': '214', 'nombre': 'OPERACIONES Y EQUIPOS DE ELABORACION DE PRODUCTOS ALIMENTARIOS'},
                   {'especialidad': '215', 'nombre': 'OPERACIONES DE PROCESOS'},
                   {'especialidad': '216', 'nombre': 'OPERACIONES DE PRODUCCION AGRARIA'},
                   {'especialidad': '217', 'nombre': 'PATRONAJE Y CONFECCION'},
                   {'especialidad': '218', 'nombre': 'PELUQUERIA'},
                   {'especialidad': '219', 'nombre': 'PROCEDIMIENTOS DE DIAGNOSTICO CLINICO Y ORTOPROTESICO'},
                   {'especialidad': '220', 'nombre': 'PROCEDIMIENTOS SANITARIOS Y ASISTENCIALES'},
                   {'especialidad': '221', 'nombre': 'PROCESOS COMERCIALES'},
                   {'especialidad': '222', 'nombre': 'PROCESOS DE GESTION ADMINISTRATIVA'},
                   {'especialidad': '223', 'nombre': 'PRODUCCION EN ARTES GRAFICAS'},
                   {'especialidad': '224', 'nombre': 'PRODUCCION TEXTIL Y TRATAMIENTOS FISICO-QUIMICOS'},
                   {'especialidad': '225', 'nombre': 'SERVICIOS A LA COMUNIDAD'},
                   {'especialidad': '226', 'nombre': 'SERVICIOS DE RESTAURACION'},
                   {'especialidad': '227', 'nombre': 'SISTEMAS Y APLICACIONES INFORMATICAS'},
                   {'especialidad': '228', 'nombre': 'SOLDADURA'},
                   {'especialidad': '229', 'nombre': 'TECNICAS Y PROCEDIMIENTOS DE IMAGEN Y SONIDO'},
                   {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'}],
          '0592': [{'especialidad': '001', 'nombre': 'ALEMAN'}, {'especialidad': '002', 'nombre': 'ARABE'},
                   {'especialidad': '003', 'nombre': 'CATALAN'}, {'especialidad': '004', 'nombre': 'CHINO'},
                   {'especialidad': '005', 'nombre': 'DANES'},
                   {'especialidad': '006', 'nombre': 'ESPAÑOL PARA EXTRANJEROS'},
                   {'especialidad': '007', 'nombre': 'EUSKERA'}, {'especialidad': '008', 'nombre': 'FRANCES'},
                   {'especialidad': '009', 'nombre': 'GALLEGO'}, {'especialidad': '010', 'nombre': 'GRIEGO'},
                   {'especialidad': '011', 'nombre': 'INGLES'}, {'especialidad': '012', 'nombre': 'ITALIANO'},
                   {'especialidad': '013', 'nombre': 'JAPONES'}, {'especialidad': '014', 'nombre': 'NEERLANDES'},
                   {'especialidad': '015', 'nombre': 'PORTUGUES'}, {'especialidad': '016', 'nombre': 'RUMANO'},
                   {'especialidad': '017', 'nombre': 'RUSO'}, {'especialidad': '018', 'nombre': 'VALENCIANO'},
                   {'especialidad': '019', 'nombre': 'FINES'}, {'especialidad': '020', 'nombre': 'SUECO'}],
          '0593': [{'especialidad': '001', 'nombre': 'ACORDEON'},
                   {'especialidad': '002', 'nombre': 'ARMONIA Y MELODIA ACOMPAÑADA'},
                   {'especialidad': '003', 'nombre': 'ARPA'}, {'especialidad': '006', 'nombre': 'CANTO'},
                   {'especialidad': '007', 'nombre': 'CARACTERIZACION'},
                   {'especialidad': '008', 'nombre': 'CLARINETE'}, {'especialidad': '009', 'nombre': 'CLAVE'},
                   {'especialidad': '011', 'nombre': 'COMPOSICION ELECTROACUSTICA'},
                   {'especialidad': '014', 'nombre': 'CONTRABAJO'},
                   {'especialidad': '015', 'nombre': 'CONTRAPUNTO Y FUGA'}, {'especialidad': '016', 'nombre': 'COROS'},
                   {'especialidad': '017', 'nombre': 'DANZA ESPAÑOLA'},
                   {'especialidad': '019', 'nombre': 'DICCION Y LECTURA EXPRESIVA'},
                   {'especialidad': '022', 'nombre': 'DIRECCION DE ESCENA'},
                   {'especialidad': '024', 'nombre': 'DRAMATURGIA'},
                   {'especialidad': '025', 'nombre': 'ESCENA LIRICA'},
                   {'especialidad': '026', 'nombre': 'ESCENOGRAFIA'}, {'especialidad': '027', 'nombre': 'ESGRIMA'},
                   {'especialidad': '029', 'nombre': 'EXPRESION CORPORAL'}, {'especialidad': '030', 'nombre': 'FAGOT'},
                   {'especialidad': '031', 'nombre': 'FLAUTA DE PICO'},
                   {'especialidad': '032', 'nombre': 'FLAUTA TRAVESERA'},
                   {'especialidad': '035', 'nombre': 'GUITARRA'},
                   {'especialidad': '036', 'nombre': 'GUITARRA FLAMENCA'},
                   {'especialidad': '037', 'nombre': 'HISTORIA DE LA CULTURA Y DEL ARTE'},
                   {'especialidad': '038', 'nombre': 'HISTORIA DE LA LITERATURA DRAMATICA'},
                   {'especialidad': '039', 'nombre': 'HISTORIA DE LA MUSICA'},
                   {'especialidad': '040', 'nombre': 'HISTORIA DEL ARTE'},
                   {'especialidad': '041', 'nombre': 'INICIACION MUSICAL'},
                   {'especialidad': '042', 'nombre': 'INSTRUMENTOS DE PULSO Y PUA'},
                   {'especialidad': '043', 'nombre': 'INTERPRETACION'},
                   {'especialidad': '044', 'nombre': 'LECTURA MUSICAL'},
                   {'especialidad': '045', 'nombre': 'LENGUA ALEMANA'},
                   {'especialidad': '046', 'nombre': 'LENGUA FRANCESA'},
                   {'especialidad': '047', 'nombre': 'LENGUA INGLESA'},
                   {'especialidad': '048', 'nombre': 'LENGUA ITALIANA'},
                   {'especialidad': '049', 'nombre': 'MIMO Y PANTOMIMA'},
                   {'especialidad': '050', 'nombre': 'MUSICA DE CAMARA'},
                   {'especialidad': '051', 'nombre': 'MUSICOLOGIA'}, {'especialidad': '052', 'nombre': 'OBOE'},
                   {'especialidad': '053', 'nombre': 'ORGANO'},
                   {'especialidad': '055', 'nombre': 'ORTOFONIA Y DICCION'},
                   {'especialidad': '056', 'nombre': 'PEDAGOGIA DEL TEATRO'},
                   {'especialidad': '058', 'nombre': 'PERCUSION'}, {'especialidad': '059', 'nombre': 'PIANO'},
                   {'especialidad': '060', 'nombre': 'PIANO APLICADO'},
                   {'especialidad': '062', 'nombre': 'REPERTORIO DE OPERA Y ORATORIO'},
                   {'especialidad': '064', 'nombre': 'REPERTORIO VOCAL ESTILISTICO'},
                   {'especialidad': '066', 'nombre': 'SAXOFON'},
                   {'especialidad': '067', 'nombre': 'SOCIOLOGIA DEL TEATRO'},
                   {'especialidad': '069', 'nombre': 'TEATRO INFANTIL'},
                   {'especialidad': '071', 'nombre': 'TECNICAS MUSICALES CONTEMPORANEAS'},
                   {'especialidad': '072', 'nombre': 'TROMBON'}, {'especialidad': '073', 'nombre': 'TROMBOM-TUBA'},
                   {'especialidad': '074', 'nombre': 'TROMPA'}, {'especialidad': '075', 'nombre': 'TROMPETA'},
                   {'especialidad': '076', 'nombre': 'TUBA'}, {'especialidad': '077', 'nombre': 'VIOLA'},
                   {'especialidad': '078', 'nombre': 'VIOLIN'}, {'especialidad': '080', 'nombre': 'TXISTU'},
                   {'especialidad': '081', 'nombre': 'BAJO ELECTRICO'},
                   {'especialidad': '082', 'nombre': 'BATERIA DE JAZZ'},
                   {'especialidad': '083', 'nombre': 'CANTE FLAMENCO'},
                   {'especialidad': '084', 'nombre': 'CANTO DE JAZZ'},
                   {'especialidad': '085', 'nombre': 'COMPOSICIÓN DE JAZZ'},
                   {'especialidad': '086', 'nombre': 'CONTRABAJO DE JAZZ'},
                   {'especialidad': '087', 'nombre': 'DULZAINA'},
                   {'especialidad': '088', 'nombre': 'FLABIOL  I TAMBORÍ'},
                   {'especialidad': '089', 'nombre': 'FLAMENCOLOGÍA'}, {'especialidad': '090', 'nombre': 'GAITA'},
                   {'especialidad': '091', 'nombre': 'GUITARRA ELÉCTRICA'},
                   {'especialidad': '092', 'nombre': 'INSTRUMENTOS DE CUERDA PULSADA DEL RENACIMIENTO Y BARROCO'},
                   {'especialidad': '093', 'nombre': 'INSTRUMENTOS DE PÚA'},
                   {'especialidad': '094', 'nombre': 'INSTRUMENTOS DE VIENTO DE JAZZ'},
                   {'especialidad': '095', 'nombre': 'INSTRUMENTOS HISTÓRICOS DE CUERDA FROTADA'},
                   {'especialidad': '096', 'nombre': 'INSTRUMENTOS HISTÓRICOS DE TECLA'},
                   {'especialidad': '097', 'nombre': 'INSTRUMENTOS HISTÓRICOS DE VIENTO'},
                   {'especialidad': '098', 'nombre': 'REPERTORIO CON PIANO PARA INSTRUMENTOS'},
                   {'especialidad': '099', 'nombre': 'TECLADOS/PIANO JAZZ'},
                   {'especialidad': '100', 'nombre': 'TECNOLOGÍA MUSICAL'},
                   {'especialidad': '101', 'nombre': 'TENORA I TIBLE'},
                   {'especialidad': '102', 'nombre': 'VIOLA DA GAMBA'},
                   {'especialidad': '103', 'nombre': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DEL BAILE FLAMENCO'},
                   {'especialidad': '104', 'nombre': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DE LA DANZA CLÁSICA'},
                   {'especialidad': '105', 'nombre': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DE LA DANZA CONTEMPORÁNEA'},
                   {'especialidad': '106', 'nombre': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DE LA DANZA ESPAÑOLA'},
                   {'especialidad': '107', 'nombre': 'CIENCIAS DE LA SALUD APLICADAS A LA DANZA'},
                   {'especialidad': '108', 'nombre': 'COMPOSICIÓN COREOGRÁFICA'},
                   {'especialidad': '109', 'nombre': 'DANZA CONTEMPORÁNEA'},
                   {'especialidad': '110', 'nombre': 'DANZA EDUCATIVA'},
                   {'especialidad': '111', 'nombre': 'ESCENIFICACIÓN APLICADA A LA DANZA'},
                   {'especialidad': '112', 'nombre': 'HISTORIA DE LA DANZA'},
                   {'especialidad': '113', 'nombre': 'PSICOPEDAGOGÍA Y GESTIÓN EDUCATIVA'},
                   {'especialidad': '114', 'nombre': 'TECNOLOGÍAS APLICADAS A LA DANZA'},
                   {'especialidad': '115', 'nombre': 'PRODUCCIÓN Y GESTIÓN DE MÚSICA Y ARTES ESCÉNICAS'},
                   {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'}],
          '0594': [{'especialidad': '012', 'nombre': 'COREOGRAFIA'},
                   {'especialidad': '017', 'nombre': 'ELEMENTOS DE ACUSTICA'},
                   {'especialidad': '018', 'nombre': 'ESCENA LIRICA'},
                   {'especialidad': '049', 'nombre': 'RITMICA Y PALEOGRAFIA'},
                   {'especialidad': '053', 'nombre': 'SOLFEO Y TEORIA DE LA MUSICA'},
                   {'especialidad': '078', 'nombre': 'FOLKLORE'},
                   {'especialidad': '083', 'nombre': 'PEDAGOGIA MUSICAL'},
                   {'especialidad': '085', 'nombre': 'HISTORIA DEL TEATRO'},
                   {'especialidad': '092', 'nombre': 'TXISTU'}, {'especialidad': '401', 'nombre': 'ACORDEON'},
                   {'especialidad': '402', 'nombre': 'ARPA'}, {'especialidad': '403', 'nombre': 'CANTO'},
                   {'especialidad': '404', 'nombre': 'CLARINETE'}, {'especialidad': '405', 'nombre': 'CLAVE'},
                   {'especialidad': '406', 'nombre': 'CONTRABAJO'}, {'especialidad': '407', 'nombre': 'CORO'},
                   {'especialidad': '408', 'nombre': 'FAGOT'}, {'especialidad': '409', 'nombre': 'FLABIOL I TAMBORI'},
                   {'especialidad': '410', 'nombre': 'FLAUTA TRAVESERA'},
                   {'especialidad': '411', 'nombre': 'FLAUTA DE PICO'},
                   {'especialidad': '412', 'nombre': 'FUNDAMENTOS DE COMPOSICION'},
                   {'especialidad': '414', 'nombre': 'GUITARRA'},
                   {'especialidad': '415', 'nombre': 'GUITARRA FLAMENCA'},
                   {'especialidad': '416', 'nombre': 'HISTORIA DE LA MUSICA'},
                   {'especialidad': '418', 'nombre': 'INSTRUMENTOS DE PUA'}, {'especialidad': '419', 'nombre': 'OBOE'},
                   {'especialidad': '420', 'nombre': 'ORGANO'}, {'especialidad': '421', 'nombre': 'ORQUESTA'},
                   {'especialidad': '422', 'nombre': 'PERCUSION'}, {'especialidad': '423', 'nombre': 'PIANO'},
                   {'especialidad': '424', 'nombre': 'SAXOFON'}, {'especialidad': '425', 'nombre': 'TENORA Y TIBLE'},
                   {'especialidad': '426', 'nombre': 'TROMBON'}, {'especialidad': '427', 'nombre': 'TROMPA'},
                   {'especialidad': '428', 'nombre': 'TROMPETA'}, {'especialidad': '429', 'nombre': 'TUBA'},
                   {'especialidad': '430', 'nombre': 'TXISTU'}, {'especialidad': '431', 'nombre': 'VIOLA'},
                   {'especialidad': '432', 'nombre': 'VIOLA DA GAMBA'}, {'especialidad': '433', 'nombre': 'VIOLIN'},
                   {'especialidad': '434', 'nombre': 'VIOLONCHELLO'},
                   {'especialidad': '435', 'nombre': 'DANZA ESPAÑOLA'},
                   {'especialidad': '436', 'nombre': 'DANZA CLASICA'},
                   {'especialidad': '437', 'nombre': 'DANZA CONTEMPORANEA'},
                   {'especialidad': '438', 'nombre': 'FLAMENCO'},
                   {'especialidad': '439', 'nombre': 'HISTORIA DE LA DANZA'},
                   {'especialidad': '440', 'nombre': 'ACROBACIA'},
                   {'especialidad': '441', 'nombre': 'CANTO APLICADO AL ARTE DRAMATICO'},
                   {'especialidad': '442', 'nombre': 'CARACTERIZACION E INDUMENTARIA'},
                   {'especialidad': '443', 'nombre': 'DANZA APLICADA AL ARTE DRAMATICO'},
                   {'especialidad': '444', 'nombre': 'DICCION Y EXPRESION ORAL'},
                   {'especialidad': '445', 'nombre': 'DIRECCION ESCENICA'},
                   {'especialidad': '446', 'nombre': 'DRAMATURGIA'}, {'especialidad': '447', 'nombre': 'ESGRIMA'},
                   {'especialidad': '448', 'nombre': 'ESPACIO ESCENICO'},
                   {'especialidad': '449', 'nombre': 'EXPRESION CORPORAL'},
                   {'especialidad': '450', 'nombre': 'ILUMINACION'},
                   {'especialidad': '451', 'nombre': 'INTERPRETACION'},
                   {'especialidad': '452', 'nombre': 'INTERPRETACION CON OBJETOS'},
                   {'especialidad': '453', 'nombre': 'INTERPRETACION EN EL MUSICAL'},
                   {'especialidad': '454', 'nombre': 'INTERPRETACION EN EL TEATRO DEL GESTO'},
                   {'especialidad': '455', 'nombre': 'LITERATURA DRAMATICA'},
                   {'especialidad': '456', 'nombre': 'TECNICAS ESCENICAS'},
                   {'especialidad': '457', 'nombre': 'TECNICAS GRAFICAS'},
                   {'especialidad': '458', 'nombre': 'TEORIA E HISTORIA DEL ARTE'},
                   {'especialidad': '459', 'nombre': 'TEORIA TEATRAL'},
                   {'especialidad': '460', 'nombre': 'LENGUAJE MUSICAL'},
                   {'especialidad': '461', 'nombre': 'BAJO ELÉCTRICO'}, {'especialidad': '462', 'nombre': 'DULZAINA'},
                   {'especialidad': '463', 'nombre': 'GUITARRA ELÉCTRICA'},
                   {'especialidad': '464', 'nombre': 'REPERTORIO CON PIANO PARA DANZA'},
                   {'especialidad': '465', 'nombre': 'CANTE FLAMENCO'},
                   {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'}],
          '0595': [{'especialidad': '001', 'nombre': 'ADORNO Y FIGURA'},
                   {'especialidad': '002', 'nombre': 'ALFARERIA'}, {'especialidad': '003', 'nombre': 'ARQUEOLOGIA'},
                   {'especialidad': '004', 'nombre': 'COMPOSICION ORNAMENTAL'},
                   {'especialidad': '005', 'nombre': 'DECORACION SOBRE PASTAS CERAMICAS'}, {'especialidad': '006',
                                                                                            'nombre': 'DERECHO USUAL Y NOCIONES CONTABILIDAD Y CORRESPONDENCIA COMERCIAL'},
                   {'especialidad': '008', 'nombre': 'DIBUJO ARQUEOLOGICO'},
                   {'especialidad': '009', 'nombre': 'DIBUJO ARTISTICO'},
                   {'especialidad': '010', 'nombre': 'DIBUJO LINEAL'},
                   {'especialidad': '011', 'nombre': 'FISICA Y QUIMICA APLICADAS A LA RESTAURACION'},
                   {'especialidad': '013', 'nombre': 'HISTORIA DEL ARTE'},
                   {'especialidad': '014', 'nombre': 'HISTORIA Y TECNICAS DEL LIBRO'},
                   {'especialidad': '015', 'nombre': 'MANUFACTURA CERAMICA'},
                   {'especialidad': '016', 'nombre': 'MATEMATICAS'},
                   {'especialidad': '017', 'nombre': 'MATERIAS PRIMAS CERAMICAS'},
                   {'especialidad': '018', 'nombre': 'MODELADO Y VACIADO'},
                   {'especialidad': '019', 'nombre': 'MODELAJE DE FIGURAS'},
                   {'especialidad': '020', 'nombre': 'MODELOS DE VAJILLERIA EN ESCAYOLA'},
                   {'especialidad': '021', 'nombre': 'PROCEDIMIENTOS DE ILUSTRACION DEL LIBRO'},
                   {'especialidad': '022', 'nombre': 'PROYECTOS DE ARTE DECORATIVO'},
                   {'especialidad': '023', 'nombre': 'QUIMICA APLICADA A LA CERAMICA'},
                   {'especialidad': '024', 'nombre': 'RESTAURACION DEL LIBRO'},
                   {'especialidad': '025', 'nombre': 'RESTAURACION DE OBRAS ESCULTORICAS'},
                   {'especialidad': '026', 'nombre': 'RESTAURACION Y TECNICAS ARQUEOLOGICAS'},
                   {'especialidad': '027', 'nombre': 'RESTAURACION Y TECNICAS PICTORICAS'},
                   {'especialidad': '028', 'nombre': 'SERIGRAFIA'}, {'especialidad': '029', 'nombre': 'TAQUIGRAFIA'},
                   {'especialidad': '030', 'nombre': 'TAQUIMECANOGRAFIA'},
                   {'especialidad': '031', 'nombre': 'TECNICA SEGOVIANA'},
                   {'especialidad': '032', 'nombre': 'TECNICA TALAVERANA'},
                   {'especialidad': '033', 'nombre': 'TECNICAS AUDIOVISUALES'},
                   {'especialidad': '034', 'nombre': 'TECNICAS DE DISEÑO GRAFICO'},
                   {'especialidad': '035', 'nombre': 'TECNICAS GRAFICAS INDUSTRIALES'},
                   {'especialidad': '036', 'nombre': 'TECNOLOGIA QUIMICA Y TEXTIL'},
                   {'especialidad': '037', 'nombre': 'TEORIA Y PRACTICA DEL DISEÑO'},
                   {'especialidad': '038', 'nombre': 'TECNOLOGIA Y PROYECTOS DE BISUTERIA Y JOYERIA'},
                   {'especialidad': '039', 'nombre': 'ELEMENTOS CONSTRUCTIVOS'},
                   {'especialidad': '040', 'nombre': 'CONOCIMIENTO DE MATERIALES'},
                   {'especialidad': '048', 'nombre': 'PREPARACION ELEMENTAL CERAMICA'},
                   {'especialidad': '049', 'nombre': 'ANALISIS QUIMICOS DE CERAMICA'},
                   {'especialidad': '051', 'nombre': 'MATERIALES Y ELEMENTOS DE CONSTRUCCION'},
                   {'especialidad': '052', 'nombre': 'DECORACION ELEMENTAL CERAMICA'},
                   {'especialidad': '054', 'nombre': 'PREPARACION CERAMICA'},
                   {'especialidad': '056', 'nombre': 'COLORIDO CERAMICO'},
                   {'especialidad': '057', 'nombre': 'CULTURA GENERAL CERAMICA'},
                   {'especialidad': '065', 'nombre': 'TEORIA Y PRACTICA DE LA FOTOGRAFIA'},
                   {'especialidad': '066', 'nombre': 'ANALISIS DE FORMA Y COLOR'},
                   {'especialidad': '068', 'nombre': 'CERAMICA APLICADA A LA DECORACION'},
                   {'especialidad': '069', 'nombre': 'COLORIDO Y PROCEDIMIENTOS PICTÓRICOS'},
                   {'especialidad': '070', 'nombre': 'DIBUJO Y TECNICAS PICTORICAS'},
                   {'especialidad': '071', 'nombre': 'DISEÑO INDUSTRIAL CERAMICO'},
                   {'especialidad': '072', 'nombre': 'ENCUADERNACION'},
                   {'especialidad': '074', 'nombre': 'FOTOGRAFÍA'},
                   {'especialidad': '075', 'nombre': 'FOTOGRAFIA APLICADA A LA RESTAURACION'},
                   {'especialidad': '080', 'nombre': 'TECNICAS DE COLORIDO APLICADO A LA CERAMICA'},
                   {'especialidad': '083', 'nombre': 'DISEÑO ASISTIDO POR ORDENADOR'},
                   {'especialidad': '084', 'nombre': 'TECNICAS MURALES'},
                   {'especialidad': '085', 'nombre': 'RESTAURACION ARQUEOLOGICA'},
                   {'especialidad': '501', 'nombre': 'CERÁMICA'},
                   {'especialidad': '502', 'nombre': 'CONSERVACIÓN Y RESTAURACIÓN DE MATERIALES ARQUEOLÓGICOS'},
                   {'especialidad': '503', 'nombre': 'CONSERVACIÓN Y RESTAURACIÓN DE OBRAS ESCULTÓRICAS'},
                   {'especialidad': '504', 'nombre': 'CONSERVACIÓN Y RESTAURACIÓN DE OBRAS PICTÓRICAS'},
                   {'especialidad': '505', 'nombre': 'CONSERVACIÓN Y RESTAURACIÓN DE TEXTILES'},
                   {'especialidad': '506', 'nombre': 'CONSERVACIÓN Y RESTAURACIÓN DEL DOCUMENTO GRAFICO'},
                   {'especialidad': '507', 'nombre': 'DIBUJO ARTÍSTICO Y COLOR'},
                   {'especialidad': '508', 'nombre': 'DIBUJO TÉCNICO'},
                   {'especialidad': '509', 'nombre': 'DISEÑO DE INTERIORES'},
                   {'especialidad': '510', 'nombre': 'DISEÑO DE MODA'},
                   {'especialidad': '511', 'nombre': 'DISEÑO DE PRODUCTO'},
                   {'especialidad': '512', 'nombre': 'DISEÑO GRAFICO'},
                   {'especialidad': '513', 'nombre': 'DISEÑO TEXTIL'},
                   {'especialidad': '514', 'nombre': 'EDICIÓN DE ARTE'},
                   {'especialidad': '515', 'nombre': 'FOTOGRAFÍA'},
                   {'especialidad': '516', 'nombre': 'HISTORIA DEL ARTE'},
                   {'especialidad': '517', 'nombre': 'JOYERÍA Y ORFEBRERÍA'},
                   {'especialidad': '518', 'nombre': 'MATERIALES Y TECNOLOGÍA: CERAMICA Y VIDRIO'},
                   {'especialidad': '519', 'nombre': 'MATERIALES Y TECNOLOGÍA: CONSERVACION Y RESTAURACION'},
                   {'especialidad': '520', 'nombre': 'MATERIALES Y TECNOLOGÍA: DISEÑO'},
                   {'especialidad': '521', 'nombre': 'MEDIOS AUDIOVISUALES'},
                   {'especialidad': '522', 'nombre': 'MEDIOS INFORMÁTICOS'},
                   {'especialidad': '523', 'nombre': 'ORGANIZACIÓN INDUSTRIAL Y LEGISLACIÓN'},
                   {'especialidad': '524', 'nombre': 'VIDRIO'}, {'especialidad': '525', 'nombre': 'VOLUMEN'},
                   {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'}],
          '0596': [{'especialidad': '001', 'nombre': 'ALFARERIA'}, {'especialidad': '002', 'nombre': 'ALFOMBRAS'},
                   {'especialidad': '004', 'nombre': 'BORDADOS Y ENCAJES'},
                   {'especialidad': '005', 'nombre': 'CALCOGRAFIA Y XILOGRAFIA'},
                   {'especialidad': '006', 'nombre': 'CERAMICA ARTISTICA'},
                   {'especialidad': '007', 'nombre': 'CORTE Y CONFECCION'},
                   {'especialidad': '008', 'nombre': 'DECORACION'},
                   {'especialidad': '009', 'nombre': 'DECORACION CERAMICA'},
                   {'especialidad': '010', 'nombre': 'DECORACION SOBRE LOZA'},
                   {'especialidad': '011', 'nombre': 'DECORACION SOBRE PORCELANA'},
                   {'especialidad': '012', 'nombre': 'DELINEACION'},
                   {'especialidad': '013', 'nombre': 'DIBUJO PUBLICITARIO'},
                   {'especialidad': '014', 'nombre': 'DISEÑO INDUSTRIAL'},
                   {'especialidad': '015', 'nombre': 'DISEÑO DE FIGURINES'},
                   {'especialidad': '016', 'nombre': 'DORADO Y POLICROMIA'},
                   {'especialidad': '017', 'nombre': 'EBANISTERIA'},
                   {'especialidad': '018', 'nombre': 'EBANISTERIA Y MAQUETERIA'},
                   {'especialidad': '019', 'nombre': 'ENCUADERNACION'},
                   {'especialidad': '020', 'nombre': 'ESGRAFIADO'}, {'especialidad': '021', 'nombre': 'ESMALTES'},
                   {'especialidad': '022', 'nombre': 'ESTAMPADO TEXTIL'},
                   {'especialidad': '023', 'nombre': 'FORJA ARTISTICA'},
                   {'especialidad': '024', 'nombre': 'FORJA Y CERRAJERIA'},
                   {'especialidad': '025', 'nombre': 'FOTOGRABADO'},
                   {'especialidad': '026', 'nombre': 'FOTOGRABADO Y TIPOGRAFIA'},
                   {'especialidad': '027', 'nombre': 'FOTOGRAFIA ARTISTICA'},
                   {'especialidad': '028', 'nombre': 'FOTOGRAFIA Y PROCESO DE REPRODUCCION'},
                   {'especialidad': '029', 'nombre': 'GRABADO'}, {'especialidad': '031', 'nombre': 'HORNOS'},
                   {'especialidad': '032', 'nombre': 'INVESTIGACION DE MATERIAS PRIMAS CERAMICAS'},
                   {'especialidad': '033', 'nombre': 'JOYERIA'},
                   {'especialidad': '035', 'nombre': 'LABRADO Y REPUJADO EN CUERO'},
                   {'especialidad': '036', 'nombre': 'LITOGRAFIA'},
                   {'especialidad': '038', 'nombre': 'LOZA Y PORCELANA'},
                   {'especialidad': '039', 'nombre': 'MANUFACTURA CERAMICA'},
                   {'especialidad': '040', 'nombre': 'MATRICERIA'},
                   {'especialidad': '041', 'nombre': 'METALISTERIA ARTISTICA'},
                   {'especialidad': '043', 'nombre': 'MODELISMO Y MAQUETISMO'},
                   {'especialidad': '044', 'nombre': 'MOLDES Y REPRODUCCIONES'},
                   {'especialidad': '045', 'nombre': 'MOSAICOS ROMANOS'},
                   {'especialidad': '046', 'nombre': 'MUÑEQUERIA ARTISTICA'},
                   {'especialidad': '047', 'nombre': 'ORFEBRERIA'},
                   {'especialidad': '048', 'nombre': 'PASTAS Y HORNOS'},
                   {'especialidad': '049', 'nombre': 'PATRONAJE, ESCALADO Y TECNICAS DE CONFECCION'},
                   {'especialidad': '050', 'nombre': 'QUIMICA APLICADA A LA CERAMICA'},
                   {'especialidad': '051', 'nombre': 'REPUJADO EN CUERO'},
                   {'especialidad': '052', 'nombre': 'REPUJADO EN METAL'},
                   {'especialidad': '053', 'nombre': 'RESTAURACION DE DIBUJOS Y GRABADOS'},
                   {'especialidad': '054', 'nombre': 'RESTAURACION DE ENCUADERNACIONES'},
                   {'especialidad': '055', 'nombre': 'RESTAURACION DE MANUSCRITOS E IMPRESOS'},
                   {'especialidad': '056', 'nombre': 'RESTAURACION DE TAPICES'},
                   {'especialidad': '057', 'nombre': 'MODELISMO INDUSTRIAL'},
                   {'especialidad': '058', 'nombre': 'TALLA DE MADERA'},
                   {'especialidad': '059', 'nombre': 'TALLA EN PIEDRA'},
                   {'especialidad': '060', 'nombre': 'TALLA DE PIEDRA Y MADERA'},
                   {'especialidad': '061', 'nombre': 'TAPICES Y ALFOMBRAS'},
                   {'especialidad': '062', 'nombre': 'TAQUIMECANOGRAFIA'},
                   {'especialidad': '063', 'nombre': 'TECNICAS DE JOYERIA'},
                   {'especialidad': '064', 'nombre': 'TEXTILES ARTISTICOS'},
                   {'especialidad': '065', 'nombre': 'VACIADO Y MODELADO'},
                   {'especialidad': '066', 'nombre': 'VIDRIERAS ARTISTICAS'},
                   {'especialidad': '068', 'nombre': 'INICIACION A LA RESTAURACION'},
                   {'especialidad': '069', 'nombre': 'RESTAURACION CERAMICA'},
                   {'especialidad': '070', 'nombre': 'TECNICAS DE DISEÑO INDUSTRIAL'},
                   {'especialidad': '071', 'nombre': 'TIPOGRAFÍA'}, {'especialidad': '072', 'nombre': 'VACIADO'},
                   {'especialidad': '074', 'nombre': 'TALLA ORNAMENTAL'},
                   {'especialidad': '081', 'nombre': 'ABANIQUERÍA'},
                   {'especialidad': '087', 'nombre': 'ARTESANIA CANARIA'},
                   {'especialidad': '088', 'nombre': 'ARTES GRAFICAS'},
                   {'especialidad': '091', 'nombre': 'DIBUJOS ANIMADOS'},
                   {'especialidad': '092', 'nombre': 'DIBUJO DEL MUEBLE'},
                   {'especialidad': '093', 'nombre': 'FIGURINES'},
                   {'especialidad': '094', 'nombre': 'REPUJADO EN CUERO Y METAL'},
                   {'especialidad': '095', 'nombre': 'RESTAURACION'}, {'especialidad': '097', 'nombre': 'SERIGRAFIA'},
                   {'especialidad': '098', 'nombre': 'MOLDEO Y MONTAJE DE PORCELANA'},
                   {'especialidad': '099', 'nombre': 'FORJA Y FUNDICION'},
                   {'especialidad': '101', 'nombre': 'MARIONETAS'},
                   {'especialidad': '102', 'nombre': 'REFLEJOS METALICOS'},
                   {'especialidad': '104', 'nombre': 'TAQUIGRAFIA'},
                   {'especialidad': '107', 'nombre': 'DISEÑO GRAFICO ASISTIDO POR ORDENADOR'},
                   {'especialidad': '108', 'nombre': 'REPRODUCCION E IMPRESION'},
                   {'especialidad': '109', 'nombre': 'CERRAJERIA Y FORJA'},
                   {'especialidad': '110', 'nombre': 'CONSTRUCCIONES NAVALES'},
                   {'especialidad': '115', 'nombre': 'IMAGINERIA CASTELLANA'},
                   {'especialidad': '117', 'nombre': 'METALISTERIA (DAMASQUINADO)'},
                   {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'},
                   {'especialidad': '601', 'nombre': 'ARTESANIA Y ORNAMENTACION CON ELEMENTOS VEGETALES'},
                   {'especialidad': '602', 'nombre': 'BORDADOS Y ENCAJES'},
                   {'especialidad': '603', 'nombre': 'COMPLEMENTOS Y ACCESORIOS'},
                   {'especialidad': '604', 'nombre': 'DORADO Y POLICROMIA'},
                   {'especialidad': '605', 'nombre': 'EBANISTERIA ARTISTICA'},
                   {'especialidad': '606', 'nombre': 'ENCUADERNACION ARTISTICA'},
                   {'especialidad': '607', 'nombre': 'ESMALTES'},
                   {'especialidad': '608', 'nombre': 'FOTOGRAFIA Y PROCESOS DE REPRODUCCION'},
                   {'especialidad': '609', 'nombre': 'MODELISMO Y MAQUETISMO'},
                   {'especialidad': '610', 'nombre': 'MOLDES Y REPRODUCCIONES'},
                   {'especialidad': '611', 'nombre': 'MUSIVARIA'},
                   {'especialidad': '612', 'nombre': 'TALLA EN PIEDRA Y MADERA'},
                   {'especialidad': '613', 'nombre': 'TECNICAS CERAMICAS'},
                   {'especialidad': '614', 'nombre': 'TECNICAS DE GRABADO Y ESTAMPACION'},
                   {'especialidad': '615', 'nombre': 'TECNICAS DE JOYERIA Y BISUTERIA'},
                   {'especialidad': '616', 'nombre': 'TECNICAS DE ORFEBRERIA Y PLATERIA'},
                   {'especialidad': '617', 'nombre': 'TECNICAS DE PATRONAJE Y CONFECCION'},
                   {'especialidad': '618', 'nombre': 'TECNICAS DEL METAL'},
                   {'especialidad': '619', 'nombre': 'TECNICAS MURALES'},
                   {'especialidad': '620', 'nombre': 'TECNICAS TEXTILES'},
                   {'especialidad': '621', 'nombre': 'TECNICAS VIDRIERAS'}],
          '0597': [{'especialidad': '041', 'nombre': 'COMPENSATORIA (A.D.)'},
                   {'especialidad': 'AL', 'nombre': 'AUDICION Y LENGUAJE'},
                   {'especialidad': 'AS', 'nombre': 'AUDICION Y LENGUAJE'},
                   {'especialidad': 'CK', 'nombre': 'COMPENSATORIA ( SEC. )'},
                   {'especialidad': 'CN', 'nombre': 'CIENCIAS DE LA NATURALEZA'},
                   {'especialidad': 'CO', 'nombre': 'EDUCACION COMPENSATORIA'},
                   {'especialidad': 'CS', 'nombre': 'CIENCIAS SOCIALES'},
                   {'especialidad': 'EA', 'nombre': 'EDUCACIÓN DE ADULTOS'},
                   {'especialidad': 'EAI', 'nombre': 'INGLES ( ED. ADULTOS )'},
                   {'especialidad': 'EF', 'nombre': 'EDUCACION FISICA'},
                   {'especialidad': 'EI', 'nombre': 'EDUCACION INFANTIL'}, {'especialidad': 'EU', 'nombre': 'EUSKERA'},
                   {'especialidad': 'FA', 'nombre': 'LENGUA EXTRANJERA: ALEMÁN'},
                   {'especialidad': 'FB', 'nombre': 'CATALAN (BALEARES)'}, {'especialidad': 'FC', 'nombre': 'CATALAN'},
                   {'especialidad': 'FF', 'nombre': 'LENGUA EXTRANJERA: FRANCÉS'},
                   {'especialidad': 'FG', 'nombre': 'GALLEGO'},
                   {'especialidad': 'FI', 'nombre': 'LENGUA EXTRANJERA: INGLÉS'},
                   {'especialidad': 'FL', 'nombre': 'FILOLOGIA: LENGUA CASTELLANA'},
                   {'especialidad': 'FN', 'nombre': 'VASCUENCE (NAVARRA)'},
                   {'especialidad': 'FR', 'nombre': 'LENGUA EXTRANJERA: FRANCES'},
                   {'especialidad': 'FS', 'nombre': 'EDUCACION FISICA'},
                   {'especialidad': 'FV', 'nombre': 'VALENCIANO'},
                   {'especialidad': 'GH', 'nombre': 'GEOGRAFIA E HISTORIA'},
                   {'especialidad': 'GS', 'nombre': 'GARANTIA SOCIAL'},
                   {'especialidad': 'LL', 'nombre': 'LENGUA Y LITERATURA'},
                   {'especialidad': 'MA', 'nombre': 'MATEMATICAS'},
                   {'especialidad': 'MC', 'nombre': 'MATEMATICAS Y CIENCIAS DE LA NATURALEZA'},
                   {'especialidad': 'MS', 'nombre': 'MUSICA (SEC.)'}, {'especialidad': 'MU', 'nombre': 'MUSICA'},
                   {'especialidad': 'PCP', 'nombre': 'P.C.P.I.'}, {'especialidad': 'PRI', 'nombre': 'PRIMARIA'},
                   {'especialidad': 'PS', 'nombre': 'PEDAGOGIA TERAPEUTICA (SEC.)'},
                   {'especialidad': 'PT', 'nombre': 'PEDAGOGIA TERAPEUTICA'}],
          '0598': [{'especialidad': '001', 'nombre': 'COCINA Y PASTELERIA'},
                   {'especialidad': '002', 'nombre': 'ESTETICA'},
                   {'especialidad': '003', 'nombre': 'FABRICACION E INSTALACION DE CARPINTERIA Y MUEBLE'},
                   {'especialidad': '004', 'nombre': 'MANTENIMIENTO DE VEHICULOS'},
                   {'especialidad': '005', 'nombre': 'MECANIZADO Y MANTENIMIENTO DE MAQUINAS'},
                   {'especialidad': '006', 'nombre': 'PATRONAJE Y CONFECCION'},
                   {'especialidad': '007', 'nombre': 'PELUQUERIA'},
                   {'especialidad': '008', 'nombre': 'PRODUCCION EN ARTES GRAFICAS'},
                   {'especialidad': '009', 'nombre': 'SERVICIOS DE RESTAURACION'},
                   {'especialidad': '010', 'nombre': 'SOLDADURA'}]}

CUERPOS = [{'codigo': '0590', 'nombre': 'PROFESORES DE ENSEÑANZA SECUNDARIA'},
           {'codigo': '0591', 'nombre': 'PROFESORES TÉCNICOS DE FORMACIÓN PROFESIONAL'},
           {'codigo': '0592', 'nombre': 'PROFESORES DE ESCUELAS OFICIALES DE IDIOMAS'},
           {'codigo': '0593', 'nombre': 'CATEDRÁTICOS DE MÚSICA Y ARTES ESCÉNICAS'},
           {'codigo': '0594', 'nombre': 'PROFESORES DE MÚSICA Y ARTES ESCÉNICAS'},
           {'codigo': '0595', 'nombre': 'PROFESORES DE ARTES PLÁSTICAS Y DISEÑO'},
           {'codigo': '0596', 'nombre': 'MAESTROS DE TALLER DE ARTES PLÁSTICAS Y DISEÑO'},
           {'codigo': '0597', 'nombre': 'MAESTROS'},
           {'codigo': '0598', 'nombre': 'PROFESORES ESPECIALISTAS EN SECTORES SINGULARES DE F. PROFES'}]

ESPECS = {'0590': {'001': 'FILOSOFIA', '002': 'GRIEGO',
                       '003': 'LATIN',
                       '004': 'LENGUA CASTELLANA Y LITERATURA',
                       '005': 'GEOGRAFIA E HISTORIA',
                       '006': 'MATEMATICAS',
                       '007': 'FISICA Y QUIMICA',
                       '008': 'BIOLOGIA Y GEOLOGIA',
                       '009': 'DIBUJO', '010': 'FRANCES',
                       '011': 'INGLES', '012': 'ALEMAN',
                       '013': 'ITALIANO',
                       '014': 'LENGUA Y LITERATURA CATALANAS (ISLAS BALEARES)',
                       '015': 'PORTUGUES', '016': 'MUSICA',
                       '017': 'EDUCACION FISICA',
                       '018': 'ORIENTACIÓN EDUCATIVA',
                       '019': 'TECNOLOGIA',
                       '039': 'TECNOLOGIA MINERA',
                       '051': 'LENGUA CATALANA Y LITERATURA',
                       '052': 'LENGUA Y LITERATURA VASCA',
                       '053': 'LENGUA Y LITERATURA GALLEGA',
                       '055': 'EDUCADORES (C.E.I.S.)',
                       '056': 'LENGUA Y LITERATURA VALENCIANA',
                       '057': 'LENGUA Y LITERATURA VASCA (NAVARRA)',
                       '058': 'APOYO AL AREA DE LENGUA Y CIENCIAS SOCIALES',
                       '059': 'APOYO AL AREA DE CIENCIAS O TECNOLOGIA',
                       '061': 'ECONOMIA', '062': 'LENGUA ARANESA',
                       '101': 'ADMINISTRACION DE EMPRESAS',
                       '102': 'ANALISIS Y QUIMICA INDUSTRIAL',
                       '103': 'ASESORIA Y PROCESOS DE IMAGEN PERSONAL',
                       '104': 'CONSTRUCCIONES CIVILES Y EDIFICACION',
                       '105': 'FORMACION Y ORIENTACION LABORAL',
                       '106': 'HOSTELERIA Y TURISMO',
                       '107': 'INFORMATICA',
                       '108': 'INTERVENCION SOCIOCOMUNITARIA',
                       '109': 'NAVEGACION E INSTALACIONES MARINAS',
                       '110': 'ORGANIZACION Y GESTION COMERCIAL',
                       '111': 'ORGANIZACION Y PROCESOS DE MANTENIMIENTO DE VEHICULOS',
                       '112': 'ORGANIZACION Y PROYECTOS DE FABRICACION MECANICA',
                       '113': 'ORGANIZACION Y PROYECTOS DE SISTEMAS ENERGETICOS',
                       '114': 'PROCESOS DE CULTIVO ACUICOLA',
                       '115': 'PROCESOS DE PRODUCCION AGRARIA',
                       '116': 'PROCESOS EN LA INDUSTRIA ALIMENTARIA',
                       '117': 'PROCESOS DIAGNOSTICOS CLINICOS Y PRODUCTOS ORTOPROTESICOS',
                       '118': 'PROCESOS SANITARIOS',
                       '119': 'PROCESOS Y MEDIOS DE COMUNICACION',
                       '120': 'PROCESOS Y PRODUCTOS DE TEXTIL, CONFECCION Y PIEL',
                       '121': 'PROCESOS Y PRODUCTOS DE VIDRIO Y CERAMICA',
                       '122': 'PROCESOS Y PRODUCTOS EN ARTES GRAFICAS',
                       '123': 'PROCESOS Y PRODUCTOS EN MADERA Y MUEBLE',
                       '124': 'SISTEMAS ELECTRONICOS',
                       '125': 'SISTEMAS ELECTROTECNICOS Y AUTOMATICOS',
                       '201': 'COCINA Y PASTELERIA',
                       '203': 'ESTETICA',
                       '204': 'FABRICACION E INSTALACION DE CARPINTERIA Y MUEBLE',
                       '205': 'INSTALACION Y MANTENIMIENTO DE EQUIPOS TERMICOS Y DE FLUIDOS',
                       '206': 'INSTALACIONES ELECTROTECNICAS',
                       '207': 'INSTALACIONES Y EQUIPOS DE CRIA Y CULTIVO',
                       '208': 'LABORATORIO',
                       '209': 'MANTENIMIENTO DE VEHICULOS',
                       '210': 'MAQUINAS, SERVICIOS Y PRODUCCION',
                       '211': 'MECANIZADO Y MANTENIMIENTO DE MAQUINAS',
                       '212': 'OFICINA DE PROYECTOS DE CONSTRUCCION',
                       '213': 'OFICINA DE PROYECTOS DE FABRICACION MECANICA',
                       '214': 'OPERACIONES Y EQUIPOS DE ELABORACION DE PRODUCTOS ALIMENTARIOS',
                       '215': 'OPERACIONES DE PROCESOS',
                       '216': 'OPERACIONES Y EQUIPOS DE PRODUCCION AGRARIA',
                       '217': 'PATRONAJE Y CONFECCION',
                       '218': 'PELUQUERIA',
                       '219': 'PROCEDIMIENTOS DE DIAGNOSTICO CLINICO Y ORTOPROTESICO',
                       '220': 'PROCEDIMIENTOS SANITARIOS Y ASISTENCIALES',
                       '221': 'PROCESOS COMERCIALES',
                       '222': 'PROCESOS DE GESTION ADMINISTRATIVA',
                       '223': 'PRODUCCION EN ARTES GRAFICAS',
                       '224': 'PRODUCCION TEXTIL Y TRATAMIENTOS FISICO-QUIMICOS',
                       '225': 'SERVICIOS A LA COMUNIDAD',
                       '226': 'SERVICIOS DE RESTAURACION',
                       '227': 'SISTEMAS Y APLICACIONES INFORMATICAS',
                       '228': 'SOLDADURA',
                       '229': 'TECNICAS Y PROCEDIMIENTOS DE IMAGEN Y SONIDO',
                       '231': 'EQUIPOS ELECTRONICOS',
                       '600': 'INSPECCION EDUCATIVA',
                       '803': 'CULTURA CLASICA',
                       '810': 'AMBITO DE COMUNICACION: FRANCES',
                       '811': 'AMBITO DE COMUNICACION: INGLES',
                       '812': 'AMBITO DE COMUNICACION: LENGUA CASTELLANA',
                       '813': 'AMBITO DE COMUNICACION: EUSKERA',
                       '814': 'AMBITO DE CONOCIMIENTO SOCIAL',
                       '815': 'AMBITO CIENTIFICO-TECNOLOGICO',
                       '905': 'CIENCIAS DE LA NATURALEZA'},
              '0591': {'016': 'PRACTICAS DE MINERIA',
                       '021': 'TALLER DE VIDRIO Y CERAMICA',
                       '025': 'ACTIVIDADES (C.E.I.S.)',
                       '026': 'APOYO AL AREA PRACTICA',
                       '201': 'COCINA Y PASTELERIA',
                       '202': 'EQUIPOS ELECTRONICOS',
                       '203': 'ESTETICA',
                       '204': 'FABRICACION E INSTALACION DE CARPINTERIA Y MUEBLE',
                       '205': 'INSTALACION Y MANTENIMIENTO DE EQUIPOS TERMICOS Y DE FLUIDOS',
                       '206': 'INSTALACIONES ELECTROTECNICAS',
                       '207': 'INSTALACIONES Y EQUIPOS DE CRIA Y CULTIVO',
                       '208': 'LABORATORIO',
                       '209': 'MANTENIMIENTO DE VEHICULOS',
                       '210': 'MAQUINAS, SERVICIOS Y PRODUCCION',
                       '211': 'MECANIZADO Y MANTENIMIENTO DE MAQUINAS',
                       '212': 'OFICINA DE PROYECTOS DE CONSTRUCCION',
                       '213': 'OFICINA DE PROYECTOS DE FABRICACION MECANICA',
                       '214': 'OPERACIONES Y EQUIPOS DE ELABORACION DE PRODUCTOS ALIMENTARIOS',
                       '215': 'OPERACIONES DE PROCESOS',
                       '216': 'OPERACIONES DE PRODUCCION AGRARIA',
                       '217': 'PATRONAJE Y CONFECCION',
                       '218': 'PELUQUERIA',
                       '219': 'PROCEDIMIENTOS DE DIAGNOSTICO CLINICO Y ORTOPROTESICO',
                       '220': 'PROCEDIMIENTOS SANITARIOS Y ASISTENCIALES',
                       '221': 'PROCESOS COMERCIALES',
                       '222': 'PROCESOS DE GESTION ADMINISTRATIVA',
                       '223': 'PRODUCCION EN ARTES GRAFICAS',
                       '224': 'PRODUCCION TEXTIL Y TRATAMIENTOS FISICO-QUIMICOS',
                       '225': 'SERVICIOS A LA COMUNIDAD',
                       '226': 'SERVICIOS DE RESTAURACION',
                       '227': 'SISTEMAS Y APLICACIONES INFORMATICAS',
                       '228': 'SOLDADURA',
                       '229': 'TECNICAS Y PROCEDIMIENTOS DE IMAGEN Y SONIDO',
                       '600': 'INSPECCION EDUCATIVA'},
              '0592': {'001': 'ALEMAN', '002': 'ARABE',
                       '003': 'CATALAN', '004': 'CHINO',
                       '005': 'DANES',
                       '006': 'ESPAÑOL PARA EXTRANJEROS',
                       '007': 'EUSKERA', '008': 'FRANCES',
                       '009': 'GALLEGO', '010': 'GRIEGO',
                       '011': 'INGLES', '012': 'ITALIANO',
                       '013': 'JAPONES', '014': 'NEERLANDES',
                       '015': 'PORTUGUES', '016': 'RUMANO',
                       '017': 'RUSO', '018': 'VALENCIANO',
                       '019': 'FINES', '020': 'SUECO'},
              '0593': {'001': 'ACORDEON',
                       '002': 'ARMONIA Y MELODIA ACOMPAÑADA',
                       '003': 'ARPA', '006': 'CANTO',
                       '007': 'CARACTERIZACION',
                       '008': 'CLARINETE', '009': 'CLAVE',
                       '011': 'COMPOSICION ELECTROACUSTICA',
                       '014': 'CONTRABAJO',
                       '015': 'CONTRAPUNTO Y FUGA', '016': 'COROS',
                       '017': 'DANZA ESPAÑOLA',
                       '019': 'DICCION Y LECTURA EXPRESIVA',
                       '022': 'DIRECCION DE ESCENA',
                       '024': 'DRAMATURGIA',
                       '025': 'ESCENA LIRICA',
                       '026': 'ESCENOGRAFIA', '027': 'ESGRIMA',
                       '029': 'EXPRESION CORPORAL', '030': 'FAGOT',
                       '031': 'FLAUTA DE PICO',
                       '032': 'FLAUTA TRAVESERA',
                       '035': 'GUITARRA',
                       '036': 'GUITARRA FLAMENCA',
                       '037': 'HISTORIA DE LA CULTURA Y DEL ARTE',
                       '038': 'HISTORIA DE LA LITERATURA DRAMATICA',
                       '039': 'HISTORIA DE LA MUSICA',
                       '040': 'HISTORIA DEL ARTE',
                       '041': 'INICIACION MUSICAL',
                       '042': 'INSTRUMENTOS DE PULSO Y PUA',
                       '043': 'INTERPRETACION',
                       '044': 'LECTURA MUSICAL',
                       '045': 'LENGUA ALEMANA',
                       '046': 'LENGUA FRANCESA',
                       '047': 'LENGUA INGLESA',
                       '048': 'LENGUA ITALIANA',
                       '049': 'MIMO Y PANTOMIMA',
                       '050': 'MUSICA DE CAMARA',
                       '051': 'MUSICOLOGIA', '052': 'OBOE',
                       '053': 'ORGANO',
                       '055': 'ORTOFONIA Y DICCION',
                       '056': 'PEDAGOGIA DEL TEATRO',
                       '058': 'PERCUSION', '059': 'PIANO',
                       '060': 'PIANO APLICADO',
                       '062': 'REPERTORIO DE OPERA Y ORATORIO',
                       '064': 'REPERTORIO VOCAL ESTILISTICO',
                       '066': 'SAXOFON',
                       '067': 'SOCIOLOGIA DEL TEATRO',
                       '069': 'TEATRO INFANTIL',
                       '071': 'TECNICAS MUSICALES CONTEMPORANEAS',
                       '072': 'TROMBON', '073': 'TROMBOM-TUBA',
                       '074': 'TROMPA', '075': 'TROMPETA',
                       '076': 'TUBA', '077': 'VIOLA',
                       '078': 'VIOLIN', '080': 'TXISTU',
                       '081': 'BAJO ELECTRICO',
                       '082': 'BATERIA DE JAZZ',
                       '083': 'CANTE FLAMENCO',
                       '084': 'CANTO DE JAZZ',
                       '085': 'COMPOSICIÓN DE JAZZ',
                       '086': 'CONTRABAJO DE JAZZ',
                       '087': 'DULZAINA',
                       '088': 'FLABIOL  I TAMBORÍ',
                       '089': 'FLAMENCOLOGÍA', '090': 'GAITA',
                       '091': 'GUITARRA ELÉCTRICA',
                       '092': 'INSTRUMENTOS DE CUERDA PULSADA DEL RENACIMIENTO Y BARROCO',
                       '093': 'INSTRUMENTOS DE PÚA',
                       '094': 'INSTRUMENTOS DE VIENTO DE JAZZ',
                       '095': 'INSTRUMENTOS HISTÓRICOS DE CUERDA FROTADA',
                       '096': 'INSTRUMENTOS HISTÓRICOS DE TECLA',
                       '097': 'INSTRUMENTOS HISTÓRICOS DE VIENTO',
                       '098': 'REPERTORIO CON PIANO PARA INSTRUMENTOS',
                       '099': 'TECLADOS/PIANO JAZZ',
                       '100': 'TECNOLOGÍA MUSICAL',
                       '101': 'TENORA I TIBLE',
                       '102': 'VIOLA DA GAMBA',
                       '103': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DEL BAILE FLAMENCO',
                       '104': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DE LA DANZA CLÁSICA',
                       '105': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DE LA DANZA CONTEMPORÁNEA',
                       '106': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DE LA DANZA ESPAÑOLA',
                       '107': 'CIENCIAS DE LA SALUD APLICADAS A LA DANZA',
                       '108': 'COMPOSICIÓN COREOGRÁFICA',
                       '109': 'DANZA CONTEMPORÁNEA',
                       '110': 'DANZA EDUCATIVA',
                       '111': 'ESCENIFICACIÓN APLICADA A LA DANZA',
                       '112': 'HISTORIA DE LA DANZA',
                       '113': 'PSICOPEDAGOGÍA Y GESTIÓN EDUCATIVA',
                       '114': 'TECNOLOGÍAS APLICADAS A LA DANZA',
                       '115': 'PRODUCCIÓN Y GESTIÓN DE MÚSICA Y ARTES ESCÉNICAS',
                       '600': 'INSPECCION EDUCATIVA'},
              '0594': {'012': 'COREOGRAFIA',
                       '017': 'ELEMENTOS DE ACUSTICA',
                       '018': 'ESCENA LIRICA',
                       '049': 'RITMICA Y PALEOGRAFIA',
                       '053': 'SOLFEO Y TEORIA DE LA MUSICA',
                       '078': 'FOLKLORE',
                       '083': 'PEDAGOGIA MUSICAL',
                       '085': 'HISTORIA DEL TEATRO',
                       '092': 'TXISTU', '401': 'ACORDEON',
                       '402': 'ARPA', '403': 'CANTO',
                       '404': 'CLARINETE', '405': 'CLAVE',
                       '406': 'CONTRABAJO', '407': 'CORO',
                       '408': 'FAGOT', '409': 'FLABIOL I TAMBORI',
                       '410': 'FLAUTA TRAVESERA',
                       '411': 'FLAUTA DE PICO',
                       '412': 'FUNDAMENTOS DE COMPOSICION',
                       '414': 'GUITARRA',
                       '415': 'GUITARRA FLAMENCA',
                       '416': 'HISTORIA DE LA MUSICA',
                       '418': 'INSTRUMENTOS DE PUA', '419': 'OBOE',
                       '420': 'ORGANO', '421': 'ORQUESTA',
                       '422': 'PERCUSION', '423': 'PIANO',
                       '424': 'SAXOFON', '425': 'TENORA Y TIBLE',
                       '426': 'TROMBON', '427': 'TROMPA',
                       '428': 'TROMPETA', '429': 'TUBA',
                       '430': 'TXISTU', '431': 'VIOLA',
                       '432': 'VIOLA DA GAMBA', '433': 'VIOLIN',
                       '434': 'VIOLONCHELLO',
                       '435': 'DANZA ESPAÑOLA',
                       '436': 'DANZA CLASICA',
                       '437': 'DANZA CONTEMPORANEA',
                       '438': 'FLAMENCO',
                       '439': 'HISTORIA DE LA DANZA',
                       '440': 'ACROBACIA',
                       '441': 'CANTO APLICADO AL ARTE DRAMATICO',
                       '442': 'CARACTERIZACION E INDUMENTARIA',
                       '443': 'DANZA APLICADA AL ARTE DRAMATICO',
                       '444': 'DICCION Y EXPRESION ORAL',
                       '445': 'DIRECCION ESCENICA',
                       '446': 'DRAMATURGIA', '447': 'ESGRIMA',
                       '448': 'ESPACIO ESCENICO',
                       '449': 'EXPRESION CORPORAL',
                       '450': 'ILUMINACION',
                       '451': 'INTERPRETACION',
                       '452': 'INTERPRETACION CON OBJETOS',
                       '453': 'INTERPRETACION EN EL MUSICAL',
                       '454': 'INTERPRETACION EN EL TEATRO DEL GESTO',
                       '455': 'LITERATURA DRAMATICA',
                       '456': 'TECNICAS ESCENICAS',
                       '457': 'TECNICAS GRAFICAS',
                       '458': 'TEORIA E HISTORIA DEL ARTE',
                       '459': 'TEORIA TEATRAL',
                       '460': 'LENGUAJE MUSICAL',
                       '461': 'BAJO ELÉCTRICO', '462': 'DULZAINA',
                       '463': 'GUITARRA ELÉCTRICA',
                       '464': 'REPERTORIO CON PIANO PARA DANZA',
                       '465': 'CANTE FLAMENCO',
                       '600': 'INSPECCION EDUCATIVA'},
              '0595': {'001': 'ADORNO Y FIGURA',
                       '002': 'ALFARERIA', '003': 'ARQUEOLOGIA',
                       '004': 'COMPOSICION ORNAMENTAL',
                       '005': 'DECORACION SOBRE PASTAS CERAMICAS',
                       '006': 'DERECHO USUAL Y NOCIONES CONTABILIDAD Y CORRESPONDENCIA COMERCIAL',
                       '008': 'DIBUJO ARQUEOLOGICO',
                       '009': 'DIBUJO ARTISTICO',
                       '010': 'DIBUJO LINEAL',
                       '011': 'FISICA Y QUIMICA APLICADAS A LA RESTAURACION',
                       '013': 'HISTORIA DEL ARTE',
                       '014': 'HISTORIA Y TECNICAS DEL LIBRO',
                       '015': 'MANUFACTURA CERAMICA',
                       '016': 'MATEMATICAS',
                       '017': 'MATERIAS PRIMAS CERAMICAS',
                       '018': 'MODELADO Y VACIADO',
                       '019': 'MODELAJE DE FIGURAS',
                       '020': 'MODELOS DE VAJILLERIA EN ESCAYOLA',
                       '021': 'PROCEDIMIENTOS DE ILUSTRACION DEL LIBRO',
                       '022': 'PROYECTOS DE ARTE DECORATIVO',
                       '023': 'QUIMICA APLICADA A LA CERAMICA',
                       '024': 'RESTAURACION DEL LIBRO',
                       '025': 'RESTAURACION DE OBRAS ESCULTORICAS',
                       '026': 'RESTAURACION Y TECNICAS ARQUEOLOGICAS',
                       '027': 'RESTAURACION Y TECNICAS PICTORICAS',
                       '028': 'SERIGRAFIA', '029': 'TAQUIGRAFIA',
                       '030': 'TAQUIMECANOGRAFIA',
                       '031': 'TECNICA SEGOVIANA',
                       '032': 'TECNICA TALAVERANA',
                       '033': 'TECNICAS AUDIOVISUALES',
                       '034': 'TECNICAS DE DISEÑO GRAFICO',
                       '035': 'TECNICAS GRAFICAS INDUSTRIALES',
                       '036': 'TECNOLOGIA QUIMICA Y TEXTIL',
                       '037': 'TEORIA Y PRACTICA DEL DISEÑO',
                       '038': 'TECNOLOGIA Y PROYECTOS DE BISUTERIA Y JOYERIA',
                       '039': 'ELEMENTOS CONSTRUCTIVOS',
                       '040': 'CONOCIMIENTO DE MATERIALES',
                       '048': 'PREPARACION ELEMENTAL CERAMICA',
                       '049': 'ANALISIS QUIMICOS DE CERAMICA',
                       '051': 'MATERIALES Y ELEMENTOS DE CONSTRUCCION',
                       '052': 'DECORACION ELEMENTAL CERAMICA',
                       '054': 'PREPARACION CERAMICA',
                       '056': 'COLORIDO CERAMICO',
                       '057': 'CULTURA GENERAL CERAMICA',
                       '065': 'TEORIA Y PRACTICA DE LA FOTOGRAFIA',
                       '066': 'ANALISIS DE FORMA Y COLOR',
                       '068': 'CERAMICA APLICADA A LA DECORACION',
                       '069': 'COLORIDO Y PROCEDIMIENTOS PICTÓRICOS',
                       '070': 'DIBUJO Y TECNICAS PICTORICAS',
                       '071': 'DISEÑO INDUSTRIAL CERAMICO',
                       '072': 'ENCUADERNACION',
                       '074': 'FOTOGRAFÍA',
                       '075': 'FOTOGRAFIA APLICADA A LA RESTAURACION',
                       '080': 'TECNICAS DE COLORIDO APLICADO A LA CERAMICA',
                       '083': 'DISEÑO ASISTIDO POR ORDENADOR',
                       '084': 'TECNICAS MURALES',
                       '085': 'RESTAURACION ARQUEOLOGICA',
                       '501': 'CERÁMICA',
                       '502': 'CONSERVACIÓN Y RESTAURACIÓN DE MATERIALES ARQUEOLÓGICOS',
                       '503': 'CONSERVACIÓN Y RESTAURACIÓN DE OBRAS ESCULTÓRICAS',
                       '504': 'CONSERVACIÓN Y RESTAURACIÓN DE OBRAS PICTÓRICAS',
                       '505': 'CONSERVACIÓN Y RESTAURACIÓN DE TEXTILES',
                       '506': 'CONSERVACIÓN Y RESTAURACIÓN DEL DOCUMENTO GRAFICO',
                       '507': 'DIBUJO ARTÍSTICO Y COLOR',
                       '508': 'DIBUJO TÉCNICO',
                       '509': 'DISEÑO DE INTERIORES',
                       '510': 'DISEÑO DE MODA',
                       '511': 'DISEÑO DE PRODUCTO',
                       '512': 'DISEÑO GRAFICO',
                       '513': 'DISEÑO TEXTIL',
                       '514': 'EDICIÓN DE ARTE',
                       '515': 'FOTOGRAFÍA',
                       '516': 'HISTORIA DEL ARTE',
                       '517': 'JOYERÍA Y ORFEBRERÍA',
                       '518': 'MATERIALES Y TECNOLOGÍA: CERAMICA Y VIDRIO',
                       '519': 'MATERIALES Y TECNOLOGÍA: CONSERVACION Y RESTAURACION',
                       '520': 'MATERIALES Y TECNOLOGÍA: DISEÑO',
                       '521': 'MEDIOS AUDIOVISUALES',
                       '522': 'MEDIOS INFORMÁTICOS',
                       '523': 'ORGANIZACIÓN INDUSTRIAL Y LEGISLACIÓN',
                       '524': 'VIDRIO', '525': 'VOLUMEN',
                       '600': 'INSPECCION EDUCATIVA'},
              '0596': {'001': 'ALFARERIA', '002': 'ALFOMBRAS',
                       '004': 'BORDADOS Y ENCAJES',
                       '005': 'CALCOGRAFIA Y XILOGRAFIA',
                       '006': 'CERAMICA ARTISTICA',
                       '007': 'CORTE Y CONFECCION',
                       '008': 'DECORACION',
                       '009': 'DECORACION CERAMICA',
                       '010': 'DECORACION SOBRE LOZA',
                       '011': 'DECORACION SOBRE PORCELANA',
                       '012': 'DELINEACION',
                       '013': 'DIBUJO PUBLICITARIO',
                       '014': 'DISEÑO INDUSTRIAL',
                       '015': 'DISEÑO DE FIGURINES',
                       '016': 'DORADO Y POLICROMIA',
                       '017': 'EBANISTERIA',
                       '018': 'EBANISTERIA Y MAQUETERIA',
                       '019': 'ENCUADERNACION',
                       '020': 'ESGRAFIADO', '021': 'ESMALTES',
                       '022': 'ESTAMPADO TEXTIL',
                       '023': 'FORJA ARTISTICA',
                       '024': 'FORJA Y CERRAJERIA',
                       '025': 'FOTOGRABADO',
                       '026': 'FOTOGRABADO Y TIPOGRAFIA',
                       '027': 'FOTOGRAFIA ARTISTICA',
                       '028': 'FOTOGRAFIA Y PROCESO DE REPRODUCCION',
                       '029': 'GRABADO', '031': 'HORNOS',
                       '032': 'INVESTIGACION DE MATERIAS PRIMAS CERAMICAS',
                       '033': 'JOYERIA',
                       '035': 'LABRADO Y REPUJADO EN CUERO',
                       '036': 'LITOGRAFIA',
                       '038': 'LOZA Y PORCELANA',
                       '039': 'MANUFACTURA CERAMICA',
                       '040': 'MATRICERIA',
                       '041': 'METALISTERIA ARTISTICA',
                       '043': 'MODELISMO Y MAQUETISMO',
                       '044': 'MOLDES Y REPRODUCCIONES',
                       '045': 'MOSAICOS ROMANOS',
                       '046': 'MUÑEQUERIA ARTISTICA',
                       '047': 'ORFEBRERIA',
                       '048': 'PASTAS Y HORNOS',
                       '049': 'PATRONAJE, ESCALADO Y TECNICAS DE CONFECCION',
                       '050': 'QUIMICA APLICADA A LA CERAMICA',
                       '051': 'REPUJADO EN CUERO',
                       '052': 'REPUJADO EN METAL',
                       '053': 'RESTAURACION DE DIBUJOS Y GRABADOS',
                       '054': 'RESTAURACION DE ENCUADERNACIONES',
                       '055': 'RESTAURACION DE MANUSCRITOS E IMPRESOS',
                       '056': 'RESTAURACION DE TAPICES',
                       '057': 'MODELISMO INDUSTRIAL',
                       '058': 'TALLA DE MADERA',
                       '059': 'TALLA EN PIEDRA',
                       '060': 'TALLA DE PIEDRA Y MADERA',
                       '061': 'TAPICES Y ALFOMBRAS',
                       '062': 'TAQUIMECANOGRAFIA',
                       '063': 'TECNICAS DE JOYERIA',
                       '064': 'TEXTILES ARTISTICOS',
                       '065': 'VACIADO Y MODELADO',
                       '066': 'VIDRIERAS ARTISTICAS',
                       '068': 'INICIACION A LA RESTAURACION',
                       '069': 'RESTAURACION CERAMICA',
                       '070': 'TECNICAS DE DISEÑO INDUSTRIAL',
                       '071': 'TIPOGRAFÍA', '072': 'VACIADO',
                       '074': 'TALLA ORNAMENTAL',
                       '081': 'ABANIQUERÍA',
                       '087': 'ARTESANIA CANARIA',
                       '088': 'ARTES GRAFICAS',
                       '091': 'DIBUJOS ANIMADOS',
                       '092': 'DIBUJO DEL MUEBLE',
                       '093': 'FIGURINES',
                       '094': 'REPUJADO EN CUERO Y METAL',
                       '095': 'RESTAURACION', '097': 'SERIGRAFIA',
                       '098': 'MOLDEO Y MONTAJE DE PORCELANA',
                       '099': 'FORJA Y FUNDICION',
                       '101': 'MARIONETAS',
                       '102': 'REFLEJOS METALICOS',
                       '104': 'TAQUIGRAFIA',
                       '107': 'DISEÑO GRAFICO ASISTIDO POR ORDENADOR',
                       '108': 'REPRODUCCION E IMPRESION',
                       '109': 'CERRAJERIA Y FORJA',
                       '110': 'CONSTRUCCIONES NAVALES',
                       '115': 'IMAGINERIA CASTELLANA',
                       '117': 'METALISTERIA (DAMASQUINADO)',
                       '600': 'INSPECCION EDUCATIVA',
                       '601': 'ARTESANIA Y ORNAMENTACION CON ELEMENTOS VEGETALES',
                       '602': 'BORDADOS Y ENCAJES',
                       '603': 'COMPLEMENTOS Y ACCESORIOS',
                       '604': 'DORADO Y POLICROMIA',
                       '605': 'EBANISTERIA ARTISTICA',
                       '606': 'ENCUADERNACION ARTISTICA',
                       '607': 'ESMALTES',
                       '608': 'FOTOGRAFIA Y PROCESOS DE REPRODUCCION',
                       '609': 'MODELISMO Y MAQUETISMO',
                       '610': 'MOLDES Y REPRODUCCIONES',
                       '611': 'MUSIVARIA',
                       '612': 'TALLA EN PIEDRA Y MADERA',
                       '613': 'TECNICAS CERAMICAS',
                       '614': 'TECNICAS DE GRABADO Y ESTAMPACION',
                       '615': 'TECNICAS DE JOYERIA Y BISUTERIA',
                       '616': 'TECNICAS DE ORFEBRERIA Y PLATERIA',
                       '617': 'TECNICAS DE PATRONAJE Y CONFECCION',
                       '618': 'TECNICAS DEL METAL',
                       '619': 'TECNICAS MURALES',
                       '620': 'TECNICAS TEXTILES',
                       '621': 'TECNICAS VIDRIERAS'},
              '0597': {'041': 'COMPENSATORIA (A.D.)',
                       'AL': 'AUDICION Y LENGUAJE',
                       'AS': 'AUDICION Y LENGUAJE',
                       'CK': 'COMPENSATORIA ( SEC. )',
                       'CN': 'CIENCIAS DE LA NATURALEZA',
                       'CO': 'EDUCACION COMPENSATORIA',
                       'CS': 'CIENCIAS SOCIALES',
                       'EA': 'EDUCACIÓN DE ADULTOS',
                       'EAI': 'INGLES ( ED. ADULTOS )',
                       'EF': 'EDUCACION FISICA',
                       'EI': 'EDUCACION INFANTIL', 'EU': 'EUSKERA',
                       'FA': 'LENGUA EXTRANJERA: ALEMÁN',
                       'FB': 'CATALAN (BALEARES)', 'FC': 'CATALAN',
                       'FF': 'LENGUA EXTRANJERA: FRANCÉS',
                       'FG': 'GALLEGO',
                       'FI': 'LENGUA EXTRANJERA: INGLÉS',
                       'FL': 'FILOLOGIA: LENGUA CASTELLANA',
                       'FN': 'VASCUENCE (NAVARRA)',
                       'FR': 'LENGUA EXTRANJERA: FRANCES',
                       'FS': 'EDUCACION FISICA',
                       'FV': 'VALENCIANO',
                       'GH': 'GEOGRAFIA E HISTORIA',
                       'GS': 'GARANTIA SOCIAL',
                       'LL': 'LENGUA Y LITERATURA',
                       'MA': 'MATEMATICAS',
                       'MC': 'MATEMATICAS Y CIENCIAS DE LA NATURALEZA',
                       'MS': 'MUSICA (SEC.)', 'MU': 'MUSICA',
                       'PCP': 'P.C.P.I.', 'PRI': 'PRIMARIA',
                       'PS': 'PEDAGOGIA TERAPEUTICA (SEC.)',
                       'PT': 'PEDAGOGIA TERAPEUTICA'},
              '0598': {'001': 'COCINA Y PASTELERIA',
                       '002': 'ESTETICA',
                       '003': 'FABRICACION E INSTALACION DE CARPINTERIA Y MUEBLE',
                       '004': 'MANTENIMIENTO DE VEHICULOS',
                       '005': 'MECANIZADO Y MANTENIMIENTO DE MAQUINAS',
                       '006': 'PATRONAJE Y CONFECCION',
                       '007': 'PELUQUERIA',
                       '008': 'PRODUCCION EN ARTES GRAFICAS',
                       '009': 'SERVICIOS DE RESTAURACION',
                       '010': 'SOLDADURA'}}
# ESPECS = {'0590': [{'especialidad': '001', 'nombre': 'FILOSOFIA'}, {'especialidad': '002', 'nombre': 'GRIEGO'},
#                    {'especialidad': '003', 'nombre': 'LATIN'},
#                    {'especialidad': '004', 'nombre': 'LENGUA CASTELLANA Y LITERATURA'},
#                    {'especialidad': '005', 'nombre': 'GEOGRAFIA E HISTORIA'},
#                    {'especialidad': '006', 'nombre': 'MATEMATICAS'},
#                    {'especialidad': '007', 'nombre': 'FISICA Y QUIMICA'},
#                    {'especialidad': '008', 'nombre': 'BIOLOGIA Y GEOLOGIA'},
#                    {'especialidad': '009', 'nombre': 'DIBUJO'}, {'especialidad': '010', 'nombre': 'FRANCES'},
#                    {'especialidad': '011', 'nombre': 'INGLES'}, {'especialidad': '012', 'nombre': 'ALEMAN'},
#                    {'especialidad': '013', 'nombre': 'ITALIANO'},
#                    {'especialidad': '014', 'nombre': 'LENGUA Y LITERATURA CATALANAS (ISLAS BALEARES)'},
#                    {'especialidad': '015', 'nombre': 'PORTUGUES'}, {'especialidad': '016', 'nombre': 'MUSICA'},
#                    {'especialidad': '017', 'nombre': 'EDUCACION FISICA'},
#                    {'especialidad': '018', 'nombre': 'ORIENTACIÓN EDUCATIVA'},
#                    {'especialidad': '019', 'nombre': 'TECNOLOGIA'},
#                    {'especialidad': '039', 'nombre': 'TECNOLOGIA MINERA'},
#                    {'especialidad': '051', 'nombre': 'LENGUA CATALANA Y LITERATURA'},
#                    {'especialidad': '052', 'nombre': 'LENGUA Y LITERATURA VASCA'},
#                    {'especialidad': '053', 'nombre': 'LENGUA Y LITERATURA GALLEGA'},
#                    {'especialidad': '055', 'nombre': 'EDUCADORES (C.E.I.S.)'},
#                    {'especialidad': '056', 'nombre': 'LENGUA Y LITERATURA VALENCIANA'},
#                    {'especialidad': '057', 'nombre': 'LENGUA Y LITERATURA VASCA (NAVARRA)'},
#                    {'especialidad': '058', 'nombre': 'APOYO AL AREA DE LENGUA Y CIENCIAS SOCIALES'},
#                    {'especialidad': '059', 'nombre': 'APOYO AL AREA DE CIENCIAS O TECNOLOGIA'},
#                    {'especialidad': '061', 'nombre': 'ECONOMIA'}, {'especialidad': '062', 'nombre': 'LENGUA ARANESA'},
#                    {'especialidad': '101', 'nombre': 'ADMINISTRACION DE EMPRESAS'},
#                    {'especialidad': '102', 'nombre': 'ANALISIS Y QUIMICA INDUSTRIAL'},
#                    {'especialidad': '103', 'nombre': 'ASESORIA Y PROCESOS DE IMAGEN PERSONAL'},
#                    {'especialidad': '104', 'nombre': 'CONSTRUCCIONES CIVILES Y EDIFICACION'},
#                    {'especialidad': '105', 'nombre': 'FORMACION Y ORIENTACION LABORAL'},
#                    {'especialidad': '106', 'nombre': 'HOSTELERIA Y TURISMO'},
#                    {'especialidad': '107', 'nombre': 'INFORMATICA'},
#                    {'especialidad': '108', 'nombre': 'INTERVENCION SOCIOCOMUNITARIA'},
#                    {'especialidad': '109', 'nombre': 'NAVEGACION E INSTALACIONES MARINAS'},
#                    {'especialidad': '110', 'nombre': 'ORGANIZACION Y GESTION COMERCIAL'},
#                    {'especialidad': '111', 'nombre': 'ORGANIZACION Y PROCESOS DE MANTENIMIENTO DE VEHICULOS'},
#                    {'especialidad': '112', 'nombre': 'ORGANIZACION Y PROYECTOS DE FABRICACION MECANICA'},
#                    {'especialidad': '113', 'nombre': 'ORGANIZACION Y PROYECTOS DE SISTEMAS ENERGETICOS'},
#                    {'especialidad': '114', 'nombre': 'PROCESOS DE CULTIVO ACUICOLA'},
#                    {'especialidad': '115', 'nombre': 'PROCESOS DE PRODUCCION AGRARIA'},
#                    {'especialidad': '116', 'nombre': 'PROCESOS EN LA INDUSTRIA ALIMENTARIA'},
#                    {'especialidad': '117', 'nombre': 'PROCESOS DIAGNOSTICOS CLINICOS Y PRODUCTOS ORTOPROTESICOS'},
#                    {'especialidad': '118', 'nombre': 'PROCESOS SANITARIOS'},
#                    {'especialidad': '119', 'nombre': 'PROCESOS Y MEDIOS DE COMUNICACION'},
#                    {'especialidad': '120', 'nombre': 'PROCESOS Y PRODUCTOS DE TEXTIL, CONFECCION Y PIEL'},
#                    {'especialidad': '121', 'nombre': 'PROCESOS Y PRODUCTOS DE VIDRIO Y CERAMICA'},
#                    {'especialidad': '122', 'nombre': 'PROCESOS Y PRODUCTOS EN ARTES GRAFICAS'},
#                    {'especialidad': '123', 'nombre': 'PROCESOS Y PRODUCTOS EN MADERA Y MUEBLE'},
#                    {'especialidad': '124', 'nombre': 'SISTEMAS ELECTRONICOS'},
#                    {'especialidad': '125', 'nombre': 'SISTEMAS ELECTROTECNICOS Y AUTOMATICOS'},
#                    {'especialidad': '201', 'nombre': 'COCINA Y PASTELERIA'},
#                    {'especialidad': '203', 'nombre': 'ESTETICA'},
#                    {'especialidad': '204', 'nombre': 'FABRICACION E INSTALACION DE CARPINTERIA Y MUEBLE'},
#                    {'especialidad': '205', 'nombre': 'INSTALACION Y MANTENIMIENTO DE EQUIPOS TERMICOS Y DE FLUIDOS'},
#                    {'especialidad': '206', 'nombre': 'INSTALACIONES ELECTROTECNICAS'},
#                    {'especialidad': '207', 'nombre': 'INSTALACIONES Y EQUIPOS DE CRIA Y CULTIVO'},
#                    {'especialidad': '208', 'nombre': 'LABORATORIO'},
#                    {'especialidad': '209', 'nombre': 'MANTENIMIENTO DE VEHICULOS'},
#                    {'especialidad': '210', 'nombre': 'MAQUINAS, SERVICIOS Y PRODUCCION'},
#                    {'especialidad': '211', 'nombre': 'MECANIZADO Y MANTENIMIENTO DE MAQUINAS'},
#                    {'especialidad': '212', 'nombre': 'OFICINA DE PROYECTOS DE CONSTRUCCION'},
#                    {'especialidad': '213', 'nombre': 'OFICINA DE PROYECTOS DE FABRICACION MECANICA'},
#                    {'especialidad': '214', 'nombre': 'OPERACIONES Y EQUIPOS DE ELABORACION DE PRODUCTOS ALIMENTARIOS'},
#                    {'especialidad': '215', 'nombre': 'OPERACIONES DE PROCESOS'},
#                    {'especialidad': '216', 'nombre': 'OPERACIONES Y EQUIPOS DE PRODUCCION AGRARIA'},
#                    {'especialidad': '217', 'nombre': 'PATRONAJE Y CONFECCION'},
#                    {'especialidad': '218', 'nombre': 'PELUQUERIA'},
#                    {'especialidad': '219', 'nombre': 'PROCEDIMIENTOS DE DIAGNOSTICO CLINICO Y ORTOPROTESICO'},
#                    {'especialidad': '220', 'nombre': 'PROCEDIMIENTOS SANITARIOS Y ASISTENCIALES'},
#                    {'especialidad': '221', 'nombre': 'PROCESOS COMERCIALES'},
#                    {'especialidad': '222', 'nombre': 'PROCESOS DE GESTION ADMINISTRATIVA'},
#                    {'especialidad': '223', 'nombre': 'PRODUCCION EN ARTES GRAFICAS'},
#                    {'especialidad': '224', 'nombre': 'PRODUCCION TEXTIL Y TRATAMIENTOS FISICO-QUIMICOS'},
#                    {'especialidad': '225', 'nombre': 'SERVICIOS A LA COMUNIDAD'},
#                    {'especialidad': '226', 'nombre': 'SERVICIOS DE RESTAURACION'},
#                    {'especialidad': '227', 'nombre': 'SISTEMAS Y APLICACIONES INFORMATICAS'},
#                    {'especialidad': '228', 'nombre': 'SOLDADURA'},
#                    {'especialidad': '229', 'nombre': 'TECNICAS Y PROCEDIMIENTOS DE IMAGEN Y SONIDO'},
#                    {'especialidad': '231', 'nombre': 'EQUIPOS ELECTRONICOS'},
#                    {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'},
#                    {'especialidad': '803', 'nombre': 'CULTURA CLASICA'},
#                    {'especialidad': '810', 'nombre': 'AMBITO DE COMUNICACION: FRANCES'},
#                    {'especialidad': '811', 'nombre': 'AMBITO DE COMUNICACION: INGLES'},
#                    {'especialidad': '812', 'nombre': 'AMBITO DE COMUNICACION: LENGUA CASTELLANA'},
#                    {'especialidad': '813', 'nombre': 'AMBITO DE COMUNICACION: EUSKERA'},
#                    {'especialidad': '814', 'nombre': 'AMBITO DE CONOCIMIENTO SOCIAL'},
#                    {'especialidad': '815', 'nombre': 'AMBITO CIENTIFICO-TECNOLOGICO'},
#                    {'especialidad': '905', 'nombre': 'CIENCIAS DE LA NATURALEZA'}],
#           '0591': [{'especialidad': '016', 'nombre': 'PRACTICAS DE MINERIA'},
#                    {'especialidad': '021', 'nombre': 'TALLER DE VIDRIO Y CERAMICA'},
#                    {'especialidad': '025', 'nombre': 'ACTIVIDADES (C.E.I.S.)'},
#                    {'especialidad': '026', 'nombre': 'APOYO AL AREA PRACTICA'},
#                    {'especialidad': '201', 'nombre': 'COCINA Y PASTELERIA'},
#                    {'especialidad': '202', 'nombre': 'EQUIPOS ELECTRONICOS'},
#                    {'especialidad': '203', 'nombre': 'ESTETICA'},
#                    {'especialidad': '204', 'nombre': 'FABRICACION E INSTALACION DE CARPINTERIA Y MUEBLE'},
#                    {'especialidad': '205', 'nombre': 'INSTALACION Y MANTENIMIENTO DE EQUIPOS TERMICOS Y DE FLUIDOS'},
#                    {'especialidad': '206', 'nombre': 'INSTALACIONES ELECTROTECNICAS'},
#                    {'especialidad': '207', 'nombre': 'INSTALACIONES Y EQUIPOS DE CRIA Y CULTIVO'},
#                    {'especialidad': '208', 'nombre': 'LABORATORIO'},
#                    {'especialidad': '209', 'nombre': 'MANTENIMIENTO DE VEHICULOS'},
#                    {'especialidad': '210', 'nombre': 'MAQUINAS, SERVICIOS Y PRODUCCION'},
#                    {'especialidad': '211', 'nombre': 'MECANIZADO Y MANTENIMIENTO DE MAQUINAS'},
#                    {'especialidad': '212', 'nombre': 'OFICINA DE PROYECTOS DE CONSTRUCCION'},
#                    {'especialidad': '213', 'nombre': 'OFICINA DE PROYECTOS DE FABRICACION MECANICA'},
#                    {'especialidad': '214', 'nombre': 'OPERACIONES Y EQUIPOS DE ELABORACION DE PRODUCTOS ALIMENTARIOS'},
#                    {'especialidad': '215', 'nombre': 'OPERACIONES DE PROCESOS'},
#                    {'especialidad': '216', 'nombre': 'OPERACIONES DE PRODUCCION AGRARIA'},
#                    {'especialidad': '217', 'nombre': 'PATRONAJE Y CONFECCION'},
#                    {'especialidad': '218', 'nombre': 'PELUQUERIA'},
#                    {'especialidad': '219', 'nombre': 'PROCEDIMIENTOS DE DIAGNOSTICO CLINICO Y ORTOPROTESICO'},
#                    {'especialidad': '220', 'nombre': 'PROCEDIMIENTOS SANITARIOS Y ASISTENCIALES'},
#                    {'especialidad': '221', 'nombre': 'PROCESOS COMERCIALES'},
#                    {'especialidad': '222', 'nombre': 'PROCESOS DE GESTION ADMINISTRATIVA'},
#                    {'especialidad': '223', 'nombre': 'PRODUCCION EN ARTES GRAFICAS'},
#                    {'especialidad': '224', 'nombre': 'PRODUCCION TEXTIL Y TRATAMIENTOS FISICO-QUIMICOS'},
#                    {'especialidad': '225', 'nombre': 'SERVICIOS A LA COMUNIDAD'},
#                    {'especialidad': '226', 'nombre': 'SERVICIOS DE RESTAURACION'},
#                    {'especialidad': '227', 'nombre': 'SISTEMAS Y APLICACIONES INFORMATICAS'},
#                    {'especialidad': '228', 'nombre': 'SOLDADURA'},
#                    {'especialidad': '229', 'nombre': 'TECNICAS Y PROCEDIMIENTOS DE IMAGEN Y SONIDO'},
#                    {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'}],
#           '0592': [{'especialidad': '001', 'nombre': 'ALEMAN'}, {'especialidad': '002', 'nombre': 'ARABE'},
#                    {'especialidad': '003', 'nombre': 'CATALAN'}, {'especialidad': '004', 'nombre': 'CHINO'},
#                    {'especialidad': '005', 'nombre': 'DANES'},
#                    {'especialidad': '006', 'nombre': 'ESPAÑOL PARA EXTRANJEROS'},
#                    {'especialidad': '007', 'nombre': 'EUSKERA'}, {'especialidad': '008', 'nombre': 'FRANCES'},
#                    {'especialidad': '009', 'nombre': 'GALLEGO'}, {'especialidad': '010', 'nombre': 'GRIEGO'},
#                    {'especialidad': '011', 'nombre': 'INGLES'}, {'especialidad': '012', 'nombre': 'ITALIANO'},
#                    {'especialidad': '013', 'nombre': 'JAPONES'}, {'especialidad': '014', 'nombre': 'NEERLANDES'},
#                    {'especialidad': '015', 'nombre': 'PORTUGUES'}, {'especialidad': '016', 'nombre': 'RUMANO'},
#                    {'especialidad': '017', 'nombre': 'RUSO'}, {'especialidad': '018', 'nombre': 'VALENCIANO'},
#                    {'especialidad': '019', 'nombre': 'FINES'}, {'especialidad': '020', 'nombre': 'SUECO'}],
#           '0593': [{'especialidad': '001', 'nombre': 'ACORDEON'},
#                    {'especialidad': '002', 'nombre': 'ARMONIA Y MELODIA ACOMPAÑADA'},
#                    {'especialidad': '003', 'nombre': 'ARPA'}, {'especialidad': '006', 'nombre': 'CANTO'},
#                    {'especialidad': '007', 'nombre': 'CARACTERIZACION'},
#                    {'especialidad': '008', 'nombre': 'CLARINETE'}, {'especialidad': '009', 'nombre': 'CLAVE'},
#                    {'especialidad': '011', 'nombre': 'COMPOSICION ELECTROACUSTICA'},
#                    {'especialidad': '014', 'nombre': 'CONTRABAJO'},
#                    {'especialidad': '015', 'nombre': 'CONTRAPUNTO Y FUGA'}, {'especialidad': '016', 'nombre': 'COROS'},
#                    {'especialidad': '017', 'nombre': 'DANZA ESPAÑOLA'},
#                    {'especialidad': '019', 'nombre': 'DICCION Y LECTURA EXPRESIVA'},
#                    {'especialidad': '022', 'nombre': 'DIRECCION DE ESCENA'},
#                    {'especialidad': '024', 'nombre': 'DRAMATURGIA'},
#                    {'especialidad': '025', 'nombre': 'ESCENA LIRICA'},
#                    {'especialidad': '026', 'nombre': 'ESCENOGRAFIA'}, {'especialidad': '027', 'nombre': 'ESGRIMA'},
#                    {'especialidad': '029', 'nombre': 'EXPRESION CORPORAL'}, {'especialidad': '030', 'nombre': 'FAGOT'},
#                    {'especialidad': '031', 'nombre': 'FLAUTA DE PICO'},
#                    {'especialidad': '032', 'nombre': 'FLAUTA TRAVESERA'},
#                    {'especialidad': '035', 'nombre': 'GUITARRA'},
#                    {'especialidad': '036', 'nombre': 'GUITARRA FLAMENCA'},
#                    {'especialidad': '037', 'nombre': 'HISTORIA DE LA CULTURA Y DEL ARTE'},
#                    {'especialidad': '038', 'nombre': 'HISTORIA DE LA LITERATURA DRAMATICA'},
#                    {'especialidad': '039', 'nombre': 'HISTORIA DE LA MUSICA'},
#                    {'especialidad': '040', 'nombre': 'HISTORIA DEL ARTE'},
#                    {'especialidad': '041', 'nombre': 'INICIACION MUSICAL'},
#                    {'especialidad': '042', 'nombre': 'INSTRUMENTOS DE PULSO Y PUA'},
#                    {'especialidad': '043', 'nombre': 'INTERPRETACION'},
#                    {'especialidad': '044', 'nombre': 'LECTURA MUSICAL'},
#                    {'especialidad': '045', 'nombre': 'LENGUA ALEMANA'},
#                    {'especialidad': '046', 'nombre': 'LENGUA FRANCESA'},
#                    {'especialidad': '047', 'nombre': 'LENGUA INGLESA'},
#                    {'especialidad': '048', 'nombre': 'LENGUA ITALIANA'},
#                    {'especialidad': '049', 'nombre': 'MIMO Y PANTOMIMA'},
#                    {'especialidad': '050', 'nombre': 'MUSICA DE CAMARA'},
#                    {'especialidad': '051', 'nombre': 'MUSICOLOGIA'}, {'especialidad': '052', 'nombre': 'OBOE'},
#                    {'especialidad': '053', 'nombre': 'ORGANO'},
#                    {'especialidad': '055', 'nombre': 'ORTOFONIA Y DICCION'},
#                    {'especialidad': '056', 'nombre': 'PEDAGOGIA DEL TEATRO'},
#                    {'especialidad': '058', 'nombre': 'PERCUSION'}, {'especialidad': '059', 'nombre': 'PIANO'},
#                    {'especialidad': '060', 'nombre': 'PIANO APLICADO'},
#                    {'especialidad': '062', 'nombre': 'REPERTORIO DE OPERA Y ORATORIO'},
#                    {'especialidad': '064', 'nombre': 'REPERTORIO VOCAL ESTILISTICO'},
#                    {'especialidad': '066', 'nombre': 'SAXOFON'},
#                    {'especialidad': '067', 'nombre': 'SOCIOLOGIA DEL TEATRO'},
#                    {'especialidad': '069', 'nombre': 'TEATRO INFANTIL'},
#                    {'especialidad': '071', 'nombre': 'TECNICAS MUSICALES CONTEMPORANEAS'},
#                    {'especialidad': '072', 'nombre': 'TROMBON'}, {'especialidad': '073', 'nombre': 'TROMBOM-TUBA'},
#                    {'especialidad': '074', 'nombre': 'TROMPA'}, {'especialidad': '075', 'nombre': 'TROMPETA'},
#                    {'especialidad': '076', 'nombre': 'TUBA'}, {'especialidad': '077', 'nombre': 'VIOLA'},
#                    {'especialidad': '078', 'nombre': 'VIOLIN'}, {'especialidad': '080', 'nombre': 'TXISTU'},
#                    {'especialidad': '081', 'nombre': 'BAJO ELECTRICO'},
#                    {'especialidad': '082', 'nombre': 'BATERIA DE JAZZ'},
#                    {'especialidad': '083', 'nombre': 'CANTE FLAMENCO'},
#                    {'especialidad': '084', 'nombre': 'CANTO DE JAZZ'},
#                    {'especialidad': '085', 'nombre': 'COMPOSICIÓN DE JAZZ'},
#                    {'especialidad': '086', 'nombre': 'CONTRABAJO DE JAZZ'},
#                    {'especialidad': '087', 'nombre': 'DULZAINA'},
#                    {'especialidad': '088', 'nombre': 'FLABIOL  I TAMBORÍ'},
#                    {'especialidad': '089', 'nombre': 'FLAMENCOLOGÍA'}, {'especialidad': '090', 'nombre': 'GAITA'},
#                    {'especialidad': '091', 'nombre': 'GUITARRA ELÉCTRICA'},
#                    {'especialidad': '092', 'nombre': 'INSTRUMENTOS DE CUERDA PULSADA DEL RENACIMIENTO Y BARROCO'},
#                    {'especialidad': '093', 'nombre': 'INSTRUMENTOS DE PÚA'},
#                    {'especialidad': '094', 'nombre': 'INSTRUMENTOS DE VIENTO DE JAZZ'},
#                    {'especialidad': '095', 'nombre': 'INSTRUMENTOS HISTÓRICOS DE CUERDA FROTADA'},
#                    {'especialidad': '096', 'nombre': 'INSTRUMENTOS HISTÓRICOS DE TECLA'},
#                    {'especialidad': '097', 'nombre': 'INSTRUMENTOS HISTÓRICOS DE VIENTO'},
#                    {'especialidad': '098', 'nombre': 'REPERTORIO CON PIANO PARA INSTRUMENTOS'},
#                    {'especialidad': '099', 'nombre': 'TECLADOS/PIANO JAZZ'},
#                    {'especialidad': '100', 'nombre': 'TECNOLOGÍA MUSICAL'},
#                    {'especialidad': '101', 'nombre': 'TENORA I TIBLE'},
#                    {'especialidad': '102', 'nombre': 'VIOLA DA GAMBA'},
#                    {'especialidad': '103', 'nombre': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DEL BAILE FLAMENCO'},
#                    {'especialidad': '104', 'nombre': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DE LA DANZA CLÁSICA'},
#                    {'especialidad': '105', 'nombre': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DE LA DANZA CONTEMPORÁNEA'},
#                    {'especialidad': '106', 'nombre': 'ANÁLISIS Y PRÁCTICA DEL REPERTORIO DE LA DANZA ESPAÑOLA'},
#                    {'especialidad': '107', 'nombre': 'CIENCIAS DE LA SALUD APLICADAS A LA DANZA'},
#                    {'especialidad': '108', 'nombre': 'COMPOSICIÓN COREOGRÁFICA'},
#                    {'especialidad': '109', 'nombre': 'DANZA CONTEMPORÁNEA'},
#                    {'especialidad': '110', 'nombre': 'DANZA EDUCATIVA'},
#                    {'especialidad': '111', 'nombre': 'ESCENIFICACIÓN APLICADA A LA DANZA'},
#                    {'especialidad': '112', 'nombre': 'HISTORIA DE LA DANZA'},
#                    {'especialidad': '113', 'nombre': 'PSICOPEDAGOGÍA Y GESTIÓN EDUCATIVA'},
#                    {'especialidad': '114', 'nombre': 'TECNOLOGÍAS APLICADAS A LA DANZA'},
#                    {'especialidad': '115', 'nombre': 'PRODUCCIÓN Y GESTIÓN DE MÚSICA Y ARTES ESCÉNICAS'},
#                    {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'}],
#           '0594': [{'especialidad': '012', 'nombre': 'COREOGRAFIA'},
#                    {'especialidad': '017', 'nombre': 'ELEMENTOS DE ACUSTICA'},
#                    {'especialidad': '018', 'nombre': 'ESCENA LIRICA'},
#                    {'especialidad': '049', 'nombre': 'RITMICA Y PALEOGRAFIA'},
#                    {'especialidad': '053', 'nombre': 'SOLFEO Y TEORIA DE LA MUSICA'},
#                    {'especialidad': '078', 'nombre': 'FOLKLORE'},
#                    {'especialidad': '083', 'nombre': 'PEDAGOGIA MUSICAL'},
#                    {'especialidad': '085', 'nombre': 'HISTORIA DEL TEATRO'},
#                    {'especialidad': '092', 'nombre': 'TXISTU'}, {'especialidad': '401', 'nombre': 'ACORDEON'},
#                    {'especialidad': '402', 'nombre': 'ARPA'}, {'especialidad': '403', 'nombre': 'CANTO'},
#                    {'especialidad': '404', 'nombre': 'CLARINETE'}, {'especialidad': '405', 'nombre': 'CLAVE'},
#                    {'especialidad': '406', 'nombre': 'CONTRABAJO'}, {'especialidad': '407', 'nombre': 'CORO'},
#                    {'especialidad': '408', 'nombre': 'FAGOT'}, {'especialidad': '409', 'nombre': 'FLABIOL I TAMBORI'},
#                    {'especialidad': '410', 'nombre': 'FLAUTA TRAVESERA'},
#                    {'especialidad': '411', 'nombre': 'FLAUTA DE PICO'},
#                    {'especialidad': '412', 'nombre': 'FUNDAMENTOS DE COMPOSICION'},
#                    {'especialidad': '414', 'nombre': 'GUITARRA'},
#                    {'especialidad': '415', 'nombre': 'GUITARRA FLAMENCA'},
#                    {'especialidad': '416', 'nombre': 'HISTORIA DE LA MUSICA'},
#                    {'especialidad': '418', 'nombre': 'INSTRUMENTOS DE PUA'}, {'especialidad': '419', 'nombre': 'OBOE'},
#                    {'especialidad': '420', 'nombre': 'ORGANO'}, {'especialidad': '421', 'nombre': 'ORQUESTA'},
#                    {'especialidad': '422', 'nombre': 'PERCUSION'}, {'especialidad': '423', 'nombre': 'PIANO'},
#                    {'especialidad': '424', 'nombre': 'SAXOFON'}, {'especialidad': '425', 'nombre': 'TENORA Y TIBLE'},
#                    {'especialidad': '426', 'nombre': 'TROMBON'}, {'especialidad': '427', 'nombre': 'TROMPA'},
#                    {'especialidad': '428', 'nombre': 'TROMPETA'}, {'especialidad': '429', 'nombre': 'TUBA'},
#                    {'especialidad': '430', 'nombre': 'TXISTU'}, {'especialidad': '431', 'nombre': 'VIOLA'},
#                    {'especialidad': '432', 'nombre': 'VIOLA DA GAMBA'}, {'especialidad': '433', 'nombre': 'VIOLIN'},
#                    {'especialidad': '434', 'nombre': 'VIOLONCHELLO'},
#                    {'especialidad': '435', 'nombre': 'DANZA ESPAÑOLA'},
#                    {'especialidad': '436', 'nombre': 'DANZA CLASICA'},
#                    {'especialidad': '437', 'nombre': 'DANZA CONTEMPORANEA'},
#                    {'especialidad': '438', 'nombre': 'FLAMENCO'},
#                    {'especialidad': '439', 'nombre': 'HISTORIA DE LA DANZA'},
#                    {'especialidad': '440', 'nombre': 'ACROBACIA'},
#                    {'especialidad': '441', 'nombre': 'CANTO APLICADO AL ARTE DRAMATICO'},
#                    {'especialidad': '442', 'nombre': 'CARACTERIZACION E INDUMENTARIA'},
#                    {'especialidad': '443', 'nombre': 'DANZA APLICADA AL ARTE DRAMATICO'},
#                    {'especialidad': '444', 'nombre': 'DICCION Y EXPRESION ORAL'},
#                    {'especialidad': '445', 'nombre': 'DIRECCION ESCENICA'},
#                    {'especialidad': '446', 'nombre': 'DRAMATURGIA'}, {'especialidad': '447', 'nombre': 'ESGRIMA'},
#                    {'especialidad': '448', 'nombre': 'ESPACIO ESCENICO'},
#                    {'especialidad': '449', 'nombre': 'EXPRESION CORPORAL'},
#                    {'especialidad': '450', 'nombre': 'ILUMINACION'},
#                    {'especialidad': '451', 'nombre': 'INTERPRETACION'},
#                    {'especialidad': '452', 'nombre': 'INTERPRETACION CON OBJETOS'},
#                    {'especialidad': '453', 'nombre': 'INTERPRETACION EN EL MUSICAL'},
#                    {'especialidad': '454', 'nombre': 'INTERPRETACION EN EL TEATRO DEL GESTO'},
#                    {'especialidad': '455', 'nombre': 'LITERATURA DRAMATICA'},
#                    {'especialidad': '456', 'nombre': 'TECNICAS ESCENICAS'},
#                    {'especialidad': '457', 'nombre': 'TECNICAS GRAFICAS'},
#                    {'especialidad': '458', 'nombre': 'TEORIA E HISTORIA DEL ARTE'},
#                    {'especialidad': '459', 'nombre': 'TEORIA TEATRAL'},
#                    {'especialidad': '460', 'nombre': 'LENGUAJE MUSICAL'},
#                    {'especialidad': '461', 'nombre': 'BAJO ELÉCTRICO'}, {'especialidad': '462', 'nombre': 'DULZAINA'},
#                    {'especialidad': '463', 'nombre': 'GUITARRA ELÉCTRICA'},
#                    {'especialidad': '464', 'nombre': 'REPERTORIO CON PIANO PARA DANZA'},
#                    {'especialidad': '465', 'nombre': 'CANTE FLAMENCO'},
#                    {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'}],
#           '0595': [{'especialidad': '001', 'nombre': 'ADORNO Y FIGURA'},
#                    {'especialidad': '002', 'nombre': 'ALFARERIA'}, {'especialidad': '003', 'nombre': 'ARQUEOLOGIA'},
#                    {'especialidad': '004', 'nombre': 'COMPOSICION ORNAMENTAL'},
#                    {'especialidad': '005', 'nombre': 'DECORACION SOBRE PASTAS CERAMICAS'}, {'especialidad': '006',
#                                                                                             'nombre': 'DERECHO USUAL Y NOCIONES CONTABILIDAD Y CORRESPONDENCIA COMERCIAL'},
#                    {'especialidad': '008', 'nombre': 'DIBUJO ARQUEOLOGICO'},
#                    {'especialidad': '009', 'nombre': 'DIBUJO ARTISTICO'},
#                    {'especialidad': '010', 'nombre': 'DIBUJO LINEAL'},
#                    {'especialidad': '011', 'nombre': 'FISICA Y QUIMICA APLICADAS A LA RESTAURACION'},
#                    {'especialidad': '013', 'nombre': 'HISTORIA DEL ARTE'},
#                    {'especialidad': '014', 'nombre': 'HISTORIA Y TECNICAS DEL LIBRO'},
#                    {'especialidad': '015', 'nombre': 'MANUFACTURA CERAMICA'},
#                    {'especialidad': '016', 'nombre': 'MATEMATICAS'},
#                    {'especialidad': '017', 'nombre': 'MATERIAS PRIMAS CERAMICAS'},
#                    {'especialidad': '018', 'nombre': 'MODELADO Y VACIADO'},
#                    {'especialidad': '019', 'nombre': 'MODELAJE DE FIGURAS'},
#                    {'especialidad': '020', 'nombre': 'MODELOS DE VAJILLERIA EN ESCAYOLA'},
#                    {'especialidad': '021', 'nombre': 'PROCEDIMIENTOS DE ILUSTRACION DEL LIBRO'},
#                    {'especialidad': '022', 'nombre': 'PROYECTOS DE ARTE DECORATIVO'},
#                    {'especialidad': '023', 'nombre': 'QUIMICA APLICADA A LA CERAMICA'},
#                    {'especialidad': '024', 'nombre': 'RESTAURACION DEL LIBRO'},
#                    {'especialidad': '025', 'nombre': 'RESTAURACION DE OBRAS ESCULTORICAS'},
#                    {'especialidad': '026', 'nombre': 'RESTAURACION Y TECNICAS ARQUEOLOGICAS'},
#                    {'especialidad': '027', 'nombre': 'RESTAURACION Y TECNICAS PICTORICAS'},
#                    {'especialidad': '028', 'nombre': 'SERIGRAFIA'}, {'especialidad': '029', 'nombre': 'TAQUIGRAFIA'},
#                    {'especialidad': '030', 'nombre': 'TAQUIMECANOGRAFIA'},
#                    {'especialidad': '031', 'nombre': 'TECNICA SEGOVIANA'},
#                    {'especialidad': '032', 'nombre': 'TECNICA TALAVERANA'},
#                    {'especialidad': '033', 'nombre': 'TECNICAS AUDIOVISUALES'},
#                    {'especialidad': '034', 'nombre': 'TECNICAS DE DISEÑO GRAFICO'},
#                    {'especialidad': '035', 'nombre': 'TECNICAS GRAFICAS INDUSTRIALES'},
#                    {'especialidad': '036', 'nombre': 'TECNOLOGIA QUIMICA Y TEXTIL'},
#                    {'especialidad': '037', 'nombre': 'TEORIA Y PRACTICA DEL DISEÑO'},
#                    {'especialidad': '038', 'nombre': 'TECNOLOGIA Y PROYECTOS DE BISUTERIA Y JOYERIA'},
#                    {'especialidad': '039', 'nombre': 'ELEMENTOS CONSTRUCTIVOS'},
#                    {'especialidad': '040', 'nombre': 'CONOCIMIENTO DE MATERIALES'},
#                    {'especialidad': '048', 'nombre': 'PREPARACION ELEMENTAL CERAMICA'},
#                    {'especialidad': '049', 'nombre': 'ANALISIS QUIMICOS DE CERAMICA'},
#                    {'especialidad': '051', 'nombre': 'MATERIALES Y ELEMENTOS DE CONSTRUCCION'},
#                    {'especialidad': '052', 'nombre': 'DECORACION ELEMENTAL CERAMICA'},
#                    {'especialidad': '054', 'nombre': 'PREPARACION CERAMICA'},
#                    {'especialidad': '056', 'nombre': 'COLORIDO CERAMICO'},
#                    {'especialidad': '057', 'nombre': 'CULTURA GENERAL CERAMICA'},
#                    {'especialidad': '065', 'nombre': 'TEORIA Y PRACTICA DE LA FOTOGRAFIA'},
#                    {'especialidad': '066', 'nombre': 'ANALISIS DE FORMA Y COLOR'},
#                    {'especialidad': '068', 'nombre': 'CERAMICA APLICADA A LA DECORACION'},
#                    {'especialidad': '069', 'nombre': 'COLORIDO Y PROCEDIMIENTOS PICTÓRICOS'},
#                    {'especialidad': '070', 'nombre': 'DIBUJO Y TECNICAS PICTORICAS'},
#                    {'especialidad': '071', 'nombre': 'DISEÑO INDUSTRIAL CERAMICO'},
#                    {'especialidad': '072', 'nombre': 'ENCUADERNACION'},
#                    {'especialidad': '074', 'nombre': 'FOTOGRAFÍA'},
#                    {'especialidad': '075', 'nombre': 'FOTOGRAFIA APLICADA A LA RESTAURACION'},
#                    {'especialidad': '080', 'nombre': 'TECNICAS DE COLORIDO APLICADO A LA CERAMICA'},
#                    {'especialidad': '083', 'nombre': 'DISEÑO ASISTIDO POR ORDENADOR'},
#                    {'especialidad': '084', 'nombre': 'TECNICAS MURALES'},
#                    {'especialidad': '085', 'nombre': 'RESTAURACION ARQUEOLOGICA'},
#                    {'especialidad': '501', 'nombre': 'CERÁMICA'},
#                    {'especialidad': '502', 'nombre': 'CONSERVACIÓN Y RESTAURACIÓN DE MATERIALES ARQUEOLÓGICOS'},
#                    {'especialidad': '503', 'nombre': 'CONSERVACIÓN Y RESTAURACIÓN DE OBRAS ESCULTÓRICAS'},
#                    {'especialidad': '504', 'nombre': 'CONSERVACIÓN Y RESTAURACIÓN DE OBRAS PICTÓRICAS'},
#                    {'especialidad': '505', 'nombre': 'CONSERVACIÓN Y RESTAURACIÓN DE TEXTILES'},
#                    {'especialidad': '506', 'nombre': 'CONSERVACIÓN Y RESTAURACIÓN DEL DOCUMENTO GRAFICO'},
#                    {'especialidad': '507', 'nombre': 'DIBUJO ARTÍSTICO Y COLOR'},
#                    {'especialidad': '508', 'nombre': 'DIBUJO TÉCNICO'},
#                    {'especialidad': '509', 'nombre': 'DISEÑO DE INTERIORES'},
#                    {'especialidad': '510', 'nombre': 'DISEÑO DE MODA'},
#                    {'especialidad': '511', 'nombre': 'DISEÑO DE PRODUCTO'},
#                    {'especialidad': '512', 'nombre': 'DISEÑO GRAFICO'},
#                    {'especialidad': '513', 'nombre': 'DISEÑO TEXTIL'},
#                    {'especialidad': '514', 'nombre': 'EDICIÓN DE ARTE'},
#                    {'especialidad': '515', 'nombre': 'FOTOGRAFÍA'},
#                    {'especialidad': '516', 'nombre': 'HISTORIA DEL ARTE'},
#                    {'especialidad': '517', 'nombre': 'JOYERÍA Y ORFEBRERÍA'},
#                    {'especialidad': '518', 'nombre': 'MATERIALES Y TECNOLOGÍA: CERAMICA Y VIDRIO'},
#                    {'especialidad': '519', 'nombre': 'MATERIALES Y TECNOLOGÍA: CONSERVACION Y RESTAURACION'},
#                    {'especialidad': '520', 'nombre': 'MATERIALES Y TECNOLOGÍA: DISEÑO'},
#                    {'especialidad': '521', 'nombre': 'MEDIOS AUDIOVISUALES'},
#                    {'especialidad': '522', 'nombre': 'MEDIOS INFORMÁTICOS'},
#                    {'especialidad': '523', 'nombre': 'ORGANIZACIÓN INDUSTRIAL Y LEGISLACIÓN'},
#                    {'especialidad': '524', 'nombre': 'VIDRIO'}, {'especialidad': '525', 'nombre': 'VOLUMEN'},
#                    {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'}],
#           '0596': [{'especialidad': '001', 'nombre': 'ALFARERIA'}, {'especialidad': '002', 'nombre': 'ALFOMBRAS'},
#                    {'especialidad': '004', 'nombre': 'BORDADOS Y ENCAJES'},
#                    {'especialidad': '005', 'nombre': 'CALCOGRAFIA Y XILOGRAFIA'},
#                    {'especialidad': '006', 'nombre': 'CERAMICA ARTISTICA'},
#                    {'especialidad': '007', 'nombre': 'CORTE Y CONFECCION'},
#                    {'especialidad': '008', 'nombre': 'DECORACION'},
#                    {'especialidad': '009', 'nombre': 'DECORACION CERAMICA'},
#                    {'especialidad': '010', 'nombre': 'DECORACION SOBRE LOZA'},
#                    {'especialidad': '011', 'nombre': 'DECORACION SOBRE PORCELANA'},
#                    {'especialidad': '012', 'nombre': 'DELINEACION'},
#                    {'especialidad': '013', 'nombre': 'DIBUJO PUBLICITARIO'},
#                    {'especialidad': '014', 'nombre': 'DISEÑO INDUSTRIAL'},
#                    {'especialidad': '015', 'nombre': 'DISEÑO DE FIGURINES'},
#                    {'especialidad': '016', 'nombre': 'DORADO Y POLICROMIA'},
#                    {'especialidad': '017', 'nombre': 'EBANISTERIA'},
#                    {'especialidad': '018', 'nombre': 'EBANISTERIA Y MAQUETERIA'},
#                    {'especialidad': '019', 'nombre': 'ENCUADERNACION'},
#                    {'especialidad': '020', 'nombre': 'ESGRAFIADO'}, {'especialidad': '021', 'nombre': 'ESMALTES'},
#                    {'especialidad': '022', 'nombre': 'ESTAMPADO TEXTIL'},
#                    {'especialidad': '023', 'nombre': 'FORJA ARTISTICA'},
#                    {'especialidad': '024', 'nombre': 'FORJA Y CERRAJERIA'},
#                    {'especialidad': '025', 'nombre': 'FOTOGRABADO'},
#                    {'especialidad': '026', 'nombre': 'FOTOGRABADO Y TIPOGRAFIA'},
#                    {'especialidad': '027', 'nombre': 'FOTOGRAFIA ARTISTICA'},
#                    {'especialidad': '028', 'nombre': 'FOTOGRAFIA Y PROCESO DE REPRODUCCION'},
#                    {'especialidad': '029', 'nombre': 'GRABADO'}, {'especialidad': '031', 'nombre': 'HORNOS'},
#                    {'especialidad': '032', 'nombre': 'INVESTIGACION DE MATERIAS PRIMAS CERAMICAS'},
#                    {'especialidad': '033', 'nombre': 'JOYERIA'},
#                    {'especialidad': '035', 'nombre': 'LABRADO Y REPUJADO EN CUERO'},
#                    {'especialidad': '036', 'nombre': 'LITOGRAFIA'},
#                    {'especialidad': '038', 'nombre': 'LOZA Y PORCELANA'},
#                    {'especialidad': '039', 'nombre': 'MANUFACTURA CERAMICA'},
#                    {'especialidad': '040', 'nombre': 'MATRICERIA'},
#                    {'especialidad': '041', 'nombre': 'METALISTERIA ARTISTICA'},
#                    {'especialidad': '043', 'nombre': 'MODELISMO Y MAQUETISMO'},
#                    {'especialidad': '044', 'nombre': 'MOLDES Y REPRODUCCIONES'},
#                    {'especialidad': '045', 'nombre': 'MOSAICOS ROMANOS'},
#                    {'especialidad': '046', 'nombre': 'MUÑEQUERIA ARTISTICA'},
#                    {'especialidad': '047', 'nombre': 'ORFEBRERIA'},
#                    {'especialidad': '048', 'nombre': 'PASTAS Y HORNOS'},
#                    {'especialidad': '049', 'nombre': 'PATRONAJE, ESCALADO Y TECNICAS DE CONFECCION'},
#                    {'especialidad': '050', 'nombre': 'QUIMICA APLICADA A LA CERAMICA'},
#                    {'especialidad': '051', 'nombre': 'REPUJADO EN CUERO'},
#                    {'especialidad': '052', 'nombre': 'REPUJADO EN METAL'},
#                    {'especialidad': '053', 'nombre': 'RESTAURACION DE DIBUJOS Y GRABADOS'},
#                    {'especialidad': '054', 'nombre': 'RESTAURACION DE ENCUADERNACIONES'},
#                    {'especialidad': '055', 'nombre': 'RESTAURACION DE MANUSCRITOS E IMPRESOS'},
#                    {'especialidad': '056', 'nombre': 'RESTAURACION DE TAPICES'},
#                    {'especialidad': '057', 'nombre': 'MODELISMO INDUSTRIAL'},
#                    {'especialidad': '058', 'nombre': 'TALLA DE MADERA'},
#                    {'especialidad': '059', 'nombre': 'TALLA EN PIEDRA'},
#                    {'especialidad': '060', 'nombre': 'TALLA DE PIEDRA Y MADERA'},
#                    {'especialidad': '061', 'nombre': 'TAPICES Y ALFOMBRAS'},
#                    {'especialidad': '062', 'nombre': 'TAQUIMECANOGRAFIA'},
#                    {'especialidad': '063', 'nombre': 'TECNICAS DE JOYERIA'},
#                    {'especialidad': '064', 'nombre': 'TEXTILES ARTISTICOS'},
#                    {'especialidad': '065', 'nombre': 'VACIADO Y MODELADO'},
#                    {'especialidad': '066', 'nombre': 'VIDRIERAS ARTISTICAS'},
#                    {'especialidad': '068', 'nombre': 'INICIACION A LA RESTAURACION'},
#                    {'especialidad': '069', 'nombre': 'RESTAURACION CERAMICA'},
#                    {'especialidad': '070', 'nombre': 'TECNICAS DE DISEÑO INDUSTRIAL'},
#                    {'especialidad': '071', 'nombre': 'TIPOGRAFÍA'}, {'especialidad': '072', 'nombre': 'VACIADO'},
#                    {'especialidad': '074', 'nombre': 'TALLA ORNAMENTAL'},
#                    {'especialidad': '081', 'nombre': 'ABANIQUERÍA'},
#                    {'especialidad': '087', 'nombre': 'ARTESANIA CANARIA'},
#                    {'especialidad': '088', 'nombre': 'ARTES GRAFICAS'},
#                    {'especialidad': '091', 'nombre': 'DIBUJOS ANIMADOS'},
#                    {'especialidad': '092', 'nombre': 'DIBUJO DEL MUEBLE'},
#                    {'especialidad': '093', 'nombre': 'FIGURINES'},
#                    {'especialidad': '094', 'nombre': 'REPUJADO EN CUERO Y METAL'},
#                    {'especialidad': '095', 'nombre': 'RESTAURACION'}, {'especialidad': '097', 'nombre': 'SERIGRAFIA'},
#                    {'especialidad': '098', 'nombre': 'MOLDEO Y MONTAJE DE PORCELANA'},
#                    {'especialidad': '099', 'nombre': 'FORJA Y FUNDICION'},
#                    {'especialidad': '101', 'nombre': 'MARIONETAS'},
#                    {'especialidad': '102', 'nombre': 'REFLEJOS METALICOS'},
#                    {'especialidad': '104', 'nombre': 'TAQUIGRAFIA'},
#                    {'especialidad': '107', 'nombre': 'DISEÑO GRAFICO ASISTIDO POR ORDENADOR'},
#                    {'especialidad': '108', 'nombre': 'REPRODUCCION E IMPRESION'},
#                    {'especialidad': '109', 'nombre': 'CERRAJERIA Y FORJA'},
#                    {'especialidad': '110', 'nombre': 'CONSTRUCCIONES NAVALES'},
#                    {'especialidad': '115', 'nombre': 'IMAGINERIA CASTELLANA'},
#                    {'especialidad': '117', 'nombre': 'METALISTERIA (DAMASQUINADO)'},
#                    {'especialidad': '600', 'nombre': 'INSPECCION EDUCATIVA'},
#                    {'especialidad': '601', 'nombre': 'ARTESANIA Y ORNAMENTACION CON ELEMENTOS VEGETALES'},
#                    {'especialidad': '602', 'nombre': 'BORDADOS Y ENCAJES'},
#                    {'especialidad': '603', 'nombre': 'COMPLEMENTOS Y ACCESORIOS'},
#                    {'especialidad': '604', 'nombre': 'DORADO Y POLICROMIA'},
#                    {'especialidad': '605', 'nombre': 'EBANISTERIA ARTISTICA'},
#                    {'especialidad': '606', 'nombre': 'ENCUADERNACION ARTISTICA'},
#                    {'especialidad': '607', 'nombre': 'ESMALTES'},
#                    {'especialidad': '608', 'nombre': 'FOTOGRAFIA Y PROCESOS DE REPRODUCCION'},
#                    {'especialidad': '609', 'nombre': 'MODELISMO Y MAQUETISMO'},
#                    {'especialidad': '610', 'nombre': 'MOLDES Y REPRODUCCIONES'},
#                    {'especialidad': '611', 'nombre': 'MUSIVARIA'},
#                    {'especialidad': '612', 'nombre': 'TALLA EN PIEDRA Y MADERA'},
#                    {'especialidad': '613', 'nombre': 'TECNICAS CERAMICAS'},
#                    {'especialidad': '614', 'nombre': 'TECNICAS DE GRABADO Y ESTAMPACION'},
#                    {'especialidad': '615', 'nombre': 'TECNICAS DE JOYERIA Y BISUTERIA'},
#                    {'especialidad': '616', 'nombre': 'TECNICAS DE ORFEBRERIA Y PLATERIA'},
#                    {'especialidad': '617', 'nombre': 'TECNICAS DE PATRONAJE Y CONFECCION'},
#                    {'especialidad': '618', 'nombre': 'TECNICAS DEL METAL'},
#                    {'especialidad': '619', 'nombre': 'TECNICAS MURALES'},
#                    {'especialidad': '620', 'nombre': 'TECNICAS TEXTILES'},
#                    {'especialidad': '621', 'nombre': 'TECNICAS VIDRIERAS'}],
#           '0597': [{'especialidad': '041', 'nombre': 'COMPENSATORIA (A.D.)'},
#                    {'especialidad': 'AL', 'nombre': 'AUDICION Y LENGUAJE'},
#                    {'especialidad': 'AS', 'nombre': 'AUDICION Y LENGUAJE'},
#                    {'especialidad': 'CK', 'nombre': 'COMPENSATORIA ( SEC. )'},
#                    {'especialidad': 'CN', 'nombre': 'CIENCIAS DE LA NATURALEZA'},
#                    {'especialidad': 'CO', 'nombre': 'EDUCACION COMPENSATORIA'},
#                    {'especialidad': 'CS', 'nombre': 'CIENCIAS SOCIALES'},
#                    {'especialidad': 'EA', 'nombre': 'EDUCACIÓN DE ADULTOS'},
#                    {'especialidad': 'EAI', 'nombre': 'INGLES ( ED. ADULTOS )'},
#                    {'especialidad': 'EF', 'nombre': 'EDUCACION FISICA'},
#                    {'especialidad': 'EI', 'nombre': 'EDUCACION INFANTIL'}, {'especialidad': 'EU', 'nombre': 'EUSKERA'},
#                    {'especialidad': 'FA', 'nombre': 'LENGUA EXTRANJERA: ALEMÁN'},
#                    {'especialidad': 'FB', 'nombre': 'CATALAN (BALEARES)'}, {'especialidad': 'FC', 'nombre': 'CATALAN'},
#                    {'especialidad': 'FF', 'nombre': 'LENGUA EXTRANJERA: FRANCÉS'},
#                    {'especialidad': 'FG', 'nombre': 'GALLEGO'},
#                    {'especialidad': 'FI', 'nombre': 'LENGUA EXTRANJERA: INGLÉS'},
#                    {'especialidad': 'FL', 'nombre': 'FILOLOGIA: LENGUA CASTELLANA'},
#                    {'especialidad': 'FN', 'nombre': 'VASCUENCE (NAVARRA)'},
#                    {'especialidad': 'FR', 'nombre': 'LENGUA EXTRANJERA: FRANCES'},
#                    {'especialidad': 'FS', 'nombre': 'EDUCACION FISICA'},
#                    {'especialidad': 'FV', 'nombre': 'VALENCIANO'},
#                    {'especialidad': 'GH', 'nombre': 'GEOGRAFIA E HISTORIA'},
#                    {'especialidad': 'GS', 'nombre': 'GARANTIA SOCIAL'},
#                    {'especialidad': 'LL', 'nombre': 'LENGUA Y LITERATURA'},
#                    {'especialidad': 'MA', 'nombre': 'MATEMATICAS'},
#                    {'especialidad': 'MC', 'nombre': 'MATEMATICAS Y CIENCIAS DE LA NATURALEZA'},
#                    {'especialidad': 'MS', 'nombre': 'MUSICA (SEC.)'}, {'especialidad': 'MU', 'nombre': 'MUSICA'},
#                    {'especialidad': 'PCP', 'nombre': 'P.C.P.I.'}, {'especialidad': 'PRI', 'nombre': 'PRIMARIA'},
#                    {'especialidad': 'PS', 'nombre': 'PEDAGOGIA TERAPEUTICA (SEC.)'},
#                    {'especialidad': 'PT', 'nombre': 'PEDAGOGIA TERAPEUTICA'}],
#           '0598': [{'especialidad': '001', 'nombre': 'COCINA Y PASTELERIA'},
#                    {'especialidad': '002', 'nombre': 'ESTETICA'},
#                    {'especialidad': '003', 'nombre': 'FABRICACION E INSTALACION DE CARPINTERIA Y MUEBLE'},
#                    {'especialidad': '004', 'nombre': 'MANTENIMIENTO DE VEHICULOS'},
#                    {'especialidad': '005', 'nombre': 'MECANIZADO Y MANTENIMIENTO DE MAQUINAS'},
#                    {'especialidad': '006', 'nombre': 'PATRONAJE Y CONFECCION'},
#                    {'especialidad': '007', 'nombre': 'PELUQUERIA'},
#                    {'especialidad': '008', 'nombre': 'PRODUCCION EN ARTES GRAFICAS'},
#                    {'especialidad': '009', 'nombre': 'SERVICIOS DE RESTAURACION'},
#                    {'especialidad': '010', 'nombre': 'SOLDADURA'}]}
