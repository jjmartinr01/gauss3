# -*- coding: utf-8 -*-
from difflib import get_close_matches
from django.template import Library
from django.db.models import Q, Sum
from cupo.models import PlantillaXLS, PDocenteCol, CargaPlantillaOrganicaCentros, EspecialidadPlantilla, PDocente
from entidades.models import Cargo, Gauser_extra
from horarios.models import SesionExtra, Sesion
from programaciones.models import Departamento
from estudios.models import Grupo, Curso

register = Library()


@register.filter
def departamentos(cupo):
    return Departamento.objects.filter(ronda=cupo.ronda)


##########################################
@register.filter
def get_horas_minutos(minutos):
    horas = int(minutos / 60)
    minutos = minutos % 60
    if horas == 0 and minutos == 0:
        return '---'
    elif horas == 0:
        return '%s minutos' % minutos
    elif minutos == 0:
        if horas == 1:
            return '1 hora'
        else:
            return '%s horas' % horas
    elif horas == 1:
        return '1 hora y %s minutos' % minutos
    else:
        return '%s horas y %s minutos' % (horas, minutos)


@register.filter
def get_sesiones_tiempo(sesiones):
    minutos_apoyos = 0
    for sesion in sesiones:
        minutos_apoyos += sesion.minutos
    return minutos_apoyos

@register.filter
def get_sextras_tiempo(sextras):
    minutos_apoyos = 0
    for sextra in sextras:
        minutos_apoyos += sextra.sesion.minutos
    return minutos_apoyos




@register.filter
def has_infantil_primaria(po):
    centros_infantil_primaria = ['C.E.I.P. - Colegio de Educación Infantil y Primaria',
                                 'C.R.A. - Colegio Rural Agrupado',
                                 'C.E.O. - Centro de Educación Obligatoria',
                                 'C.E.E. - Centro de Educación Especial',
                                 'E.I.P.C. - Escuela Infantil']
    if po.ronda_centro.entidad.entidadextra.tipo_centro in centros_infantil_primaria:
        return True
    else:
        return False

###########################################################################
@register.filter
def get_actividades_cursos(po, x_actividades):
    actividades = []
    minutos_actividades_total = 0
    areas = {'LCL': [168607, 170306, 168625, 170325, 168644, 170344],
             'LCRM': [168606, 170305, 168624, 170324, 168643, 170343],
             'MAT': [168608, 170307, 168626, 170326, 168645, 170345],
             'CCSS': [168604, 170303, 168622, 170322, 168641, 170341],
             'CCNN': [168605, 170304, 168623, 170323, 168642, 170342],
             'ING': [168615, 170314, 168633, 170333, 168652, 170352],
             'EF': [168612, 170311, 168630, 170330, 168649, 170349],
             'MUS': [168610, 170309, 168628, 170328, 168647, 170347],
             'PLA': [168611, 170310, 168629, 170329, 168648, 170348],
             'VSC': [168660, 170321, 168640, 170340, 168659, 170359]}

    cursos_id = Grupo.objects.filter(ronda=po.ronda_centro).values_list('cursos', flat=True).distinct()
    cursos = Curso.objects.filter(id__in=cursos_id)
    sextras_actividad = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex__in=x_actividades)
    for curso in cursos:
        dic = {'curso': curso}
        minutos_actividades = 0
        for materia, claves_extra in areas.items():
            sextras = sextras_actividad.filter(materia__clave_ex__in=claves_extra, grupo__cursos__in=[curso])
            ses_ids = sextras.values_list('sesion__id', flat=True).distinct()
            # dic[materia] = sextras_actividad.filter(materia__clave_ex__in=claves_extra, grupo__cursos__in=[curso])
            dic[materia] = Sesion.objects.filter(id__in=ses_ids)
            # for sextra in dic[materia]:
            #     minutos_actividades += sextra.sesion.minutos
            for sesion in Sesion.objects.filter(id__in=ses_ids):
                minutos_actividades += sesion.minutos
        dic['n'] = minutos_actividades
        minutos_actividades_total += minutos_actividades
        if minutos_actividades > 0:
            actividades.append(dic)
    return actividades

