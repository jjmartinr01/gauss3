# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.db import models
from datetime import date
from entidades.models import Entidad, Subentidad, Ronda, Dependencia, Gauser_extra
from estudios.models import Curso as ECurso
from estudios.models import Grupo as EGrupo
from estudios.models import Materia as EMateria

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

ETAPAS = (('ba', 'Infantil'), ('ca', 'Primaria'), ('da', 'Secundaria'), ('ea', 'FP Básica'), ('fa', 'Bachillerato'),
          ('ga', 'FP Grado Medio'), ('ha', 'FP Grado Superior'))


class Curso(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Curso", max_length=150)
    etapa = models.CharField("Nombre de la etapa", max_length=75, null=True, blank=True, choices=ETAPAS)
    tipo = models.CharField("Tipo de estudio", max_length=75, null=True, blank=True)
    nombre_especifico = models.CharField("Nombre específico", max_length=150, null=True, blank=True)
    familia = models.CharField("Departamento", max_length=150, null=True, blank=True)
    observaciones = models.TextField("Observaciones", null=True, blank=True)
    grupos = models.ManyToManyField(Subentidad, blank=True)
    edad = models.IntegerField("Edad con la que puede iniciarse este curso", blank=True, null=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    class Meta:
        ordering = ['etapa', 'tipo', 'nombre']

    def __unicode__(self):
        return u'%s (%s)' % (self.nombre, self.ronda.entidad.name)


# Ligar un Grupo a un curso es problemático porque alumnos de un grupo pueden pertenecer a varios cursos. Por ejemplo
# los alumnos del grupo 1Bach A pueden pertenecer a los cursos de Ciencias y de Artes
class Grupo(models.Model):
    ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
    cursos = models.ManyToManyField(Curso, blank=True)
    nombre = models.CharField("Nombre", max_length=100)
    observaciones = models.TextField("Observaciones", null=True, blank=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    @property
    def entidad(self):
        return self.ronda.entidad

    @property
    def tutores(self):
        tutores_id = Gauser_extra_horarios.objects.filter(grupo__id=self.id).values_list('tutor__id')
        return Gauser_extra.objects.filter(id__in=tutores_id).distinct()

    @property
    def cotutores(self):
        cotutores_id = Gauser_extra_horarios.objects.filter(grupo__id=self.id).values_list('cotutor__id')
        return Gauser_extra.objects.filter(id__in=cotutores_id).distinct()

    @property
    def gausers_extra_horarios(self):
        return Gauser_extra_horarios.objects.filter(grupo__id=self.id)

    class Meta:
        ordering = ['nombre']

    def __unicode__(self):
        cursos = self.cursos.all().values_list('nombre', flat=True)
        return u'%s - %s - %s' % (self.nombre, ', '.join(cursos), self.ronda)


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
#     def __unicode__(self):
#         curso_nombre = self.curso.nombre if self.curso else 'No asignada a un curso'
#         return u'%s - %s (%s horas)' % (self.nombre, curso_nombre, self.horas)


class Horario(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
    descripcion = models.TextField("Breve descripción", blank=True, null=True)
    lunes = models.BooleanField('Lunes?', default=True)
    martes = models.BooleanField('Martes?', default=True)
    miercoles = models.BooleanField('Miércoles?', default=True)
    jueves = models.BooleanField('Jueves?', default=True)
    viernes = models.BooleanField('Viernes?', default=True)
    sabado = models.BooleanField('Sábado?', default=False)
    domingo = models.BooleanField('Domingo?', default=False)
    predeterminado = models.BooleanField("Horario predeterminado?", default=False)

    @property
    def pixels_hora(self):
        return 60

    @property
    def pixels_minuto(self):
        return 2

    @property
    def pixels_offset(self):
        return 50

    def sesiones_aula(self, aula):
        return self.sesion_set.filter(dependencia=aula)

    def horas_aula(self, aula):
        hs = self.sesion_set.filter(dependencia=aula).values_list('inicio', 'fin').distinct().order_by('inicio')
        return [{'top': (hora[0].hour * 60 + hora[0].minute - hs[0][0].hour * 60 - hs[0][
            0].minute) * self.pixels_minuto + self.pixels_offset,
                 'height': (hora[1].hour * 60 + hora[1].minute - hora[0].hour * 60 - hora[
                     0].minute) * self.pixels_minuto,
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
        hs = self.sesion_set.filter(grupo=grupo).values_list('inicio', 'fin').distinct().order_by('inicio')
        return [{'top': (hora[0].hour * 60 + hora[0].minute - hs[0][0].hour * 60 - hs[0][
            0].minute) * self.pixels_minuto + self.pixels_offset,
                 'height': (hora[1].hour * 60 + hora[1].minute - hora[0].hour * 60 - hora[
                     0].minute) * self.pixels_minuto,
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
        hs = self.sesion_set.filter(g_e=ge).values_list('inicio', 'fin').distinct().order_by('inicio')
        return [{'top': (hora[0].hour * 60 + hora[0].minute - hs[0][0].hour * 60 - hs[0][
            0].minute) * self.pixels_minuto + self.pixels_offset,
                 'height': (hora[1].hour * 60 + hora[1].minute - hora[0].hour * 60 - hora[
                     0].minute) * self.pixels_minuto,
                 'inicio': hora[0], 'fin': hora[1]} for hora in hs]

    def hora_inicio_ge(self, ge):
        horas = self.sesion_set.filter(g_e=ge).values_list('inicio', 'fin').distinct().order_by('inicio')
        return horas[0][0]

    def hora_fin_ge(self, ge):
        horas = self.sesion_set.filter(g_e=ge).values_list('inicio', 'fin').distinct().order_by('inicio')
        return horas.last()[1]

    @property
    def horas(self):
        return self.sesion_set.all().values_list('inicio', 'fin').distinct().order_by('inicio')

    @property
    def hora_inicio(self):
        horas = self.sesion_set.all().values_list('inicio', 'fin').distinct().order_by('inicio')
        return horas[0][0]

    @property
    def hora_fin(self):
        horas = self.sesion_set.all().values_list('inicio', 'fin').distinct().order_by('inicio')
        return horas.last()[1]

    @property
    def horario_height(self):
        horas = self.sesion_set.all().values_list('inicio', 'fin').distinct().order_by('inicio')
        l = horas.last()[1]
        i = horas[0][0]
        return (l.hour * 60 + l.minute - i.hour * 60 - i.minute + 5) * self.pixels_minuto + self.pixels_offset

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

    def horario_guardias(self, dia):
        gs = []
        for hora in self.horas:
            ss = Sesion.objects.filter(horario=self, inicio=hora[0], fin=hora[1], actividad__guardia=True, dia=dia)
            gs.append({'hora': hora, 'sesiones': ss})
        return gs

    def __unicode__(self):
        p = ' - Predeterminado' if self.predeterminado else ''
        return u'Horario de %s (%s)%s' % (self.entidad, self.descripcion[:150], p)


class Tramo_horario(models.Model):
    horario = models.ForeignKey(Horario, on_delete=models.CASCADE)
    dia = models.CharField("Día de la semana", blank=True, choices=DIAS_SEMANA, max_length=15)
    nombre = models.CharField("Tramo", max_length=350, blank=True)
    inicio = models.TimeField("Hora de inicio (en minutos)", max_length=50, blank=True)
    fin = models.TimeField("Hora de fin (en minutos)", max_length=50, blank=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    class Meta:
        ordering = ['inicio']

    def __unicode__(self):
        return u'%s (%s-%s) - %s (%s)' % (
            self.nombre, self.inicio, self.fin, self.horario.entidad.name, self.horario.entidad.ronda.nombre)


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

    def __unicode__(self):
        return u'%s %s (%s)' % (self.nombre, self.entidad, self.clave_ex)


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

    class Meta:
        verbose_name_plural = "Sesiones"

    @property
    def top(self):
        hora_inicio = self.horario.hora_inicio_ge(self.g_e)
        # hora_inicio = self.horario.hora_inicio
        offset = self.horario.pixels_offset
        pixels_minuto = self.horario.pixels_minuto
        return (
                   self.inicio.hour * 60 + self.inicio.minute - hora_inicio.hour * 60 - hora_inicio.minute) * pixels_minuto + offset

    @property
    def height(self):
        hora_inicio = self.horario.hora_inicio
        hora_fin = self.horario.hora_fin
        pixels_minuto = self.horario.pixels_minuto
        return (hora_fin.hour * 60 + hora_fin.minute - hora_inicio.hour * 60 - hora_inicio.minute) * pixels_minuto

    def __unicode__(self):
        return u'%s - %s' % (self.dia, self.horario)

        # return u'%s - %s (%s)' % (self.dia, self.horario, self.g_e.gauser.get_full_name())


# import csv
# with open('sesiones.csv', 'wb') as csvfile:
#     spamw = csv.writer(csvfile, delimiter=';', quotechar='|', quoting=csv.QUOTE_MINIMAL)
#     for s in ss:
#         try:
#             grupo = s.grupo.clave_ex
#         except:
#             grupo = ''
#         try:
#             dependencia = slugify(s.aula.clave_ex)
#         except:
#             dependencia = ''
#         try:
#             materia = s.materia.clave_ex
#         except:
#             materia = ''
#         try:
#             actividad = slugify(s.actividad_docente.clave_ex)
#         except:
#             actividad = ''
#         try:
#             tramo = slugify(s.tramo_horario.tramo)
#         except:
#             tramo = ''
#         try:
#             inicio = s.tramo_horario.inicio.strftime('%H:%M')
#         except:
#             inicio = ''
#         try:
#             fin = s.tramo_horario.fin.strftime('%H:%M')
#         except:
#             fin = ''
#         try:
#             spamw.writerow([s.dia, s.docente.gauser.dni, grupo, dependencia, materia, actividad, tramo, inicio, fin])
#         except:
#             print 'Error con sesion %s' % s.id
# #
# def migra_sesiones():
#     d_m = {'L': 'lunes', 'M': 'martes', 'X': 'miercoles', 'J': 'jueves', 'V': 'viernes'}
#     import csv
#     from datetime import datetime
#     r = Ronda.objects.get(id=26)
#     e = Entidad.objects.get(id=14)
#     h = Horario.objects.get(id=24)
#     with open('sesiones.csv', 'rb') as csvfile:
#         spamreader = csv.reader(csvfile, delimiter=';', quotechar='|')
#         for row in spamreader:
#             print row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]
#             dia = d_m[row[0]]
#             try:
#                 docente = Gauser_extra.objects.get(gauser__dni=row[1], ronda=r)
#             except:
#                 docente = None
#                 print 'Error en docente %s' % row[1]
#             try:
#                 grupo = Grupo.objects.get(ronda=r, clave_ex=row[2])
#             except:
#                 grupo = None
#                 print 'Error en grupo %s' % row[2]
#             try:
#                 dependencia = Dependencia.objects.get(clave_ex=row[3])
#             except:
#                 dependencia = None
#                 print 'Error en dependencia %s' % row[3]
#             try:
#                 materia = Materia.objects.get(curso__entidad__ronda=r, clave_ex=row[4])
#             except:
#                 materia = None
#                 print 'Error en materia %s' % row[4]
#             try:
#                 actividad = Actividad.objects.get(clave_ex=row[5], entidad=e)
#             except:
#                 actividad = None
#                 print 'Error en actividad %s' % row[5]
#             try:
#                 nombre = row[6]
#             except:
#                 nombre = ''
#                 print 'Error en nombre %s' % row[6]
#             try:
#                 inicio = datetime.strptime(row[7],'%H:%M')
#             except:
#                 inicio = None
#                 print 'Error en inicio %s' % row[7]
#             try:
#                 fin = datetime.strptime(row[8], '%H:%M')
#             except:
#                 fin = None
#                 print 'Error en fin %s' % row[8]
#             Sesion.objects.create(horario=h, dia=dia, nombre=nombre, inicio=inicio, fin=fin, g_e=docente, grupo=grupo, dependencia=dependencia, materia=materia, actividad=actividad)
#             print 'Sesion creada'



TIPO_FALTA = (('f', 'Falta'), ('r', 'Retraso'))


class Falta_asistencia(models.Model):
    sesion = models.ForeignKey(Sesion, related_name='falta', on_delete=models.CASCADE)
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.SET_NULL, related_name='ge11', blank=True, null=True)
    fecha_falta = models.DateField('Fecha en la que falta')
    tipo = models.CharField('Retraso o Falta', max_length=10, choices=TIPO_FALTA, default='f')
    justificada = models.BooleanField('La ha justificado?', default=False)

    def __unicode__(self):
        return u'Falta: %s - %s (%s)' % (self.g_e, self.sesion.materia.nombre, self.fecha_falta)


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

    def __unicode__(self):
        return u'%s - %s' % (self.fecha, self.sesion)


class Gauser_extra_horarios(models.Model):
    ge = models.OneToOneField(Gauser_extra, on_delete=models.CASCADE)
    grupo = models.ForeignKey(Grupo, blank=True, null=True, on_delete=models.CASCADE)
    tutor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='tutor_ge', on_delete=models.CASCADE)
    cotutor = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='cotutor_ge', on_delete=models.CASCADE)

    def __unicode__(self):
        return u'%s - %s' % (self.ge, self.grupo)






def sesion2sesion():
    from horarios.models import Sesion
    from estudios.models import Materia as EMateria
    from estudios.models import Grupo as EGrupo
    sesiones=Sesion.objects.filter(materia__isnull=False, emateria__isnull=True)
    for s in sesiones:
        # print s.materia.clave_ex
        emateria = EMateria.objects.get(clave_ex=s.materia.clave_ex, curso__ronda=s.materia.curso.ronda)
        # print emateria
        s.emateria = emateria
        s.save()