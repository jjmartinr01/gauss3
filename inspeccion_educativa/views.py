# -*- coding: utf-8 -*-
import logging
import xlwt
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.utils import timezone, translation
from django.utils.timezone import localdate, timedelta
from django.template import RequestContext
from django.db.models import Q
from django.forms import ModelForm, ModelChoiceField, URLField, Form
from django.core.paginator import Paginator
import sys
from django.core import serializers

from gauss.constantes import CODE_CONTENEDOR
from autenticar.control_acceso import LogGauss, permiso_required, gauss_required
from inspeccion_educativa.models import CentroMDB, TareaInspeccion, InspectorTarea
from autenticar.views import crear_nombre_usuario
from mensajes.views import encolar_mensaje, crea_mensaje_cola

logger = logging.getLogger('django')

@gauss_required
def cargar_centros_mdb(request):
    from inspeccion_educativa.models import CENTROS
    # ("742", "C.R.A. ENTREVALLES", "C.R.A.", "BADARÁN")
    for centro in CENTROS:
        CentroMDB.objects.get_or_create(code_mdb=centro[0], tipo=centro[2], nombre=centro[1], localidad=centro[3])
    return HttpResponse('CentrosMDB creados')

@permiso_required('acceso_miembros_entidad')
def tareas_ie(request):
    g_e = request.session["gauser_extra"]
    fecha_min = localdate() - timedelta(2)
    fecha_max = localdate() + timedelta(7)
    tareas = InspectorTarea.objects.filter(inspector=g_e, tarea__realizada=False, tarea__fecha__gte=fecha_min, tarea__fecha__lte=fecha_max)
    logger.info('Entra en ' + request.META['PATH_INFO'] + ' no POST')
    if 'ge' in request.GET:
        pass
    return render(request, "tareas_ie.html", {'g_e':g_e, 'tareas':tareas})
