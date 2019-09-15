# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, timedelta, datetime
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
from gauss.constantes import *
from gauss.rutas import *
from bancos.models import Banco
from django.db.models import Q
from autenticar.models import Gauser, Permiso, Menu_default


# post_save.connect(update_stock, sender=TransactionDetail, dispatch_uid="update_stock_count")

# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían


def update_anagrama_organizacion(instance, filename):
    nombre = filename.partition('.')
    nombre = str(instance.iniciales) + '_anagrama.' + nombre[2]
    return os.path.join("anagramas/", nombre)


class Organization(models.Model):
    organization = models.CharField("Organización a la que pertenece la entidad", max_length=100)
    iniciales = models.CharField("iniciales de la organización", max_length=30)
    fecha_fundada = models.DateField("Fecha de fundación", null=True, blank=True)
    web = models.URLField("Página web")
    anagrama = models.ImageField("Anagrama de la organización", upload_to=update_anagrama_organizacion, null=True,
                                 blank=True)

    def filename(self):
        return os.path.basename(self.anagrama.name)

    def __str__(self):
        return u'%s (%s)' % (self.organization, self.iniciales)


class Ronda(models.Model):
    entidad = models.ForeignKey('Entidad', related_name='rondas', null=True, blank=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre del periodo de funcionamiento", max_length=30)
    inicio = models.DateField("Fecha de inicio de ronda", null=True, blank=True)
    fin = models.DateField("Fecha de finalización de ronda", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Rondas"
        ordering = ['-inicio', 'nombre']

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.entidad.name)


def update_anagrama_entidad(instance, filename):
    nombre = filename.partition('.')
    nombre = str(instance.code) + '_anagrama.' + nombre[2]
    return os.path.join("anagramas/", nombre)


GNS = ((1, 'Entidad'), (2, 'Asociación'), (3, 'Asociación de Padres de Alumnos'),
       (4, 'Asociación de Madres y Padres de Alumnos'), (101, 'Grupo'), (102, 'Grupo Scout'),
       (5, 'Asociación Deportiva'), (103, 'Club Deportivo'), (104, 'IES'), (105, 'Colegio'))
PLURAL_GN = {1: 'Entidades', 2: 'Asociaciones', 3: 'Asociaciones de Padres de Alumnos',
             4: 'Asociaciones de Madres y Padres de Alumnos', 101: 'Grupos', 102: 'Grupos Scout',
             5: 'Asociaciones Deportivas', 103: 'Clubes Deportivos', 104: 'IES', 105: 'Colegios'}

GUS = ((101, 'usuario'), (102, 'miembro'), (103, 'socio'))


class Entidad(models.Model):
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.CASCADE)
    ronda = models.ForeignKey(Ronda, related_name='entidades', null=True, blank=True, on_delete=models.CASCADE)
    code = models.IntegerField("Código de entidad", null=True, blank=True)
    nif = models.CharField("NIF", max_length=20, null=True, blank=True)
    banco = models.ForeignKey(Banco, null=True, blank=True, on_delete=models.CASCADE)
    iban = models.CharField("IBAN", max_length=40, null=True, blank=True)
    name = models.CharField("Nombre", max_length=250, null=True, blank=True)
    address = models.CharField("Dirección", max_length=375, null=True, blank=True)
    localidad = models.CharField("Localidad", max_length=200, null=True, blank=True)
    provincia = models.CharField("Provincia", max_length=4, choices=PROVINCIAS, default='0')
    postalcode = models.CharField("Código postal", max_length=20, null=True, blank=True)
    tel = models.CharField("Teléfono", max_length=20, null=True, blank=True)
    fax = models.CharField("Fax", max_length=20, null=True, blank=True)
    web = models.URLField("Web", max_length=100, null=True, blank=True)
    mail = models.EmailField("E-mail", max_length=100, null=True, blank=True)
    anagrama = models.ImageField("Anagrama", upload_to=update_anagrama_entidad, blank=True)
    dominio = models.CharField("Subdominio", max_length=200, null=True, blank=True)
    general_name = models.IntegerField("Nombre general", default=1, choices=GNS)
    general_user = models.IntegerField("Nombre general de usuario", default=101, choices=GUS)
    secret = models.CharField("Clave secreta asociada a la entidad", blank=True, null=True, max_length=50)

    class Meta:
        verbose_name_plural = "Entidades"

    @property
    def de_la_entidad(self):
        gn = self.get_general_name_display()
        return 'de la %s' % (gn) if self.general_name < 100 else 'del %s' % (gn)

    @property
    def a_la_entidad(self):
        gn = self.get_general_name_display()
        return 'a la %s' % (gn) if self.general_name < 100 else 'al %s' % (gn)

    @property
    def la_entidad(self):
        gn = self.get_general_name_display()
        return 'la %s' % (gn) if self.general_name < 100 else 'el %s' % (gn)

    @property
    def entidades(self):
        return PLURAL_GN[self.general_name]

    @property
    def de_las_entidades(self):
        gns = PLURAL_GN[self.general_name]
        return 'de las %s' % (gns) if self.general_name < 100 else 'de los %s' % (gns)

    @property
    def a_las_entidades(self):
        gn = self.get_general_name_display()
        return 'a las %s' % (gn) if self.general_name < 100 else 'a los %s' % (gn)

    @property
    def las_entidades(self):
        gn = self.get_general_name_display()
        return 'las %s' % (gn) if self.general_name < 100 else 'los %s' % (gn)

    def __str__(self):
        return u'%s (%s)' % (self.name, self.code)

