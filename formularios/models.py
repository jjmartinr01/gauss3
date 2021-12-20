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


class GformDestinatario(models.Model):
    gform = models.ForeignKey(Gform, on_delete=models.CASCADE)
    destinatario = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True,
                                     related_name='get_destinatarios')
    corrector = models.ForeignKey(GE, on_delete=models.SET_NULL, blank=True, null=True, related_name='get_correctores')

    def __str__(self):
        return '%s -- Dest: %s Corr: %s' % (self.gform, self.destinatario, self.corrector)


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
            ('EL', 'Escala lineal'), ('FI', 'Firma del usuario'), ('EN', 'Número entero'))


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
        elif self.gfsi.tipo == 'EN':
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

#########################################################################
################## Evaluación docentes en prácticas #####################
#########################################################################

class EvalFunPract(models.Model):  # Evaluación Funcionarios en Prácticas
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre del cuestionario', max_length=200, blank=True, null=True)
    observaciones_ins = models.TextField('Observaciones para el inspector', blank=True, null=True, default='')
    observaciones_doc = models.TextField('Observaciones para el docente', blank=True, null=True, default='')
    observaciones_tut = models.TextField('Observaciones para el tutor', blank=True, null=True, default='')
    observaciones_dir = models.TextField('Observaciones para el director', blank=True, null=True, default='')
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    @property
    def cuestiones(self):
        return EvalFunPractDimSubCue.objects.filter(evalfunpractdimsub__evalfunpractdim__evalfunpract=self)

    @property
    def efpdscs(self):
        return EvalFunPractDimSubCue.objects.filter(evalfunpractdimsub__evalfunpractdim__evalfunpract=self)

    @property
    def num_dim(self):
        return self.evalfunpractdim_set.all().count()

    @property
    def num_subdim(self):
        return EvalFunPractDimSub.objects.filter(evalfunpractdim__evalfunpract=self).count()

    @property
    def num_cuestiones(self):
        return EvalFunPractDimSubCue.objects.filter(evalfunpractdimsub__evalfunpractdim__evalfunpract=self).count()

    class Meta:
        ordering = ['pk', ]

    def __str__(self):
        return 'Cuestionario de Evaluación de Funcionarios en Prácticas - %s' % (self.pk)


class EvalFunPractDim(models.Model):  # Dimensión
    evalfunpract = models.ForeignKey(EvalFunPract, on_delete=models.CASCADE)
    dimension = models.TextField('Dimensión a evaluar')
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    @property
    def valor(self):
        return sum(list(self.evalfunpractdimsub_set.all().values_list('valor', flat=True)))

    class Meta:
        ordering = ['evalfunpract', ]

    def __str__(self):
        return '%s - %s' % (self.evalfunpract, self.dimension)


class EvalFunPractDimSub(models.Model):  # Subdimension
    evalfunpractdim = models.ForeignKey(EvalFunPractDim, on_delete=models.CASCADE)
    subdimension = models.TextField('Subdimensión a evaluar')
    valor = models.IntegerField('Valor total de esta subdimensión', default=10)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    class Meta:
        ordering = ['evalfunpractdim', ]

    def __str__(self):
        return '%s - %s' % (self.evalfunpractdim, self.subdimension)


class EvalFunPractDimSubCue(models.Model):  # Cuestion
    evalfunpractdimsub = models.ForeignKey(EvalFunPractDimSub, on_delete=models.CASCADE)
    pregunta = models.TextField('Texto de la pregunta a responder')
    responde_ins = models.BooleanField('¿Esta cuestión la responde el inspector?', default=False)
    responde_doc = models.BooleanField('¿Esta cuestión la responde el docente?', default=True)
    responde_doc_jefe = models.BooleanField('¿La responde el docente si es jefe de departamento?', default=True)
    responde_doc_tutor = models.BooleanField('¿La responde el docente si es tutor de un grupo?', default=True)
    responde_doc_orientador = models.BooleanField('¿La responde el docente si es orientador?', default=True)
    responde_tut = models.BooleanField('¿Esta cuestión la responde el tutor?', default=True)
    responde_dir = models.BooleanField('¿Esta cuestión la responde el director?', default=True)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    class Meta:
        ordering = ['evalfunpractdimsub', 'pk']

    def __str__(self):
        return '%s -> ins: %s, doc:%s, tut:%s, dir:%s' % (self.pregunta[:50], self.responde_ins, self.responde_doc,
                                                          self.responde_tut, self.responde_dir)


