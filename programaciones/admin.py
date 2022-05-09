# -*- coding: utf-8 -*-
from django.contrib import admin
from programaciones.models import *


admin.site.register(Titulo_FP)
admin.site.register(Programacion_modulo)
admin.site.register(Obj_general)
admin.site.register(UD_modulo)
admin.site.register(Cont_unidad_modulo)
admin.site.register(Especialidad_funcionario)
admin.site.register(Cuerpo_funcionario)
admin.site.register(Departamento)
admin.site.register(Materia_programaciones)
admin.site.register(Resultado_aprendizaje)
admin.site.register(Objetivo)
admin.site.register(Especialidad_entidad)
admin.site.register(Gauser_extra_programaciones)
admin.site.register(ProgramacionSubida)
############################################################
############### Programaciones Secundaria ##################
############################################################
admin.site.register(ProgSec)
admin.site.register(CEProgSec)
admin.site.register(CEvProgSec)
admin.site.register(LibroRecurso)
admin.site.register(ActExCom)
admin.site.register(SaberBas)
admin.site.register(SitApren)
admin.site.register(ActSitApren)
admin.site.register(InstrEval)
admin.site.register(CriInstrEval)
admin.site.register(CuadernoProf)
admin.site.register(EscalaCP)
admin.site.register(EscalaCPvalor)
admin.site.register(CalAlum)
admin.site.register(CalAlumValor)
############################################################
admin.site.register(RepoSitApren)
admin.site.register(RepoCEv)
admin.site.register(RepoSitAprenLike)
admin.site.register(RepoActSitApren)
admin.site.register(RepoInstrEval)
admin.site.register(RepoCriInstrEval)
############################################################
############################################################

