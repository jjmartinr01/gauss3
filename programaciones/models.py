# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unicodedata
import os

from django.db import models

from estudios.models import Materia, Curso
from entidades.models import Gauser_extra, Ronda, Entidad


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_programacion(instance, filename):
    ext = filename.rpartition('.')[2]
    file_nombre = '%s' % (instance.materia.nombre)
    curso = instance.materia.curso.ronda.nombre.replace('/', '-')
    ruta = 'programaciones/%s/%s/%s/%s/%s/%s' % (
        instance.materia.curso.ronda.entidad.code,
        curso,
        instance.sube.gauser_extra_programaciones.departamento.nombre,
        instance.materia.curso.get_etapa_display(),
        instance.materia.curso.nombre,
        file_nombre)
    ruta = ruta.replace(' ', '_').replace(',', '').replace(';', '').replace('.', '')
    filename_normalizado = unicodedata.normalize('NFKD', ruta).encode('ascii', 'ignore') #.decode('utf-8')
    return '%s.%s' %(filename_normalizado, ext)


class ProgramacionSubida(models.Model):
    sube = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    archivo = models.FileField("Archivo con la programación", upload_to=update_programacion, null=True, blank=True,
                               max_length=500)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    creado = models.DateField("Fecha de creación", auto_now_add=True)

    @property
    def filename(self):
        return os.path.basename(self.archivo.name)

    def __str__(self):
        return u'%s - %s (%s)' % (self.materia.curso.ronda.entidad.code, self.materia.nombre, self.materia.curso)

def crea_departamentos(ronda):
    ds = [(u'Actividades Complementarias y Extraescolares', u'AEX', False, 3), (u'Artes Plásticas', u'AP', True, 3),
          (u'Cultura Clásica', u'CC', True, 3), (u'Ciencias Naturales', u'CN', True, 3),
          (u'Economía', u'ECO', True, 3), (u'Educación Física', u'EF', True, 3),
          (u'Filosofía', u'FIL', True, 3), (u'Física y Química', u'FQ', True, 3),
          (u'Formación y Orientación Laboral', u'FOL', True, 3), (u'Francés', u'FRA', True, 3),
          (u'Geografía e Historia', u'GH', True, 3), (u'Griego', u'GRI', True, 3), (u'Inglés', u'ING', True, 3),
          (u'Latín', u'LAT', True, 3), (u'Lengua Castellana y Literatura', u'LCL', True, 3),
          (u'Matemáticas', u'MAT', True, 3), (u'Música', u'MUS', True, 3), (u'Orientación', u'ORI', True, 3),
          (u'Tecnología', u'TEC', True, 3), (u'Administración y gestión', u'ADG', True, 3),
          (u'Electricidad y electrónica', u'ELE', True, 3), (u'Ningún departamento', u'N_D', True, 0),
          (u'Alemán', u'ALE', True, 3), (u'Fabricación Mecánica', u'FME', True, 3)]
    for d in ds:
        try:
            Departamento.objects.get(ronda=ronda, abreviatura=d[1])
        except:
            Departamento.objects.create(ronda=ronda, nombre=d[0], abreviatura=d[1], didactico=d[2],
                                        horas_coordinador=d[3])


class Departamento(models.Model):
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE)
    nombre = models.CharField('Denominación', max_length=310)
    abreviatura = models.CharField("Abreviatura", max_length=10)
    didactico = models.BooleanField("Es un departamento didáctico", default=True)
    horas_coordinador = models.IntegerField("Número de horas de coordinación para el jefe de departamento", null=True,
                                            blank=True)

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.ronda)


materias = ['168963', '168961', '168864', '67985', '67987', '63500', '67995', '168953', '67996', '168871', '67994',
            '168956', '168951', '168959', '63491', '67986', '168870', '168874', '168868', '168960', '168958', '168962',
            '168877', '63493', '67993', '168876', '63502', '63499', '63501', '63495', '67989', '67983', '168869',
            '168872', '67992', '168875', '168957', '168964', '168866', '63494', '63496', '168954', '63503', '63498',
            '168865', '67984', '168952', '168950', '63492', '168873', '168867']


