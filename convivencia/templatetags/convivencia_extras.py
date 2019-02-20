# -*- coding: utf-8 -*-
from django.template import Library
from django.db.models import Q
from autenticar.models import Permiso
from convivencia.models import *
from entidades.models import Subentidad
from estudios.models import Curso

register = Library()


@register.filter
def has_any_cargo(gauser_extra, cargos_comprobar):
    if gauser_extra.gauser.username == 'gauss':
        return True
    else:
        return len([cargo for cargo in gauser_extra.cargos.all() if cargo in cargos_comprobar]) > 0


# @register.filter
# def sanciones(conductas):
#     s = []
#     for conducta in conductas:
#         for sancion in conducta.sanciones.all():
#             s.append(sancion.id)
#     return Sancion.objects.filter(id__in=set(s))

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
def estadistica_informes(sancionado):
    informes = Informe_sancionador.objects.filter(Q(sancionado=sancionado), ~Q(fichero=''))
    cnc, gpc, rof, exp = 0, 0, 0, 0
    for informe in informes:
        cnc += informe.conductas.filter(tipo='CNC').count()
        gpc += informe.conductas.filter(tipo='GPC').count()
        rof += informe.conductas.filter(tipo='ROF').count()
        exp += [0, 1][informe.expulsion]
    return {'cnc': cnc, 'gpc': gpc, 'rof': rof, 'exp': exp, 'informes': informes, 'tcnc': cnc + rof}

@register.filter
def estadistica_informes_is2pdf(sancionado):
    informes = Informe_sancionador.objects.filter(sancionado=sancionado)
    cnc, gpc, rof, exp = 0, 0, 0, 0
    for informe in informes:
        cnc += informe.conductas.filter(tipo='CNC').count()
        gpc += informe.conductas.filter(tipo='GPC').count()
        rof += informe.conductas.filter(tipo='ROF').count()
        exp += [0, 1][informe.expulsion]
    return {'cnc': cnc, 'gpc': gpc, 'rof': rof, 'exp': exp, 'informes': informes.count(), 'tcnc': cnc + rof}


@register.filter
def get_grupos(gauser_extra):
    sub_alumnos = Subentidad.objects.get(entidad=gauser_extra.ronda.entidad, clave_ex='alumnos')
    grupos = gauser_extra.subentidades.filter(parent=sub_alumnos).values_list('nombre', flat=True)
    return ', '.join(list(set(grupos)))

@register.filter
def get_cursos(gauser_extra):
    sub_alumnos = Subentidad.objects.get(entidad=gauser_extra.ronda.entidad, clave_ex='alumnos')
    grupos = gauser_extra.subentidades.filter(parent=sub_alumnos)
    cursos = Curso.objects.filter(grupos__in=grupos).values_list('nombre', flat=True)
    return ', '.join(list(set(cursos)))

# @register.filter
# def impone_sancion(gauser_extra, sancion):
#     permiso = False
#     for cargo in sancion.cargos.all():
#         if cargo in gauser_extra.cargos.all():
#             permiso = True
#     return permiso