class DocConfEntidad(models.Model):
    entidad = models.OneToOneField(Entidad, on_delete=models.CASCADE)
    header = models.TextField("Cabecera de página", blank=True, null=True)
    footer = models.TextField("Pie de página", blank=True, null=True)
    pagesize = models.CharField('Tamaño del papel', max_length=5, blank=True, null=True, default='A4')
    margintop = models.CharField('Tamaño del papel', max_length=5, blank=True, null=True, default='52')
    marginright = models.CharField('Tamaño del papel', max_length=5, blank=True, null=True, default='20')
    marginbottom = models.CharField('Tamaño del papel', max_length=5, blank=True, null=True, default='10')
    marginleft = models.CharField('Tamaño del papel', max_length=5, blank=True, null=True, default='20')
    encoding = models.CharField('Tamaño del papel', max_length=15, blank=True, null=True, default='UTF-8')
    headerspacing = models.CharField('Tamaño del papel', max_length=5, blank=True, null=True, default='5')

    def __str__(self):
        return u'%s (top: %s, bottom: %s, left: %s, right: %s)' % (self.entidad, self.margintop, self.marginbottom, self.marginleft, self.marginright)


class Subentidad(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre", max_length=250, null=True, blank=True)
    edad_min = models.IntegerField("Edad de acceso", null=True, blank=True)
    edad_max = models.IntegerField("Edad de finalización", null=True, blank=True)
    mensajes = models.BooleanField("Están en lista de mensajería", default=False)
    observaciones = models.TextField("Observaciones", null=True, blank=True)
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
    fecha_expira = models.DateField('Fecha de expiración', default=date(3000, 1, 1))
    creado = models.DateField('Fecha de creación', auto_now_add=True)

    @property
    def rango_edad(self):
        return self.edad_max - self.edad_min

    class Meta:
        verbose_name_plural = "Subentidades"
        ordering = ['parent__nombre', 'nombre']

    def __str__(self):
        return u'Subentidad: %s (%s)' % (self.nombre, self.entidad.name)


class Subsubentidad(models.Model):
    subentidad = models.ForeignKey(Subentidad, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre", max_length=250, null=True, blank=True)
    observaciones = models.TextField("Observaciones", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Subsubentidades"

    def __str__(self):
        return u'Subentidad: %s (%s)' % (self.nombre, self.entidad.name)


class Alta_Baja(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    gauser = models.ForeignKey('autenticar.Gauser', on_delete=models.CASCADE)
    autor = models.CharField("Creador de la alta/baja", max_length=200, blank=True, null=True, default='Desconocido')
    observaciones = models.TextField("Observaciones", null=True, blank=True)
    fecha_alta = models.DateField('Fecha de alta', null=True, blank=True, auto_now_add=True)
    fecha_baja = models.DateField('Fecha de baja', null=True, blank=True)

    @property
    def estado_unidad_familiar(self):
        bajas = Alta_Baja.objects.filter(entidad=self.entidad, fecha_baja__isnull=False).order_by('-fecha_baja')
        ges = Gauser_extra.objects.filter(ronda__entidad=self.entidad, gauser=self.gauser)
        gs = []
        for ge in ges:
            for miembro in ge.unidad_familiar:
                if not any(d['gauser'] == miembro.gauser for d in gs):
                    is_baja = bajas.filter(gauser=miembro.gauser).count() > 0
                    gs.append({'gauser': miembro.gauser, 'is_baja': is_baja})
        return gs

    def dar_alta(self, autor):
        ge, tutor1, tutor2 = None, None, None
        if self.fecha_baja:
            ges = Gauser_extra.objects.filter(gauser=self.gauser, ronda__entidad=self.entidad)
            try:
                ge = ges.get(ronda=self.entidad.ronda)
                tutor1 = ge.tutor1
                tutor2 = ge.tutor2
            except:
                ge = ges.order_by('ronda').reverse()[0]
                tutor1 = ge.tutor1
                tutor2 = ge.tutor2
                ge.pk = None
                if tutor1: tutor1.pk = None
                if tutor2: tutor2.pk = None
            if tutor1:
                tutor1.ronda = self.entidad.ronda
                tutor1.activo = True
                tutor1.save()
                try:
                    baja = Alta_Baja.objects.get(gauser=tutor1.gauser, entidad=self.entidad)
                    baja.observaciones += "(Autor: %s) Es dado de alta con fecha %s<br>" % (autor, date.today())
                    baja.fecha_baja = None
                    baja.autor = autor
                    baja.save()
                except:
                    Alta_Baja.objects.create(gauser=tutor1.gauser, entidad=self.entidad, fecha_baja=None, autor=autor,
                                             observaciones='(Autor: %s) Se da de alta.<br>' % (autor))
            if tutor2:
                tutor2.ronda = self.entidad.ronda
                tutor2.activo = True
                tutor2.save()
                try:
                    baja = Alta_Baja.objects.get(gauser=tutor2.gauser, entidad=self.entidad)
                    baja.observaciones += "(Autor: %s) Es dado de alta con fecha %s<br>" % (autor, date.today())
                    baja.fecha_baja = None
                    baja.autor = autor
                    baja.save()
                except:
                    Alta_Baja.objects.create(gauser=tutor2.gauser, entidad=self.entidad, fecha_baja=None, autor=autor,
                                             observaciones='(Autor: %s) Se da de alta.<br>' % (autor))
            ge.ronda = self.entidad.ronda
            ge.activo = True
            ge.tutor1 = tutor1
            ge.tutor2 = tutor2
            ge.save()
            self.observaciones += "(Autor: %s) Es dado de alta con fecha %s<br>" % (autor, date.today())
            self.fecha_baja = None
            self.autor = autor
            self.save()
        return {'ge': ge, 'tutor1': tutor1, 'tutor2': tutor2}

    class Meta:
        verbose_name_plural = "Altas y bajas"

    def __str__(self):
        return u'%s (%s) - Alta: %s, Baja: %s' % (
            self.gauser.get_full_name(), self.entidad.name, self.fecha_alta, self.fecha_baja)


NIVELES = ((1, 'Cargo/Perfil de primer nivel'), (2, 'Cargo/Perfil de segundo nivel'),
           (3, 'Cargo/Perfil de tercer nivel'), (4, 'Cargo/Perfil de cuarto nivel'),
           (5, 'Cargo/Perfil de quinto nivel'), (6, 'Cargo/Perfil de sexto nivel'))


class Cargo(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    cargo = models.CharField("Cargo", max_length=200, null=True, blank=True)
    permisos = models.ManyToManyField('autenticar.Permiso', blank=True)
    nivel = models.IntegerField('Nivel jerárquico en el organigrama', null=True, blank=True, choices=NIVELES,
                                default=6)

    class Meta:
        ordering = ['nivel', 'cargo']

    def __str__(self):
        return u'%s' % (self.cargo)


CAMPOS_RESERVA = (('first_name', 'Nombre'), ('last_name', 'Apellidos'), ('address', 'Dirección'), ('sexo', 'Sexo'),
                  ('email', 'e-mail'), ('telfij', 'Teléfono fijo'), ('telmov', 'Teléfono móvil'),
                  ('nacimiento', 'Fecha de nacimiento'), ('dni', 'DNI/NIF'),
                  ('first_name_tutor1', 'Nombre del primer tutor'), ('dni_tutor1', 'DNI/NIF del primer tutor'),
                  ('last_name_tutor1', 'Apellidos del primer tutor'),
                  ('telfij_tutor1', 'Teléfono fijo del primer tutor'),
                  ('telmov_tutor1', 'Teléfono móvil del primer tutor'), ('email_tutor1', 'e-mail del primer tutor'),
                  ('first_name_tutor2', 'Nombre del segundo tutor'), ('dni_tutor2', 'DNI/NIF del segundo tutor'),
                  ('last_name_tutor2', 'Apellidos del segundo tutor'),
                  ('telfij_tutor2', 'Teléfono fijo del segundo tutor'),
                  ('telmov_tutor2', 'Teléfono móvil del segundo tutor'), ('email_tutor2', 'e-mail del segundo tutor'),
                  ('observaciones', 'Observaciones'))


class ConfiguraReservaPlaza(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    campo = models.CharField("Campo de reserva", max_length=20, choices=CAMPOS_RESERVA, blank=True)
    texto = models.CharField('Texto que se mostrará asociado al campo', max_length=200, blank=True, default='')
    usado = models.BooleanField('Es usado en el formulario?', default=False)
    required = models.BooleanField('Es obligatorio?', default=False)
    columns = models.IntegerField('Número de columnas que ocupa', blank=True, null=True, default=4)
    orden = models.IntegerField('Orden que ocupa en el formulario', blank=True, null=True, default=1)
    row = models.BooleanField('Comienza una nueva fila?', default=False)

    class Meta:
        verbose_name_plural = "Configuraciones de reserva de plazas"
        ordering = ['entidad', 'orden']

    def __str__(self):
        return u'%s %s (%s) - columns: %s' % (self.entidad.name, self.campo, self.required, self.columns)


class Reserva_plaza(models.Model):
    NAC_DEF = date.today() - timedelta(7000)
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    first_name = models.CharField("Nombre", max_length=30, null=True, blank=True, default='')
    last_name = models.CharField("Apellidos", max_length=30, null=True, blank=True, default='')
    address = models.CharField("Dirección postal", max_length=100, null=True, blank=True, default='')
    sexo = models.CharField("Sexo", max_length=10, choices=SEXO, blank=True, default='M')
    email = models.CharField("Correo electrónico", max_length=100, null=True, blank=True, default='')
    telfij = models.CharField("Teléfono fijo", max_length=30, null=True, blank=True, default='')
    telmov = models.CharField("Teléfono móvil", max_length=30, null=True, blank=True, default='')
    nacimiento = models.DateField("Fecha de nacimiento", blank=True, null=True, default=NAC_DEF)
    dni = models.CharField("Teléfono móvil", max_length=30, null=True, blank=True, default='')
    first_name_tutor1 = models.CharField("Nombre", max_length=30, null=True, blank=True, default='')
    last_name_tutor1 = models.CharField("Apellidos", max_length=30, null=True, blank=True, default='')
    telfij_tutor1 = models.CharField("Teléfono fijo del primer tutor", max_length=30, null=True, blank=True, default='')
    telmov_tutor1 = models.CharField("Teléfono móvil del primer tutor", max_length=30, blank=True, default='')
    email_tutor1 = models.CharField("Correo electrónico del primer tutor", max_length=100, blank=True, default='')
    dni_tutor1 = models.CharField("Teléfono móvil", max_length=30, null=True, blank=True, default='')
    first_name_tutor2 = models.CharField("Nombre", max_length=30, null=True, blank=True, default='')
    last_name_tutor2 = models.CharField("Apellidos", max_length=30, null=True, blank=True, default='')
    telfij_tutor2 = models.CharField("Teléfono fijo del segundo tutor", max_length=30, blank=True, default='')
    telmov_tutor2 = models.CharField("Teléfono móvil del segundo tutor", max_length=30, blank=True, default='')
    email_tutor2 = models.CharField("Correo electrónico del primer tutor", max_length=100, blank=True, default='')
    dni_tutor2 = models.CharField("Teléfono móvil", max_length=30, null=True, blank=True, default='')
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')
    creado = models.DateTimeField('Fecha y hora de la solicitud de reserva', auto_now_add=True)

    def subentidades(self):  # Devuelve las subentidades a las que podría pertenecer
        born = self.nacimiento
        today = date.today()
        try:
            edad = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            return ' o '.join([s.nombre for s in
                               Subentidad.objects.filter(entidad=self.entidad, edad_min__lte=edad, edad_max__gte=edad,
                                                         fecha_expira__gt=date.today())])
        except:
            return 'No es posible saberlo'  # Esto será devuelto cuando el gauser no tenga definido nacimiento

    class Meta:
        verbose_name_plural = "Reservas de plaza"

    def __str__(self):
        return u'%s %s (%s)' % (self.first_name, self.last_name, self.nacimiento)


class Dependencia(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la dependencia", max_length=200)
    es_aula = models.BooleanField("Se utiliza como aula", default=False)
    abrev = models.CharField("Abreviatura de la dependencia", max_length=50, blank=True, null=True)
    edificio = models.CharField("Edificio en el que se encuentra", max_length=40, null=True, blank=True, default='')
    planta = models.CharField("Planta en la que se encuentra", max_length=40, null=True, blank=True, default='')
    largo = models.DecimalField("Largura del aula en metros", max_digits=5, decimal_places=2, null=True, blank=True,
                                default=10)
    ancho = models.DecimalField("Anchura del aula en metros", max_digits=5, decimal_places=2, null=True, blank=True,
                                default=6)
    observaciones = models.TextField("Observaciones", null=True, blank=True, default='')
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    class Meta:
        ordering = ['edificio', 'planta', 'nombre']

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.entidad.name)


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_foto(instance, filename):
    nombre = filename.partition('.')
    return os.path.join("fotos/", str(instance.ronda.entidad.code) + '_' + str(instance.id) + '.' + nombre[2])


class Gauser_extra(models.Model):
    gauser = models.ForeignKey('autenticar.Gauser', null=True, blank=True, related_name='entidades',
                               on_delete=models.CASCADE)
    entidad = models.ForeignKey(Entidad, null=True, blank=True, related_name='entidades', on_delete=models.CASCADE)
    subentidades = models.ManyToManyField(Subentidad, blank=True, related_name='entidades')
    subsubentidades = models.ManyToManyField(Subsubentidad, blank=True, related_name='entidades')
    cargos = models.ManyToManyField(Cargo, blank=True, related_name='entidades')
    ronda = models.ForeignKey(Ronda, null=True, blank=True, related_name='g_eronda', on_delete=models.CASCADE)
    permisos = models.ManyToManyField('autenticar.Permiso', blank=True, related_name='entidades')
    id_organizacion = models.CharField("Nº de identificación general", max_length=20, blank=True, null=True)
    id_entidad = models.CharField("Nº de identificación en la entidad", max_length=20, blank=True, null=True)
    alias = models.CharField("Alias con el que te conocen", max_length=75, null=True, blank=True)
    activo = models.BooleanField("Activo", default=False)
    observaciones = models.TextField("Datos de interés a tener en cuenta", null=True, blank=True)
    foto = models.ImageField("Fotografía", upload_to=update_foto, blank=True, null=True)
    tutor1 = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='primer_tutor_entidades')
    tutor2 = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='segundo_tutor_entidades')
    hermanos = models.ManyToManyField('self', blank=True, related_name='hermanos_entidades')
    ocupacion = models.CharField("Ocupación/Profesión del socio", max_length=300, blank=True, null=True)
    banco = models.ForeignKey(Banco, null=True, blank=True, related_name='entidades', on_delete=models.CASCADE)
    entidad_bancaria = models.CharField("Entidad bancaria", max_length=50, blank=True, null=True)
    num_cuenta_bancaria = models.CharField("Número de IBAN", max_length=50, blank=True, null=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)
    consentimiento = models.BooleanField('Consentimiento datos en gauss', default=False)
    fecha_consentimiento = models.DateTimeField('Fecha y hora firma de consentimiento', blank=True, null=True)
    uso_imagenes = models.BooleanField('Autoriza al uso de imágenes', default=False)

    # tutor_entidad1 = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
    #                                    related_name='tutor_entidad')
    # tutor_entidad2 = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
    #                                    related_name='cotutor')

    def dar_baja(self, autor):
        try:
            baja = Alta_Baja.objects.get(gauser=self.gauser, entidad=self.entidad)
            baja.observaciones += '(Autor: %s) Se da de baja con fecha %s)<br>' % (autor, date.today())
            baja.fecha_baja = date.today()
            baja.autor = autor
            baja.save()
        except:
            baja = Alta_Baja.objects.create(gauser=self.gauser, entidad=self.entidad, fecha_baja=date.today(),
                                            autor=autor, observaciones='(Autor: %s) Se da de baja con fecha %s)<br>' % (
                    autor, date.today()))
        return baja

    def has_nivel(self, nivel):
        return len([cargo for cargo in self.cargos.all() if cargo.nivel <= nivel]) > 0

    def has_cargos(self, cargos_comprobar):  # Devuelve True (False) si (no) posee algún (ningún) cargos_comprobar
        if type(cargos_comprobar) == list:
            p_ids = self.cargos.all().values_list('nivel', flat=True)
            return len([cargo for cargo in p_ids if cargo in cargos_comprobar]) > 0
        else:
            return len([cargo for cargo in self.cargos.all() if cargo in cargos_comprobar]) > 0

    def has_permiso(self, permiso_comprobar):
        if self.gauser.username == 'gauss' or permiso_comprobar == 'libre':
            return True
        else:
            try:
                permiso = Permiso.objects.get(code_nombre=permiso_comprobar)
                if permiso in self.permisos.all():
                    return True
                else:
                    for cargo in self.cargos.all():
                        if permiso in cargo.permisos.all():
                            return True
                return False
            except:
                return False

    @property
    def permisos_cargos(self):
        return Permiso.objects.filter(id__in=self.cargos.values_list('permisos__id', flat=True))

    @property
    def permisos_list(self):  # Devuelve la lista de permisos que tiene
        permisos1 = self.permisos.all().values_list('id', flat=True)
        permisos2 = []  # self.perfiles.all().values_list('permisos__id', flat=True)
        permisos3 = self.cargos.all().values_list('permisos__id', flat=True)
        permisos = list(set(list(permisos1) + list(permisos2) + list(permisos3)))
        return Permiso.objects.filter(id__in=permisos)

    @property
    def es_padre(self):
        tutores = Gauser_extra.objects.filter(ronda=self.ronda).values_list('tutor1', 'tutor2')
        # Flat la lista y eliminamos los elementos None
        tutores = filter(None, set([e for l in tutores for e in l]))
        return self.id in tutores

    @property
    def edad(self):
        born = self.gauser.nacimiento
        today = date.today()
        try:
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except:
            return 300  # Este entero será devuelto cuando el gauser no tenga definido nacimiento

    @property
    def unidad_familiar(self):
        tutores = [self.id]
        if self.tutor1:
            tutores.append(self.tutor1.id)
        if self.tutor2:
            tutores.append(self.tutor2.id)
        familia_ids = Gauser_extra.objects.filter(Q(id__in=tutores) |
                                                  Q(tutor1__id__in=tutores) | Q(tutor2__id__in=tutores),
                                                  ronda=self.ronda).values_list('id', 'tutor1__id', 'tutor2__id')
        ids = filter(None, set([e for l in familia_ids for e in l]))
        return Gauser_extra.objects.filter(id__in=ids).order_by('gauser__nacimiento')

    def subentidades_hijos(self, propias=True):
        subentidades = list(self.subentidades.all().values_list('id', flat=True)) if propias else []
        hijos = Gauser_extra.objects.filter(Q(tutor1=self) | Q(tutor2=self))
        subentidades += list(hijos.values_list('subentidades__id', flat=True))
        return subentidades

    @property
    def permisos_id(self):
        p_ids = self.permisos.all().values_list('pk', flat=True)
        return p_ids

    class Meta:
        verbose_name_plural = "Datos extra de un usuario (Gauser_extra)"
        ordering = ['gauser__last_name']

    def __str__(self):
        return u'%s -- %s' % (self.gauser, self.ronda)


class GE_extra_field(models.Model):
    ge = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    code = models.CharField('Code', max_length=50, blank=True, null=True)
    name = models.CharField('Nombre', max_length=50, blank=True, null=True)
    value = models.TextField('Valor', blank=True, null=True)

    def __str__(self):
        return u'%s -- %s - %s' % (self.ge, self.code, self.name)


def user_auto_id(ge):
    eai = ge.ronda.entidad.entidad_auto_id
    if eai.auto:
        prefijo = eai.prefijo if eai.prefijo else ''
        sufijo = eai.sufijo if eai.sufijo else ''
        num = eai.lexema
        if eai.lexema == 'num':
            reg = r'^%s[0-9]+%s$' % (prefijo, sufijo)
            num = "%05d" % (Gauser_extra.objects.filter(ronda=ge.ronda, id_entidad__iregex=reg).count() + 1)
        elif eai.lexema == 'timestamp':
            num = datetime.now().strftime('%y%m%d%H%M%S')
        id_entidad = "%s%s%s" % (prefijo, num, sufijo)
        ok = False
        incidencias = []
        inicio = datetime.now()
        dt = datetime.now() - inicio
        while not ok or dt.seconds > 4:  # El control del tiempo es para evitar bucles muy grandes
            num_ids = Gauser_extra.objects.filter(ronda=ge.ronda, id_entidad=id_entidad).count()
            incidencias.append((id_entidad, num_ids))
            if num_ids == 0:
                ok = True
            else:
                if eai.lexema == 'num':
                    num = "%05d" % (int(num) + 1)
                elif eai.lexema == 'timestamp':
                    num = datetime.now().strftime('%y%m%d%H%M%S')
                id_entidad = "%s%s%s" % (prefijo, num, sufijo)
                dt = datetime.now() - inicio
        ge.id_entidad = id_entidad
        ge.save()
        return incidencias
    else:
        return False


def ge_id_patron_match(ge):
    id_entidad = ge.id_entidad
    eai = ge.ronda.entidad.entidad_auto_id
    prefijo_match = id_entidad.startswith(eai.prefijo)
    sufijo_match = id_entidad.endswith(eai.sufijo)
    quitar_sufijo = -len(eai.sufijo) if len(eai.sufijo) > 0 else 1000
    lexema = id_entidad[len(eai.prefijo):quitar_sufijo]
    if eai.lexema == 'num':
        lexema_match = lexema.isdigit()
    elif eai.lexema == 'timestamp':
        try:
            datetime.strptime(lexema, '%y%m%d%H%M%S')
            lexema_match = True
        except:
            lexema_match = False
    else:
        lexema_match = False
    return prefijo_match and sufijo_match and lexema_match


@receiver(post_save, sender=Gauser_extra, dispatch_uid="update_id_entidad")
def update_id(sender, instance, **kwargs):
    try:
        eai = instance.ronda.entidad.entidad_auto_id.auto
    except:
        eai = Entidad_auto_id.objects.create(entidad=instance.ronda.entidad)
    if eai:
        num = Gauser_extra.objects.filter(ronda=instance.ronda, id_entidad=instance.id_entidad).count()
        if num > 1 or not ge_id_patron_match(instance):
            user_auto_id(instance)


class Entidad_auto_id(models.Model):
    LEXEMAS = (('num', 'Número incremental'), ('timestamp', 'Instante del alta'))
    entidad = models.OneToOneField(Entidad, on_delete=models.CASCADE)
    auto = models.BooleanField('Auto', default=False)
    prefijo = models.CharField('Prefijo', max_length=15, blank=True, null=True, default='')
    lexema = models.CharField('Lexema', max_length=15, default='num', choices=LEXEMAS)
    sufijo = models.CharField('Sufijo', max_length=15, blank=True, null=True, default='')

    def __str__(self):
        return u'%s -- %s -- %s-%s-%s' % (self.entidad, self.auto, self.prefijo, self.lexema, self.sufijo)


# TIPOS = (('gchar', 'Texto con un máximo de 150 caracteres'), ('gselect', 'Seleccionar uno o varios valores'),
#          ('gint', 'Número entero (sin decimales)'), ('gfloat', 'Número con decimales'), ('gbool', 'Respuesta Sí/No'),
#          ('gdatetime', 'Fecha y hora (dd/mm/yyyy HH:mm)'), ('gdate', 'Fecha (dd/mm/yyyy)'),
#          ('gtext', 'Texto de longitud ilimitada'), ('gfile', 'Archivo'))
#
#
# def pass_generator(size=6, chars=string.ascii_letters + string.digits):
#     return ''.join(random.choice(chars) for x in range(size))
#
#
# def guarda_archivo(instance, filename):
#     nombre = filename.rpartition('.')
#     instance.fich_name = filename.rpartition('/')[2]
#     fichero = pass_generator(size=20) + '.' + nombre[2]
#     return '/'.join(['entidades', str(instance.ge.ronda.entidad.code), fichero])
#
#
# class GE_extra_field(models.Model):
#     ge = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
#     ancho = models.IntegerField("Número de columnas (anchura)", blank=True, null=True)
#     tipo = models.CharField('Tipo de entrada', max_length=30, choices=TIPOS)
#     label = models.CharField('Label', max_length=150)
#     select = models.BooleanField('Es un select múltiple?', default=False)
#     gchar = models.CharField('Texto con un máximo de 150 caracteres', max_length=150, blank=True, null=True)
#     gint = models.IntegerField('Número entero (sin decimales)', blank=True, null=True)
#     gfloat = models.FloatField('Número con decimales', max_length=50, blank=True, null=True)
#     gdate = models.DateField('Fecha (dd/mm/yyyy)', max_length=50, blank=True, null=True)
#     gdatetime = models.DateTimeField('Fecha y hora (dd/mm/yyyy HH:mm)', max_length=50, blank=True, null=True)
#     gtext = models.TextField('Texto de longitud ilimitada', blank=True, null=True)
#     gbool = models.BooleanField('Respuesta Sí/No', default=False)
#     archivo = models.FileField('Archivo', blank=True, null=True, upload_to=guarda_archivo)
#     content_type_archivo = models.CharField('Tipo de archivo', max_length=200, blank=True, null=True)
#     fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)
#
#     def __str__(self):
#         comentario = 'Original' if not self.ginput else self.rellenador.gauser.get_full_name()
#         return u'%s, %s (Tipo: %s) - %s' % (self.gform.nombre, self.label, self.tipo, comentario)
#
#
# class GE_extra_field_option(models.Model):
#     ge_extra_field = models.ForeignKey(GE_extra_field, blank=True, null=True, on_delete=models.CASCADE)
#     text = models.CharField('Text', max_length=150)
#     value = models.CharField('Value', max_length=50)
#     selected = models.BooleanField('Selected', default=False)
#
#     def __str__(self):
#         return u'%s (%s) - Seleccionada: %s' % (self.text, self.value, self.selected)


class Menu(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    menu_default = models.ForeignKey(Menu_default, blank=True, null=True, on_delete=models.CASCADE)
    texto_menu = models.CharField("Texto", max_length=300, blank=True, null=True)
    pos = models.IntegerField('Posición en la lista de menús', default=1)

    class Meta:
        ordering = ['entidad', 'pos', 'id']

    @property
    def siblings(self):
        return Menu.objects.filter(entidad=self.entidad, menu_default__parent=self.menu_default.parent).exclude(
            id=self.id)

    @property
    def permisos(self):
        return self.menu_default.permiso_set.all()

    @property
    def parent(self):
        return Menu.objects.get(menu_default=self.menu_default.parent)

    @property
    def children(self):
        return Menu.objects.filter(entidad=self.entidad, menu_default__parent=self.menu_default).distinct()

    def __str__(self):
        try:
            parent = ' - Padre: ' + self.parent.menu_default.code_menu
        except:
            parent = ''
        return u'N%s - %s.%s --> %s --> %s (%s)%s' % (
            self.menu_default.nivel, self.pos, self.menu_default.code_menu,
            self.menu_default.texto_menu, self.texto_menu, self.entidad.code, parent)


class Filtrado(models.Model):
    propietario = models.ForeignKey(Gauser_extra, on_delete=models.SET_NULL, null=True, blank=True)
    nombre = models.CharField("Nombre del filtro", max_length=200)
    operacion = models.CharField("Operaciones de filtrado", max_length=40, null=True, blank=True)

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.propietario.entidad.name)


FILTROS = (('gauser__first_name__icontains', 'El nombre contiene el texto ...'),
           ('gauser__last_name__icontains', 'Los apellidos contienen el texto ...'),
           ('subentidades__in', 'Pertenece a las Secciones/Departamentos ...'),
           ('cargos__in', 'Tiene alguno de los Cargos/Perfiles ...'),
           ('observaciones__icontains', 'En las observaciones pone ...'),
           ('ronda__id', 'Ha sido usuario en el año ...'),
           ('tutor1__gauser__first_name__icontains', 'El nombre del primer tutor contiene el texto ...'),
           ('tutor1__gauser__last_name__icontains', 'Los apellidos del primer tutor contienen el texto ...'),
           ('tutor2__gauser__first_name__icontains', 'El nombre del segundo tutor contiene el texto ...'),
           ('tutor2__gauser__last_name__icontains', 'Los apellidos del segundo tutor contienen el texto ...'),
           ('ocupacion__icontains', 'La ocupación/profesión es ...'),
           ('banco__in', 'El banco con el que trabaja es ...'),
           ('gauser__localidad__icontains', 'La localidad donde reside es ...'),
           ('gauser__provincia__icontains', 'La provincia donde reside es ...'),
           ('gauser__nacimiento__gt', 'La fecha de nacimiento es posterior a ...'),
           ('gauser__nacimiento__lt', 'La fecha de nacimiento es anterior a ...'),
           ('gauser_extra_estudios__grupo__nombre__icontains', 'El nombre del grupo del usuario contiene ...'),
           )


class FiltroQ(models.Model):
    filtrado = models.ForeignKey(Filtrado, on_delete=models.CASCADE)
    n_filtro = models.IntegerField("Número de filtro: 1, 2, ... del correspondiente Filtrado")
    filtro = models.CharField("Filtro utilizado", max_length=70, null=True, blank=True, choices=FILTROS)
    value = models.CharField("Valor a comparar", max_length=20, null=True, blank=True)

    class Meta:
        ordering = ['n_filtro']

    def __str__(self):
        return u'%s (%s)' % (self.filtrado, self.filtro)


CAMPOS = (('gauser__first_name', 'Nombre'),
          ('gauser__last_name', 'Apellidos'),
          ('gauser__email', 'Email'),
          ('gauser__address', 'Dirección'),
          ('gauser__telfij', 'Teléfono fijo'),
          ('gauser__telmov', 'Teléfono móvil'),
          ('subentidades__nombre', 'Secciones/Departamentos'),
          ('cargos__cargo', 'Cargos/Perfiles'),
          ('observaciones', 'Observaciones'),
          ('ronda__nombre', 'Año de los datos mostrados'),
          ('tutor1__gauser__first_name', 'Nombre del primer tutor'),
          ('tutor1__gauser__last_name', 'Apellidos del primer tutor'),
          ('tutor2__gauser__first_name', 'Nombre del segundo tutor'),
          ('tutor2__gauser__last_name', 'Apellidos del segundo tutor'),
          ('ocupacion', 'La ocupación/profesión del usuario'),
          # ('banco', 'Banco con el que trabaja el usuario'),
          ('gauser__localidad', 'Localidad de residencia'),
          ('gauser__provincia', 'Provincia de residencia'),
          ('gauser__nacimiento', 'La fecha de nacimiento'),
          ('gauser_extra_estudios__grupo__nombre', 'Nombre del grupo'),
          ('gauser_extra_estudios__grupo__tutor__gauser__first_name', 'Nombre del tutor del grupo'),
          ('gauser_extra_estudios__grupo__tutor__gauser__last_name', 'Apellidos del tutor del grupo'),
          )


class CampoF(models.Model):
    filtrado = models.ForeignKey(Filtrado, on_delete=models.CASCADE)
    campo = models.CharField("Campo a mostrar en el resultado", max_length=70, null=True, blank=True, choices=CAMPOS)

    def __str__(self):
        return u'%s (%s)' % (self.filtrado, self.campo)


class ConfigurationUpdate(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    app = models.CharField("Nombre de la aplicación", max_length=80)
    last_update = models.DateTimeField('Fecha y hora de la última actualización', default=timezone.datetime(2000, 1, 1))
    updated = models.BooleanField('La app está actualizada?', default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return u'%s -- %s (%s)' % (self.entidad, self.app, self.updated)

# n='cosa'
# m='valor de la cosa'
#
# exec(n + " = '" + m + "'")
# n
# 'cosa'
# cosa
# 'valor de la cosa'
# exec("%s = '%s'" %(n,m))