class Materia_programaciones(models.Model):
    materia = models.OneToOneField(Materia, on_delete=models.CASCADE)
    tipo = models.CharField("Tipo de materia", max_length=50, null=True, blank=True)
    codigo = models.CharField('Código', max_length=20, blank=True, null=True)
    ects = models.IntegerField('Número de créditos ECTS', blank=True, null=True)
    provisional = models.BooleanField('Actividad cargada de forma incompleta', default=False)
    departamentos = models.ManyToManyField(Departamento, blank=True)

    @property
    def entidad(self):
        return self.materia.curso.ronda.entidad

    class Meta:
        ordering = ['materia__nombre', 'materia__curso']

    def __str__(self):
        return u'%s (%s horas)' % (self.materia.nombre, self.materia.horas)


class Resultado_aprendizaje(models.Model):
    materia = models.ForeignKey(Materia_programaciones, on_delete=models.CASCADE)
    resultado = models.TextField("Resultado")
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)

    def __str__(self):
        return u'%s - %s' % (self.resultado[:80], self.materia)


class Objetivo(models.Model):
    materia = models.ForeignKey(Materia_programaciones, on_delete=models.CASCADE)  # Este campo es utilizado en programacion_append.html
    resultado_aprendizaje = models.ForeignKey(Resultado_aprendizaje, blank=True, null=True, on_delete=models.CASCADE)
    texto = models.TextField("Objetivo")
    crit_eval = models.TextField("Criterio de evaluación", blank=True, null=True)
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)

    def __str__(self):
        return u'%s - %s' % (self.texto[:80], self.resultado_aprendizaje)


