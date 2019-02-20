# -*- coding: utf-8 -*-
from django.contrib import admin
from entidades.models import *



class Gauser_extraAdmin(admin.ModelAdmin):
    search_fields = ['gauser__last_name']
    list_filter = ['entidad', 'ronda']


class SubentidadAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    list_filter = ['entidad', 'entidad__ronda']

class CargoAdmin(admin.ModelAdmin):
    search_fields = ['cargo']
    list_filter = ['entidad', 'entidad__ronda']

class DependenciaAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    list_filter = ['entidad', 'entidad__ronda']

class Menu_Admin(admin.ModelAdmin):
    list_filter = ['entidad']


admin.site.register(Organization)
admin.site.register(Entidad)
admin.site.register(Menu, Menu_Admin)
admin.site.register(Gauser_extra, Gauser_extraAdmin)
admin.site.register(Subentidad, SubentidadAdmin)
admin.site.register(Subsubentidad)
admin.site.register(Alta_Baja)
admin.site.register(Cargo, CargoAdmin)
admin.site.register(Dependencia, DependenciaAdmin)
admin.site.register(Ronda)
admin.site.register(ConfiguraReservaPlaza)
admin.site.register(Reserva_plaza)
admin.site.register(ConfigurationUpdate)