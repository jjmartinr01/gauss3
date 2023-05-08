# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.utils.text import slugify
from django.utils.timezone import now, datetime
import os

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from autenticar.models import Gauser
from gauss.rutas import MEDIA_PROGRAMACIONES
from gauss.funciones import pass_generator
from calendario.models import Vevent
from estudios.models import Materia, Curso, AreaMateria, CompetenciaEspecifica, CriterioEvaluacion, Grupo
from entidades.models import Gauser_extra, Ronda, Entidad
from horarios.models import Horario, Sesion
from actividades.models import Actividad
from mensajes.models import Aviso


#############################################################################
##################### PROGRAMACIONES ANTIGUAS  ##############################
#############################################################################


def update_aaee(instance, filename):
    ext = filename.rpartition('.')[2]
    ronda_slugify = slugify(instance.ronda.nombre)
    ruta = 'programaciones/%s/%s/Aspectos_Generales_PGA/Programa_actividades_extraescolares' % (
        instance.materia.curso.ronda.entidad.code, ronda_slugify)
    return '%s.%s' % (ruta, ext)


def update_libros(instance, filename):
    ext = filename.rpartition('.')[2]
    ronda_slugify = slugify(instance.ronda.nombre)
    ruta = 'programaciones/%s/%s/Aspectos_Generales_PGA/Libros_de_texto_y_materiales' % (
        instance.materia.curso.ronda.entidad.code, ronda_slugify)
    return '%s.%s' % (ruta, ext)


def ruta_programaciones(ronda, filename='', tipo='pga', ruta='absoluta'):
    """
    :param ronda:
    :param filename:
    :param tipo: str
                    pga -> ruta a aspectos generales pga
                    pec -> ruta a aspectos generales pec
                    centro -> ruta a programaciones centro
                    ronda -> ruta a programaciones ronda
    :param ruta: str que puede ser 'relativa' o 'absoluta'
    :return: str que contiene la ruta 'relativa' o 'absoluta' según se haya elegido
    """
    centro_code = ronda.entidad.code
    ronda_slugify = slugify(ronda.nombre)
    ruta_centro_relativa = 'programaciones/%s/' % centro_code
    ruta_centro_absoluta = '%s%s/' % (MEDIA_PROGRAMACIONES, centro_code)
    ruta_ronda_relativa = '%s%s/' % (ruta_centro_relativa, ronda_slugify)
    ruta_ronda_absoluta = '%s%s/' % (ruta_centro_absoluta, ronda_slugify)
    if tipo == 'pga':
        relativa = '%sAspectos_Generales_PGA/%s' % (ruta_ronda_relativa, filename)
        absoluta = '%sAspectos_Generales_PGA/%s' % (ruta_ronda_absoluta, filename)
    elif tipo == 'pec':
        relativa = '%sPEC/%s' % (ruta_ronda_relativa, filename)
        absoluta = '%sPEC/%s' % (ruta_ronda_absoluta, filename)
    elif tipo == 'centro':
        relativa = '%s%s' % (ruta_centro_relativa, filename)
        absoluta = '%s%s' % (ruta_centro_absoluta, filename)
    else:
        relativa = '%s%s' % (ruta_ronda_relativa, filename)
        absoluta = '%s%s' % (ruta_ronda_absoluta, filename)
    d = {'relativa': relativa, 'absoluta': absoluta}
    return d[ruta]


def rutas_aspectos_pga(pga, filename=''):
    centro_code = pga.ronda.entidad.code
    ronda_slugify = slugify(pga.ronda.nombre)
    relativa = 'programaciones/%s/%s/Aspectos_Generales_PGA/%s' % (centro_code, ronda_slugify, filename)
    absoluta = '%s%s/%s/Aspectos_Generales_PGA/%s' % (MEDIA_PROGRAMACIONES, centro_code, ronda_slugify, filename)
    return {'relativa': relativa, 'absoluta': absoluta, 'centro': 'programaciones/%s/' % centro_code}


def rutas_pec(pec, filename=''):
    centro_code = pec.entidad.code
    ronda_slugify = slugify(pec.entidad.ronda.nombre)
    relativa = 'programaciones/%s/%s/PEC/%s' % (centro_code, ronda_slugify, filename)
    absoluta = '%s%s/%s/PEC/%s' % (MEDIA_PROGRAMACIONES, centro_code, ronda_slugify, filename)
    return {'relativa': relativa, 'absoluta': absoluta}


class PGA(models.Model):
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE)
    fprofesorado = models.TextField("Plan formación profesorado", blank=True, null=True, default='')
    convenios = models.TextField("Previsión de acuerdos y/o convenios", blank=True, null=True, default='')
    obras = models.TextField("siutación instalaciones y previsión de obras", blank=True, null=True, default='')
    creado = models.DateField("Fecha de creación", auto_now_add=True)

    @property
    def horario(self):
        return Horario.objects.get(ronda=self.ronda, predeterminado=True)

    @property
    def reuniones_equipo_directivo(self):
        h = Horario.objects.get(ronda=self.ronda, predeterminado=True)
        sesiones = Sesion.objects.filter(actividad__nombre__icontains='reuniones del equipo directivo', horario=h)
        return set(sesiones.values_list('dia', 'inicio', 'fin'))

    @property
    def reuniones_departamentos(self):
        h = Horario.objects.get(ronda=self.ronda, predeterminado=True)
        sesiones = Sesion.objects.filter(actividad__nombre__icontains='de departamento', horario=h)
        return set(
            sesiones.values_list('dia', 'inicio', 'fin', 'g_e__gauser_extra_programaciones__departamento__nombre'))

    @property
    def reuniones_equipos_docentes(self):
        h = Horario.objects.get(ronda=self.ronda, predeterminado=True)
        q = models.Q(actividad__nombre__icontains='tutores del mismo nivel') | models.Q(
            actividad__nombre__icontains='equipos docentes')
        sesiones = Sesion.objects.filter(models.Q(horario=h), q)
        return set([(s.dia, s.inicio, s.fin, s.actividad.nombre) for s in sesiones])
        # return set([(s.dia, s.inicio, s.fin, s.g_e.gauser_extra_horarios.cursos.all().values_list('nombre', flat=True)) for s in sesiones])

    @property
    def reuniones_ccp(self):
        h = Horario.objects.get(ronda=self.ronda, predeterminado=True)
        sesiones = Sesion.objects.filter(horario=h, actividad__nombre__icontains='comis')
        return set([(s.dia, s.inicio, s.fin, s.actividad.nombre) for s in sesiones])
        # return set([(s.dia, s.inicio, s.fin, s.g_e.gauser_extra_horarios.cursos.all().values_list('nombre', flat=True)) for s in sesiones])

    @property
    def reuniones_claustro(self):
        return ReunionesPrevistas.objects.filter(pga=self, tipo='CLA')

    @property
    def reuniones_consejo(self):
        return ReunionesPrevistas.objects.filter(pga=self, tipo='CON')

    @property
    def reuniones_evaluacion(self):
        return ReunionesPrevistas.objects.filter(pga=self, tipo='EVA')

    @property
    def festivos(self):
        return Vevent.objects.filter(entidad=self.ronda.entidad, dtstart__gte=self.ronda.inicio,
                                     dtend__lte=self.ronda.fin, festivo=True)

    @property
    def aaee(self):  # Actividades extraescolares
        return Actividad.objects.filter(organizador__ronda=self.ronda)

    def __str__(self):
        return '%s - %s (%s)' % (self.ronda.entidad.name, self.ronda.nombre, self.creado)


def update_documentos_pga(instance, filename):
    ext = filename.rpartition('.')[2]
    ruta = rutas_aspectos_pga(instance.pga, instance.doc_nombre)['relativa']
    return '%s.%s' % (ruta, ext)


class PGAdocumento(models.Model):
    TIPOS = (('programa_actividades_extraescolares', 'Programa actividades extraescolares'),
             ('libros_de_texto_y_materiales', 'Libros de texto y materiales'),
             ('estadistica_comienzo_curso', 'Estadística de comienzo de curso'))
    pga = models.ForeignKey(PGA, on_delete=models.CASCADE)
    doc_nombre = models.CharField('Nombre del documento', max_length=200, choices=TIPOS)
    doc_file = models.FileField("Archivo del documento asociado a la PGA", upload_to=update_documentos_pga)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)

    @property
    def filename(self):
        return os.path.basename(self.doc_file.name)

    def __str__(self):
        return 'Documento PGA: %s' % (self.doc_nombre)


