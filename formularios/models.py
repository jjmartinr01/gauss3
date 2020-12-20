# -*- coding: utf-8 -*-
from django.db import models
from django.template import Context, Template
from django.utils.text import slugify

from entidades.models import Cargo, Subentidad, Entidad
from entidades.models import Gauser_extra as GE
from gauss.funciones import pass_generator


def genera_identificador():
    return pass_generator(20)


class Gform(models.Model):
    propietario = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
    identificador = models.CharField('Código identificador del Gform', max_length=21, default=genera_identificador)
    cargos_destino = models.ManyToManyField(Cargo, blank=True)
    subentidades_destino = models.ManyToManyField(Subentidad, blank=True)
    nombre = models.CharField('Nombre del formulario', max_length=150)
    activo = models.BooleanField('El formulario esta activo', default=False)
    anonimo = models.BooleanField('Las respuestas son anónimas?', default=False)
    fecha_max_rellenado = models.DateTimeField('Fecha máxima para el rellenado', max_length=50, blank=True, null=True)
    template = models.TextField('Plantilla para crear PDF', blank=True, null=True, default='')
    creado = models.DateTimeField('Fecha de creación', auto_now_add=True)

    class Meta:
        ordering = ['propietario__ronda', 'id']

    def template_procesado(self, identificador):
        template = Template(self.template)
        pregunta = {}
        respuesta = {}
        for gfsi in GformSectionInput.objects.filter(gformsection__gform=self):
            t = Template(gfsi.pregunta).render(Context())
            pregunta[gfsi.orden] = t
        if identificador:
            gformresponde = self.gformresponde_set.get(identificador=identificador)
            for r in gformresponde.gformrespondeinput_set.all():
                if r.gfsi.tipo == 'EL':
                    respuesta[r.gfsi.orden] = r.rentero
                elif r.gfsi.tipo == 'FI':
                    respuesta[r.gfsi.orden] = r.render_firma
                else:
                    respuesta[r.gfsi.orden] = Template(r.rtexto).render(Context())
        context = Context({'respuesta': respuesta, 'gform': self, 'pregunta': pregunta})
        return template.render(context)

    # @property
    # def contestados2(self):
    #     num_preguntas = self.ginput_set.filter(ginput__isnull=True).count()
    # Resto 1 para no contar el "original" :
    # return 0 if num_preguntas == 0 else self.ginput_set.all().count() / num_preguntas - 1
    #
    # @property
    # def contestados(self):
    #     return self.ginput_set.filter(ginput__isnull=False).values_list('rellenador__id', flat=True).distinct().count()
    #
    # @property
    # def num_preguntas(self):
    #     return self.ginput_set.filter(ginput__isnull=True).count()

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
    rellenador = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
    tipo = models.CharField('Tipo de entrada', max_length=3, choices=GSITIPOS, default='RC')
    pregunta = models.TextField('Pregunta', default='Texto de la pregunta')
    elmin = models.IntegerField('Valor mínimo en la escal lineal', default=1)
    labelmin = models.CharField('Etiqueta min valor', max_length=30, default='Poco')
    elmax = models.IntegerField('Valor máximo en la escal lineal', default=5)
    labelmax = models.CharField('Etiqueta max valor', max_length=30, default='Mucho')

    # firma = models.TextField('Firma requerida', null=True, blank=True)

    class Meta:
        ordering = ['gformsection__gform__id', 'orden']

    def __str__(self):
        return '%s - %s... - %s' % (self.tipo, self.pregunta[:15], self.gformsection)


class GformSectionInputOps(models.Model):
    gformsectioninput = models.ForeignKey(GformSectionInput, on_delete=models.CASCADE)
    orden = models.IntegerField("Orden dentro de las posibles opciones", blank=True, null=True)
    opcion = models.CharField('Opción', blank=True, null=True, max_length=150, default='Esta es una opción')
    puntuacion = models.IntegerField('Puntuación si esta es la opción elegida', default=0)

    class Meta:
        ordering = ['gformsectioninput__id', 'orden']

    def __str__(self):
        return '%s - %s...' % (self.gformsectioninput, self.opcion[:15])


