# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re
from django.db import models
from django.db.models import Q
from django.utils import timezone
from autenticar.models import Gauser
from entidades.models import Subentidad, Cargo, Entidad
from entidades.models import Gauser_extra as GE
from gauss.rutas import RUTA_MEDIA


def iniciales(s):  # Función para devolver las iniciales de una cadena
    s = s.split()
    iniciales = ''
    for e in s:
        if len(e) > 2: iniciales += e[0].upper()
    return iniciales


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_fichero(instance, filename):
    fichero = '%s/acta_%s.pdf' % (instance.convocatoria.entidad.code, instance.id)
    ruta = os.path.join("actas/", fichero)
    return ruta

def nextday2():
    return timezone.now() + timezone.timedelta(2)

class ConvReunion(models.Model):
    creador = models.ForeignKey(Gauser, blank=True, null=True, related_name='convcrea', on_delete=models.SET_NULL)
    convoca = models.ForeignKey(Gauser, blank=True, null=True, related_name='convconv', on_delete=models.SET_NULL)
    cargo_convocante = models.ForeignKey(Cargo, blank=True, null=True, on_delete=models.SET_NULL)
    convoca_text = models.CharField('Nombre del convocante (texto)', blank=True, null=True, max_length=100)
    cargo_convocante_text = models.CharField('Cargo del convocante (texto)', blank=True, null=True, max_length=100)
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Título de la convocatoria", max_length=300, blank=True, null=True)
    lugar = models.CharField('Lugar de la convocatoria', max_length=300, blank=True, null=True, default='')
    texto_convocatoria = models.TextField("Texto de la convocatoria", blank=True, null=True)
    convocados = models.ManyToManyField(Subentidad, blank=True)
    convocados_text = models.TextField('Convocados en formato texto', null=True, blank=True)
    fecha_hora = models.DateTimeField("Fecha y hora de la convocatoria", blank=True, null=True, default=nextday2)
    plantilla = models.BooleanField("Es una plantilla de convocatorias de reunión", default=False)
    basada_en = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='configura')
    fecha = models.DateField("Fecha emisión de la convocatoria", blank=True, null=True, default=timezone.now)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)
    educa_pk = models.IntegerField("pk de la convocatoria en gauss_educa", blank=True, null=True)

    def permiso(self, g_e, p):
        q1 = Q(cargo__in=g_e.cargos.all()) | Q(gauser=g_e.gauser)
        q2 = Q(plantilla=self) | Q(plantilla=self.basada_en)
        q3 = eval('Q(%s=True)' % p)
        return PermisoReunion.objects.filter(q1, q2, q3).count() > 0 or self.creador == g_e.gauser

    class Meta:
        ordering = ['-fecha_hora']

    def __str__(self):
        try:
            return '%s (%s) -- %s' % (self.nombre, self.fecha_hora, self.entidad)
        except:
            return '%s (%s)' % (self.nombre, self.fecha_hora)


class PuntoConvReunion(models.Model):
    convocatoria = models.ForeignKey(ConvReunion, blank=True, null=True, related_name='punto',
                                     on_delete=models.CASCADE)
    punto = models.TextField("Texto punto de la convocatoria", blank=True, null=True)
    orden = models.IntegerField('Orden dentro de la convocatoria', blank=True, null=True, default=0)
    texto_acta = models.TextField("Aspectos tratados en la reunión de la convocatoria", blank=True, null=True)

    class Meta:
        ordering = ['convocatoria', 'orden']

    def __str__(self):
        return '%s (%s)' % (self.convocatoria, self.punto[:100])