class ReunionesPrevistas(models.Model):
    TIPOS = (('CLA', 'Reunión del claustro de profesores'),
             ('CON', 'Reunión del Consejo Escolar'),
             ('CCP', 'Reunión de la Comisión de Coordinación Pedagógica'),
             ('EVA', 'Reunión de evaluación'))
    pga = models.ForeignKey(PGA, on_delete=models.CASCADE)
    tipo = models.CharField("Tipo de reunión", max_length=5, choices=TIPOS, default='CLA')
    nombre = models.CharField("Nombre de la reunión", blank=True, null=True, max_length=200)
    description = models.TextField("Descripción de la reunión", blank=True, null=True, default='')
    fecha = models.DateTimeField("Fecha y hora de la reunión", blank=True, null=True)

    def __str__(self):
        return '%s - Reunión %s (%s)' % (self.pga.ronda.nombre, self.get_tipo_display(), self.fecha)


class PEC(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    signos = models.TextField("Signos de identidad del centro", blank=True, null=True, default='')
    organizacion = models.TextField("Organización general del centro", blank=True, null=True, default='')
    lineapedagogica = models.TextField("Línea pedagógica", blank=True, null=True, default='')
    participacion = models.TextField("Modelo de participación en la vida escolar", blank=True, null=True, default='')
    proyectos = models.TextField("Proyectos que desarrolla el centro", blank=True, null=True, default='')

    @property
    def cursos(self):
        return Curso.objects.filter(ronda=self.entidad.ronda)

    def __str__(self):
        return 'Proyecto Educativo de Centro: %s' % (self.entidad.name)


def update_documentos_pec(instance, filename):
    ext = filename.rpartition('.')[2]
    nombre = slugify(instance.get_tipo_display())
    ruta = rutas_pec(instance.pec, nombre)['relativa']
    return '%s.%s' % (ruta, ext)


class PECdocumento(models.Model):
    TIPOS = (('pat', 'Plan de Acción Tutorial'),
             ('poap', 'Plan de Orientación Académica y Profesional'),
             ('pad', 'Plan de Atención a la Diversidad'),
             ('pc', 'Plan de Convivencia'),
             ('rof', 'Reglamento de Organización y Funcionamiento'),
             ('otros', 'Otros documentos'))
    pec = models.ForeignKey(PEC, on_delete=models.CASCADE)
    tipo = models.CharField('Tipo de documento', choices=TIPOS, max_length=10, default='otros')
    doc_nombre = models.CharField('Nombre del documento', max_length=200)
    doc_file = models.FileField("Archivo del documento asociado al PEC", upload_to=update_documentos_pec)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)

    @property
    def filename(self):
        return os.path.basename(self.doc_file.name)

    def __str__(self):
        return 'Documento PEC: %s' % (self.doc_nombre)


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_programacion(instance, filename):
    ext = filename.rpartition('.')[2]
    file_nombre = '%s' % (instance.materia.nombre)
    ruta = 'programaciones/%s/%s/Programaciones_didacticas/%s/%s/%s/%s' % (
        instance.materia.curso.ronda.entidad.code,
        slugify(instance.sube.ronda.nombre),
        slugify(instance.sube.gauser_extra_programaciones.departamento.nombre),
        slugify(instance.materia.curso.get_etapa_display()),
        slugify(instance.materia.curso.nombre),
        slugify(file_nombre))
    return '%s.%s' % (ruta, ext)


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
        return '%s - %s (%s)' % (self.materia.curso.ronda.entidad.code, self.materia.nombre, self.materia.curso)


def crea_departamentos(ronda):
    ds = [('Actividades Complementarias y Extraescolares', 'AEX', False, False, 3),
          ('Artes Plásticas', 'AP', True, False, 3),
          ('Cultura Clásica', 'CC', True, False, 3), ('Ciencias Naturales', 'CN', True, False, 3),
          ('Economía', 'ECO', True, False, 3), ('Educación Física', 'EF', True, False, 3),
          ('Filosofía', 'FIL', True, False, 3), ('Física y Química', 'FQ', True, False, 3),
          ('Formación y Orientación Laboral', 'FOL', True, False, 3), ('Francés', 'FRA', True, False, 3),
          ('Geografía e Historia', 'GH', True, False, 3), ('Griego', 'GRI', True, False, 3),
          ('Inglés', 'ING', True, False, 3),
          ('Latín', 'LAT', True, False, 3), ('Lengua Castellana y Literatura', 'LCL', True, False, 3),
          ('Matemáticas', 'MAT', True, False, 3), ('Música', 'MUS', True, False, 3),
          ('Orientación', 'ORI', True, False, 3),
          ('Tecnología', 'TEC', True, False, 3), ('Ningún departamento', 'N_D', True, False, 0),
          ('Alemán', 'ALE', True, False, 3), ('Actividades físicas y deportivas', 'AFD', True, False, 3),
          ('Administración y gestión', 'ADG', True, True, 3),
          ('Agraria', 'A', True, True, 3),
          ('Artes gráficas', 'ARG', True, True, 3),
          ('Artes y Artesanías', 'AYA', True, True, 3),
          ('Comercio y marketing', 'CM', True, True, 3),
          ('Edificación y obra civil', 'EOC', True, True, 3),
          ('Energía y Agua', 'EYA', True, True, 3),
          ('Electricidad y electrónica', 'EE', True, True, 3),
          ('Fabricación mecánica', 'FME', True, True, 3),
          ('Hostelería y turismo', 'HT', True, True, 3),
          ('Imagen personal', 'IP', True, True, 3),
          ('Imagen y Sonido', 'IS', True, True, 3),
          ('Industrias alimentarias', 'IA', True, True, 3),
          ('Industrias Extractivas', 'IEX', True, True, 3),
          ('Informática y comunicaciones', 'IC', True, True, 3),
          ('Instalación y mantenimiento', 'IM', True, True, 3),
          ('Madera, mueble y corcho', 'MMC', True, True, 3),
          ('Marítimo-Pesquera', 'MP', True, True, 3),
          ('Química', 'Q', True, True, 3),
          ('Sanidad', 'S', True, True, 3),
          ('Servicios socioculturaes y a la comunidad', 'SSC', True, True, 3),
          ('Textil, confección y piel', 'TCP', True, True, 3),
          ('Transporte y mantenimiento de vehículos', 'TMV', True, True, 3),
          ('Vídrio y Cerámica', 'VC', True, True, 3)]

    for d in ds:
        try:
            Departamento.objects.get(ronda=ronda, abreviatura=d[1])
        except:
            Departamento.objects.create(ronda=ronda, nombre=d[0], abreviatura=d[1], didactico=d[2],
                                        fp=d[3], horas_coordinador=d[4])


class Departamento(models.Model):
    ETAPAS = (('INF', 'Infantil'), ('PRI', 'Primaria'), ('SEC', 'Secundaria'))
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE)
    nombre = models.CharField('Denominación', max_length=310)
    abreviatura = models.CharField("Abreviatura", max_length=10)
    didactico = models.BooleanField("Es un departamento didáctico", default=True)
    fp = models.BooleanField("Es una familia profesional", default=False)
    horas_coordinador = models.IntegerField("Nº de horas de coordinación jefe de departamento", null=True, blank=True)
    etapa = models.CharField('Etapa', choices=ETAPAS, max_length=4, blank=True, null=True, default='SEC')

    # En primaria y secundaria no existen departamentos, pero utilizamos esta tabla para recoger la
    # estructura de 'Ciclo' que se utiliza en ellas.

    @property
    def jefe(self):
        try:
            return self.gauser_extra_programaciones_set.get(jefe=True)
        except:
            return Gauser_extra_programaciones.objects.none()

    @property
    def entidad(self):
        return self.ronda.entidad

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.ronda)


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
        return '%s (%s horas)' % (self.materia.nombre, self.materia.horas)


class Resultado_aprendizaje(models.Model):
    materia = models.ForeignKey(Materia_programaciones, on_delete=models.CASCADE)
    resultado = models.TextField("Resultado")
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)

    def __str__(self):
        return '%s - %s' % (self.resultado[:80], self.materia)


class Objetivo(models.Model):
    materia = models.ForeignKey(Materia_programaciones,
                                on_delete=models.CASCADE)  # Este campo es utilizado en programacion_append.html
    resultado_aprendizaje = models.ForeignKey(Resultado_aprendizaje, blank=True, null=True, on_delete=models.CASCADE)
    texto = models.TextField("Objetivo")
    crit_eval = models.TextField("Criterio de evaluación", blank=True, null=True)
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)

    def __str__(self):
        return '%s - %s' % (self.texto[:80], self.resultado_aprendizaje)


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
        return '%s - %s' % (self.code, self.nombre)


