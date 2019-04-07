# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from entidades.models import Ronda, Gauser_extra
from estudios.models import Materia


# Create your models here.

class CompetenciasMateria(models.Model):
    ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, blank=True, null=True, on_delete=models.CASCADE)
    ccl = models.IntegerField('Competencia Lingüistica', blank=True, null=True, default=0)
    cmct = models.IntegerField('Competencia matemática y competencias básicas en ciencia y tecnología', blank=True,
                               null=True, default=0)
    cd = models.IntegerField('Competencia digital', blank=True, null=True, default=0)
    cpaa = models.IntegerField('Aprender a aprender', blank=True, null=True, default=0)
    csc = models.IntegerField('Competencias sociales y cívicas', blank=True, null=True, default=0)
    sie = models.IntegerField('Sentido de la iniciativa y espíritu emprendedor', blank=True, null=True, default=0)
    cec = models.IntegerField('Conciencia y expresiones culturales', blank=True, null=True, default=0)

    class Meta:
        ordering = ['ronda', 'materia']

    @property
    def total_percentage(self):
        self.ccl = self.ccl if self.ccl else 0
        self.cmct = self.cmct if self.cmct else 0
        self.cd = self.cd if self.cd else 0
        self.cpaa = self.cpaa if self.cpaa else 0
        self.csc = self.csc if self.csc else 0
        self.sie = self.sie if self.sie else 0
        self.cec = self.cec if self.cec else 0
        return self.ccl + self.cmct + self.cd + self.cpaa + self.csc + self.sie + self.cec

    def __str__(self):
        return u'%s: CCL %s - CMCT %s - CD %s - CPAA %s - CSC %s - SIE %s - CEC %s' % (
            self.materia, self.ccl, self.cmct, self.cd, self.cpaa, self.csc, self.sie, self.cec)


class CompetenciasMateriaAlumno(models.Model):
    profesor = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    alumno = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='cma', on_delete=models.CASCADE)
    materia = models.ForeignKey(CompetenciasMateria, blank=True, null=True, on_delete=models.CASCADE)
    ccl = models.IntegerField('Competencia Lingüistica', blank=True, null=True)
    cmct = models.IntegerField('Competencia matemática y competencias básicas en ciencia y tecnología', blank=True,
                               null=True)
    cd = models.IntegerField('Competencia digital', blank=True, null=True)
    cpaa = models.IntegerField('Aprender a aprender', blank=True, null=True)
    csc = models.IntegerField('Competencias sociales y cívicas', blank=True, null=True)
    sie = models.IntegerField('Sentido de la iniciativa y espíritu emprendedor', blank=True, null=True)
    cec = models.IntegerField('Conciencia y expresiones culturales', blank=True, null=True)

    @property
    def ccl_value(self):
        CompetenciasMateriaAlumno.objects.filter(alumno=self.alumno).values_list('materia__ccl', 'ccl')


    class Meta:
        ordering = ['alumno__gauser__last_name', 'materia']

    def __str__(self):
        return u'%s, %s: CCL %s - CMCT %s - CD %s - CPAA %s - CSC %s - SIE %s - CEC %s' % (
            self.alumno, self.materia, self.ccl, self.cmct, self.cd, self.cpaa, self.csc, self.sie, self.cec)
