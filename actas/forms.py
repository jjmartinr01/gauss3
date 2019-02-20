# -*- coding: utf-8 -*-
import datetime
from django.db.models import Q
from django.forms import ModelForm, ModelMultipleChoiceField, CheckboxSelectMultiple, TextInput, ModelChoiceField, \
    DateField, Textarea

from actas.models import Convocatoria, Acta
from entidades.models import Subentidad
from gauss import settings


class MiModelMultipleChoiceField(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return "%s" % obj.nombre


class MiModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return u'%s' % (obj.nombre)


class ActaForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.g_e = kwargs.pop('g_e')
        super(ActaForm, self).__init__(*args, **kwargs)
        conv_usadas = Acta.objects.filter(convocatoria__convocante__entidad=self.g_e.ronda.entidad,
                                          fecha_aprobacion__gt=datetime.date.min).values_list('convocatoria__id')
        convocatorias = Convocatoria.objects.filter(Q(convocante__entidad=self.g_e.ronda.entidad) & ~Q(id__in=conv_usadas))
        self.fields['convocatoria'] = MiModelChoiceField(queryset=convocatorias)

    class Meta:
        model = Acta
        fields = ('convocatoria', 'contenido_html', 'fecha_aprobacion')


class Acta_subirForm(ModelForm):
    class Meta:
        model = Acta
        fields = ('pdf_escaneado', 'fecha_aprobacion',)


class ConvocatoriaForm(ModelForm):
    class Meta:
        model = Convocatoria
        fields = ('nombre', 'fecha_hora', 'texto_convocatoria', 'convocados')
        widgets = {'nombre': TextInput(attrs={'size': 80, }),
                   'fecha_hora': TextInput(attrs={'size': 18, }),
                   'texto_convocatoria': Textarea(attrs={'cols': 80, })}