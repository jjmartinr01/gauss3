# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
from django.db import models

# Tipos de IBAN. "p" es País, "c2" es secuencia de 2 caracteres de inicio, "sepa" es si tienen sistema SEPA o no,
# "l" longitud del IBAN, "e" es un ejemplo de IBAN en ese país
tipos_iban = [{"p": "Albania", "c2": "AL", "sepa": False, "l": 28, "e": "AL35202111090000000001234567"},
              {"p": "Andorra", "c2": "AD", "sepa": False, "l": 24, "e": "AD1400080001001234567890"},
              {"p": "Azerbaiyán", "c2": "AZ", "sepa": False, "l": 28, "e": "AZ96AZEJ00000000001234567890"},
              {"p": "Bahrein", "c2": "BH", "sepa": False, "l": 22, "e": "BH02CITI00001077181611"},
              {"p": "Bélgica", "c2": "BE", "sepa": True, "l": 16, "e": "BE71096123456769"},
              {"p": "Bosnia y Herzegovina", "c2": "BA", "sepa": False, "l": 20, "e": "BA275680000123456789"},
              {"p": "Brasil", "c2": "BR", "sepa": False, "l": 29, "e": "BR1500000000000010932840814P2"},
              {"p": "Islas Vírgenes Británicas", "c2": "VG", "sepa": False, "l": 24, "e": "VG21PACG0000000123456789"},
              {"p": "Bulgaria", "c2": "BG", "sepa": True, "l": 22, "e": "BG18RZBB91550123456789"},
              {"p": "Costa Rica", "c2": "CR", "sepa": False, "l": 22, "e": "CR37012600000123456789"},
              {"p": "Dinamarca", "c2": "DK", "sepa": True, "l": 18, "e": "DK9520000123456789"},
              {"p": "Alemania", "c2": "DE", "sepa": True, "l": 22, "e": "DE91100000000123456789"},
              {"p": "República Dominicana", "c2": "DO", "sepa": False, "l": 28, "e": "DO22ACAU00000000000123456789"},
              {"p": "El Salvador", "c2": "SV", "sepa": False, "l": 28, "e": "SV43ACAT00000000000000123123"},
              {"p": "Estonia", "c2": "EE", "sepa": True, "l": 20, "e": "EE471000001020145685"},
              {"p": "Islas Feroe", "c2": "FO", "sepa": True, "l": 18, "e": "FO9264600123456789"},
              {"p": "Finlandia", "c2": "FI", "sepa": True, "l": 18, "e": "FI1410093000123458"},
              {"p": "Francia", "c2": "FR", "sepa": True, "l": 27, "e": "FR7630006000011234567890189"},
              {"p": "Georgia", "c2": "GE", "sepa": False, "l": 22, "e": "GE60NB0000000123456789"},
              {"p": "Gibraltar", "c2": "GI", "sepa": True, "l": 23, "e": "GI04BARC000001234567890"},
              {"p": "Grecia", "c2": "GR", "sepa": True, "l": 27, "e": "GR9608100010000001234567890"},
              {"p": "Groenlandia", "c2": "GL", "sepa": True, "l": 18, "e": "GL8964710123456789"},
              {"p": "Gran Bretaña", "c2": "GB", "sepa": True, "l": 22, "e": "GB98MIDL07009312345678"},
              {"p": "Guatemala", "c2": "GT", "sepa": False, "l": 28, "e": "GT20AGRO00000000001234567890"},
              {"p": "Irak", "c2": "IQ", "sepa": False, "l": 23, "e": "IQ20CBIQ861800101010500"},
              {"p": "Irlanda", "c2": "IE", "sepa": True, "l": 22, "e": "IE64IRCE92050112345678"},
              {"p": "Islandia", "c2": "IS", "sepa": True, "l": 26, "e": "IS030001121234561234567890"},
              {"p": "Israel", "c2": "IL", "sepa": False, "l": 23, "e": "IL170108000000012612345"},
              {"p": "Italia", "c2": "IT", "sepa": True, "l": 27, "e": "IT60X0542811101000000123456"},
              {"p": "Jordania", "c2": "JO", "sepa": False, "l": 30, "e": "JO71CBJO0000000000001234567890"},
              {"p": "Kazajstán", "c2": "KZ", "sepa": False, "l": 20, "e": "KZ563190000012344567"},
              {"p": "Katar", "c2": "QA", "sepa": False, "l": 29, "e": "QA54QNBA000000000000693123456"},
              {"p": "Kosovo", "c2": "XK", "sepa": False, "l": 20, "e": "XK051212012345678906"},
              {"p": "Croacia", "c2": "HR", "sepa": True, "l": 21, "e": "HR1723600001101234565"},
              {"p": "Kuwait", "c2": "KW", "sepa": False, "l": 30, "e": "KW81CBKU0000000000001234560101"},
              {"p": "Letonia", "c2": "LV", "sepa": True, "l": 21, "e": "LV97HABA0012345678910"},
              {"p": "Líbano", "c2": "LB", "sepa": False, "l": 28, "e": "LB92000700000000123123456123"},
              {"p": "Liechtenstein", "c2": "LI", "sepa": True, "l": 21, "e": "LI7408806123456789012"},
              {"p": "Lituania", "c2": "LT", "sepa": True, "l": 20, "e": "LT601010012345678901"},
              {"p": "Luxemburgo", "c2": "LU", "sepa": True, "l": 20, "e": "LU120010001234567891"},
              {"p": "Malta", "c2": "MT", "sepa": True, "l": 31, "e": "MT31MALT01100000000000000000123"},
              {"p": "Mauritania", "c2": "MR", "sepa": False, "l": 27, "e": "MR1300020001010000123456753"},
              {"p": "Mauricio", "c2": "MU", "sepa": False, "l": 30, "e": "MU43BOMM0101123456789101000MUR"},
              {"p": "macedonia", "c2": "MK", "sepa": False, "l": 19, "e": "MK07200002785123453"},
              {"p": "Moldavia", "c2": "MD", "sepa": False, "l": 24, "e": "MD21EX000000000001234567"},
              {"p": "Mónaco", "c2": "MC", "sepa": True, "l": 27, "e": "MC5810096180790123456789085"},
              {"p": "Montenegro", "c2": "ME", "sepa": False, "l": 22, "e": "ME25505000012345678951"},
              {"p": "Países Bajos", "c2": "NL", "sepa": True, "l": 18, "e": "NL02ABNA0123456789"},
              {"p": "Noruega", "c2": "NO", "sepa": True, "l": 15, "e": "NO8330001234567"},
              {"p": "Austria", "c2": "AT", "sepa": True, "l": 20, "e": "AT483200000012345864"},
              {"p": "Pakistán", "c2": "PK", "sepa": False, "l": 24, "e": "PK36SCBL0000001123456702"},
              {"p": "Palestina", "c2": "PS", "sepa": False, "l": 29, "e": "PS92PALS000000000400123456702"},
              {"p": "Polonia", "c2": "PL", "sepa": True, "l": 28, "e": "PL10105000997603123456789123"},
              {"p": "Portugal", "c2": "PT", "sepa": True, "l": 25, "e": "PT50002700000001234567833"},
              {"p": "Rumania", "c2": "RO", "sepa": True, "l": 24, "e": "RO09BCYP0000001234567890"},
              {"p": "Santa Lucía", "c2": "LC", "sepa": False, "l": 32, "e": "LC14BOSL123456789012345678901234"},
              {"p": "San Marino", "c2": "SM", "sepa": True, "l": 27, "e": "SM76P0854009812123456789123"},
              {"p": "Santo Tomé y Príncipe", "c2": "ST", "sepa": False, "l": 25, "e": "ST23000200000289355710148"},
              {"p": "Arabia Saudita", "c2": "SA", "sepa": False, "l": 24, "e": "SA4420000001234567891234"},
              {"p": "Suecia", "c2": "SE", "sepa": True, "l": 24, "e": "SE1412345678901234567890"},
              {"p": "Suiza", "c2": "CH", "sepa": True, "l": 21, "e": "CH5604835012345678009"},
              {"p": "Serbia", "c2": "RS", "sepa": False, "l": 22, "e": "RS35105008123123123173"},
              {"p": "Seychelles", "c2": "SC", "sepa": False, "l": 31, "e": "SC52BAHL01031234567890123456USD"},
              {"p": "República Eslovaca", "c2": "SK", "sepa": True, "l": 24, "e": "SK8975000000000012345671"},
              {"p": "Eslovenia", "c2": "SI", "sepa": True, "l": 19, "e": "SI56192001234567892"},
              {"p": "España", "c2": "ES", "sepa": True, "l": 24, "e": "ES1000492352082414205416"},
              {"p": "Timor Oriental", "c2": "TL", "sepa": False, "l": 23, "e": "TL380080012345678910157"},
              {"p": "Turquía", "c2": "TR", "sepa": False, "l": 26, "e": "TR320010009999901234567890"},
              {"p": "Chequia", "c2": "CZ", "sepa": True, "l": 24, "e": "CZ5508000000001234567899"},
              {"p": "Túnez", "c2": "TN", "sepa": False, "l": 24, "e": "TN4401000067123456789123"},
              {"p": "Ucrania", "c2": "UA", "sepa": False, "l": 29, "e": "UA903052992990004149123456789"},
              {"p": "Hungría", "c2": "HU", "sepa": True, "l": 28, "e": "HU93116000060000000012345676"},
              {"p": "Emiratos Árabes Unidos", "c2": "AE", "sepa": False, "l": 23, "e": "AE460090000000123456789"},
              {"p": "Belarús", "c2": "BY", "sepa": False, "l": 28, "e": "BY86AKBB10100000002966000000"},
              {"p": "Chipre", "c2": "CY", "sepa": True, "l": 28, "e": "CY21002001950000357001234567"}]


