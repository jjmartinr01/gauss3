# -*- coding: utf-8 -*-
import os

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.db.models import Q

from entidades.models import Subentidad, Entidad, Cargo, DocConfEntidad
from entidades.models import Gauser_extra as GE
from autenticar.models import Gauser

from gauss.funciones import pass_generator
from gauss.rutas import RUTA_BASE


class Etiqueta_documental(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    nombre = models.CharField("Carpeta/Etiqueta", max_length=300, null=True, blank=True)
    padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    @property
    def hijos(self):
        lista = [self]
        try:
            for e in Etiqueta_documental.objects.filter(padre=self):
                lista = lista + e.hijos
            return lista
        except:
            return lista

    @property
    def etiquetas(self):
        lista = [self.nombre]
        try:
            lista = lista + self.padre.etiquetas
            return lista
        except:
            return lista

    @property
    def etiquetas_text(self):
        return '/'.join(reversed(self.etiquetas))

    class Meta:
        verbose_name_plural = "Etiquetas/Carpetas para los Documentos"

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.entidad.name)


def update_fichero_documental(instance, filename):
    nombre = filename.partition('.')
    instance.fich_name = filename.rpartition('/')[2].replace(' ', '_')
    nombre = pass_generator(size=20) + '.' + nombre[2]
    return '/'.join(['documentos', str(instance.propietario.ronda.entidad.code), nombre])


def update_fichero_contrato(instance, filename):
    nombre = filename.partition('.')
    nombre = 'Contrato_' + str(instance.entidad.id) + '.' + nombre[2]
    return '/'.join(['documentos', str(instance.entidad.code), nombre])


