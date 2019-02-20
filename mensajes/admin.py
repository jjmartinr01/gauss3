# -*- coding: utf-8 -*-
from django.contrib import admin
from mensajes.models import Mensaje, Aviso, Adjunto, Borrado, Importante, Leido, Mensaje_cola, Etiqueta

class Aviso_extraAdmin(admin.ModelAdmin):
    search_fields = ['usuario__gauser__last_name']
    list_filter = ['usuario__entidad', 'usuario__ronda']

admin.site.register(Mensaje)
admin.site.register(Mensaje_cola)
admin.site.register(Adjunto)
admin.site.register(Etiqueta)
admin.site.register(Borrado)
admin.site.register(Importante)
admin.site.register(Leido)
admin.site.register(Aviso, Aviso_extraAdmin)