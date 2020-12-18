# -*- coding: utf-8 -*-
from django.template import Library
from formularios.models import GSITIPOS, GformSection, GformSectionInput
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





