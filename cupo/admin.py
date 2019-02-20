# -*- coding: utf-8 -*-
from django.contrib import admin
from cupo.models import Cupo,  Profesores_cupo, EspecialidadCupo, Materia_cupo, Profesor_cupo


admin.site.register(Cupo)
admin.site.register(Materia_cupo)
admin.site.register(Profesores_cupo)
admin.site.register(EspecialidadCupo)
admin.site.register(Profesor_cupo)