class ProcesoEvalFunPract(models.Model):
    nombre = models.CharField('Nombre', max_length=210, blank=True, null=True)
    g_e = models.ForeignKey(GE, on_delete=models.CASCADE, null=True, blank=True)
    evalfunpract = models.ForeignKey(EvalFunPract, on_delete=models.CASCADE)
    identificador = models.CharField('Identificador del Cuestionario', max_length=21, default=genera_identificador)
    fecha_min = models.DateField('Fecha inicio para rellenar', null=True, blank=True)
    fecha_max = models.DateField('Fecha final para rellenar', null=True, blank=True)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    @property
    def is_activo(self):
        hoy = now().date()
        if (hoy >= self.fecha_min) and (hoy <= self.fecha_max):
            return True
        else:
            return False

    def __str__(self):
        return '%s -> %s' % (self.nombre, self.evalfunpract)


class EvalFunPractAct(models.Model):  # Evaluación Funcionarios en Prácticas Actores
    procesoevalfunpract = models.ForeignKey(ProcesoEvalFunPract, on_delete=models.CASCADE, null=True, blank=True)
    inspector = models.ForeignKey(GE, on_delete=models.CASCADE, related_name='get_inspector')
    tutor = models.ForeignKey(GE, on_delete=models.CASCADE, related_name='get_tutor')
    director = models.ForeignKey(GE, on_delete=models.CASCADE, related_name='get_director')
    docente = models.ForeignKey(GE, on_delete=models.CASCADE, related_name='get_docente')
    docente_jefe = models.BooleanField('¿El docente en practicas es jefe de departamento?', default=False)
    docente_tutor = models.BooleanField('¿El docente en practicas es tutor de un grupo de alumnos?', default=False)
    docente_orientador = models.BooleanField('¿El docente en practicas es orientador?', default=False)
    respondido_ins = models.BooleanField('¿Este cuestionario está respondido por el inspector?', default=False)
    respondido_doc = models.BooleanField('¿Este cuestionario está respondido por el docente?', default=False)
    respondido_tut = models.BooleanField('¿Este cuestionario está respondido por el tutor?', default=False)
    respondido_dir = models.BooleanField('¿Este cuestionario está respondido por el director?', default=False)
    fecha_min = models.DateField('Fecha inicio para rellenar', null=True, blank=True)
    fecha_max = models.DateField('Fecha final para rellenar', null=True, blank=True)
    actualiza_efprs = models.BooleanField('¿Se deben actualizar las efprs?', default=False)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    @property
    def is_activo(self):
        hoy = now().date()
        if (hoy >= self.fecha_min) and (hoy <= self.fecha_max):
            return True
        else:
            return False

    @property
    def efprs_docente(self):
        evalfprs_totales = self.evalfunpractres_set.all()
        if self.docente_orientador:
            evalfprs = evalfprs_totales.filter(evalfunpractdimsubcue__responde_doc_orientador=True)
        elif self.docente_tutor and self.docente_jefe:
            q = models.Q(evalfunpractdimsubcue__responde_doc_tutor=True) | models.Q(
                evalfunpractdimsubcue__responde_doc_jefe=True)
            evalfprs = evalfprs_totales.filter(q).distinct()
        elif self.docente_tutor:
            evalfprs = evalfprs_totales.filter(evalfunpractdimsubcue__responde_doc_tutor=True)
        elif self.docente_jefe:
            evalfprs = evalfprs_totales.filter(evalfunpractdimsubcue__responde_doc_jefe=True)
        else:
            evalfprs = evalfprs_totales.filter(evalfunpractdimsubcue__responde_doc=True)
        return evalfprs

    def efprs(self, destinatario):
        evalfprs_totales = self.evalfunpractres_set.all()
        if self.docente_orientador:
            evalfprs = evalfprs_totales.filter(evalfunpractdimsubcue__responde_doc_orientador=True)
        elif self.docente_tutor and self.docente_jefe:
            q = models.Q(evalfunpractdimsubcue__responde_doc_tutor=True) | models.Q(
                evalfunpractdimsubcue__responde_doc_jefe=True)
            evalfprs = evalfprs_totales.filter(q).distinct()
        elif self.docente_tutor:
            evalfprs = evalfprs_totales.filter(evalfunpractdimsubcue__responde_doc_tutor=True)
        elif self.docente_jefe:
            evalfprs = evalfprs_totales.filter(evalfunpractdimsubcue__responde_doc_jefe=True)
        else:
            evalfprs = evalfprs_totales.filter(evalfunpractdimsubcue__responde_doc=True)
        # if destinatario == 'docente':
        #     return evalfprs
        if destinatario == 'tutor':
            return evalfprs.filter(evalfunpractdimsubcue__responde_tut=True)
        elif destinatario == 'director':
            return evalfprs.filter(evalfunpractdimsubcue__responde_dir=True)
        elif destinatario == 'inspector':
            return evalfprs.filter(evalfunpractdimsubcue__responde_ins=True)
        else:
            return evalfprs

    @property
    def calificacion_maxima_posible(self):
        cal_max_pos = 0
        for dim in self.procesoevalfunpract.evalfunpract.evalfunpractdim_set.all():
            cal_max_pos += dim.valor
        return cal_max_pos

    def cal_efpr(self, efpr):
        return efpr.calificacion

    def cal_subdim(self, subdim):
        subdim_efprs = self.efprs('docente').filter(evalfunpractdimsubcue__evalfunpractdimsub=subdim)
        calificacion = 0
        calificacion_maxima = 0
        for subdim_efpr in subdim_efprs:
            calificacion += self.cal_efpr(subdim_efpr)
            calificacion_maxima += 5
        try:
            return calificacion / calificacion_maxima * subdim.valor
        except:
            return -1

    def cal_dim(self, dim):
        calificacion = 0
        for subdim in dim.evalfunpractdimsub_set.all():
            calificacion += self.cal_subdim(subdim)
        return calificacion

    @property
    def cal_total(self):
        try:
            calificacion = 0
            for dim in self.procesoevalfunpract.evalfunpract.evalfunpractdim_set.all():
                calificacion += self.cal_dim(dim)
            if calificacion > 0:
                return round(calificacion, 2)
            else:
                return '---'
        except:
            return '-*-'

    class Meta:
        ordering = ['procesoevalfunpract', 'docente__ronda__entidad']

    # @property
    # def template_procesado(self):
    #     template = Template(self.gform.template)
    #     pregunta = {}
    #     respuesta = {}
    #     for gfsi in GformSectionInput.objects.filter(gformsection__gform=self.gform):
    #         t = Template(gfsi.pregunta).render(Context())
    #         pregunta[gfsi.orden] = t
    #
    #     for r in self.gformrespondeinput_set.all():
    #         respuesta[r.gfsi.orden] = r.respuesta
    #     context = Context({'respuesta': respuesta, 'gform': self.gform, 'pregunta': pregunta})
    #     return template.render(context)

    def __str__(self):
        return '%s - %s' % (self.procesoevalfunpract, self.inspector.gauser.get_full_name())


