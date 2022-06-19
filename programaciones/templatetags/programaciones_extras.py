# -*- coding: utf-8 -*-
from django.template import Library
from autenticar.models import Permiso
from estudios.models import Gauser_extra_estudios
from programaciones.models import *

register = Library()

@register.filter
def ecpv_selected(calalum, ecpv):
    return calalum.calalumvalor_set.filter(ecpv=ecpv).count() > 0

@register.filter
def get_ecpv_xs(ecp, y):
    return ecp.escalacpvalor_set.filter(y=y)

@register.filter
def get_posibles_psec(cuaderno):
    psec_ids = DocProgSec.objects.filter(gep__ge=cuaderno.ge).values_list('psec__id', flat=True)
    return ProgSec.objects.filter(id__in=psec_ids)
#################################################
@register.filter
def get_recpv_xs(recp, y):
    return recp.repoescalacpvalor_set.filter(y=y)

#################################################
########  Estas dos funciones trabajan juntas para crear una función de tres variables
########  Observarlas en cuadernodocente_accordion_content.html
########  cuaderno|get_cieval:cieval|get_calalum:alumno
@register.filter
def get_cieval(cuaderno, cieval):
    return cuaderno, cieval


@register.filter
def get_calalum(cuaderno_cieval, alumno):
    try:
        cuaderno, cieval = cuaderno_cieval
        return CalAlum.objects.get(alumno=alumno, cie=cieval, cp=cuaderno)
    except Exception as msg:
        return str(msg)

########  Fin de las dos funciones
#################################################

#################################################
########  Estas dos funciones trabajan juntas para crear una función de tres variables
########  Observarlas en cuadernodocente_accordion_content.html
########  cuaderno|get_cev_cals:cev|get_calalum_cev:alumno

@register.filter
def get_cev_cals(cuaderno, cev):
    return cuaderno, cev


@register.filter
def get_calalum_cev(cuaderno_cev, alumno):
    try:
        cuaderno, cev = cuaderno_cev
        return cuaderno.calificacion_alumno_cev(alumno, cev)
    except Exception as msg:
        return str(msg)

########  Fin de las dos funciones
#################################################

#################################################
########  Estas dos funciones trabajan juntas para crear una función de tres variables
########  Observarlas en cuadernodocente_accordion_content.html
########  cuaderno|get_ce_cal:ce|get_calalum_ce:alumno

@register.filter
def get_ce_cal(cuaderno, ce):
    return cuaderno, ce


@register.filter
def get_calalum_ce(cuaderno_ce, alumno):
    try:
        cuaderno, ce = cuaderno_ce
        return cuaderno.calificacion_alumno_ce(alumno, ce)
    except Exception as msg:
        return str(msg)

########  Fin de las dos funciones
#################################################

#################################################
########  Esta función calcula la calificación global de un alumno del cuaderno

@register.filter
def get_global_cal(cuaderno, alumno):
    return cuaderno.calificacion_alumno(alumno)

########  Fin de la función
#################################################



@register.filter
def puede_borrar(psec, g_e):
    try:
        return psec.get_permiso(g_e.gauser_extra_programaciones) == 'X'
    except:
        return False

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