class GformResponde(models.Model):
    gform = models.ForeignKey(Gform, on_delete=models.CASCADE)
    g_e = models.ForeignKey(GE, on_delete=models.CASCADE)
    identificador = models.CharField('Identificador del destinatario', max_length=21, default=genera_identificador)
    respondido = models.BooleanField('¿Este cuestionario está respondido?', default=False)

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
    rtexto = models.TextField('Respuesta de texto', blank=True, null=True)
    ropciones = models.ManyToManyField(GformSectionInputOps, blank=True)
    rfirma = models.TextField('Firma en base64', blank=True, null=True)
    rentero = models.IntegerField('Respuesta número entero', blank=True, null=True)
    rarchivo = models.FileField('Respuesta tipo archivo', blank=True, null=True, upload_to=sube_archivo)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    feedback = models.TextField('Feedback sobre la evaluación de la respuesta proporcionada', blank=True, null=True)
    puntuacion = models.IntegerField('Puntuación a la respuesta dada', default=5)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    class Meta:
        ordering = ['gformresponde__identificador', 'id']

    @property
    def render_firma(self):
        template = """{% autoescape off %}
                       <table><tr><td><img src='{{ rfirma }}' style='width:200px;'></td></tr>
                       <tr><td><p>{{ rtexto }}</p></td></tr></table>{% endautoescape %}"""
        return Template(template).render(Context({'rfirma': self.rfirma, 'rtexto': self.rtexto}))

    def __str__(self):
        return '%s - %s' % (self.gformresponde, self.gfsi)


# class GformSectionInputRespuesta(models.Model):
#     gformsectioninput = models.ForeignKey(GformSectionInput, on_delete=models.CASCADE)
#     rellenador = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
#     respuesta = models.TextField('Respuesta de texto', blank=True, null=True)
#     archivo = models.FileField('Respuesta tipo archivo', blank=True, null=True, upload_to=sube_archivo)
#     feedback = models.TextField('Feedback sobre la evaluación de la respuesta proporcionada', blank=True, null=True)
#     puntuacion = models.IntegerField('Puntuación a la respuesta dada', default=5)
#
#     class Meta:
#         ordering = ['gformsectioninput__gformsection__gform']
#
#     def __str__(self):
#         return '%s - %s...' % (self.gformsectioninput, self.respuesta[:15])


# class GformSectionInputRC(models.Model):
#     gformsectioninput = models.OneToOneField(GformSectionInput, on_delete=models.CASCADE)
#     respuesta = models.CharField('Respuesta corta', max_length=150, blank=True, null=True)
#     feedback = models.TextField('Feedback sobre la evaluación de la respuesta proporcionada', blank=True, null=True)
#     puntuacion = models.IntegerField('Puntuación a la respuesta dada', default=5)
#
#     def __str__(self):
#         return '%s - %s...' % (self.gformsectioninput, self.respuesta[:15])


# class GformSectionInputRL(models.Model):
#     gformsectioninput = models.OneToOneField(GformSectionInput, on_delete=models.CASCADE)
#     respuesta = models.TextField('Respuesta Larga', blank=True, null=True)
#     feedback = models.TextField('Feedback sobre la evaluación de la respuesta proporcionada', blank=True, null=True)
#     puntuacion = models.IntegerField('Puntuación a la respuesta dada', default=5)
#
#     def __str__(self):
#         return '%s - %s...' % (self.gformsectioninput, self.respuesta[:15])


# class GformSectionInputEM(models.Model):
#     gformsectioninput = models.OneToOneField(GformSectionInput, on_delete=models.CASCADE)
#     respuesta = models.TextField('Respuesta Larga', blank=True, null=True)
# feedback = models.TextField('Feedback sobre la evaluación de la respuesta proporcionada', blank=True, null=True)
# puntuacion = models.IntegerField('Puntuación a la respuesta dada', default=5)
#
# def __str__(self):
#     return '%s - %s...' % (self.gformsectioninput, self.respuesta[:15])


# class GformSectionInputEMO(models.Model):
#     gformsectioninputem = models.ForeignKey(GformSectionInputEM, on_delete=models.CASCADE)
#     orden = models.IntegerField("Orden dentro de las posibles opciones", blank=True, null=True)
#     opcion = models.CharField('Opción', blank=True, null=True, max_length=150)
#     opcion_elegida = models.BooleanField('¿Es la opción elegida?', default=False)
#     puntuacion = models.IntegerField('Puntuación si esta es la opción elegida', default=0)
#
#     def __str__(self):
#         return '%s - %s...' % (self.gformsectioninputem, self.opcion[:15])


