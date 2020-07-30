# -*- coding: utf-8 -*-
from django.template import Library
from datetime import datetime, timedelta
from autenticar.models import Permiso
from domotica.models import Grupo
from vut.models import DomoticaVUT

register = Library()


@register.filter
def borra_grupo_domotica(g_e, grupo):
    if grupo.propietario == g_e.gauser or g_e.has_permiso('borra_grupos_domotica'):
        return True
    else:
        return False

@register.filter
def edita_grupo_domotica(g_e, grupo):
    if grupo.propietario == g_e.gauser or g_e.has_permiso('edita_grupos_domotica'):
        return True
    else:
        return False

@register.filter
def edita_grupoid_domotica(g_e, grupoid):
    grupo = Grupo.objects.get(id=grupoid)
    if grupo.propietario == g_e.gauser or g_e.has_permiso('edita_grupos_domotica'):
        return True
    else:
        return False

@register.filter
def grupos_domotica(g_e, grupo):
    return Grupo.objects.filter(propietario=g_e.gauser).exclude(id=grupo)

@register.filter
def borra_dispositivo_domotica(g_e, dispositivo):
    if dispositivo.permiso(g_e.gauser) == 'BORRAR' or g_e.has_permiso('borra_dispositivos_domotica'):
        return True
    else:
        return False

@register.filter
def copiasVUT(dispositivo):
    return DomoticaVUT.objects.filter(dispositivo=dispositivo)