class Especialidad_funcionario(models.Model):
    cuerpo = models.ForeignKey(Cuerpo_funcionario, blank=True, null=True, on_delete=models.CASCADE)
    code = models.CharField('Código del cuerpo', max_length=10)
    nombre = models.CharField('Nombre del cuerpo', max_length=100)

    def __str__(self):
        return '%s - %s (%s)' % (self.code, self.nombre, self.cuerpo)


# class Cuerpo_entidad(models.Model):
#     entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
#     cuerpo = models.ForeignKey(Cuerpo_funcionario, blank=True, null=True, on_delete=models.CASCADE)
#
#     def __str__(self):
#         return '%s - %s' % (self.entidad, self.cuerpo)


class Especialidad_entidad(models.Model):
    ronda = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(Especialidad_funcionario, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ["especialidad__cuerpo"]
        verbose_name_plural = "Especialidades de funcionarios en la entidad"

    def __str__(self):
        return '%s - %s' % (self.ronda, self.especialidad)


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
        return '%s - %s' % (self.ge, self.departamento)


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
        return 'Título: %s' % (self.nombre)


class Obj_general(models.Model):
    titulo = models.ForeignKey(Titulo_FP, on_delete=models.CASCADE)
    objetivo = models.TextField('Objetivo general')
    educa_pk = models.CharField("pk en gauss_educa", max_length=12, blank=True, null=True)

    def __str__(self):
        return 'Título: %s - %s' % (self.titulo.nombre, self.objetivo)


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
        return '%s' % (self.modulo)


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
        return '%s - %s' % (self.nombre, self.duracion)


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
        return '%s - %s (%s horas)' % (self.unidad.nombre, self.contenido[:200], self.duracion)


#############################################################################
##################### PROGRAMACIONES LOMLOE  ################################
#############################################################################

class ProgSec(models.Model):
    TIPOS = (('BOR', 'Borrador'), ('DEF', 'Definitiva'), ('RE', 'Refuerzo Educativo'),
             ('AAC', 'Adaptación de Acceso al Currículo'), ('AC', 'Adaptación Curricular'),
             ('ACS', 'Adaptación Curricular Significativa'), ('EC', 'Enriquecimiento Curricular'),
             ('PRE', 'Plan de Recuperación'), ('PRT', 'Programa de Refuerzo Transitorio'),
             ('DIV', 'Diversificación Curricular'),)
    pga = models.ForeignKey(PGA, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre específico para la programación', blank=True, max_length=300)
    gep = models.ForeignKey(Gauser_extra_programaciones, blank=True, null=True, on_delete=models.CASCADE)
    alumno = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.SET_NULL)
    materia = models.ForeignKey(Materia_programaciones, blank=True, null=True, on_delete=models.CASCADE)
    areamateria = models.ForeignKey(AreaMateria, on_delete=models.CASCADE, blank=True, null=True)
    curso = models.ForeignKey(Curso, on_delete=models.SET_NULL, blank=True, null=True)
    tipo = models.CharField('Tipo de programación', max_length=4, choices=TIPOS, default='BOR', blank=True, null=True)
    departamento = models.ForeignKey(Departamento, on_delete=models.SET_NULL, blank=True, null=True)
    inicio_clases = models.DateField('Fecha de inicio de las clases', blank=True, null=True)
    fin_clases = models.DateField('Fecha de fin de las clases', blank=True, null=True)
    es_copia_de = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True)
    procdiversidad = models.TextField('Proced. adop. medidas de aten. a la divers.', blank=True, null=True, default='')
    planrecup = models.TextField('Organización y seguimiento de los PREs', blank=True, null=True, default='')
    identificador = models.CharField('Identificador', max_length=11, default=pass_generator)
    borrado = models.BooleanField('¿ProgSec borrada?', default=False)
    creado = models.DateField('Fecha de creación', auto_now_add=True)
    modificado = models.DateTimeField('Fecha de modificación', auto_now=True)

    @property
    def get_saberes(self):
        return self.saberbas_set.filter(borrado=False)

    @property
    def es_borrable(self):
        return CalAlumCE.objects.filter(cp__psec=self, valor__gt=0, cp__borrado=False).count() == 0

    @property
    def dias_curso(self):
        return range(1, 176)  # Un total de 175 días: 1, 2, 3, ..., 174, 175

    @property
    def tiempo_curso(self):
        inicio = self.inicio_clases
        fin = self.fin_clases
        # inicio = datetime(2021,9,1)
        # fin = datetime(2022,6,23)
        return (fin - inicio).total_seconds()
        # return 24105600 #Tiempo en segundos aproximado entre 9 septiembre y 15 de junio

    @property
    def num_periodos(self):
        return self.saberbas_set.aggregate(models.Sum('periodos'))['periodos__sum']

    def dia_curso_from_fecha(self, fecha):
        # El día uno de curso es la fecha self.inicio_clases
        # El día último de curso es la fecha self.fin_clases
        inicio = self.inicio_clases
        fin = self.fin_clases
        # inicio = datetime(2021, 9, 1)
        # fin = datetime(2022, 6, 23)
        try:
            return int((fecha - inicio) * 175 / (fin - inicio))
        except:
            return 0

    # @property
    # def comienzo(self):
    #     return self.saberbas_set.aggregate(models.Min('comienzo'))['comienzo__min']

    # @property
    # def fin(self):
    #     return self.saberbas_set.aggregate(models.Max('comienzo'))['comienzo__max']

    def get_permiso(self, gep):
        permiso = ''
        if self.cuadernoprof_set.filter(borrado=False).count() > 0:
            permiso += 'C'
        if gep == self.gep:
            permiso += 'LEX'
        try:
            permiso += self.docprogsec_set.get(gep=gep).permiso
        except:
            if gep.ge.has_permiso('ve_todas_programaciones'):
                permiso += 'L'
            else:
                permiso = 'No tiene permiso'
        return permiso

    def cepsec_evaluadas(self):
        cepsecs = []
        for criinstreval in CriInstrEval.objects.filter(peso__gt=0, ieval__asapren__sapren__sbas__psec=self,
                                                        borrado=False, ieval__borrado=False,
                                                        ieval__asapren__borrado=False,
                                                        ieval__asapren__sapren__borrado=False,
                                                        ieval__asapren__sapren__sbas__borrado=False):
            if criinstreval.cevps.cepsec not in cepsecs:
                cepsecs.append(criinstreval.cevps.cepsec)
        return cepsecs

    def cevpsec_evaluadas(self, cepsec):
        cevpsecs = []
        for criinstreval in CriInstrEval.objects.filter(peso__gt=0, ieval__asapren__sapren__sbas__psec=self,
                                                        cevps__cepsec=cepsec, borrado=False, ieval__borrado=False,
                                                        ieval__asapren__borrado=False,
                                                        ieval__asapren__sapren__borrado=False,
                                                        ieval__asapren__sapren__sbas__borrado=False):
            if criinstreval.cevps not in cevpsecs:
                cevpsecs.append(criinstreval.cevps)
        return cevpsecs

    @property
    def procedimientos_utilizados(self):
        procedimientos = {nombre: 0 for tipo, nombre in InstrEval.TIPOS}
        pesos = {'ceps_total': 0}
        for cepsec in self.cepsec_evaluadas():
            pesos['ceps_total'] += cepsec.valor
            pesos[cepsec.id] = {'cevs_total': 0}
            for cevpsec in self.cevpsec_evaluadas(cepsec):
                pesos[cepsec.id]['cevs_total'] += cevpsec.valor
                pesos[cepsec.id][cevpsec.id] = {'crii_total': 0}
                for criinstreval in cevpsec.criinstreval_set.filter(peso__gt=0, borrado=False, ieval__borrado=False,
                                                                    ieval__asapren__borrado=False,
                                                                    ieval__asapren__sapren__borrado=False,
                                                                    ieval__asapren__sapren__sbas__borrado=False):
                    pesos[cepsec.id][cevpsec.id]['crii_total'] += criinstreval.peso
        for cepsec in self.cepsec_evaluadas():
            contrib_cepsec = cepsec.valor / pesos['ceps_total']
            for cevpsec in self.cevpsec_evaluadas(cepsec):
                contrib_cevpsec = cevpsec.valor / pesos[cepsec.id]['cevs_total']
                for criinstreval in cevpsec.criinstreval_set.filter(peso__gt=0, borrado=False, ieval__borrado=False,
                                                                    ieval__asapren__borrado=False,
                                                                    ieval__asapren__sapren__borrado=False,
                                                                    ieval__asapren__sapren__sbas__borrado=False):
                    contrib_crii = criinstreval.peso / pesos[cepsec.id][cevpsec.id]['crii_total']
                    proc = criinstreval.ieval.get_tipo_display()
                    procedimientos[proc] += contrib_cepsec * contrib_cevpsec * contrib_crii * 100
        return procedimientos

    @property
    def asignaturas_ambito(self):
        return set(self.areamateria.competenciaespecifica_set.all().values_list('asignatura', flat=True))

    @property
    def ces_asignaturas_ambito(self):
        caa = {}
        for ce in self.areamateria.competenciaespecifica_set.all():
            if not ce.asignatura:
                ce.asignatura = ce.am.nombre
                ce.save()
        ces = self.areamateria.competenciaespecifica_set.all()
        for a in set(ces.values_list('asignatura', flat=True)):
            caa[a] = ces.filter(asignatura=a)
        return caa

    def ces_asignatura(self, asignatura):
        return self.areamateria.competenciaespecifica_set.filter(asignatura=asignatura)

    @property
    def ceprogsec_porcentajes(self):
        ceps = self.ceprogsec_set.all()
        total_valores = ceps.aggregate(models.Sum('valor'))['valor__sum']
        return {cep.id: str(round(cep.valor / total_valores * 100, 2)) for cep in ceps}

    def __str__(self):
        return '%s - %s (%s)' % (self.pga.ronda, self.areamateria, self.gep.ge.gauser.get_full_name())


