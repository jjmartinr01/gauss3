# -*- coding: utf-8 -*-
from django.contrib import admin
from tutorados.models import Informe_seguimiento, Pregunta, Respuesta, Informe_tareas, Fichero_tarea, Tarea_propuesta


admin.site.register(Informe_seguimiento)
admin.site.register(Pregunta)
admin.site.register(Respuesta)
admin.site.register(Informe_tareas)
admin.site.register(Tarea_propuesta)
admin.site.register(Fichero_tarea)