@register.filter
def get_actividades_grupos(po, x_actividades):
    "{'grupo': Grupo.objects.none(), 'LCL': sesiones, 'LCRM': sesiones, ...}"
    actividades = []
    minutos_actividades_total = 0
    areas = {'LCL': [168607, 170306, 168625, 170325, 168644, 170344],
             'LCRM': [168606, 170305, 168624, 170324, 168643, 170343],
             'MAT': [168608, 170307, 168626, 170326, 168645, 170345],
             'CCSS': [168604, 170303, 168622, 170322, 168641, 170341],
             'CCNN': [168605, 170304, 168623, 170323, 168642, 170342],
             'ING': [168615, 170314, 168633, 170333, 168652, 170352],
             'EF': [168612, 170311, 168630, 170330, 168649, 170349],
             'MUS': [168610, 170309, 168628, 170328, 168647, 170347],
             'PLA': [168611, 170310, 168629, 170329, 168648, 170348],
             'VSC': [168660, 170321, 168640, 170340, 168659, 170359]}

    grupos = Grupo.objects.filter(ronda=po.ronda_centro)
    sextras_actividad = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex__in=x_actividades)
    for grupo in grupos:
        dic = {'grupo': grupo}
        minutos_actividades = 0
        for materia, claves_extra in areas.items():
            # dic[materia] = sextras_actividad.filter(materia__clave_ex__in=claves_extra, grupo=grupo)
            # for sextra in dic[materia]:
            #     minutos_actividades += sextra.sesion.minutos

            sextras = sextras_actividad.filter(materia__clave_ex__in=claves_extra, grupo=grupo)
            ses_ids = sextras.values_list('sesion__id', flat=True).distinct()
            dic[materia] = Sesion.objects.filter(id__in=ses_ids)
            for sesion in Sesion.objects.filter(id__in=ses_ids):
                minutos_actividades += sesion.minutos

        dic['n'] = minutos_actividades
        minutos_actividades_total += minutos_actividades
        if minutos_actividades > 0:
            actividades.append(dic)
    return actividades

@register.filter
def get_actividades_infantil(po, x_actividades):
    actividads = []
    minutos_actividads_total = 0
    areas = {'CSMAP': [48053, 48066, 48080],
             'LCR': [48052, 48065, 48079],
             'CE': [48054, 48067, 48081],
             'Inglés': [48057, 48071, 48085],
             'AE': [48060, 48074, 48088],
             'RC': [48061, 48075, 48089]}
    grupos = Grupo.objects.filter(ronda=po.ronda_centro)
    sextras_actividad = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex__in=x_actividades)
    for grupo in grupos:
        dic = {'grupo': grupo}
        minutos_actividads = 0
        for materia, claves_extra in areas.items():
            dic[materia] = sextras_actividad.filter(materia__clave_ex__in=claves_extra, grupo=grupo)
            for sextra in dic[materia]:
                minutos_actividads += sextra.sesion.minutos
        dic['n'] = minutos_actividads
        minutos_actividads_total += minutos_actividads
        if minutos_actividads > 0:
            actividads.append(dic)
    return actividads

@register.filter
def get_docentes_actividad(po, x_actividades):
    actividads = []
    # etapas = {'INF': 3, 'PRI': 12}
    cursos = {'INF': [100304, 100305, 100306], 'PRI': [101317, 101318, 101319, 101320, 101321, 101322]}
    # grupos = Grupo.objects.filter(ronda=po.ronda_centro)
    sextras_actividad = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex__in=x_actividades)
    docentes = Gauser_extra.objects.filter(id__in=sextras_actividad.values_list('sesion__g_e', flat=True))
    for docente in docentes:
        minutos_actividad_infantil = 0
        sextras_actividad_infantil = sextras_actividad.filter(sesion__g_e=docente, grupo__cursos__clave_ex__in=cursos['INF'])
        ses_infantil = Sesion.objects.filter(id__in=sextras_actividad_infantil.values_list('sesion', flat=True)).distinct()
        for si in ses_infantil:
            minutos_actividad_infantil += si.minutos
        minutos_actividad_primaria = 0
        sextras_actividad_primaria = sextras_actividad.filter(sesion__g_e=docente, grupo__cursos__clave_ex__in=cursos['PRI'])
        ses_primaria = Sesion.objects.filter(id__in=sextras_actividad_primaria.values_list('sesion', flat=True)).distinct()
        for sp in ses_primaria:
            minutos_actividad_primaria += sp.minutos
        actividads.append({'docente':docente, 'infantil': minutos_actividad_infantil, 'primaria': minutos_actividad_primaria,
                       'total': minutos_actividad_infantil + minutos_actividad_primaria, 'ses_primaria': ses_primaria,
                       'ses_infantil': ses_infantil})
    return actividads