# TITULOS_DICT = [{'titulo': 'Técnico Superior en Administración y Finanzas',
#                  'ab_titulo': 'TS_AF',
#                  'deno': 'Administración y Finanzas',
#                  'nivel': 'Formación Profesional de Grado Superior',
#                  'duracion': '2.000 horas',
#                  'familia': 'Administración y Gestión',
#                  'ref_eu_name': 'Referente en la Clasificación Internacional Normalizada de la Educación',
#                  'ref_eu': 'CINE-5b',
#                  },
#                 {'titulo': 'Técnico  en  Gestión Administrativa',
#                  'ab_titulo': 'T_GA',
#                  'deno': 'Gestión Administrativa',
#                  'nivel': 'Formación Profesional de Grado Medio',
#                  'duracion': '2.000 horas',
#                  'familia': 'Administración y Gestión',
#                  'ref_eu_name': 'Referente en la Clasificación Internacional Normalizada de la Educación',
#                  'ref_eu': 'CINE-3',
#                  },
#                 {'titulo': 'Técnico en Instalaciones de Telecomunicaciones',
#                  'ab_titulo': 'T_IT',
#                  'deno': 'Instalaciones de Telecomunicaciones',
#                  'nivel': 'Formación Profesional de Grado Medio',
#                  'duracion': '2000 horas',
#                  'familia': 'Electricidad y Electrónica',
#                  'ref_eu_name': 'Referente en la Clasificación Internacional Normalizada de la Educación',
#                  'ref_eu': 'CINE-3'},
#                 {'titulo': 'Técnico  Superior  en  Sistemas  de  Telecomunicaciones  e  Informáticos',
#                  'ab_titulo': 'TS_STI',
#                  'deno': 'Sistemas de Telecomunicaciones e Informáticos',
#                  'nivel': 'Formación Profesional de Grado Superior',
#                  'duracion': '2000 horas',
#                  'familia': 'Electricidad y Electrónica',
#                  'ref_eu_name': 'Referente en la Clasificación Internacional Normalizada de la Educación',
#                  'ref_eu': 'CINE-5b',
#                  'obj_generales': [
#                      'Elaborar informes y documentación técnica, reconociendo esquemas y consultando catálogos y las prescripciones reglamentarias, para desarrollar proyectos de instalaciones y sistemas de telecomunicaciones.',
#                      'Reconocer sistemas de telecomunicaciones, aplicando leyes y teoremas para calcular sus parámetros.',
#                      'Definir unidades de obra y sus características técnicas, interpretando planos y esquemas, para elaborar el presupuesto.',
#                      'Definir la estructura, equipos y conexionado general de las instalaciones y sistemas de telecomunicaciones, partiendo de los cálculos y utilizando catálogos comerciales, para configurar instalaciones.',
#                      'Dibujar los planos de trazado general y esquemas eléctricos y electrónicos, utilizando programas informáticos de diseño asistido, para configurar instalaciones y sistemas de telecomunicación.',
#                      'Aplicar técnicas de control de almacén, utilizando programas informáticos, para gestionar el suministro.',
#                      'Definir las fases y actividades del desarrollo de la instalación según documentación técnica pertinente, especificando los recursos necesarios, para planificar el montaje.',
#                      'Replantear la instalación, teniendo en cuenta los planos y esquemas y las posibles condiciones de la instalación, para realizar el lanzamiento.',
#                      'Identificar los recursos humanos y materiales, dando respuesta a las necesidades del montaje, para realizar su lanzamiento.',
#                      'Aplicar técnicas de gestión y montaje en sistemas de telecomunicaciones, interpretando anteproyectos y utilizando instrumentos y herramientas adecuadas, para supervisar el montaje.',
#                      'Definir procedimientos, operaciones y secuencias de intervención en instalaciones de telecomunicaciones, analizando información técnica de equipos y recursos, para planificar el mantenimiento.',
#                      'Aplicar técnicas de mantenimiento en sistemas e instalaciones de telecomunicaciones, utilizando los instrumentos y herramientas apropiados, para ejecutar los procesos de mantenimiento.',
#                      'Ejecutar pruebas de funcionamiento, ajustando equipos y elementos, para poner en servicio las instalaciones.',
#                      'Definir los medios de protección personal y de las instalaciones, identificando los riesgos y factores de riesgo del montaje, mantenimiento y uso de las instalaciones, para elaborar el estudio básico de seguridad y salud.',
#                      'Reconocer la normativa de gestión de calidad y de residuos aplicada a las instalaciones de telecomunicaciones y eléctricas, para supervisar el cumplimiento de la normativa.',
#                      'Preparar los informes técnicos, certificados de instalación y manuales de instrucciones y mantenimiento, siguiendo los procedimientos y formatos oficiales para elaborar la documentación técnica y administrativa.',
#                      'Analizar y utilizar los recursos y oportunidades de aprendizaje relacionadas con la evolución científica, tecnológica y organizativa del sector y las tecnologías de la información y la comunicación, para mantener el espíritu de actualización y adaptarse a nuevas situaciones laborales y personales.',
#                      'Desarrollar la creatividad y el espíritu de innovación para responder a los retos que se presentan en los procesos y en la organización del trabajo y de la vida personal.',
#                      'Tomar decisiones de forma fundamentada, analizando las variables implicadas, integrando saberes de distinto ámbito y aceptando los riesgos y la posibilidad de equivocación en las mismas, para afrontar y resolver distintas situaciones, problemas o contingencias.',
#                      'Desarrollar técnicas de liderazgo, motivación, supervisión y comunicación en contextos de trabajo en grupo, para facilitar la organización y coordinación de equipos de trabajo.',
#                      'Aplicar estrategias y técnicas de comunicación, adaptándose a los contenidos que se van a transmitir, a la finalidad y a las características de los receptores, para asegurar la eficacia en los procesos de comunicación.',
#                      'Evaluar situaciones de prevención de riesgos laborales y de protección ambiental, proponiendo y aplicando medidas de prevención personales y colectivas, de acuerdo con la normativa aplicable en los procesos del trabajo, para garantizar entornos seguros.',
#                      'Identificar y proponer las acciones profesionales necesarias, para dar respuesta a la accesibilidad universal y al «diseño para todos».',
#                      'Identificar y aplicar parámetros de calidad en los trabajos y actividades realizados en el proceso de aprendizaje, para valorar la cultura de la evaluación y de la calidad y ser capaces de supervisar y mejorar los procedimientos de gestión de calidad.',
#                      'Utilizar procedimientos relacionados con la cultura emprendedora, empresarial y de iniciativa profesional, para realizar la gestión básica de una pequeña empresa o emprender un trabajo.',
#                      'Reconocer sus derechos y deberes como agente activo en la sociedad, teniendo en cuenta el marco legal que regula las condiciones sociales y laborales, para participar como ciudadano democrático.',
#                  ]}]

# TITULOS = (('TS_STI', 'Técnico Superior en Sistemas de Telecomunicaciones e Informáticos',),
#            ('T_IT', 'Técnico en Instalaciones de Telecomunicaciones'),
#            ('T_GA', 'Técnico en Gestión Administrativa'),
#            ('TS_AF', 'Técnico Superior en Administración y Finanzas'))



