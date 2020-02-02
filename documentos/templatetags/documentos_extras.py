# -*- coding: utf-8 -*-
from django.template import Library
from django.db.models import Q
from datetime import datetime, timedelta
from autenticar.models import Permiso
from documentos.models import Ges_documental, Permiso_Ges_documental, Etiqueta_documental

register = Library()


@register.filter
def documentos_accesibles(g_e):
    return Permiso_Ges_documental.objects.filter(gauser=g_e.gauser,
                                                 documento__propietario__ronda__entidad=g_e.ronda.entidad)


@register.filter
def borra_grupo_domoticavvvvvvvvvv(g_e, grupo):
    if grupo.propietario == g_e.gauser or g_e.has_permiso('borra_grupos_domotica'):
        return True
    else:
        return False
