# -*- coding: utf-8 -*-
import logging
import csv
import re
# import operator
# import os
from bancos.models import Banco

logger = logging.getLogger('django')

# https://www.bde.es/webbde/es/estadis/ifm/if_es.html
# https://www.iban.es/codigos-bic.html
# https://www.iban.es/bic/espana.html



def crea_bancos(request):
    # csv_file  = open('/home/juanjo/django/gauss_scout/bancos_bic.csv', "rb")
    # fichero = csv.reader(csv_file, delimiter=';')
    # banco_bics = {}
    # for row in fichero:
    # fila = []
    # for col in row:
    # fila.append(unicode(col,'utf-8'))
    # banco_bics[fila[2]] = fila[0]
    # csv_file.close()

    csv_file = open('/home/juanjo/django/gauss_asocia/bancos_nuevo.csv', "rb")
    fichero = csv.reader(csv_file, delimiter=';')
    # Iniciamos un forloop para recorrer todas las filas del archivo (no la primera que contiene nombre de los campos)
    for row in fichero:
        fila = []
        for col in row:
            fila.append(unicode(col, 'utf-8'))
        web = fila[10] if fila[10] else ' '
        bic = fila[4] if fila[4] else ' '
        tel = fila[8] if fila[8] else ' '
        fax = fila[9] if fila[9] else ' '
        try:
            Banco.objects.get(codigo=fila[2])
        except:
            Banco.objects.create(codigo=fila[2], nombre=fila[0], nif=fila[1], tipo=fila[3], tel=tel, fax=fax, web=web,
                                 address=fila[5], cp=fila[6], pais=fila[7], bic=bic)
    csv_file.close()


# http://bandir.infotelefonica.es/3191 página que me permite ver los datos y evolución de las entidades el 3191 es el código de entidad
# def asocia_bancos(request):
#     g_es = usuarios_ronda(request.session['gauser_extra'].ronda)
#     codes = ''
#     for g_e in g_es:
#         num_cuenta_bancaria = re.sub("[^0-9a-zA-Z]", "", str(g_e.num_cuenta_bancaria))
#         if len(num_cuenta_bancaria) > 18:
#             if num_cuenta_bancaria[0:2] != 'ES':
#                 banco_code = re.sub("[^0-9]", "", num_cuenta_bancaria)[0:4]
#             else:
#                 banco_code = re.sub("[^0-9a-zA-Z]", "", num_cuenta_bancaria)[4:8]
            # try:
            # crear_aviso(request,False,banco_code+' '+num_cuenta_bancaria+' '+g_e.gauser.get_full_name())
            # codes = codes + ' ' + banco_code
            # if banco_code == '2097':
            #     g_e.banco = Banco.objects.get(
            #         codigo='2095')  # 2097 era Vital kutxa, le asignamos bankia que es el 2095 kutxabank
            # crear_aviso(request,False,'Entra en 2097')
            # elif banco_code == '2037':
            #     g_e.banco = Banco.objects.get(codigo='2038')  # 2037 era cajarioja, le asignamos bankia que es el 2038
            # crear_aviso(request,False,'Entra en 2037')
            # elif banco_code == '2054' or banco_code == '0142':
            #     g_e.banco = Banco.objects.get(
            #         codigo='2100')  # 0142 banco pequeña empresa,2054 era la CAN, le asignamos Caixabank que es el 2100
            #
            # elif banco_code == '2096' or banco_code == '0208':
            #     g_e.banco = Banco.objects.get(
            #         codigo='2108')  # 2096 era la caja duero, le asignamos Banco inversiones  que es el 2108
            #
            # elif banco_code == '3021':
            #     g_e.banco = Banco.objects.get(codigo='3191')  # de cajalon a nueva caja rural de aragón
            #
            # elif banco_code == '0030':
            #     g_e.banco = Banco.objects.get(codigo='0049')  # banco español de crédito a banco santander
            #
            # elif banco_code == '0104':
            #     g_e.banco = Banco.objects.get(codigo='0182')  # argentaria a bbva
            #
            # elif banco_code == '0008':
            #     g_e.banco = Banco.objects.get(codigo='0081')  # argentaria a bbva
            #
            # else:
            #     g_e.banco = Banco.objects.get(codigo=banco_code)
            # crear_aviso(request,False,'Graba %s'%g_e.banco.nombre)
            # g_e.save()
            # crear_aviso(request,False,'Graba %s'%g_e.banco.nombre)
            # except:
        # pass

