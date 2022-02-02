from django.db import models
from autenticar.models import Gauser
from entidades.models import Entidad

# Create your models here.

class Procedimiento(models.Model):
    nombre = models.CharField('Nombre del procedimiento', max_length=300)
    # Persona que crea el procedimiento
    creador = models.ForeignKey(Gauser, on_delete=models.SET_NULL, blank=True, null=True)
    # Entidad a la que pertence el procedimiento -- entidad del creador
    entidad = models.ForeignKey(Entidad, on_delete=models.SET_NULL, blank=True, null=True)
    # Entidades que pueden hacer uso del procedimiento
    destinatarios = models.ManyToManyField(Entidad, blank=True)
    inicio = models.DateField('Fecha de inicio del procedimiento', blank=True)
    fin = models.DateField('Fecha de finalización del procedimiento', blank=True)
    plantilla = models.BooleanField('¿Es una plantilla de procedimientos?', default=False)

    class Meta:
        verbose_name_plural = "Procedimientos"

    def __str__(self):
        if self.plantilla:
            return 'Plantilla: %s' % (self.nombre)
        else:
            return '%s (%s -- %s)' % (self.nombre, self.inicio, self.fin)

class NormaProcedimiento(models.Model):
    proc = models.ForeignKey(Procedimiento, on_delete=models.CASCADE)
    norma = models.TextField('Nombre de la norma')
    texto = models.TextField('Contenido de la norma', blank=True)

    class Meta:
        verbose_name_plural = "Normas de Procedimientos"

    def __str__(self):
        return '%s -- %s' % (self.norma[:300], self.proc.nombre[:300])

class FaseProcedimiento(models.Model):
    CONS = ((' > ', 'Valoración en la fase anterior mayor que ...'),
            (' >= ', 'Valoración en la fase anterior igual o mayor que ...'),
            (' < ', 'Valoración en la fase anterior menor que ...'),
            (' <= ', 'Valoración en la fase anterior igual o menor que ...'),
            (' == ', 'Valoración en la fase anterior igual a ...'))
    proc = models.ForeignKey(Procedimiento, on_delete=models.CASCADE)
    fproc_anterior = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    nombre = models.CharField('Nombre de la fase del procedimiento', max_length=300)
    inicio = models.DateField('Fecha de inicio de la fase del procedimiento', blank=True)
    fin = models.DateField('Fecha de finalización de la fase del procedimiento', blank=True)
    finalizada = models.BooleanField('¿Esta fase ha finalizado?', default=False)
    # Parámetros para comprobar cumplimiento de la condición anterior
    cumplir_condicion = models.BooleanField('¿Iniciar esta fase al cumplir condición de fproc_anterior', default=False)
    operador_condicion = models.CharField('Operador de la condición', choices=CONS, max_length=5, default=' > ')
    valor_condicion = models.FloatField('Valor a cumplir en la condición', blank=True, default=0)

    # La condición para llegar a esta fase la debe cumplir la fase anterior:
    @property
    def condicion(self):
        if self.cumplir_condicion:
            try:
                return eval(str(self.fproc_anterior.valoracion) + self.operador_condicion + str(self.valor_condicion))
            except:
                return False
        else:
            return True


    @property
    def valoracion(self):
        val = 0
        peso = 0
        for v in self.resultadofaseprocedimiento_set.all():
            val += v.valoracion * v.peso_valoracion
            peso += v.peso_valoracion
        try:
            return val/peso
        except:
            return 0

    class Meta:
        verbose_name_plural = "Fases Procedimientos"

    def __str__(self):
        return '%s (Fase anterior: %s)' % (self.nombre[:300], self.fproc_anterior)

class ResultadoFaseProcedimiento(models.Model):
    fproc = models.ForeignKey(FaseProcedimiento, on_delete=models.CASCADE,blank=True, null=True)
    nombre = models.CharField('Nombre del resultado de la fase del procedimiento', max_length=300)
    texto = models.TextField('Texto/Documento generado en esta fase', blank=True)
    valoracion = models.FloatField('Valoración numérica de este resultado', default=-1000)
    peso_valoracion = models.FloatField('Peso de la valoración numérica de este resultado', default=0)

    class Meta:
        verbose_name_plural = "Resultados Fases Procedimientos"

    def __str__(self):
        return '%s (Valoración: %s)' % (self.nombre[:300], self.valoracion)