# -*- coding: utf-8 -*-
import re
import os
from datetime import datetime
from django.db import models
from django.template import Context, Template
from django.utils.text import slugify
from autenticar.models import Gauser
from entidades.models import Entidad, Ronda, Gauser_extra, Subentidad
from django.utils.timezone import now

from estudios.models import Curso
from gauss.funciones import pass_generator

# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
# def update_fichero(instance, filename):
#     instance.fich_name = filename
#     ext = filename.partition('.'), [2]
#     ahora = datetime.now()
#     fichero = 'fichero_registro_%s.%s' % (ahora.strftime('%Y%m%d%H%M%f'),, ext)
#     return os.path.join("inspeccion_educativa/", str(instance.entidad.code), fichero)
#
#
# class Fichero(models.Model):
#     entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
#     fichero = models.FileField("Fichero con información", upload_to=update_fichero, blank=True)
#     fich_name = models.CharField('Nombre del fichero', max_length=200, blank=True, null=True)
#     content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
#
#     def __str__(self):
#         return u'%s' % (self.fichero)


# Id', 'CODIFICACIÓN', 'NOMBRE DEL INSPECTOR', 'EQUIPO'
# INSPECTORES = (
#     ("1", "PMI", "PILAR MANERO IMAÑA"),
#     ("2", "VSG", "VIRGINIA SABANZA GONZÁLEZ"),
#     ("4", "FAF", "FERNANDO ARNEDO FRANCO"),
#     ("5", "JAG", "JOSÉ ANTONIO GARRIDO RUIZ"),
#     ("6", "TMM", "TOMÁS SAN MIGUEL MORENO"),
#     ("7", "ASM", "ANTONIO SILVÁN DE LA MATA"),
#     ("8", "TSD", "TRINIDAD SÁENZ DOMÍNGUEZ"),
#     ("9", "ARS", "ARACELI ROJAS SÁENZ"),
#     ("11", "PRH", "PILAR RENET HERMOSO DE MENDOZA"),
#     ("12", "JZF", "JAVIER ZORZANO FIEL"),
#     ("13", "FRD", "FULGENCIO REDONDO DOMÍNGUEZ"),
#     ("15", "PCB", "PEDRO CÉSAR CACEO BARRIO"),
#     ("16", "IRS", "JOSÉ IGNACIO RUBIO SANCHO")
# )

INSPECTORES = (
    ("1", "PILAR MANERO IMAÑA"),
    ("2", "VIRGINIA SABANZA GONZÁLEZ"),
    ("4", "FERNANDO ARNEDO FRANCO"),
    ("5", "JOSÉ ANTONIO GARRIDO RUIZ"),
    ("6", "TOMÁS SAN MIGUEL MORENO"),
    ("7", "ANTONIO SILVÁN DE LA MATA"),
    ("8", "TRINIDAD SÁENZ DOMÍNGUEZ"),
    ("9", "ARACELI ROJAS SÁENZ"),
    ("11", "PILAR RENET HERMOSO DE MENDOZA"),
    ("12", "JAVIER ZORZANO FIEL"),
    ("13", "FULGENCIO REDONDO DOMÍNGUEZ"),
    ("15", "PEDRO CÉSAR CACEO BARRIO"),
    ("16", "JOSÉ IGNACIO RUBIO SANCHO")
)

INSPECTORES_GAUSER = {
    "1": "mpmaneroi01",
    "2": "",
    "4": "",
    "5": "jagarridor01",
    "6": "tsanmiguelm01",
    "7": "asilvand01",
    "8": "",
    "9": "arojass01",
    "11": "mpreneth01",
    "12": "",
    "13": "",
    "15": "pccaceob01",
    "16": "",
}