def get_banco(cuenta_bancaria):
    # Eliminar todos los símbolos que no sean números o letras de la cuenta_bancaria
    num_cuenta_bancaria = re.sub("[^0-9a-zA-Z]", "", str(cuenta_bancaria))
    # La cuenta bancaria puede ser el iban (24 caracteres) o la cuenta bancaria tradicional (20 dígitos) en España
    # Comprobamos si la cuenta bancaria comienza por dos letras. Esto indicaría que es un IBAN
    if re.findall('^[a-zA-Z]{2}', num_cuenta_bancaria):
        if num_cuenta_bancaria[0:2].upper() == 'ES':
            banco_code = num_cuenta_bancaria[4:8]
        else:
            # 'Es un IBAN extranjero'
            return Banco.objects.none()
    elif len(num_cuenta_bancaria) == 20:
        banco_code = num_cuenta_bancaria[0:4]
    else:
        # 'No se puede identificar el tipo de cuenta bancaria'
        return Banco.objects.none()
    # A continuación comprobamos si el banco_code coincide con alguno de los bancos o cajas ya desaparecidas y lo
    # hacemos corresponder con el banco que actualmente se asocia a ese código:
    if banco_code == '2097':
        return Banco.objects.get(codigo='2095')  # 2097 era Vital kutxa, le asignamos bankia que es el 2095 kutxabank
    elif banco_code == '2037':
        return Banco.objects.get(codigo='2038')  # 2037 era cajarioja, le asignamos bankia que es el 2038
    elif banco_code == '2054' or banco_code == '0142':
        return Banco.objects.get(codigo='2100')  # 0142 banco pequeña empresa, 2054 era la CAN, ahora Caixabank el 2100
    elif banco_code == '2096' or banco_code == '0208':
        return Banco.objects.get(codigo='2108')  # 2096 era la caja duero, ahora Banco inversiones que es el 2108
    elif banco_code == '3021':
        return Banco.objects.get(codigo='3191')  # de cajalon a nueva caja rural de aragón
    elif banco_code == '0030':
        return Banco.objects.get(codigo='0049')  # banco español de crédito a banco santander
    elif banco_code == '0104':
        return Banco.objects.get(codigo='0182')  # argentaria a bbva
    elif banco_code == '0008':
        return Banco.objects.get(codigo='0081')  # argentaria a bbva
    else: # Si no es ninguno de los anteriores, estará registrado en GAUSS por su código
        return Banco.objects.get(codigo=banco_code)

class Banco(models.Model):
    nombre = models.CharField("Nombre del banco", max_length=350, null=True, blank=True)
    nif = models.CharField("NIF", max_length=25, null=True, blank=True)
    codigo = models.CharField("Código de cuatro dígitos", max_length=10, null=True, blank=True)
    tipo = models.CharField("Tipo de entidad bancaria", max_length=100, null=True, blank=True)
    bic = models.CharField("BIC/SWIFT", max_length=15, null=True, blank=True)
    address = models.CharField("Dirección", max_length=250, null=True, blank=True)
    cp = models.CharField("Código postal", max_length=15, null=True, blank=True)
    pais = models.CharField("País", max_length=150, null=True, blank=True)
    tel = models.CharField("Teléfono", max_length=15, null=True, blank=True)
    fax = models.CharField("Fax", max_length=15, null=True, blank=True)
    web = models.CharField("Página web", max_length=50, null=True, blank=True)

    def __str__(self):
        return '%s (%s)' % (self.nombre, self.nif)