class DocProgSec(models.Model):  # Docente habilitado en la progsec
    PERMISOS = (('L', 'Lectura'), ('E', 'Edición'), ('X', 'Edición y borrado'))
    psec = models.ForeignKey(ProgSec, on_delete=models.CASCADE)
    gep = models.ForeignKey(Gauser_extra_programaciones, blank=True, null=True, on_delete=models.CASCADE)
    permiso = models.CharField('Permiso en relación a esta programación', max_length=5, choices=PERMISOS, default='L')

    def __str__(self):
        return '%s - %s (%s)' % (self.psec, self.gep, self.get_permiso_display())


class CEProgSec(models.Model):
    NIVELES = (('00INF0', 'Primer Ciclo Infantil - 0 años'), ('00INF1', 'Primer Ciclo Infantil - 1 año'),
               ('00INF2', 'Primer Ciclo Infantil - 2 años'), ('00INF3', 'Segundo Ciclo Infantil - 3 años'),
               ('00INF4', 'Segundo Ciclo Infantil - 4 años'), ('00INF5', 'Segundo Ciclo Infantil - 5 años'),
               ('10PRI1', 'Primer Ciclo Primaria - 1er Curso'), ('10PRI2', 'Primer Ciclo Primaria - 2o Curso'),
               ('10PRI3', 'Segundo Ciclo Primaria - 3er Curso'), ('10PRI4', 'Segundo Ciclo Primaria - 4o Curso'),
               ('10PRI5', 'Tercer Ciclo Primaria - 5o Curso'), ('10PRI6', 'Tercer Ciclo Primaria - 6o Curso'),
               ('20ESO1', '1º de ESO'), ('20ESO2', '2º de ESO'), ('20ESO3', '3º de ESO'), ('20ESO4', '4º de ESO'))
    GRADOS = ((5, '5%'), (10, '10%'), (15, '15%'), (20, '20%'), (25, '25%'), (30, '30%'), (35, '35%'),
              (40, '40%'), (45, '45%'), (50, '50%'), (55, '55%'), (60, '60%'), (65, '65%'), (70, '70%'),
              (75, '75%'), (80, '80%'), (85, '85%'), (90, '90%'), (95, '95%'), (100, '100%'),)
    psec = models.ForeignKey(ProgSec, on_delete=models.CASCADE)
    ce = models.ForeignKey(CompetenciaEspecifica, on_delete=models.CASCADE)
    valor = models.FloatField('Peso del criterio en la puntuación total de la Comp. Específ.', blank=True, default=1)
    nivel = models.CharField('Nivel de referencia para evaluar al alumno/a', max_length=7, default='', blank=True,
                             null=True, choices=NIVELES)
    description = models.TextField('Descripción de la modificación asociada', default='')
    grado = models.IntegerField('Grado de adquisción de la competencia específica', default=100, choices=GRADOS)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    @property
    def cevrogsec_porcentajes(self):
        cevs = self.cevprogsec_set.all()
        total_valores = cevs.aggregate(models.Sum('valor'))['valor__sum']
        return {cev.id: str(round(cev.valor / total_valores * 100, 2)) for cev in cevs}

    @property
    def num_criinstreval_vinculados(self):
        total = 0
        for cevpsec in self.cevprogsec_set.all():
            cantidad = cevpsec.criinstreval_vinculados.count()
            if cantidad == 0:
                cantidad = 1
            total += cantidad
        return total

    @property
    def tipos_procedimientos_utilizados(self):
        tipos = []
        for cevpsec in self.cevprogsec_set.all():
            for criinstreval in cevpsec.criinstreval_vinculados:
                tipos.append((criinstreval.ieval.tipo, criinstreval.ieval.get_tipo_display()))
        return set(tipos)

    class Meta:
        verbose_name_plural = 'Competencias específicas asociadas a una programación'
        ordering = ['ce__asignatura', 'ce__orden', ]

    def __str__(self):
        return '%s - %s (%s)' % (self.psec, self.ce, self.valor)


class CEvProgSec(models.Model):
    cepsec = models.ForeignKey(CEProgSec, on_delete=models.CASCADE, blank=True, null=True)
    cev = models.ForeignKey(CriterioEvaluacion, on_delete=models.CASCADE)
    valor = models.FloatField('Peso del criterio en la puntuación total de la Comp. Específ.', blank=True, default=1)
    description = models.TextField('Descripción de la aplicación asociada al CEV', default='')
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    @property
    def criinstreval_vinculados(self):
        return self.criinstreval_set.filter(peso__gt=0, borrado=False)

    class Meta:
        verbose_name_plural = 'Criterios de Evaluación asociados a una programación'
        ordering = ['cev__orden', ]

    def __str__(self):
        return '%s - %s (%s)' % (self.cepsec, self.cev, self.valor)


def update_documentos_psec(instance, filename):
    centro_code = str(instance.psec.pga.ronda.entidad.code)
    ronda = slugify(instance.psec.pga.ronda.nombre)
    curso = slugify(instance.psec.materia.curso.nombre)
    materia = slugify(instance.psec.materia.nombre)
    nombre = slugify(instance.nombre)
    ext = filename.rpartition('.')[2]
    return 'programaciones/%s/%s/materias/%s/%s/%s.%s' % (centro_code, ronda, curso, materia, nombre, ext)