###########################################################################

@register.filter
def get_actividades_con_grupos(po):
    x_actividades = []
    actividades = []
    for a in po.plantillaxls_set.filter(x_actividad__iregex=r'\d', x_unidad__iregex=r'\d'):
        if a.x_actividad not in x_actividades and a.x_actividad != '1':
            x_actividades.append(a.x_actividad)
            actividades.append((a.x_actividad, a.actividad))
    return actividades


# @register.filter
# def docentes_desdoble(po):
#     desdobles = []
#     # etapas = {'INF': 3, 'PRI': 12}
#     cursos = {'INF': [100304, 100305, 100306], 'PRI': [101317, 101318, 101319, 101320, 101321, 101322]}
#     # grupos = Grupo.objects.filter(ronda=po.ronda_centro)
#     sextras_desdoble = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex='546')
#     docentes = Gauser_extra.objects.filter(id__in=sextras_desdoble.values_list('sesion__g_e', flat=True))
#     for docente in docentes:
#         minutos_desdoble_infantil = 0
#         sextras_desdoble_infantil = sextras_desdoble.filter(sesion__g_e=docente, grupo__cursos__clave_ex__in=cursos['INF'])
#         ses_infantil = Sesion.objects.filter(id__in=sextras_desdoble_infantil.values_list('sesion', flat=True)).distinct()
#         for si in ses_infantil:
#             minutos_desdoble_infantil += si.minutos
#         minutos_desdoble_primaria = 0
#         sextras_desdoble_primaria = sextras_desdoble.filter(sesion__g_e=docente, grupo__cursos__clave_ex__in=cursos['PRI'])
#         ses_primaria = Sesion.objects.filter(id__in=sextras_desdoble_primaria.values_list('sesion', flat=True)).distinct()
#         for sp in ses_primaria:
#             minutos_desdoble_primaria += sp.minutos
#         desdobles.append({'docente':docente, 'infantil': minutos_desdoble_infantil, 'primaria': minutos_desdoble_primaria,
#                        'total': minutos_desdoble_infantil + minutos_desdoble_primaria, 'ses_primaria': ses_primaria,
#                        'ses_infantil': ses_infantil})
#     return desdobles

# @register.filter
# def docentes_apoyo(po):
#     apoyos = []
#     # etapas = {'INF': 3, 'PRI': 12}
#     cursos = {'INF': [100304, 100305, 100306], 'PRI': [101317, 101318, 101319, 101320, 101321, 101322]}
#     # grupos = Grupo.objects.filter(ronda=po.ronda_centro)
#     sextras_apoyo = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex='522')
#     docentes = Gauser_extra.objects.filter(id__in=sextras_apoyo.values_list('sesion__g_e', flat=True))
#     for docente in docentes:
#         minutos_apoyo_infantil = 0
#         sextras_apoyo_infantil = sextras_apoyo.filter(sesion__g_e=docente, grupo__cursos__clave_ex__in=cursos['INF'])
#         ses_infantil = Sesion.objects.filter(id__in=sextras_apoyo_infantil.values_list('sesion', flat=True)).distinct()
#         for si in ses_infantil:
#             minutos_apoyo_infantil += si.minutos
#         minutos_apoyo_primaria = 0
#         sextras_apoyo_primaria = sextras_apoyo.filter(sesion__g_e=docente, grupo__cursos__clave_ex__in=cursos['PRI'])
#         ses_primaria = Sesion.objects.filter(id__in=sextras_apoyo_primaria.values_list('sesion', flat=True)).distinct()
#         for sp in ses_primaria:
#             minutos_apoyo_primaria += sp.minutos
#         apoyos.append({'docente':docente, 'infantil': minutos_apoyo_infantil, 'primaria': minutos_apoyo_primaria,
#                        'total': minutos_apoyo_infantil + minutos_apoyo_primaria, 'ses_primaria': ses_primaria,
#                        'ses_infantil': ses_infantil})
#     return apoyos


