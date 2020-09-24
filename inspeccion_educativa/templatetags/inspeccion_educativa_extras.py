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