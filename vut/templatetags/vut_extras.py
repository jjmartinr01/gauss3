# -*- coding: utf-8 -*-
from django.template import Library
from datetime import datetime, timedelta
from autenticar.models import Permiso
from vut.models import Vivienda, ContabilidadVUT, PartidaVUT, RegistroPolicia


register = Library()


@register.filter
def number_viviendas_same_propietario(vivienda):
    entidad = vivienda.entidad
    return Vivienda.objects.filter(gpropietario=vivienda.gpropietario, entidad=vivienda.entidad).count()


@register.filter
def is_today_or_yesterday(fecha):
    hoy = datetime.today().date()
    ayer = hoy - timedelta(1)
    if fecha == hoy or fecha == ayer:
        return True
    else:
        return False

@register.filter
def contains_hoy(reserva):
    hoy = datetime.today().date()
    if reserva.entrada <= hoy and reserva.salida >= hoy:
        return True
    else:
        return False

@register.filter
def has_permiso_vut(autorizado, permiso):
    permiso = Permiso.objects.get(code_nombre=permiso)
    if permiso in autorizado.permisos.all():
        return True
    else:
        return False

@register.filter
def viviendas(propietario):
    return Vivienda.objects.filter(gpropietario=propietario)

@register.filter
def contabilidades(propietario):
    return ContabilidadVUT.objects.filter(propietario=propietario)

@register.filter
def partidas_contabilidad(contabilidad):
    return PartidaVUT.objects.filter(contabilidad=contabilidad)

@register.filter
def registro_enviado(viajero):
    try:
        vivienda = viajero.reserva.vivienda
        r = RegistroPolicia.objects.get(viajero=viajero, vivienda=vivienda)
        return r.enviado
    except:
        return True

@register.filter
def has_parte_pdf_PN(viajero):
    try:
        r = RegistroPolicia.objects.get(viajero=viajero)
        if r.pdf_PN:
            return r.id
        else:
            return False
    except:
        return False