# class GformSectionInputSC(models.Model):
#     gformsectioninput = models.OneToOneField(GformSectionInput, on_delete=models.CASCADE)
#     feedback = models.TextField('Feedback sobre la evaluación de la respuesta proporcionada', blank=True, null=True)
#     puntuacion = models.IntegerField('Puntuación a la respuesta dada', default=5)
#
#     def __str__(self):
#         return '%s - %s...' % (self.gformsectioninput, self.respuesta[:15])
#
#
# class GformSectionInputSCO(models.Model):
#     gformsectioninputsc = models.ForeignKey(GformSectionInputSC, on_delete=models.CASCADE)
#     orden = models.IntegerField("Orden dentro de las posibles opciones", blank=True, null=True)
#     opcion = models.CharField('Opción', blank=True, null=True, max_length=150)
#     opcion_elegida = models.BooleanField('¿Es la opción elegida?', default=False)
#     puntuacion = models.IntegerField('Puntuación si esta es la opción elegida', default=0)
#
#     def __str__(self):
#         return '%s - %s...' % (self.gformsectioninputsc, self.opcion[:15])
#

# class GformSectionInputSO(models.Model):
#     gformsectioninput = models.OneToOneField(GformSectionInput, on_delete=models.CASCADE)
#     feedback = models.TextField('Feedback sobre la evaluación de la respuesta proporcionada', blank=True, null=True)
#     puntuacion = models.IntegerField('Puntuación a la respuesta dada', default=5)
#
#     def __str__(self):
#         return '%s - %s...' % (self.gformsectioninput, self.respuesta[:15])
#
#
# class GformSectionInputSOO(models.Model):
#     gformsectioninputso = models.ForeignKey(GformSectionInputSO, on_delete=models.CASCADE)
#     orden = models.IntegerField("Orden dentro de las posibles opciones", blank=True, null=True)
#     opcion = models.CharField('Opción', blank=True, null=True, max_length=150)
#     opcion_elegida = models.BooleanField('¿Es la opción elegida?', default=False)
#     puntuacion = models.IntegerField('Puntuación si esta es la opción elegida', default=0)
#
#     def __str__(self):
#         return '%s - %s...' % (self.gformsectioninputso, self.opcion[:15])
#
#
#
#
# class GformSectionInputSA(models.Model):
#     gformsectioninput = models.OneToOneField(GformSectionInput, on_delete=models.CASCADE)
#     respuesta = models.FileField('Respuesta Larga', blank=True, null=True, upload_to=sube_archivo)
#     feedback = models.TextField('Feedback sobre la evaluación de la respuesta proporcionada', blank=True, null=True)
#     puntuacion = models.IntegerField('Puntuación a la respuesta dada', default=5)
#
#     def __str__(self):
#         return '%s - %s...' % (self.gformsectioninput, self.respuesta[:15])
#
#
# class GformSectionInputEL(models.Model):
#     gformsectioninput = models.OneToOneField(GformSectionInput, on_delete=models.CASCADE)
#     valor_min = models.IntegerField('Valor mínimo de la escala', default=1)
#     valor_max = models.IntegerField('Valor máximo de la escala', default=5)
#     respuesta = models.IntegerField('Respuesta', blank=True, null=True)
#
#     def __str__(self):
#         return '%s - %s...' % (self.gformsectioninput, self.respuesta[:15])


TIPOS = (('gchar', 'Texto con un máximo de 150 caracteres'), ('gselect', 'Seleccionar uno o varios valores'),
         ('gint', 'Número entero (sin decimales)'), ('gfloat', 'Número con decimales'), ('gbool', 'Respuesta Sí/No'),
         ('gdatetime', 'Fecha y hora (dd/mm/yyyy HH:mm)'), ('gdate', 'Fecha (dd/mm/yyyy)'),
         ('gtext', 'Texto de longitud ilimitada'), ('gfile', 'Archivo'))

