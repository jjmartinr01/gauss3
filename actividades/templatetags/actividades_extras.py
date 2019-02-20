# -*- coding: utf-8 -*-
from django import template
from datetime import datetime, date
from horarios.models import Horario, Tramo_horario
from estudios.models import Grupo

register = template.Library()

@register.filter
def future_dates_only(the_date):
   if the_date > date.today():
       return True
   else:
       return False


@register.filter
def tramos_horarios(actividad):
    horario = Horario.objects.get(entidad=actividad.organizador.entidad, predeterminado=True)
    return Tramo_horario.objects.filter(horario=horario)

@register.filter
def grupos_entidad(actividad):
    return Grupo.objects.filter(ronda=actividad.organizador.ronda)



