# -*- coding: utf-8 -*-
from django.template import Library
from gauss.funciones import human_readable_list
from entidades.models import Subentidad
from estudios.models import Curso, Grupo, Materia, Gauser_extra_estudios, Matricula
from datetime import datetime, time

register = Library()


@register.filter
def federados_iban(federados):
    num = 0
    for federado in federados:
        if federado.piban:
            num = (num + 1) if len(federado.entidad.iban) == 24 else num
    return num


@register.filter
def socios_totales(federados):
    num = 0
    for federado in federados:
        num += federado.entidad.num_usuarios
    return num

@register.filter
def alumnos_grupo(grupo):
    return Gauser_extra_estudios.objects.filter(grupo=grupo)

@register.filter
def pendientes_alumno(ms, alumno):
    return Matricula.objects.filter(ge=alumno, materia__in=ms)

@register.filter
def human_readable_pendientes(matriculas):
    materias = matriculas.values_list('materia__id', flat=True)
    ms = Materia.objects.filter(id__in=materias)
    ms_text_array = ['%s (%s)' % (m[0], m[1]) for m in ms.values_list('nombre', 'curso__nombre')]
    return human_readable_list(ms_text_array)

