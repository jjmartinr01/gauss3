# -*- coding: utf-8 -*-

from django.db import models
from django.template import Context, Template
from django.utils.text import slugify
from django.utils.timezone import now

from entidades.models import Cargo, Subentidad, Entidad
from entidades.models import Gauser_extra as GE
from gauss.funciones import pass_generator


def genera_identificador():
    return pass_generator(20)


class Gform(models.Model):
    DESTINATARIOS = (('ENT', 'Personas de mi entidad'), ('ORG', 'Personas de mi organización'))
    propietario = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
    colaboradores = models.ManyToManyField(GE, blank=True, related_name='gform_colaboradores')
    identificador = models.CharField('Código identificador del Gform', max_length=21, default=genera_identificador)
    destinatarios = models.CharField('Destinatarios del formulario', max_length=5, choices=DESTINATARIOS, default='ENT')
    # cargos_destino = models.ManyToManyField(Cargo, blank=True)
    # subentidades_destino = models.ManyToManyField(Subentidad, blank=True)
    nombre = models.CharField('Nombre del formulario', max_length=150)
    activo = models.BooleanField('El formulario esta activo', default=False)
    anonimo = models.BooleanField('Las respuestas son anónimas?', default=False)
    multiple = models.BooleanField('Se puede rellenar varias veces?', default=False)
    fecha_max_rellenado = models.DateTimeField('Fecha máxima para el rellenado', max_length=50, blank=True, null=True)
    template = models.TextField('Plantilla para crear PDF', blank=True, null=True, default='')
    observaciones = models.TextField('Notas aclaratorias para el formulario', blank=True, null=True, default='')
    creado = models.DateTimeField('Fecha de creación', auto_now_add=True)

    def get_rol(self, g_e):
        if g_e.gauser == self.propietario.gauser:
            return 'propietario' if g_e.gauser.sexo == 'H' else 'propietaria'
        elif self.colaboradores.filter(gauser=g_e.gauser).count() > 0:
            return 'colaborador' if g_e.gauser.sexo == 'H' else 'colaboradora'
        else:
            return 'Sin acceso'

    def is_propietario_o_colaborador(self, g_e):
        con1 = g_e.gauser == self.propietario.gauser
        con2 = self.colaboradores.filter(gauser=g_e.gauser).count() > 0
        return True if (con1 or con2) else False

    class Meta:
        ordering = ['propietario__ronda', 'id']

    @property
    def accesible(self):
        if self.fecha_max_rellenado:
            return True if (self.fecha_max_rellenado > now() and self.activo) else False
        else:
            return True if self.activo else False

    @property
    def num_respuestas(self):
        return self.gformresponde_set.filter(respondido=True).count()

    @property
    def template_procesado(self):
        template = Template(self.template)
        pregunta = {}
        respuesta = {}
        for gfsi in GformSectionInput.objects.filter(gformsection__gform=self):
            t = Template(gfsi.pregunta).render(Context())
            pregunta[gfsi.orden] = t
            if gfsi.tipo in ['RC', 'RL']:
                respuesta[gfsi.orden] = 'Lorem ipsum ' * 10
            elif gfsi.tipo in ['EM', 'SC', 'SO']:
                respuesta[gfsi.orden] = gfsi.gformsectioninputops_set.all()[0].opcion
            elif gfsi.tipo == 'SA':
                respuesta[gfsi.orden] = 'nombre_de_archivo_inventado.pdf'
            elif gfsi.tipo == 'EL':
                respuesta[gfsi.orden] = 2
            elif gfsi.tipo == 'FI':
                table = """{% autoescape off %}
                               <table><tr><td><img src="" style="height:140px;width:160px;" alt="Firma"></td></tr>
                               <tr><td><p>Nombre del firmante<br>Cargo</p></td></tr></table>{% endautoescape %}
                           """
                ctx = Context()
                respuesta[gfsi.orden] = Template(table).render(ctx)

        context = Context({'respuesta': respuesta, 'gform': self, 'pregunta': pregunta})
        return template.render(context)

    def __str__(self):
        activo = 'Formulario activo' if self.activo else 'Formulario desactivado'
        return '%s - %s (%s)' % (self.propietario.ronda.entidad.name, self.nombre, activo)


