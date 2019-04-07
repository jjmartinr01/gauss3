# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from math import ceil
from django.template import Library
from django.db.models import Q
from competencias_clave.models import CompetenciasMateriaAlumno, CompetenciasMateria
from estudios.models import Materia

register = Library()


@register.filter
def valorar_cc(gauser_extra, capacidad):
    qs = {'ccl': Q(ccl__gt=0), 'cmct': Q(cmct__gt=0), 'cd': Q(cd__gt=0), 'cpaa': Q(cpaa__gt=0), 'csc': Q(csc__gt=0),
          'sie': Q(sie__gt=0), 'cec': Q(cec__gt=0)}
    # Con el filtro se evitan tomar calificaciones de valor cero, es decir que no se han calificado.
    cma = CompetenciasMateriaAlumno.objects.filter(Q(alumno=gauser_extra), qs[capacidad])
    if cma.count() > 0:
        try:
            ccs = list(cma.values_list('materia__' + capacidad, capacidad, 'materia__materia__horas'))
            total_ponderacion = sum([cc[0] * cc[2] for cc in ccs]) + 0.0000001 #Evitar que sea cero y se pueda hacer la división:
            total_valoracion = ceil(sum([cc[1] * cc[0] * cc[2] for cc in ccs]) / total_ponderacion)
            return min(10, int(total_valoracion))
        except:
            # Una de las causas de error es que la Materia no tenga el parámetro "horas" definido
            return '<span style="color:red">Error</span>'
    else:
        return '<span style="color:red">SV</span>'


@register.filter
def estadistica_profesor(gauser_extra, capacidad):
    qs = {'ccl': Q(ccl__gt=0), 'cmct': Q(cmct__gt=0), 'cd': Q(cd__gt=0), 'cpaa': Q(cpaa__gt=0), 'csc': Q(csc__gt=0),
          'sie': Q(sie__gt=0), 'cec': Q(cec__gt=0)}
    # Con el filtro se evitan tomar calificaciones de valor cero, es decir que no se han calificado.
    return CompetenciasMateriaAlumno.objects.filter(Q(profesor=gauser_extra), qs[capacidad]).count()

@register.filter
def materias(profesores):
    etapas = ['da']
    ms = Materia.objects.filter(curso__ronda=profesores[0].ronda, curso__etapa__in=etapas)
    return CompetenciasMateria.objects.filter(materia__in=ms).order_by('materia__curso__etapa', 'materia__curso')

