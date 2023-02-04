# -*- coding: utf-8 -*-
from django.template import Library
from django.db.models import Q
from autenticar.models import Permiso
from entidades.models import Organization, Entidad
from estudios.models import Gauser_extra_estudios
from programaciones.models import *

register = Library()

@register.filter
def get_estadistica(objeto):
    if type(objeto) == Organization:
        anyo = datetime.now().year if datetime.now().month in [9, 10, 11, 12] else datetime.now().year - 1
        fecha_comienzo_ronda = datetime(anyo, 9, 1)
        psecs = ProgSec.objects.filter(pga__ronda__entidad__organization=objeto,
                                       pga__ronda__inicio__gte=fecha_comienzo_ronda)
    elif type(objeto) == Entidad:
        psecs = ProgSec.objects.filter(pga__ronda=objeto.ronda)
    elif type(objeto) == Departamento:
        psecs = ProgSec.objects.filter(departamento=objeto)
    else:
        return 'Error'
    psec_bor = psecs.filter(tipo='BOR')
    psec_def = psecs.filter(tipo='DEF')
    psec_otr = psecs.exclude(
        id__in=[*psec_bor.values_list('id', flat=True)] + [*psec_def.values_list('id', flat=True)])
    saprens = SitApren.objects.filter(sbas__psec__in=psecs)
    asaprens = ActSitApren.objects.filter(sapren__in=saprens)
    procs = InstrEval.objects.filter(asapren__in=asaprens)
    return {'n_psecs': psecs.count(), 'n_psec_bor': psec_bor.count(), 'n_psec_def': psec_def.count(),
            'n_psec_otr': psec_otr.count(), 'n_saprens': saprens.count(), 'n_procs': procs.count(),
            'n_asaprens': asaprens.count()}


@register.filter
def cbarra2br(texto):
    # Transformar "\n" en <br> para imprimir en html
    return texto.replace('\n', '<br>')
@register.filter
def keyvalue(diccionario, key):
    return diccionario[key]

@register.filter
def float2stringpoint(number):
    return str(number).replace(',', '.')

@register.filter
def get_rondas_ge(ge):
    # Fecha a partir de la cual se pueden encontrar programaciones:
    fecha_inicio = datetime.strptime('01/01/2020', '%d/%m/%Y')
    rondas_id = Gauser_extra.objects.filter(ronda__inicio__gt=fecha_inicio,
                                            gauser=ge.gauser).values_list('ronda__id', flat=True)
    return Ronda.objects.filter(id__in=rondas_id)


@register.filter
def ecpv_selected(calalum, ecpv):
    return calalum.calalumvalor_set.filter(ecpv=ecpv).count() > 0


@register.filter
def get_ecpv_xs(ecp, y):
    return ecp.escalacpvalor_set.filter(y=y)


@register.filter
def get_posibles_psec(cuaderno):
    # comprobar si es una sies que depende de un ies:
    g_e = cuaderno.ge
    ies = cuaderno.ge.ronda.entidad.entidadextra.depende_de
    if ies:
        ge_ies = Gauser_extra.objects.get(gauser=g_e.gauser, ronda=ies.ronda)
        q = Q(gep__ge=cuaderno.ge) | Q(gep__ge=ge_ies)
    else:
        q = Q(gep__ge=cuaderno.ge)
    psec_ids = DocProgSec.objects.filter(q).values_list('psec__id', flat=True)
    return ProgSec.objects.filter(id__in=psec_ids)


#################################################
@register.filter
def get_recpv_xs(recp, y):
    return recp.repoescalacpvalor_set.filter(y=y)

@register.filter
def calificacion_alumno(cuaderno, alumno):
    return cuaderno.calificacion_alumno(alumno)

#################################################
########  Estas dos funciones trabajan juntas para crear una función de tres variables
########  Observarlas en cuadernodocente_accordion_content.html
########  cuaderno|get_asignatura:asignatura|calificacion_alumno_asignatura:alumno
@register.filter
def get_asignatura(cuaderno, asignatura):
    return cuaderno, asignatura
@register.filter
def calificacion_alumno_asignatura(cuaderno_asignatura, alumno):
    try:
        cuaderno, asignatura = cuaderno_asignatura
        return cuaderno.calificacion_alumno_asignatura(alumno, asignatura)
    except Exception as msg:
        return str(msg)
#################################################
########  Estas dos funciones trabajan juntas para crear una función de tres variables
########  Observarlas en cuadernodocente_accordion_content.html
########  cuaderno|get_cep:cep|get_calalumce:alumno
@register.filter
def get_cep(cuaderno, cep):
    return cuaderno, cep


@register.filter
def get_calalumce(cuaderno_cep, alumno):
    try:
        cuaderno, cep = cuaderno_cep
        # return cuaderno.calificacion_alumno_ce(alumno, cep.ce)
        return CalAlumCE.objects.get(alumno=alumno, cep=cep, cp=cuaderno)
    except Exception as msg:
        return str(msg)


@register.filter
def get_calalumce_valor(cuaderno_cep, alumno):
    try:
        cuaderno, cep = cuaderno_cep
        return cuaderno.calificacion_alumno_ce(alumno, cep.ce)
    except Exception as msg:
        return str(msg)

########  Fin de las dos funciones
#################################################

#################################################
########  Estas dos funciones trabajan juntas para crear una función de tres variables
########  Observarlas en cuadernodocente_accordion_content.html
########  cuaderno|get_cep:cep|get_calalumce:alumno
@register.filter
def get_cevp(cuaderno, cevp):
    return cuaderno, cevp


@register.filter
def get_calalumcev(cuaderno_cevp, alumno):
    try:
        cuaderno, cevp = cuaderno_cevp
        return CalAlumCEv.objects.get(calalumce__alumno=alumno, cevp=cevp, calalumce__cp=cuaderno)
    except Exception as msg:
        return str(msg)


########  Fin de las dos funciones
#################################################

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


########  Estas funciones calculan la calificación global de un alumno del cuaderno en función de su asignatura

@register.filter
def get_global_asignatura(cuaderno, asignatura):
    return cuaderno, asignatura


@register.filter
def get_global_cal_asignatura(cuaderno_asignatura, alumno):
    try:
        cuaderno, asignatura = cuaderno_asignatura
        return cuaderno.calificacion_alumno_asignatura(alumno, asignatura)
    except Exception as msg:
        return str(msg)


########  Fin de la función
#################################################


@register.filter
def puede_borrar(psec, g_e):
    try:
        return 'X' in psec.get_permiso(g_e.gauser_extra_programaciones)
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