class LibroRecurso(models.Model):
    psec = models.ForeignKey(ProgSec, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre del libro o recurso', blank=True, max_length=300)
    isbn = models.CharField('ISBN', blank=True, max_length=20)
    observaciones = models.TextField('Observaciones', blank=True)
    doc_file = models.FileField("Libro/recurso asociado a la programación", upload_to=update_documentos_psec, null=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    @property
    def filename(self):
        return os.path.basename(self.doc_file.name)

    def __str__(self):
        return 'Libro-Recurso: %s' % (self.nombre)


class ActExCom(models.Model):
    psec = models.ForeignKey(ProgSec, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre de la actividad', blank=True, max_length=300)
    observaciones = models.TextField('Observaciones', blank=True)
    inicio = models.DateTimeField('Fecha y hora de comienzo', blank=True, null=True)
    fin = models.DateTimeField('Fecha y hora de finalización', blank=True, null=True)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'Actividades extraescolares en programaciones (ActExCom)'
        ordering = ['inicio', ]

    def __str__(self):
        return '%s - %s (%s - %s)' % (self.psec, self.nombre, self.inicio, self.fin)


class SaberBas(models.Model):
    psec = models.ForeignKey(ProgSec, on_delete=models.CASCADE)
    orden = models.IntegerField('Orden del saber básico dentro del conjunto de saberes', default=1)
    nombre = models.CharField('Nombre de la actividad', blank=True, max_length=300)
    comienzo = models.DateField('Fecha de comienzo programada', default=now)
    periodos = models.IntegerField('Número estimado de periodos lectivos para impartirlo', default=1)
    librorecursos = models.ManyToManyField(LibroRecurso, blank=True)
    actexcoms = models.ManyToManyField(ActExCom, blank=True)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)
    borrado = models.BooleanField('¿SaberBas borrado?', default=False)

    @property
    def get_sitaprens(self):
        return self.sitapren_set.filter(borrado=False)

    @property
    def es_borrable(self):
        return CalAlumValor.objects.filter(ca__cie__ieval__asapren__sapren__sbas=self, ca__cp__tipo='PRO',
                                           ca__cp__borrado=False, ecpv__valor__gt=0).count() == 0

    @property
    def fin(self):
        # Fecha de finalización aproximada calculada para este saber básico:
        inicio = self.psec.inicio_clases
        fin = self.psec.fin_clases
        # inicio = datetime(2021, 9, 1)
        # fin = datetime(2022, 6, 23)
        timedelta_periodo = (fin - inicio) / self.psec.num_periodos
        return self.comienzo + timedelta_periodo * self.periodos

    @property
    def num_divs(self):
        # Devuelve el número de divs que ocupa este saber básico en el diagrama de Gantt
        divisiones_gantt = len(self.psec.dias_curso)
        n_periodos = self.psec.num_periodos
        try:
            return int(self.periodos * divisiones_gantt / n_periodos)
        except:
            return 0

    @property
    def div_comienzo(self):
        return self.psec.dia_curso_from_fecha(self.comienzo)

    @property
    def divs_gantt(self):
        c = self.div_comienzo
        return range(c, c + self.num_divs)

    @property
    def num_criinstreval(self):
        num = CriInstrEval.objects.filter(ieval__asapren__sapren__sbas=self, peso__gt=0, borrado=False).count()
        return num
        # return 1 if num == 0 else num

    class Meta:
        # ordering = ['psec', ]
        ordering = ['psec', 'comienzo']
        # ordering = ['psec', 'orden']

    def __str__(self):
        return '%s - %s (%s)' % (self.psec, self.nombre, self.periodos)


class SitApren(models.Model):
    sbas = models.ForeignKey(SaberBas, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre dado a la situación de aprendizaje', blank=True, max_length=300)
    objetivo = models.TextField('Descripción de la situación de aprendizaje y lo que pretende conseguir', blank=True)
    ceps = models.ManyToManyField(CEProgSec, blank=True)
    contenidos_sbas = models.TextField('Saberes básicos que se van a trabajar en la SAP', blank=True, default='')
    # producto = models.TextField('Producto o productos resultado de la situación de aprendizaje', blank=True)
    borrado = models.BooleanField('¿SitApren borrada?', default=False)

    class Meta:
        verbose_name_plural = 'Situaciones de aprendizaje'
        ordering = ['sbas__psec', 'sbas', 'id']

    @property
    def get_asaprens(self):
        return self.actsitapren_set.filter(borrado=False)

    @property
    def es_borrable(self):
        return CalAlumValor.objects.filter(ca__cie__ieval__asapren__sapren=self, ca__cp__tipo='PRO',
                                           ca__cp__borrado=False, ecpv__valor__gt=0).count() == 0

    def ceps_es_borrable(self, ceps):
        cevps = ceps.cevprogsec_set.all()
        return CalAlumValor.objects.filter(ca__cie__ieval__asapren__sapren=self, ca__cp__tipo='PRO',
                                           ca__cp__borrado=False, ecpv__valor__gt=0,
                                           ca__cie__cevps__in=cevps).count() == 0

    @property
    def num_asapren(self):
        return self.actsitapren_set.count()

    @property
    def num_instreval(self):
        return InstrEval.objects.filter(asapren__sapren=self, borrado=False).count()

    @property
    def num_criinstreval(self):
        return CriInstrEval.objects.filter(ieval__asapren__sapren=self, peso__gt=0, borrado=False).count()

    def __str__(self):
        return '%s - %s' % (self.sbas, self.nombre)


class ActSitApren(models.Model):
    sapren = models.ForeignKey(SitApren, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre dado a la situación de aprendizaje', blank=True, max_length=300)
    description = models.TextField('Descripción de la actividad ligada a la situación de aprendizaje', blank=True)
    producto = models.TextField('Producto o productos resultado de la situación de aprendizaje', blank=True)
    borrado = models.BooleanField('¿ActSitApren borrado?', default=False)

    class Meta:
        verbose_name_plural = 'Actividades en situaciones de aprendizaje'
        ordering = ['sapren__sbas__psec', 'sapren__sbas', 'sapren', 'id']

    @property
    def get_instrevals(self):
        return self.instreval_set.filter(asapren=self, borrado=False)

    @property
    def es_borrable(self):
        return CalAlumValor.objects.filter(ca__cie__ieval__asapren=self, ecpv__valor__gt=0, ca__cp__tipo='PRO',
                                           ca__cp__borrado=False).count() == 0

    @property
    def num_criinstreval(self):
        return CriInstrEval.objects.filter(ieval__asapren=self, peso__gt=0, borrado=False).count()

    def __str__(self):
        return '%s - %s' % (self.sapren, self.nombre)


class InstrEval(models.Model):
    # TIPOS = (('ESVAL', 'Escala de valoración'), ('LCONT', 'Lista de control'), ('RANEC', 'Registro anecdótico'),
    #          ('CUADE', 'Revisión del cuaderno'), ('COMPO', 'Composición y/o ensayo'),
    #          ('PRESC', 'Preguntas de respuesta corta'), ('PREEM', 'Preguntas de emparejamiento'),
    #          ('PTINC', 'Preguntas de texto incompleto'), ('POMUL', 'Preguntas de opción múltiple'),
    #          ('PRVOF', 'Preguntas de verdadero/falso justificadas'), ('PRAYD', 'Preguntas de analogías y diferencias'),
    #          ('PRIEL', 'Preguntas de interpretación y/o elaboración de gráficos, tablas, mapas, ...'),
    #          ('TMONO', 'Trabajo monográfico o de investigación'), ('EXATR', 'Examen tradicional/Prueba objetiva'))
    ESCALAS = (('ESVCL', 'Escala de valoración cualitativa'), ('ESVCN', 'Escala de valoración cuantitativa'),
               ('LCONT', 'Lista de control'))
    TIPOS = (('OBSS', 'Observación sistemática'), ('PROD', 'Procesos de diálogo/Debates'),
             ('ESQMA', 'Esquemas y mapas conceptuales'), ('PREJ', 'Pruebas de ejecución'),
             ('PRESE', 'Presentación de un producto'), ('CUADE', 'Revisión del cuaderno o producto'),
             ('EXATR', 'Examen tradicional/Prueba objetiva/competencial'),
             ('BLOOM', 'Preguntas de análisis, evaluación y/o creación'), ('COMPO', 'Composición y/o ensayo'),
             ('TMONO', 'Trabajo monográfico o de investigación'))
    asapren = models.ForeignKey(ActSitApren, on_delete=models.CASCADE, blank=True, null=True)
    tipo = models.CharField('Tipo de instrumento', blank=True, max_length=10, choices=TIPOS)
    nombre = models.CharField('Nombre dado al instrumento', blank=True, max_length=300)
    borrado = models.BooleanField('¿InstrEval borrado?', default=False)

    class Meta:
        verbose_name_plural = 'Instrumentos/Procedimientos de evaluación'
        ordering = ['asapren__sapren__sbas__psec', 'asapren__sapren__sbas', 'asapren__sapren', 'asapren', 'id']

    @property
    def es_borrable(self):
        return CalAlumValor.objects.filter(ca__cie__ieval=self, ecpv__valor__gt=0, ca__cp__tipo='PRO',
                                           ca__cp__borrado=False).count() == 0

    @property
    def get_criinstreval(self):
        # Para evitar utilizar criinstreval_set.all que devolvería también aquellos que tienen peso 0
        return CriInstrEval.objects.filter(ieval=self, peso__gt=0, borrado=False)

    @property
    def num_criinstreval(self):
        return CriInstrEval.objects.filter(ieval=self, peso__gt=0, borrado=False).count()

    def __str__(self):
        return '%s - %s' % (self.asapren, self.nombre)


class CriInstrEval(models.Model):
    ieval = models.ForeignKey(InstrEval, on_delete=models.CASCADE)
    cevps = models.ForeignKey(CEvProgSec, on_delete=models.CASCADE, blank=True, null=True)
    peso = models.IntegerField('Peso sobre la evaluación del mismo criterio en otros saberes', default=0)
    borrado = models.BooleanField('¿CriInstrEval borrado?', default=False)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'Criterios de Evaluación asociados a un instrumento/procedimiento'
        ordering = ['cevps__cepsec__ce__asignatura', 'cevps__cepsec__ce__orden', 'cevps__cev__orden']

    @property
    def es_borrable(self):
        return CalAlumValor.objects.filter(ca__cie=self, ecpv__valor__gt=0, ca__cp__tipo='PRO',
                                           ca__cp__borrado=False).count() == 0

    def __str__(self):
        return '%s - %s (%s)' % (self.ieval, self.cevps, self.peso)


############################################################
class RepoSitApren(models.Model):
    autor = models.ForeignKey(Gauser_extra, on_delete=models.SET_NULL, blank=True, null=True)
    nombre = models.CharField('Nombre dado a la situación de aprendizaje', blank=True, max_length=300)
    objetivo = models.TextField('Descripción de la situación de aprendizaje y lo que pretende conseguir', blank=True)
    areamateria = models.ForeignKey(AreaMateria, on_delete=models.CASCADE, blank=True, null=True)
    ces = models.ManyToManyField(CompetenciaEspecifica, blank=True)
    publicar = models.BooleanField('¿Publicar?', default=False)
    es_copia_de = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True)
    borrada = models.BooleanField('¿Está borrada?', default=False)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)
    contenidos_sbas = models.TextField('Saberes básicos que se van a trabajar en la SAP', blank=True, default='')

    class Meta:
        verbose_name_plural = 'SAP Repositorio de situaciones de aprendizaje'
        ordering = ['autor', 'areamateria', 'id']

    # @property
    # def ces(self): #Competencias específicas
    #     ce_ids = self.repocev_set.values_list('cev__ce__id').distinct()
    #     return CompetenciaEspecifica.objects.filter(id__in=ce_ids)

    @property
    def val_global(self):
        try:
            rsaprenlikes = self.repositaprenlike_set.all()
            suma = rsaprenlikes.aggregate(models.Sum('like'))['like__sum']
            return round(suma / rsaprenlikes.count(), 2)
        except:
            return ''

    @property
    def num_asapren(self):
        return self.repoactsitapren_set.count()

    @property
    def num_instreval(self):
        return RepoInstrEval.objects.filter(asapren__sapren=self).count()

    @property
    def num_criinstreval(self):
        return RepoCriInstrEval.objects.filter(ieval__asapren__sapren=self, peso__gt=0).count()

    def __str__(self):
        return '%s - %s' % (self.areamateria, self.nombre)


class RepoSitAprenLike(models.Model):
    rsap = models.ForeignKey(RepoSitApren, on_delete=models.CASCADE, blank=True, null=True)
    ge = models.ForeignKey(Gauser_extra, on_delete=models.SET_NULL, blank=True, null=True)
    like = models.IntegerField('Puntuación dada a la situación de aprendizaje', default=0)
    creado = models.DateField("Fecha de creación", auto_now_add=True)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'SAP Likes para situaciones de aprendizaje'
        ordering = ['rsap', 'like']

    def __str__(self):
        return '%s - %s' % (self.rsap, self.like)


class RepoCEv(models.Model):
    sapren = models.ForeignKey(RepoSitApren, on_delete=models.CASCADE)
    cev = models.ForeignKey(CriterioEvaluacion, on_delete=models.CASCADE)
    valor = models.FloatField('Peso del criterio en la puntuación total de la Comp. Específ.', blank=True, default=1)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'SAP Criterios de Evaluación empleados en una Situación de Aprendizaje'
        ordering = ['sapren', 'cev__ce__orden', 'cev__orden', ]

    def __str__(self):
        return '%s - %s (%s)' % (self.cev.ce, self.cev, self.valor)


class RepoActSitApren(models.Model):
    sapren = models.ForeignKey(RepoSitApren, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre dado a la situación de aprendizaje', blank=True, max_length=300)
    description = models.TextField('Descripción de la actividad ligada a la situación de aprendizaje', blank=True)
    producto = models.TextField('Producto o productos resultado de la situación de aprendizaje', blank=True)

    class Meta:
        verbose_name_plural = 'SAP Actividades en situaciones de aprendizaje'
        ordering = ['sapren', 'id']

    @property
    def num_criinstreval(self):
        return RepoCriInstrEval.objects.filter(ieval__asapren=self, peso__gt=0).count()

    def __str__(self):
        return '%s - %s' % (self.sapren, self.nombre)


class RepoInstrEval(models.Model):
    ESCALAS = (('ESVCL', 'Escala de valoración cualitativa'), ('ESVCN', 'Escala de valoración cuantitativa'),
               ('LCONT', 'Lista de control'))
    # TIPOS = (('CUADE', 'Revisión del cuaderno'), ('COMPO', 'Composición y/o ensayo'), ('RANEC', 'Registro anecdótico'),
    #          ('PRESC', 'Preguntas de respuesta corta'), ('PREEM', 'Preguntas de emparejamiento'),
    #          ('PTINC', 'Preguntas de texto incompleto'), ('POMUL', 'Preguntas de opción múltiple'),
    #          ('PRVOF', 'Preguntas de verdadero/falso justificadas'), ('PRAYD', 'Preguntas de analogías y diferencias'),
    #          ('PRIEL', 'Preguntas de interpretación y/o elaboración de gráficos, tablas, mapas, ...'),
    #          ('TMONO', 'Trabajo monográfico o de investigación'), ('EXATR', 'Examen tradicional/Prueba objetiva'))
    TIPOS = (('OBSS', 'Observación sistemática'), ('PROD', 'Procesos de diálogo/Debates'),
             ('ESQMA', 'Esquemas y mapas conceptuales'), ('PREJ', 'Pruebas de ejecución'),
             ('PRESE', 'Presentación de un producto'), ('CUADE', 'Revisión del cuaderno o producto'),
             ('EXATR', 'Examen tradicional/Prueba objetiva/competencial'),
             ('BLOOM', 'Preguntas de análisis, evaluación y/o creación'), ('COMPO', 'Composición y/o ensayo'),
             ('TMONO', 'Trabajo monográfico o de investigación'))
    asapren = models.ForeignKey(RepoActSitApren, on_delete=models.CASCADE, blank=True, null=True)
    tipo = models.CharField('Tipo de instrumento', blank=True, max_length=10, choices=TIPOS)
    nombre = models.CharField('Nombre dado al instrumento', blank=True, max_length=300)

    class Meta:
        verbose_name_plural = 'SAP Instrumentos/Procedimientos de evaluación'
        ordering = ['asapren__sapren', 'asapren', 'id']

    @property
    def get_criinstreval(self):
        # Para evitar utilizar criinstreval_set.all que devolvería también aquellos que tienen peso 0
        return RepoCriInstrEval.objects.filter(ieval=self, peso__gt=0)

    @property
    def num_criinstreval(self):
        return RepoCriInstrEval.objects.filter(ieval=self, peso__gt=0).count()

    def __str__(self):
        return '%s - %s' % (self.asapren, self.nombre)


class RepoCriInstrEval(models.Model):
    ieval = models.ForeignKey(RepoInstrEval, on_delete=models.CASCADE)
    cevps = models.ForeignKey(RepoCEv, on_delete=models.CASCADE, blank=True, null=True)
    peso = models.IntegerField('Peso sobre la evaluación del mismo criterio en otros saberes', default=0)
    modificado = models.DateTimeField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'SAP Criterios de Evaluación asociados a un instrumento/procedimiento'
        ordering = ['cevps__cev__ce__orden', 'cevps__cev__orden']

    def __str__(self):
        return '%s - %s (%s)' % (self.ieval, self.cevps, self.peso)


############################################################

class CuadernoProf(models.Model):
    VISTAS = (('NOR', 'Vista Normal'), ('COM', 'Vista por competencias'))
    TIPOS = (('PRO', 'Nivel de detalle: Procedimientos de evaluación'),
             ('CRI', 'Nivel de detalle: Criterios de evaluación'),
             ('CES', 'Nivel de detalle: Competencias específicas'),)
    ge = models.ForeignKey(Gauser_extra, on_delete=models.SET_NULL, related_name='cuaderno_docente_set', blank=True,
                           null=True)
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, blank=True, null=True)
    psec = models.ForeignKey(ProgSec, on_delete=models.CASCADE, blank=True, null=True)
    vmin = models.IntegerField('Valor mínimo de calificación asignable a un alumno', default=0)
    vmax = models.IntegerField('Valor máximo de calificación asignable a un alumno', default=10)
    alumnos = models.ManyToManyField(Gauser_extra, blank=True, related_name='cuaderno_alumno_set')
    vista = models.CharField('Tipo de vista', max_length=3, choices=VISTAS, default='NOR')
    tipo = models.CharField('Tipo de vista', max_length=3, choices=TIPOS, default='PRO')
    borrado = models.BooleanField('¿Cuaderno borrado?', default=False)
    log = models.TextField('Log del cuaderno', blank=True, default='')

    class Meta:
        verbose_name_plural = 'Cuadernos de docente'
        ordering = ['-id', 'psec', 'ge']

    @property
    def num_columns(self):
        # El número de columnas del cuaderno será el número de CriInstrEval más la columna del nombre
        return CriInstrEval.objects.filter(ieval__asapren__sapren__sbas__psec=self.psec, borrado=False).count() + 1

    @property
    def nombre(self):
        try:
            ronda = self.psec.pga.ronda
        except:
            ronda = 'Curso escolar desconocido'
        try:
            am = self.psec.areamateria.nombre
        except:
            am = 'Asignatura desconocida'
        try:
            if self.alumnos.count() > 0:
                grupos = []
                for alumno in self.alumnos.all():
                    try:
                        if alumno.gauser_extra_estudios.grupo.nombre not in grupos:
                            grupos.append(alumno.gauser_extra_estudios.grupo.nombre)
                    except:
                        if 'Grupo desconocido' not in grupos:
                            grupos.append('Grupo desconocido')
                grupo = '-'.join(grupos)
            else:
                grupo = self.grupo.nombre
        except:
            grupo = 'Grupo desconocido'
        return '%s - %s - %s (%s)' % (ronda, am, grupo, self.tipo)

    def calificacion_alumno_cev(self, alumno, cev):  # Calificación de un determinado criterio de evaluación
        cas = self.calalum_set.filter(alumno=alumno, cie__cevps__cev=cev)
        numerador = 0
        denominador = 0
        for ca in cas:
            if ca.cal > 0:
                numerador += ca.cie.peso * ca.cal
                denominador += ca.cie.peso
        try:
            return round(numerador / denominador, 2)
        except:
            return 0

    def calificacion_alumno_ce(self, alumno, ce):  # Calificación de una determinada competencia específica
        try:
            return self.calalumce_set.get(alumno=alumno, cep__ce=ce).valor
        except Exception as msg:
            try:
                # En algún cuaderno se ha generado más de un calalumnce y, por tanto, aparece esta exception.
                # Es necesario borrar todas las calalumnces y generarlas de nuevo
                calalumnces = self.calalumce_set.filter(alumno=alumno, cep__ce=ce)
                if calalumnces.count() > 1:
                    for calalumnce in calalumnces:
                        calalumnce.calalumcev_set.all().delete()
                    calalumnces.delete()
                    calalumvalores = CalAlumValor.objects.filter(ca__alumno=alumno, ca__cp=self)
                    for calalumvalor in calalumvalores:
                        # El grabado, save(), de un calalumvalor provoca la creación de calalumces y calalumcevs.
                        # De esta forma regeneramos todos los valores:
                        calalumvalor.save()
                    # Registramos el error:
                    aviso = 'cuaderno 10000: %s - alumno: %s - msg: %s' % (self.id, alumno.id, msg)
                    Aviso.objects.create(usuario=alumno, aviso=aviso, fecha=now(), aceptado=True)
                elif calalumnces.count() == 0:
                    # calalumvalores = CalAlumValor.objects.filter(ca__alumno=alumno, ca__cp=self)
                    # for calalumvalor in calalumvalores:
                    #    # El grabado, save(), de un calalumvalor provoca la creación de calalumces y calalumcevs.
                    #    # De esta forma regeneramos todos los valores:
                    #     calalumvalor.save()
                    ## Registramos el error:
                    aviso = 'cuaderno 10000-0: %s - alumno: %s - msg: %s' % (self.id, alumno.id, msg)
                    Aviso.objects.create(usuario=alumno, aviso=aviso, fecha=now(), aceptado=True)
                    return 0
                try:
                    return self.calalumce_set.get(alumno=alumno, cep__ce=ce).valor
                except:
                    return 10000
            except:
                return 20000
            # cep = CEProgSec.objects.get(psec=self.psec, ce=ce)
            # cace = CalAlumCE.objects.create(alumno=alumno, cp=self, cep=cep)

        #################################################################
        ######## LINEAS DE CÓDIGO ANTIGUAS:
        # try:
        #     cepsec = self.psec.ceprogsec_set.get(ce=ce)
        # except:
        #     return 1000000  # Si se da un error devolverá una cantidad tan grande que lo evidenciará
        # cevpsecs = cepsec.cevprogsec_set.all()
        # numerador = 0
        # denominador = 0
        # for cevp in cevpsecs:
        #     cal_cev = self.calificacion_alumno_cev(alumno, cevp.cev)
        #     if cal_cev > 0:
        #         numerador += cal_cev * cevp.valor
        #         denominador += cevp.valor
        # try:
        #     return round(numerador / denominador, 2)
        # except:
        #     return 0

    def calificacion_alumno(self, alumno):
        ceps = self.psec.ceprogsec_set.all()
        numerador = 0
        denominador = 0
        for cep in ceps:
            cal_ce = self.calificacion_alumno_ce(alumno, cep.ce)
            if cal_ce > 0:
                numerador += cal_ce * cep.valor
                denominador += cep.valor
        try:
            return round(numerador / denominador, 2)
        except:
            return 0

    def calificacion_alumno_asignatura(self, alumno, asignatura):
        ceps = self.psec.ceprogsec_set.filter(ce__asignatura=asignatura)
        numerador = 0
        denominador = 0
        for cep in ceps:
            cal_ce = self.calificacion_alumno_ce(alumno, cep.ce)
            if cal_ce > 0:
                numerador += cal_ce * cep.valor
                denominador += cep.valor
        try:
            return round(numerador / denominador, 2)
        except:
            return 0

    @property
    def estructura_cuaderno(self):
        sbs_array = []
        for sb in self.psec.saberbas_set.filter(borrado=False):
            sb_element = {'sb': sb, 'sb_columns': 0, 'saps': []}
            saps = sb.sitapren_set.filter(borrado=False)
            if saps.count() == 0:
                sb_element['sb_columns'] += 1
                sap_dict = {'sap': False, 'sap_columns': 1, 'asaps': []}
                asap_dict = {'asap': False, 'asap_columns': 1, 'ievals': []}
                ieval_dict = {'ieval': False, 'ieval_columns': 1, 'cievals': []}
                ieval_dict['cievals'].append(False)
                asap_dict['ievals'].append(ieval_dict)
                sap_dict['asaps'].append(asap_dict)
                sb_element['saps'].append(sap_dict)
            for sap in saps:
                sap_element = {'sap': sap, 'sap_columns': 0, 'asaps': []}
                asaps = sap.actsitapren_set.filter(borrado=False)
                if asaps.count() == 0:
                    sb_element['sb_columns'] += 1
                    sap_element['sap_columns'] += 1
                    asap_dict = {'asap': False, 'asap_columns': 1, 'ievals': []}
                    ieval_dict = {'ieval': False, 'ieval_columns': 1, 'cievals': []}
                    ieval_dict['cievals'].append(False)
                    asap_dict['ievals'].append(ieval_dict)
                    sap_dict['asaps'].append(asap_dict)
                for asap in asaps:
                    asap_element = {'asap': asap, 'asap_columns': 0, 'ievals': []}
                    ievals = asap.instreval_set.filter(borrado=False)
                    if ievals.count() == 0:
                        sb_element['sb_columns'] += 1
                        sap_element['sap_columns'] += 1
                        asap_element['asap_columns'] += 1
                        ieval_dict = {'ieval': False, 'ieval_columns': 1, 'cievals': []}
                        asap_element['ievals'].append(ieval_dict)
                        ieval_dict['cievals'].append(False)
                    for ieval in ievals:
                        ieval_element = {'ieval': ieval, 'ieval_columns': 0, 'cievals': []}
                        cievals = ieval.get_criinstreval
                        if cievals.count() == 0:
                            sb_element['sb_columns'] += 1
                            sap_element['sap_columns'] += 1
                            asap_element['asap_columns'] += 1
                            ieval_element['ieval_columns'] += 1
                            ieval_element['cievals'].append(False)
                        for cieval in cievals:
                            sb_element['sb_columns'] += 1
                            sap_element['sap_columns'] += 1
                            asap_element['asap_columns'] += 1
                            ieval_element['ieval_columns'] += 1
                            ieval_element['cievals'].append(cieval)
                        asap_element['ievals'].append(ieval_element)
                    sap_element['asaps'].append(asap_element)
                sb_element['saps'].append(sap_element)
            sbs_array.append(sb_element)
        return sbs_array

    def __str__(self):
        autor = '%s (%s)' % (self.ge.gauser.get_full_name(), self.ge.gauser.email)
        return '%s -- %s - Borrado: %s' % (self.nombre, autor, self.borrado)


class CalAlumCE(models.Model):
    ORDEN = {'00INF0': 1, '00INF1': 2, '00INF2': 3, '00INF3': 4, '00INF4': 5, '00INF5': 6, '10PRI1': 7, '10PRI2': 8,
             '10PRI3': 9, '10PRI4': 10, '10PRI5': 11, '10PRI6': 12, '20ESO1': 13, '20ESO2': 14, '20ESO3': 15,
             '20ESO4': 16}
    cp = models.ForeignKey(CuadernoProf, on_delete=models.CASCADE, blank=True, null=True)
    alumno = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    cep = models.ForeignKey(CEProgSec, on_delete=models.CASCADE)
    valor = models.FloatField('Valor cuantitativo asociado a la competencia específica', default=0)
    obs = models.TextField('Observaciones a la calificación otorgada', blank=True, default='')

    @property
    def valor_final(self):
        try:
            orden_curso_alumno = self.ORDEN[self.cp.psec.areamateria.curso]
            orden_nivel_alumno = self.ORDEN[self.cep.nivel]
            diferencia = orden_curso_alumno - orden_nivel_alumno
        except:
            diferencia = 0
        return self.valor * (1 / 2) ** diferencia

    def __str__(self):
        return '%s - %s (%s)' % (self.cep.psec, self.cep.ce.nombre, self.valor)


class CalAlumCEv(models.Model):
    calalumce = models.ForeignKey(CalAlumCE, on_delete=models.CASCADE)
    cevp = models.ForeignKey(CEvProgSec, on_delete=models.CASCADE)
    valor = models.FloatField('Valor cuantitativo asociado al criterio de evaluación', default=0)
    obs = models.TextField('Observaciones a la calificación otorgada', blank=True, default='')

    # def save(self, *args, **kwargs):
    #     self.slug = slugify(self.title)
    #     super(CalAlumCEv, self).save(*args, **kwargs)
    def __str__(self):
        return '%s - %s (%s)' % (self.calalumce, self.cevp.cev.texto[:50], self.valor)


@receiver(post_save, sender=CalAlumCEv)
def update_calalumce(sender, instance, **kwargs):
    numerador_final = 0
    denominador_final = 0
    for calalumcev in instance.calalumce.calalumcev_set.all():
        if calalumcev.valor > 0:  # Esto es para no tener en cuenta las calificaciones iguales a 0
            numerador_final += calalumcev.cevp.valor * calalumcev.valor
            denominador_final += calalumcev.cevp.valor
    try:
        instance.calalumce.valor = round(numerador_final / denominador_final, 2)
    except:
        instance.calalumce.valor = 0
    instance.calalumce.save()


class EscalaCP(models.Model):  # Escala utilizada en el CuardernoProf
    ESCALAS = (('ESVCL', 'Escala de valoración cualitativa'), ('ESVCN', 'Escala de valoración cuantitativa'),
               ('LCONT', 'Lista de control'))
    cp = models.ForeignKey(CuadernoProf, on_delete=models.CASCADE)
    ieval = models.ForeignKey(InstrEval, on_delete=models.CASCADE, blank=True, null=True)
    tipo = models.CharField('Tipo de escala', max_length=10, choices=ESCALAS, default='ESVCN')
    nombre = models.CharField('Nombre dado a la escala', max_length=300, blank=True, default='')

    @property
    def get_ecpvys(self):
        y_values = set(self.escalacpvalor_set.all().values_list('y', flat=True))
        return y_values

    def get_ecpvxs(self, y):
        return self.escalacpvalor_set.filter(y=y)

    def __str__(self):
        return '%s (%s)' % (self.cp, self.get_tipo_display())


class EscalaCPvalor(models.Model):  # Escala utilizada en el CuardernoProf
    ESCALAS = (('ESVCL', 'Escala de valoración cualitativa'), ('ESVCN', 'Escala de valoración cuantitativa'),
               ('LCONT', 'Lista de control'))
    ecp = models.ForeignKey(EscalaCP, on_delete=models.CASCADE)
    x = models.IntegerField('Coordenada X', default=1)
    y = models.IntegerField('Coordenada Y', default=0)
    texto_cualitativo = models.CharField('Texto descripción cualitativa de cumplimiento', max_length=300, blank=True)
    valor = models.FloatField('Valor cuantitativo asociado a la valoración cualitativa', default=0)

    class Meta:
        ordering = ['ecp', 'y', 'x']

    def __str__(self):
        return '%s (%s - %s)' % (self.ecp, self.texto_cualitativo, self.valor)


class CalAlum(models.Model):
    cp = models.ForeignKey(CuadernoProf, on_delete=models.CASCADE, blank=True, null=True)
    alumno = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE)
    cie = models.ForeignKey(CriInstrEval, on_delete=models.CASCADE)
    ecp = models.ForeignKey(EscalaCP, on_delete=models.CASCADE, blank=True, null=True)
    obs = models.TextField('Observaciones a la calificación otorgada', blank=True, default='')

    @property
    def cal(self):
        calificacion = 0
        cavs = self.calalumvalor_set.all()
        n = 0
        for cav in cavs:
            if cav.ecpv.valor > 0:
                n += 1
                calificacion += cav.ecpv.valor
        try:
            return round(calificacion / n, 2)
        except:
            return 0

    def __str__(self):
        return '%s - Alumno: %s - %s (%s)' % (self.ecp, self.alumno.gauser.get_full_name(), self.cie, self.cal)


class CalAlumValor(models.Model):
    ca = models.ForeignKey(CalAlum, on_delete=models.CASCADE)
    ecpv = models.ForeignKey(EscalaCPvalor, on_delete=models.CASCADE, blank=True, null=True)
    obs = models.TextField('Observaciones a la calificación otorgada', blank=True, default='')

    def __str__(self):
        return '%s (%s)' % (self.ca, self.ecpv)


@receiver(post_save, sender=CalAlumValor)
def update_calalumcev(sender, instance, **kwargs):
    alumno = instance.ca.alumno
    cuaderno = instance.ca.cp
    cevps = instance.ca.cie.cevps
    cev = cevps.cev
    calalumce, c = CalAlumCE.objects.get_or_create(cp=cuaderno, alumno=alumno, cep=cevps.cepsec)
    calalumcev, c = CalAlumCEv.objects.get_or_create(calalumce=calalumce, cevp=cevps)
    cas = cuaderno.calalum_set.filter(alumno=alumno, cie__cevps__cev=cev)
    numerador = 0
    denominador = 0
    for ca in cas:
        if ca.cal > 0:
            numerador += ca.cie.peso * ca.cal
            denominador += ca.cie.peso
    try:
        calalumcev.valor = round(numerador / denominador, 2)
    except:
        calalumcev.valor = 0
    calalumcev.save()


class RepoEscalaCP(models.Model):  # Escala utilizada en el CuardernoProf
    ESCALAS = (('ESVCL', 'Escala de valoración cualitativa'), ('ESVCN', 'Escala de valoración cuantitativa'),
               ('LCONT', 'Lista de control'))
    creador = models.ForeignKey(Gauser_extra, on_delete=models.CASCADE, blank=True, null=True)
    tipo = models.CharField('Tipo de escala', max_length=10, choices=ESCALAS, default='ESVCN')
    nombre = models.CharField('Nombre dado a la escala', max_length=300, blank=True, default='')
    identificador = models.CharField('Identificador', max_length=11, default=pass_generator)
    observaciones = models.TextField('Observaciones', blank=True, null=True, default='')

    class Meta:
        ordering = ['creador', 'observaciones', 'nombre']

    @property
    def get_recpvys(self):
        y_values = set(self.repoescalacpvalor_set.all().values_list('y', flat=True))
        return y_values

    def get_recpvxs(self, y):
        return self.repoescalacpvalor_set.filter(y=y)

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.tipo)


class RepoEscalaCPvalor(models.Model):  # Escala utilizada en el CuardernoProf
    ESCALAS = (('ESVCL', 'Escala de valoración cualitativa'), ('ESVCN', 'Escala de valoración cuantitativa'),
               ('LCONT', 'Lista de control'))
    ecp = models.ForeignKey(RepoEscalaCP, on_delete=models.CASCADE)
    x = models.IntegerField('Coordenada X', default=1)
    y = models.IntegerField('Coordenada Y', default=0)
    texto_cualitativo = models.CharField('Texto descripción cualitativa de cumplimiento', max_length=300, blank=True)
    valor = models.FloatField('Valor cuantitativo asociado a la valoración cualitativa', default=0)

    class Meta:
        ordering = ['ecp', 'y', 'x']

    def __str__(self):
        return '%s (%s - %s)' % (self.ecp, self.texto_cualitativo, self.valor)


#############################################################################
########################### OTRAS FUNCIONES  ################################
#############################################################################

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
