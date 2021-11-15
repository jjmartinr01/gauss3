# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.db import models
from django.db.models import Q
from django.utils.timezone import now

from cupo.habilitar_permisos import Miembro_Equipo_Directivo
from entidades.views import get_entidad_general
from gauss.funciones import pass_generator
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
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'Cupos de profesorado'
        ordering = ['-creado']

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
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')

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
        tipo_centro = self.ronda_centro.entidad.entidadextra.tipo_centro
        if 'C.E.I.P.' in tipo_centro or 'C.R.A.' in tipo_centro:
            departamentos = self.plantillaxls_set.all().values('puesto', 'x_puesto').distinct()
            for d in departamentos:
                DepEntidad.objects.get_or_create(ronda=self.ronda_centro, nombre=d['puesto'], clave_ex=d['x_puesto'])
        else:
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
            try:
                act, c = Actividad.objects.get_or_create(entidad=self.ronda_centro.entidad, clave_ex=a['x_actividad'])
                if c:
                    act.requiere_unidad = b[a['l_requnidad']]
                    act.nombre = a['actividad']
                    act.requiere_materia = b[a['docencia']]
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
        try:
            cargo, c = Cargo.objects.get_or_create(entidad=self.ronda_centro.entidad, clave_cargo='g_docente',
                                                   borrable=False)
        except:
            Cargo.objects.filter(entidad=self.ronda_centro.entidad, clave_cargo='g_docente').delete()
            cargo = Cargo.objects.create(entidad=self.ronda_centro.entidad, clave_cargo='g_docente', borrable=False)
        cargo.cargo = 'Docente'
        cargo.save()
        for code_nombre in cargo_data['permisos']:
            cargo.permisos.add(Permiso.objects.get(code_nombre=code_nombre))
        return cargo

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
        cargo = self.carga_cargo_g_docente()
        for ge in ges:
            if not ge['x_docente'] in x_docentes:
                x_docentes.append(ge['x_docente'])
                last_name, first_name = ge['docente'].split(', ')
                clave_ex, dni, puesto, x_puesto, x_departamento = ge['x_docente'], ge['dni'], ge['puesto'], ge[
                    'x_puesto'], ge['x_departamento']
                dni_inicial = dni
                if len(dni) == 8:
                    dni = '0%s' % dni
                username, email = ge['email'].split('@')[0], ge['email']
                try:
                    if len(dni_inicial) == 8:
                        try:
                            gauser = Gauser.objects.get(dni=dni_inicial)
                        except:
                            gauser = Gauser.objects.get(dni=dni)
                    else:
                        gauser = Gauser.objects.get(dni=dni)
                except Exception as msg:
                    log = 'Error: %s. dni %s - username %s' % (str(msg), dni, username)
                    LogCarga.objects.create(g_e=self.g_e, log=log)
                    try:
                        gex = Gauser_extra.objects.get(clave_ex=clave_ex, ronda=self.ronda_centro)
                        gauser = gex.gauser
                        gauser.set_password(pass_generator(size=9))
                        log = 'Sin embargo existe usuario con clave_x: %s - %s' % (clave_ex, gex)
                        logger.warning(log)
                        LogCarga.objects.create(g_e=self.g_e, log=log)
                    except:
                        try:
                            gauser = Gauser.objects.get(email=email)
                            gauser.set_password(pass_generator(size=9))
                            log = 'Sin embargo existe usuario con email: %s - %s' % (email, gauser)
                            logger.warning(log)
                            LogCarga.objects.create(g_e=self.g_e, log=log)
                        except:
                            try:
                                gauser = Gauser.objects.get(username=username)
                                gauser.set_password(pass_generator(size=9))
                                log = 'Ya existe un usuario: %s' % username
                                logger.warning(log)
                                LogCarga.objects.create(g_e=self.g_e, log=log)
                            except:
                                gauser = Gauser.objects.create_user(username, email=email, last_login=now(),
                                                                    password=pass_generator(size=9))
                                log = 'Creado usuario: %s' % (gauser)
                                LogCarga.objects.create(g_e=self.g_e, log=log)
                try:
                    gauser.username = username
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
            for apartado in self.estructura_po:
                for nombre_columna, contenido_columna in self.estructura_po[apartado].items():
                    LogCarga.objects.create(g_e=gex, log='Inicio carga PDocenteCol %s - %s'% (contenido_columna['codecol'], contenido_columna['horas_base']))
                    try:
                        pdc = PDocenteCol.objects.get(pd=pd, codecol=contenido_columna['codecol'],
                                                          periodos_base=contenido_columna['horas_base'])
                        LogCarga.objects.create(g_e=gex, log='existe PDocenteCol %s' % contenido_columna['codecol'])
                    except:
                        pdc = PDocenteCol.objects.create(pd=pd, codecol=contenido_columna['codecol'],
                                                          periodos_base=contenido_columna['horas_base'])
                        LogCarga.objects.create(g_e=gex, log='Creado PDocenteCol %s' % contenido_columna['codecol'])
                    # pdc, c = PDocenteCol.objects.get_or_create(pd=pd, codecol=contenido_columna['codecol'],
                    #                                            periodos_base=contenido_columna['horas_base'])
                    pdc.nombre = nombre_columna
                    sesiones_id = sextras.filter(contenido_columna['q']).values_list('sesion__id', flat=True)
                    pdc.sesiones.add(*Sesion.objects.filter(id__in=sesiones_id))
                    LogCarga.objects.create(g_e=gex, log='Added sesiones a PDocenteCol')
                    # pdc.periodos = pdc.sesiones.count() # pdc.periodos se calcula automáticamente en pdc.save()
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
        try:
            miembro_equipo_directivo = Cargo.objects.get(entidad=self.ronda_centro.entidad, clave_cargo='202006011113')
        except:
            miembro_equipo_directivo = Cargo.objects.create(entidad=self.ronda_centro.entidad, borrable=False,
                                                            cargo='Miembro del Equipo Directivo',
                                                            nivel=1, clave_cargo='202006011113')
            miembro_equipo_directivo.permisos.add(*permisos)
        for pxls in self.plantillaxls_set.filter(x_actividad__in=['529', '530', '532']):
            try:
                gex = Gauser_extra.objects.get(ronda=self.ronda_centro, clave_ex=pxls.x_docente)
                gex.cargos.add(miembro_equipo_directivo)
            except:
                pass

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
        LogCarga.objects.create(g_e=self.g_e, log="Inicio habilitar miembros equipo directivo")
        self.habilitar_miembros_equipo_directivo()
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

    @property
    def num_sesiones(self):
        p = 0
        for pdcol in self.pdocentecol_set.all():
            p += pdcol.sesiones.all().count()
        return p

    @property
    def minutos_periodo(self):
        tipo_centro = self.g_e.ronda.entidad.entidadextra.tipo_centro
        if 'I.E.S.' in tipo_centro:
            mins_periodo = 55
        elif 'C.E.P.A' in tipo_centro:
            mins_periodo = 45
        elif 'C.E.I.P.' in tipo_centro:
            mins_periodo = 60
        elif 'C.R.A.' in tipo_centro:
            mins_periodo = 60
        elif self.g_e.jornada_contratada in ['23:00', '24:00', '25:00', '16:40', '8:20']:
            mins_periodo = 60
        else:
            mins_periodo = 55
        return mins_periodo

    @property
    def num_minutos_docencia(self):
        minutos = 0
        for pdcol in self.pdocentecol_set.all():
            minutos += pdcol.minutos
        return minutos

    @property
    def num_periodos_docencia(self):
        return int(self.num_minutos_docencia / self.minutos_periodo)

    @property
    def num_periodos_basicos(self):
        minutos = 0
        for pdcol in self.pdocentecol_set.all():
            if pdcol.periodos_base:
                minutos += pdcol.minutos
        return int(minutos / self.minutos_periodo)

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

    @property
    def num_sesiones(self):
        return self.sesiones.count()

    @property
    def num_periodos_sesiones(self):
        num_minutos = 0
        for s in self.sesiones.all():
            num_minutos += s.minutos
        return int(num_minutos / self.pd.minutos_periodo)

    @property
    def minutos(self):
        num_minutos = 0
        for s in self.sesiones.all():
            num_minutos += s.minutos
        return num_minutos + self.periodos_added * self.pd.minutos_periodo

    @property
    def num_periodos(self):
        return int(self.minutos / self.pd.minutos_periodo)

    class Meta:
        ordering = ['codecol',]

    def save(self, *args, **kwargs):
        if self.sesiones.all().count() > 0:
            self.periodos = self.num_periodos
        super(PDocenteCol, self).save(*args, **kwargs)

    def __str__(self):
        return '%s - %s - (%s periodos y %s minutos)' % (self.pd, self.nombre, self.periodos, self.minutos)


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
