# -*- coding: utf-8 -*-

from django.forms import ModelForm, ModelMultipleChoiceField, ModelChoiceField, TextInput, DateField

# from entidades.models import Subentidad, Entidad
# from autenticar.models import Gauser_extra, Gauser
from entidades.models import Subentidad, Entidad, Gauser_extra
from autenticar.models import Gauser

from gauss import settings


class EntidadForm(ModelForm):
    class Meta:
        model = Entidad
        exclude = ('organization', 'code', 'name', 'banco', 'anagrama', 'general_name', 'general_user')
        # widgets = {'iban': TextInput(attrs={'size': '30'}),
        #            'address': TextInput(attrs={'size': '30'}), }



class Gauser_mis_datos_Form(ModelForm):
    nacimiento = DateField(input_formats=('%d/%m/%Y', '%d \d\e %B \d\e %Y',))
    class Meta:
        model = Gauser
        fields = ('username', 'first_name', 'last_name', 'email', 'sexo', 'dni', 'address', 'postalcode', 'localidad',
                  'provincia', 'nacimiento', 'telfij', 'telmov')


class Gauser_extra_mis_datos_Form(ModelForm):
    class Meta:
        model = Gauser_extra
        fields = ('foto',)


class GauserForm(ModelForm):
    # nacimiento = DateField(input_formats=settings.DATE_INPUT_FORMATS)
    class Meta:
        model = Gauser
        fields = ('username', 'first_name', 'last_name', 'email', 'sexo', 'dni', 'address', 'postalcode', 'localidad',
                  'provincia', 'nacimiento', 'telfij', 'telmov', 'familia')


class Gauser_extraForm(ModelForm):
    class Meta:
        model = Gauser_extra
        fields = (
            'activo', 'observaciones', 'foto', 'id_organizacion', 'num_cuenta_bancaria', 'ocupacion',
            'tutor1', 'tutor2', 'cargos','subentidades', 'id_entidad')


class Padre_extraForm(ModelForm):
    class Meta:
        model = Gauser_extra
        fields = ('activo', 'observaciones', 'foto', 'ocupacion', 'num_cuenta_bancaria')


class SocioAdulto_extraForm(ModelForm):
    class Meta:
        model = Gauser_extra
        fields = (
            'activo', 'observaciones', 'foto', 'id_organizacion', 'num_cuenta_bancaria', 'ocupacion')


class Voluntario_extraForm(ModelForm):
    class Meta:
        model = Gauser_extra
        fields = (
            'activo', 'observaciones', 'foto', 'id_organizacion', 'num_cuenta_bancaria', 'ocupacion')


class Educando_extraForm(ModelForm):
    class Meta:
        model = Gauser_extra
        fields = (
            'activo', 'observaciones', 'foto', 'id_organizacion', 'num_cuenta_bancaria', 'tutor1', 'tutor2')