def guarda_archivo(instance, filename):
    nombre = filename.rpartition('.')
    instance.fich_name = filename.rpartition('/')[2]
    fichero = pass_generator(size=20) + '.' + nombre[2]
    return '/'.join(['formularios', str(instance.gform.propietario.ronda.entidad.code), fichero])


class GformSection(models.Model):
    gform = models.ForeignKey(Gform, on_delete=models.CASCADE)
    title = models.CharField('Título de la sección', max_length=150, blank=True, default='Título de la sección')
    description = models.TextField('Descripción', blank=True, null=True, default='Descripción')
    orden = models.IntegerField('Orden en el formulario')

    @property
    def render_gfs(self):
        template = """{% autoescape off %}
                       <h3>{{title}}</h3>
                       <span style='color:grey;'>{{description}}</span>{% endautoescape %}"""
        return Template(template).render(Context({'title': self.title, 'description': self.description}))

    class Meta:
        ordering = ['gform__id', 'orden']

    def __str__(self):
        return '%s - %s (%s)' % (self.orden, self.title, self.gform)


GSITIPOS = (('RC', 'Respuesta corta'), ('RL', 'Respuesta larga'), ('EM', 'Elección múltiple'),
            ('SC', 'Seleccionar casillas'), ('SO', 'Seleccionar opción'), ('SA', 'Subir archivo'),
            ('EL', 'Escala lineal'), ('FI', 'Firma del usuario'))


class GformSectionInput(models.Model):
    gformsection = models.ForeignKey(GformSection, blank=True, null=True, on_delete=models.CASCADE)
    orden = models.IntegerField("Orden dentro de la sección", blank=True, null=True)
    rellenador = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True, related_name='rellenador')
    creador = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
    tipo = models.CharField('Tipo de entrada', max_length=3, choices=GSITIPOS, default='RC')
    pregunta = models.TextField('Pregunta', default='Texto de la pregunta')
    elmin = models.IntegerField('Valor mínimo en la escal lineal', default=1)
    labelmin = models.CharField('Etiqueta min valor', max_length=30, default='Poco')
    elmax = models.IntegerField('Valor máximo en la escal lineal', default=5)
    labelmax = models.CharField('Etiqueta max valor', max_length=30, default='Mucho')
    requerida = models.BooleanField('¿Es obligatorio responder a esta pregunta?', default=True)

    @property
    def gfs(self):
        return self.gformsection

    class Meta:
        ordering = ['gformsection__gform__id', 'orden']

    def __str__(self):
        return '%s - %s... - %s' % (self.tipo, self.pregunta[:15], self.gformsection)


class GformSectionInputOps(models.Model):
    gformsectioninput = models.ForeignKey(GformSectionInput, on_delete=models.CASCADE)
    orden = models.IntegerField("Orden dentro de las posibles opciones", blank=True, null=True)
    opcion = models.CharField('Opción', blank=True, null=True, max_length=150, default='Esta es una opción')
    puntuacion = models.IntegerField('Puntuación si esta es la opción elegida', default=0)

    @property
    def gfsi(self):
        return self.gformsectioninput

    class Meta:
        ordering = ['gformsectioninput__id', 'orden']

    def __str__(self):
        return '%s - %s...' % (self.gformsectioninput, self.opcion[:15])


