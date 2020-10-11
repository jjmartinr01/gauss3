from django.contrib import admin
from inspeccion_educativa.models import *

class CentroMDBAdmin(admin.ModelAdmin):
    search_fields = ['nombre', 'code']
    list_filter = ['code', 'localidad']

# Register your models here.
admin.site.register(TareaInspeccion)
admin.site.register(InspectorTarea)
admin.site.register(CentroMDB, CentroMDBAdmin)
admin.site.register(PlantillaInformeInspeccion)
admin.site.register(VariantePII)
admin.site.register(InformeInspeccion)
admin.site.register(VariableII)
