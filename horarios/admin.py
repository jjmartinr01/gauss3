from django.contrib import admin
from horarios.models import Horario, Actividad, Tramo_horario, Sesion, Falta_asistencia, CargaMasiva, Guardia
# Register your models here.

class HorarioAdmin(admin.ModelAdmin):
    search_fields = ['ronda__entidad']
    list_filter = ['predeterminado', 'ronda']

class GuardiaAdmin(admin.ModelAdmin):
    search_fields = ['sesion__horario__ronda__entidad']
    list_filter = ['sesion__horario__predeterminado', 'sesion__horario__ronda']

admin.site.register(Horario, HorarioAdmin)
admin.site.register(Actividad)
admin.site.register(Tramo_horario)
admin.site.register(Sesion)
admin.site.register(Falta_asistencia)
admin.site.register(CargaMasiva)
admin.site.register(Guardia, GuardiaAdmin)