# @register.filter
# def get_apoyos(po):
#     "{'grupo': Grupo.objects.none(), 'LCL': sesiones, 'LCRM': sesiones, ...}"
#     apoyos = []
#     # num_apoyos_total = 0
#     minutos_apoyos_total = 0
#     areas = {'LCL': [168607, 170306, 168625, 170325, 168644, 170344],
#              'LCRM': [168606, 170305, 168624, 170324, 168643, 170343],
#              'MAT': [168608, 170307, 168626, 170326, 168645, 170345],
#              'CCSS': [168604, 170303, 168622, 170322, 168641, 170341],
#              'CCNN': [168605, 170304, 168623, 170323, 168642, 170342],
#              'ING': [168615, 170314, 168633, 170333, 168652, 170352],
#              'EF': [168612, 170311, 168630, 170330, 168649, 170349],
#              'MUS': [168610, 170309, 168628, 170328, 168647, 170347],
#              'PLA': [168611, 170310, 168629, 170329, 168648, 170348],
#              'VSC': [168660, 170321, 168640, 170340, 168659, 170359]}
#
#     grupos = Grupo.objects.filter(ronda=po.ronda_centro)
#     sextras_apoyo = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex='522')
#     for grupo in grupos:
#         dic = {'grupo': grupo}
#         minutos_apoyos = 0
#         for materia, claves_extra in areas.items():
#             dic[materia] = sextras_apoyo.filter(materia__clave_ex__in=claves_extra, grupo=grupo)
#             for sextra in dic[materia]:
#                 minutos_apoyos += sextra.sesion.minutos
#         dic['n'] = minutos_apoyos
#         minutos_apoyos_total += minutos_apoyos
#         if minutos_apoyos > 0:
#             apoyos.append(dic)
#     return apoyos

# @register.filter
# def get_apoyos_grupos(po):
#     "{'grupo': Grupo.objects.none(), 'LCL': sesiones, 'LCRM': sesiones, ...}"
#     apoyos = []
#     minutos_apoyos_total = 0
#     areas = {'LCL': [168607, 170306, 168625, 170325, 168644, 170344],
#              'LCRM': [168606, 170305, 168624, 170324, 168643, 170343],
#              'MAT': [168608, 170307, 168626, 170326, 168645, 170345],
#              'CCSS': [168604, 170303, 168622, 170322, 168641, 170341],
#              'CCNN': [168605, 170304, 168623, 170323, 168642, 170342],
#              'ING': [168615, 170314, 168633, 170333, 168652, 170352],
#              'EF': [168612, 170311, 168630, 170330, 168649, 170349],
#              'MUS': [168610, 170309, 168628, 170328, 168647, 170347],
#              'PLA': [168611, 170310, 168629, 170329, 168648, 170348],
#              'VSC': [168660, 170321, 168640, 170340, 168659, 170359]}
#
#     grupos = Grupo.objects.filter(ronda=po.ronda_centro)
#     sextras_apoyo = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex='522')
#     for grupo in grupos:
#         dic = {'grupo': grupo}
#         minutos_apoyos = 0
#         for materia, claves_extra in areas.items():
#             # dic[materia] = sextras_apoyo.filter(materia__clave_ex__in=claves_extra, grupo=grupo)
#             # for sextra in dic[materia]:
#             #     minutos_apoyos += sextra.sesion.minutos
#
#             sextras = sextras_apoyo.filter(materia__clave_ex__in=claves_extra, grupo=grupo)
#             ses_ids = sextras.values_list('sesion__id', flat=True).distinct()
#             dic[materia] = Sesion.objects.filter(id__in=ses_ids)
#             for sesion in Sesion.objects.filter(id__in=ses_ids):
#                 minutos_apoyos += sesion.minutos
#
#         dic['n'] = minutos_apoyos
#         minutos_apoyos_total += minutos_apoyos
#         if minutos_apoyos > 0:
#             apoyos.append(dic)
#     return apoyos

