# -*- coding: utf-8 -*-
from django.template import Library
from autenticar.models import Permiso
from entidades.models import Subentidad, Gauser_extra
from estudios.models import Gauser_extra_estudios
from programaciones.models import Departamento

register = Library()


@register.filter
def departamentos(cupo):
    return Departamento.objects.filter(ronda=cupo.ronda)