# -*- coding: utf-8 -*-
from django.template import Library
from django.db.models import Q, Sum
from cupo.models import PlantillaXLS, PDocenteCol
from programaciones.models import Departamento

register = Library()


@register.filter
def departamentos(cupo):
    return Departamento.objects.filter(ronda=cupo.ronda)


##########################################

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

def calcula_plantilla_organica(departamento, horas_basicas):
    LCL_MU = (
    (10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7), (115, 129, 8),
    (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13), (205, 219, 14))
    RESTO = (
    (12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7), (124, 139, 8),
    (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13), (220, 235, 14))
    plantilla_organica = 0
    plantillas = LCL_MU if (departamento.nombre == 'Música' or 'astellana' in departamento.nombre) else RESTO
    for plantilla in plantillas:
        if horas_basicas >= plantilla[0] and horas_basicas <= plantilla[1]:
            plantilla_organica = plantilla[2]
    return plantilla_organica

@register.filter
def get_columnas_departamento(po, departamento):
    horas_totales, horas_basicas, columnas = 0, 0, []
    miembros_departamento = departamento.miembrodepartamento_set.all().values_list('g_e', flat=True)
    pdcols = PDocenteCol.objects.filter(pd__po=po, pd__g_e__id__in=miembros_departamento)
    for apartado in po.estructura_po:
        for nombre_columna, contenido_columna in po.estructura_po[apartado].items():
            periodos = pdcols.filter(codecol=contenido_columna['codecol']).aggregate(Sum('periodos'))['periodos__sum']
            horas_totales += periodos
            if contenido_columna['horas_base']:
                horas_basicas += periodos
            columnas.append({'codecol': contenido_columna['codecol'],
                             'periodos': periodos})
    hp = calcula_plantilla_organica(departamento, horas_basicas)
    return {'columnas': columnas, 'horas_basicas': horas_basicas, 'horas_totales': horas_totales, 'horas_plantilla': hp}

@register.filter
def get_columnas_docente(po, docente):
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


############################################

LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7), (115, 129, 8),
          (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13), (205, 219, 14))
RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7), (124, 139, 8),
         (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13), (220, 235, 14))


@register.filter
def horas_departamento(departamento, g_e):
    try:
        psXLS = PlantillaXLS.objects.filter(departamento=departamento, entidad=g_e.ronda.entidad)
    except:
        psXLS = PlantillaXLS.objects.filter(departamento=departamento, g_e=g_e)
    troncales = Q(grupo_materias__icontains='tronca') | Q(grupo_materias__icontains='extranj') | Q(
        grupo_materias__icontains='obligator')
    libreconf = Q(grupo_materias__icontains='libre conf')
    espec = Q(grupo_materias__icontains='espec')
    troneso = psXLS.filter(Q(etapa='da') & troncales).count()
    espeeso = psXLS.filter(Q(etapa='da') & espec).count()
    libreso = psXLS.filter(Q(etapa='da') & libreconf).count()
    tronbac = psXLS.filter(Q(etapa='fa') & troncales).count()
    espebac = psXLS.filter(Q(etapa='fa') & espec).count()
    gm = psXLS.filter(etapa='ga').count()
    gs = psXLS.filter(etapa='ha').count()
    fpb = psXLS.filter(etapa='ea').count()
    horas_basicas = troneso + espeeso + libreso + tronbac + espebac + gm + gs + fpb
    plantilla_organica = 0
    plantillas = LCL_MU if (departamento == 'Música' or 'astellana' in departamento) else RESTO
    for plantilla in plantillas:
        if horas_basicas >= plantilla[0] and horas_basicas <= plantilla[1]:
            plantilla_organica = plantilla[2]
    return {'troneso': troneso, 'espeeso': espeeso, 'libreso': libreso, 'tronbac': tronbac, 'espebac': espebac,
            'gm': gm, 'gs': gs, 'fpb': fpb, 'horas_basicas': horas_basicas, 'plantilla_organica': plantilla_organica}