def asocia_banco_entidad(entidad):
    banco_encontrado = True
    banco_code = re.sub("[^0-9a-zA-Z]", "", entidad.iban)[4:8]
    if banco_code == '2097':  # 2097 era Vital kutxa
        entidad.banco = Banco.objects.get(codigo='2095')  # le asignamos bankia que es el 2095 kutxabank
    elif banco_code == '2037':
        entidad.banco = Banco.objects.get(codigo='2038')  # 2037 era cajarioja, le asignamos bankia que es el 2038
    elif banco_code == '2054' or banco_code == '0142':
        entidad.banco = Banco.objects.get(
            codigo='2100')  # 0142 banco pequeña empresa,2054 era la CAN, le asignamos Caixabank que es el 2100
    elif banco_code == '2096' or banco_code == '0208':  # 2096 era la caja duero
        entidad.banco = Banco.objects.get(codigo='2108')  # le asignamos Banco inversiones  que es el 2108
    elif banco_code == '3021':
        entidad.banco = Banco.objects.get(codigo='3191')  # de cajalon a nueva caja rural de aragón
    elif banco_code == '0030':
        entidad.banco = Banco.objects.get(codigo='0049')  # banco español de crédito a banco santander
    elif banco_code == '0104':
        entidad.banco = Banco.objects.get(codigo='0182')  # argentaria a bbva
    elif banco_code == '0008':
        entidad.banco = Banco.objects.get(codigo='0081')  # argentaria a bbva
    elif banco_code == '0103':  # Era el Banco Zaragozano
        entidad.banco = Banco.objects.get(codigo='0065')  # BARCLAYS BANK
    else:
        try:
            entidad.banco = Banco.objects.get(codigo=banco_code)
        except:
            banco_encontrado = False
    # crear_aviso(request,False,'Graba %s'%entidad.banco.nombre)
    entidad.save()
    return banco_encontrado


def asocia_banco_ge(g_e):
    num_cuenta_bancaria = re.sub("[^0-9a-zA-Z]", "", str(g_e.num_cuenta_bancaria))
    if len(num_cuenta_bancaria) > 18:
        if num_cuenta_bancaria[0:2] != 'ES':
            banco_code = re.sub("[^0-9]", "", num_cuenta_bancaria)[0:4]
        else:
            banco_code = re.sub("[^0-9a-zA-Z]", "", num_cuenta_bancaria)[4:8]
        if banco_code == '2097':  # 2097 era Vital kutxa,
            g_e.banco = Banco.objects.get(codigo='2095')  # le asignamos bankia que es el 2095 kutxabank
        elif banco_code == '2037':
            g_e.banco = Banco.objects.get(codigo='2038')  # 2037 era cajarioja, le asignamos bankia que es el 2038
        elif banco_code == '2054' or banco_code == '0142':  # 0142 banco pequeña empresa,2054 era la CAN
            g_e.banco = Banco.objects.get(codigo='2100')  # le asignamos Caixabank que es el 2100
        elif banco_code == '2096' or banco_code == '0208':  # 2096 era la caja duero
            g_e.banco = Banco.objects.get(codigo='2108')  # le asignamos Banco inversiones  que es el 2108
        elif banco_code == '3021':
            g_e.banco = Banco.objects.get(codigo='3191')  # de cajalon a nueva caja rural de aragón
        elif banco_code == '0030':
            g_e.banco = Banco.objects.get(codigo='0049')  # banco español de crédito a banco santander
        elif banco_code == '0104':
            g_e.banco = Banco.objects.get(codigo='0182')  # argentaria a bbva
        elif banco_code == '0008':
            g_e.banco = Banco.objects.get(codigo='0081')  # argentaria a bbva
        elif banco_code == '0103':  # Este era el banco zaragozano. Absorvido por Barclays Bank
            g_e.banco = Banco.objects.get(codigo='0065')  # BARCLAYS BANK
        else:
            g_e.banco = Banco.objects.get(codigo=banco_code)
        g_e.save()

