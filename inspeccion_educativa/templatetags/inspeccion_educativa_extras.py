# -*- coding: utf-8 -*-
from django.template import Library
from entidades.models import Subentidad
from estudios.models import Grupo, Materia
from horarios.models import Sesion
from datetime import datetime, timedelta, time
from inspeccion_educativa.models import InspectorAsignado

register = Library()


# @register.simple_tag(takes_context=True)
# def get_next_friday(context):
#     selected_date = context['selected_date']
#     next_month = selected_date.month % 12 + 1
#     return datetime.date(1900, next_month, 1).strftime("%b")

@register.simple_tag(takes_context=False)
def get_next_friday():
    d = datetime.today().date() - timedelta(4)
    while d.weekday() != 4:
        d += timedelta(1)
    return d.strftime('%d-%m-%Y')

@register.simple_tag(takes_context=False)
def get_last_monday():
    d = datetime.today().date() - timedelta(4)
    while d.weekday() != 0:
        d -= timedelta(1)
    return d.strftime('%d-%m-%Y')

@register.filter
def texto2nombre(s):
    return s.title().replace('_', ' ')


@register.filter
def permiso_instarea_w(instarea, g_e):
    c1 = instarea.tarea.creador.gauser == g_e.gauser
    c2 = 'w' in instarea.tarea.permiso(g_e.gauser)
    c3 = g_e.has_permiso('edita_cualquier_tarea_ie')
    try:
        if c1 or c2 or c3:
            return True
        else:
            return False
    except:
        return False


@register.filter
def permiso_instarea_x(instarea, g_e):
    c1 = instarea.tarea.creador.gauser == g_e.gauser
    c2 = 'x' in instarea.tarea.permiso(g_e.gauser)
    c3 = g_e.has_permiso('borra_cualquier_tarea_ie')
    try:
        if c1 or c2 or c3:
            return True
        else:
            return False
    except:
        return False

@register.filter
def get_iniciales(nombre):
    palabras = nombre.split()
    iniciales = ''
    for palabra in palabras:
        iniciales += palabra[0]
    return iniciales

@register.filter
def inspectores_colaboradores(instarea):
    # inspector = instarea.inspector
    # inspectores = instarea.tarea.inspectortarea_set.exclude(inspector=inspector)
    iniciales = []
    for i in instarea.tarea.inspectortarea_set.all():
        iniciales.append(get_iniciales(i.inspector.gauser.get_full_name()))
    return ', '.join(iniciales)

@register.filter
def get_puntos(inspector):
    ias = InspectorAsignado.objects.filter(inspector=inspector)
    puntos = 0
    for ia in ias:
        puntos += ia.cenins.puntos
    return puntos