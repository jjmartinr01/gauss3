from django.contrib import admin
from vut.models import *
# Register your models here.

class ReservaAdmin(admin.ModelAdmin):
    search_fields = ['vivienda__nombre', 'vivienda__gpropietario__first_name', 'entrada']
    # list_filter = ['vivienda',]

class ViviendaAdmin(admin.ModelAdmin):
    search_fields = ['nombre', 'gpropietario__first_name']
    # list_filter = ['gpropietario__first_name']

# class VpropietarioAdmin(admin.ModelAdmin):
#     search_fields = ['vivienda__nombre', 'propietario__first_name', 'entrada']
    # list_filter = ['vivienda',]

admin.site.register(Vivienda, ViviendaAdmin)
admin.site.register(Ayudante)
admin.site.register(Reserva, ReservaAdmin)
admin.site.register(Viajero)
admin.site.register(PagoAyudante)
admin.site.register(RegistroPolicia)
admin.site.register(Autorizado)
admin.site.register(ContabilidadVUT)
admin.site.register(AutorizadoContabilidadVut)
admin.site.register(PartidaVUT)
admin.site.register(AsientoVUT)
admin.site.register(FotoWebVivienda)
admin.site.register(DayWebVivienda)
# admin.site.register(Vpropietario, VpropietarioAdmin)
