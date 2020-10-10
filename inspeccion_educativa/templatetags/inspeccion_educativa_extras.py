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
    try:
        if instarea.tarea.creador.gauser == g_e.gauser or 'w' in instarea.tarea.permiso(g_e.gauser):
            return True
        else:
            return False
    except:
        return False

@register.filter
def permiso_instarea_x(instarea, g_e):
    try:
        if instarea.tarea.creador.gauser == g_e.gauser or 'x' in instarea.tarea.permiso(g_e.gauser):
            return True
        else:
            return False
    except:
        return False