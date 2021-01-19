# -*- coding: utf-8 -*-


# En Gauss_educa manage.py shell:
from extraescolares.models import *
from datetime import datetime
acts = Actividad.objects.filter(centro__id=1, fecha_inicio__gte=datetime.strptime('01/09/2017', '%d/%m/%Y'))

actividades=[]
for a in acts:
    act={}
    act['organizador']=a.organizador.id
    act['actividad_title']=a.actividad_title
    act['description']=a.description
    act['fecha_inicio'] = a.fecha_inicio.strftime('%d/%m/%Y')
    act['fecha_fin'] = a.fecha_fin.strftime('%d/%m/%Y')
    act['tramos_horarios'] = list(a.tramos_horarios.all().values_list('id', flat=True))
    act['colaboradores'] = list(a.colaboradores.all().values_list('id', flat=True))
    act['alumnos_incluidos'] = list(a.alumnos_incluidos.all().values_list('id', flat=True))
    act['aprobada'] = a.aprobada
    act['slideable'] = a.slideable
    actividades.append(act)

# El objeto actividades lo grabamos en un archivo:

f=open('actividades.txt', 'w')
import json
d=json.dumps(actividades)
f.write(d)
f.close()

# El archivo en copiado en Gauss_asocia. Arrancamos Gauss_asocia manage.py shell:

f=open('actividades.txt')
acts=json.load(f)

# Tenemos ahora cargado en acts las actividades de Gauss_educa. Definimos la función

from horarios.models import Tramo_horario
from calendario.models import *
from django.template.loader import render_to_string

def crea_evento_actividad(g_e, actividad):
    tramos_horarios = Tramo_horario.objects.filter(horario__entidad=g_e.ronda.entidad,
                                                   horario__ronda=g_e.ronda).order_by('inicio')
    description = render_to_string('actividad_event_description.html', {'actividad': actividad})
    inicio = datetime.combine(actividad.fecha_inicio, tramos_horarios.first().inicio)
    fin = datetime.combine(actividad.fecha_fin, tramos_horarios.last().fin)
    evento = Vevent.objects.create(entidad=g_e.ronda.entidad, uid='extraescolar' + str(actividad.id), dtend=fin,
                                   description=description, dtstart=inicio,
                                   summary=actividad.actividad_title)
    evento.propietarios.add(g_e.gauser)
    evento.subentidades.add(*Subentidad.objects.filter(entidad=g_e.ronda.entidad))
    return evento


for a in acts:
    g_e = Gauser_extra.objects.get(educa_pk=a['organizador'])
    actividad = Actividad.objects.create(organizador=g_e, actividad_title=a['actividad_title'],description=a['description'],fecha_inicio=datetime.strptime(a['fecha_inicio'], '%d/%m/%Y'),fecha_fin=datetime.strptime(a['fecha_fin'], '%d/%m/%Y'),aprobada=False, slideable=True)
    equ_tramos_horarios={'Aquí escribir equivalencia entre tramos horarios'}
    for t in a['tramos_horarios']:
        tramo = Tramo_horario.objects.get(id=equ_tramos_horarios[t])
        actividad.tramos_horarios.add(tramo)
    for c in a['colaboradores']:
        ge = Gauser_extra.objects.get(educa_pk=c)
        actividad.colaboradores.add(ge)
    for a in a['alumnos_incluidos']:
        ge = Gauser_extra.objects.get(educa_pk=a)
        actividad.alumnos_incluidos.add(ge)
    crea_evento_actividad(g_e, actividad)