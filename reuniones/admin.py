# -*- coding: utf-8 -*-
from django.contrib import admin
from reuniones.models import ConvReunion, PuntoConvReunion, ActaReunion, FirmaActa


admin.site.register(ConvReunion)
admin.site.register(PuntoConvReunion)
admin.site.register(ActaReunion)
admin.site.register(FirmaActa)