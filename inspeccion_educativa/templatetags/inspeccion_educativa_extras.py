# -*- coding: utf-8 -*-
from django.template import Library
from entidades.models import Subentidad
from estudios.models import Grupo, Materia
from horarios.models import Sesion
from datetime import datetime, time

register = Library()


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

def get_iniciales(nombre):
    words = nombre.split(' ')
    character = ''
    for word in words:
        character += word[0]
    return character

@register.filter
def inspectores_colaboradores(instarea):
    # inspector = instarea.inspector
    # inspectores = instarea.tarea.inspectortarea_set.exclude(inspector=inspector)
    iniciales = []
    for i in instarea.tarea.inspectortarea_set.all():
        iniciales.append(get_iniciales(i.inspector.gauser.get_full_name()))
    return ', '.join(iniciales)