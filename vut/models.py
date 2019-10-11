# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from PIL import Image
import random
import os

from django.db import models
from django.utils.timezone import now, timedelta
from django.core.files.storage import FileSystemStorage

from autenticar.models import Permiso, Gauser
from entidades.models import Entidad, Gauser_extra
from gauss.funciones import pass_generator

# Create your models here.

PAISES = (('A9401AAAAA', 'AFGANISTAN'), ('A9399AAAAA', 'AFRICA'), ('A9102AAAAA', 'ALBANIA'), ('A9103AAAAA', 'ALEMANIA'),
          ('A9299AAAAA', 'AMERICA'), ('A9133AAAAA', 'ANDORRA'), ('A9301AAAAA', 'ANGOLA'),
          ('A9255AAAAA', 'ANTIGUA BARBUDA'), ('A9200AAAAA', 'ANTILLAS NEERLANDESAS'), ('A9600AAAAA', 'APATRIDA'),
          ('A9403AAA1A', 'ARABIA SAUDITA'), ('A9304AAAAA', 'ARGELIA'), ('A9202AAAAA', 'ARGENTINA'),
          ('A9142AAAAA', 'ARMENIA'), ('A9257AAAAA', 'ARUBA'), ('A9499AAAAA', 'ASIA'), ('A9500AAAAA', 'AUSTRALIA'),
          ('A9104AAAAA', 'AUSTRIA'), ('A9143AAA2A', 'AZERBAYAN'), ('A9203AAAAA', 'BAHAMAS'), ('A9405AAAAA', 'BAHREIN'),
          ('A9432AAAAA', 'BANGLADESH'), ('A9205AAAAA', 'BARBADOS'), ('A9105AAAAA', 'BELGICA'), ('A9207AAAAA', 'BELICE'),
          ('A9407AAAAA', 'BHUTAN'), ('A9144AAAAA', 'BIELORRUSIA'), ('A9204AAAAA', 'BOLIVIA'),
          ('A9156AAAAA', 'BOSNIA HERZEGOVINA'), ('A9305AAAAA', 'BOTSWANA'), ('A9206AAAAA', 'BRASIL'),
          ('A9409AAAAA', 'BRUNEI'), ('A9134AAAAA', 'BULGARIA'), ('A9303AAAAA', 'BURKINA FASO'),
          ('A9321AAAAA', 'BURUNDI'), ('A9315AAAAA', 'CABO VERDE'), ('A9402AAAAA', 'CAMBOYA'), ('A9308AAAAA', 'CAMERUN'),
          ('A9208AAAAA', 'CANADA'), ('A9372AAAAA', 'CHAD'), ('A9106AAAAD', 'CHECOSLOVAQUIA'), ('A9210AAAAA', 'CHILE'),
          ('A9406AAAAA', 'CHINA'), ('A9107AAAAA', 'CHIPRE'), ('A9212AAAAA', 'COLOMBIA'), ('A9311AAAAA', 'COMORES'),
          ('A9460AAAAA', 'COREA NORTE'), ('A9410AAAAA', 'COREA SUR'), ('A9314AAAAA', 'COSTA MARFIL'),
          ('A9214AAAAA', 'COSTA RICA'), ('A9140AAAAA', 'CROACIA'), ('A9216AAAAA', 'CUBA'), ('A9258AAAAA', 'CURAÇAO'),
          ('A9108AAAAA', 'DINAMARCA'), ('A9317AAAAA', 'DJIBOUTI'), ('A9217AAAAA', 'DOMINICA'),
          ('A9222AAAAA', 'ECUADOR'), ('A9300AAAAA', 'EGIPTO'), ('A9429AAAAA', 'EMIRATOS ARABES UNIDOS'),
          ('A9384AAAAA', 'ERITREA'), ('A9158AAAAA', 'ESLOVAQUIA'), ('A9141AAAAA', 'ESLOVENIA'),
          ('A9109AAAAA', 'ESPAÑA'), ('A9525AAA1A', 'ESTADOS FEDERADOS MICRONESIA'),
          ('A9224AAA1A', 'ESTADOS UNIDOS AMERICA'), ('A9137AAAAA', 'ESTONIA'), ('A9318AAAAA', 'ETIOPIA'),
          ('A9199AAAAA', 'EUROPA'), ('A9396AAAAA', 'FERNANDO POO'), ('A9550AAAAA', 'FIDJI'),
          ('A9411AAAAA', 'FILIPINAS'), ('A9110AAAAA', 'FINLANDIA'), ('A9111AAAAA', 'FRANCIA'), ('A9320AAAAA', 'GABON'),
          ('A9323AAAAA', 'GAMBIA'), ('A9145AAAAA', 'GEORGIA'), ('A9322AAAAA', 'GHANA'), ('A9113AAAAA', 'GRECIA'),
          ('A9228AAAAA', 'GUATEMALA'), ('A9325AAA3A', 'GUINEA'), ('A9328AAA1A', 'GUINEA BISSAU'),
          ('A9324AAAAA', 'GUINEA ECUATORIAL'), ('A9225AAAAA', 'GUYANA'), ('A9230AAAAA', 'HAITI'),
          ('A9232AAAAA', 'HONDURAS'), ('A9462AAAAA', 'HONG KONG CHINO'), ('A9114AAAAA', 'HUNGRIA'),
          ('A9395AAAAA', 'IFNI'), ('A9412AAAAA', 'INDIA'), ('A9414AAAAA', 'INDONESIA'), ('A9413AAAAA', 'IRAK'),
          ('A9415AAAAA', 'IRAN'), ('A9115AAAAA', 'IRLANDA'), ('A9116AAAAA', 'ISLANDIA'),
          ('A9518AAAAA', 'ISLAS MARIANAS NORTE'), ('A9520AAAAA', 'ISLAS MARSHALL'), ('A9551AAA1A', 'ISLAS SALOMON'),
          ('A9417AAAAA', 'ISRAEL'), ('A9117AAAAA', 'ITALIA'), ('A9233AAAAA', 'JAMAICA'), ('A9416AAAAA', 'JAPON'),
          ('A9419AAAAA', 'JORDANIA'), ('A9465AAAAA', 'KAZAJSTAN'), ('A9336AAAAA', 'KENIA'), ('A9501AAAAA', 'KIRIBATI'),
          ('A9421AAAAA', 'KUWAIT'), ('A9418AAAAA', 'LAOS'), ('A9337AAAAA', 'LESOTHO'), ('A9138AAAAA', 'LETONIA'),
          ('A9423AAAAA', 'LIBANO'), ('A9342AAAAA', 'LIBERIA'), ('A9344AAAAA', 'LIBIA'), ('A9118AAAAA', 'LIECHTENSTEIN'),
          ('A9139AAAAA', 'LITUANIA'), ('A9119AAAAA', 'LUXEMBURGO'), ('A9463AAAAA', 'MACAO'),
          ('A9159AAAAA', 'MACEDONIA'), ('A9354AAAAA', 'MADAGASCAR'), ('A9425AAAAA', 'MALASIA'),
          ('A9346AAAAA', 'MALAWI'), ('A9436AAAAA', 'MALDIVAS'), ('A9347AAAAA', 'MALI'), ('A9120AAAAA', 'MALTA'),
          ('A9348AAAAA', 'MARRUECOS'), ('A9349AAAAA', 'MAURICIO'), ('A9350AAAAA', 'MAURITANIA'),
          ('A9234AAA1A', 'MEXICO'), ('A9148AAAAA', 'MOLDAVIA'), ('A9121AAAAA', 'MONACO'), ('A9427AAAAA', 'MONGOLIA'),
          ('A9160AAAAA', 'MONTENEGRO'), ('A9351AAAAA', 'MOZAMBIQUE'), ('A9400AAAAA', 'MYANMAR'),
          ('A9353AAAAA', 'NAMIBIA'), ('A9541AAAAA', 'NAURU'), ('A9420AAAAA', 'NEPAL'), ('A9236AAAAA', 'NICARAGUA'),
          ('A9360AAAAA', 'NIGER'), ('A9352AAAAA', 'NIGERIA'), ('A9122AAAAA', 'NORUEGA'),
          ('A9540AAAAA', 'NUEVA ZELANDA'), ('A9599AAAAA', 'OCEANIA'), ('A9444AAAAA', 'OMAN'),
          ('A9123AAA1A', 'PAISES BAJOS'), ('A9424AAA1A', 'PAKISTAN'), ('A9440AAAAA', 'PALESTINA'),
          ('A9238AAAAA', 'PANAMA'), ('A9542AAAAA', 'PAPUA NUEVA GUINEA'), ('A9240AAAAA', 'PARAGUAY'),
          ('A9242AAAAA', 'PERU'), ('A9124AAAAA', 'POLONIA'), ('A9125AAAAA', 'PORTUGAL'), ('A9244AAAAA', 'PUERTO RICO'),
          ('A9431AAAAA', 'QATAR'), ('A9112AAA1A', 'REINO UNIDO'), ('A9302AAA1A', 'REPUBLICA BENIN'),
          ('A9310AAA1A', 'REPUBLICA CENTROAFRICANA'), ('A9157AAAAA', 'REPUBLICA CHECA'),
          ('A9312AAA1A', 'REPUBLICA CONGO'), ('A9380AAAAA', 'REPUBLICA DEMOCRATICA CONGO'),
          ('A9218AAA1A', 'REPUBLICA DOMINICANA'), ('A9229AAAAA', 'REPUBLICA GRANADA'),
          ('A9466AAA1A', 'REPUBLICA KIRGUISTAN'), ('A9369AAAAA', 'REPUBLICA SUDAN SUR'), ('A9397AAAAA', 'RIO MUNI'),
          ('A9306AAAAA', 'RUANDA'), ('A9127AAAAA', 'RUMANIA'), ('A9149AAAAA', 'RUSIA'), ('A9398AAAAA', 'SAHARA'),
          ('A9256AAA1A', 'SAINT KITTS NEVIS'), ('A9220AAAAA', 'SALVADOR'), ('A9552AAAAA', 'SAMOA OCCIDENTAL'),
          ('A9135AAAAA', 'SAN MARINO'), ('A9259AAAAA', 'SAN MARTIN'), ('A9254AAA1A', 'SAN VICENTE GRANADINAS'),
          ('A9253AAAAA', 'SANTA LUCIA'), ('A9136AAA2A', 'SANTA SEDE'), ('A9361AAAAA', 'SANTO TOME PRINCIPE'),
          ('A9362AAAAA', 'SENEGAL'), ('A9155AAAAA', 'SERBIA'), ('A9363AAAAA', 'SEYCHELLES'),
          ('A9364AAAAA', 'SIERRA LEONA'), ('A9426AAAAA', 'SINGAPUR'), ('A9433AAAAA', 'SIRIA'),
          ('A9365AAAAA', 'SOMALIA'), ('A9404AAAAA', 'SRI LANKA'), ('A9367AAAAA', 'SUDAFRICA'), ('A9368AAAAA', 'SUDAN'),
          ('A9128AAAAA', 'SUECIA'), ('A9129AAAAA', 'SUIZA'), ('A9250AAAAA', 'SURINAM'), ('A9371AAAAA', 'SWAZILANDIA'),
          ('A9469AAAAA', 'TADJIKISTAN'), ('A9408AAA3A', 'TAIWAN TAIPEI'), ('A9370AAAAA', 'TANZANIA'),
          ('A9428AAAAA', 'THAILANDIA'), ('A9464AAAAA', 'TIMOR ORIENTAL'), ('A9374AAAAA', 'TOGO'),
          ('A9554AAAAA', 'TONGA'), ('A9245AAAAA', 'TRINIDAD TOBAGO'), ('A9378AAAAA', 'TUNEZ'),
          ('A9467AAAAA', 'TURKMENIA'), ('A9130AAAAA', 'TURQUIA'), ('A9560AAAAA', 'TUVALU'), ('A9152AAAAA', 'UCRANIA'),
          ('A9358AAAAA', 'UGANDA'), ('A9190AAA1A', 'UNION EUROPEA'), ('A9246AAAAA', 'URUGUAY'),
          ('A9468AAAAA', 'UZBEKISTAN'), ('A9565AAAAA', 'VANUATU'), ('A9248AAAAA', 'VENEZUELA'),
          ('A9430AAAAA', 'VIETNAM'), ('A9434AAAAA', 'YEMEN'), ('A9132AAAAD', 'YUGOSLAVIA'), ('A9382AAAAA', 'ZAMBIA'),
          ('A9357AAAAA', 'ZIMBABWE'))