class ActaReunion(models.Model):
    convocatoria = models.ForeignKey(ConvReunion, blank=True, null=True, on_delete=models.CASCADE)
    redacta = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.SET_NULL)
    nombre = models.CharField("Título del acta", max_length=300, blank=True, null=True)
    preambulo = models.TextField("Preámbulo del acta", blank=True, null=True)
    epilogo = models.TextField("Epílogo del acta", blank=True, null=True)
    pdf = models.FileField("Fichero generado", upload_to=update_fichero, blank=True, null=True)
    pdf_escaneado = models.FileField("Subir el fichero escaneado", upload_to=update_fichero, blank=True, null=True)
    publicada = models.BooleanField("Publicar para lectura antes de aprobar", default=False)
    fecha_aprobacion = models.DateField("Fecha en la que se aprobó el acta", null=True, blank=True)
    asistentes = models.ManyToManyField(GE, blank=True, related_name='asisten')
    asistentes_text = models.TextField('Asistentes en formato texto', null=True, blank=True)
    num_last_page = models.IntegerField('Número de la última página', blank=True, null=True)
    control = models.IntegerField('Código numérico para el control de asistencia', default=0)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    def is_redactada_por(self, g_e):
        q1 = g_e.gauser.username == 'gauss'
        q2 = g_e.has_permiso('w_cualquier_acta_reunion')
        q3 = self.convocatoria.creador == g_e.gauser
        q4 = self.redacta == g_e.gauser
        q5 = self.convocatoria.permiso(g_e, 'puede_redactar')
        if q1 or q2 or q3 or q4 or q5:
            return True
        elif g_e.has_permiso('w_actas_subentidades_reunion'):
            subentidades_convocadas = self.convocatoria.convocados.all()
            for sub in g_e.subentidades.all():
                if sub in subentidades_convocadas:
                    return True
        else:
            return False

    @property
    def firmada(self):
        num_firmas_requeridas = self.firmaacta_set.all().count()
        if num_firmas_requeridas > 0:
            if self.firmaacta_set.filter(firmada=True).count() == num_firmas_requeridas:
                return True
            else:
                return False
        else:
            return False

    @property
    def num_firmantes(self):
        return self.firmaacta_set.filter(firmada=True).count(), self.firmaacta_set.all().count()

    @property
    def onlyread(self):
        if self.publicada or self.fecha_aprobacion:
            return True
        else:
            return False

    @property
    def acta_anterior(self):
        if self.convocatoria.basada_en:
            convocatorias_anteriores = ConvReunion.objects.filter(fecha_hora__lt=self.convocatoria.fecha_hora,
                                                                  basada_en=self.convocatoria.basada_en)
            if convocatorias_anteriores.count() > 0:
                convocatoria_anterior = convocatorias_anteriores[0]
                return ActaReunion.objects.get(convocatoria=convocatoria_anterior)
            else:
                return None
        else:
            return None

    @property
    def num_last_page_acta_anterior(self):
        if self.acta_anterior:
            return self.acta_anterior.num_last_page
        else:
            return 0

    @property
    def num_pages(self):
        # http://code.activestate.com/recipes/496837-count-pdf-pages/
        rxcountpages = re.compile(r"/Type\s*/Page([^s]|$)", re.MULTILINE | re.DOTALL)
        data = self.pdf.read()
        return len(rxcountpages.findall(data))

    class Meta:
        ordering = ['-convocatoria__fecha_hora']

    def __str__(self):
        try:
            return 'Acta de la convocatoria de %s (%s) - %s' % (
                self.convocatoria.nombre, self.convocatoria.fecha_hora, self.convocatoria.convocante.entidad.name)
        except:
            return 'Acta de la convocatoria de %s (%s)' % (
                self.convocatoria.nombre, self.convocatoria.fecha_hora)


def update_firma(instance, filename):
    a = instance.acta
    ruta = os.path.join("reuniones/%s/%s/firmas/" % (a.convocatoria.entidad.code, a.id),
                        str(a.id) + '_' + str(instance.ge.id) + '.png')
    return ruta


class FirmaActa(models.Model):
    TIPOS = (('FIR', 'Firma'), ('VB', 'Visto bueno'))
    acta = models.ForeignKey(ActaReunion, blank=True, null=True, on_delete=models.CASCADE)
    ge = models.ForeignKey(GE, blank=True, null=True, on_delete=models.SET_NULL)
    tipo = models.CharField('Tipo de firma', max_length=5, choices=TIPOS, default='FIR')
    texto_firmado = models.TextField('Contenido del acta en el momento de la firma', default='')
    firmante = models.CharField('Nombre del firmante', blank=True, null=True, max_length=100)
    cargo = models.CharField('Cargo del firmante', blank=True, null=True, max_length=100)
    firma = models.ImageField('Imagen de la firma', upload_to=update_firma, blank=True, null=True)
    firmada = models.BooleanField('¿Está firmada?', default=False)

    @property
    def modificada(self):
        return (not self.firmada) and (len(self.texto_firmado) > 0)

    class Meta:
        ordering = ['acta']

    def __str__(self):
        return '%s (%s)' % (self.acta, self.firmante)


class AcuerdoActa(models.Model):
    acta = models.ForeignKey(ActaReunion, blank=True, null=True, on_delete=models.CASCADE)
    acuerdo = models.TextField("Acuerdo", blank=True, null=True)

    class Meta:
        ordering = ['acta']

    def __str__(self):
        return '%s (%s)' % (self.acta, self.acuerdo)

class PermisoReunion(models.Model):
    plantilla = models.ForeignKey(ConvReunion, blank=True, null=True, on_delete=models.CASCADE)
    gauser = models.ForeignKey(Gauser, on_delete=models.CASCADE, null=True, blank=True)
    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE, blank=True, null=True)
    edita_plantilla = models.BooleanField('Puede editar la plantilla', default=False)
    puede_convocar = models.BooleanField('Puede hacer convocatorias basadas en la plantilla', default=False)
    puede_redactar = models.BooleanField('Puede redactar actas basadas en la plantilla', default=False)

    def __str__(self):
        return '%s - (%s) edita: %s, convoca: %s, redacta: %s' % (self.plantilla, self.gauser.get_full_name(),
                                                                  self.edita_plantilla, self.puede_convocar,
                                                                  self.puede_redactar)