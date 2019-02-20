# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import os
import random
import string

from django.forms import ModelForm
from django.shortcuts import render
from django.core.files import File
from django.template import RequestContext
from django.template.loader import render_to_string

# from autenticar.models import Gauser_extra, Permiso, Gauser
# from entidades.models import Entidad, Ronda
from autenticar.models import Permiso, Gauser, Menu_default
from entidades.models import Entidad, Ronda, Gauser_extra, Menu
from mensajes.models import Aviso
from mensajes.views import crear_aviso
from gauss.rutas import *
from entidades.models import Gauser_extra as GE



class EntidadForm(ModelForm):
    class Meta:
        model = Entidad
        exclude = ('ronda', 'anagrama')
        # widgets = {'iban': TextInput(attrs={'size': '30'}),
        #            'address': TextInput(attrs={'size': '30'}), }




def ge2ge(request):
    from documentos.models import Ges_documental, Contrato_gauss
    obs = Ges_documental.objects.all()
    for o in obs:
        try:
            gen = GE.objects.get(gauser=o.propietario.gauser, entidad=o.propietario.entidad, ronda=o.propietario.ronda)
        except:
            gen = None
        o.propietario2 = gen
        o.save()
    obs = Contrato_gauss.objects.all()
    for o in obs:
        try:
            gen = GE.objects.get(gauser=o.firma_gauss.gauser, entidad=o.firma_gauss.entidad, ronda=o.firma_gauss.ronda)
        except:
            gen = None
        o.firma_gauss2 = gen
        try:
            gen = GE.objects.get(gauser=o.firma_entidad.gauser, entidad=o.firma_entidad.entidad, ronda=o.firma_entidad.ronda)
        except:
            gen = None
        o.firma_entidad2 = gen
        o.save()

    # from  horarios.models import *
    # for falta in Falta_asistencia.objects.all():

#     # GE.objects.all().delete()
#     ges = Gauser_extra.objects.all()
#     for ge in ges:
#         nuevo_ge = GE.objects.create(gauser=ge.gauser, entidad=ge.ronda.entidad, ronda=ge.ronda,
#                                      id_organizacion=ge.id_organizacion, id_entidad=ge.id_entidad,
#                                      alias=ge.alias, activo=ge.activo, observaciones=ge.observaciones,
#                                      foto=ge.foto, ocupacion=ge.ocupacion,
#                                      banco=ge.banco, entidad_bancaria=ge.ronda.entidad_bancaria,
#                                      num_cuenta_bancaria=ge.num_cuenta_bancaria)
#         nuevo_ge.subentidades.add(*ge.subentidades.all())
#         nuevo_ge.subsubentidades.add(*ge.subsubentidades.all())
#         nuevo_ge.cargos.add(*ge.cargos.all())
#         nuevo_ge.permisos.add(*ge.permisos.all())
#     for ge in ges:
#         nuevo_ge = GE.objects.get(gauser=ge.gauser, entidad=ge.ronda.entidad, ronda=ge.ronda)
#         try:
#             tutor1 = GE.objects.get(gauser=ge.tutor1.gauser, entidad=ge.ronda.entidad, ronda=ge.ronda)
#         except:
#             tutor1 = None
#         try:
#             tutor2 = GE.objects.get(gauser=ge.tutor2.gauser, entidad=ge.ronda.entidad, ronda=ge.ronda)
#         except:
#             tutor2 = None
#         nuevo_ge.tutor1 = tutor1
#         nuevo_ge.tutor2 = tutor2
#         for h in ge.hermanos.all():
#             nuevo_ge.hermanos.add(GE.objects.get(gauser=h.gauser, entidad=ge.ronda.entidad, ronda=ge.ronda))
#         nuevo_ge.save()
