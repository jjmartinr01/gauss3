# -*- coding: utf-8 -*-
from django.template import Library
from autenticar.models import Permiso
from entidades.models import Subentidad
from horarios.models import Horario, Sesion
from tutorados.models import Pregunta, Respuesta, Fichero_tarea, Tarea_propuesta
from datetime import datetime

register = Library()


@register.filter
def respuesta(pregunta, g_e):
    try:
        r = Respuesta.objects.get(informe=pregunta.informe, pregunta=pregunta, usuario=g_e).respuesta
    except:
        r = ''
    return r


@register.filter
def materia(g_e, grupo):
    horario = Horario.objects.get(entidad=g_e.ronda.entidad, ronda=g_e.ronda, predeterminado=True)
    try:
        s = '(%s)' % Sesion.objects.filter(horario=horario, grupo=grupo, g_e=g_e)[0].materia.nombre
    except:
        s = ''
    return s


@register.filter
def ficheros_tarea(g_e, informe):
    return Fichero_tarea.objects.filter(tarea__usuario=g_e, tarea__informe=informe)


@register.filter
def texto_tarea(g_e, informe):
    tarea, c = Tarea_propuesta.objects.get_or_create(usuario=g_e, informe=informe)
    if c:
        tarea.fecha = datetime.today()
        tarea.texto_tarea = ''
        tarea.save()
    return Tarea_propuesta.objects.get(usuario=g_e, informe=informe).texto_tarea


@register.filter
def num_preguntas_responder(informe, g_e):
    preguntas = Pregunta.objects.filter(informe=informe).count()
    respuestas = Respuesta.objects.filter(informe=informe, usuario=g_e).count()
    faltan = preguntas - respuestas
    return faltan

@register.filter
def rellenado(informe, g_e):
    tareas = Tarea_propuesta.objects.filter(informe=informe, usuario=g_e).count()
    if tareas > 0:
        return True
    else:
        return False