class EvalFunPractRes(models.Model):  # Evaluación Funcionarios en Prácticas Respuestas
    evalfunpractact = models.ForeignKey(EvalFunPractAct, on_delete=models.CASCADE)
    evalfunpractdimsubcue = models.ForeignKey(EvalFunPractDimSubCue, on_delete=models.CASCADE)
    respuesta_ins = models.IntegerField('Respuesta del inspector', null=True, blank=True, default=-1)
    respuesta_doc = models.IntegerField('Respuesta del docente', null=True, blank=True, default=-1)
    respuesta_tut = models.IntegerField('Respuesta del tutor', null=True, blank=True, default=-1)
    respuesta_dir = models.IntegerField('Respuesta del director', null=True, blank=True, default=-1)
    inspector = models.IntegerField('Respuesta del inspector', null=True, blank=True, default=-1)
    docente = models.IntegerField('Respuesta del docente', null=True, blank=True, default=-1)
    tutor = models.IntegerField('Respuesta del tutor', null=True, blank=True, default=-1)
    director = models.IntegerField('Respuesta del director', null=True, blank=True, default=-1)
    obsdocente = models.TextField('Observaciones del docente', null=True, blank=True, default='')
    obsdirector = models.TextField('Observaciones del director', null=True, blank=True, default='')
    obstutor = models.TextField('Observaciones del tutor', null=True, blank=True, default='')
    obsinspector = models.TextField('Observaciones del inspector', null=True, blank=True, default='')
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    @property
    def num_cues_subdim(self):
        efpa = self.evalfunpractact
        subdim = self.evalfunpractdimsubcue.evalfunpractdimsub
        return efpa.efprs('docente').filter(evalfunpractdimsubcue__evalfunpractdimsub=subdim).count()

    @property
    def calificacion(self):
        num_actores = 0  # Partimos de la suposición de que no ha respondido ninguno de los actores
        cal = 0  # La calificación inicial es 0
        if self.evalfunpractdimsubcue.responde_dir:
            if self.director > -1:
                num_actores += 1
                cal += self.director
        if self.evalfunpractdimsubcue.responde_ins:
            if self.inspector > -1:
                num_actores += 1
                cal += self.inspector
        if self.evalfunpractdimsubcue.responde_tut:
            if self.tutor > -1:
                num_actores += 1
                cal += self.tutor
        if self.docente > -1:
            num_actores += 1
            cal += self.docente
        try:
            return cal / num_actores
        except:
            return -1

    @property
    def calificacion_relativa(self):
        subdim = self.evalfunpractdimsubcue.evalfunpractdimsub
        cal_max_cues = 5
        try:
            return self.calificacion / cal_max_cues * subdim.valor / self.num_cues_subdim
        except:
            return '---'

    class Meta:
        ordering = ['evalfunpractact', 'evalfunpractdimsubcue']

    def __str__(self):
        return '%s -> ins: %s, doc:%s, tut:%s, dir:%s' % (self.evalfunpractdimsubcue.pregunta[:50], self.respuesta_ins,
                                                          self.respuesta_doc, self.respuesta_tut, self.respuesta_dir)