# ID', 'NOMBRE CENTRO', 'TIPO', 'LOCALIDAD'
CENTROS = (
    ("633", "ATENCIÓN INVIDENTES", "O.N.C.E.", "LOGROÑO"),
    ("634", "AULA HOSPITALARIA", "HOSPITAL SAN PEDRO", "LOGROÑO"),
    ("635", "C.E.E. MARQUÉS DE VALLEJO", "E.E.", "LOGROÑO"),
    ("636", "C.E.I.P. ÁNGEL OLIVÁN", "C.E.I.P.", "CALAHORRA"),
    ("637", "C.E.I.P. ANTONIO DELGADO CALVETE ", "C.E.I.P.", "ARNEDO"),
    ("638", "C.E.I.P. AURELIO PRUDENCIO ", "C.E.I.P.", "CALAHORRA"),
    ("639", "C.E.I.P. AVELINA CORTÁZAR", "C.E.I.P.", "ALBERITE"),
    ("640", "C.E.I.P. B. JERÓNIMO HERMOSILLA ", "C.E.I.P.", "SANTO DOMINGO DE LA CALZADA"),
    ("641", "C.E.I.P. BRETÓN DE LOS HERREROS ", "C.E.I.P.", "LOGROÑO"),
    ("642", "C.E.I.P. CABALLERO ROSA", "C.E.I.P.", "LOGROÑO"),
    ("643", "C.E.I.P. CASALARREINA", "C.E.I.P.", "CASALARREINA"),
    ("644", "C.E.I.P. CERVANTES ", "C.E.I.P.", "FUENMAYOR"),
    ("645", "C.E.I.P. DOCTOR CASTROVIEJO ", "C.E.I.P.", "LOGROÑO"),
    ("646", "C.E.I.P. DUQUESA DE LA VICTORIA ", "C.E.I.P.", "LOGROÑO"),
    ("647", "C.E.I.P. EDUARDO GONZÁLEZ GALLARZA (L)", "C.E.I.P.", "LARDERO"),
    ("648", "C.E.I.P. EDUARDO GONZÁLEZ GALLARZA (RS)", "C.E.I.P.", "RINCÓN DE SOTO"),
    ("649", "C.E.I.P. ELADIO DEL CAMPO ÍÑIGUEZ", "C.E.I.P.", "MURILLO DE RÍO LEZA"),
    ("650", "C.E.I.P. ESCULTOR VICENTE OCHOA ", "C.E.I.P.", "LOGROÑO"),
    ("651", "C.E.I.P. LA ESTACIÓN", "C.E.I.P.", "ARNEDO"),
    ("652", "C.E.I.P. GENERAL ESPARTERO ", "C.E.I.P.", "LOGROÑO"),
    ("653", "C.E.I.P. GONZALO DE BERCEO (L)", "C.E.I.P.", "LOGROÑO"),
    ("654", "C.E.I.P. GONZALO DE BERCEO (V)", "C.E.I.P.", "VILLAMEDIANA"),
    ("655", "C.E.I.P. GREGORIA ARTACHO ", "C.E.I.P.", "CENICERO"),
    ("656", "C.E.I.P. JOSÉ ORTEGA VALDERRAMA ", "C.E.I.P.", "PRADEJÓN"),
    ("657", "C.E.I.P. JUAN YAGUE ", "C.E.I.P.", "LOGROÑO"),
    ("658", "C.E.I.P. LA GUINDALERA", "C.E.I.P.", "LOGROÑO"),
    ("659", "C.E.I.P. LAS GAUNAS ", "C.E.I.P.", "LOGROÑO"),
    ("660", "C.E.I.P. MADRE DE DIOS ", "C.E.I.P.", "LOGROÑO"),
    ("661", "C.E.I.P. MIGUEL ÁNGEL SÁINZ", "C.E.I.P.", "ALDEANUEVA DE EBRO"),
    ("662", "C.E.I.P. MILENARIO DE LA LENGUA CASTELLANA ", "C.E.I.P.", "LOGROÑO"),
    ("663", "C.E.I.P. NAVARRETE EL MUDO ", "C.E.I.P.", "LOGROÑO"),
    ("664", "C.E.I.P. NUESTRA SEÑORA DE LA VEGA ", "C.E.I.P.", "HARO"),
    ("665", "C.E.I.P. NUESTRA SEÑORA DEL SAGRARIO ", "C.E.I.P.", "NAVARRETE"),
    ("666", "C.E.I.P. OBISPO BLANCO NÁJERA ", "C.E.I.P.", "LOGROÑO"),
    ("667", "C.E.I.P. OBISPO EZEQUIEL MORENO ", "C.E.I.P.", "ALFARO"),
    ("668", "C.E.I.P. QUINTILIANO ", "C.E.I.P.", "CALAHORRA"),
    ("669", "C.E.I.P. SÁENZ DE TEJADA ", "C.E.I.P.", "QUEL"),
    ("670", "C.E.I.P. SAN FELICES DE BILIBIO ", "C.E.I.P.", "HARO"),
    ("671", "C.E.I.P. SAN FERNANDO ", "C.E.I.P.", "NÁJERA"),
    ("672", "C.E.I.P. SAN FRANCISCO ", "C.E.I.P.", "LOGROÑO"),
    ("673", "C.E.I.P. SAN LORENZO ", "C.E.I.P.", "EZCARAY"),
    ("674", "C.E.I.P. SAN PELAYO ", "C.E.I.P.", "BAÑOS DE RÍO TOBÍA"),
    ("675", "C.E.I.P. SAN PÍO X", "C.E.I.P.", "LOGROÑO"),
    ("676", "C.E.I.P. SAN PRUDENCIO ", "C.E.I.P.", "ALBELDA"),
    ("677", "C.E.I.P. SANCHO III EL MAYOR ", "C.E.I.P.", "NÁJERA"),
    ("678", "C.E.I.P. SIETE INFANTES DE LARA ", "C.E.I.P.", "LOGROÑO"),
    ("679", "C.E.I.P. VARIA ", "C.E.I.P.", "LOGROÑO"),
    ("680", "C.E.I.P. VÉLEZ DE GUEVARA ", "C.E.I.P.", "LOGROÑO"),
    ("682", "C.E.I.P. VUELO MADRID MANILA", "C.E.I.P.", "LOGROÑO"),
    ("683", "C.P.C. PURÍSIMA CONCEPCIÓN - ADORATRICES", "CONCERTADO", "LOGROÑO"),
    ("684", "C.P.C. ALCASTE", "CONCERTADO", "LOGROÑO"),
    ("685", "C.P.C. AMOR MISERICORDIOSO", "CONCERTADO", "ALFARO"),
    ("686", "C.P.C. APOSTÓLICO MENESIANO", "CONCERTADO", "SANTO DOMINGO DE LA CALZADA"),
    ("687", "C.P.C. COMPAÑÍA DE MARÍA", "CONCERTADO", "LOGROÑO"),
    ("689", "C.P.C. DIVINO MAESTRO", "CONCERTADO", "LOGROÑO"),
    ("690", "C.P.C. ESCUELAS PÍAS", "CONCERTADO", "LOGROÑO"),
    ("691", "C.P.C. INMACULADO CORAZÓN DE MARÍA", "CONCERTADO", "LOGROÑO"),
    ("692", "C.P.C. LA INMACULADA (Obra Misionera de Jesús y María)", "CONCERTADO", "LOGROÑO"),
    ("693", "C.P.C. LA MILAGROSA", "CONCERTADO", "CALAHORRA"),
    ("694", "C.P.C. LA PLANILLA", "CONCERTADO", "CALAHORRA"),
    ("695", "C.P.C. LA SALLE – EL PILAR", "CONCERTADO", "ALFARO"),
    ("697", "C.P.C. LOS BOSCOS", "CONCERTADO", "LOGROÑO"),
    ("698", "C.P.C. NTRA. SRA. DE LA PIEDAD", "CONCERTADO", "NÁJERA"),
    ("699", "C.P.C. NTRA. SRA. DEL BUEN CONSEJO", "CONCERTADO", "LOGROÑO"),
    ("701", "C.P.C. PAULA MONTAL", "CONCERTADO", "LOGROÑO"),
    ("702", "C.P.C. REY PASTOR", "CONCERTADO", "LOGROÑO"),
    ("703", "C.P.C. SAGRADO CORAZÓN (Logroño)", "CONCERTADO", "LOGROÑO"),
    ("704", "C.P.C. SAGRADO CORAZÓN (Haro)", "CONCERTADO", "HARO"),
    ("705", "C.P.C. SAGRADO CORAZÓN DE JESÚS (Arnedo)", "CONCERTADO", "ARNEDO"),
    ("706", "C.P.C. SAGRADOS CORAZONES", "CONCERTADO", "SANTO DOMINGO DE LA CALZADA"),
    ("707", "C.P.C. SALESIANOS - SANTO DOMINGO SAVIO", "CONCERTADO", "LOGROÑO"),
    ("708", "C.P.C. SAN AGUSTÍN", "CONCERTADO", "CALAHORRA"),
    ("709", "C.P.C. SAN ANDRÉS", "CONCERTADO", "CALAHORRA"),
    ("710", "C.P.C. SAN JOSÉ", "CONCERTADO", "LOGROÑO"),
    ("711", "C.P.C. SANTA MARÍA (Marianistas)", "CONCERTADO", "LOGROÑO"),
    ("712", "C.P.C. SANTA TERESA", "CONCERTADO", "CALAHORRA"),
    ("713", "C.P.C. LA SALLE-LA ESTRELLA", "CONCERTADO", "SAN ASENSIO"),
    ("714", "C.P.C.E.I. CUENTACUENTOS", "C.P.C.E.I.", "LOGROÑO"),
    ("715", "C.P.C.E.I. ARCO IRIS", "C.P.C.E.I.", "LOGROÑO"),
    ("717", "C.P.C.E.I. CHIQUITINES", "C.P.C.E.I.", "LOGROÑO"),
    ("718", "C.P.C.E.I. CHUPETE", "C.P.C.E.I.", "NAVARRETE"),
    ("719", "C.P.C.E.I. COLORÍN COLORADO", "C.P.C.E.I.", "LOGROÑO"),
    ("720", "C.P.C.E.I. D'ACUARELA", "C.P.C.E.I.", "LOGROÑO"),
    ("722", "C.P.C.E.I. DISNEYLANDIA", "C.P.C.E.I.", "LOGROÑO"),
    ("723", "C.P.C.E.I. EL PARQUE", "C.P.C.E.I.", "LOGROÑO"),
    ("724", "C.P.C.E.I. ENTREVIÑAS-EL PLANO", "C.P.C.E.I.", "LOGROÑO"),
    ("725", "C.P.C.E.I. PEQUELANDIA BABY", "C.P.C.E.I.", "LOGROÑO"),
    ("726", "C.P.C.E.I. LA RANA JUANA", "C.P.C.E.I.", "LOGROÑO"),
    ("727", "C.P.C.E.I. LUNA LUNERA", "C.P.C.E.I.", "LOGROÑO"),
    ("728", "C.P.C.E.I. PEQUELANDIA", "C.P.C.E.I.", "LOGROÑO"),
    ("729", "C.P.C.E.I. PEQUELANDI SCHOOL", "C.P.C.E.I.", "LOGROÑO"),
    ("730", "C.P.C.E.I. POMPITAS", "C.P.C.E.I.", "LOGROÑO"),
    ("731", "C.P.C.E.I. RICURAS SOCIEDAD CIVIL", "C.P.C.E.I.", "LOGROÑO"),
    ("732", "C.P.C.E.I. SANTO DOMINGO SAVIO", "C.P.C.E.I.", "LOGROÑO"),
    ("733", "C.P.C.E.I. SOL Y LUNA I", "C.P.C.E.I.", "LOGROÑO"),
    ("735", "C.R.A. ALHAMA ", "C.R.A.", "CERVERA DEL RÍO ALHAMA"),
    ("736", "C.R.A. CAMEROS NUEVO ", "C.R.A.", "TORRECILLA EN CAMEROS"),
    ("737", "C.R.A. VALLE OJA-TIRÓN", "C.R.A.", "CASTAÑARES DE RIOJA"),
    ("738", "C.R.A. CUENCA DEL NAJERILLA ", "C.R.A.", "URUÑUELA"),
    ("739", "C.R.A. DE ARNEDILLO ", "C.R.A.", "ARNEDILLO"),
    ("740", "C.R.A. VISTA LA HEZ", "C.R.A.", "AUSEJO"),
    ("741", "C.R.A. VALLE DEL LINARES", "C.R.A.", "IGEA"),
    ("742", "C.R.A. ENTREVALLES", "C.R.A.", "BADARÁN"),
    ("743", "C.R.A. ENTREVIÑAS ", "C.R.A.", "SAN VICENTE DE LA SONSIERRA"),
    ("744", "C.R.A. LAS CUATRO VILLAS ", "C.R.A.", "AGONCILLO"),
    ("745", "C.R.A. MONCALVILLO ", "C.R.A.", "NALDA"),
    ("746", "CEPA DE ALFARO", "CEPA", "ALFARO"),
    ("747", "CEPA DE ARNEDO", "CEPA", "ARNEDO"),
    ("748", "CEPA DE NÁJERA", "CEPA", "NÁJERA"),
    ("749", "CEPA PLUS ULTRA", "CEPA", "LOGROÑO"),
    ("750", "CEPA RIOJA ALTA", "CEPA", "SANTO DOMÍNGO"),
    ("751", "CEPA SAN FRANCISCO", "CEPA", "CALAHORRA"),
    ("752", "CONSERVATORIO ELEMENTAL DE MÚSICA (Calahorra)", "CONSERVATORIO DE MÚSICA", "CALAHORRA"),
    ("753", "CONSERVATORIO ELEMENTAL DE MÚSICA (Haro)", "CONSERVATORIO DE MÚSICA", "HARO"),
    ("754", "CONSERVATORIO PROFESIONAL DE MÚSICA (Logroño)", "CONSERVATORIO DE MÚSICA", "LOGROÑO"),
    ("755", "E.I.P.C. EL TRENECITO", "E.I.P.C.", "CENICERO"),
    ("756", "E.I.P.C. MUNICIPAL LA CASA CUNA", "E.I.P.C.", "LOGROÑO"),
    ("757", "E.I.P.C. PIRULETA", "E.I.P.C.", "AGONCILLO"),
    ("758", "E.I.P.C. REINA ESTEFANÍA", "E.I.P.C.", "NÁJERA"),
    ("759", "E.O.E.P. LOGROÑO ESTE", "E.O.E.P.", "LOGROÑO"),
    ("760", "E.O.E.P. LOGROÑO OESTE", "E.O.E.P.", "LOGROÑO"),
    ("761", "E.O.E.P. RIOJA ALTA", "E.O.E.P.", "NÁJERA"),
    ("762", "E.O.E.P. RIOJA BAJA", "E.O.E.P.", "CALAHORRA"),
    ("763", "E.O.I. DE CALAHORRA", "E.O.I.", "CALAHORRA"),
    ("764", "E.O.I. EL FUERO DE LOGROÑO", "E.O.I.", "LOGROÑO"),
    ("765", "EQUIPO DE ATENCIÓN TEMPRANA", "E.A.T.", "LOGROÑO"),
    ("766", "ESCUELA DE ARTE Y SUPERIOR DE DISEÑO", "ESCUELA DE ARTE", "LOGROÑO"),
    ("767", "ESCUELA MUNICIPAL DE MÚSICA", "E.M.", "LOGROÑO"),
    ("768", "ESCUELA MÚSICA DE ALDEANUEVA DE E.", "E.M.", "ALDEANUEVA DE E."),
    ("769", "ESCUELA MÚSICA DE ALFARO", "E.M.", "ALFARO"),
    ("770", "ESCUELA MÚSICA DE ARNEDO", "E.M.", "ARNEDO"),
    ("771", "ESCUELA MÚSICA DE AUTOL", "E.M.", "AUTOL"),
    ("772", "ESCUELA MÚSICA DE CALAHORRA", "E.M.", "CALAHORRA"),
    ("773", "ESCUELA MÚSICA DE HARO", "E.M.", "HARO"),
    ("774", "ESCUELA MÚSICA DE PRADEJÓN", "E.M.", "PRADEJÓN"),
    ("775", "ESCUELA MÚSICA MUSICALIA", "E.M.", "LOGROÑO"),
    ("776", "ESCUELA MÚSICA PICCOLO Y SAXO", "E.M.", "LOGROÑO"),
    ("777", "I.E.S. BATALLA DE CLAVIJO ", "I.E.S.", "LOGROÑO"),
    ("778", "C.I.P.F.P. CAMINO DE SANTIAGO", "C.I.P.F.P.", "SANTO DOMINGO DE LA CALZADA"),
    ("779", "I.E.S. CELSO DÍAZ ", "I.E.S.", "ARNEDO"),
    ("780", "I.E.S. COMERCIO ", "I.E.S.", "LOGROÑO"),
    ("781", "I.E.S. DUQUES DE NÁJERA ", "I.E.S.", "LOGROÑO"),
    ("782", "I.E.S. ESCULTOR DANIEL ", "I.E.S.", "LOGROÑO"),
    ("783", "I.E.S. ESTEBAN MANUEL VILLEGAS ", "I.E.S.", "NÁJERA"),
    ("784", "I.E.S. FRANCISCO TOMÁS Y VALENTE ", "I.E.S.", "FUENMAYOR"),
    ("785", "I.E.S. GONZALO DE BERCEO ", "I.E.S.", "ALFARO"),
    ("786", "I.E.S. HERMANOS D’ELHUYAR ", "I.E.S.", "LOGROÑO"),
    ("787", "I.E.S. INVENTOR COSME GARCÍA ", "I.E.S.", "LOGROÑO"),
    ("788", "I.E.S. LA LABORAL ", "I.E.S.", "LARDERO"),
    ("790", "I.E.S. MARCO FABIO QUINTILIANO ", "I.E.S.", "CALAHORRA"),
    ("792", "I.E.S. PRÁXEDES MATEO SAGASTA ", "I.E.S.", "LOGROÑO"),
    ("793", "I.E.S. REY DON GARCÍA ", "I.E.S.", "NÁJERA"),
    ("794", "I.E.S. TOMÁS MINGOT ", "I.E.S.", "LOGROÑO"),
    ("795", "I.E.S. VALLE DEL CIDACOS ", "I.E.S.", "CALAHORRA"),
    ("796", "I.E.S. VALLE DEL OJA ", "I.E.S.", "SANTO DOMINGO DE LA CALZADA"),
    ("797", "I.E.S. VIRGEN DE VICO ", "I.E.S.", "ARNEDO"),
    ("798", "NINGUNO", "NINGUNO", "NINGUNO"),
    ("800", "SECCIÓN IES DE BAÑOS DE RÍO TOBÍA", "SECCIÓN", "BAÑOS DE R.T."),
    ("801", "SECCIÓN IES DE CERVERA", "SECCIÓN", "CERVERA DEL R. A."),
    ("802", "SECCIÓN IES DE PRADEJÓN", "SECCIÓN", "PRADEJÓN"),
    ("803", "SECCIÓN IES DE RINCÓN DE SOTO", "SECCIÓN", "RINCÓN DE SOTO"),
    ("804", "E.I.P.C. SAN PELAYO", "E.I.P.C.", "SAN VICENTE DE LA SONSIERRA"),
    ("805", "E.I.P.C. EL CUBO", "E.I.P.C.", "LOGROÑO"),
    ("806", "E.I.P.C. EL ARCO", "E.I.P.C.", "LOGROÑO"),
    ("807", "C.P.C.E.I. SAN JOSÉ", "C.P.C.E.I.", "LOGROÑO"),
    ("808", "C.P.C.E.I. LA SALLE-EL PILAR", "C.P.C.E.I.", "ALFARO"),
    ("809", "C.P.C.E.I. DREAMS", "C.P.C.E.I.", "LOGROÑO"),
    ("810", "C.P.C.E.I. PIÑATA", "C.P.C.E.I.", "LOGROÑO"),
    ("811", "C.P.C.E.I. LOS PITUFOS", "C.P.C.E.I.", "LOGROÑO"),
    ("812", "C.P.C.E.I. A GATAS", "C.P.C.E.I.", "LOGROÑO"),
    ("813", "C.P.C.E.I. LA NORIA I", "C.P.C.E.I.", "LOGROÑO"),
    ("814", "C.P.C.E.I. LA NORIA II", "C.P.C.E.I.", "LOGROÑO"),
    ("816", "C.P.C.E.I. OLYMA GARDEN", "C.P.C.E.I.", "LOGROÑO"),
    ("817", "C.P.C.E.I. COLE PETETE", "C.P.C.E.I.", "LOGROÑO"),
    ("818", "C.P.C.E.I. ENTREPUENTES", "C.P.C.E.I.", "LOGROÑO"),
    ("819", "C.E.I.P. VILLA PATRO", "C.E.I.P.", "LARDERO"),
    ("820", "E.O.I. HARO", "E.O.I.", "HARO"),
    ("821", "E.O.I. EXT. SANTO DOMINGO DE LA CALZADA", "E.O.I.", "SANTO DOMÍNGO DE LA CALZADA"),
    ("822", "E.O.I. EXT. NÁJERA", "E.O.I.", "NÁJERA"),
    ("823", "E.O.I. EXT. ARNEDO", "E.O.I.", "ARNEDO"),
    ("824", "E.O.I. EXT. ALFARO", "E.O.I.", "ALFARO"),
    ("825", "C.E.I.P. EL ARCO", "C.E.I.P.", "LOGROÑO"),
    ("827", "C.E.O. VILLA DE AUTOL", "C.E.O.", "AUTOL"),
    ("828", "I.E.S. CIUDAD DE HARO", "I.E.S.", "HARO"),
    ("829", "E.I.P.C. CARRUSEL", "E.I.P.C.", "LOGROÑO"),
    ("830", "E.I.P.C. NUESTRA SRA. DE VICO", "E.I.P.C.", "ARNEDO"),
    ("831", "E.I.P.C. NUESTRA SRA. DEL CARMEN", "E.I.P.C.", "CALAHORRA"),
    ("832", "E.I.P.C. PRÍNCIPE FELIPE", "E.I.P.C.", "RINCÓN DE SOTO"),
    ("833", "E.I.P.C. LA FLORIDA", "E.I.P.C.", "ALFARO"),
    ("834", "E.I.P.C. LAS LUCES", "E.I.P.C.", "HARO"),
    ("835", "E.I.P.C. NTRA. SRA. DEL BUEYO", "E.I.P.C.", "ALBELDA DE IREGUA"),
    ("836", "E.I.P.C. MERCEDES BENITO", "E.I.P.C.", "ALBERITE"),
    ("837", "E.I.P.C. DANIEL ALONSO", "E.I.P.C.", "ALCANADRE"),
    ("838", "E.I.P.C. PELUSÍN", "E.I.P.C.", "AUSEJO"),
    ("839", "E.I.P.C. DINO", "E.I.P.C.", "AUTOL"),
    ("840", "E.I.P.C. SANTOS MÁRTIRES", "E.I.P.C.", "CALAHORRA"),
    ("841", "E.I.P.C. SAN MIGUEL", "E.I.P.C.", "CERVERA DEL RIO ALHAMA"),
    ("842", "E.I.P.C. GLORIA FUERTES", "E.I.P.C.", "FUENMAYOR"),
    ("843", "E.I.P.C. COLETITAS Y CUQUÍN", "E.I.P.C.", "GALILEA"),
    ("844", "E.I.P.C. LOS ALMENDROS", "E.I.P.C.", "LARDERO"),
    ("845", "E.I.P.C. CHISPITA", "E.I.P.C.", "LOGROÑO"),
    ("846", "E.I.P.C. ELADIO DEL CAMPO", "E.I.P.C.", "MURILLO DE RÍO LEZA"),
    ("847", "E.I.P.C. LAS SANTITAS", "E.I.P.C.", "NAVARRETE"),
    ("848", "E.I.P.C. LA ALEGRÍA", "E.I.P.C.", "PRADEJÓN"),
    ("849", "E.I.P.C. VIRGEN DE LA PLAZA", "E.I.P.C.", "SANTO DOMINGO DE LA C."),
    ("850", "E.I.P.C. GONZALO DE BERCEO", "E.I.P.C.", "VILLAMEDIANA DE IREGUA"),
    ("851", "C.P.C.E.I. TROMPÍN S.P.", "C.P.C.E.I.", "LOGROÑO"),
    ("852", "C.P.C.E.I. NTRA. SRA. DEL PILAR", "C.P.C.E.I.", "BAÑOS DE RÍO TOBÍA"),
    ("853", "C.P.C.E.I. ALADÍN S.C.", "C.P.C.E.I.", "NÁJERA"),
    ("854", "C.P.C.E.I. DO RE MI", "C.P.C.E.I.", "LOGROÑO"),
    ("855", "C.P.C.E.I. SOLETES", "C.P.C.E.I.", "LOGROÑO"),
    ("856", "C.P.C.E.I. PIN Y PON", "C.P.C.E.I.", "LOGROÑO"),
    ("857", "C.P.C.E.I. CARAMELO", "C.P.C.E.I.", "LOGROÑO"),
    ("858", "C.P.C.E.I. NANNY'S", "C.P.C.E.I.", "LOGROÑO"),
    ("859", "C.P.C.E.I. LA INMACULADA", "C.P.C.E.I.", "LOGROÑO"),
    ("861", "C.P.E.D. ESCUELAS CENETED", "C.P.E.D.", "LOGROÑO"),
    ("862", "OTROS", "OTROS", "OTROS"),
    ("863", "C.P.F.P. LA PLANILLA", "C.P.F.P.", "CALAHORRA"),
    ("864", "C.P.F.P. SANITARIO CIENCIAS RADIOLÓGICAS", "C.P.F.P.", "LOGROÑO"),
    ("865", "C.E.E. LOS ÁNGELES", "E.E.", "LOGROÑO"),
    ("866", "E.I.P.C. VILLA DE EZCARAY", "E.I.P.C.", "EZCARAY"),
    ("867", "C.P.C.E.I. SANTA MARÍA", "C.P.C.E.I.", "LOGROÑO"),
    ("868", "C.P.C.E.I. LA CASITA DE COCO", "C.P.C.E.I.", "LOGROÑO"),
    ("869", "SECCIÓN IES DE MURILLO DE RÍO LEZA", "SECCIÓN", "MURILLO DE RÍO LEZA"),
    ("870", "SECCIÓN IES DE ALDEANUEVA DE EBRO", "SECCIÓN", "ALDEANUEVA DE EBRO"),
    ("871", "SECCIÓN IES DE EZCARAY", "SECCIÓN", "EZCARAY"),
    ("872", "ESCUELA MÚSICA DE RINCÓN DE SOTO", "E.M.", "RINCÓN DE SOTO"),
    ("873", "C.P.F.P. ESCUELA DEPORTIVA DE LA FEDERACIÓN RIOJANA DE NATACIÓN", "C.P.F.P.", "LOGROÑO"),
)

