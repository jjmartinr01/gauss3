# -*- coding: utf-8 -*-
from django.template import Library
from datetime import datetime, timedelta
from django.utils import timezone
from autenticar.models import Permiso
from vut.models import Vivienda, ContabilidadVUT, PartidaVUT, RegistroPolicia
import json

register = Library()


@register.filter
def number_viviendas_same_propietario(g_e):
    return Vivienda.objects.filter(propietarios__in=[g_e.gauser], entidad=g_e.ronda.entidad).count()

@register.filter
def viviendas_same_propietario(g_e):
    return Vivienda.objects.filter(propietarios__in=[g_e.gauser], entidad=g_e.ronda.entidad)

@register.filter
def copropietarios(vivienda, g_e):
    return vivienda.propietarios.exclude(id=g_e.gauser.id)



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
    return Vivienda.objects.filter(propietarios__in=[propietario])


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


@register.filter
def portada(vivienda):
    fotos = vivienda.fotowebvivienda_set.filter(orden=1)
    if fotos.count() == 0:
        try:
            return vivienda.fotowebvivienda_set.filter(orden__gt=0)[0].foto.url
        except:
            return None
    return fotos[0].foto.url


@register.filter
def portada1(vivienda):
    fotos = vivienda.fotowebvivienda_set.filter(orden=1)
    if fotos.count() == 0:
        try:
            return vivienda.fotowebvivienda_set.filter(orden__gt=0)[0].foto.url
        except:
            return None
    return fotos[0].foto.url


@register.filter
def portada2(vivienda):
    fotos = vivienda.fotowebvivienda_set.filter(orden=2)
    if fotos.count() == 0:
        try:
            return vivienda.fotowebvivienda_set.filter(orden__gt=0)[0].foto.url
        except:
            return None
    return fotos[0].foto.url


@register.filter
def split_by_comma(texto):
    precios = texto.split(',')
    personas = ['Un huésped: ', 'Dos huéspedes: ', 'Tres huéspedes: ', 'Cuatro huéspedes: ', 'Cinco huéspedes: ',
                'Seis huéspedes: ', 'Siete huéspedes: ', 'Ocho huéspedes: ', 'Nueve huéspedes: ', 'Diez huéspedes: ',
                'Once huéspedes: ', 'Doce huéspedes:', 'Trece huéspedes: ', 'Catorce huéspedes: ', 'Quince huéspedes: ']
    return [(personas[i], precios[i]) for i in range(len(precios))]


@register.filter
def reservas2eventos(vivienda):
    today = timezone.datetime.today()
    reservas = vivienda.reserva_set.filter(salida__gte=today)
    eventos = [{'start': r.entrada.strftime('%Y-%m-%d'),
                'end': r.salida.strftime('%Y-%m-%d'),
                'className': 'booked',
                # 'overlap': False,
                'color': '#bbbbbb',
                'title': '%s (%s)' % (r.get_portal_display(), r.nombre)} for r in reservas]
    return json.dumps(eventos)
    # return eventos

@register.filter
def num_registradas(viviendas):
    return viviendas.filter(nregistro__iregex=r'^[0-9a-zA-Z]').count()