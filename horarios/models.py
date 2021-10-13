# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.db import models
from django.db.models import Q
from datetime import date
from entidades.models import Entidad, Subentidad, Ronda, Dependencia, Gauser_extra
from estudios.models import Curso as ECurso, Gauser_extra_estudios
from estudios.models import Grupo as EGrupo
from estudios.models import Materia as EMateria
from gauss.funciones import pass_generator, usuarios_ronda

DIAS_SEMANA = (
    ('lunes', 'lunes'),
    ('martes', 'martes'),
    ('miercoles', 'miércoles'),
    ('jueves', 'jueves'),
    ('viernes', 'viernes'),
    ('sabado', 'sábado'),
    ('domingo', 'domingo'),
)

DIAS = (
    (1, 'lunes'),
    (2, 'martes'),
    (3, 'miércoles'),
    (4, 'jueves'),
    (5, 'viernes'),
    (6, 'sábado'),
    (7, 'domingo'),
)

# ETAPAS = (('ba', 'Infantil'), ('ca', 'Primaria'), ('da', 'Secundaria'), ('ea', 'FP Básica'), ('fa', 'Bachillerato'),
#           ('ga', 'FP Grado Medio'), ('ha', 'FP Grado Superior'))
ETAPAS = (('ba', 'Infantil'), ('ca', 'Primaria'), ('da', 'Secundaria'), ('ea', 'FP Básica'), ('fa', 'Bachillerato'),
          ('ga', 'FP Grado Medio'), ('ha', 'FP Grado Superior'), ('ia', 'Enseñanzas Iniciales de Personas Adultas'),
          ('ja', 'Educación Secundaria de Personas Adultas'),
          ('ka', 'Educación Secundaria de Personas Adultas a Distancia Semipresencial'),
          ('la', 'Educación Secundaria de Personas Adultas a Distancia'), ('ma', 'Educación para Personas Adultas'),
          ('na', 'Preparación Pruebas de Acceso a CCFF'), ('za', 'Etapa no identificada'))


# class Curso(models.Model):
#     entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
#     ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
#     nombre = models.CharField("Curso", max_length=150)
#     etapa = models.CharField("Nombre de la etapa", max_length=75, null=True, blank=True, choices=ETAPAS)
#     tipo = models.CharField("Tipo de estudio", max_length=75, null=True, blank=True)
#     nombre_especifico = models.CharField("Nombre específico", max_length=150, null=True, blank=True)
#     familia = models.CharField("Departamento", max_length=150, null=True, blank=True)
#     observaciones = models.TextField("Observaciones", null=True, blank=True)
#     grupos = models.ManyToManyField(Subentidad, blank=True)
#     edad = models.IntegerField("Edad con la que puede iniciarse este curso", blank=True, null=True)
#     clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
#
#     class Meta:
#         ordering = ['etapa', 'tipo', 'nombre']
#
#     def __str__(self):
#         return '%s (%s)' % (self.nombre, self.ronda.entidad.name)


# Ligar un Grupo a un curso es problemático porque alumnos de un grupo pueden pertenecer a varios cursos. Por ejemplo
# los alumnos del grupo 1Bach A pueden pertenecer a los cursos de Ciencias y de Artes
# class Grupo(models.Model):
#     ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
#     cursos = models.ManyToManyField(Curso, blank=True)
#     nombre = models.CharField("Nombre", max_length=100)
#     observaciones = models.TextField("Observaciones", null=True, blank=True)
#     clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
#
#     @property
#     def entidad(self):
#         return self.ronda.entidad
#
#     @property
#     def tutores(self):
#         tutores_id = Gauser_extra_horarios.objects.filter(grupo__id=self.id).values_list('tutor__id')
#         return Gauser_extra.objects.filter(id__in=tutores_id).distinct()
#
#     @property
#     def cotutores(self):
#         cotutores_id = Gauser_extra_horarios.objects.filter(grupo__id=self.id).values_list('cotutor__id')
#         return Gauser_extra.objects.filter(id__in=cotutores_id).distinct()
#
#     @property
#     def gausers_extra_horarios(self):
#         return Gauser_extra_horarios.objects.filter(grupo__id=self.id)
#
#     class Meta:
#         ordering = ['nombre']
#
#     def __str__(self):
#         cursos = self.cursos.all().values_list('nombre', flat=True)
#         return '%s - %s - %s' % (self.nombre, ', '.join(cursos), self.ronda)