class GformResponde(models.Model):
    gform = models.ForeignKey(Gform, on_delete=models.CASCADE)
    g_e = models.ForeignKey(GE, on_delete=models.CASCADE)
    identificador = models.CharField('Identificador del destinatario', max_length=21, default=genera_identificador)
    respondido = models.BooleanField('¿Este cuestionario está respondido?', default=False)
    # borrado = models.BooleanField('¿Este cuestionario está borrado?', default=False)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    class Meta:
        ordering = ['gform', 'g_e']

    @property
    def template_procesado(self):
        template = Template(self.gform.template)
        pregunta = {}
        respuesta = {}
        for gfsi in GformSectionInput.objects.filter(gformsection__gform=self.gform):
            t = Template(gfsi.pregunta).render(Context())
            pregunta[gfsi.orden] = t

        for r in self.gformrespondeinput_set.all():
            respuesta[r.gfsi.orden] = r.respuesta
        context = Context({'respuesta': respuesta, 'gform': self.gform, 'pregunta': pregunta})
        return template.render(context)

    def __str__(self):
        return '%s - %s' % (self.gform, self.g_e.gauser.get_full_name())


def sube_archivo(instance, filename):
    nombre = filename.rpartition('.')
    fichero = slugify(nombre[0]) + '.' + nombre[2]
    entidad_code = str(instance.gformresponde.gform.propietario.ronda.entidad.code)
    gform = str(instance.gformresponde.gform.id)
    return '/'.join(['formularios', entidad_code, gform, fichero])


class GformRespondeInput(models.Model):
    gformresponde = models.ForeignKey(GformResponde, on_delete=models.CASCADE)
    gfsi = models.ForeignKey(GformSectionInput, on_delete=models.CASCADE)
    rtexto = models.TextField('Respuesta de texto', blank=True, null=True, default='')
    ropciones = models.ManyToManyField(GformSectionInputOps, blank=True)
    rfirma = models.TextField('Firma en base64', blank=True, null=True, default='')
    rfirma_nombre = models.CharField('Nombre del firmante', blank=True, null=True, default='', max_length=100)
    rfirma_cargo = models.CharField('Cargo del firmante', blank=True, null=True, default='', max_length=100)
    rentero = models.IntegerField('Respuesta número entero', blank=True, null=True)
    rarchivo = models.FileField('Respuesta tipo archivo', blank=True, null=True, upload_to=sube_archivo)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    feedback = models.TextField('Feedback sobre la evaluación de la respuesta proporcionada', blank=True, null=True)
    puntuacion = models.IntegerField('Puntuación a la respuesta dada', default=5)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    class Meta:
        ordering = ['gformresponde__identificador', 'gfsi__orden']

    @property
    def respuesta(self):
        if self.gfsi.tipo in ['RC', 'RL']:
            return Template(self.rtexto).render(Context())
        elif self.gfsi.tipo in ['EM', 'SC', 'SO']:
            texto = '; '.join([o.opcion for o in self.ropciones.all()])
            return Template(texto).render(Context())
        elif self.gfsi.tipo == 'SA':
            return self.rarchivo.name.rpartition('/')[2]
        elif self.gfsi.tipo == 'EL':
            return self.rentero
        elif self.gfsi.tipo == 'FI':
            template = """{% autoescape off %}
                           <table><tr><td><img src='{{ rfirma }}' style='width:120px;'></td></tr>
                           <tr><td><p>{{ rfirma_nombre }}<br>{{ rfirma_cargo }}</p></td></tr></table>{% endautoescape %}
                       """
            ctx = Context(
                {'rfirma': self.rfirma, 'rfirma_nombre': self.rfirma_nombre, 'rfirma_cargo': self.rfirma_cargo})
            return Template(template).render(ctx)

    def __str__(self):
        return '%s - %s' % (self.gformresponde, self.gfsi)





