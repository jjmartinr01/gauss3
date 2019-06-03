# -*- coding: utf-8 -*-
from django.contrib import admin
from reuniones.models import ConvReunion, PuntoConvReunion, ActaReunion


admin.site.register(ConvReunion)
admin.site.register(PuntoConvReunion)
admin.site.register(ActaReunion)