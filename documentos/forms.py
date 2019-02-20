# -*- coding: utf-8 -*-

from datetime import datetime
from django.forms import ModelForm, ModelMultipleChoiceField, ModelChoiceField, TextInput

from documentos.models import Ges_documental, Contrato_gauss, Etiqueta_documental
from entidades.models import Subentidad


class MiModelMultipleChoiceField(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return "%s" % obj.nombre


class MiModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return u'%s' % (obj.nombre)


class Ges_documentalForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.g_e = kwargs.pop('g_e')
        super(Ges_documentalForm, self).__init__(*args, **kwargs)
        acceden = Subentidad.objects.filter(entidad=self.g_e.ronda.entidad, fecha_expira__gt=datetime.today())
        etiqueta = Etiqueta_documental.objects.filter(entidad=self.g_e.ronda.entidad)
        self.fields['acceden'] = MiModelMultipleChoiceField(queryset=acceden)
        self.fields['etiqueta'] = MiModelChoiceField(queryset=etiqueta)

    class Meta:
        model = Ges_documental
        fields = ('nombre', 'key_words', 'acceden', 'texto', 'fichero', 'etiqueta')
        widgets = {'nombre': TextInput(attrs={'size': 60})}

class Contrato_gaussForm(ModelForm):
    class Meta:
        model = Contrato_gauss
        exclude = ('content_type',)
        # fields = ('fichero')