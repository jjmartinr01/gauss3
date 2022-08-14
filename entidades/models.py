# -*- coding: utf-8 -*-

# from __future__ import unicode_literals
import random
import string
import logging
from datetime import date, timedelta, datetime
from difflib import get_close_matches
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import os

from bancos.views import get_banco_from_num_cuenta_bancaria
from cupo.habilitar_permisos import ESPECIALIDADES
from gauss.constantes import *
from gauss.rutas import *
from bancos.models import Banco
from django.db.models import Q
from autenticar.models import Gauser, Permiso, Menu_default

logger = logging.getLogger('django')


def pass_generator(size=6, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


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
        return '%s (%s)' % (self.organization, self.iniciales)


class Ronda(models.Model):
    entidad = models.ForeignKey('Entidad', related_name='rondas', null=True, blank=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre del periodo de funcionamiento", max_length=30)
    inicio = models.DateField("Fecha de inicio de ronda", null=True, blank=True)
    fin = models.DateField("Fecha de finalización de ronda", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Rondas"
        ordering = ['-inicio', 'nombre']

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.entidad.name)


def update_anagrama_entidad(instance, filename):
    nombre = filename.partition('.')
    nombre = str(instance.code) + '_anagrama.' + nombre[2]
    return os.path.join("anagramas/", nombre)


GNS = ((1, 'Entidad'), (2, 'Asociación'), (3, 'Asociación de Padres de Alumnos'),
       (4, 'Asociación de Madres y Padres de Alumnos'), (101, 'Grupo'), (102, 'Grupo Scout'),
       (5, 'Asociación Deportiva'), (103, 'Club Deportivo'), (104, 'IES'), (105, 'Colegio'), (6, 'Federación'))
PLURAL_GN = {1: 'Entidades', 2: 'Asociaciones', 3: 'Asociaciones de Padres de Alumnos',
             4: 'Asociaciones de Madres y Padres de Alumnos', 101: 'Grupos', 102: 'Grupos Scout',
             5: 'Asociaciones Deportivas', 103: 'Clubes Deportivos', 104: 'IES', 105: 'Colegios', 6: 'Federaciones'}

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
    def docconf(self):
        try:
            return DocConfEntidad.objects.get(entidad=self, predeterminado=True)
        except:
            return DocConfEntidad.objects.filter(entidad=self)[0]

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

    @property
    def num_usuarios(self):
        bajas = Alta_Baja.objects.filter(entidad=self, fecha_baja__isnull=False).values_list('gauser__id', flat=True)
        nacimiento_early = date(date.today().year - 100, 1, 1)
        nacimiento_last = date(date.today().year - 3, 12, 31)
        filtro = ~Q(gauser__id__in=bajas) & ~Q(gauser__username='gauss') & Q(ronda=self.ronda) & Q(
            gauser__nacimiento__gte=nacimiento_early) & Q(gauser__nacimiento__lte=nacimiento_last)
        return Gauser_extra.objects.filter(filtro).count()

    def __str__(self):
        return '%s (%s)' % (self.name, self.code)


@receiver(post_save, sender=Entidad, dispatch_uid="entidad_auto_id_creation")
def crea_entidad_auto_id(sender, instance, **kwargs):
    Entidad_auto_id.objects.get_or_create(entidad=instance)


# La siguiente clase/tabla se define para cargar los datos del fichero:
# Racima -> Gestión -> Seguimiento -> Catálogo de consultas -> Centro -> Datos de los centros
class EntidadExtra(models.Model):
    entidad = models.OneToOneField(Entidad, on_delete=models.CASCADE)
    titularidad = models.CharField('Titularidad', max_length=35, blank=True, null=True)
    tipo_centro = models.CharField('Tipo de centro', max_length=75, blank=True, null=True)
    depende_de = models.ForeignKey(Entidad, on_delete=models.SET_NULL, blank=True, null=True, related_name='depende_de')
    comedor = models.BooleanField('¿Tiene servicio de comedor?', default=False)
    transporte = models.BooleanField('¿Tiene servicio de transporte escolar?', default=False)
    director = models.CharField('Nombre del director/a', max_length=75, blank=True, null=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)

    def __str__(self):
        return '%s -> %s, %s' % (self.entidad, self.titularidad, self.tipo_centro)


# La siguiente clase/tabla se define para cargar los datos del fichero:
# Racima -> Gestión -> Seguimiento -> Catálogo de consultas -> Centro -> Datos de los centros
# En dicho archivo una entrada de centro da lugar a varios expedientes:
class EntidadExtraExpediente(models.Model):
    eextra = models.ForeignKey(EntidadExtra, on_delete=models.CASCADE)
    expediente = models.CharField('Tipo de expediente', max_length=100, blank=True, null=True)

    def __str__(self):
        return '%s -> %s' % (self.eextra, self.expediente)


# La siguiente clase/tabla se define para cargar los datos del fichero:
# Racima -> Gestión -> Seguimiento -> Catálogo de consultas -> Centro -> Datos de los centros
# En dicho archivo una entrada de expediente puede dar lugar a varias ofertas:
class EntidadExtraExpedienteOferta(models.Model):
    eeexpediente = models.ForeignKey(EntidadExtraExpediente, on_delete=models.CASCADE)
    oferta = models.CharField('Oferta', max_length=100, blank=True, null=True)

    def __str__(self):
        return '%s -> %s' % (self.eeexpediente, self.oferta)


class DocConfEntidad(models.Model):
    ORIENTATION = (('Portrait', 'Vertical'), ('Landscape', 'Horizontal'))
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    predeterminado = models.BooleanField('¿Es la configuración predeterminada?', default=False)
    nombre = models.CharField('Nombre de la configuración', max_length=100, default='')
    header = models.TextField("Cabecera de página", blank=True, null=True)
    footer = models.TextField("Pie de página", blank=True, null=True)
    pagesize = models.CharField('Tamaño del papel', max_length=5, blank=True, null=True, default='A4')
    margintop = models.CharField('Margen Top', max_length=5, blank=True, null=True, default='52')
    marginright = models.CharField('Margen Right', max_length=5, blank=True, null=True, default='20')
    marginbottom = models.CharField('Margen Bottom', max_length=5, blank=True, null=True, default='10')
    marginleft = models.CharField('Margen Left', max_length=5, blank=True, null=True, default='20')
    encoding = models.CharField('Encoding', max_length=15, blank=True, null=True, default='UTF-8')
    headerspacing = models.CharField('Header Spacing', max_length=5, blank=True, null=True, default='5')
    orientation = models.CharField('Orientación del papel', max_length=12, choices=ORIENTATION, default='Portrait')
    editable = models.BooleanField('¿Es editable el asunto?', default=True)

    @property
    def url_header(self):
        return '%s%s_header_%s.html' % (MEDIA_DOCCONF, self.entidad.code, self.pk)

    @property
    def url_footer(self):
        return '%s%s_footer_%s.html' % (MEDIA_DOCCONF, self.entidad.code, self.pk)

    @property
    def url_pdf(self):
        return '%s%s_pdf_%s.pdf' % (MEDIA_DOCCONF, self.entidad.code, self.pk)

    @property
    def get_opciones(self):
        return {
            'orientation': self.orientation,
            'page-size': self.pagesize,
            'margin-top': self.margintop,
            'margin-right': self.marginright,
            'margin-bottom': self.marginbottom,
            'margin-left': self.marginleft,
            'header-spacing': self.headerspacing,
            'encoding': self.encoding,
            'header-html': self.url_header,
            '--footer-html': self.url_footer,
            'no-outline': None,
            'load-error-handling': 'ignore'
        }

    def __str__(self):
        return '%s (top: %s, bottom: %s, left: %s, right: %s)' % (
            self.entidad, self.margintop, self.marginbottom, self.marginleft, self.marginright)


# Cada vez que se graba un DocConfEntidad se actualizan los html asociados a la cabecera y el pie
@receiver(post_save, sender=DocConfEntidad, dispatch_uid="update_html_header_footer")
def update_html_header_footer(sender, instance, **kwargs):
    if not os.path.exists(os.path.dirname(instance.url_header)):
        os.makedirs(os.path.dirname(instance.url_header))
    html_header = render_to_string('template_cabecera_pie.html', {'html': instance.header})
    with open(instance.url_header, "w") as html_file:
        html_file.write("{0}".format(html_header))
    html_footer = render_to_string('template_cabecera_pie.html', {'html': instance.footer})
    with open(instance.url_footer, "w") as html_file:
        html_file.write("{0}".format(html_footer))


class Subentidad(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre", max_length=250, null=True, blank=True)
    edad_min = models.IntegerField("Edad de acceso", null=True, blank=True)
    edad_max = models.IntegerField("Edad de finalización", null=True, blank=True)
    mensajes = models.BooleanField("Están en lista de mensajería", default=False)
    observaciones = models.TextField("Observaciones", null=True, blank=True)
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
    # clave_ex_editable = models.BooleanField("Se puede modificar la Clave externa?", default=True)
    fecha_expira = models.DateField('Fecha de expiración', default=date(3000, 1, 1))
    creado = models.DateField('Fecha de creación', auto_now_add=True)

    @property
    def rango_edad(self):
        return self.edad_max - self.edad_min

    class Meta:
        verbose_name_plural = "Subentidades"
        ordering = ['parent__nombre', 'nombre']

    def __str__(self):
        return 'Subentidad: %s (%s)' % (self.nombre, self.entidad.name)


class Subsubentidad(models.Model):
    subentidad = models.ForeignKey(Subentidad, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre", max_length=250, null=True, blank=True)
    observaciones = models.TextField("Observaciones", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Subsubentidades"

    def __str__(self):
        return 'Subentidad: %s (%s)' % (self.nombre, self.entidad.name)

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
            # Recuperar el usuario
            ges = Gauser_extra.objects.filter(gauser=self.gauser, ronda__entidad=self.entidad)
            try:
                ge = ges.get(ronda=self.entidad.ronda)
            except:
                ge = ges.order_by('ronda').reverse()[0]
                ge.pk = None
                ge.ronda = self.entidad.ronda
            ge.activo = True
            ge.save()
            # Recuperar tutores
            try:
                tutores = ((ge.tutor1, 'tutor1'), (ge.tutor2, 'tutor2'))
                for tutor, id_tutor in tutores:
                    if tutor:
                        # Comprobar si el tutor es de la ronda actual
                        if tutor.ronda != ge.ronda:
                            try:
                                tutor_encontrado = Gauser_extra.objects.get(gauser=tutor.gauser, ronda=ge.ronda)
                            except:
                                tutor_encontrado = tutor
                                tutor_encontrado.pk = None
                                tutor_encontrado.ronda = ge.ronda
                            tutor_encontrado.activo = True
                            tutor_encontrado.save()
                            setattr(ge, id_tutor, tutor_encontrado)
                            ge.save()
                            # Arreglar la baja del tutor:
                            b, c = Alta_Baja.objects.get_or_create(gauser=tutor_encontrado.gauser, entidad=self.entidad)
                            b.observaciones += "(Autor: %s) Es dado de alta con fecha %s<br>" % (autor, timezone.now())
                            b.fecha_baja = None
                            b.autor = autor
                            b.save()
            except Exception as msg:
                logger.info('%s' % str(msg))
            self.observaciones += "(Autor: %s) Es dado de alta con fecha %s<br>" % (autor, timezone.now())
            self.fecha_baja = None
            self.autor = autor
            self.save()
        return {'ge': ge, 'tutor1': ge.tutor1, 'tutor2': ge.tutor2}

    class Meta:
        verbose_name_plural = "Altas y bajas"

    def __str__(self):
        return '%s (%s) - Alta: %s, Baja: %s' % (
            self.gauser.get_full_name(), self.entidad.name, self.fecha_alta, self.fecha_baja)


NIVELES = ((1, 'Cargo/Perfil de primer nivel'), (2, 'Cargo/Perfil de segundo nivel'),
           (3, 'Cargo/Perfil de tercer nivel'), (4, 'Cargo/Perfil de cuarto nivel'),
           (5, 'Cargo/Perfil de quinto nivel'), (6, 'Cargo/Perfil de sexto nivel'))

# clave_cargo:  'g_inspector_educacion', 'g_docente', 'g_madre_padre', 'g_alumno', 'g_director_general'
#
class Cargo(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    cargo = models.CharField("Cargo", max_length=200, null=True, blank=True)
    permisos = models.ManyToManyField('autenticar.Permiso', blank=True)
    nivel = models.IntegerField('Nivel jerárquico en el organigrama', null=True, blank=True, choices=NIVELES,
                                default=6)
    borrable = models.BooleanField('¿Este cargo se puede borrar?', default=True)
    clave_cargo = models.CharField('Clave asociada al cargo', max_length=30, default='')

    def export_data(self):
        return {'clave_cargo': self.clave_cargo, 'cargo': self.cargo,
                'permisos': [p.code_nombre for p in self.permisos.all()]}

    class Meta:
        ordering = ['entidad', 'clave_cargo', 'nivel', 'cargo']

    def __str__(self):
        return '%s - %s' % (self.cargo, self.entidad)


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
                  ('observaciones', 'Observaciones'), ('num_cuenta_bancaria', 'IBAN cuenta bancaria'))


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
        return '%s %s (%s) - columns: %s' % (self.entidad.name, self.campo, self.required, self.columns)


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
    num_cuenta_bancaria = models.CharField("IBAN", max_length=30, null=True, blank=True, default='')
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
        return '%s %s (%s)' % (self.first_name, self.last_name, self.nacimiento)


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
        return '%s (%s)' % (self.nombre, self.entidad.name)


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_foto(instance, filename):
    nombre = filename.partition('.')
    return os.path.join("fotos/", str(instance.ronda.entidad.code) + '_' + str(instance.id) + '.' + nombre[2])


def pass_generator50():
    return pass_generator(size=50, chars='abcdefghijklmnpqrstuvwxyzABCDEFGHIJKLMNPQRSTUVWXYZ123456789')


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
    # banco = models.ForeignKey(Banco, null=True, blank=True, related_name='entidades', on_delete=models.CASCADE)
    # entidad_bancaria = models.CharField("Entidad bancaria", max_length=50, blank=True, null=True)
    num_cuenta_bancaria = models.CharField("Número de IBAN", max_length=50, blank=True, null=True)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)
    consentimiento = models.BooleanField('Consentimiento datos en gauss', default=False)
    fecha_consentimiento = models.DateTimeField('Fecha y hora firma de consentimiento', blank=True, null=True)
    uso_imagenes = models.BooleanField('Autoriza al uso de imágenes', default=False)
    puesto = models.CharField("Puesto", max_length=175, null=True, blank=True)
    tipo_personal = models.CharField("Tipo de personal", max_length=75, null=True, blank=True)
    jornada_contratada = models.CharField("Tipo de personal", max_length=8, null=True, blank=True)
    creado = models.DateTimeField('Fecha de creación', auto_now_add=True, null=True)

    # tutor_entidad1 = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
    #                                    related_name='tutor_entidad')
    # tutor_entidad2 = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
    #                                    related_name='cotutor')

    @property
    def banco(self):
        return get_banco_from_num_cuenta_bancaria(self.num_cuenta_bancaria)

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
        p_ids = self.permisos_list.values_list('pk', flat=True)
        return p_ids

    class Meta:
        verbose_name_plural = "Datos extra de un usuario (Gauser_extra)"
        ordering = ['gauser__last_name']

    def __str__(self):
        return '%s -- %s' % (self.gauser, self.ronda)


class GE_extra_field(models.Model):
    ge = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    code = models.CharField('Code', max_length=50, blank=True, null=True)
    name = models.CharField('Nombre', max_length=50, blank=True, null=True)
    value = models.TextField('Valor', blank=True, null=True)

    def __str__(self):
        return '%s -- %s - %s' % (self.ge, self.code, self.name)


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
        eai_auto = instance.ronda.entidad.entidad_auto_id.auto
    except:
        eai = Entidad_auto_id.objects.create(entidad=instance.ronda.entidad)
        eai_auto = eai.auto
    if eai_auto:
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
        return '%s -- %s -- %s-%s-%s' % (self.entidad, self.auto, self.prefijo, self.lexema, self.sufijo)


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
        return 'N%s - %s.%s --> %s --> %s (%s)%s' % (
            self.menu_default.nivel, self.pos, self.menu_default.code_menu,
            self.menu_default.texto_menu, self.texto_menu, self.entidad.code, parent)


########################### CONFIGURACIÓN FILTROS ###########################

# class FiltroEntidad(models.Model):
#     TIPOSVALOR = (('str', 'Cadena de texto'), ('date', 'Fecha'), ('datetime', 'Fecha y hora'), ('int', 'Entero'),
#                   ('float', 'Decimal'),)
#     entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
#     clase = models.CharField("Clase sobre la que se hace el queryset", max_length=30, default='')
#     q = models.CharField("Query", max_length=75, default='')
#     nombre = models.CharField("Nombre del filtro", max_length=75, default='')
#     tipo_valor = models.CharField("Tipo de valor", max_length=15, choices=TIPOSVALOR)
#
#     def __str__(self):
#         return '%s - %s - %s' % (self.entidad, self.clase, self.nombre)
#
#
# class CampoFiltroEntidad(models.Model):
#     entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
#     clase = models.CharField("Clase sobre la que se hace el queryset", max_length=30, default='')
#     campo = models.CharField("Campo", max_length=75, default='')
#     nombre = models.CharField("Nombre del campo", max_length=75, default='')
#
#     def __str__(self):
#         return '%s - %s - %s' % (self.entidad, self.clase, self.campo)


class Filtrado(models.Model):
    propietario = models.ForeignKey(Gauser_extra, on_delete=models.SET_NULL, null=True, blank=True)
    nombre = models.CharField("Nombre del filtro", max_length=200)
    operacion = models.CharField("Operaciones de filtrado", max_length=40, null=True, blank=True)

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.propietario.entidad.name)


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
        return '%s (%s)' % (self.filtrado, self.filtro)


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
        return '%s (%s)' % (self.filtrado, self.campo)


########################### FIN CONFIGURACIÓN FILTROS ###########################


class ConfigurationUpdate(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    app = models.CharField("Nombre de la aplicación", max_length=80)
    last_update = models.DateTimeField('Fecha y hora de la última actualización', default=timezone.datetime(2000, 1, 1))
    updated = models.BooleanField('La app está actualizada?', default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return '%s -- %s (%s)' % (self.entidad, self.app, self.updated)


def update_fichero_carga_masiva(instance, filename):
    nombre = filename.partition('.')
    try:
        nombre = '%s_%s.%s' % (str(instance.ronda.entidad.code), pass_generator(), nombre[2])
    except:
        nombre = '%s_%s.%s' % (str(instance.g_e.ronda.entidad.code), pass_generator(), nombre[2])
    return os.path.join("carga_masiva/", nombre)



class CargaMasiva(models.Model):
    TIPOS = (('EXCEL', 'Usuarios cargados desde Racima'),
             ('PENDIENTES', 'Alumnos con materias pendientes cargados desde Racima'),
             ('HORARIOXLS', 'Sesiones cargadas desde el archivo excel de Racima'),
             ('CENTROSRACIMA', 'Consulta -> Centro -> Datos de los centros'),
             ('PLANTILLAXLS', 'Sesiones cargadas desde el archivo excel de Racima'),
             ('DOCENTES_RACIMA', 'Docentes cargados desde consulta general'))
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE, blank=True, null=True)
    # Persona que ha realizado la carga masiva
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.SET_NULL, blank=True, null=True)
    fichero = models.FileField("Fichero con datos", upload_to=update_fichero_carga_masiva, blank=True)
    tipo = models.CharField("Tipo de archivo", max_length=15, choices=TIPOS)
    incidencias = models.TextField("Incidencias producidas", blank=True, null=True, default='')
    cargado = models.BooleanField("¿Se ha cargado el archivo?", default=False)
    error = models.BooleanField("¿Se ha producido un error en la carga del archivo archivo?", default=False)
    creado = models.DateField('Fecha de creación', auto_now_add=True, blank=True, null=True)
    log = models.TextField("Log de los incidentes durante la carga", blank=True, null=True, default='')

    class Meta:
        verbose_name_plural = "Cargas Masivas"
        ordering = ['ronda']

    @property
    def dias_autoborrado(self):
        dias_para_autoborrado = 90
        dias = (date.today() - self.creado).days
        return dias_para_autoborrado - dias
    def __str__(self):
        if self.ronda:
            return 'Cargado: %s -- %s -> %s' % (self.cargado, self.creado, self.g_e)
        else:
            return 'Cargado: %s (%s -> %s)' % (self.cargado, self.creado, self.g_e)



# n='cosa'
# m='valor de la cosa'
#
# exec(n + " = '" + m + "'")
# n
# 'cosa'
# cosa
# 'valor de la cosa'
# exec("%s = '%s'" %(n,m))


class EnlaceGE(models.Model):
    usuario = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    code = models.CharField("Código", max_length=50, default=pass_generator50)
    enlace = models.CharField("Enlace", max_length=100)
    deadline = models.DateField('Fecha límite de validez')

    def __str__(self):
        return '%s -- %s (%s)' % (self.enlace, self.usuario, self.deadline)

###############################################################################
###############################################################################
###############################################################################

# class PuestoRacima(models.Model):
#     code = models.CharField('Código del cuerpo', max_length=10)
#     nombre = models.CharField('Nombre del cuerpo', max_length=100)
#
#     def __str__(self):
#         return '%s - %s' % (self.code, self.nombre)

class Cuerpo_funcionario(models.Model):
    code = models.CharField('Código del cuerpo', max_length=10)
    nombre = models.CharField('Nombre del cuerpo', max_length=100)

    def __str__(self):
        return '%s - %s' % (self.code, self.nombre)


class Especialidad_funcionario(models.Model):
    cuerpo = models.ForeignKey(Cuerpo_funcionario, blank=True, null=True, on_delete=models.CASCADE)
    code = models.CharField('Código de la especialidad', max_length=10)
    nombre = models.CharField('Nombre de la especialidad', max_length=100)

    def __str__(self):
        return '%s - %s (%s)' % (self.code, self.nombre, self.cuerpo)

def crea_cuerpos_especialidades():
    CUERPOS = (("590", "PROFESORES DE ENSEÑANZA SECUNDARIA"),
               ("511", "CATEDRÁTICOS DE ENSEÑANZA SECUNDARIA"),
               ("591", "PROFESORES TÉCNICOS DE FORMACIÓN PROFESIONAL"),
               ("592", "PROFESORES DE ESCUELAS OFICIALES DE IDIOMAS"),
               ("512", "CATEDRÁTICOS DE ESCUELAS OFICIALES DE IDIOMAS"),
               ("593", "CATEDRÁTICOS DE MÚSICA Y ARTES ESCÉNICAS"),
               ("594", "PROFESORES DE MÚSICA Y ARTES ESCÉNICAS"),
               ("595", "PROFESORES DE ARTES PLÁSTICAS Y DISEÑO"),
               ("513", "CATEDRÁTICOS DE ARTES PLÁSTICAS Y DISEÑO"),
               ("596", "MAESTROS DE TALLER DE ARTES PLÁSTICAS Y DISEÑO"),
               ("597", "MAESTROS"),
               ("510", "INSPECTORES DE EDUCACIÓN"))

    ESPECIALIDADES = (("001", "Filosofía", "590"),
                      ("002", "Griego", "590"),
                      ("003", "Latín", "590"),
                      ("004", "Lengua Castellana y Literatura", "590"),
                      ("005", "Geografía e Historia", "590"),
                      ("006", "Matemáticas", "590"),
                      ("007", "Física y Química", "590"),
                      ("008", "Biología y Geología", "590"),
                      ("009", "Dibujo", "590"),
                      ("010", "Francés", "590"),
                      ("011", "Inglés", "590"),
                      ("012", "Alemán", "590"),
                      ("013", "Italiano", "590"),
                      ("016", "Música", "590"),
                      ("017", "Educación Física", "590"),
                      ("018", "Orientación educativa (*)", "590"),
                      ("019", "Tecnología", "590"),
                      ("061", "Economía", "590"),
                      ("101", "Administración de Empresas", "590"),
                      ("102", "Análisis y Química Industrial", "590"),
                      ("103", "Asesoría y Procesos de Imagen Personal", "590"),
                      ("104", "Construcciones Civiles y Edificación", "590"),
                      ("105", "Formación y Orientación Laboral", "590"),
                      ("106", "Hostelería y Turismo", "590"),
                      ("107", "Informática", "590"),
                      ("108", "Intervención Socio-comunitaria", "590"),
                      ("109", "Navegación e Instalaciones Marinas", "590"),
                      ("110", "Organización y Gestión Comercial", "590"),
                      ("111", "Organización y Procesos de Mantenimiento de Vehículos", "590"),
                      ("112", "Organización y Proyectos de Fabricación Mecánica", "590"),
                      ("113", "Organización y Proyectos de Sistemas Energéticos", "590"),
                      ("114", "Procesos de Cultivo Acuícola", "590"),
                      ("115", "Procesos de Producción Agraria", "590"),
                      ("116", "Procesos en la Industria Alimentaria", "590"),
                      ("117", "Procesos Diagnósticos Clínicos y Procedimientos Ortoprotésicos", "590"),
                      ("118", "Procesos Sanitarios", "590"),
                      ("119", "Procesos y Medios de Comunicación", "590"),
                      ("120", "Procesos y Productos de Textil, Confección y Piel", "590"),
                      ("121", "Procesos y Productos de Vidrio y Cerámica", "590"),
                      ("122", "Procesos y Productos en Artes Gráficas", "590"),
                      ("123", "Procesos y Productos en Madera y Mueble", "590"),
                      ("124", "Sistemas Electrónicos", "590"),
                      ("125", "Sistemas Electrotécnicos y Automáticos", "590"),
                      ("803", "Cultura Clásica", "590"),
                      ("001", "Filosofía", "511"),
                      ("002", "Griego", "511"),
                      ("003", "Latín", "511"),
                      ("004", "Lengua Castellana y Literatura", "511"),
                      ("005", "Geografía e Historia", "511"),
                      ("006", "Matemáticas", "511"),
                      ("007", "Física y Química", "511"),
                      ("008", "Biología y Geología", "511"),
                      ("009", "Dibujo", "511"),
                      ("010", "Francés", "511"),
                      ("011", "Inglés", "511"),
                      ("012", "Alemán", "511"),
                      ("013", "Italiano", "511"),
                      ("016", "Música", "511"),
                      ("017", "Educación Física", "511"),
                      ("018", "Orientación educativa (*)", "511"),
                      ("019", "Tecnología", "511"),
                      ("061", "Economía", "511"),
                      ("101", "Administración de Empresas", "511"),
                      ("102", "Análisis y Química Industrial", "511"),
                      ("103", "Asesoría y Procesos de Imagen Personal", "511"),
                      ("104", "Construcciones Civiles y Edificación", "511"),
                      ("105", "Formación y Orientación Laboral", "511"),
                      ("106", "Hostelería y Turismo", "511"),
                      ("107", "Informática", "511"),
                      ("108", "Intervención Socio-comunitaria", "511"),
                      ("109", "Navegación e Instalaciones Marinas", "511"),
                      ("110", "Organización y Gestión Comercial", "511"),
                      ("111", "Organización y Procesos de Mantenimiento de Vehículos", "511"),
                      ("112", "Organización y Proyectos de Fabricación Mecánica", "511"),
                      ("113", "Organización y Proyectos de Sistemas Energéticos", "511"),
                      ("114", "Procesos de Cultivo Acuícola", "511"),
                      ("115", "Procesos de Producción Agraria", "511"),
                      ("116", "Procesos en la Industria Alimentaria", "511"),
                      ("117", "Procesos Diagnósticos Clínicos y Procedimientos Ortoprotésicos", "511"),
                      ("118", "Procesos Sanitarios", "511"),
                      ("119", "Procesos y Medios de Comunicación", "511"),
                      ("120", "Procesos y Productos de Textil, Confección y Piel", "511"),
                      ("121", "Procesos y Productos de Vidrio y Cerámica", "511"),
                      ("122", "Procesos y Productos en Artes Gráficas", "511"),
                      ("123", "Procesos y Productos en Madera y Mueble", "511"),
                      ("124", "Sistemas Electrónicos", "511"),
                      ("125", "Sistemas Electrotécnicos y Automáticos", "511"),
                      ("803", "Cultura Clásica", "511"),
                      ("201", "Cocina y Pastelería", "591"),
                      ("202", "Equipos Electrónicos", "591"),
                      ("203", "Estética", "591"),
                      ("204", "Fabricación e Instalación de Carpintería y Mueble", "591"),
                      ("205", "Instalaciones y Mantenimiento de Equipos Térmicos y de Fluidos", "591"),
                      ("206", "Instalaciones Electrotécnicas", "591"),
                      ("207", "Instalaciones y Equipos de Cría y Cultivo", "591"),
                      ("208", "Laboratorio", "591"),
                      ("209", "Mantenimiento de Vehículos", "591"),
                      ("210", "Máquinas, Servicios y Producción", "591"),
                      ("211", "Mecanizado y Mantenimiento de Máquinas", "591"),
                      ("212", "Oficina de Proyectos de Construcción", "591"),
                      ("213", "Oficina de Proyectos y Fabricación Mecánica", "591"),
                      ("214", "Operaciones y Equipos de Elaboración de Productos Alimentarios", "591"),
                      ("215", "Operaciones de Procesos", "591"),
                      ("216", "Operaciones y Equipos de Producción Agraria", "591"),
                      ("217", "Patronaje y Confección", "591"),
                      ("218", "Peluquería", "591"),
                      ("219", "Procedimientos de Diagnóstico Clínico y Ortoprotésico", "591"),
                      ("220", "Procedimientos Sanitarios y Asistenciales", "591"),
                      ("221", "Procesos Comerciales", "591"),
                      ("222", "Procesos de Gestión Administrativa", "591"),
                      ("223", "Producción en Artes Gráficas", "591"),
                      ("224", "Producción Textil y Tratamiento Físico-Químicos", "591"),
                      ("225", "Servicios a la Comunidad", "591"),
                      ("226", "Servicios de Restauración", "591"),
                      ("227", "Sistemas y Aplicaciones Informáticos", "591"),
                      ("228", "Soldadura", "591"),
                      ("229", "Técnicas y Procedimientos de Imagen y Sonido", "591"),
                      ("001", "Alemán", "592"),
                      ("002", "Árabe", "592"),
                      ("006", "Español", "592"),
                      ("008", "Francés", "592"),
                      ("010", "Griego", "592"),
                      ("011", "Inglés", "592"),
                      ("012", "Italiano", "592"),
                      ("013", "Japonés", "592"),
                      ("015", "Portugués", "592"),
                      ("017", "Ruso", "592"),
                      ("001", "Alemán", "512"),
                      ("002", "Árabe", "512"),
                      ("006", "Español", "512"),
                      ("008", "Francés", "512"),
                      ("010", "Griego", "512"),
                      ("011", "Inglés", "512"),
                      ("012", "Italiano", "512"),
                      ("013", "Japonés", "512"),
                      ("015", "Portugués", "512"),
                      ("017", "Ruso", "512"),
                      ("002", "Armonía y Melodía Acompañada", "593"),
                      ("003", "Arpa", "593"),
                      ("005", "Ballet Clásico", "593"),
                      ("006", "Canto", "593"),
                      ("007", "Caracterización", "593"),
                      ("008", "Clarinete", "593"),
                      ("009", "Clave", "593"),
                      ("010", "Composición e Instrumentación", "593"),
                      ("013", "Conjunto Coral e Instrumental", "593"),
                      ("014", "Contrabajo", "593"),
                      ("015", "Contrapunto y Fuga", "593"),
                      ("017", "Danza Española", "593"),
                      ("021", "Dirección Coros y Conjunto Coral", "593"),
                      ("023", "Dirección de Orquesta y Conjunto Instrumental", "593"),
                      ("024", "Dramaturgia", "593"),
                      ("026", "Escenografía", "593"),
                      ("027", "Esgrima", "593"),
                      ("028", "Estética e Historia de la Música, Cultura y Arte", "593"),
                      ("029", "Expresión Corporal", "593"),
                      ("030", "Fagot", "593"),
                      ("031", "Flauta de Pico", "593"),
                      ("032", "Flauta Travesera", "593"),
                      ("035", "Guitarra", "593"),
                      ("037", "Historia de la Cultura y del Arte", "593"),
                      ("038", "Historia de la Literatura Dramática", "593"),
                      ("042", "Instrumentos de Pulso y Púa", "593"),
                      ("043", "Interpretación", "593"),
                      ("050", "Música de Cámara", "593"),
                      ("051", "Musicología", "593"),
                      ("052", "Oboe", "593"),
                      ("053", "Órgano", "593"),
                      ("055", "Ortofonía y Dicción", "593"),
                      ("058", "Percusión", "593"),
                      ("059", "Piano", "593"),
                      ("061", "Repentización, Transposición Instrumental y Acompañamiento", "593"),
                      ("066", "Saxofón", "593"),
                      ("068", "Solfeo y Teoría de la Música", "593"),
                      ("072", "Trombón", "593"),
                      ("074", "Trompa", "593"),
                      ("075", "Trompeta", "593"),
                      ("076", "Tuba", "593"),
                      ("077", "Viola", "593"),
                      ("078", "Violín", "593"),
                      ("079", "Violoncello", "593"),
                      ("402", "Arpa", "594"),
                      ("403", "Canto", "594"),
                      ("404", "Clarinete", "594"),
                      ("405", "Clave", "594"),
                      ("406", "Contrabajo", "594"),
                      ("407", "Coro", "594"),
                      ("408", "Fagot", "594"),
                      ("410", "Flauta Travesera", "594"),
                      ("411", "Flauta de Pico", "594"),
                      ("412", "Fundamentos de Composición", "594"),
                      ("414", "Guitarra", "594"),
                      ("415", "Guitarra Flamenca", "594"),
                      ("416", "Historia de la Música", "594"),
                      ("417", "Instrumento de Cuerda Pulsada del Renacimiento y del Barroco", "594"),
                      ("419", "Oboe", "594"),
                      ("420", "Órgano", "594"),
                      ("421", "Orquesta", "594"),
                      ("422", "Percusión", "594"),
                      ("423", "Piano", "594"),
                      ("424", "Saxofón", "594"),
                      ("426", "Trombón", "594"),
                      ("427", "Trompa", "594"),
                      ("428", "Trompeta", "594"),
                      ("429", "Tuba", "594"),
                      ("431", "Viola", "594"),
                      ("432", "Viola da Gamba", "594"),
                      ("433", "Violín", "594"),
                      ("434", "Violoncello", "594"),
                      ("435", "Danza Española", "594"),
                      ("436", "Danza Clásica", "594"),
                      ("437", "Danza Contemporánea", "594"),
                      ("438", "Flamenco", "594"),
                      ("439", "Historia de la Danza", "594"),
                      ("440", "Acrobacia", "594"),
                      ("441", "Canto Aplicado al Arte Dramático", "594"),
                      ("442", "Caracterización e Indumentaria", "594"),
                      ("443", "Danza Aplicada al Arte Dramático", "594"),
                      ("444", "Dicción y Expresión Oral", "594"),
                      ("445", "Dirección Escénica", "594"),
                      ("446", "Dramaturgia", "594"),
                      ("447", "Esgrima", "594"),
                      ("448", "Espacio Escénico", "594"),
                      ("449", "Expresión Corporal", "594"),
                      ("450", "Iluminación", "594"),
                      ("451", "Interpretación", "594"),
                      ("454", "Interpretación en el Teatro del Gesto", "594"),
                      ("455", "Literatura Dramática", "594"),
                      ("456", "Técnicas Escénicas", "594"),
                      ("457", "Técnicas Gráficas", "594"),
                      ("458", "Teoría e Historia del Arte", "594"),
                      ("460", "Lenguaje Musical", "594"),
                      ("501", "Cerámica", "513"),
                      ("502", "Conservación y Restauración de Materiales Arqueológicos", "513"),
                      ("503", "Conservación y Restauración de Obras Escultóricas", "513"),
                      ("504", "Conservación y Restauración de Obras Pictóricas", "513"),
                      ("505", "Conservación y Restauración de Textiles", "513"),
                      ("506", "Conservación y Restauración del Documento Gráfico", "513"),
                      ("507", "Dibujo Artístico y Color", "513"),
                      ("508", "Dibujo Técnico", "513"),
                      ("509", "Diseño de Interiores", "513"),
                      ("510", "Diseño de Moda", "513"),
                      ("511", "Diseño de Productos", "513"),
                      ("512", "Diseño Gráfico", "513"),
                      ("513", "Diseño Textil", "513"),
                      ("514", "Edición de Arte", "513"),
                      ("515", "Fotografía", "513"),
                      ("516", "Historia del Arte", "513"),
                      ("517", "Joyería y Orfebrería", "513"),
                      ("518", "Materiales y Tecnología: Cerámica y Vidrio", "513"),
                      ("519", "Materiales y Tecnología: Conservación y Restauración", "513"),
                      ("520", "Materiales y Tecnología: Diseño", "513"),
                      ("521", "Medios Audiovisuales", "513"),
                      ("522", "Medios Informáticos", "513"),
                      ("523", "Organización Industrial y Legislación", "513"),
                      ("524", "Vidrio", "513"),
                      ("525", "Volumen", "513"),
                      ("501", "Cerámica", "595"),
                      ("502", "Conservación y Restauración de Materiales Arqueológicos", "595"),
                      ("503", "Conservación y Restauración de Obras Escultóricas", "595"),
                      ("504", "Conservación y Restauración de Obras Pictóricas", "595"),
                      ("505", "Conservación y Restauración de Textiles", "595"),
                      ("506", "Conservación y Restauración del Documento Gráfico", "595"),
                      ("507", "Dibujo Artístico y Color", "595"),
                      ("508", "Dibujo Técnico", "595"),
                      ("509", "Diseño de Interiores", "595"),
                      ("510", "Diseño de Moda", "595"),
                      ("511", "Diseño de Productos", "595"),
                      ("512", "Diseño Gráfico", "595"),
                      ("513", "Diseño Textil", "595"),
                      ("514", "Edición de Arte", "595"),
                      ("515", "Fotografía", "595"),
                      ("516", "Historia del Arte", "595"),
                      ("517", "Joyería y Orfebrería", "595"),
                      ("518", "Materiales y Tecnología: Cerámica y Vidrio", "595"),
                      ("519", "Materiales y Tecnología: Conservación y Restauración", "595"),
                      ("520", "Materiales y Tecnología: Diseño", "595"),
                      ("521", "Medios Audiovisuales", "595"),
                      ("522", "Medios Informáticos", "595"),
                      ("523", "Organización Industrial y Legislación", "595"),
                      ("524", "Vidrio", "595"),
                      ("525", "Volumen", "595"),
                      ("601", "Artesanía y Ornamentación con elementos vegetales", "596"),
                      ("602", "Bordados y Encajes", "596"),
                      ("603", "Complementos y Accesorios", "596"),
                      ("604", "Dorado y Policromía", "596"),
                      ("605", "Ebanistería Artística", "596"),
                      ("606", "Encuadernación Artística", "596"),
                      ("607", "Esmaltes", "596"),
                      ("608", "Fotografía y Procesos de Reproducción", "596"),
                      ("609", "Modelismo y Maquetismo", "596"),
                      ("610", "Moldes y Reproducciones", "596"),
                      ("611", "Musivaria", "596"),
                      ("612", "Talla en Piedra y Madera", "596"),
                      ("613", "Técnicas Cerámicas", "596"),
                      ("614", "Técnicas de Grabado y Estampación", "596"),
                      ("615", "Técnicas de Joyería y Bisutería", "596"),
                      ("616", "Técnicas de Orfebrería y Platería", "596"),
                      ("617", "Técnicas de Patronaje y Confección", "596"),
                      ("618", "Técnicas del Metal", "596"),
                      ("619", "Técnicas Murales", "596"),
                      ("620", "Técnicas Textiles", "596"),
                      ("621", "Técnicas Vidrieras", "596"),
                      ("031", "Educación Infantil", "597"),
                      ("032", "Inglés", "597"),
                      ("033", "Francés", "597"),
                      ("034", "Educación Física", "597"),
                      ("035", "Música", "597"),
                      ("036", "Pedagogía Terapéutica", "597"),
                      ("037", "Audición y Lenguaje", "597"),
                      ("038", "Educación Primaria", "597"))
    for c in CUERPOS:
        Cuerpo_funcionario.objects.get_or_create(code=c[0], nombre=c[1])
    for e in ESPECIALIDADES:
        cuerpo = Cuerpo_funcionario.objects.get(code=e[2])
        Especialidad_funcionario.objects.get_or_create(code=e[0], nombre=e[1], cuerpo=cuerpo)

class Departamento(models.Model):
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE, related_name='get_departamentos')
    nombre = models.CharField('Denominación', max_length=310)
    abreviatura = models.CharField("Abreviatura", max_length=10, blank=True, null=True)
    didactico = models.BooleanField("Es un departamento didáctico", default=True)
    fp = models.BooleanField("Es una familia profesional", default=False)
    horas_coordinador = models.IntegerField("Número de horas de coordinación para el jefe de departamento", default=3)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
    orden = models.IntegerField("Orden en el listado de departamentos", default=100)
    # miembros = models.ManyToManyField(Gauser_extra, blank=True)

    def save(self, *args, **kwargs):
        posiciones = {'Griego': 2, 'Orientación': 20, 'Tecnología': 14, 'Matemáticas': 6, 'Educación Física': 13,
                      'Filosofía': 1, 'Geografía e Historia': 5, 'Inglés': 11, 'Formación y Orientación Laboral': 17,
                      'Lengua Castellana y Literatura': 4, 'Ciencias Naturales': 8, 'Latín': 3, 'Artes Plásticas': 9,
                      'Física y Química': 7, 'Música': 12, 'Economía': 15, 'Cultura Clásica': 16, 'Francés': 10}
        nombre_departamento = get_close_matches(self.nombre, posiciones, 1)
        if len(nombre_departamento) > 0:
            self.orden = posiciones[nombre_departamento[0]]
        else:
            self.orden = 100
        super(Departamento, self).save(*args, **kwargs)

    @property
    def entidad(self):
        return self.ronda.entidad

    class Meta:
        verbose_name_plural = "Departamentos"
        ordering = ['orden', 'nombre']

    def __str__(self):
        return '%s - %s - %s' % (self.clave_ex, self.nombre, self.ronda)

class MiembroDepartamento(models.Model):
    PUESTOS = (('M', 'Maestro'), ('S', 'Profesor de Secundaria'), ('C', 'Catedrático'), ('T', 'Profesor Técnico'))
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(Especialidad_funcionario, on_delete=models.CASCADE, blank=True, null=True)
    puesto = models.CharField('Contiene el campo clave_cargo de la clase Cargo', blank=True, null=True, max_length=250)

    def get_puesto(self):
        return Cargo.objects.get(entidad=self.departamento.ronda.entidad, clave_cargo=self.puesto)

    def __str__(self):
        return '%s - dep: %s - puesto: %s' % (self.g_e, self.departamento.nombre, self.get_puesto())


class EspecialidadDocenteBasica(models.Model):
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE)
    puesto = models.CharField('Denominación puesto', max_length=310)
    clave_ex = models.CharField("Clave externa", max_length=15, blank=True, null=True)
    orden = models.IntegerField("Orden en el listado de departamentos", default=100)

    def save(self, *args, **kwargs):
        posiciones = {a[1]: int(a[0]) for a in ESPECIALIDADES}
        # Se obtiene una lista del tipo:
        # posiciones = {'Griego': 2, 'Orientación Educativa': 20, 'Tecnología': 14, 'Educación Física': 13,
        #               'Filosofía': 1, 'Geografía e Historia': 5, 'Inglés': 11, 'Formación y Orientación Laboral': 17,
        #               'Lengua Castellana y Literatura': 4, 'Ciencias Naturales': 8, 'Latín': 3, 'Artes Plásticas': 9,
        #               'Física y Química': 7, 'Música': 16, 'Economía': 15, 'Cultura Clásica': 16, 'Francés': 10,
        #               'Dibujo': 9, 'Biología y Geología': 8, 'Alemán': 12, 'Apoyo al Área de Ciencias o Tecnología': 60,
        #               'Apoyo al Área de Lengua y Ciencias Sociales': 61, 'Pedagogía Terapéutica': 36, 'Italiano': 13,
        #               'Audición y Lenguaje': 37, 'Educación Infantil': 31, 'Educación Primaria': 32, 'Matemáticas': 6}
        nombre_especialidad = get_close_matches(self.puesto, posiciones, 1)
        if len(nombre_especialidad) > 0:
            self.orden = posiciones[nombre_especialidad[0]]
        else:
            self.orden = 800
        super(EspecialidadDocenteBasica, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Especialidades docentes básicas"
        ordering = ['orden', 'puesto']

    def __str__(self):
        return '%s - %s - %s' % (self.clave_ex, self.puesto, self.ronda)

class MiembroEDB(models.Model):
    edb = models.ForeignKey(EspecialidadDocenteBasica, on_delete=models.CASCADE)
    g_e = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)

    def __str__(self):
        return '%s - g_e: %s' % (self.edb, self.g_e)
