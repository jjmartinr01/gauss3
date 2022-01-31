# -*- coding: utf-8 -*-
from datetime import date
import re
from django.db import models
from django.contrib.auth.models import AbstractUser
from gauss.constantes import *
from bancos.models import Banco

def genera_nie(a=''):
    if a:
        a = a.upper()
        dni = re.sub('[^0-9]', '', a)
        if not dni:
            return ''
        if a[0] in 'XYZ':
            comienzo = a[0]
            dni = dni[-7:] # Cadenas de más de 7 cifras eliminamos las primeras
            while len(dni) < 7:
                dni = '0' + dni
            # Para calcular letra nie, el comienzo X se sustituye por 0, el Y por 1 y Z por 2
            comienzos = {'X': '0', 'Y': '1', 'Z': '2'}
            dni = comienzos[comienzo] + dni
            letra = 'TRWAGMYFPDXBNJZSQVHLCKE'[int(dni) % 23]
            return comienzo + dni[1:] + letra
        else:
            dni = dni[-8:] # Cadenas de más de 8 cifras eliminamos las primeras
            while len(dni) < 8:
                dni = '0' + dni
            letra = 'TRWAGMYFPDXBNJZSQVHLCKE'[int(dni) % 23]
            return dni + letra
    else:
        return ''

TIPO = (('Gauss', 'Gauss'),
        ('Restringido', 'Restringido'),
        ('Accesible', 'Accesible'))
NIVEL = ((1, 'Menú principal'),
         (2, 'Menú de segundo nivel'),
         (3, 'Menú de tercer nivel'),
         (4, 'Menú de cuarto nivel'))


class Menu_default(models.Model):
    code_menu = models.CharField("Código identificador del menú", max_length=100, blank=True, null=True)
    texto_menu = models.CharField("Texto", max_length=300, blank=True, null=True)
    href = models.CharField("Cadena redirigida en urls.py", max_length=200, blank=True, null=True)
    nivel = models.IntegerField("Nivel dentro de la estructura del menú", choices=NIVEL, blank=True, null=True)
    tipo = models.CharField("Tipo de menú", max_length=30, choices=TIPO, blank=True, null=True)
    parent = models.ForeignKey('self', related_name='parent_menu_default', blank=True, null=True, on_delete=models.CASCADE)
    pos = models.IntegerField('Posición en la lista de menús', default=1)

    @property
    def permisos(self):
        return self.permiso_set.all()

    class Meta:
        ordering = ['pos', 'id']

    @property
    def children(self):
        return Menu_default.objects.filter(parent=self)

    def __str__(self):
        return '%s --> %s' % (self.code_menu, self.texto_menu)


class Permiso(models.Model):
    TIPOS = (
        ('MEN', 'Permiso para acceder a un menú'),
        ('SUB', 'Permiso para acceder a un submenú'),
        ('MTE', 'Permiso para acceder a un elemento de un menú'),
        ('STE', 'Permiso para acceder a un elemento de un submenú'),
        ('ESP', 'Permiso especial para determinadas acciones'),
        ('MENU', 'Permiso para acceder a menús o submenús'),
        ('ACTION', 'Permiso para realizar acciones dentro de un módulo'),
    )
    nombre = models.CharField("Nombre del permiso", max_length=100, blank=True, null=True)
    code_nombre = models.CharField("Código del permiso", max_length=50)
    tipo = models.CharField("tipo", max_length=10, blank=True, null=True)
    menu = models.ForeignKey(Menu_default, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ['menu', 'pk']

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.code_nombre)


class Gauser(AbstractUser):
    sexo = models.CharField("Sexo", max_length=10, choices=SEXO, blank=True, null=True)
    dni = models.CharField("DNI", max_length=20, null=True, blank=True)
    address = models.CharField("Dirección", max_length=100, blank=True, null=True)
    postalcode = models.CharField("Código postal", max_length=10, blank=True, null=True)
    localidad = models.CharField("Localidad de residencia", max_length=50, blank=True, null=True)
    provincia = models.CharField("Provincia", max_length=50, blank=True, choices=PROVINCIAS, null=True)
    nacimiento = models.DateField("Fecha de nacimiento", blank=True, null=True)
    telfij = models.CharField("Teléfono fijo", max_length=30, blank=True, null=True)
    telmov = models.CharField("Teléfono móvil", max_length=30, blank=True, null=True)
    familia = models.BooleanField("Familia numerosa", default=False)
    fecha_alta = models.DateField("Fecha de alta en la entidad", blank=True, null=True)
    fecha_baja = models.DateField("Fecha de baja en la entidad", blank=True, null=True)
    ficticio = models.BooleanField("Este es un usuario ficticio?", default=False)
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)
    dni_duplicado = models.BooleanField('¿DNI duplicado?', default=True)

    @property
    def has_mail(self):
        if len(self.email) > 5:
            return True

    class Meta:
        verbose_name_plural = "Usuarios (Gauser)"
        ordering = ['pk']

    def save(self, *args, **kwargs):
        self.dni = genera_nie(self.dni)
        super(Gauser, self).save(*args, **kwargs)

    def __str__(self):
        if self.email:
            texto = '%s %s (%s)' % (self.first_name, self.last_name, self.email)
        else:
            texto = '%s %s' % (self.first_name, self.last_name)
        return texto


class Enlace(models.Model):
    usuario = models.ForeignKey(Gauser, on_delete=models.CASCADE)
    code = models.CharField("Código", max_length=40)
    enlace = models.CharField("Enlace", max_length=100)
    deadline = models.DateField('Fecha límite de validez')
    expiration = models.DateTimeField('Fecha y hora de expiración', blank=True, null=True)

    def __str__(self):
        return '%s -- %s (%s)' % (self.enlace, self.usuario, self.deadline)

# class Candidato(models.Model):
#     gauser= models.ForeignKey(Gauser, on_delete=models.CASCADE)
#     sexo = models.CharField("Sexo", max_length=10, choices=SEXO, blank=True, null=True)
#     dni = models.CharField("DNI", max_length=20, null=True, blank=True)
#     address = models.CharField("Dirección", max_length=100, blank=True, null=True)
#     postalcode = models.CharField("Código postal", max_length=10, blank=True, null=True)
#     localidad = models.CharField("Localidad de residencia", max_length=50, blank=True, null=True)
#     provincia = models.CharField("Provincia", max_length=50, blank=True, null=True)
#     nacimiento = models.DateField("Fecha de nacimiento", blank=True, null=True)
#     telfij = models.CharField("Teléfono fijo", max_length=30, blank=True, null=True)
#     telmov = models.CharField("Teléfono móvil", max_length=30, blank=True, null=True)
#     familia = models.BooleanField("Familia numerosa", default=False)
#     username = models.CharField("username del candidato", max_length=30, blank=True, null=True)
#     first_name = models.CharField("first name del candidato", max_length=130, blank=True, null=True)
#     last_name = models.CharField("last name del candidato", max_length=130, blank=True, null=True)
#     email = models.CharField("email del candidato", max_length=130, blank=True, null=True)
#     password = models.CharField("password del candidato", max_length=230, blank=True, null=True)
#     arreglado = models.BooleanField("Está ya arreglada la confusión", default=False)
#
#     def __str__(self):
#         return '%s -- %s (%s)' % (self.gauser, self.username, self.dni)