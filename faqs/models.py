from django.db import models
from entidades.models import Menu, Entidad


# Create your models here.


class FaqGauss(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, null=True, blank=True)
    pregunta = models.CharField('Pregunta', max_length=300, null=True, blank=True, default='')
    respuesta = models.TextField('Respuesta', blank=True, null=True, default='')

    class Meta:
        ordering = ['menu']

    def __str__(self):
        return '%s' % (self.pregunta)


class FaqSection(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre de la sección', max_length=150, null=True, blank=True, default='')

    class Meta:
        ordering = ['entidad']

    def __str__(self):
        return '%s -- %s' % (self.entidad.name, self.nombre)


class FaqEntidad(models.Model):
    faqsection = models.ForeignKey(FaqSection, on_delete=models.CASCADE)
    pregunta = models.CharField('Pregunta', max_length=200, null=True, blank=True, default='')
    respuesta = models.TextField('Respuesta', blank=True, null=True, default='')

    class Meta:
        ordering = ['faqsection']

    def __str__(self):
        return '%s -- %s' % (self.faqsection.entidad.name, self.pregunta)