GRUPOS = (
    (1, 'Grupo de preguntas 1'), (2, 'Grupo de preguntas 2'), (3, 'Grupo de preguntas 3'), (4, 'Grupo de preguntas 4'),
    (5, 'Grupo de preguntas 5'), (6, 'Grupo de preguntas 6'), (7, 'Grupo de preguntas 7'), (8, 'Grupo de preguntas 8'),
    (9, 'Grupo de preguntas 9'), (10, 'Grupo de preguntas 10'), (11, 'Grupo de preguntas 11'),
    (12, 'Grupo de preguntas 12'), (13, 'Grupo de preguntas 13'), (14, 'Grupo de preguntas 14'),
    (15, 'Grupo de preguntas 15'), (16, 'Grupo de preguntas 16'), (17, 'Grupo de preguntas 17'),
    (18, 'Grupo de preguntas 18'), (19, 'Grupo de preguntas 19'), (20, 'Grupo de preguntas 20'))


class Ginput(models.Model):
    gform = models.ForeignKey(Gform, blank=True, null=True, on_delete=models.CASCADE)
    grupo = models.IntegerField('Grupo de preguntas al que pertenece', choices=GRUPOS, default=1)
    cargos_permitidos = models.ManyToManyField(Cargo, blank=True)  # Cargos que tienen acceso a esta Ginput
    row = models.IntegerField("Número de fila", blank=True, null=True)
    col = models.IntegerField("Número de columna", blank=True, null=True)
    ancho = models.IntegerField("Número de columnas (anchura)", blank=True, null=True)
    rellenador = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
    tipo = models.CharField('Tipo de entrada', max_length=30, choices=TIPOS)
    label = models.CharField('Label', max_length=150)
    select = models.BooleanField('Es un select múltiple?', default=False)
    gchar = models.CharField('Texto con un máximo de 150 caracteres', max_length=150, blank=True, null=True)
    gint = models.IntegerField('Número entero (sin decimales)', blank=True, null=True)
    gfloat = models.FloatField('Número con decimales', max_length=50, blank=True, null=True)
    gdate = models.DateField('Fecha (dd/mm/yyyy)', max_length=50, blank=True, null=True)
    gdatetime = models.DateTimeField('Fecha y hora (dd/mm/yyyy HH:mm)', max_length=50, blank=True, null=True)
    gtext = models.TextField('Texto de longitud ilimitada', blank=True, null=True)
    gbool = models.BooleanField('Respuesta Sí/No', default=False)
    archivo = models.FileField('Archivo', blank=True, null=True, upload_to=guarda_archivo)
    content_type_archivo = models.CharField('Tipo de archivo', max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)
    ginput = models.ForeignKey('self', related_name='copia', blank=True, null=True, on_delete=models.CASCADE)
    evaluable = models.BooleanField('Este Ginput es evaluable', default=False)

    def __str__(self):
        comentario = 'Original' if not self.ginput else self.rellenador.gauser.get_full_name()
        return '%s, %s (Tipo: %s) - %s' % (self.gform.nombre, self.label, self.tipo, comentario)


class Goption(models.Model):
    ginput = models.ForeignKey(Ginput, blank=True, null=True, on_delete=models.CASCADE)
    text = models.CharField('Text', max_length=150)
    value = models.CharField('Value', max_length=50)
    selected = models.BooleanField('Selected', default=False)

    def __str__(self):
        return '%s (%s) - Seleccionada: %s' % (self.text, self.value, self.selected)


class IrGrupoSi(models.Model):
    # Si la goption es "selected" (es True) entonces ir al grupo indicado
    goption = models.ForeignKey(Goption, blank=True, null=True, on_delete=models.CASCADE)
    grupo_siguiente = models.IntegerField('Grupo de preguntas al que pertenece', choices=GRUPOS, default=1)

    @property
    def cumple_condicion(self):
        return self.goption.selected

    @property
    def grupo_actual(self):
        return self.goption.ginput.grupo

    # @property
    def get_grupo_actual_display(self):
        return self.goption.ginput.get_grupo_display()

    @property
    def grupo_anterior(self):
        try:
            return IrGrupoSi.objects.get(goption__ginput__gform=self.goption.ginput.gform, goption__selected=True,
                                         grupo_siguiente=self.goption.ginput.grupo).grupo_actual
        except:
            return IrGrupoSi.objects.none()


class EvalGinput(models.Model):
    ginput = models.ForeignKey(Ginput, blank=True, null=True, on_delete=models.CASCADE)
    evaluador = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True)
    feedback = models.TextField('Evaluación de la respuesta a este Ginput', blank=True, null=True)
    puntos = models.IntegerField('Valor numérico de la evaluación', blank=True, null=True)

    def __str__(self):
        return '%s (%s) - Seleccionada: %s' % (self.ginput, self.evaluador, self.puntos)
