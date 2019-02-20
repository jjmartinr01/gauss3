# -*- coding: utf-8 -*-
from django.template import Library
from entidades.models import Subentidad
from estudios.models import Curso, Grupo, Materia, Gauser_extra_estudios
from datetime import datetime, time

register = Library()


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