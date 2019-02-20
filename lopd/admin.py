# -*- coding: utf-8 -*-
from django.contrib import admin
from lopd.models import Estructura_lopd, Incidencia_lopd, Fichero_incidencia


admin.site.register(Estructura_lopd)
admin.site.register(Incidencia_lopd)
admin.site.register(Fichero_incidencia)