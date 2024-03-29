# -*- coding: utf-8 -*-
from django.template import Library
from gauss.funciones import human_readable_list
from entidades.models import Subentidad
from estudios.models import Curso, Grupo, Materia, Gauser_extra_estudios, Matricula, AreaMateria
from datetime import datetime, time

register = Library()


@register.filter
def get_ps_cursos(ps):
    cs = []
    for curso in AreaMateria.CURSOS_LOMLOE:
        if ps.etapa in curso[0]:
            cs.append(curso)
    return cs

@register.filter
def grupos_curso(curso):
    return Grupo.objects.filter(cursos__in=[curso])


@register.filter
def materias_grupo(grupo):
    materias__id = grupo.sesion_set.filter(horario__predeterminado=True).values_list('materia__id', flat=True)
    return Materia.objects.filter(id__in=materias__id).distinct()

@register.filter
def alumnos_grupo(grupo):
    return Gauser_extra_estudios.objects.filter(grupo=grupo)

@register.filter
def pendientes_alumno(ms, alumno):
    return ms.filter(ge=alumno)

@register.filter
def human_readable_pendientes(matriculas):
    materias = matriculas.values_list('materia__id', flat=True)
    ms = Materia.objects.filter(id__in=materias)
    ms_text_array = ['%s (%s)' % (m[0], m[1]) for m in ms.values_list('nombre', 'curso__nombre')]
    return human_readable_list(ms_text_array)

