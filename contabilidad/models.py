# -*- coding: utf-8 -*-
import re
import os
from django.db import models
from django.utils.text import slugify
from django.utils.timezone import datetime
from django.db.models.signals import post_delete
from django.dispatch import receiver

from autenticar.models import Gauser
from bancos.views import num_cuenta2iban, asocia_banco_ge
from entidades.models import Entidad, Subentidad, Ronda, Cargo, Gauser_extra

from bancos.models import Banco
from gauss.funciones import pass_generator, usuarios_ronda
from vut.models import Vivienda


def update_file(instance, filename):
    nombre = filename.partition('.')
    nombre = '%s.%s' % (pass_generator(size=10), nombre[2])
    return os.path.join('contabilidad/', nombre)


def update_fichero(instance, filename):
    nombre = filename.rpartition('.')
    instance.fich_name = filename
    fichero = pass_generator(size=20) + '.' + nombre[2]
    return '/'.join(['contabilidad', str(instance.entidad.code), fichero])


class File_contabilidad(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero, blank=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Ficheros de contabilidad"

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def __str__(self):
        return u'%s (%s)' % (self.fichero, self.entidad.name)


class Presupuesto(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    # ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateField('Fecha de modificación', auto_now=True)
    nombre = models.CharField('Nombre del presupuesto', max_length=300, blank=True, null=True)
    describir = models.TextField('Descripción del presupuesto (opcional)', null=True, blank=True)
    archivado = models.BooleanField('Está archivado?', default=False)

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return u'Presupuesto de la entidad %s (%s)' % (self.entidad.name, self.modificado)


class Partida(models.Model):
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE)
    tipo = models.CharField('Tipo de partida', max_length=6, choices=(('GASTO', 'Gasto'), ('INGRE', 'Ingreso')))
    nombre = models.CharField('Nombre de la partida', max_length=150)
    cantidad = models.FloatField('Cantidad monetaria (euros)')
    creado = models.DateField('Fecha de creación', auto_now_add=True)  # carga automaticamente la fecha al crearse
    modificado = models.DateField('Fecha de modificación',
                                  auto_now=True)  # carga automaticamente la fecha al modificarse

    def __str__(self):
        # return u'%s - Partida de %s (%s)' % (self.presupuesto.id, self.get_tipo_display(),self.nombre)
        return u'%s (%s)' % (self.nombre, self.get_tipo_display())


class Asiento(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE)
    concepto = models.CharField('Concepto', max_length=100)
    nombre = models.CharField('Pequeña descripción', max_length=250, null=True, blank=True)
    cantidad = models.FloatField('Cantidad monetaria (euros)')
    escaneo = models.ForeignKey(File_contabilidad, blank=True, null=True, related_name='escaneo',
                                on_delete=models.CASCADE)
    creado = models.DateField('Fecha de creación', auto_now_add=True)  # carga automaticamente la fecha al crearse
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    def filename(self):
        return os.path.basename(self.escaneo.name)

    def fileextension(self):
        fileName, fileExtension = os.path.splitext(self.escaneo.name)
        return fileExtension

    def __str__(self):
        return u'%s - %s (%s)' % (self.partida.presupuesto.id, self.concepto, self.cantidad)


###################################################################################################
################################ CUOTAS ###########################################################
###################################################################################################


class Politica_cuotas(models.Model):
    TIPOS_CUOTA = (('fija', 'Cuota fija'), ('hermanos', 'Cuota condicionada al número de hermanos'),
                   ('vut', 'Cuota asociada al número de VUT'),
                   ('domotica', 'Cuota asociada al número de controles domóticos'))
    MESES = ((1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'), (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'),
             (8, 'Agosto'), (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'))
    TIPOS_PAGO = (('RCUR', 'Pago recurrente'), ('OOFF', 'Pago único'))
    TIPOS_COBRO = (('MEN', 'Mensual'), ('ANU', 'Anual'), ('UNI', 'Único'))
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    tipo = models.CharField('Tipo de cuota', max_length=10, choices=TIPOS_CUOTA, default='fija')
    cargo = models.ForeignKey(Cargo, null=True, blank=True, on_delete=models.CASCADE)
    tipo_cobro = models.CharField('Tipo de cobro', max_length=6, choices=TIPOS_COBRO)
    seqtp = models.CharField('Tipo de pago', max_length=6, choices=TIPOS_PAGO, default='RCUR')
    cuota = models.CharField('Cuotas separadas por comas', blank=True, null=True, max_length=200)
    cantidad = models.FloatField('Cantidad monetaria (euros)', blank=True, null=True)
    concepto = models.CharField('Concepto', max_length=100)
    exentos = models.ManyToManyField(Gauser, blank=True, help_text='&nbsp;</span><span style="display:none;">')
    descuentos = models.TextField('Descuentos', null=True, blank=True)
    dia = models.IntegerField('Día del mes que se pasa la couta', null=True, blank=True)
    mes = models.IntegerField('Mes de cobro (en caso de couta anual)', null=True, blank=True, choices=MESES)
    creado = models.DateField('Fecha de creación', auto_now_add=True)  # carga automaticamente la fecha al crearse
    modificado = models.DateField('Fecha de modificación', auto_now=True)

    class Meta:
        ordering = ['-modificado']
        verbose_name_plural = "Políticas de cuotas"

    @property
    def destinatarios(self):
        usuarios = usuarios_ronda(self.entidad.ronda, cargos=[self.cargo]).exclude(gauser__in=self.exentos.all())
        dicts_destinatarios = []
        if self.tipo == 'hermanos':
            usuarios_analizados = []
            for u in usuarios:
                if u not in usuarios_analizados:
                    familiares = u.unidad_familiar
                    usuarios_analizados.extend(familiares)
                    familiares_gauser = familiares.values_list('gauser__id', flat=True)
                    deudores = familiares.filter(id__in=usuarios)
                    num = deudores.count()
                    texto = ', '.join(deudores.values_list('gauser__first_name', flat=True))
                    try:
                        oa = OrdenAdeudo.objects.filter(politica=self, fecha_firma__isnull=False,
                                                        gauser__id__in=familiares_gauser)[0]
                    except:
                        oa = OrdenAdeudo.objects.none()
                    dicts_destinatarios.append({'oa': oa, 'ge': u, 'num': num, 'texto': texto})
        elif self.tipo == 'vut':
            for u in usuarios:
                viviendas = Vivienda.objects.filter(gpropietario=u.gauser, borrada=False, entidad=u.ronda.entidad)
                num = viviendas.count()
                texto = '%d viviendas gestionadas por %s' % (num, u.gauser.get_full_name())
                if num > 0:
                    try:
                        oa = OrdenAdeudo.objects.get(politica=self, fecha_firma__isnull=False, gauser=u.gauser)
                    except:
                        oa = OrdenAdeudo.objects.none()
                    dicts_destinatarios.append({'oa': oa, 'ge': u, 'num': num, 'texto': texto})
        else:  # Esta será la opción relacionada con la cuota tipo "fija"
            for u in usuarios:
                num = 1
                texto = '%s' % (u.gauser.get_full_name())
                try:
                    oa = OrdenAdeudo.objects.get(politica=self, fecha_firma__isnull=False, gauser=u.gauser)
                except:
                    oa = OrdenAdeudo.objects.none()
                dicts_destinatarios.append({'oa': oa, 'ge': u, 'num': num, 'texto': texto})
        return dicts_destinatarios

    @property
    def array_cuotas(self):
        if not self.cuota:
            self.cuota = '0'
            self.save()
        importes = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", self.cuota)))
        return importes + [importes[-1]] * 1000

    @property
    def no_exentos(self):
        importes = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", self.cuota)))
        return importes + [importes[-1]] * 1000

    @property
    def mndtid(self):
        return "%s-%s-%s"[:34] % (self.entidad.code, self.pk, self.creado.strftime('%s'))

    @property
    def mandate_reference(self):
        return "%s-%s-%s"[:34] % (self.entidad.code, self.pk, self.creado.strftime('%s'))

    @property
    def creditor_identifier(self):
        return at_02(self.entidad.banco.nif)

    @property
    def creditor_identifier_verbose(self):
        return "%s - %s" % (at_02(self.entidad.banco.nif), self.entidad.name)

    @property
    def creditor_address(self):
        return self.entidad.address

    @property
    def creditor_postalcode_city_town(self):
        postalcode = self.entidad.postalcode
        localidad = self.entidad.localidad
        provincia = self.entidad.get_provincia_display()
        return "%s - %s - %s" % (postalcode, localidad, provincia)

    @property
    def creditor_country(self):
        return 'ESPAÑA'

    def __str__(self):
        return u'%s - %s (%s)' % (self.entidad.name, self.cargo, self.cantidad)


class Remesa_emitida(models.Model):
    politica = models.ForeignKey(Politica_cuotas, on_delete=models.CASCADE)
    grupo = models.CharField('Cadena que identifica unívocamente un grupo', max_length=40)
    reqdcolltndt = models.DateField('Requested Collection Date', max_length=40, blank=True, null=True)
    ctrlsum = models.FloatField('Control sum', max_length=40, blank=True, null=True)
    nboftxs = models.IntegerField('Number of transactions', blank=True, null=True)
    visible = models.BooleanField('Es visible?', default=True)
    creado = models.DateTimeField('Fecha de creación', auto_now_add=True)

    class Meta:
        ordering = ['-creado']
        verbose_name_plural = "Remesas emitidas"

    @property
    def rmtinf(self):
        return '%s - %s (%s)' % (self.politica.concepto,
                                 self.politica.get_tipo_cobro_display(),
                                 datetime.today().strftime('%d-%m-%Y'))

    def __str__(self):
        c = self.politica.cargo.cargo if self.politica.cargo else 'No asignada a cargo'
        return u'%s - %s (%s)' % (self.politica.entidad.name, c, self.grupo)


class Remesa(models.Model):
    emitida = models.ForeignKey(Remesa_emitida, on_delete=models.CASCADE)
    ge = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, blank=True, null=True)
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE)
    dtofsgntr = models.DateField('Fecha deudor firma mandato')
    dbtriban = models.CharField('IBAN del deudor', max_length=30)
    # rmtinf = models.CharField('Información del acreedor al deudor (concepto)', max_length=140)
    # instdamt = models.FloatField('Cantidad de dinero')  # decimales separados por "." y con un máximo de 2 decimales
    counter = models.IntegerField('Identificación única de remesa')
    creado = models.DateTimeField('Fecha de creación', auto_now_add=True)

    @property
    def orden_adeudo(self):
        try:
            return OrdenAdeudo.objects.get(gauser=self.ge.gauser, politica=self.emitida.politica,
                                           fecha_firma__isnull=False)
        except:
            return OrdenAdeudo.objects.none()

    @property
    def deudores(self):
        if self.emitida.politica.tipo == 'hermanos':
            familiares = self.ge.unidad_familiar
            return familiares.filter(id__in=self.emitida.politica.destinatarios)
        else:
            return Gauser_extra.objects.filter(id=self.ge)

    @property
    def instdamt(self):
        if self.emitida.politica.tipo == 'hermanos':
            familiares = self.ge.unidad_familiar
            num_pagos = familiares.filter(id__in=self.emitida.politica.destinatarios).count()
        if self.emitida.politica.tipo == 'vut':
            num_pagos = Vivienda.objects.filter(gpropietario=self.ge.gauser, borrada=False,
                                                entidad=self.ge.ronda.entidad).count()
        else:
            num_pagos = 1
        importes = self.emitida.politica.array_cuotas
        return sum(importes[:num_pagos])

    @property
    def deudores_str(self):
        if self.emitida.politica.tipo == 'hermanos':
            familiares = self.ge.unidad_familiar
            deudores = familiares.filter(id__in=usuarios)
            usuarios_id += list(deudores.values_list('id', flat=True))
            n_cs = familiares.values_list('num_cuenta_bancaria', flat=True)
            deudores_str = ', '.join(deudores.values_list('gauser__first_name', flat=True))

        return True

    @property
    def rmtinf(self):
        nombres = ', '.join(deudores.values_list('gauser__first_name', flat=True))
        return 'Pago de cuota: %s - %s (%s)' % (self.emitida.politica.concepto,
                                                self.emitida.politica.get_tipo_cobro_display(),
                                                datetime.today().strftime('%d-%m-%Y'))

    @property
    def mndtid(self):
        return "%s-%s-%s"[:34] % (self.pk, self.ge.ronda.entidad.code, self.creado.strftime('%s'))

    @property
    def dbtrnm(self):
        return self.ge.gauser.get_full_name()[:69] if self.ge else 'No asignada a un gauser_extra'

    class Meta:
        verbose_name_plural = "Remesas individuales"

    def __str__(self):
        return '%s - %s - %s' % (self.emitida.politica.entidad.name, self.rmtinf, self.dbtrnm)


# ------------------------------------------------------------ #
# ------------------------------------------------------------ #
# ------------------------------------------------------------ #


def at_02(nif):  # Diseñado a partir del documento "adeudos_sepa.pdf"
    tabla = {'A': '10', 'G': '16', 'M': '22', 'S': '28', 'Y': '34', 'B': '11', 'H': '17', 'N': '23', 'T': '29',
             'Z': '35', 'C': '12', 'I': '18', 'O': '24', 'U': '30', 'D': '13', 'J': '19', 'P': '25', 'V': '31',
             'E': '14', 'K': '20', 'Q': '26', 'W': '32', 'F': '15', 'L': '21', 'R': '27', 'X': '33', '0': '0', '1': '1',
             '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9'}
    a = 'ES'  # Primera parte de la identificación devuelta y correspondiente a España
    d = nif
    cad = re.sub('[^0-9a-zA-Z]+', '', d) + a + '00'
    for k, v in tabla.items():
        cad = cad.replace(k, v)
    cad = str(98 - int(cad) % 97)
    b = cad if len(cad) == 2 else '0' + cad
    c = '001'
    return a + b + c + d


def update_firma(instance, filename):
    politica = instance.politica
    ruta = os.path.join("contabilidad/%s/firmas_adeudos/" % (politica.entidad.id),
                        str(politica.id) + '_' + str(instance.gauser.dni) + '.png')
    return ruta



class OrdenAdeudo(models.Model):
    gauser = models.ForeignKey(Gauser, on_delete=models.CASCADE)
    politica = models.ForeignKey(Politica_cuotas, on_delete=models.CASCADE)
    firma = models.ImageField('Imagen de la firma del deudor', upload_to=update_firma, blank=True, null=True)
    fecha_firma = models.DateField("Fecha y hora en la que se realizó la firma", blank=True, null=True)
    texto_firmado = models.TextField("Texto firmado", blank=True, null=True)

    @property
    def g_e(self):
        return Gauser_extra.objects.get(gauser=self.gauser, ronda=self.politica.entidad.ronda)

    @property
    def mndtid(self):
        return "%011d-%011d-%011d" % (self.pk, self.politica.entidad.code, self.gauser.pk)

    @property
    def debtor_name(self):
        return self.gauser.get_full_name()

    @property
    def debtor_address(self):
        return self.gauser.address

    @property
    def debtor_postalcode_city_town(self):
        pc = self.gauser.postalcode
        localidad = self.gauser.localidad
        provincia = self.gauser.get_provincia_display()
        return pc + ' - ' + localidad + ' - ' + provincia

    @property
    def debtor_country(self):
        return 'ESPAÑA'

    @property
    def debtor_bic(self):
        ge = Gauser_extra.objects.get(gauser=self.gauser, ronda=self.politica.entidad.ronda)
        return ge.banco.bic

    @property
    def debtor_account(self):
        ge = Gauser_extra.objects.get(gauser=self.gauser, ronda=self.politica.entidad.ronda)
        return ge.num_cuenta_bancaria

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return '%s - %s (%s)' % (self.politica.id, self.politica.entidad, self.gauser.get_full_name())


@receiver(post_delete, sender=OrdenAdeudo)
def delete_firma(sender, instance, *args, **kwargs):
    try:
        os.remove(instance.firma.path)
    except:
        pass