@register.filter
def docentes_departamento(po, x_departamento):
    return po.plantilladocente_set.filter(x_departamento=x_departamento)


@register.filter
def plantilla_departamento(po, departamento):
    try:
        pds = po.plantilladocente_set.filter(departamento=departamento)
        sumas = pds.aggregate(
            Sum('tutorias'),
            Sum('cppaccffgs'),
            Sum('mayor55'),
            Sum('jefatura'),
            Sum('desdobbac'),
            Sum('desdobeso'),
            Sum('fpb'),
            Sum('gs'),
            Sum('gm'),
            Sum('espebac'),
            Sum('tronbac'),
            Sum('libreso'),
            Sum('espeeso'),
            Sum('troneso'),
            Sum('refuerzo1'),
            Sum('pmar2'),
            Sum('pmar1'),
            Sum('pacg'),
            Sum('relve'),
        )
        sumas['num_docentes'] = pds.count()
        sumas['departamento'] = departamento
        sumas['x_departamento'] = pds[0].x_departamento
        sumas['horas_basicas'] = sumas['troneso__sum'] + sumas['espeeso__sum'] + sumas['libreso__sum'] + sumas[
            'tronbac__sum'] + sumas['espebac__sum'] + sumas['gm__sum'] + sumas['gs__sum'] + sumas['fpb__sum'] + sumas[
                                     'desdobeso__sum'] + sumas['desdobbac__sum'] + sumas['jefatura__sum'] + sumas[
                                     'relve__sum']
        sumas['horas_totales'] = sumas['horas_basicas'] + sumas['mayor55__sum'] + sumas['cppaccffgs__sum'] + sumas[
            'tutorias__sum'] + sumas['refuerzo1__sum'] + sumas['pacg__sum'] + sumas['pmar1__sum'] + sumas['pmar2__sum']

        LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7),
                  (115, 129, 8), (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13),
                  (205, 219, 14), (220, 234, 15), (235, 249, 16), (250, 264, 17), (265, 279, 18), (280, 294, 19))
        RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7),
                 (124, 139, 8), (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13),
                 (220, 235, 14), (236, 251, 15), (252, 267, 16), (268, 283, 17), (284, 299, 18), (300, 235, 19))
        sumas['plantilla_organica'] = 0
        horas_basicas = sumas['horas_basicas']
        condicion = departamento == 'Música' or 'astellana' in departamento or 'Matem' in departamento
        plantillas = LCL_MU if condicion else RESTO
        for plantilla in plantillas:
            if horas_basicas >= plantilla[0] and horas_basicas <= plantilla[1]:
                sumas['plantilla_organica'] = plantilla[2]
        return sumas
    except Exception as msg:
        return str(msg)


@register.filter
def plantilla_departamento_ies(po, departamento):
    try:
        pds = po.plantilladocente_set.filter(departamento=departamento)
        sumas = pds.aggregate(
            Sum('tutorias'),
            Sum('cppaccffgs'),
            Sum('mayor55'),
            Sum('jefatura'),
            Sum('desdobbac'),
            Sum('desdobeso'),
            Sum('fpb'),
            Sum('gs'),
            Sum('gm'),
            Sum('espebac'),
            Sum('tronbac'),
            Sum('libreso'),
            Sum('espeeso'),
            Sum('troneso'),
            Sum('refuerzo1'),
            Sum('pmar2'),
            Sum('pmar1'),
            Sum('pacg'),
            Sum('relve'),
        )
        sumas['num_docentes'] = pds.count()
        sumas['departamento'] = departamento
        sumas['x_departamento'] = pds[0].x_departamento
        sumas['horas_basicas'] = sumas['troneso__sum'] + sumas['espeeso__sum'] + sumas['libreso__sum'] + sumas[
            'tronbac__sum'] + sumas['espebac__sum'] + sumas['gm__sum'] + sumas['gs__sum'] + sumas['fpb__sum'] + sumas[
                                     'desdobeso__sum'] + sumas['desdobbac__sum'] + sumas['jefatura__sum'] + sumas[
                                     'relve__sum']
        sumas['horas_totales'] = sumas['horas_basicas'] + sumas['mayor55__sum'] + sumas['cppaccffgs__sum'] + sumas[
            'tutorias__sum'] + sumas['refuerzo1__sum'] + sumas['pacg__sum'] + sumas['pmar1__sum'] + sumas['pmar2__sum']

        LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7),
                  (115, 129, 8), (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13),
                  (205, 219, 14), (220, 234, 15), (235, 249, 16), (250, 264, 17), (265, 279, 18), (280, 294, 19))
        RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7),
                 (124, 139, 8), (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13),
                 (220, 235, 14), (236, 251, 15), (252, 267, 16), (268, 283, 17), (284, 299, 18), (300, 235, 19))
        sumas['plantilla_organica'] = 0
        horas_basicas = sumas['horas_basicas']
        condicion = departamento == 'Música' or 'astellana' in departamento or 'Matem' in departamento
        plantillas = LCL_MU if condicion else RESTO
        for plantilla in plantillas:
            if horas_basicas >= plantilla[0] and horas_basicas <= plantilla[1]:
                sumas['plantilla_organica'] = plantilla[2]
        return sumas
    except Exception as msg:
        return str(msg)


