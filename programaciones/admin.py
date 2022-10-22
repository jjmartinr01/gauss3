# -*- coding: utf-8 -*-
from django.contrib import admin
from django.db.models import Q
from django import forms

from entidades.models import Cargo
from programaciones.models import *


class ProgSecAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pga'].queryset = PGA.objects.filter(ronda__entidad=self.instance.gep.ge.ronda.entidad)
        self.fields['materia'].queryset = Materia_programaciones.objects.none()
        self.fields['curso'].queryset = Curso.objects.none()
        try:
            cargo_docente = Cargo.objects.filter(clave_cargo='g_docente', entidad=self.instance.gep.ge.ronda.entidad)
            self.fields['gep'].queryset = Gauser_extra_programaciones.objects.filter(ge__ronda=self.instance.gep.ge.ronda, cargos__in=cargo_docente)
        except:
            self.fields['gep'].queryset = Gauser_extra_programaciones.objects.none()
class ProgSecAdmin(admin.ModelAdmin):
    form = ProgSecAdminForm


class CuadernoProfAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['alumnos'].queryset = self.instance.alumnos.all()
        self.fields['psec'].queryset = ProgSec.objects.filter(gep__ge__ronda=self.instance.ge.ronda)
        self.fields['grupo'].queryset = Grupo.objects.filter(ronda=self.instance.ge.ronda)
        try:
            q = Q(clave_cargo='g_docente') | Q(clave_cargo='g_inspector_educacion')
            cargo_docente = Cargo.objects.filter(Q(entidad=self.instance.ge.ronda.entidad), q)
            self.fields['ge'].queryset = Gauser_extra.objects.filter(ronda=self.instance.psec.pga.ronda, cargos__in=cargo_docente)
        except:
            try:
                self.fields['ge'].queryset = Gauser_extra.objects.filter(ronda=self.instance.psec.pga.ronda)
            except:
                self.fields['ge'].queryset = Gauser_extra.objects.none()
class CuadernoProfAdmin(admin.ModelAdmin):
    form = CuadernoProfAdminForm
    search_fields = ['ge__ronda__entidad__name']
    # list_filter = ['entidad', 'ronda']


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
admin.site.register(ProgSec, ProgSecAdmin)
admin.site.register(CEProgSec)
admin.site.register(CEvProgSec)
admin.site.register(LibroRecurso)
admin.site.register(ActExCom)
admin.site.register(SaberBas)
admin.site.register(SitApren)
admin.site.register(ActSitApren)
admin.site.register(InstrEval)
admin.site.register(CriInstrEval)
admin.site.register(CuadernoProf, CuadernoProfAdmin)
admin.site.register(CalAlumCE)
admin.site.register(CalAlumCEv)
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
admin.site.register(RepoEscalaCP)
admin.site.register(RepoEscalaCPvalor)
############################################################