# @register.filter
# def get_apoyos_cursos(po):
#     apoyos = []
#     minutos_apoyos_total = 0
#     areas = {'LCL': [168607, 170306, 168625, 170325, 168644, 170344],
#              'LCRM': [168606, 170305, 168624, 170324, 168643, 170343],
#              'MAT': [168608, 170307, 168626, 170326, 168645, 170345],
#              'CCSS': [168604, 170303, 168622, 170322, 168641, 170341],
#              'CCNN': [168605, 170304, 168623, 170323, 168642, 170342],
#              'ING': [168615, 170314, 168633, 170333, 168652, 170352],
#              'EF': [168612, 170311, 168630, 170330, 168649, 170349],
#              'MUS': [168610, 170309, 168628, 170328, 168647, 170347],
#              'PLA': [168611, 170310, 168629, 170329, 168648, 170348],
#              'VSC': [168660, 170321, 168640, 170340, 168659, 170359]}
#
#     cursos_id = Grupo.objects.filter(ronda=po.ronda_centro).values_list('cursos', flat=True).distinct()
#     cursos = Curso.objects.filter(id__in=cursos_id)
#     sextras_apoyo = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex='522')
#     for curso in cursos:
#         dic = {'curso': curso}
#         minutos_apoyos = 0
#         for materia, claves_extra in areas.items():
#             sextras = sextras_apoyo.filter(materia__clave_ex__in=claves_extra, grupo__cursos__in=[curso])
#             ses_ids = sextras.values_list('sesion__id', flat=True).distinct()
#             # dic[materia] = sextras_apoyo.filter(materia__clave_ex__in=claves_extra, grupo__cursos__in=[curso])
#             dic[materia] = Sesion.objects.filter(id__in=ses_ids)
#             # for sextra in dic[materia]:
#             #     minutos_apoyos += sextra.sesion.minutos
#             for sesion in Sesion.objects.filter(id__in=ses_ids):
#                 minutos_apoyos += sesion.minutos
#         dic['n'] = minutos_apoyos
#         minutos_apoyos_total += minutos_apoyos
#         if minutos_apoyos > 0:
#             apoyos.append(dic)
#     return apoyos


# @register.filter
# def get_apoyos_infantil(po):
#     apoyos = []
#     minutos_apoyos_total = 0
#     areas = {'CSMAP': [48053, 48066, 48080],
#              'LCR': [48052, 48065, 48079],
#              'CE': [48054, 48067, 48081],
#              'Inglés': [48057, 48071, 48085],
#              'AE': [48060, 48074, 48088],
#              'RC': [48061, 48075, 48089]}
#     grupos = Grupo.objects.filter(ronda=po.ronda_centro)
#     sextras_apoyo = SesionExtra.objects.filter(sesion__horario=po.horario, actividad__clave_ex='522')
#     for grupo in grupos:
#         dic = {'grupo': grupo}
#         minutos_apoyos = 0
#         for materia, claves_extra in areas.items():
#             dic[materia] = sextras_apoyo.filter(materia__clave_ex__in=claves_extra, grupo=grupo)
#             for sextra in dic[materia]:
#                 minutos_apoyos += sextra.sesion.minutos
#         dic['n'] = minutos_apoyos
#         minutos_apoyos_total += minutos_apoyos
#         if minutos_apoyos > 0:
#             apoyos.append(dic)
#     return apoyos


##########################################
@register.filter
def get_plazas_puesto_incompletas(objeto, puesto):
    completas = ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '24:00']
    if objeto.__class__.__name__ == 'Entidad':
        centro = objeto  # El objeto es del tipo Entidad
    else:
        centro = objeto.ronda_centro.entidad  # El objeto es del tipo PlantillaOrganica
    ges_totales = Gauser_extra.objects.filter(ronda=centro.ronda, puesto=puesto)
    ges_completas = ges_totales.filter(jornada_contratada__in=completas)
    return ges_totales.count() - ges_completas.count()


@register.filter
def get_plazas_puesto_completas(objeto, puesto):
    completas = ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '24:00']
    if objeto.__class__.__name__ == 'Entidad':
        centro = objeto  # El objeto es del tipo Entidad
    else:
        centro = objeto.ronda_centro.entidad  # El objeto es del tipo PlantillaOrganica
    ges_totales = Gauser_extra.objects.filter(ronda=centro.ronda, puesto=puesto)
    ges_completas = ges_totales.filter(jornada_contratada__in=completas)
    return ges_completas.count()


