from django.contrib import admin
from horarios.models import Horario, Actividad, Tramo_horario, Sesion, Falta_asistencia, CargaMasiva
# Register your models here.

class SubentidadAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    list_filter = ['entidad', 'entidad__ronda']

admin.site.register(Horario)
admin.site.register(Actividad)
admin.site.register(Tramo_horario)
admin.site.register(Sesion)
admin.site.register(Falta_asistencia)
admin.site.register(CargaMasiva)