# ('PARTICIPACIÓN', 'DEFINICIÓN'),
PARTICIPACIONES = (('CC', 'Comité de Calidad'),
                   ('CO', 'Colaboración'),
                   ('EC', 'Equipo Coordinación'),
                   ('IN', 'Individual'),
                   ('IP', 'Inspectores de Primaria'),
                   ('IS', 'Inspectores de Secundaria'),
                   ('LA', 'Logroño-Rioja Alta'),
                   ('LB', 'Logroño-Rioja Baja'),
                   ('LM', 'Logroño-Rioja Media'),
                   ('TT', 'Todos'))

# ('OBJETO', 'DEFINICIÓN'),
OBJETOS = (('C', 'Centro'),
           ('P', 'Profesores'),
           ('A', 'Alumnos/Padres'),
           ('OT', 'Otros'))

# 'TIPO DE ACTUACIÓN', 'DEFINICIÓN'
TIPOS = (
    ('ES', 'Específica'),
    ('HA', 'Habitual'),
    ('IN', 'Incidental'),
    ('PR', 'Prioritaria'))

LOCALIZACIONES = (("CE", "Centro"), ("OT", "Otros"), ("SE", "Sede"))

# "FUNCIÓN INSPECTORA","DEFINICIÓN"),
FUNCIONES = (
    ("AR", "Arbitraje/Mediación"),
    ("AS", "Asesoramiento/Información"),
    ("CM", "Comisiones/Tribunales"),
    ("CT", "Control"),
    ("EV", "Evaluación"),
    ("OT", "Otras"),
)