class Cuerpo_funcionario(models.Model):
    code = models.CharField('Código del cuerpo', max_length=10)
    nombre = models.CharField('Nombre del cuerpo', max_length=100)

    def __str__(self):
        return u'%s - %s' % (self.code, self.nombre)


class Especialidad_funcionario(models.Model):
    cuerpo = models.ForeignKey(Cuerpo_funcionario, blank=True, null=True, on_delete=models.CASCADE)
    code = models.CharField('Código del cuerpo', max_length=10)
    nombre = models.CharField('Nombre del cuerpo', max_length=100)

    def __str__(self):
        return u'%s - %s (%s)' % (self.code, self.nombre, self.cuerpo)


# class Cuerpo_entidad(models.Model):
#     entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
#     cuerpo = models.ForeignKey(Cuerpo_funcionario, blank=True, null=True, on_delete=models.CASCADE)
#
#     def __str__(self):
#         return u'%s - %s' % (self.entidad, self.cuerpo)


class Especialidad_entidad(models.Model):
    ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(Especialidad_funcionario, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ["especialidad__cuerpo"]
        verbose_name_plural = "Especialidades de funcionarios en la entidad"

    def __str__(self):
        return u'%s - %s' % (self.ronda, self.especialidad)


class Gauser_extra_programaciones(models.Model):
    ge = models.OneToOneField(Gauser_extra, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(Especialidad_entidad, blank=True, null=True, on_delete=models.CASCADE)
    puesto = models.CharField('Puesto cargado de exportación de horarios Racima', max_length=150, blank=True, null=True)
    departamento = models.ForeignKey(Departamento, blank=True, null=True, on_delete=models.CASCADE)
    jefe = models.BooleanField('Es jefe del departamento?', default=False)

    class Meta:
        ordering = ["ge__gauser__last_name"]
        verbose_name_plural = "Gausers extra en programaciones"

    def __str__(self):
        return u'%s - %s' % (self.ge, self.departamento)


class Titulo_FP(models.Model):
    REF_EU_NAME_GENERAL = 'Referente en la Clasificación Internacional Normalizada de la Educación'
    NIVELES = (('FPGS', 'Formación Profesional de Grado Superior'),
               ('FPGM', 'Formación Profesional de Grado Medio'),
               ('FPB', 'Formación Profesional Básica'))
    FAMILIAS = (('AFD', 'Actividades físicas y deportivas'),
                ('AG', 'Administración y gestión'),
                ('A', 'Agraria'),
                ('ARG', 'Artes gráficas'),
                ('CM', 'Comercio y marketing'),
                ('EOC', 'Edificación y obra civil'),
                ('EE', 'Electricidad y electrónica'),
                ('FM', 'Fabricación mecánica'),
                ('HT', 'Hostelería y turismo'),
                ('IP', 'Imagen personal'),
                ('IA', 'Industrias alimentarias'),
                ('IC', 'Informática y comunicaciones'),
                ('IM', 'Instalación y mantenimiento'),
                ('MMC', 'Madera, mueble y corcho'),
                ('Q', 'Química'),
                ('S', 'Sanidad'),
                ('SSC', 'Servicios socioculturaes y a la comunidad'),
                ('TCP', 'Textil, confección y piel'),
                ('TMV', 'Transporte y mantenimiento de vehículos'))
    titulo = models.CharField('Título al que da acceso', max_length=350)
    abv_titulo = models.CharField('Abreviatura del título', max_length=35)
    nombre = models.CharField('Denominación', max_length=300)  # Ejemplo: Gestión Administrativa
    nivel = models.CharField('Nivel de FP', choices=NIVELES, max_length=10)
    duracion = models.IntegerField('Número de horas totales', default=2000)
    familia = models.CharField('Familia Profesional', default='AG', choices=FAMILIAS, max_length=10)
    ref_eu_name = models.CharField('Título al que da acceso', max_length=350, default=REF_EU_NAME_GENERAL)
    ref_eu = models.CharField('Referencia europea', max_length=50)
    cursos = models.ManyToManyField(Curso, blank=True)

    @property
    def autotitulo(self):
        if self.nivel == 'FPGS':
            return 'Técnico Superior en %s' % (self.nombre)
        elif self.nivel == 'FPGM':
            return 'Técnico en %s' % (self.nombre)
        else:
            return 'Título Profesional Básico en %s' % (self.nombre)

    def __str__(self):
        return u'Título: %s' % (self.nombre)


class Obj_general(models.Model):
    titulo = models.ForeignKey(Titulo_FP, on_delete=models.CASCADE)
    objetivo = models.TextField('Objetivo general')
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)

    def __str__(self):
        return u'Título: %s - %s' % (self.titulo.nombre, self.objetivo)


class Programacion_modulo(models.Model):
    g_e = models.ForeignKey(Gauser_extra, blank=True, null=True, related_name='exportar', on_delete=models.CASCADE)
    gep = models.ForeignKey(Gauser_extra_programaciones, blank=True, null=True, on_delete=models.CASCADE)
    titulo = models.ForeignKey(Titulo_FP, blank=True, null=True, on_delete=models.CASCADE)
    modulo = models.ForeignKey(Materia_programaciones, blank=True, null=True, on_delete=models.CASCADE)
    obj_gen = models.ManyToManyField(Obj_general, blank=True)
    act_refuerzo = models.TextField('Actividades de refuerzo/recuperación', blank=True, null=True)
    act_fct = models.TextField('Actividades durante la Formación en Centros de Trabajo', blank=True, null=True)
    crit_eval_gen = models.TextField('Criterio general de evaluación/calificación', blank=True, null=True)
    pro_formacion = models.TextField('Necesidad/propuesta de formación del profesorado', blank=True, null=True)
    file_path = models.CharField('Ruta hasta el archivo sin extensión', blank=True, null=True, max_length=300)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateField("Fecha de modificación", auto_now=True)
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)

    @property
    def resultados_aprendizaje_aplicados(self):
        ra = []
        for u in self.ud_modulo_set.all():
            ra += u.resultados_aprendizaje
        return list(set(ra))

    @property
    def objetivos_aplicados(self):
        objs = []
        for u in self.ud_modulo_set.all():
            objs += list(u.objetivos.all())
        return list(set(objs))

    def __str__(self):
        return u'%s' % (self.modulo)


