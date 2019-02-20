from django.contrib import admin
from estudios.models import *

# Register your models here.

class CursoAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    list_filter = ['ronda']

class GrupoAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    list_filter = ['ronda__entidad', 'ronda']

class MateriaAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    list_filter = ['curso__ronda__entidad', 'curso__ronda']

class Gauser_extra_estudiosAdmin(admin.ModelAdmin):
    search_fields = ['ge__gauser__last_name']
    list_filter = ['ge__ronda__entidad', 'ge__ronda']

admin.site.register(Curso, CursoAdmin)
admin.site.register(Grupo, GrupoAdmin)
admin.site.register(Materia, MateriaAdmin)
admin.site.register(Gauser_extra_estudios, Gauser_extra_estudiosAdmin)
admin.site.register(Matricula)