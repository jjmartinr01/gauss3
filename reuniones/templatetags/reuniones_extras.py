# -*- coding: utf-8 -*-
from django.template import Library
from actas.models import Convocatoria


register = Library()

@register.filter
def is_redactada_por(acta, g_e):
    return acta.is_redactada_por(g_e)

@register.filter
def lista_subentidades_convocadas(convocatoria):
    value = list(convocatoria.convocados.all().values_list('nombre', flat=True))
    l = len(value)
    if l == 0:
        return "la %s" % convocatoria.entidad.name
    elif l == 1:
        return value[0]
    s = ", ".join(value[:-1])
    return "%s y %s" % (s, value[-1])

@register.filter
def convocante(convocatoria):
    if convocatoria.convoca:
        return convocatoria.convoca.get_full_name()
    else:
        return "«convocante»"

@register.filter
def cargo_convocante(convocatoria):
    if convocatoria.cargo_convocante:
        return convocatoria.cargo_convocante.cargo
    else:
        return "«cargo del convocante»"

@register.filter
def lugar(convocatoria):
    if convocatoria.lugar:
        return convocatoria.lugar
    else:
        return "«lugar»"

@register.filter
def edita_conv_reunion(g_e, convocatoria):
    if g_e.gauser.username == 'gauss' or g_e.has_permiso('w_conv_reunion'):
        return True
    elif convocatoria.creador == g_e.gauser or convocatoria.convoca == g_e.gauser:
        return True
    elif g_e.has_permiso('w_conv_reunion'):
        subentidades_convocadas = convocatoria.convocados.all()
        for sub in g_e.subentidades.all():
            if sub in subentidades_convocadas:
                return True
    else:
        return False


@register.filter
def procesa_texto_convocatoria(convocatoria):
    fh = datetime.now()
    t = Template(convocatoria.texto_convocatoria)
    c = {'convocados': ', '.join(configuracion.subentidades_convocadas.all().values_list('nombre', flat=True)),
         'dia_nombre': fh.strftime('%A').lower(),
         'dia_num': fh.strftime('%d'),
         'mes_nombre': fh.strftime('%B').lower(),
         'year': fh.strftime('%Y'), 'nombre': configuracion.nombre,
         'hora': fh.strftime('%H:%M'), 'lugar': configuracion.lugar,
         'cargo_convocante': configuracion.cargo_convocante}
    context = Context(c)
    texto_base = t.render(context)
    c['texto_convocatoria'] = texto_base
    c['convocante'] = g_e
    texto_ejemplo_convocatoria = render_to_string('convocatoria_texto.html', {'c': c})
    value = list(convocatoria.convocados.all().values_list('nombre', flat=True))
    l = len(value)
    if l == 0:
        return ""
    elif l == 1:
        return value[0]
    s = ", ".join(value[:-1])
    return "%s y %s" % (s, value[-1])