@register.filter
def get_plazas_puesto(objeto, puesto):
    cpoc = CargaPlantillaOrganicaCentros.objects.all().last()
    if objeto.__class__.__name__ == 'Entidad':
        centro = objeto  # El objeto es del tipo Entidad
    else:
        centro = objeto.ronda_centro.entidad  # El objeto es del tipo PlantillaOrganica
    eps = EspecialidadPlantilla.objects.filter(cpoc=cpoc, centro=centro)
    nombres = eps.values_list('nombre', flat=True)
    # return get_close_matches(puesto.upper(), nombres, 1)
    return eps.filter(nombre__in=get_close_matches(puesto.upper(), nombres, 1))


@register.filter
def get_plazas(objeto):
    cpoc = CargaPlantillaOrganicaCentros.objects.all().last()
    if objeto.__class__.__name__ == 'Entidad':
        entidad = objeto  # El objeto es del tipo Entidad
        return EspecialidadPlantilla.objects.filter(cpoc=cpoc, centro=entidad)
    else:
        po = objeto  # El objeto es del tipo PlantillaOrganica
        return EspecialidadPlantilla.objects.filter(cpoc=cpoc, centro=po.ronda_centro.entidad)


@register.filter
def get_fecha_plazas(po):
    return CargaPlantillaOrganicaCentros.objects.all().last().creado


@register.filter
def get_apartados(po):
    apartados = []
    num_cols = 0
    for apartado in po.estructura_po:
        num_cols += len(po.estructura_po[apartado])
    for apartado in po.estructura_po:
        colspan = len(po.estructura_po[apartado])
        apartados.append({'nombre': apartado, 'colspan': colspan,
                          'width': int(po.anchura_cols[1] * colspan / num_cols)})
    return apartados


@register.filter
def get_columnas(po):
    columnas = []
    for apartado in po.estructura_po:
        for nombre_columna in po.estructura_po[apartado]:
            columnas.append(nombre_columna)
    return columnas


def calcula_plantilla_organica_edb(edb, horas_basicas):
    def num_profesores_calculados(min_num_horas, intervalo_horas, horas):
        if horas < min_num_horas:
            return 0
        else:
            return int((horas - min_num_horas) / intervalo_horas) + 1

    if edb.puesto == 'Música' or 'astellana' in edb.puesto:
        return num_profesores_calculados(10, 15, horas_basicas)
    else:
        return num_profesores_calculados(12, 16, horas_basicas)


def calcula_plantilla_organica(departamento, horas_basicas):
    def num_profesores_calculados(min_num_horas, intervalo_horas, horas):
        if horas < min_num_horas:
            return 0
        else:
            return int((horas - min_num_horas) / intervalo_horas) + 1

    if departamento.nombre == 'Música' or 'astellana' in departamento.nombre:
        return num_profesores_calculados(10, 15, horas_basicas)
    else:
        return num_profesores_calculados(12, 16, horas_basicas)
    # LCL_MU = (
    #     (10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7), (115, 129, 8),
    #     (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13), (205, 219, 14))
    # RESTO = (
    #     (12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7), (124, 139, 8),
    #     (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13), (220, 235, 14))
    # plantilla_organica = 0
    # plantillas = LCL_MU if (departamento.nombre == 'Música' or 'astellana' in departamento.nombre) else RESTO
    # for plantilla in plantillas:
    #     if horas_basicas >= plantilla[0] and horas_basicas <= plantilla[1]:
    #         plantilla_organica = plantilla[2]
    # return plantilla_organica


@register.filter
def get_columnas_edb(po, edb):
    horas_totales, horas_basicas, columnas = 0, 0, []
    miembros_edb = edb.miembroedb_set.all().values_list('g_e', flat=True)
    pdcols = PDocenteCol.objects.filter(pd__po=po, pd__g_e__id__in=miembros_edb)
    for apartado in po.estructura_po:
        for nombre_columna, contenido_columna in po.estructura_po[apartado].items():
            periodos = pdcols.filter(codecol=contenido_columna['codecol']).aggregate(Sum('periodos'))['periodos__sum']
            if not periodos:
                periodos = 0
            horas_totales += periodos
            if contenido_columna['horas_base']:
                horas_basicas += periodos
            columnas.append({'codecol': contenido_columna['codecol'],
                             'periodos': periodos})
    hp = calcula_plantilla_organica_edb(edb, horas_basicas)
    return {'columnas': columnas, 'horas_basicas': horas_basicas, 'horas_totales': horas_totales,
            'horas_plantilla': hp, 'departamento': edb.id}