ACTUACIONES = (
    ("CO", "Comisiones/Tribunales"),
    ("DO", "Documentación"),
    ("ES", "Estudio"),
    ("EX", "Expediente discipinario"),
    ("FI", "Formación impartida"),
    ("FR", "Formación recibida"),
    ("IN", "Informe"),
    ("OT", "Otras"),
    ("RE", "Reunión"),
    ("RV", "Recepción visitas"),
    ("TF", "Teléfono/Correo Electrónico"),
    ("VID", "Visado"),
)

NIVELES = (
    ("EI", "Infantil"),
    ("PR", "Primaria"),
    ("PS", "Primaria y Secundaria"),
    ("SE", "Secundaria"),
)

SECTORES = (
    ("LA", "Logroño-Rioja Alta"),
    ("LB", "Logroño-Rioja Baja"),
    ("LM", "Logroño-Rioja Media"),
)


# ("742", "C.R.A. ENTREVALLES", "C.R.A.", "BADARÁN")
class CentroMDB(models.Model):
    code = models.CharField("Código La Rioja", max_length=10, null=True, blank=True)
    code_mdb = models.CharField("Código MDB", max_length=10, null=True, blank=True)
    tipo = models.CharField("Tipo MDB", max_length=30, null=True, blank=True)
    nombre = models.CharField("Nombre MDB", max_length=210, null=True, blank=True)
    localidad = models.CharField("Localidad MDB", max_length=30, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Centros MDB'

    def __str__(self):
        return '%s (%s) - %s - %s' % (self.nombre, self.code, self.code_mdb, self.localidad)


rel_code_MDB = (
    (26002849, '635'),
    (26002977, '636'),
    (26000257, '637'),
    (26000464, '638'),
    (26002199, '640'),
    (26001213, '641'),
    (26002795, '642'),
    (26007999, '643'),
    (26000919, '644'),
    (26001791, '649'),
    (26002761, '645'),
    (26000087, '639'),
    (26002850, '646'),
    (26001122, '647'),
    (26002096, '648'),
    (26008177, '825'),
    (26003064, '650'),
    (26002990, '652'),
    (26001237, '653'),
    (26002473, '654'),
    (26000661, '655'),
    (26002023, '656'),
    (26001262, '657'),
    (26002898, '651'),
    (26008001, '658'),
    (26003210, '659'),
    (26001626, '660'),
    (26000105, '661'),
    (26002734, '662'),
    (26001249, '663'),
    (26002588, '664'),
    (26001894, '665'),
    (26002771, '666'),
    (26000130, '667'),
    (26002989, '668'),
    (26007771, '669'),
    (26000971, '670'),
    (26001811, '671'),
    (26003052, '672'),
    (26003532, '673'),
    (26000373, '674'),
    (26001250, '675'),
    (26000063, '676'),
    (26002825, '677'),
    (26007781, '678'),
    (26001717, '679'),
    (26003003, '680'),
    (26008189, '819'),
    (26001201, '682'),
    (26003076, '752'),
    (26003520, '753'),
    (26008499, '827'),
    (26003571, '746'),
    (26003568, '747'),
    (26003684, '748'),
    (26002941, '749'),
    (26003556, '750'),
    (26003301, '751'),
    (26008207, '778'),
    (26008864, ''),
    (26008827, ''),
    (26008748, ''),
    (26008840, ''),
    (26008803, '873'),
    (26008700, '861'),
    (26008153, ''),
    (26001377, '865'),
    (26008268, '812'),
    (26008441, '853'),
    (26008104, '715'),
    (26002886, ''),
    (26008347, '857'),
    (26007938, '717'),
    (26008086, '718'),
    (26008293, ''),
    (26008311, '817'),
    (26008128, '719'),
    (26008712, ''),
    (26008025, '714'),
    (26008098, '720'),
    (26007926, ''),
    (26008062, '722'),
    (26008451, '854'),
    (26008165, '809'),
    (26007872, '723'),
    (26008323, '818'),
    (26007823, '724'),
    (26008761, '868'),
    (26001501, '859'),
    (26008271, '813'),
    (26008281, '814'),
    (26007975, '726'),
    (26008049, ''),
    (26008256, '811'),
    (26008074, '727'),
    (26008359, '858'),
    (26008505, '852'),
    (26008301, '816'),
    (26007811, '728'),
    (26007941, '729'),
    (26008372, '856'),
    (26008220, '810'),
    (26008013, '730'),
    (26007987, '731'),
    (26007963, '733'),
    (26008530, '855'),
    (26008517, '851'),
    (26000506, '693'),
    (26002205, '706'),
    (26000476, '709'),
    (26002953, '684'),
    (26000154, '685'),
    (26001444, '687'),
    (26001341, '689'),
    (26001420, '690'),
    (26001456, '691'),
    (26003040, '695'),
    (26001328, '697'),
    (26001821, '698'),
    (26001468, '699'),
    (26001331, '701'),
    (26001471, '683'),
    (26001353, '702'),
    (26001419, '703'),
    (26000993, '704'),
    (26000269, '705'),
    (26001481, '707'),
    (26000592, '708'),
    (26001432, '710'),
    (26001584, '711'),
    (26000488, '712'),
    (26002138, '713'),
    (26002692, '686'),
    (26008815, ''),
    (26008839, ''),
    (26008529, '864'),
    (26000555, '863'),
    (26008116, ''),
    (26002928, '754'),
    (26003428, '735'),
    (26007768, '739'),
    (26003386, '736'),
    (26003398, '738'),
    (26003477, '742'),
    (26003374, '743'),
    (26007744, '744'),
    (26003465, '745'),
    (26003416, '741'),
    (26003490, '737'),
    (26007756, '740'),
    (26008414, '829'),
    (26008384, '833'),
    (26008426, '834'),
    (26008396, '830'),
    (26008402, '831'),
    (26008438, '832'),
    (26008633, '845'),
    (26008611, '843'),
    (26008566, '837'),
    (26008581, '839'),
    (26008244, '806'),
    (26008232, '805'),
    (26008141, '755'),
    (26008645, '846'),
    (26008608, '842'),
    (26008682, '850'),
    (26008669, '848'),
    (26008657, '847'),
    (26008621, '844'),
    (26008554, '836'),
    (26008050, '756'),
    (26008542, '835'),
    (26008578, '838'),
    (26008131, '757'),
    (26008037, '758'),
    (26008694, '841'),
    (26008190, '804'),
    (26008591, '840'),
    (26008736, '866'),
    (26008670, '849'),
    (26007793, '770'),
    (26007902, '768'),
    (26007896, '774'),
    (26007847, '773'),
    (26007859, '772'),
    (26007884, '771'),
    (26007801, '769'),
    (26007860, '767'),
    (26008751, '872'),
    (26003091, '764'),
    (26003313, '763'),
    (26008724, '820'),
    (26007835, '775'),
    (26003611, '776'),
    (26008219, '766'),
    (26003441, '777'),
    (26000270, '779'),
    (26008475, '828'),
    (26001638, '780'),
    (26003088, '781'),
    (26002862, '782'),
    (26001845, '783'),
    (26003581, '784'),
    (26003507, '785'),
    (26001559, '786'),
    (26001596, '787'),
    (26001134, '788'),
    (26000579, '790'),
    (26001560, '792'),
    (26002710, '793'),
    (26003209, '794'),
    (26000543, '795'),
    (26002230, '796'),
    (26000282, '797'),
    (26008785, '870'),
    (26003660, '800'),
    (26003635, '801'),
    (26008797, '871'),
    (26008773, '869'),
    (26003647, '802'),
    (26003659, '803'),
)


class TareaInspeccion(models.Model):
    # entidad_inspectora = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE, related_name="entidades_inspectoras")
    # centro_educativo  = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    creador = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    ronda_centro = models.ForeignKey(Ronda, blank=True, null=True, on_delete=models.CASCADE)
    fecha = models.DateField("Fecha de realización", blank=True, null=True)
    sector = models.CharField("Sector", max_length=10, choices=SECTORES, blank=True)
    localizacion = models.CharField("Localización", max_length=10, choices=LOCALIZACIONES, blank=True)
    nivel = models.CharField("Nivel educativo", max_length=10, choices=NIVELES, blank=True)
    actuacion = models.CharField("Actuación", max_length=10, choices=ACTUACIONES, blank=True)
    objeto = models.CharField("Objeto", max_length=10, choices=OBJETOS, blank=True)
    asunto = models.CharField("Asunto/Tema", max_length=310, blank=True)
    tipo = models.CharField("Tipo de actuación", max_length=10, choices=TIPOS, blank=True)
    funcion = models.CharField("Tipo de función", max_length=10, choices=FUNCIONES, blank=True)
    participacion = models.CharField("Participación", max_length=10, choices=PARTICIPACIONES, blank=True)
    colaboracion = models.CharField("Especifica colaboración", max_length=300, blank=True)
    observaciones = models.TextField("Notas aclaratorias/Observaciones", blank=True, null=True)
    centro_mdb = models.ForeignKey(CentroMDB, null=True, blank=True, on_delete=models.CASCADE)
    centro = models.ForeignKey(Entidad, null=True, blank=True, on_delete=models.SET_NULL)
    inspector_mdb = models.CharField("Inspector MDB", max_length=10, choices=INSPECTORES, blank=True)
    realizada = models.BooleanField("¿Está realizada?", default=False)
    clave_ex = models.IntegerField("Id de la MDB para identificar tarea", default=0)

    def permiso(self, gauser):
        return ''.join(list(self.inspectortarea_set.filter(inspector__gauser=gauser).values_list('permiso', flat=True)))

    class Meta:
        verbose_name_plural = 'Actuaciones de Inspección'

    def __str__(self):
        return '%s - %s - %s' % (self.fecha, self.ronda_centro, self.asunto)


ROLES = (('1', 'Encargado'), ('2', 'Acompañante'), ('3', 'Colaborador'), ('4', 'Presidente'),
         ('5', 'Secretario'), ('6', 'Vocal'),)
PERMISOS = (('r', 'Lectura'),
            ('rw', 'Lectura y escritura'),
            ('rwx', 'Lectura, escritura y borrado'),)


class InspectorTarea(models.Model):
    inspector = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    tarea = models.ForeignKey(TareaInspeccion, blank=True, null=True, on_delete=models.CASCADE)
    rol = models.CharField("Rol del inspector", max_length=10, choices=ROLES, blank=True)
    permiso = models.CharField('Permisos sobre la tarea', max_length=15, choices=PERMISOS, default='r')

    class Meta:
        ordering = ['-tarea__fecha']
        verbose_name_plural = 'Inspectores asociados con Tareas/Actuaciones'

    def __str__(self):
        return '%s - %s - %s' % (self.permiso, self.inspector, self.tarea)


class PlantillaInformeInspeccion(models.Model):
    creador = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.SET_NULL)
    asunto = models.CharField('Nombre del asunto', blank=True, null=True, default='', max_length=300)
    destinatario = models.TextField('Destinatario del informe', blank=True, null=True, default='')
    modificado = models.DateField("Fecha de modificación", auto_now=True)

    class Meta:
        verbose_name_plural = 'Plantillas de Informes de Inspección'
        ordering = ['-modificado']

    def __str__(self):
        return '%s - %s' % (self.asunto, self.creador)


