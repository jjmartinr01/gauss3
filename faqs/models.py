from django.db import models
from entidades.models import Menu, Entidad
from autenticar.models import Permiso, Gauser


# Create your models here.


class FaqGauss(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, null=True, blank=True)
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE, null=True, blank=True)
    pregunta = models.CharField('Pregunta', max_length=300, null=True, blank=True, default='')
    respuesta = models.TextField('Respuesta', blank=True, null=True, default='')

    class Meta:
        ordering = ['menu']

    def __str__(self):
        return '%s' % (self.pregunta)


class FaqSection(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre de la sección', max_length=150, null=True, blank=True, default='')
    borrada = models.BooleanField('Está borrada?', default=False)
    modificada = models.DateField('Última fecha de modificación', auto_now=True)

    @property
    def num_preguntas(self):
        return FaqEntidad.objects.filter(faqsection=self, borrada=False).count()

    @property
    def num_preguntas_pub(self):
        return FaqEntidad.objects.filter(faqsection=self, publicada=True, borrada=False).count()

    @property
    def num_preguntas_borradas(self):
        return FaqEntidad.objects.filter(faqsection=self, borrada=True).count()

    class Meta:
        ordering = ['entidad']

    def __str__(self):
        return '%s -- %s (borrada: %s)' % (self.entidad.name, self.nombre, self.borrada)


class FaqEntidad(models.Model):
    faqsection = models.ForeignKey(FaqSection, on_delete=models.CASCADE)
    pregunta = models.CharField('Pregunta', max_length=200, null=True, blank=True, default='')
    respuesta = models.TextField('Respuesta', blank=True, null=True, default='')
    publicada = models.BooleanField('Está publicada?', default=False)
    borrada = models.BooleanField('Está borrada?', default=False)
    modificada = models.DateField('Última fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['faqsection', 'id']

    def __str__(self):
        return '%s -- %s (borrada: %s)' % (self.faqsection.entidad.name, self.pregunta, self.borrada)


class FaqSugerida(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    gauser = models.ForeignKey(Gauser, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    texto = models.TextField('Respuesta', blank=True, null=True, default='')
    aceptada = models.BooleanField('Está aceptada?', default=False)
    modificada = models.DateField('Última fecha de modificación', auto_now=True)

    @property
    def hijos(self):
        return FaqSugerida.objects.filter(parent=self)

    @property
    def nivel(self):
        if not self.parent:
            return 0
        else:
            return 1 + self.parent.nivel

    @property
    def rpadding(self):
        return 10*self.nivel

    class Meta:
        ordering = ['entidad', 'id']

    def __str__(self):
        return '%s -- %s (aceptada: %s)' % (self.texto[:30], self.entidad.name, self.aceptada)