def get_banco_from_num_cuenta_bancaria(num_cuenta_bancaria):
    num_cuenta_bancaria = re.sub("[^0-9a-zA-Z]", "", str(num_cuenta_bancaria))
    if len(num_cuenta_bancaria) > 18:
        if num_cuenta_bancaria[0:2] != 'ES':
            banco_code = re.sub("[^0-9]", "", num_cuenta_bancaria)[0:4]
        else:
            banco_code = re.sub("[^0-9a-zA-Z]", "", num_cuenta_bancaria)[4:8]
        if banco_code == '2097':  # 2097 era Vital kutxa,
            banco = Banco.objects.get(codigo='2095')  # le asignamos bankia que es el 2095 kutxabank
        elif banco_code == '2037':
            banco = Banco.objects.get(codigo='2038')  # 2037 era cajarioja, le asignamos bankia que es el 2038
        elif banco_code == '2054' or banco_code == '0142':  # 0142 banco pequeña empresa,2054 era la CAN
            banco = Banco.objects.get(codigo='2100')  # le asignamos Caixabank que es el 2100
        elif banco_code == '2096' or banco_code == '0208':  # 2096 era la caja duero
            banco = Banco.objects.get(codigo='2108')  # le asignamos Banco inversiones  que es el 2108
        elif banco_code == '3021':
            banco = Banco.objects.get(codigo='3191')  # de cajalon a nueva caja rural de aragón
        elif banco_code == '0030':
            banco = Banco.objects.get(codigo='0049')  # banco español de crédito a banco santander
        elif banco_code == '0104':
            banco = Banco.objects.get(codigo='0182')  # argentaria a bbva
        elif banco_code == '0008':
            banco = Banco.objects.get(codigo='0081')  # argentaria a bbva
        elif banco_code == '0103':  # Este era el banco zaragozano. Absorvido por Barclays Bank
            banco = Banco.objects.get(codigo='0065')  # BARCLAYS BANK
        else:
            try:
                banco = Banco.objects.get(codigo=banco_code)
            except:
                banco = Banco.objects.none()
        return banco


# def calc_iban(request):
#     g_es = Gauser_extra.objects.all()
#     tabla = {'A': '10', 'G': '16', 'M': '22', 'S': '28', 'Y': '34', 'B': '11', 'H': '17', 'N': '23', 'T': '29',
#              'Z': '35', 'C': '12', 'I': '18', 'O': '24', 'U': '30', 'D': '13', 'J': '19', 'P': '25', 'V': '31',
#              'E': '14', 'K': '20', 'Q': '26', 'W': '32', 'F': '15', 'L': '21', 'R': '27', 'X': '33', '0': '0', '1': '1',
#              '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9'}
#     for g_e in g_es:
#         num_cuenta_bancaria = re.sub("[^0-9a-zA-Z]", "", str(g_e.num_cuenta_bancaria))
#         if len(num_cuenta_bancaria) > 18 and num_cuenta_bancaria[0:2] != 'ES':
#             cad = num_cuenta_bancaria + 'ES00'
#             for k, v in tabla.items():
#                 cad = cad.replace(k, v)
#             cad = str(98 - int(cad) % 97)
#             cad = cad if len(cad) > 1 else '0' + cad
#             num_cuenta_bancaria = 'ES' + cad + num_cuenta_bancaria
#             g_e.num_cuenta_bancaria = num_cuenta_bancaria
#             g_e.save()