class VariantePII(models.Model):
    plantilla = models.ForeignKey(PlantillaInformeInspeccion, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre de la variante del informe', blank=True, null=True, default='', max_length=300)
    texto = models.TextField('Contenido del informe', blank=True, null=True, default='')

    class Meta:
        ordering = ['plantilla__id', 'id', ]
        verbose_name_plural = 'Modelos pertenecientes a plantillas de informes'

    def __str__(self):
        return '%s - %s' % (self.plantilla, self.nombre)


class InformeInspeccion(models.Model):
    inspector = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.SET_NULL)
    variante = models.ForeignKey(VariantePII, blank=True, null=True, on_delete=models.SET_NULL)
    title = models.CharField('Nombre de la variable', blank=True, null=True, default='', max_length=300)
    destinatario = models.TextField('Destinatario del informe', blank=True, null=True, default='')
    asunto = models.CharField('Nombre del asunto', blank=True, null=True, default='', max_length=300)
    texto = models.TextField('Contenido del informe', blank=True, null=True, default='')
    modificado = models.DateField("Fecha de modificación", auto_now=True)
    creado = models.DateField("Fecha de creación", default=now)

    @property
    def texto_procesado(self):
        template = Template(self.texto)
        # d = {v.nombre: v.valor for v in self.variableii_set.all()}
        # context = Context(d)
        # return template.render(context)
        return template.render(Context({v.nombre: v.valor for v in self.variableii_set.all()}))

    @property
    def get_variables(self):
        nombres = [n.strip() for n in re.findall(r'{{(.*?)}}', self.texto)]
        for nombre in nombres:
            VariableII.objects.get_or_create(informe=self, nombre=nombre)
        for variable in self.variableii_set.all():
            if variable.nombre not in nombres:
                variable.delete()
        return self.variableii_set.all()

    class Meta:
        verbose_name_plural = 'Informes de Inspección'
        ordering = ['-modificado', '-id']

    def __str__(self):
        return '%s - %s' % (self.inspector, self.asunto)