CUE = [
    {'dim': 'DEDICACIÓN AL CENTRO',
     'subdims': [
         {
             'subdim': 'Participación en los órganos colegiados y de coordinación del docente, así como en iniciativas para mejorar la práctica docente y el trabajo en equipo.',
             'valor': 2,
             'pregs': [
                 {'subsub': 'Participación en los órganos de gobierno',
                  'preg': 'Se interesa por lo tratado en el consejo escolar, pidiendo información y haciendo propuestas a sus representantes y al equipo directivo.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de gobierno',
                  'preg': 'Participa activamente en el claustro, haciendo propuestas viables sobre los temas que figuran en el orden del día y propone, para su discusión, iniciativas de interés general.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de gobierno',
                  'preg': 'Asume responsabilidades como miembro del claustro participando en las iniciativas de este órgano.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de gobierno',
                  'preg': 'Realiza propuestas para la elaboración, modificación y actualización de los documentos generales del centro: programación general anual (criterios pedagógicos para la elaboración de horarios, necesidades de equipamiento, etc.), proyecto educativo de centro, plan de convivencia, reglamento de organización y funcionamiento, etc.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Coordina y participa activamente en la elaboración de la programación didáctica del departamento, de acuerdo con los criterios fijados por la comisión de coordinación pedagógica y con las directrices generales del proyecto educativo.',
                  'docente': False,
                  'docente-jefe': True,
                  'docente-tutor': False,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Convoca y prepara las reuniones del departamento; deja constancia escrita de los acuerdos alcanzados;  hace el seguimiento de los mismos; comenta con los profesores del departamento la marcha del curso y propone, si es necesario, cambios en la programación para adaptarla a las necesidades observadas.',
                  'docente': False,
                  'docente-jefe': True,
                  'docente-tutor': False,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'En su caso, coordina y asume las tareas fijadas por el departamento para la atención de los alumnos con necesidades específicas de apoyo educativo programadas en colaboración con los servicios de apoyo.',
                  'docente': False,
                  'docente-jefe': True,
                  'docente-tutor': False,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Participa activamente en las reuniones de la comisión de coordinación pedagógica aportando iniciativas y sugerencias –tanto propias como de sus compañeros- para el cumplimiento de sus competencias, e informa a los miembros de su departamento de las resoluciones aprobadas.',
                  'docente': False,
                  'docente-jefe': True,
                  'docente-tutor': False,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Coordina y asume las tareas relativas a la organización de los espacios e instalaciones, así como la adquisición del material didáctico y científico (destinado a profesores y alumnos) necesario para el departamento; tomando iniciativas para facilitar su uso.',
                  'docente': False,
                  'docente-jefe': True,
                  'docente-tutor': False,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Participa activamente en la elaboración de la programación didáctica del departamento.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': True,
                  'orientador': False, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
{'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Participa activamente en la elaboración de las programaciones didácticas, en todo lo referente a la atención a la diversidad.',
                  'docente': False,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Participa activamente en las reuniones del departamento, comenta la marcha del curso y propone, si es necesario, cambios en la programación para adaptarla a las necesidades observadas.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': True,
                  'orientador': False, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
{'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Participa activamente en las reuniones de los órganos de coordinación docente,  comenta la marcha del curso y propone, si es necesario, cambios en la programación para adaptarla a las necesidades observadas.',
                  'docente': False,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'En su caso, asume las tareas fijadas por el departamento para la atención de los alumnos con necesidades específicas de apoyo educativo.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Conoce las resoluciones adoptadas en la comisión de coordinación pedagógica y propone, a través del jefe del departamento, iniciativas sobre el desarrollo de sus funciones y competencias.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Hace propuestas sobre material de interés para el departamento, tanto del destinado a los alumnos como del que pueda favorecer la actualización didáctica y científica del profesorado, tomando iniciativas para facilitar su uso.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': True,
                  'orientador': False, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
{'subsub': 'Participación en los órganos de coordinación docente',
                  'preg': 'Hace propuestas sobre material de interés para los alumnos del centro, tanto del destinado a los alumnos como del que pueda favorecer la actualización didáctica y científica del profesorado, tomando iniciativas para facilitar su uso.',
                  'docente': False,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Adopción de iniciativas para la mejora de la práctica docente y del trabajo en equipo',
                  'preg': 'Aporta datos y criterios de evaluación de su propia práctica docente y de la del departamento, promoviendo  que ésta se haga a través de la revisión de los elementos y desarrollo de la programación didáctica.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
{'subsub': 'Adopción de iniciativas para la mejora de la práctica docente y del trabajo en equipo',
                  'preg': 'Aporta datos y criterios de evaluación de su propia práctica docente, promoviendo que ésta se haga a través de la revisión de los elementos y desarrollo de las unidades de intervención.',
                  'docente': False,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Adopción de iniciativas para la mejora de la práctica docente y del trabajo en equipo',
                  'preg': 'Promueve la participación en diversas iniciativas de mejora y de trabajo en equipo, tanto en programas institucionales  como en otros,  así como el intercambio de experiencias sobre aspectos didácticos con otros profesores.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': 'Adopción de iniciativas para la mejora de la práctica docente y del trabajo en equipo',
                  'preg': 'Promueve la participación del departamento en actividades de formación: haciendo propuestas de grupos de trabajo, aportando información de cursos que puedan ser de interés, etc.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
    {'subsub': 'Adopción de iniciativas para la mejora de la práctica docente y del trabajo en equipo',
                  'preg': 'Promueve la participación en actividades de formación: haciendo propuestas de grupos de trabajo, aportando información de cursos que puedan ser de interés, etc.',
                  'docente': False,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  }
             ]},
         {
             'subdim': 'Colaboración y puesta en marcha de actividades extraescolares y de cualesquiera otras que dinamicen la vida del centro y que contribuyan al aprovechamiento de los recursos del entorno.',
             'valor': 4,
             'pregs': [
                 {'subsub': '',
                  'preg': 'Presenta propuestas y participa en la organización de la biblioteca escolar, en colaboración con la jefatura de estudios.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': '',
                  'preg': 'Propone, planifica y asume la realización de actividades complementarias y extraescolares, incluyéndolas en la programación didáctica, en su caso.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': '',
                  'preg': 'Prepara las visitas con el grupo clase y, cuando sea necesario, con los padres, presentándolas e informando de los objetivos de la actividad y de su relación con el resto de las actividades.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  },
                 {'subsub': '',
                  'preg': 'Elabora y/o utiliza guías didácticas, documentación y, en general, los recursos didácticos convenientes, planifica tareas que deben realizar los alumnos durante las actividades complementarias y valora su esfuerzo y grado de participación.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': True,
                  'tutor': False,
                  'inspector': False
                  }
             ]},
         {'subdim': 'Atención a padres y alumnos y, en su caso, ejercicio de la tutoría.',
          'valor': 4,
          'pregs': [
              {'subsub': '',
               'preg': 'Se muestra disponible para atender las demandas de los alumnos, incluso fuera de clase.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Informa por escrito, al menos tres veces en el curso, a los padres de los alumnos sobre el aprovechamiento académico de estos y la marcha de su proceso educativo, orientándolos, cuando sea preciso, en los procesos de reclamación.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Identifica las dificultades de aprendizaje y adopta las medidas de carácter general correspondientes (técnicas de estudio, orientaciones, etc.).',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Toma las iniciativas necesarias para facilitar la integración de cada alumno en su grupo y de éste en las actividades del centro.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Facilita y lleva a cabo –tanto por iniciativa propia como por demanda de los padres- entrevistas y reuniones, tanto individuales como colectivas, a fin de informarles sobre el funcionamiento del centro y la marcha académica de sus hijos.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Toma iniciativas para abordar, junto con los padres, aspectos tales como la creación de hábitos de autonomía y responsabilidad en los alumnos.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Cumple el plan de acción tutorial, siguiendo las directrices del jefe de estudios y de los profesionales  del departamento de orientación.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'A lo largo del curso lleva a cabo, de manera sistemática, actividades para la organización del aula (distribución de responsabilidades, informaciones de interés para los alumnos, resolución de conflictos, establecimiento de normas de convivencia, etc.)',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Realiza el seguimiento periódico y sistemático de las faltas de puntualidad y asistencia de sus alumnos, interesándose por los motivos e informando a sus padres y, en su caso, profesores, oportunamente.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Coordina las sesiones de evaluación y elabora, custodia y facilita los informes derivados de las mismas.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Propicia el análisis y la reflexión sobre los resultados de la evaluación , informando a padres y alumnos sobre las medidas adoptadas en la sesión correspondiente.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Coordina el equipo docente en la adopción, aplicación y seguimiento de medidas de apoyo para las dificultades del aprendizaje y de cuantos acuerdos se hayan tomado, no sólo en las sesiones de evaluación, sino también mediante contactos y reuniones periódicas, convocadas a tal efecto, con los distintos profesores del grupo.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Tiene iniciativa y colabora, en su caso, con los profesionales del departamento de orientación.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Es mediador y facilitador de las relaciones entre las familias, el profesorado y el centro escolar.',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Durante su permanencia en el centro, muestra disposición para atender las necesidades del mismo (sustituciones, proyectos, apoyos, etc.)',
               'docente': False,
               'docente-jefe': False,
               'docente-tutor': True,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Se muestra disponible para atender las demandas de los alumnos, incluso fuera de clase.',
               'docente': True,
               'docente-jefe': True,
               'docente-tutor': False,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Proporciona, en su caso,  a los tutores los datos necesarios para que puedan informar por escrito, al menos tres veces en el curso, a los padres sobre el aprovechamiento académico de los alumnos y la marcha de su proceso educativo.',
               'docente': True,
               'docente-jefe': True,
               'docente-tutor': False,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Identifica las dificultades de aprendizaje y adopta las medidas de carácter general correspondientes (técnicas de estudio, orientaciones, etc.).',
               'docente': True,
               'docente-jefe': True,
               'docente-tutor': False,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Participa activamente en las reuniones de padres convocadas por los tutores de los grupos de sus alumnos y proporciona información y orientación sobre las áreas que imparte.',
               'docente': True,
               'docente-jefe': True,
               'docente-tutor': False,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Informa a los padres de las horas en las que está disponible, atiende sus demandas y propicia el contacto con ellos para resolver las dificultades de sus hijos, informándoles sobre su marcha académica y las medidas adoptadas.',
               'docente': True,
               'docente-jefe': True,
               'docente-tutor': False,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Asume las medidas que se adoptan en las sesiones de evaluación, (adaptaciones, medidas de refuerzo, decisiones de promoción...).',
               'docente': True,
               'docente-jefe': True,
               'docente-tutor': False,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               },
              {'subsub': '',
               'preg': 'Durante su permanencia en el centro, muestra disposición para atender las necesidades del mismo (sustituciones, proyectos, apoyos, etc.)',
               'docente': True,
               'docente-jefe': True,
               'docente-tutor': False,
               'orientador': True, 'director': True,
               'tutor': False,
               'inspector': False
               }
          ]}
     ]},
    {'dim': 'ACTIVIDAD DOCENTE DENTRO DEL AULA',
     'subdims': [
         {
             'subdim': 'Preparación de la clase y de los materiales didácticos en el marco de las decisiones  adoptadas en la programación didáctica.',
             'valor': 6,
             'pregs': [
                 {'subsub': '',
                  'preg': 'Planifica el desarrollo de las unidades didácticas o de programación, organizándolas a lo largo del curso con una distribución adecuada, incluyendo actividades que se ajusten a las características de cada grupo (nivel de conocimientos previos, sus intereses, etc.).',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': '',
                  'preg': 'Planifica el desarrollo de las actuaciones, organizándolas a lo largo del curso con una distribución adecuada, incluyendo actividades que se ajusten a las características de cada grupo (nivel de conocimientos previos, sus intereses, etc.).',
                  'docente': False,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Planifica el desarrollo de las clases de modo flexible, teniendo en cuenta y preparando los materiales didácticos –ajustados a las características de sus alumnos y a la metodología escogida en cada momento-, previendo los medios (organización de espacios y recursos) que se van a necesitar, así como las correspondientes normas de uso, instalaciones y guías que se consideren precisas.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': '',
                  'preg': 'Planifica el desarrollo de las actividades de modo flexible, teniendo en cuenta y preparando los materiales (ajustados a las características de los alumnos y a la metodología escogida en cada momento), previendo los medios (organización de espacios y recursos) que se van a necesitar, así como las correspondientes normas de uso, instalaciones y guías que se consideren precisas.',
                  'docente': False,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Prevé y planifica a lo largo del curso la utilización de recursos externos al aula que requiere el área que imparte: trabajos de campo, museos, visitas a instalaciones de diversos tipos, contactos con agentes externos, etc.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': '',
                  'preg': 'Prevé y planifica a lo largo del curso la utilización de recursos externos al aula: trabajos de campo, museos, visitas a instalaciones de diversos tipos, contactos con agentes externos, etc.',
                  'docente': False,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Dispone de documentos (diario de clase, programación de cada sesión, cuaderno de notas o registro de observación) que le permiten realizar la planificación diaria y el seguimiento de la marcha de las clases en sus aspectos más significativos.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Plantea  las clases de forma coherente con el conjunto de la programación didáctica y, más concretamente, con la unidad didáctica o de trabajo de la que forma parte y los contenidos previstos son relevantes y significativos.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  }
             ]},
         {
             'subdim': 'Utilización de una metodología de enseñanza adecuada para promover el aprendizaje significativo de los contenidos escolares.',
             'valor': 6,
             'pregs': [
                 {'subsub': '',
                  'preg': 'Presenta un plan de trabajo a los alumnos, antes de cada unidad didáctica o de programación y, en general, cuida de que no se pierda el contexto ni la visión de conjunto en cada sesión.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': '',
                  'preg': 'Presenta un plan de trabajo a los alumnos, antes de cada intervención  y, en general, cuida de que no se pierda el contexto ni la visión de conjunto en cada sesión.',
                  'docente': False,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Toma iniciativas que le permiten conocer los intereses y conocimientos previos de sus alumnos, adoptando medidas para motivarlos.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Utiliza la metodología establecida en la programación didáctica, correspondiente a las características de los distintos grupos de alumnos.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': '',
                  'preg': 'Utiliza la metodología adaptada  a las características de los distintos grupos de alumnos.',
                  'docente': False,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Fomenta la adquisición de aquellas técnicas de estudio y de trabajo que son las propias de los contenidos de su área.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Plantea en clase unos contenidos bien estructurados y organizados de acuerdo con la programación, proponiendo actividades variadas que parten de situaciones o problemas reales, que impliquen la búsqueda de información, optando por un planteamiento globalizado cuando la situación lo requiera.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': '',
                  'preg': 'Plantea en sus actuaciones unos  contenidos bien estructurados y organizados de acuerdo con los planes de orientación, proponiendo actividades variadas que parten de situaciones o problemas reales, que impliquen la búsqueda de información, optando por un planteamiento globalizado cuando la situación lo requiera.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Integra en la correspondiente unidad didáctica o de programación los recursos didácticos que sean pertinentes: diferentes lenguajes, medios audiovisuales e informáticos, mapas, gráficos…etc.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': '',
                  'preg': 'Integra en la correspondiente unidad de intervención  los recursos didácticos que sean pertinentes: diferentes lenguajes, medios audiovisuales e informáticos, mapas, gráficos, etc.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Realiza actividades, individualizadas y/o en grupo, coherentes con los objetivos y las actividades planteados.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Revisa y replantea su planificación y, por lo tanto, sus estrategias, de acuerdo con la información obtenida en los procesos de evaluación de los alumnos y de la práctica docente.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  }
             ]},
         {
             'subdim': 'Procedimientos de evaluación de los aprendizajes e información sobre los mismos que se da a los alumnos y a sus familias.',
             'valor': 6,
             'pregs': [
                 {'subsub': ' Procedimientos de evaluación',
                  'preg': 'Solicita, a comienzo de curso,  información sobre sus alumnos al tutor del curso anterior, así como a aquellos profesores que puedan disponer de información relevante sobre los mismos.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': ' Procedimientos de evaluación',
                  'preg': 'Solicita, a comienzo de curso, información sobre los alumnos al tutor del curso anterior, así como a aquellos profesores que puedan disponer de información relevante sobre los mismos.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': ' Procedimientos de evaluación',
                  'preg': 'Realiza una evaluación inicial, bien general, bien referida a una unidad didáctica o de programación, que luego utiliza como punto de partida para ajustar la programación.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': ' Procedimientos de evaluación',
                  'preg': 'Realiza una evaluación inicial, que luego utiliza como punto de partida para ajustar su intervención en el aula.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': ' Procedimientos de evaluación',
                  'preg': 'Corrige y explica los trabajos y actividades, favoreciendo la autoevaluación.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': ' Procedimientos de evaluación',
                  'preg': 'Participa activamente en todas las sesiones de evaluación, aporta información relevante y toma en consideración la información proporcionada por los otros profesores.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': ' Procedimientos de evaluación',
                  'preg': 'Adopta unos criterios de evaluación que tienen en cuenta la graduación con la que se deben alcanzar los objetivos y contenidos seleccionados y tiene en cuenta la especial atención al alumnado con necesidad específica de apoyo educativo.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': ' Procedimientos de evaluación',
                  'preg': 'Aplica los criterios de calificación establecidos en la programación didáctica.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': 'Instrumentos de evaluación utilizados por el profesor',
                  'preg': 'Emplea unos instrumentos de evaluación adecuados a los contenidos que pretende evaluar y al grado de madurez del alumnado, de acuerdo con los criterios de evaluación del área.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': 'Instrumentos de evaluación utilizados por el profesor',
                  'preg': 'Utiliza instrumentos variados y adecuados a los distintos contenidos, de tal manera que permitan contrastar los resultados y los diferentes grados de aprendizaje que han alcanzado los alumnos.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': 'Instrumentos de evaluación utilizados por el profesor',
                  'preg': 'Elabora instrumentos de evaluación específicos, coherentes con los criterios de evaluación formulados, para alumnos con necesidad de adaptaciones, con necesidad específica de apoyo educativo, etc.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': 'Información sobre evaluación',
                  'preg': 'Utiliza adecuadamente los modelos de información para las familias establecidos por el centro para recoger, tres veces por curso, los logros y dificultades de los alumnos.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': 'Información sobre evaluación',
                  'preg': 'Utiliza adecuadamente los modelos establecidos por el centro para recoger a lo largo de la etapa los datos más relevantes sobre el aprendizaje de los alumnos en relación con los objetivos y criterios de evaluación de las distintas áreas.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': 'Información sobre evaluación',
                  'preg': 'Establece los medios que garanticen que los alumnos conozcan, en todo momento, los progresos y dificultades sobre su proceso de aprendizaje.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  }
             ]},
         {
             'subdim': 'Utilización de medidas ordinarias y extraordinarias para atender a la diversidad de capacidades, intereses y motivaciones de los alumnos, especialmente de aquéllos con mayores dificultades de aprendizaje.',
             'valor': 6,
             'pregs': [
                 {'subsub': '',
                  'preg': 'Adopta medidas de apoyo a las deficiencias de aprendizaje, tanto preventivas como de corrección o ayuda, hace el seguimiento y evalúa los resultados.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Toma medidas para facilitar el aprendizaje de las cuestiones que habitualmente ofrecen mayores dificultades, así como para que puedan profundizar los alumnos con un ritmo de aprendizaje más rápido.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Utiliza diferentes estrategias metodológicas en función de las características e intereses de los alumnos, materiales didácticos graduados en función de su dificultad y ajusta el desarrollo temporal de la programación a los diferentes ritmos de los alumnos.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Tiene criterios claros relativos a las causas y el momento en el que debe llevar a cabo una propuesta de adaptación curricular.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Elabora las adaptaciones curriculares para los alumnos que las precisen (en colaboración con los servicios de apoyo con los que cuenta), asume su aplicación, hace el seguimiento recogiendo documentalmente la selección de contenidos, las modificaciones metodológicas y de evaluación que se realicen.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': '',
                  'preg': 'Elabora las adaptaciones curriculares para los alumnos que las precisen, asume su aplicación, hace el seguimiento recogiendo documentalmente la selección de contenidos, las modificaciones metodológicas y de evaluación que se realicen.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Tiene fijados los materiales, lugar, hora y agrupamientos de los alumnos a los que aplica las distintas medidas de atención a la diversidad, revisa y adecua las adaptaciones previstas a la realidad de sus alumnos.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Realiza propuestas sobre la modificación o adquisiciones de recursos materiales que permitan adecuarlos a los alumnos con necesidades específicas.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Colabora con el profesorado de apoyo a la integración y, en su caso, con el orientador.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': '',
                  'preg': 'Colabora con el profesorado de apoyo a la integración.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  }
             ]},
         {
             'subdim': 'Organización del trabajo en el aula para favorecer la adecuada marcha de la clase y la participación e implicación del alumnado en su proceso de aprendizaje.',
             'valor': 6,
             'pregs': [
                 {'subsub': '',
                  'preg': 'Consigue que las relaciones entre los alumnos dentro del aula y de éstos con el profesor, sean correctas y fluidas, y se plantean desde una perspectiva no discriminatoria.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Favorece la elaboración de normas de convivencia con la aportación de todos y reacciona de forma ecuánime, adecuada e inmediata, ante situaciones inesperadas o conflictivas.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Fomenta la participación, el respeto y la colaboración entre los alumnos y acepta, de buen grado, sus sugerencias y aportaciones.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
                 {'subsub': '',
                  'preg': 'Plantea la clase con un ritmo de progresión adecuado y con tiempos suficientes para las distintas actividades.',
                  'docente': True,
                  'docente-jefe': True,
                  'docente-tutor': True,
                  'orientador': False, 'director': False,
                  'tutor': True,
                  'inspector': True
                  },
{'subsub': '',
                  'preg': 'Plantea la intervención en el aula  con un ritmo de progresión adecuado y con tiempos suficientes para las distintas actividades.',
                  'docente': True,
                  'docente-jefe': False,
                  'docente-tutor': False,
                  'orientador': True, 'director': False,
                  'tutor': True,
                  'inspector': True
                  }
             ]}
     ]}
]
