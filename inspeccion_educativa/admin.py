from django import forms
from django.contrib import admin
from inspeccion_educativa.models import *

class CentroMDBAdmin(admin.ModelAdmin):
    search_fields = ['nombre', 'code']
    list_filter = ['code', 'localidad']

class TareaInspeccionAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['creador'].queryset = Gauser_extra.objects.filter(ronda=self.instance.creador.ronda)
class TareaInspeccionAdmin(admin.ModelAdmin):
    form = TareaInspeccionAdminForm

# Register your models here.
admin.site.register(TareaInspeccion, TareaInspeccionAdmin)
admin.site.register(InspectorTarea)
admin.site.register(CentroMDB, CentroMDBAdmin)
admin.site.register(PlantillaInformeInspeccion)
admin.site.register(VariantePII)
admin.site.register(InformeInspeccion)
admin.site.register(VariableII)