class VariableII(models.Model):
    informe = models.ForeignKey(InformeInspeccion, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre de la variable', blank=True, null=True, default='', max_length=50)
    valor = models.CharField('Valor de la variable', blank=True, null=True, default='', max_length=150)

    class Meta:
        verbose_name_plural = 'Variables asociadas a un informe'

    def __str__(self):
        return '%s - %s - %s' % (self.informe, self.nombre, self.valor)


class FirmaII(models.Model):
    FV = (('F', 'Firmado'), ('V', 'Visto Bueno'))
    informe = models.ForeignKey(InformeInspeccion, on_delete=models.CASCADE)
    firmante = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.SET_NULL)
    tipo = models.CharField('Tipo de firma', default='F', choices=FV, max_length=5)
    cargo = models.CharField('Cargo del firmante', blank=True, null=True, max_length=150)
    nombre = models.CharField('Nombre del firmante', blank=True, null=True, max_length=150)
    visible = models.BooleanField('Firma visible?', default=False)


# class IIVariable(models.Model):
#     informe = models.ForeignKey(PlantillaInformeInspeccion, on_delete=models.CASCADE)
#     nombre=models.CharField('Nombre de la variable', blank=True, null=True, default='', max_length=300)
#     valor = models.CharField('Valor de la variable', blank=True, null=True, default='', max_length=300)