# class Materia(models.Model):
#     curso = models.ForeignKey(Curso, null=True, blank=True, on_delete=models.CASCADE)
#     nombre = models.CharField("Nombre de la materia", max_length=100, null=True, blank=True)
#     abreviatura = models.CharField("Abreviatura de la materia", max_length=20, null=True, blank=True)
#     horas = models.IntegerField("Número de horas a impartir por semana", null=True, blank=True)
#     duracion = models.IntegerField('Horas totales previstas para impartir toda la materia', blank=True, null=True)
#     observaciones = models.TextField("Observaciones", null=True, blank=True)
#     clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
#
#     @property
#     def entidad(self):
#         return self.curso.ronda.entidad
#
#     class Meta:
#         ordering = ['curso', 'nombre']
#
#     def __str__(self):
#         curso_nombre = self.curso.nombre if self.curso else 'No asignada a un curso'
#         return '%s - %s (%s horas)' % (self.nombre, curso_nombre, self.horas)


class Horario(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre dado al horario', blank=True, null=True, max_length=200)
    descripcion = models.TextField("Breve descripción", blank=True, null=True, default='')
    lunes = models.BooleanField('Lunes?', default=True)
    martes = models.BooleanField('Martes?', default=True)
    miercoles = models.BooleanField('Miércoles?', default=True)
    jueves = models.BooleanField('Jueves?', default=True)
    viernes = models.BooleanField('Viernes?', default=True)
    sabado = models.BooleanField('Sábado?', default=False)
    domingo = models.BooleanField('Domingo?', default=False)
    predeterminado = models.BooleanField("Horario predeterminado?", default=False)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    @property
    def pixels_hora(self):
        return 60

    @property
    def pixels_minuto(self):
        return 2

    @property
    def pixels_offset(self):
        return 50

    def get_horario_grupo(self, grupo):
        """
        :param grupo: Grupo
        :return: dictionary {tramo_string1: {1: sesiones, 2: sesiones ...}, tramo_string2: {1: sesiones, ...
        """
        # Días para los cuales se calcula el horario
        dias_dict = {1: self.lunes, 2: self.martes, 3: self.miercoles, 4: self.jueves, 5: self.viernes,
                     6: self.sabado, 7: self.domingo}
        dias = [d for d, valor in dias_dict.items() if valor]
        sse_ids = SesionExtra.objects.filter(sesion__horario=self, grupo=grupo).values_list('sesion__id', flat=True)
        ss = Sesion.objects.filter(id__in=sse_ids)
        tramos = ss.values_list('hora_inicio', 'hora_inicio_cadena', 'hora_fin_cadena').distinct()
        horario = {}
        for inicio, s_inicio, s_fin in tramos:
            tramo = '%s-%s' % (s_inicio, s_fin)
            sesiones_por_dia = {}
            for d in dias:
                try:
                    sesiones_por_dia[d] = ss.get(hora_inicio=inicio, dia=d)
                except:
                    sesiones_por_dia[d] = Sesion.objects.none()
            horario[tramo] = sesiones_por_dia
        return horario

    def get_horario(self, docente):
        """
        :param docente: Gauser_extra
        :return: dictionary {tramo_string1: {1: sesiones, 2: sesiones ...}, tramo_string2: {1: sesiones, ...
        """
        # Días para los cuales se calcula el horario
        dias_dict = {1: self.lunes, 2: self.martes, 3: self.miercoles, 4: self.jueves, 5: self.viernes,
                     6: self.sabado, 7: self.domingo}
        dias = [d for d, valor in dias_dict.items() if valor]
        ss = self.sesion_set.filter(g_e=docente)
        tramos = ss.values_list('hora_inicio', 'hora_inicio_cadena', 'hora_fin_cadena').distinct()
        horario = {}
        for inicio, s_inicio, s_fin in tramos:
            tramo = '%s-%s' % (s_inicio, s_fin)
            sesiones_por_dia = {}
            for d in dias:
                try:
                    sesiones_por_dia[d] = ss.get(hora_inicio=inicio, dia=d)
                except:
                    sesiones_por_dia[d] = Sesion.objects.none()
            horario[tramo] = sesiones_por_dia
        return horario

    def sesiones_aula(self, aula):
        return self.sesion_set.filter(dependencia=aula)

    def horas_aula(self, aula):
        hs = self.sesion_set.filter(dependencia=aula).values_list('hora_inicio', 'hora_fin').distinct().order_by(
            'hora_inicio')
        return [{'top': (hora[0] - hs[0][0]) * self.pixels_minuto + self.pixels_offset,
                 'height': (hora[1] - hora[0]) * self.pixels_minuto,
                 'inicio': hora[0], 'fin': hora[1]} for hora in hs]

    def hora_inicio_aula(self, aula):
        horas = self.sesion_set.filter(dependencia=aula).values_list('inicio', 'fin').distinct().order_by('inicio')
        return horas[0][0]

    def hora_fin_aula(self, aula):
        horas = self.sesion_set.filter(dependencia=aula).values_list('inicio', 'fin').distinct().order_by('inicio')
        return horas.last()[1]

    def sesiones_grupo(self, grupo):
        return self.sesion_set.filter(grupo=grupo)

    def horas_grupo(self, grupo):
        hs = self.sesion_set.filter(grupo=grupo).values_list('hora_inicio', 'hora_fin').distinct().order_by(
            'hora_inicio')
        return [{'top': (hora[0] - hs[0][0]) * self.pixels_minuto + self.pixels_offset,
                 'height': (hora[1] - hora[0]) * self.pixels_minuto,
                 'inicio': hora[0], 'fin': hora[1]} for hora in hs]

    def hora_inicio_grupo(self, grupo):
        horas = self.sesion_set.filter(grupo=grupo).values_list('inicio', 'fin').distinct().order_by('inicio')
        return horas[0][0]

    def hora_fin_grupo(self, grupo):
        horas = self.sesion_set.filter(grupo=grupo).values_list('inicio', 'fin').distinct().order_by('inicio')
        return horas.last()[1]

    def sesiones_ge(self, ge):
        return self.sesion_set.filter(g_e=ge)

    def horas_ge(self, ge):
        # hs = self.sesion_set.filter(g_e=ge).values_list('inicio', 'fin').distinct().order_by('inicio')
        # return [{'top': (hora[0].hour * 60 + hora[0].minute - hs[0][0].hour * 60 - hs[0][
        #     0].minute) * self.pixels_minuto + self.pixels_offset,
        #          'height': (hora[1].hour * 60 + hora[1].minute - hora[0].hour * 60 - hora[
        #              0].minute) * self.pixels_minuto,
        #          'inicio': hora[0], 'fin': hora[1]} for hora in hs]
        hs = self.sesion_set.filter(g_e=ge).values_list('hora_inicio', 'hora_fin', 'hora_inicio_cadena',
                                                        'hora_fin_cadena').distinct().order_by('hora_inicio')
        return [{'top': (hora[0] - hs[0][0]) * self.pixels_minuto + self.pixels_offset,
                 'height': (hora[1] - hora[0]) * self.pixels_minuto,
                 'inicio': hora[0], 'fin': hora[1], 'his': hora[2], 'hfs': hora[3]} for hora in hs]

    def hora_inicio_ge(self, ge):
        horas = self.sesion_set.filter(g_e=ge).values_list('hora_inicio', 'hora_fin').distinct().order_by('hora_inicio')
        return horas[0][0]

    def hora_fin_ge(self, ge):
        horas = self.sesion_set.filter(g_e=ge).values_list('hora_inicio', 'hora_fin').distinct().order_by('hora_inicio')
        return horas.last()[1]

    @property
    def horas(self):
        return Tramo_horario.objects.filter(horario=self).values_list('inicio', 'fin').order_by('inicio')
        # return self.sesion_set.all().values_list('inicio', 'fin').distinct().order_by('inicio')

    @property
    def hora_inicio(self):
        horas = self.sesion_set.all().values_list('hora_inicio', 'hora_fin').distinct().order_by('hora_inicio')
        return horas[0][0]

    @property
    def hora_fin(self):
        horas = self.sesion_set.all().values_list('hora_inicio', 'hora_fin').distinct().order_by('hora_inicio')
        return horas.last()[1]

    @property
    def horario_height(self):
        try:
            horas = self.sesion_set.all().values_list('hora_inicio', 'hora_fin').distinct().order_by('hora_inicio')
            l = horas.last()[1]
            i = horas[0][0]
            return (l - i + 5) * self.pixels_minuto + self.pixels_offset
        except:
            return 400

    @property
    def subentidades(self):
        ids = Sesion.objects.filter(tramo_horario__horario=self).values_list('subentidad__id', flat=True).distinct()
        return Subentidad.objects.filter(id__in=ids, fecha_expira__gt=date.today()).distinct()

    @property
    def dias_con_sesion(self):
        return self.sesion_set.all().values_list('dia', flat=True).distinct()

    @property
    def dias(self):
        d = {}
        if self.lunes: d['lunes'] = 'Lunes'
        if self.martes: d['martes'] = 'Martes'
        if self.miercoles: d['miercoles'] = 'Miércoles'
        if self.jueves: d['jueves'] = 'Jueves'
        if self.viernes: d['viernes'] = 'Viernes'
        if self.sabado: d['sabado'] = 'Sábado'
        if self.domingo: d['domingo'] = 'Domingo'
        return d

    @property
    def dias_number(self):
        d = []
        if self.lunes: d.append(1)
        if self.martes: d.append(2)
        if self.miercoles: d.append(3)
        if self.jueves: d.append(4)
        if self.viernes: d.append(5)
        if self.sabado: d.append(6)
        if self.domingo: d.append(7)
        return d

    def horario_guardias(self, dia):
        gs = []
        tramos = self.sesion_set.all().values_list('horario', 'hora_inicio_cadena',
                                                   'hora_fin_cadena').distinct().order_by('hora_inicio')
        for tramo in tramos:
            ss = SesionExtra.objects.filter(sesion__horario=self, sesion__hora_inicio_cadena=tramo[1],
                                            actividad__guardia=True, sesion__dia=dia).distinct()
            gs.append({'tramo': tramo, 'sesiones': ss})
        # g_es = usuarios_ronda(self.entidad.ronda)
        # gs = []
        # for hora in self.horas:
        #     ss = Sesion.objects.filter(horario=self, inicio=hora[0], fin=hora[1], actividad__guardia=True, dia=dia,
        #                                g_e__in=g_es).distinct()
        #     gs.append({'hora': hora, 'sesiones': ss})
        return gs

    @property
    def sesiones_error(self):
        tramos = Tramo_horario.objects.filter(horario=self)
        inicios = tramos.values_list('inicio', flat=True)
        finales = tramos.values_list('fin', flat=True)
        return Sesion.objects.filter(Q(horario=self), ~Q(inicio__in=inicios) | ~Q(fin__in=finales))

    def __str__(self):
        p = ' - Predeterminado' if self.predeterminado else ''
        return 'Horario de %s (%s)%s' % (self.entidad, self.descripcion[:150], p)


class Tramo_horario(models.Model):
    horario = models.ForeignKey(Horario, on_delete=models.CASCADE)
    dia = models.CharField("Día de la semana", blank=True, choices=DIAS_SEMANA, max_length=15)
    nombre = models.CharField("Tramo", max_length=350, blank=True)
    inicio = models.TimeField("Hora de inicio (en minutos)", max_length=50, blank=True)
    fin = models.TimeField("Hora de fin (en minutos)", max_length=50, blank=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    class Meta:
        ordering = ['inicio']

    def __str__(self):
        return 'Sesion'
        try:
            nombre = self.nombre
        except:
            nombre = 'Sin nombre'
        return '%s (%s-%s) - %s (%s)' % (
            nombre, self.inicio, self.fin, self.horario.entidad.name, self.horario.entidad.ronda.nombre)


class Actividad(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la actividad", max_length=350, blank=True, null=True)
    requiere_unidad = models.BooleanField("Requiere unidad", default=False)
    requiere_materia = models.BooleanField("Requiere materia", default=False)
    guardia = models.BooleanField("Es una guardia?", default=False)
    observaciones = models.TextField("Observaciones", null=True, blank=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Actividades"
        ordering = ['id']

    def __str__(self):
        return '%s %s (%s)' % (self.nombre, self.entidad, self.clave_ex)


class Sesion(models.Model):
    tramo_horario = models.ForeignKey(Tramo_horario, null=True, blank=True, on_delete=models.CASCADE)
    horario = models.ForeignKey(Horario, null=True, blank=True, on_delete=models.CASCADE)
    dia_borrar = models.CharField("Día de la semana", blank=True, choices=DIAS_SEMANA, max_length=15)
    dia = models.IntegerField("Día de la semana", blank=True, choices=DIAS)
    nombre = models.CharField("Nombre: 1ª hora, Recreo, ...", max_length=350, blank=True, null=True)
    inicio = models.TimeField("Hora de inicio", max_length=50, blank=True, null=True)
    fin = models.TimeField("Hora de fin", max_length=50, blank=True, null=True)
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.SET_NULL, null=True, blank=True)
    subentidad = models.ForeignKey(Subentidad, null=True, blank=True, on_delete=models.CASCADE)
    grupo = models.ForeignKey(EGrupo, null=True, blank=True, on_delete=models.CASCADE)
    asistentes = models.ManyToManyField(Gauser_extra, blank=True, related_name='asistentes10')
    dependencia = models.ForeignKey(Dependencia, null=True, blank=True, on_delete=models.CASCADE)
    materia = models.ForeignKey(EMateria, null=True, blank=True, on_delete=models.CASCADE)
    actividad = models.ForeignKey(Actividad, null=True, blank=True, on_delete=models.CASCADE)
    #################################
    hora_inicio = models.IntegerField('Hora inicio periodo en minutos', default=0)
    hora_fin = models.IntegerField('Hora fin periodo en minutos', default=0)
    hora_inicio_cadena = models.CharField('Hora inicio periodo en formato H:i', max_length=8, blank=True, null=True)
    hora_fin_cadena = models.CharField('Hora fin periodo en formato H:i', max_length=8, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Sesiones"
        ordering = ['hora_inicio']

    def grupos(self):
        gs = []
        for se in self.sesionextra_set.all():
            if se.grupo not in gs:
                gs.append(se.grupo)
        return gs

    @property
    def clase_horario(self):
        try:
            if self.sesionextra_set.all()[0].materia:
                ch = [str(self.sesionextra_set.all()[0].materia.id)]
                for sext in self.sesionextra_set.all():
                    ch.append(str(sext.grupo.id))
                return '_'.join(ch)
            else:
                return self.sesionextra_set.all()[0].actividad.clave_ex
        except:
            return self.sesionextra_set.all()[0].actividad.clave_ex

    @property
    def top(self):
        hi = self.horario.hora_inicio_ge(self.g_e)
        offset = self.horario.pixels_offset
        pixels_minuto = self.horario.pixels_minuto
        return (self.hora_inicio - hi) * pixels_minuto + offset

    @property
    def height(self):
        hi = self.horario.hora_inicio
        hf = self.horario.hora_fin
        pixels_minuto = self.horario.pixels_minuto
        return (hf - hi) * pixels_minuto

    def __str__(self):
        return '%s - %s' % (self.dia, self.horario)


class SesionExtra(models.Model):
    sesion = models.ForeignKey(Sesion, on_delete=models.CASCADE, blank=True, null=True)
    grupo = models.ForeignKey(EGrupo, null=True, blank=True, on_delete=models.CASCADE)
    dependencia = models.ForeignKey(Dependencia, null=True, blank=True, on_delete=models.CASCADE)
    materia = models.ForeignKey(EMateria, null=True, blank=True, on_delete=models.CASCADE)
    actividad = models.ForeignKey(Actividad, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Sesiones Información Extra"

    def __str__(self):
        return '%s' % (self.sesion)


TIPO_FALTA = (('f', 'Falta'), ('r', 'Retraso'))


class Falta_asistencia(models.Model):
    sesion = models.ForeignKey(Sesion, related_name='falta', on_delete=models.CASCADE)
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.SET_NULL, related_name='ge11', blank=True, null=True)
    fecha_falta = models.DateField('Fecha en la que falta')
    tipo = models.CharField('Retraso o Falta', max_length=10, choices=TIPO_FALTA, default='f')
    justificada = models.BooleanField('La ha justificado?', default=False)

    def __str__(self):
        return 'Falta: %s - %s (%s)' % (self.g_e, self.sesion.materia.nombre, self.fecha_falta)


def update_tarea(instance, filename):
    nombre = filename.partition('.')
    return os.path.join("guardias/", str(instance.ge.ronda.entidad.code) + '_' + str(instance.id) + '.' + nombre[2])


class Guardia(models.Model):
    ge = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    sesion = models.ForeignKey(Sesion, on_delete=models.CASCADE)
    fecha = models.DateField("Fecha de la guardia")
    observaciones = models.TextField("Descripción", blank=True, null=True)
    tarea = models.FileField("Tarea", upload_to=update_tarea, blank=True, null=True)
    content_type = models.CharField('Content Type del archivo tarea', max_length=50, blank=True, null=True)

    def __str__(self):
        return '%s - %s' % (self.fecha, self.sesion)


class Gauser_extra_horarios(models.Model):
    ge = models.OneToOneField(Gauser_extra, on_delete=models.CASCADE)
    # grupo = models.ForeignKey(Grupo, blank=True, null=True, on_delete=models.CASCADE)
    tutor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='tutor_ge', on_delete=models.CASCADE)
    cotutor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='cotutor_ge',
                                on_delete=models.CASCADE)

    def __str__(self):
        return '%s - %s' % (self.ge, self.grupo)


def update_fichero_carga_masiva(instance, filename):
    nombre = filename.partition('.')
    nombre = '%s_%s.%s' % (str(instance.ronda.entidad.code), pass_generator(), nombre[2])
    return os.path.join("carga_masiva/", nombre)


class CargaMasiva(models.Model):
    TIPOS = (('PLUMIER', 'Horarios Peñalara Plumier'), ('', ''), ('', ''), ('', ''), ('', ''),)
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE, related_name='horarios')
    fichero = models.FileField("Fichero con datos", upload_to=update_fichero_carga_masiva, blank=True)
    tipo = models.CharField("Tipo de archivo", max_length=15, choices=TIPOS)
    incidencias = models.TextField("Incidencias producidas", blank=True, null=True, default='')
    cargado = models.BooleanField("¿Se ha cargado el archivo?", default=False)

    class Meta:
        verbose_name_plural = "Cargas Masivas"
        ordering = ['-ronda']

    def __str__(self):
        return '%s -- Cargado: %s' % (self.ronda, self.cargado)


class PlataformaDistancia(models.Model):
    PLATAFORMAS = (('moodle', 'Moodle'), ('edmodo', 'Edmodo'), ('gcroom', 'Google Classroom'),
                   ('msteams', 'Microsoft Teams'), ('otra', 'Otras plataformas'),
                   ('ninguna', 'No uso plataforma'))
    VIDEOCONFER = (('meet', 'Google Meet'), ('webex', 'Cisco Webex'), ('teams', 'Microsoft Teams'),
                   ('otra', 'Otras plataformas'), ('ninguna', 'No uso plataforma'))
    profesor = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    materia = models.ForeignKey(EMateria, null=True, blank=True, on_delete=models.CASCADE)
    grupo = models.ForeignKey(EGrupo, null=True, blank=True, on_delete=models.CASCADE)
    plataforma = models.CharField('Plataforma educativa', default='ninguna', choices=PLATAFORMAS, max_length=10)
    platvideo = models.CharField('Plataforma video-conferencias', default='ninguna', choices=VIDEOCONFER, max_length=10)
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')

    def __str__(self):
        return '%s - %s: %s' % (self.profesor.gauser.get_full_name(), self.grupo, self.plataforma)


class SeguimientoAlumno(models.Model):
    DISPONIBILIDAD = ((1, 'Muy reducida'), (2, 'Mejorable'), (3, 'Buena'), (4, 'Excelente'))
    DISPOSITIVOS = ((1, 'Teléfono NO Smartphone'), (2, 'Teléfono Smartphone'),
                    (3, 'Tablet'), (4, 'Ordenador'), (5, 'Televión NO smart TV'),
                    (6, 'Televisión smart TV'))
    PROGRAMA = ((1, 'Ninguno'), (2, 'PROA'), (3, 'PAI'))
    VALORES = ((1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'))
    APRENDIZAJE = ((1, 'INSUFICIENTE'), (2, 'MEJORABLE'), (3, 'BUENO'), (4, 'EXCELENTE'))
    alumno = models.ForeignKey(Gauser_extra_estudios, blank=True, null=True, on_delete=models.CASCADE)
    smartphone = models.BooleanField('¿Tiene teléfono móvil o tablet?', default=False)
    ordenador = models.BooleanField('¿Tiene ordenador?', default=False)
    internet = models.BooleanField('¿Tiene conexión a internet?', default=False)
    clases = models.BooleanField('¿Está siguiendo las clases?', default=False)
    localizable = models.BooleanField('¿El alumno está localizable?', default=False)
    absentista = models.BooleanField('¿Es un alumno absentista?', default=False)
    contelef = models.BooleanField('¿Has podido contactar telefónicamente?', default=False)
    ticpreferente = models.IntegerField('¿Qué dispositivo usa preferentemente?', default=1, choices=DISPOSITIVOS)
    ticdisponible = models.IntegerField('¿Disponibilidad de usar el dispositivo?', default=1, choices=DISPONIBILIDAD)
    obsaccesibilidad = models.IntegerField('Valora la accesibilidad del alumno a internet', default=1, choices=VALORES)
    obscompdigitales = models.IntegerField('Valora las competencias digitales del alumno', default=1, choices=VALORES)
    acompeducativo = models.BooleanField('¿El alumno tiene ayuda en casa para el uso de las TIC?', default=False)
    materialesdidacticos = models.BooleanField('¿El alumno tiene en casa los materiales didácticos?', default=False)
    atdiversidad = models.BooleanField('¿El alumno está en algún grupo de atención a la diversidad?', default=False)
    programa = models.IntegerField('¿En qué programa de apoyo participa?', default=1, choices=PROGRAMA)
    apoyo = models.BooleanField('¿Necesita apoyo emocional?', default=False)
    valoracion = models.IntegerField('¿Valoración de su aprendizaje a distancia?', default=1, choices=APRENDIZAJE)
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')

    def __str__(self):
        return '%s - %s - Tel: %s, PC: %s, Int: %s, Clases: %s' % (
            self.alumno.ge.gauser.get_full_name(), self.alumno.grupo, self.smartphone, self.ordenador, self.internet,
            self.clases)

# def sesion2sesion():
#     from horarios.models import Sesion
#     from estudios.models import Materia as EMateria
#     from estudios.models import Grupo as EGrupo
#     sesiones = Sesion.objects.filter(materia__isnull=False, emateria__isnull=True)
#     for s in sesiones:
#         emateria = EMateria.objects.get(clave_ex=s.materia.clave_ex, curso__ronda=s.materia.curso.ronda)
#         s.emateria = emateria
#         s.save()