# TIPOS = (('gchar', 'Texto con un máximo de 150 caracteres'), ('gselect', 'Seleccionar uno o varios valores'),
#          ('gint', 'Número entero (sin decimales)'), ('gfloat', 'Número con decimales'), ('gbool', 'Respuesta Sí/No'),
#          ('gdatetime', 'Fecha y hora (dd/mm/yyyy HH:mm)'), ('gdate', 'Fecha (dd/mm/yyyy)'),
#          ('gtext', 'Texto de longitud ilimitada'), ('gfile', 'Archivo'))
#
# GRUPOS = (
#     (1, 'Grupo de preguntas 1'), (2, 'Grupo de preguntas 2'), (3, 'Grupo de preguntas 3'), (4, 'Grupo de preguntas 4'),
#     (5, 'Grupo de preguntas 5'), (6, 'Grupo de preguntas 6'), (7, 'Grupo de preguntas 7'), (8, 'Grupo de preguntas 8'),
#     (9, 'Grupo de preguntas 9'), (10, 'Grupo de preguntas 10'), (11, 'Grupo de preguntas 11'),
#     (12, 'Grupo de preguntas 12'), (13, 'Grupo de preguntas 13'), (14, 'Grupo de preguntas 14'),
#     (15, 'Grupo de preguntas 15'), (16, 'Grupo de preguntas 16'), (17, 'Grupo de preguntas 17'),
#     (18, 'Grupo de preguntas 18'), (19, 'Grupo de preguntas 19'), (20, 'Grupo de preguntas 20'))
#
#
# class Ginput(models.Model):
#     gform = models.ForeignKey(Gform, blank=True, null=True, on_delete=models.CASCADE)
#     grupo = models.IntegerField('Grupo de preguntas al que pertenece', choices=GRUPOS, default=1)
#     cargos_permitidos = models.ManyToManyField(Cargo, blank=True)  # Cargos que tienen acceso a esta Ginput
#     row = models.IntegerField("Número de fila", blank=True, null=True)
#     col = models.IntegerField("Número de columna", blank=True, null=True)
#     ancho = models.IntegerField("Número de columnas (anchura)", blank=True, null=True)
#     rellenador = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
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
#     ginput = models.ForeignKey('self', related_name='copia', blank=True, null=True, on_delete=models.CASCADE)
#     evaluable = models.BooleanField('Este Ginput es evaluable', default=False)
#
#     def __str__(self):
#         comentario = 'Original' if not self.ginput else self.rellenador.gauser.get_full_name()
#         return '%s, %s (Tipo: %s) - %s' % (self.gform.nombre, self.label, self.tipo, comentario)
#
#
# class Goption(models.Model):
#     ginput = models.ForeignKey(Ginput, blank=True, null=True, on_delete=models.CASCADE)
#     text = models.CharField('Text', max_length=150)
#     value = models.CharField('Value', max_length=50)
#     selected = models.BooleanField('Selected', default=False)
#
#     def __str__(self):
#         return '%s (%s) - Seleccionada: %s' % (self.text, self.value, self.selected)
#
#
# class IrGrupoSi(models.Model):
#     # Si la goption es "selected" (es True) entonces ir al grupo indicado
#     goption = models.ForeignKey(Goption, blank=True, null=True, on_delete=models.CASCADE)
#     grupo_siguiente = models.IntegerField('Grupo de preguntas al que pertenece', choices=GRUPOS, default=1)
#
#     @property
#     def cumple_condicion(self):
#         return self.goption.selected
#
#     @property
#     def grupo_actual(self):
#         return self.goption.ginput.grupo
#
#     # @property
#     def get_grupo_actual_display(self):
#         return self.goption.ginput.get_grupo_display()
#
#     @property
#     def grupo_anterior(self):
#         try:
#             return IrGrupoSi.objects.get(goption__ginput__gform=self.goption.ginput.gform, goption__selected=True,
#                                          grupo_siguiente=self.goption.ginput.grupo).grupo_actual
#         except:
#             return IrGrupoSi.objects.none()
#
#
# class EvalGinput(models.Model):
#     ginput = models.ForeignKey(Ginput, blank=True, null=True, on_delete=models.CASCADE)
#     evaluador = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
#     feedback = models.TextField('Evaluación de la respuesta a este Ginput', blank=True, null=True)
#     puntos = models.IntegerField('Valor numérico de la evaluación', blank=True, null=True)
#
#     def __str__(self):
#         return '%s (%s) - Seleccionada: %s' % (self.ginput, self.evaluador, self.puntos)