@register.filter
def get_columnas_departamento(po, departamento):
    horas_totales, horas_basicas, columnas = 0, 0, []
    miembros_departamento = departamento.miembrodepartamento_set.all().values_list('g_e', flat=True)
    pdcols = PDocenteCol.objects.filter(pd__po=po, pd__g_e__id__in=miembros_departamento)
    for apartado in po.estructura_po:
        for nombre_columna, contenido_columna in po.estructura_po[apartado].items():
            periodos = pdcols.filter(codecol=contenido_columna['codecol']).aggregate(Sum('periodos'))['periodos__sum']
            if not periodos:
                periodos = 0
            horas_totales += periodos
            if contenido_columna['horas_base']:
                horas_basicas += periodos
            columnas.append({'codecol': contenido_columna['codecol'],
                             'periodos': periodos})
    hp = calcula_plantilla_organica(departamento, horas_basicas)
    return {'columnas': columnas, 'horas_basicas': horas_basicas, 'horas_totales': horas_totales,
            'horas_plantilla': hp, 'departamento': departamento.id}


@register.filter
def get_columnas_docente2(po, docente):
    horas_totales, horas_basicas, columnas = 0, 0, []
    pdcols = PDocenteCol.objects.filter(pd__po=po, pd__g_e=docente)
    for apartado in po.estructura_po:
        for nombre_columna, contenido_columna in po.estructura_po[apartado].items():
            periodos = pdcols.filter(codecol=contenido_columna['codecol']).aggregate(Sum('periodos'))['periodos__sum']
            horas_totales += periodos
            if contenido_columna['horas_base']:
                horas_basicas += periodos
            columnas.append({'codecol': contenido_columna['codecol'],
                             'periodos': periodos})
    return {'columnas': columnas, 'horas_basicas': horas_basicas, 'horas_totales': horas_totales}


@register.filter
def get_pdocente(po, docente):
    return PDocente.objects.get(po=po, g_e=docente)


# def get_pdcol(docente, po):
#     return PDocenteCol.objects.filter(pd__po=po, pd__g_e=docente)
@register.filter
def pdocentecolset(pdocente, localidad):
    return pdocente.pdocentecol_set.filter(localidad=localidad)


@register.filter
def get_columnas_docente(po, docente):
    minutos_totales, horas_totales, horas_basicas, columnas = 0, 0, 0, []
    pd = PDocente.objects.get(po=po, g_e=docente)
    mins_periodo = pd.calcula_minutos_periodo()
    pdcols = PDocenteCol.objects.filter(pd__po=po, pd__g_e=docente)
    for apartado in po.estructura_po:
        for nombre_columna, contenido_columna in po.estructura_po[apartado].items():
            periodos, minutos = 0, 0
            for pdc in pdcols.filter(codecol=contenido_columna['codecol']):
                periodos += pdc.periodos
                minutos += pdc.minutos
            horas_totales += periodos
            minutos_totales += minutos
            if contenido_columna['horas_base']:
                horas_basicas += periodos
            columnas.append({'codecol': contenido_columna['codecol'],
                             'periodos': periodos, 'minutos': minutos})
    return {'columnas': columnas, 'horas_basicas': horas_basicas, 'horas_totales': horas_totales,
            'minutos_totales': minutos_totales, 'horas': minutos_totales / mins_periodo, 'mins_periodo': mins_periodo}


@register.filter
def get_grupos(po):
    return Grupo.objects.filter(ronda=po.ronda_centro)


############################################

@register.filter
def get_horas_media(cc):
    horas = 0
    for materia in cc.materia_cupo_set.all():
        horas += materia.horas * materia.num_alumnos
    try:
        return horas / cc.num_alumnos
    except:
        return 0

# LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7), (115, 129, 8),
#           (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13), (205, 219, 14))
# RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7), (124, 139, 8),
#          (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13), (220, 235, 14))


