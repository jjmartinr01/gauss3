# -*- coding: utf-8 -*-
from django.template import Library
from autenticar.models import Permiso
from entidades.models import Subentidad, Gauser_extra, Cargo
from estudios.models import Gauser_extra_estudios

register = Library()


@register.filter
def list_usuarios_ronda(ronda, cargo):
    return Gauser_extra.objects.filter(ronda=ronda, cargos__in=[cargo])

@register.filter
def get_dependencias(sesion):
    deps = set([s.dependencia.nombre for s in sesion.sesionextra_set.all() if s.dependencia])
    if deps:
        return deps
    else:
        return ["No hay asignada ninguna dependencia",]

@register.filter
def get_height(sesion):
    return (sesion.hora_fin - sesion.hora_inicio)*2

@register.filter
def profesorado(entidad):
    cargos = Cargo.objects.filter(entidad=entidad, clave_cargo='g_docente')
    return Gauser_extra.objects.filter(ronda=entidad.ronda, cargos__in=cargos)

@register.filter
def profesorado_por_ronda(ronda):
    cargos = Cargo.objects.filter(entidad=ronda.entidad, clave_cargo='g_docente')
    return Gauser_extra.objects.filter(ronda=ronda, cargos__in=cargos)

@register.filter
def puestos_especialidad(entidad):
    cargos = Cargo.objects.filter(entidad=entidad, clave_cargo='g_docente')
    return set(Gauser_extra.objects.filter(ronda=entidad.ronda, cargos__in=cargos).values_list('puesto', flat=True))

@register.filter
def profesorado_puestos_especialidad(entidad, puesto):
    cargos = Cargo.objects.filter(entidad=entidad, clave_cargo='g_docente')
    return Gauser_extra.objects.filter(ronda=entidad.ronda, cargos__in=cargos, puesto=puesto)


@register.filter
def has_cargos(gauser_extra, cargos_comprobar):
    if gauser_extra.gauser.username == 'gauss':
        return True
    else:
        return len([cargo for cargo in gauser_extra.cargos.all() if cargo in cargos_comprobar]) > 0

@register.filter
def has_permiso(gauser_extra, permiso_comprobar):
    if gauser_extra.gauser.username == 'gauss' or permiso_comprobar == 'libre':
        return True
    else:
        try:
            permiso = Permiso.objects.get(code_nombre=permiso_comprobar)
        except:
            return False
        if permiso in gauser_extra.permisos.all():
            return True
        else:
            for cargo in gauser_extra.cargos.all():
                if permiso in cargo.permisos.all():
                    return True
            return False

@register.filter
def nid(value,arg):
   """Devuelve el objecto con el número de id (nid) indicado"""
   return value.get(id=arg)

@register.filter
def grupos_alumnos(g_e):
   """Devuelve el grupo de alumnos al que pertenece el gauser_extra"""
   sub_alumnos = Subentidad.objects.get(entidad=g_e.ronda.entidad, clave_ex='alumnos')
   return g_e.subentidades.filter(parent=sub_alumnos)
   # texto_grupos = ', '.join([g.nombre for g in grupos])
   # return texto_grupos


@register.filter
def alumnos_in_grupo(grupo):
   """Devuelve los alumnos que pertenecen al grupo"""
   return Gauser_extra_estudios.objects.filter(grupo=grupo).order_by('ge__gauser__last_name')

@register.filter
def cargos_ronda(cargo, ronda):
   """Devuelve los alumnos que pertenecen al grupo"""
   return Gauser_extra.objects.filter(ronda=ronda, cargos__in=[cargo]).count()

@register.filter
def valor_campo_reserva(reserva, campo):
    return getattr(reserva, campo)