@register.filter
def plantilla_departamento_cepa(po, departamento):
    pds = po.plantilladocente_set.filter(departamento=departamento)
    sumas = pds.aggregate(
        Sum('tutorias'),
        Sum('iniciales1'),
        Sum('iniciales2'),
        Sum('mayor55'),
        Sum('jefatura'),
        Sum('espa1'),
        Sum('espa2'),
        Sum('espads1'),
        Sum('espads2'),
        Sum('epaofi'),
        Sum('epainf'),
        Sum('epaing'),
        Sum('epamec'),
        Sum('epan2'),
        Sum('epainm'),
        Sum('epamay'),
    )
    sumas['num_docentes'] = pds.count()
    sumas['departamento'] = departamento
    sumas['x_departamento'] = pds[0].x_departamento
    sumas['horas_basicas'] = sumas['iniciales1__sum'] + sumas['iniciales2__sum'] + sumas['espa1__sum'] + sumas[
        'espa2__sum'] + sumas['espads1__sum'] + sumas['espads2__sum'] + sumas[
                                 'jefatura__sum'] + sumas['epainm__sum'] + sumas['epamay__sum'] + sumas[
                                 'epaofi__sum'] + sumas['epainf__sum'] + sumas[
                                 'epaing__sum'] + sumas['epamec__sum'] + sumas['epan2__sum']
    sumas['horas_totales'] = sumas['horas_basicas'] + sumas['mayor55__sum'] + sumas['tutorias__sum']

    LCL_MU = ((10, 24, 1), (25, 39, 2), (40, 54, 3), (55, 69, 4), (70, 84, 5), (85, 99, 6), (100, 114, 7),
              (115, 129, 8), (130, 144, 9), (145, 159, 10), (160, 174, 11), (175, 189, 12), (190, 204, 13),
              (205, 219, 14), (220, 234, 15), (235, 249, 16), (250, 264, 17), (265, 279, 18), (280, 294, 19))
    RESTO = ((12, 27, 1), (28, 43, 2), (44, 59, 3), (60, 75, 4), (76, 91, 5), (92, 107, 6), (108, 123, 7),
             (124, 139, 8), (140, 155, 9), (156, 171, 10), (172, 187, 11), (188, 203, 12), (204, 219, 13),
             (220, 235, 14), (236, 251, 15), (252, 267, 16), (268, 283, 17), (284, 299, 18), (300, 235, 19))
    sumas['plantilla_organica'] = 0
    horas_basicas = sumas['horas_basicas']
    condicion = departamento == 'Música' or 'astellana' in departamento or 'Matem' in departamento
    plantillas = LCL_MU if condicion else RESTO
    for plantilla in plantillas:
        if horas_basicas >= plantilla[0] and horas_basicas <= plantilla[1]:
            sumas['plantilla_organica'] = plantilla[2]
    return sumas
