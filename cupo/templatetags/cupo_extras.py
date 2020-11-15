# -*- coding: utf-8 -*-
from django.template import Library
from django.db.models import Q
from cupo.models import PlantillaXLS
from programaciones.models import Departamento

register = Library()


@register.filter
def departamentos(cupo):
    return Departamento.objects.filter(ronda=cupo.ronda)


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