class Vivienda(models.Model):
    POL = (('PN', 'Policía Nacional'), ('GC', 'Guardia Civil'))
    propietario = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    gpropietario = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la vivienda", blank=True, max_length=200, null=True)
    address = models.CharField("Dirección", blank=True, max_length=200, null=True)
    habitaciones = models.IntegerField("Número de habitaciones", blank=True, null=True)
    camas = models.IntegerField("Número de camas", blank=True, null=True)
    inquilinos = models.IntegerField("Número máximo de inquilinos", blank=True, null=True)
    iban = models.CharField("IBAN asociado a la vivienda", blank=True, max_length=50, null=True)
    nif = models.CharField("NIF del establecimiento", blank=True, max_length=50, null=True)
    municipio = models.CharField("Municipio del establecimiento", blank=True, max_length=150, null=True)
    provincia = models.CharField("Provincia del establecimiento", blank=True, max_length=150, null=True)
    observaciones = models.TextField("Observaciones sobre la vivienda", blank=True, null=True, default='')
    police = models.CharField("Selecciona el organismo policial", blank=True, max_length=5, choices=POL, default='')
    police_code = models.CharField("Código para web de la policía", blank=True, max_length=150, null=True, default='')
    police_pass = models.CharField("Password para web de la policía", blank=True, max_length=150, null=True, default='')
    borrada = models.BooleanField("Esta vivienda está borrada?", default=False)
    nregistro = models.CharField("Núm. registro VUT Com. Aut.", blank=True, max_length=30, null=True, default='')
    nombreweb = models.CharField("Título/Nombre", blank=True, null=True, max_length=300, default='')
    subnombreweb = models.CharField("Sub-Título/Texto bajo nombre", blank=True, null=True, max_length=300, default='')
    descripcionweb = models.TextField("Descripción de la vivienda", default='', blank=True, null=True)
    preciosweb = models.CharField("Secuencia de precios", blank=True, null=True, max_length=200, default='')
    publicarweb = models.BooleanField("Debe mostrarse en web?", default=False)

    class Meta:
        ordering = ['provincia', 'municipio', 'nombre']

    @property
    def portales(self):
        return CalendarioVivienda.objects.filter(vivienda=self).values_list('portal', flat=True)

    @property
    def has_domotica(self):
        return DomoticaVUT.objects.filter(vivienda=self).count() > 0

    @property
    def codigo_entidad_emisora(self):
        return self.police_code[-10:]

    @property
    def gauser_extra(self):
        return Gauser_extra.objects.get(ronda=self.entidad.ronda, gauser=self.gpropietario)

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.municipio)

