# -*- coding: utf-8 -*-
from django.template import Library
from entidades.models import Subentidad
from estudios.models import Grupo, Materia
from horarios.models import Sesion
from datetime import datetime, time

register = Library()


# @register.filter
# def cursos_from_subentidad(subentidad):
#     try:
#         cursos_entidad = Curso.objects.filter(entidad=subentidad.entidad, grupos__in=[subentidad])
#     except:
#         sub = Subentidad.objects.get(id=subentidad)
#         cursos_entidad = Curso.objects.filter(entidad=sub.entidad, grupos__in=[sub])
#     return cursos_entidad


@register.filter
def filtrar_pds(pds, campo):
    if campo == 'profesor':
        return set([(pd.profesor.id, pd.profesor.gauser.get_full_name()) for pd in pds])
    elif campo == 'curso':
        return set(list(pds.values_list('grupo__cursos', 'grupo__cursos__nombre')))
    elif campo == 'grupo':
        return set(list(pds.values_list('grupo', 'grupo__nombre')))
    elif campo == 'plataforma_educativa':
        return set([(pd.plataforma, pd.get_plataforma_display()) for pd in pds])
    elif campo == 'plataforma_video':
        return set([(pd.platvideo, pd.get_platvideo_display()) for pd in pds])

@register.filter
def convierte_sino(sa, campo):
    estado = getattr(sa, campo)
    return 'Sí' if estado else 'No'


@register.filter
def grupos_curso(curso):
    return Grupo.objects.filter(cursos__in=[curso])


@register.filter
def materias_grupo(grupo):
    materias__id = grupo.sesion_set.filter(horario__predeterminado=True).values_list('materia__id', flat=True)
    return Materia.objects.filter(id__in=materias__id).distinct()


# @register.filter
# def hora_position(hora, hora_inicio):
#     hora_inicio = time(8, 15)
#     minutes_dif = hora.hour * 60 + hora.minute - hora_inicio.hour * 60 - hora_inicio.minute + 50
#     return minutes_dif


pixels_hora = 60
offset = 50

# @register.filter
# def horario_height(sesiones):
#     inicios = [s.inicio.hour for s in sesiones]
#     fines = [s.fin.hour for s in sesiones]
#     try:
#         h = (max(fines) - min(inicios) + 5)*pixels_hora + offset
#     except:
#         h = pixels_hora + offset
#     return h + 200

@register.filter
def horario_height(horas):
    inicio = horas[0][0]
    fin = horas[-1][0]
    try:
        h = (fin - inicio + 5)*pixels_hora + offset
    except:
        h = pixels_hora + offset
    return h + 200

@register.filter
def style_cell2(sesion):
    horario = sesion.horario
    sesiones_ge = horario.sesion_set.filter(g_e=sesion.g_e).order_by('dia')
    hora_inicio = sesiones_ge.order_by('inicio').values_list('inicio', flat=True)[0]
    top = sesion.inicio.hour * pixels_hora + sesion.inicio.minute * int(
        pixels_hora / 60) - hora_inicio.hour * pixels_hora - hora_inicio.minute * int(pixels_hora / 60) + offset
    height = sesion.fin.hour * pixels_hora + sesion.fin.minute * int(
        pixels_hora / 60) - sesion.inicio.hour * pixels_hora - sesion.inicio.minute * int(pixels_hora / 60)
    return "top: %spx;min-height: %spx;z-index: %s" % (top, height, sesion.inicio.hour)

@register.filter
def style_cell(sesion, hora_inicio):
    # hora_inicio = time(8, 15)
    top = sesion.inicio.hour * pixels_hora + sesion.inicio.minute * int(
        pixels_hora / 60) - hora_inicio.hour * pixels_hora - hora_inicio.minute * int(pixels_hora / 60) + offset
    height = sesion.fin.hour * pixels_hora + sesion.fin.minute * int(
        pixels_hora / 60) - sesion.inicio.hour * pixels_hora - sesion.inicio.minute * int(pixels_hora / 60)
    return "top: %spx;min-height: %spx;z-index: %s" % (top, height, sesion.inicio.hour)


@register.filter
def list_sesiones(sesiones, dia):
    return sesiones.filter(dia=dia)


@register.filter
def horas2(sesiones):
    try:
        # horario = sesiones[0].horario
        # sesiones_ge = horario.sesion_set.filter(g_e=sesion.g_e).order_by('dia')
        hora_inicio = sesiones.order_by('inicio').values_list('inicio', flat=True)[0]
        tuples = [(s.inicio, s.fin, s.inicio.hour * pixels_hora + s.inicio.minute * int(
        pixels_hora / 60) - hora_inicio.hour * pixels_hora - hora_inicio.minute * int(pixels_hora / 60) + offset) for s
              in sesiones.order_by('inicio')]
        tuples_definitivas = [tuples[0]]
        t_anterior = tuples[0][2]
        for t in tuples[1:]:
            diferencia = t[2] - t_anterior
            if diferencia > 24:
                tuples_definitivas.append(t)
            t_anterior = t[2]
        return tuples_definitivas
    except:
        return []

@register.filter
def top_hora(horas, position):
    hora_inicio = horas[0]
    hora= horas[position]
    return hora[0].hour * pixels_hora + hora[0].minute * int(pixels_hora / 60) - hora_inicio.hour * pixels_hora - hora_inicio.minute * int(pixels_hora / 60) + offset

@register.filter
def horas(sesiones, hora_inicio):
    # hora_inicio = time(8, 15)
    # tuples = []
    # for s in sesiones.order_by('inicio'):
    #     top = s.inicio.hour * pixels_hora + s.inicio.minute * int(
    #         pixels_hora / 60) - hora_inicio.hour * pixels_hora - hora_inicio.minute * int(pixels_hora / 60) + offset
    #     height = s.fin.hour * pixels_hora + s.fin.minute * int(
    #         pixels_hora / 60) - s.inicio.hour * pixels_hora - s.inicio.minute * int(pixels_hora / 60)
    #     tuples.append((s.inicio, s.fin, top, height))
    try:
        tuples = [(s.inicio, s.fin, s.inicio.hour * pixels_hora + s.inicio.minute * int(
        pixels_hora / 60) - hora_inicio.hour * pixels_hora - hora_inicio.minute * int(pixels_hora / 60) + offset) for s
              in sesiones.order_by('inicio')]
        tuples_definitivas = [tuples[0]]
        t_anterior = tuples[0][2]
        for t in tuples[1:]:
            diferencia = t[2] - t_anterior
            if diferencia > 24:
                tuples_definitivas.append(t)
            t_anterior = t[2]
        return tuples_definitivas
    except:
        return []


@register.filter
def sesiones_coincidentes(sesion, sesiones):
    return sesiones.filter(dia=sesion.dia, inicio=sesion.inicio)


@register.filter
def guardias(tramo, dia):
    return Sesion.objects.filter(horario=tramo[0], inicio=tramo[1], fin=tramo[2], actividad__guardia=True, dia=dia)

@register.filter
def alumnos(grupo):
    return grupo.gauser_extra_estudios_set.all().order_by('ge__gauser__last_name')