# @register.filter
# def horas_departamento(departamento, g_e):
#     try:
#         psXLS = PlantillaXLS.objects.filter(departamento=departamento, entidad=g_e.ronda.entidad)
#     except:
#         psXLS = PlantillaXLS.objects.filter(departamento=departamento, g_e=g_e)
#     troncales = Q(grupo_materias__icontains='tronca') | Q(grupo_materias__icontains='extranj') | Q(
#         grupo_materias__icontains='obligator')
#     libreconf = Q(grupo_materias__icontains='libre conf')
#     espec = Q(grupo_materias__icontains='espec')
#     troneso = psXLS.filter(Q(etapa='da') & troncales).count()
#     espeeso = psXLS.filter(Q(etapa='da') & espec).count()
#     libreso = psXLS.filter(Q(etapa='da') & libreconf).count()
#     tronbac = psXLS.filter(Q(etapa='fa') & troncales).count()
#     espebac = psXLS.filter(Q(etapa='fa') & espec).count()
#     gm = psXLS.filter(etapa='ga').count()
#     gs = psXLS.filter(etapa='ha').count()
#     fpb = psXLS.filter(etapa='ea').count()
#     horas_basicas = troneso + espeeso + libreso + tronbac + espebac + gm + gs + fpb
#     plantilla_organica = 0
#     plantillas = LCL_MU if (departamento == 'Música' or 'astellana' in departamento) else RESTO
#     for plantilla in plantillas:
#         if horas_basicas >= plantilla[0] and horas_basicas <= plantilla[1]:
#             plantilla_organica = plantilla[2]
#     return {'troneso': troneso, 'espeeso': espeeso, 'libreso': libreso, 'tronbac': tronbac, 'espebac': espebac,
#             'gm': gm, 'gs': gs, 'fpb': fpb, 'horas_basicas': horas_basicas, 'plantilla_organica': plantilla_organica}
#

# @register.filter
# def docentes_departamento(po, x_departamento):
#     return po.plantilladocente_set.filter(x_departamento=x_departamento)


# @register.filter
# def plantilla_departamento(po, departamento):
#     try:
#         pds = po.plantilladocente_set.filter(departamento=departamento)
#         sumas = pds.aggregate(
#             Sum('tutorias'),
#             Sum('cppaccffgs'),
#             Sum('mayor55'),
#             Sum('jefatura'),
#             Sum('desdobbac'),
#             Sum('desdobeso'),
#             Sum('fpb'),
#             Sum('gs'),
#             Sum('gm'),
#             Sum('espebac'),
#             Sum('tronbac'),
#             Sum('libreso'),
#             Sum('espeeso'),
#             Sum('troneso'),
#             Sum('refuerzo1'),
#             Sum('pmar2'),
#             Sum('pmar1'),
#             Sum('pacg'),
#             Sum('relve'),
#         )
#         sumas['num_docentes'] = pds.count()
#         sumas['departamento'] = departamento
#         sumas['x_departamento'] = pds[0].x_departamento
#         sumas['horas_basicas'] = sumas['troneso__sum'] + sumas['espeeso__sum'] + sumas['libreso__sum'] + sumas[
#             'tronbac__sum'] + sumas['espebac__sum'] + sumas['gm__sum'] + sumas['gs__sum'] + sumas['fpb__sum'] + sumas[
#                                      'desdobeso__sum'] + sumas['desdobbac__sum'] + sumas['jefatura__sum'] + sumas[
#                                      'relve__sum']
#         sumas['horas_totales'] = sumas['horas_basicas'] + sumas['mayor55__sum'] + sumas['cppaccffgs__sum'] + sumas[
#             'tutorias__sum'] + sumas['refuerzo1__sum'] + sumas['pacg__sum'] + sumas['pmar1__sum'] + sumas['pmar2__sum']
#
#         LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7),
#                   (115, 129, 8), (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13),
#                   (205, 219, 14), (220, 234, 15), (235, 249, 16), (250, 264, 17), (265, 279, 18), (280, 294, 19))
#         RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7),
#                  (124, 139, 8), (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13),
#                  (220, 235, 14), (236, 251, 15), (252, 267, 16), (268, 283, 17), (284, 299, 18), (300, 235, 19))
#         sumas['plantilla_organica'] = 0
#         horas_basicas = sumas['horas_basicas']
#         condicion = departamento == 'Música' or 'astellana' in departamento or 'Matem' in departamento
#         plantillas = LCL_MU if condicion else RESTO
#         for plantilla in plantillas:
#             if horas_basicas >= plantilla[0] and horas_basicas <= plantilla[1]:
#                 sumas['plantilla_organica'] = plantilla[2]
#         return sumas
#     except Exception as msg:
#         return str(msg)
