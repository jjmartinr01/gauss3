# -*- coding: utf-8 -*-
from django.contrib import admin
from documentos.models import *

class Docs_Admin(admin.ModelAdmin):
    list_filter = ['propietario__ronda__entidad']

class Etiqueta_Admin(admin.ModelAdmin):
    list_filter = ['entidad']


admin.site.register(Ges_documental, Docs_Admin)
admin.site.register(Compartir_Ges_documental)
admin.site.register(Contrato_gauss)
admin.site.register(Etiqueta_documental, Etiqueta_Admin)
admin.site.register(Normativa)
admin.site.register(NormativaEtiqueta)