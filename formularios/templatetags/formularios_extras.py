# -*- coding: utf-8 -*-
from django.template import Library
from formularios.models import GSITIPOS, GformSection, GformSectionInput, GformResponde, GformRespondeInput

register = Library()


@register.filter
def cuestiones_grupo(ginputs, grupo):
    return ginputs.filter(grupo=grupo)

@register.filter
def hay_preguntas(gform, grupo):
    return gform.ginput_set.filter(grupo=grupo).count() > 0

@register.filter
def gsitipos(gfsi):
    return GSITIPOS


@register.filter
def totalgfsis(gfsi):
    return GformSectionInput.objects.filter(gformsection__gform=gfsi.gformsection.gform).count()

@register.filter
def elvalues(gfsi):
    return ['%s' % i for i in range(int(gfsi.elmin), int(gfsi.elmax + 1))]

@register.filter
def get_rfirma(gfsi, gformresponde):
    try:
        return GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rfirma
    except:
        return ''

@register.filter
def get_rtexto(gfsi, gformresponde):
    try:
        return GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rtexto
    except:
        return ''

@register.filter
def get_ifchecked(gfsio, gformresponde):
    gfsi = gfsio.gformsectioninput
    try:
        if gfsio in GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).ropciones.all():
            return 'checked'
        else:
            return ''
    except:
        return ''

@register.filter
def get_fich_name(gfsi, gformresponde):
    try:
        filename = GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rarchivo.name
        return filename.rpartition('/')[2]
    except:
        return ''

@register.filter
def get_el_value(gfsi, gformresponde):
    try:
        return GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rentero
    except:
        return ''

@register.filter
def checked_if_igual_a(a, b):
    if int(a) == int(b):
        return 'true'
    else:
        return 'false'