class UD_modulo(models.Model):  # Unidad didáctica del módulo
    programacion = models.ForeignKey(Programacion_modulo, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre de la unidad didáctica', max_length=300, blank=True, null=True)
    orden = models.IntegerField('Número de unidad didáctica', blank=True, null=True)
    duracion = models.IntegerField('Número de horas lectivas destinadas a la unidad didáctica', blank=True, null=True)
    objetivos = models.ManyToManyField(Objetivo, blank=True)
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)

    @property
    def resultados_aprendizaje(self):
        ra = []
        for o in self.objetivos.all():
            if not o.resultado_aprendizaje in ra:
                ra.append(o.resultado_aprendizaje)
        return ra

    def objetivos_ra(self, ra):
        return self.objetivos.filter(resultado_aprendizaje=ra)

    class Meta:
        ordering = ["orden"]
        verbose_name_plural = "Unidades didácticas de módulos"

    def __str__(self):
        return u'%s - %s' % (self.nombre, self.duracion)


class Cont_unidad_modulo(models.Model):
    unidad = models.ForeignKey(UD_modulo, blank=True, null=True, on_delete=models.CASCADE)
    objetivos = models.TextField('Objetivos específicos de este contenido', blank=True, null=True)
    contenido = models.TextField('Contenido a desarrollar en esta unidad didáctica', blank=True, null=True)
    actividades = models.TextField('Actividades de enseñanza-aprendizaje y de evaluación', blank=True, null=True)
    duracion = models.IntegerField('Número de horas lectivas destinadas a desarrollar este contenido', blank=True,
                                   null=True)
    orden = models.IntegerField('Orden del contenido dentro de la unidad didáctica', blank=True, null=True)
    nombre = models.CharField('Nombre de la unidad didáctica', max_length=300, blank=True, null=True)

    class Meta:
        ordering = ["orden"]
        verbose_name_plural = "Contenidos de la unidad didáctica"

    def __str__(self):
        return u'%s - %s (%s horas)' % (self.unidad.nombre, self.contenido[:200], self.duracion)


