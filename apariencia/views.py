# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
from apariencia.models import Apariencia_default, Apariencia


def apariencia(request):
    return HttpResponse('De momento no es posible configurar la apariencia')


def actualizar_apariencias(request):
    g_e = request.session['gauser_extra']
    apariencias = Apariencia_default.objects.all()
    for apariencia in apariencias:
        try:
            Apariencia.objects.get(code_texto=apariencia.code_texto)
        except:
            Apariencia.objects.create(entidad=g_e.ronda.entidad, code_texto=apariencia.code_texto,
                                      texto_default=apariencia.texto,
                                      texto=apariencia.texto, lugar=apariencia.lugar, acceso=True)
    return HttpResponse('Apariencias actualizadas')