class Vpropietario(models.Model):
    propietario = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    vivienda = models.ForeignKey(Vivienda, blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return u'%s (%s)' % (self.gpropietario, self.vivienda)


PORTALES = (('BOO', 'Booking'), ('AIR', 'Airbnb'), ('HOM', 'Homeaway'), ('REN', 'Rentalia'), ('NIU', 'Niumba'),
            ('OAP', 'Only Apartments'), ('WIM', 'Wimdu'), ('TRI', 'TripAdvisor'), ('OTR', 'Otros/Privado'))


class DayWebVivienda(models.Model):
    vivienda = models.ForeignKey(Vivienda, blank=True, null=True, on_delete=models.CASCADE)
    fecha = models.DateField('Fecha con nuevo precio', blank=True, null=True)
    preciosweb = models.CharField("Secuencia de precios", blank=True, null=True, max_length=200, default='')
    bloqueado = models.BooleanField('Esta fecha el alquiler está bloqueado', default=False)

    def __str__(self):
        if self.bloqueado:
            return u'%s - %s (Bloqueado)' % (self.vivienda, self.fecha)
        else:
            return u'%s - %s (%s)' % (self.vivienda, self.fecha, self.preciosweb)


# http://q2housing.com/portales-de-alquiler-vivienda-turistica/
class CalendarioVivienda(models.Model):
    vivienda = models.ForeignKey(Vivienda, blank=True, null=True, on_delete=models.CASCADE)
    portal = models.CharField("Portal que proporciona el calendario", blank=True, choices=PORTALES, max_length=3)
    ical = models.CharField("URL del ical", blank=True, max_length=250, null=True, default='')

    def __str__(self):
        return u'%s <- %s -> %s' % (self.vivienda, self.get_portal_display(), self.ical)


def update_foto(instance, filename):
    v = instance.vivienda
    ext = filename.rpartition('.')[-1]
    nombre = pass_generator()
    ruta = os.path.join("vut/%s/%s/fotosweb/" % (v.entidad.id, v.id), "%s.%s" % (nombre, ext))
    return ruta


class FotoWebVivienda(models.Model):
    vivienda = models.ForeignKey(Vivienda, blank=True, null=True, on_delete=models.CASCADE)
    foto = models.ImageField('Foto de la vivienda para mostrar en web', upload_to=update_foto, blank=True, null=True)
    caption = models.CharField("Título/Nombre de la foto", blank=True, null=True, max_length=300, default='')
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    orden = models.IntegerField("Orden en el que se muestra", default=0)

    # portada = models.BooleanField("Es la fotografía de portada?", default=False)

    def filename(self):
        f = os.path.basename(self.foto.name)
        return os.path.split(f)[1]

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """
            REQUIRES:
                1.	'from PIL import Image'

            DOES:
                1.	check to see if the image needs to be resized
                2.	check how to resize the image based on its aspect ratio
                3.	resize the image accordingly

            ABOUT:
                based loosely on djangosnippet #688
                http://www.djangosnippets.org/snippets/688/

            VERSIONS I'M WORKING WITH:
                Django 1.0
                Python 2.5.1

            BY:
                Tanner Netterville
                tanner@cabedge.com
        """
        fotos = FotoWebVivienda.objects.filter(vivienda=self.vivienda)
        if not self.orden:
            self.orden = fotos.count() + 5
        super(FotoWebVivienda, self).save()

        filename = str(self.foto.path)
        try:
            mw = 1024  # maximum allowed width
            mh = 567
            image = Image.open(filename)
            pw, ph = image.size  # actual picture width (and picture height)

            if pw > mw:
                nw = mw
                nh = int(ph * nw / pw)
                image = image.resize((nw, nh), Image.ANTIALIAS)
                image.save(filename)
            image.close()
        except:
            pass

        # filename = str(self.foto.path)
        # try:
        #     nw = 850
        #     nh = 567
        #     image = Image.open(filename)
        #     pw, ph = image.size
        #     pr = float(pw) / float(ph)
        #     nr = float(nw) / float(nh)
        #
        #     if pr > nr:
        #         # photo aspect is wider than destination ratio
        #         tw = int(round(nh * pr))
        #         image = image.resize((tw, nh), Image.ANTIALIAS)
        #         l = int(round((tw - nw) / 2.0))
        #         image = image.crop((l, 0, l + nw, nh))
        #     elif pr < nr:
        #         # photo aspect is taller than destination ratio
        #         th = int(round(nw / pr))
        #         image = image.resize((nw, th), Image.ANTIALIAS)
        #         t = int(round((th - nh) / 2.0))
        #         print((0, t, nw, t + nh))
        #         image = image.crop((0, t, nw, t + nh))
        #     else:
        #         # photo aspect matches the destination ratio
        #         image = image.resize((nw, nh), Image.ANTIALIAS)
        #
        #     image.save(filename)
        # except:
        #     pass

    def __str__(self):
        return u'%s (%s - %s)' % (self.foto, self.caption, self.vivienda.nombre)


class Autorizado(models.Model):
    ESTADOS = (
        ('OFE', 'En oferta a la persona autorizada'), ('ACE', 'Autorización aceptada'),
        ('REC', 'Autorización rechazada'))
    vivienda = models.ForeignKey(Vivienda, blank=True, null=True, on_delete=models.CASCADE)
    autorizado = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    estado = models.CharField('Estado de la autorización', max_length=3, default='OFE', choices=ESTADOS)
    permisos = models.ManyToManyField(Permiso, blank=True)

    def __str__(self):
        return u'%s <-> %s' % (self.vivienda, self.autorizado)


class Ayudante(models.Model):
    TIPO = (('P', 'Porcentaje (%)'), ('F', 'Cantidad fija'))
    vivienda = models.ForeignKey(Vivienda, on_delete=models.CASCADE)
    apellido1 = models.CharField("Primer apellido", blank=True, max_length=150, null=True, default='')
    apellido2 = models.CharField("Segundo apellido", blank=True, max_length=150, null=True, default='')
    nombre = models.CharField("Nombre", blank=True, max_length=150, null=True, default='')
    nif = models.CharField("NIF del ayudante", blank=True, max_length=50, null=True, default='')
    tipo = models.CharField("Tipo de cobro", default='P', max_length=3, choices=TIPO)
    cantidad = models.FloatField('Cantidad en euros o porcentaje', blank=True, null=True, default=0)
    iban = models.CharField("IBAN del ayudante", blank=True, max_length=50, null=True)

    class Meta:
        ordering = ['apellido1', 'apellido2', 'nombre']

    def __str__(self):
        return u'%s %s, %s - %s' % (self.apellido1, self.apellido2, self.nombre, self.vivienda)


def aleatorio():  # Esta función no se puede borrar porque afecta a las migrations
    return True  # Es un error de django


class Reserva(models.Model):
    ESTADO = (('ACE', 'Aceptada'), ('CAN', 'Cancelada'))
    vivienda = models.ForeignKey(Vivienda, on_delete=models.CASCADE, blank=True, null=True)
    secret = models.CharField('Cadena secreta utilizada en url de registro', max_length=20, default=pass_generator)
    nombre = models.CharField('Nombre', blank=True, max_length=150, null=True, default='')
    entrada = models.DateField('Fecha y hora de entrada', blank=True, null=True, default=now)
    salida = models.DateField('Fecha y hora de salida', blank=True, null=True, default=now)
    noches = models.IntegerField('Número de noches reservado', default=1)
    code = models.CharField('Código de confirmación', blank=True, max_length=150, null=True, default='')
    total = models.FloatField('Importe total cobrado', blank=True, null=True, default=0)
    limpieza = models.FloatField('Importe total cobrado', blank=True, null=True, default=0)
    estado = models.CharField('Estado', max_length=3, default='ACE', choices=ESTADO)
    num_viajeros = models.IntegerField('Número de viajeros previsto', default=0)
    borrada = models.BooleanField('Esta reserva está borrada?', default=False)
    portal = models.CharField("Portal en el que se ha hecho la reserva", blank=True, choices=PORTALES, max_length=3)
    creado = models.DateTimeField("Fecha y hora en el que se graba la reserva", auto_now_add=True)

    class Meta:
        ordering = ['-entrada', 'vivienda']

    @property
    def salida2(self):
        return self.entrada + timedelta(self.noches)

    def save(self, *args, **kwargs):
        self.salida = self.entrada + timedelta(self.noches)
        super(Reserva, self).save(*args, **kwargs)

    def __str__(self):
        return u'%s - %s - %s (%s) - %s' % (self.vivienda, self.nombre, self.code, self.total, self.entrada)


def update_firma(instance, filename):
    v = instance.reserva.vivienda
    ruta = os.path.join("vut/%s/%s/firmas/" % (v.entidad.id, v.id),
                        str(instance.reserva.code) + '_' + str(instance.ndi) + '.png')
    return ruta


class Viajero(models.Model):
    TIPOS = (('D', 'DNI'), ('P', 'Pasaporte'), ('C', 'Permiso de conducir'), ('I', 'Carta o documento de identidad'),
             ('X', 'Permiso de residencia de la UE'), ('N', 'NIE o tarjeta española de extranjeros'))
    SEXOS = (('F', 'Sexo femenino'), ('M', 'Sexo masculino'))
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    num = models.IntegerField('Número de parte', blank=True, null=True)
    ndi = models.CharField("Número de documento de identidad", blank=True, max_length=150, null=True)
    tipo_ndi = models.CharField("Tipo de documento", blank=True, max_length=3, null=True, choices=TIPOS)
    fecha_exp = models.DateField('Fecha de expedición del documento (AAAAMMDD)', blank=True, null=True)
    apellido1 = models.CharField("Primer apellido", blank=True, max_length=150, null=True)
    apellido2 = models.CharField("Segundo apellido", blank=True, max_length=150, null=True)
    nombre = models.CharField("Nombre", blank=True, max_length=150, null=True)
    sexo = models.CharField("Sexo", default='F', max_length=3, choices=SEXOS)
    nacimiento = models.DateField('Fecha de nacimiento (AAAAMMDD)', blank=True, null=True)
    pais = models.CharField("País de nacionalidad", blank=True, max_length=11, null=True, choices=PAISES)
    firma = models.ImageField('Imagen de la firma del viajero', upload_to=update_firma, blank=True, null=True)
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')
    fichero_policia = models.BooleanField('Insertado en fichero policía', default=False)
    creado = models.DateTimeField("Fecha y hora en el que el viajero graba sus datos", auto_now_add=True)

    @property
    def nombre_completo(self):
        return '%s %s %s' % (self.nombre, self.apellido1, self.apellido2)

    @property
    def fecha_entrada(self):
        hoy = now().date()
        ayer = hoy - timedelta(1)
        if self.reserva.entrada == hoy:
            return self.reserva.entrada
        else:
            return ayer

    def save(self, *args, **kwargs):
        num = Viajero.objects.filter(reserva__vivienda__police_code=self.reserva.vivienda.police_code).count() + 1
        self.num = num
        super(Viajero, self).save(*args, **kwargs)

    class Meta:
        ordering = ['reserva__vivienda', '-num']

    def __str__(self):
        return u'%s - %s %s, %s (%s)' % (self.num, self.apellido1, self.apellido2, self.nombre, self.creado.date())
    # def __str__(self):
    #     return u'%s' % (self.num)


class PagoAyudante(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
    ayudante = models.ForeignKey(Ayudante, on_delete=models.CASCADE)
    pago = models.FloatField('Cantidad pagada al ayudante', blank=True, null=True)

    class Meta:
        ordering = ['ayudante__apellido1', 'ayudante__apellido2', 'ayudante__nombre']

    def __str__(self):
        return u'%s %s, %s - %s (%s Euros)' % (self.ayudante.apellido1, self.ayudante.apellido2, self.ayudante.nombre,
                                               self.reserva, self.pago)


def update_parte(instance, filename):
    v = instance.vivienda
    nombre = v.codigo_entidad_emisora
    ext = instance.ext
    ruta = os.path.join("vut/%s/%s/partes/" % (v.entidad.id, v.id), "%s.%s" % (nombre, ext))
    return ruta


def update_pdfPN(instance, filename):
    v = instance.vivienda
    viajero = instance.viajero.id
    ruta = os.path.join("vut/%s/%s/partes/" % (v.entidad.id, v.id), "%s.pdf" % (viajero))
    return ruta


class RegistroPolicia(models.Model):
    vivienda = models.ForeignKey(Vivienda, blank=True, on_delete=models.CASCADE)
    viajero = models.ForeignKey(Viajero, blank=True, on_delete=models.CASCADE, related_name='registro', null=True)
    enviado = models.BooleanField('Ha sido enviado a la PN/GC?', default=False)
    viajeros = models.ManyToManyField(Viajero, blank=True)
    parte = models.FileField('Fichero de registro generado', upload_to=update_parte, blank=True, null=True)
    pdf_PN = models.FileField('Fichero generado por la PN', upload_to=update_pdfPN, blank=True, null=True)
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')
    creado = models.DateTimeField("Fecha y hora en el que el viajero graba sus datos", auto_now_add=True)
    n = models.IntegerField('Número de registro', default=1)

    def save(self, *args, **kwargs):
        n = RegistroPolicia.objects.filter(vivienda=self.vivienda).count() + 1
        self.n = n / 1000 + n % 1000  # Cantidad circular 1,2,3,....,999,1,2,3,....
        super(RegistroPolicia, self).save(*args, **kwargs)

    @property
    def ext(self):
        return '%03d' % self.n
        # return str(self.n).zfill(3)

    @property
    def filename(self):
        return os.path.basename(self.parte.name)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s - %s (%s)' % (self.ext, self.vivienda.nombre, self.creado)


###################################################################################################
########################## CONTABILIDAD ###########################################################
###################################################################################################

class ContabilidadVUT(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    propietario = models.ForeignKey(Gauser, blank=True, null=True, related_name='vut', on_delete=models.CASCADE)
    viviendas = models.ManyToManyField(Vivienda, blank=True)
    nombre = models.CharField('Nombre', max_length=200, default='Contabilidad VUT', blank=True, null=True)
    inicio = models.DateField('Fecha de inicio de la contabilidad', blank=True, null=True)
    fin = models.DateField('Fecha de finalización de la contabilidad', blank=True, null=True)
    describir = models.TextField('Descripción de la información recogida', null=True, blank=True)
    borrada = models.BooleanField('Está borrada?', default=False)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    @property
    def portales(self):
        portales_ = []
        for vivienda in self.viviendas.all():
            for portal in vivienda.portales:
                if portal not in portales_:
                    portales_.append(portal)
        return portales_

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'Contabilidad para %s (%s) - B: %s' % (self.propietario.get_full_name(), self.modificado, self.borrada)


class AutorizadoContabilidadVut(models.Model):
    ESTADOS = (
        ('OFE', 'En oferta a la persona autorizada'), ('ACE', 'Autorización aceptada'),
        ('REC', 'Autorización rechazada'))
    contabilidad = models.ForeignKey(ContabilidadVUT, blank=True, null=True, on_delete=models.CASCADE)
    autorizado = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    estado = models.CharField('Estado de la autorización', max_length=3, default='OFE', choices=ESTADOS)
    permisos = models.ManyToManyField(Permiso, blank=True)

    def __str__(self):
        return u'%s <-> %s' % (self.contabilidad, self.autorizado)


class PartidaVUT(models.Model):
    TIPOS = (('GASTO', 'Gasto'), ('INGRE', 'Ingreso'), ('I_BOO', 'Ingreso Booking'), ('I_AIR', 'Ingreso Airbnb'),
             ('I_HOM', 'Ingreso Homeaway'), ('I_REN', 'Ingreso Rentalia'), ('I_NIU', 'Ingreso Niumba'),
             ('I_OAP', 'Ingreso Only apartments'), ('I_WIM', 'Ingreso Wimdu'))
    contabilidad = models.ForeignKey(ContabilidadVUT, on_delete=models.CASCADE)
    tipo = models.CharField('Tipo de partida', max_length=6, choices=TIPOS)
    nombre = models.CharField('Nombre de la partida', max_length=150)
    creado = models.DateField('Fecha de creación', auto_now_add=True)  # Se graba automaticamente al crearse
    modificado = models.DateField('Fecha de modificación', auto_now=True)  # Se graba automaticamente al modificarse

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.get_tipo_display())


def update_fichero(instance, filename):
    nombre = filename.rpartition('.')
    instance.fich_name = filename
    fichero = pass_generator(size=30) + '.' + nombre[2]
    return '/'.join(['contabilidad_vut', str(instance.vivienda.entidad.id), str(instance.vivienda.id), fichero])


class AsientoVUT(models.Model):
    partida = models.ForeignKey(PartidaVUT, on_delete=models.CASCADE)
    vivienda = models.ForeignKey(Vivienda, blank=True, null=True, on_delete=models.CASCADE)
    concepto = models.CharField('Concepto', max_length=100)
    descripcion = models.TextField('Pequeña descripción', max_length=250, null=True, blank=True)
    cantidad = models.FloatField('Cantidad monetaria (euros)')
    fichero = models.FileField("Fichero con la información de facturación", upload_to=update_fichero, blank=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    def filename(self):
        return os.path.basename(self.fich_name)

    def fileextension(self):
        fileName, fileExtension = os.path.splitext(self.fich_name)
        return fileExtension

    def __str__(self):
        return u'%s - %s (%s)' % (self.partida.contabilidad.id, self.concepto, self.cantidad)


###################################################################################################
############################## DOMÓTICA ###########################################################
###################################################################################################

class DomoticaVUT(models.Model):
    TIPO_DOMOTICA = (
    ('SELFLOCKING', 'Auto-bloqueo'), ('ONOFF', 'Interruptor'), ('TERMOSTATO', 'Control de temperatura'))
    vivienda = models.ForeignKey(Vivienda, blank=True, null=True, on_delete=models.CASCADE)
    url = models.CharField('URL para la activación del dispositivo', blank=True, null=True, max_length=250)
    nombre = models.CharField('Nombre dado al dispositivo', blank=True, null=True, max_length=250)
    texto = models.TextField('Texto a enviar', blank=True, null=True)
    tipo = models.CharField('Tipo de dispositivo', max_length=15, default='SELFLOCKING', choices=TIPO_DOMOTICA)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.vivienda)


class ConfEnlacesDomoticaVUT(models.Model):
    propietario = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    url = models.CharField('URL para manejar los dispositivos configurados', blank=True, null=True, max_length=250)
    inicio = models.DateField('Fecha desde la que está activo el enlace', null=True, blank=True)
    fin = models.DateField('Fecha hasta la que está activo el enlace', null=True, blank=True)
    nombre = models.CharField('Nombre de la configuración', blank=True, null=True, max_length=250)
    domoticas = models.ManyToManyField(DomoticaVUT, blank=True)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.vivienda)