def update_fichero(instance, filename):
    nombre, dot, ext = filename.rpartition('.')
    instance.fich_name = filename
    fichero = pass_generator(size=20) + '.' + ext
    return '/'.join(['inspeccion', str(instance.informe.inspector.ronda.entidad.code), fichero])


class FileAttachedII(models.Model):
    informe = models.ForeignKey(InformeInspeccion, on_delete=models.CASCADE)
    fichero = models.FileField("Fichero adjunto a informe de inspección", upload_to=update_fichero, blank=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Ficheros adjuntos a informes de inspección"

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def __str__(self):
        return '%s (%s)' % (self.fichero, self.informe)


#######################################################################################
#######################################################################################


def code_grupo():
    return pass_generator(10)


def get_grupos_cis(ronda):  # get grupos de centros inspeccionados
    centros = CentroInspeccionado.objects.filter(ronda=ronda)
    grupos = {g: [] for g in centros.values_list('grupo', flat=True).distinct()}
    for c in centros:
        grupos[c.grupo].append(c)
    return grupos


class CentroInspeccionado(models.Model):
    TIPOS = (('PU', 'Público'), ('PR', 'Privado'))
    ETAPAS = (('INF', 'Infantil'), ('PRI', 'Primaria'), ('SEC', 'Secundaria'), ('IP', 'Infantil y Primaria'),
              ('IPS', 'Infantil, Primaria y Secundaria'), ('PS', 'Primaria y Secundaria'))
    CL = (('A', 'Tipo A'), ('B', 'Tipo B'), ('C', 'Tipo C'), ('D', 'Tipo D'), ('E', 'Tipo E'))
    ZONAS = (('RB', 'Logroño - Rioja Baja'), ('RM', 'Logroño - Rioja Media'), ('RA', 'Logroño - Rioja Alta'))
    PUNTOS = ((1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12))
    centro = models.OneToOneField(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    ronda = models.ForeignKey(Ronda, on_delete=models.CASCADE)  # Ronda de la entidad inspectora
    tipo = models.CharField('Tipo de centro', max_length=5, choices=TIPOS, blank=True, null=True, default='PU')
    zona = models.ForeignKey(Subentidad, blank=True, null=True, on_delete=models.SET_NULL)
    zonai = models.CharField('Zona de inspección', max_length=5, choices=ZONAS, default='RM')
    etapas = models.CharField('Etapas en el centro', max_length=5, choices=ETAPAS, blank=True, null=True, default='IP')
    clasificado = models.CharField('Clasificación', max_length=5, choices=CL, blank=True, null=True, default='C')
    puntos = models.IntegerField('Puntos asignados', default=1)
    grupo = models.CharField('Grupo de centros al que pertenece', max_length=12, default=code_grupo)
    inspector = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name_plural = 'Centros Inspeccionados'
        ordering = ['id']

    def centros_grupo(self):
        return CentroInspeccionado.objects.filter(grupo=self.grupo)

    def s_centros_grupo(self):
        cs = self.centros_grupo().values_list('centro__name', flat=True)
        return ', '.join(cs)

    def __str__(self):
        return '%s (%s)' % (self.centro, self.inspector)


#######################################################################################
#######################################################################################

def update_acta(instance, filename):
    nombre, dot, ext = filename.rpartition('.')
    fichero = slugify(instance.curso.nombre) + '.' + ext
    instance.fich_name = fichero
    code = str(instance.ronda.entidad.code)
    ronda = slugify(instance.ronda.nombre)
    return '/'.join(['inspeccion', 'actas', code, ronda, fichero])

class ActaCursoFirmada(models.Model):
    TIPOS = (('ORD', 'Ordinaria'), ('EXT', 'Extraordinaria'),('OFP1', 'Ordinaria junio 1 (FP)'),
             ('OFP2', 'Ordinaria junio 2 (FP)'), ('OFPE', 'Ordinaria enero (FP)'))
    subido_por = models.ForeignKey(Gauser, on_delete=models.SET_NULL, blank=True, null=True)
    ronda = models.ForeignKey(Ronda, on_delete=models.SET_NULL, blank=True, null=True) #Ronda del centro que sube acta
    curso = models.ForeignKey(Curso, on_delete=models.SET_NULL, blank=True, null=True)
    convocatoria = models.CharField('Tipo de convocatoria', max_length=5, choices=TIPOS, default='ORD')
    acta = models.FileField("Fichero escaneado del acta firmada", upload_to=update_acta, blank=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)
    creado = models.DateField("Fecha de creación", default=now)

    class Meta:
        verbose_name_plural = 'Actas de evaluación firmadas'
        ordering = ['id']

    def __str__(self):
        return '%s (%s) - %s' % (self.ronda, self.get_convocatoria_display(), self.fich_name)