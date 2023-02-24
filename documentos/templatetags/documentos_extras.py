# -*- coding: utf-8 -*-
from django.template import Library
from documentos.models import NormativaEtiqueta, Normativa

register = Library()


@register.filter
def permiso_w(doc, g_e):
    return 'w' in doc.permisos(g_e)

@register.filter
def permiso_x(doc, g_e):
    return 'x' in doc.permisos(g_e)

@register.filter
def get_permisos(doc, g_e):
    return doc.permisos(g_e)

@register.filter
def get_normativas(etiqueta):
    return Normativa.objects.filter(etiquetas__in=[etiqueta])