class Ges_documental(models.Model):
    propietario = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True, related_name='ge20')
    etiqueta = models.ForeignKey(Etiqueta_documental, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre del documento", max_length=240)
    acceden = models.ManyToManyField(Subentidad, blank=True)
    cargos = models.ManyToManyField(Cargo, blank=True)
    key_words = models.CharField("Palabras clave", max_length=250, blank=True, null=True)
    texto = models.TextField("Texto del documento o resumen", blank=True, null=True)
    fichero = models.FileField("Fichero con documento", upload_to=update_fichero_documental, blank=True, null=True)
    fich_name = models.CharField("Nombre del fichero", max_length=100, blank=True, null=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    borrado = models.BooleanField("Archivo borrado?", default=False)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    def permisos(self, g_e):
        q1 = Q(subentidad__in=g_e.subentidades.all()) | Q(cargo__in=g_e.cargos.all()) | Q(gauser=g_e.gauser)
        q2 = Q(documento=self)
        return ''.join(Compartir_Ges_documental.objects.filter(q1, q2).values_list('permiso', flat=True))

    class Meta:
        ordering = ['-creado']
        verbose_name_plural = "Documentos (Gestión Documental)"

    def __str__(self):
        return '%s (%s) - Borrado: %s' % (self.nombre, self.modificado, self.borrado)


@receiver(pre_delete, sender=Ges_documental)
def fichero_del_pre_delete(sender, **kwargs):
    try:
        archivo = RUTA_BASE + kwargs['instance'].fichero.url
        # archivo = kwargs['instance'].fichero.path
        if os.path.isfile(archivo):
            os.remove(archivo)
    except:
        pass


PERMISOS = (('r', 'lectura'),
            ('rw', 'lectura y escritura'),
            ('rwx', 'lectura, escritura y borrado'),)


class Compartir_Ges_documental(models.Model):
    documento = models.ForeignKey(Ges_documental, on_delete=models.CASCADE, null=True, blank=True)
    subentidad = models.ForeignKey(Subentidad, on_delete=models.CASCADE, blank=True, null=True)
    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE, blank=True, null=True)
    gauser = models.ForeignKey(Gauser, on_delete=models.CASCADE, null=True, blank=True)
    permiso = models.CharField('Permiso sobre el documento', max_length=15, choices=PERMISOS, default='r')

    def __str__(self):
        return '%s (%s)' % (self.documento.nombre, self.permiso)


class Contrato_gauss(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    firma_gauss = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True, related_name='firma_gauss21')
    firma_entidad = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True,
                                      related_name='firma_entidad2')
    texto = models.TextField("Texto del contrato")
    fichero = models.FileField("Contrato firmado", upload_to=update_fichero_contrato, blank=True, null=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = "Contratos con entidades"

    def __str__(self):
        return '%s (%s)' % (self.entidad, self.modificado)


###################################################################################
##############################DISEÑO TEXTOS EVALUABLES#############################
###################################################################################
def crea_clave():
    return pass_generator(49)

class TextoEvaluable(models.Model):
    RESPUESTAS = (('respuestatxt', 'Texto'), ('respuestaopm', 'Opción Múltiple'), ('respuestavof', 'Verdadero o Falso'))
    TIPOS = (('personal', 'Solo puedes acceder tú a este texto evaluable'),
             ('entidad', 'Podrá ser accesible por personas de tu Entidad con los permisos adecuados'),
             ('organization', 'Podrá ser accesible por personas de tu Organización con los permisos adecuados'),
             ('public', 'Podrá ser accesible por cualquier persona registrada en GAUSS con los permisos adecuados'))
    propietario = models.ForeignKey(GE, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE)
    title = models.CharField('Título del texto', max_length=200, default='', blank=True, null=True)
    orden = models.IntegerField('Orden de aparición con respecto a sus hermanos (mismo padre)', default=0)
    enum = models.BooleanField('¿Es enumerable?', default=False)
    pre_enum = models.CharField('Prefijo de la enumeración', blank=True, null=True, default='', max_length=30)
    suf_enum = models.CharField('Sufijo de la enumeración', blank=True, null=True, default='', max_length=30)
    texto = models.TextField('Texto', blank=True, null=True, default='')
    respuesta = models.CharField('Tipo de respuesta', max_length=15, default='respuestatxt', choices=RESPUESTAS)
    tipo = models.CharField('Tipo de accesibilidad al documento', max_length=15, default='personal', choices=TIPOS)
    dce = models.ForeignKey(DocConfEntidad, blank=True, null=True, on_delete=models.SET_NULL)
    secret = models.CharField('clave secreta enlace', max_length=50, default=crea_clave)
    plantilla =models.BooleanField('¿Es una plantilla?', default=False)
    borrado = models.BooleanField('¿Texto borrado?', default=False)

    @property
    def deep_enum(self):
        if self.parent:
            return "%s.%s" % (self.parent.deep_enum, self.enum)
        else:
            return "%s" % (self.enum)

    def get_pte(self, ge):
        if self.tipo == 'entidad':
            pte = self.permisotextoevaluable_set.get(ge__gauser=ge.gauser,
                                                     ge__ronda__entidad=self.propietario.ronda.entidad)
        elif self.tipo == 'organization':
            pte = self.permisotextoevaluable_set.get(ge__gauser=ge.gauser,
                                                     ge__ronda__entidad__organization=self.propietario.ronda.entidad.organization)
        elif self.tipo == 'public':
            pte = self.permisotextoevaluable_set.get(ge__gauser=ge.gauser)
        else:
            pte = PermisoTextoEvaluable.objects.none()
        return pte

    def has_permiso(self, ge, permiso):
        """
        :param permiso: string que contiene  ve_te, modifica_te, ...
        :return: True or False. Puede ser None si se produce un error
        """
        if ge.gauser == self.propietario.gauser or ge.gauser.username == 'gauss':
            return True
        try:
            pte = self.get_pte(ge)
            if permiso in pte.permiso:
                return True
            else:
                return False
        except:
            return None

    def add_permiso(self, ge, permiso):
        """
        :param permiso: string que contiene  ve_te, modifica_te, ...
        :return: True or False dependiendo de si la operación se ha podido realizar
        """
        try:
            pte = self.get_pte(ge)
            if not permiso in pte.permiso:
                pte.permiso += permiso
                pte.save()
            return True
        except:
            return False

    def del_permiso(self, ge, permiso):
        """
        :param permiso: string que contiene  ve_te, modifica_te, ...
        :return: True or False dependiendo de si la operación se ha podido realizar
        """
        try:
            pte = self.get_pte(ge)
            if permiso in pte.permiso:
                pte.permiso.replace(permiso, '')
                pte.save()
            return True
        except:
            return False

    def __str__(self):
        return '%s - %s (%s)' % (self.propietario.ronda, self.title, self.tipo)


class OpTextoEvaluable(models.Model):
    textoevaluable = models.ForeignKey(TextoEvaluable, on_delete=models.CASCADE)
    option = models.CharField('Nombre de la opción', max_length=200, blank=True, null=True, default='')
    valor = models.IntegerField('Valor de la opción', blank=True, null=True, default=0)

    def __str__(self):
        return '%s (%s -> %s)' % (self.textoevaluable, self.option, self.valor)


class RubricaTextoEvaluable(models.Model):
    textoevaluable = models.ForeignKey(TextoEvaluable, on_delete=models.CASCADE)
    aspecto = models.TextField('Aspecto a evaluar', blank=True, null=True, default='')
    orden = models.IntegerField('Orden en el que se mostrará el aspecto', default=1)

    def __str__(self):
        return '%s (%s -> %s)' % (self.textoevaluable, self.orden, self.aspecto[:100])


class NivelRubricaTextoEvaluable(models.Model):
    rubte = models.ForeignKey(RubricaTextoEvaluable, on_delete=models.CASCADE)
    criterio = models.TextField('Criterio de evaluación', blank=True, null=True, default='')
    orden = models.IntegerField('Orden en el que se mostrará el criterio', default=1)
    valor = models.IntegerField('Valor asignado al criterio', default=1)

    def __str__(self):
        return '%s (%s -> %s)' % (self.rubte, self.criterio[:100], self.valor)


class PermisoTextoEvaluable(models.Model):
    permisos = (
        ('ve_te', 'Puede ver el texto evaluable'), ('modifica_te', 'Puede modificar el texto evaluable'),
        ('borra_te', 'Puede borrar el texto evaluable'), ('add_te', 'Puede añadir apartados al texto evaluable'),
        ('ve_reste', 'Puede ver respuestas al texto evaluable'),
        ('add_reste', 'Puede dar respuesta al texto evaluable'),
        ('eval_reste', 'Puede evaluar las respuestas al texto evaluable'))
    textoevaluable = models.ForeignKey(TextoEvaluable, on_delete=models.CASCADE)
    ge = models.ForeignKey(GE, blank=True, null=True, on_delete=models.CASCADE)
    cargo = models.ForeignKey(Cargo, blank=True, null=True, on_delete=models.CASCADE)
    permiso = models.CharField('Permisos', blank=True, null=True, max_length=100)

    def __str__(self):
        return '%s (%s) - %s' % (self.textoevaluable, self.ge.gauser.get_full_name(), self.permiso)


class RespuestaTextoEvaluable(models.Model):
    propietario = models.ForeignKey(GE, on_delete=models.CASCADE)
    textoevaluable = models.ForeignKey(TextoEvaluable, on_delete=models.CASCADE)
    respuestatxt = models.TextField('Texto de la respuesta', blank=True, null=True, default='')
    respuestaopm = models.ForeignKey(OpTextoEvaluable, on_delete=models.CASCADE)
    respuestavof = models.BooleanField('Verdadero o Falso', default=False)

    def __str__(self):
        return '%s (%s)' % (self.textoevaluable, self.propietario.gauser.get_full_name())


class EvalRespuestaTextoEvaluable(models.Model):
    reste = models.ForeignKey(RespuestaTextoEvaluable, on_delete=models.CASCADE)
    nrubte = models.ForeignKey(NivelRubricaTextoEvaluable, on_delete=models.CASCADE)

    def __str__(self):
        return '%s || %s' % (self.reste, self.nrubte)

###################################################################################
