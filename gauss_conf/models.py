# # -*- coding: utf-8 -*-
# from datetime import date
# from django.db import models
# from django.contrib.auth.models import AbstractUser
# from gauss.constantes import *
# from bancos.models import Banco
# import os
# ###########################################################
#
# from django.contrib.auth.models import AbstractUser
# from django.db.models import Q
#
# def update_anagrama_entidad(instance, filename):
#     nombre = filename.partition('.')
#     nombre = str(instance.code) + '_anagrama.' + nombre[2]
#     return os.path.join("anagramas/", nombre)
#
#
# def update_anagrama_organizacion(instance, filename):
#     nombre = filename.partition('.')
#     nombre = str(instance.iniciales) + '_anagrama.' + nombre[2]
#     return os.path.join("anagramas/", nombre)
#
#
# class Organization2(models.Model):
#     organization = models.CharField("Organización a la que pertenece la entidad", max_length=100)
#     iniciales = models.CharField("iniciales de la organización", max_length=30)
#     fecha_fundada = models.DateField("Fecha de fundación", null=True, blank=True)
#     web = models.URLField("Página web")
#     anagrama = models.ImageField("Anagrama de la organización", upload_to=update_anagrama_organizacion, null=True,
#                                  blank=True)
#
#     def filename(self):
#         return os.path.basename(self.anagrama.name)
#
#     def __unicode__(self):
#         return u'%s (%s)' % (self.organization, self.iniciales)
#
#
# class Ronda2(models.Model):
#     entidad = models.ForeignKey('Entidad2', related_name='rondas', null=True, blank=True)
#     nombre = models.CharField("Nombre del periodo de funcionamiento", max_length=30)
#     inicio = models.DateField("Fecha de inicio de ronda", null=True, blank=True)
#     fin = models.DateField("Fecha de finalización de ronda", null=True, blank=True)
#
#     def __unicode__(self):
#         return u'%s (%s)' % (self.nombre, self.entidad.name)
#
#
# class Entidad2(models.Model):
#     organization = models.ForeignKey(Organization2, null=True, blank=True)
#     ronda = models.ForeignKey(Ronda2, related_name='entidades', null=True, blank=True)
#     code = models.IntegerField("Código de entidad", null=True, blank=True)
#     nif = models.CharField("NIF", max_length=20, null=True, blank=True)
#     banco = models.ForeignKey(Banco, null=True, blank=True)
#     iban = models.CharField("IBAN", max_length=40, null=True, blank=True)
#     name = models.CharField("Nombre", max_length=250, null=True, blank=True)
#     address = models.CharField("Dirección", max_length=375, null=True, blank=True)
#     localidad = models.CharField("Localidad", max_length=200, null=True, blank=True)
#     provincia = models.CharField("Provincia", max_length=4, choices=PROVINCIAS, default='0')
#     postalcode = models.CharField("Código postal", max_length=20, null=True, blank=True)
#     tel = models.CharField("Teléfono", max_length=20, null=True, blank=True)
#     fax = models.CharField("Fax", max_length=20, null=True, blank=True)
#     web = models.URLField("Web", max_length=100, null=True, blank=True)
#     mail = models.EmailField("E-mail", max_length=100, null=True, blank=True)
#     anagrama = models.ImageField("Anagrama", upload_to=update_anagrama_entidad, blank=True)
#     dominio = models.CharField("Subdominio", max_length=200, null=True, blank=True)
#
#     class Meta:
#         verbose_name_plural = "Entidades"
#
#     def __unicode__(self):
#         return u'Entidad2: %s (%s)' % (self.code, self.name)
#
#
# class Subentidad2(models.Model):
#     entidad = models.ForeignKey(Entidad2)
#     nombre = models.CharField("Nombre", max_length=250, null=True, blank=True)
#     edad_min = models.IntegerField("Edad de acceso", null=True, blank=True)
#     edad_max = models.IntegerField("Edad de finalización", null=True, blank=True)
#     mensajes = models.BooleanField("Están en lista de mensajería", default=False)
#     observaciones = models.TextField("Observaciones", null=True, blank=True)
#
#     @property
#     def rango_edad(self):
#         return self.edad_max - self.edad_min
#
#     class Meta:
#         verbose_name_plural = "Subentidades"
#
#     def __unicode__(self):
#         return u'Subentidad2: %s (%s)' % (self.nombre, self.entidad.name)
#
#
# class Subsubentidad2(models.Model):
#     subentidad = models.ForeignKey(Subentidad2)
#     nombre = models.CharField("Nombre", max_length=250, null=True, blank=True)
#     observaciones = models.TextField("Observaciones", null=True, blank=True)
#
#     class Meta:
#         verbose_name_plural = "Subsubentidades"
#
#     def __unicode__(self):
#         return u'Subentidad2: %s (%s)' % (self.nombre, self.entidad.name)
#
#
# class Alta_Baja2(models.Model):
#     entidad = models.ForeignKey(Entidad2)
#     gauser = models.ForeignKey('gauss_conf.Gauser2')
#     observaciones = models.TextField("Observaciones", null=True, blank=True)
#     fecha_alta = models.DateField('Fecha de alta', null=True, blank=True)
#     fecha_baja = models.DateField('Fecha de baja', null=True, blank=True)
#
#     class Meta:
#         verbose_name_plural = "Altas y bajas"
#
#     def __unicode__(self):
#         return u'%s (%s) - Alta: %s, Baja: %s' % (
#             self.gauser.get_full_name(), self.entidad.name, self.fecha_alta, self.fecha_baja)
#
#
# NIVELES = ((1, 'Cargo/Perfil de primer nivel'), (2, 'Cargo/Perfil de segundo nivel'),
#            (3, 'Cargo/Perfil de tercer nivel'), (4, 'Cargo/Perfil de cuarto nivel'),
#            (5, 'Cargo/Perfil de quinto nivel'), (6, 'Cargo/Perfil de sexto nivel'))
#
#
# class Cargo2(models.Model):
#     entidad = models.ForeignKey(Entidad2)
#     cargo = models.CharField("Cargo", max_length=200, null=True, blank=True)
#     permisos = models.ManyToManyField('gauss_conf.Permiso2', blank=True)
#     nivel = models.IntegerField('Nivel jerárquico en el organigrama', null=True, blank=True, choices=NIVELES,
#                                 default=NIVELES[0][0])
#
#     def __unicode__(self):
#         return u'%s' % (self.cargo)
#
#
# class Reserva_plaza2(models.Model):
#     entidad = models.ForeignKey(Entidad2)
#     first_name = models.CharField("Nombre", max_length=30, null=True, blank=True)
#     last_name = models.CharField("Apellidos", max_length=30, null=True, blank=True)
#     address = models.CharField("Dirección postal", max_length=100, null=True, blank=True)
#     sexo = models.CharField("Sexo", max_length=10, choices=SEXO, blank=True)
#     email = models.CharField("Correo electrónico", max_length=100, null=True, blank=True)
#     telfij = models.CharField("Teléfono fijo", max_length=30, null=True, blank=True)
#     telmov = models.CharField("Teléfono móvil", max_length=30, null=True, blank=True)
#     nacimiento = models.DateField("Fecha de nacimiento", blank=True, null=True)
#     first_name_tutor1 = models.CharField("Nombre", max_length=30, null=True, blank=True)
#     last_name_tutor1 = models.CharField("Apellidos", max_length=30, null=True, blank=True)
#     telfij_tutor1 = models.CharField("Teléfono fijo del primer tutor", max_length=30, null=True, blank=True)
#     telmov_tutor1 = models.CharField("Teléfono móvil del primer tutor", max_length=30, null=True, blank=True)
#     email_tutor1 = models.CharField("Correo electrónico del primer tutor", max_length=100, null=True, blank=True)
#     first_name_tutor2 = models.CharField("Nombre", max_length=30, null=True, blank=True)
#     last_name_tutor2 = models.CharField("Apellidos", max_length=30, null=True, blank=True)
#     telfij_tutor2 = models.CharField("Teléfono fijo del segundo tutor", max_length=30, null=True, blank=True)
#     telmov_tutor2 = models.CharField("Teléfono móvil del segundo tutor", max_length=30, null=True, blank=True)
#     email_tutor2 = models.CharField("Correo electrónico del primer tutor", max_length=100, null=True, blank=True)
#
#     def subentidades(self):  # Devuelve las subentidades a las que podría pertenecer
#         born = self.nacimiento
#         today = date.today()
#         try:
#             edad = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
#             return ' o '.join([s.nombre for s in Subentidad2.objects.filter(edad_min__lte=edad, edad_max__gte=edad)])
#         except:
#             return 'No es posible saberlo'  # Esto será devuelto cuando el gauser no tenga definido nacimiento
#
#     class Meta:
#         verbose_name_plural = "Reservas de plaza"
#
#     def __unicode__(self):
#         return u'%s %s (%s)' % (self.nombre, self.apellidos, self.nacimiento)
#
#
#
#
#
#
#
#
#
#
# class Permiso2(models.Model):
#     TIPOS = (
#         ('MEN', 'Permiso para acceder a un menú'),
#         ('SUB', 'Permiso para acceder a un submenú'),
#         ('MTE', 'Permiso para acceder a un elemento de un menú'),
#         ('STE', 'Permiso para acceder a un elemento de un submenú'),
#         ('ESP', 'Permiso especial para determinadas acciones'),
#     )
#     nombre = models.CharField("Nombre del permiso", max_length=100)
#     code_nombre = models.CharField("Código del permiso", max_length=50)
#     tipo = models.CharField("tipo", max_length=10)
#
#     class Meta:
#         ordering = ['pk']
#
#     def __unicode__(self):
#         return u'%s (%s)' % (self.nombre, self.code_nombre)
#         # return u'%s (%s)' % (self.nombre,self.code_nombre)
#
#
# # class Perfil(models.Model):
# # nombre = models.CharField("Nombre", max_length=50)
# # permisos = models.ManyToManyField(Permiso)
# #
# # class Meta:
# # verbose_name_plural = "perfiles"
# #         ordering = ['pk']
# #
# #     def __unicode__(self):
# #         return u'%s' % (self.nombre)
#
#
# # Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
# def update_foto(instance, filename):
#     nombre = filename.partition('.')
#     return os.path.join("fotos/", str(instance.entidad.code) + '_' + str(instance.id) + '.' + nombre[2])
#
#
# class Gauser2(AbstractUser):
#     sexo = models.CharField("Sexo", max_length=10, choices=SEXO, blank=True)
#     dni = models.CharField("DNI", max_length=20, null=True, blank=True)
#     address = models.CharField("Dirección", max_length=100, blank=True)
#     postalcode = models.CharField("Código postal", max_length=10, blank=True)
#     localidad = models.CharField("Localidad de residencia", max_length=50, blank=True)
#     provincia = models.CharField("Provincia", max_length=50, blank=True, choices=PROVINCIAS)
#     nacimiento = models.DateField("Fecha de nacimiento", blank=True, null=True)
#     telfij = models.CharField("Teléfono fijo", max_length=30, blank=True)
#     telmov = models.CharField("Teléfono móvil", max_length=30, blank=True)
#     familia = models.BooleanField("Familia numerosa", default=False)
#     fecha_alta = models.DateField("Fecha de alta en la entidad", blank=True, null=True)
#     fecha_baja = models.DateField("Fecha de baja en la entidad", blank=True, null=True)
#
#     @property
#     def has_mail(self):
#         if len(self.email) > 5:
#             return True
#
#     class Meta:
#         verbose_name_plural = "Usuarios (Gauser)"
#
#     def __unicode__(self):
#         if self.email:
#             texto = u'%s %s (%s)' % (self.first_name, self.last_name, self.email)
#         else:
#             texto = u'%s %s' % (self.first_name, self.last_name)
#         return texto
#
#
# class Gauser_extra2(models.Model):
#     gauser = models.ForeignKey(Gauser2, null=True, blank=True)
#     entidad = models.ForeignKey(Entidad2, null=True, blank=True)
#     subentidades = models.ManyToManyField(Subentidad2, blank=True)
#     subsubentidades = models.ManyToManyField(Subsubentidad2, blank=True)
#     cargos = models.ManyToManyField(Cargo2, blank=True)
#     ronda = models.ForeignKey(Ronda2, null=True, blank=True)
#     permisos = models.ManyToManyField(Permiso2, blank=True)
#     # perfiles = models.ManyToManyField(Perfil, null=True, blank=True)
#     id_organizacion = models.CharField("Nº de identificación general", max_length=20, blank=True, null=True)
#     id_entidad = models.CharField("Nº de identificación en la entidad", max_length=20, blank=True, null=True)
#     alias = models.CharField("Alias con el que te conocen", max_length=75, null=True, blank=True)
#     activo = models.BooleanField("Activo", default=False)
#     observaciones = models.TextField("Datos de interés a tener en cuenta", null=True, blank=True)
#     foto = models.ImageField("Fotografía", upload_to=update_foto, blank=True, null=True)
#     tutor1 = models.ForeignKey('self', null=True, blank=True, related_name='primer_tutor')
#     tutor2 = models.ForeignKey('self', null=True, blank=True, related_name='segundo_tutor')
#     hermanos = models.ManyToManyField('self', blank=True, related_name='hermanos')
#     ocupacion = models.CharField("Ocupación/Profesión del socio", max_length=300, blank=True, null=True)
#     banco = models.ForeignKey(Banco, null=True, blank=True)
#     entidad_bancaria = models.CharField("Entidad2 bancaria", max_length=50, blank=True, null=True)
#     num_cuenta_bancaria = models.CharField("Número de IBAN", max_length=50, blank=True, null=True)
#
#     def has_perfiles(self, perfiles_comprobar):  # Devuelve True (False) si (no) posee algún (ningún) perfiles_comprobar
#         if type(perfiles_comprobar) == list:
#             p_ids = self.perfiles.all().values_list('pk', flat=True)
#             return len([perfil for perfil in p_ids if perfil in perfiles_comprobar]) > 0
#         else:
#             return len([perfil for perfil in self.perfiles.all() if perfil in perfiles_comprobar]) > 0
#
#     def has_nivel(self, nivel):
#         return len([cargo for cargo in self.cargos if cargo.nivel <= nivel]) > 0
#
#     def has_cargos(self, cargos_comprobar):  # Devuelve True (False) si (no) posee algún (ningún) cargos_comprobar
#         if type(cargos_comprobar) == list:
#             p_ids = self.cargos.all().values_list('nivel', flat=True)
#             return len([cargo for cargo in p_ids if cargo in cargos_comprobar]) > 0
#         else:
#             return len([cargo for cargo in self.cargos.all() if cargo in cargos_comprobar]) > 0
#
#     def has_permiso(self, permiso_comprobar):
#         # Devuelve True o False dependiendo de si posee o no el permiso_comprobar
#         if permiso_comprobar == 'libre':
#             acceso = True
#         else:
#             permisos1 = self.permisos.all().values_list('id', flat=True)
#             permisos2 = []  #self.perfiles.all().values_list('permisos__id', flat=True)
#             permisos3 = self.cargos.all().values_list('permisos__id', flat=True)
#             permisos = Permiso2.objects.filter(id__in=list(set(list(permisos1) + list(permisos2) + list(permisos3))))
#             acceso = len([p for p in permisos if p.code_nombre == permiso_comprobar]) > 0
#         return acceso
#
#     @property
#     def permisos_list(self):  # Devuelve la lista de permisos que tiene
#         permisos1 = self.permisos.all().values_list('id', flat=True)
#         permisos2 = []  #self.perfiles.all().values_list('permisos__id', flat=True)
#         permisos3 = self.cargos.all().values_list('permisos__id', flat=True)
#         permisos = list(set(list(permisos1) + list(permisos2) + list(permisos3)))
#         return Permiso2.objects.filter(id__in=permisos)
#
#     @property
#     def es_padre(self):
#         tutores = Gauser_extra2.objects.filter(entidad=self.entidad, ronda=self.entidad.ronda).values_list('tutor1',
#                                                                                                           'tutor2')
#         # Flat la lista y eliminamos los elementos None
#         tutores = filter(None, set([e for l in tutores for e in l]))
#         return self.id in tutores
#
#     @property
#     def edad(self):
#         born = self.gauser.nacimiento
#         today = date.today()
#         try:
#             return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
#         except:
#             return 300  #Este entero será devuelto cuando el gauser no tenga definido nacimiento
#
#     @property
#     def unidad_familiar(self):
#         tutores = [self.id]
#         if self.tutor1:
#             tutores.append(self.tutor1.id)
#         if self.tutor2:
#             tutores.append(self.tutor2.id)
#         familia_ids = Gauser_extra2.objects.filter(Q(id__in=tutores) |
#                     Q(tutor1__id__in=tutores) | Q(tutor2__id__in=tutores), entidad=self.entidad,
#                     ronda=self.entidad.ronda).values_list('id', 'tutor1__id', 'tutor2__id')
#         ids = filter(None, set([e for l in familia_ids for e in l]))
#         return Gauser_extra2.objects.filter(id__in=ids).order_by('gauser__nacimiento')
#
#     # @property
#     # def perfiles_id(self):
#     #     p_ids = self.perfiles.all().values_list('pk', flat=True)
#     #     return p_ids
#
#     @property
#     def permisos_id(self):
#         p_ids = self.permisos.all().values_list('pk', flat=True)
#         # for perfil in self.perfiles.all():
#         #p_ids = p_ids + perfil.permisos.all().values_list('pk',flat=True)
#         return p_ids
#
#     # @property
#     # def familiares(self, cargo=False, subentidad=False):
#     #     # Devuelve los familiares de Gauser_extra2 que pertenecen a una subentidad, que tienen un determinado
#     #     # perfil/cargo o que cumplen las dos condiciciones:
#     #     tutores_id = []
#     #     if self.tutor1:
#     #         tutores_id.append(self.tutor1.id)
#     #     if self.tutor2:
#     #         tutores_id.append(self.tutor2.id)
#     #     if len(tutores_id) > 0:
#     #         hermanos = usuarios.filter(
#     #             Q(tutor1__id__in=tutores_id) | Q(tutor2__id__in=tutores_id)).distinct()
#     #
#     #     return p_ids
#
#     class Meta:
#         verbose_name_plural = "Datos extra de un usuario (Gauser_extra)"
#         ordering = ['gauser__last_name']
#
#     def __unicode__(self):
#         return u'%s -- %s -- %s' % (self.gauser.get_full_name(), self.entidad.name, self.ronda)
#
#
#
# ###########################################################
#
#
#
#