def crea_cuerpos_especialidades():
    CUERPOS = (("590", "PROFESORES DE ENSEÑANZA SECUNDARIA"),
               ("511", "CATEDRÁTICOS DE ENSEÑANZA SECUNDARIA"),
               ("591", "PROFESORES TÉCNICOS FORMACIÓN PROFESIONAL"),
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


modulos = [
    ("Circuito cerrado de televisión y seguridad electrónica", "Instalaciones de Telecomunicaciones"),
    ("Comunicación empresarial y atención al cliente", "Gestión Administrativa"),
    ("Comunicación y Atención al Cliente", "Administración y Finanzas"),
    ("Configuración de Infraestructuras de Sistemas de Telecomunicaciones",
     "Sistemas de Telecomunicaciones e Informáticos"),
    ("Contabilidad y Fiscalidad", "Administración y Finanzas"),
    ("Electrónica aplicada", "Instalaciones de Telecomunicaciones"),
    ("Elementos de Sistemas de Telecomunicaciones", "Sistemas de Telecomunicaciones e Informáticos"),
    ("Empresa e Iniciativa Emprendedora", "Sistemas de Telecomunicaciones e Informáticos"),
    ("Empresa en el aula", "Gestión Administrativa"),
    ("Empresa y administración", "Gestión Administrativa"),
    ("Equipos microinformáticos", "Instalaciones de Telecomunicaciones"),
    ("Formación y orientación laboral", "Gestión Administrativa"),
    ("Formación y orientación laboral", "Instalaciones de Telecomunicaciones"),
    ("Gestión de la Documentación Jurídica y Empresarial", "Administración y Finanzas"),
    ("Gestión de Proyectos de Instalaciones de Telecomunicaciones", "Sistemas de Telecomunicaciones e Informáticos"),
    ("Gestión de Recursos Humanos", "Administración y Finanzas"),
    ("Gestión Financiera", "Administración y Finanzas"),
    ("Gestión Logística y Comercial", "Administración y Finanzas"),
    ("Infraestructuras comunes de telecomunicación en viviendas y edificios", "Instalaciones de Telecomunicaciones"),
    ("Infraestructuras de redes de datos y sistemas de telefonía", "Instalaciones de Telecomunicaciones"),
    ("Instalaciones de megafonía y sonorización", "Instalaciones de Telecomunicaciones"),
    ("Instalaciones de radiocomunicaciones", "Instalaciones de Telecomunicaciones"),
    ("Instalaciones domóticas", "Instalaciones de Telecomunicaciones"),
    ("Instalaciones eléctricas básicas", "Instalaciones de Telecomunicaciones"),
    ("Ofimática y Proceso de la Información", "Administración y Finanzas"),
    ("Operaciones administrativas de compra-venta", "Gestión Administrativa"),
    ("Operaciones administrativas de recursos humanos", "Gestión Administrativa"),
    ("Operaciones auxiliares de gestión de tesorería", "Gestión Administrativa"),
    ("Proceso Integral de la Actividad Comercial", "Administración y Finanzas"),
    ("Proyecto de Administración y Finanzas", "Administración y Finanzas"),
    ("Recursos Humanos y Responsabilidad Social Corporativa", "Administración y Finanzas"),
    ("Redes Telemáticas", "Sistemas de Telecomunicaciones e Informáticos"),
    ("Simulación Empresarial", "Administración y Finanzas"),
    ("Sistemas de Producción Audiovisual", "Sistemas de Telecomunicaciones e Informáticos"),
    ("Sistemas de Radiocomunicaciones", "Sistemas de Telecomunicaciones e Informáticos"),
    ("Sistemas de Telefonía Fija y Móvil", "Sistemas de Telecomunicaciones e Informáticos"),
    ("Sistemas Informáticos y Redes Locales", "Sistemas de Telecomunicaciones e Informáticos"),
    ("Sistemas Integrados y Hogar Digital", "Sistemas de Telecomunicaciones e Informáticos"),
    ("Técnica contable", "Gestión Administrativa"),
    ("Técnicas y Procesos en Infraestructuras de Telecomunicaciones", "Sistemas de Telecomunicaciones e Informáticos"),
    ("Tratamiento de la documentación contable", "Gestión Administrativa"),
    ("Tratamiento informático de la información", "Gestión Administrativa"),
]
