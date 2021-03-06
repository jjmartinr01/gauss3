# -*- coding: utf-8 -*-
from django.template import Library
from autenticar.models import Permiso
from programaciones.models import *

register = Library()


@register.filter
def docpec(pec, tipo):
    try:
        return PECdocumento.objects.get(pec=pec, tipo=tipo)
    except:
        p = False
    return p

@register.filter
def programacion(materia):
    try:
        p = ProgramacionSubida.objects.get(materia=materia)
    except:
        p = False
    return p


@register.filter
def criterios_eval(progamacion):
    criterios = []
    for u in progamacion.ud_modulo_set.all():
        for o in u.objetivos.all():
            criterios.append(o.crit_eval)
    return set(criterios)


@register.filter
def objetivos_ra(ud, ra):
    return ud.objetivos.filter(resultado_aprendizaje=ra)


@register.filter
def unidades_ra(prog, ra):
    objs = Objetivo.objects.filter(resultado_aprendizaje=ra)
    uds = UD_modulo.objects.filter(programacion=prog, objetivos__in=objs).distinct().values_list('orden', flat=True)
    return uds
#
# @register.filter
# def has_cargos(gauser_extra, cargos_comprobar):
#     if gauser_extra.gauser.username == 'gauss':
#         return True
#     else:
#         return len([cargo for cargo in gauser_extra.cargos.all() if cargo in cargos_comprobar]) > 0
#
# @register.filter
# def has_permiso(gauser_extra, permiso_comprobar):
#     if gauser_extra.gauser.username == 'gauss' or permiso_comprobar == 'libre':
#         return True
#     else:
#         try:
#             permiso = Permiso.objects.get(code_nombre=permiso_comprobar)
#         except:
#             return False
#         if permiso in gauser_extra.permisos.all():
#             return True
#         else:
#             for cargo in gauser_extra.cargos.all():
#                 if permiso in cargo.permisos.all():
#                     return True
#             return False