def num_cuenta2iban(num_cuenta_bancaria):
    tabla = {'A': '10', 'G': '16', 'M': '22', 'S': '28', 'Y': '34', 'B': '11', 'H': '17', 'N': '23', 'T': '29',
             'Z': '35', 'C': '12', 'I': '18', 'O': '24', 'U': '30', 'D': '13', 'J': '19', 'P': '25', 'V': '31',
             'E': '14', 'K': '20', 'Q': '26', 'W': '32', 'F': '15', 'L': '21', 'R': '27', 'X': '33', '0': '0', '1': '1',
             '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9'}
    iban = num_cuenta_bancaria
    num_cuenta_bancaria = re.sub("[^0-9a-zA-Z]", "", str(num_cuenta_bancaria))
    if len(num_cuenta_bancaria) > 18 and num_cuenta_bancaria[0:2] != 'ES':
        cad = num_cuenta_bancaria + 'ES00'
        for k, v in tabla.items():
            cad = cad.replace(k, v)
        cad = str(98 - int(cad) % 97)
        cad = cad if len(cad) > 1 else '0' + cad
        iban = 'ES' + cad + num_cuenta_bancaria
    return iban


def bancos_sin_bic(request):
    bancos = Banco.objects.all()
    for banco in bancos:
        if not banco.bic:
            logger.info('Banco %s sin BIC' % banco.codigo)


from html.parser import HTMLParser


# from HTMLParser import HTMLParser #para python 2.7


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ' '.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def download_bancos(request):
    csv_file = open('/home/juanjo/django/gauss_scout/bancos.csv', "rb")
    fichero = csv.reader(csv_file, delimiter=';')
    # Iniciamos un forloop para recorrer todas las filas del archivo (no la primera que contiene nombre de los campos)
    # La primera columna contiene los códigos de los bancos
    codigos = []
    for row in fichero:
        codigos.append(row[0])
    csv_file.close()

    csv_file = open('/home/juanjo/django/gauss_scout/bancos_nuevo.csv', "w+")
    fichero = csv.writer(csv_file, delimiter=';')
    for codigo in codigos:
        # os.system('wget -P/home/juanjo/django/gauss_scout/media/bancos http://bandir.infotelefonica.es/%s'%(codigo))

        with open('/home/juanjo/django/gauss_scout/media/bancos/%s' % (codigo), "r") as myfile:
            data = myfile.read().replace('\n', ' ')
        data = strip_tags(data).decode('iso-8859-1').encode('utf8')  # Codifica utf8
        data = ' '.join(data.split())  # Reemplaza los espacios en blanco por un solo espacio
        # data = data.replace(': ',':').replace('Datos de contacto:','').replace('(adsbygoogle = window.adsbygoogle || []).push({});','')

        p = re.compile('.*?[:]')
        data = p.sub('', data,
                     count=1)  # reemplazamos los primeros caracteres hasta los ":" por nada. Principio no útil

        p = re.compile('[(][a][d][s][b][y].*')
        data = p.sub('', data, count=1)  # reemplazamos los últimos caracteres hasta los ":" por nada. Fin no útil

        strip_strings = [u'CIF Entidad:', u'Código Entidad:', u'Tipo de Entidad:', u'Swift/BIC:',
                         u'Datos de Contacto: Dirección:', u'Código Postal:', u'País:', u'Tel:', u'Fax:', u'Sitio web:']
        for s in strip_strings:
            data = data.replace(s.encode('utf8'), ';')
        data = data.replace(u'Nombre completo:'.encode('utf8'), '')

        # data = ''.join(data.split()) #Reemplaza los espacios en blanco por un solo espacio
        data = data.split(';')
        for p, d in enumerate(data):
            data[p] = d.rstrip().lstrip()  # Reemplaza los espacios en blanco iniciales y finales
        fichero.writerow(data)

    csv_file.close()
