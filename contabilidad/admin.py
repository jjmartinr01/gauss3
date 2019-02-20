# -*- coding: utf-8 -*-
from django.contrib import admin
from contabilidad.models import Presupuesto, Partida, Asiento, Politica_cuotas, Remesa, File_contabilidad, Remesa_emitida


admin.site.register(Presupuesto)
admin.site.register(Partida)
admin.site.register(Asiento)
admin.site.register(File_contabilidad)
admin.site.register(Politica_cuotas)
admin.site.register(Remesa)
admin.site.register(Remesa_emitida)
