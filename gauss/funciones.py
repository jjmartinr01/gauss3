# -*- coding: utf-8 -*-

import logging
import string
import random
import os
import pdfkit
from datetime import date
from django.db.models import Q
from django.template import RequestContext
from django.template.loader import render_to_string
from gauss.rutas import MEDIA_DOCUMENTOS, MEDIA_ANAGRAMAS
from entidades.models import Alta_Baja, Gauser_extra

logger = logging.getLogger('django')

try:
    from __builtin__ import str, unicode
except:
    from builtins import str


def paginar(total, paso=15, c=1):
    lis = range(1, total + 1)
    ult = None if total % paso == 1 else total
    pagination = []
    contador = 0
    for i in range(1, len(lis) + 1, paso):
        contador += 1
        current = 'current' if c == contador else ''
        last = i + (paso - 1) if (i + paso - 1) <= total else ult
        pagination.append({'first': i, 'last': last, 'current': current})
    return pagination


def human_readable_list(elements, separator=', ', last_separator=' y ', type='title'):
    """
    :param elements: list of elements to be stringyfied
    :param separator: join string between two list elements
    :param last_separator: join string between the two last list elements
    :param type: title (all words first cap), upper (all in caps), lower (all in lowercase), capitalize (first word)
    :return: string with all elements joined
    """
    try:
        cap_operation = getattr(str, type)
        hrl = last_separator.join(cap_operation(separator.join(elements)).rsplit(separator, 1))
    except:
        cap_operation = getattr(unicode, type)
        hrl = last_separator.join(cap_operation(separator.join(elements)).rsplit(separator, 1))
    words_to_be_replaced = [' De ', ' Y ', ' E ', ' Al ', ' O ', ' Del ']
    for w in words_to_be_replaced:
        hrl = hrl.replace(w, w.lower())
    return hrl


def padres_madres(subentidad):
    tutores_id = Gauser_extra.objects.filter(ronda=subentidad.entidad.ronda, subentidades__in=[subentidad]).values_list(
        'tutor1__id', 'tutor2__id')
    return Gauser_extra.objects.filter(id__in=[e for l in tutores_id for e in l]).distinct()


def html_to_pdf(request, texto, media=MEDIA_DOCUMENTOS, fichero='borrar', title='Documento generado por GAUSS',
                attach=False, tipo='inf', pagecount=False):
    """
    :param request: datos de session necesarios para identificar usuario
    :param datos: Diccionario con los datos de configuaran el pdf
    :param fichero: string con el nombre del fichero
    :param tipo: string -> 'doc' documento con TOC, 'inf' informe sin TOC
    :param attach: string con lista de archivos separados por espacios
    :return: El fichero pdf creado
    """
    logger.info(u'html_to_pdf')
    fichero_html = media + fichero + '.html'
    fichero_pdf = media + fichero + '.pdf'

    if not os.path.exists(os.path.dirname(fichero_pdf)):
        os.makedirs(os.path.dirname(fichero_pdf))
        logger.info(u'Se crea ruta: %s' % (fichero_pdf))

    if not os.path.exists(os.path.dirname(media)):
        os.makedirs(os.path.dirname(media))
        logger.info(u'Se crea ruta: %s' % (media))

    html_template = 'genera_documento2pdf.html'
    c = render_to_string(html_template, {'texto': texto, 'title': title}, request=request)
    logger.info(u'Escritura en %s' % (fichero_html))
    with open(fichero_html, "w") as html_file:
        html_file.write("{0}".format(c.encode('utf-8')))

    cabecera = MEDIA_ANAGRAMAS + '%s_cabecera.html' % request.session['gauser_extra'].ronda.entidad.code
    pie = MEDIA_ANAGRAMAS + '%s_pie.html' % request.session['gauser_extra'].entidad.code
    if tipo == 'doc':
        estilo = media + 'estilo.xsl'
        comando = 'wkhtmltopdf -q -L 20 -R 20 -B 20 --header-spacing 5 --header-html %s --footer-html %s toc --xsl-style-sheet %s %s %s' % (
            cabecera, pie, estilo, fichero_html, fichero_pdf)
        logger.info(u'Ejecuta: %s' % (comando))
        os.system(comando)
    elif tipo == 'inf':
        # comando = 'wkhtmltopdf -q -L 20 -R 20 -B 20 --header-spacing 5 --header-html %s --footer-html %s %s %s' % (
        #     cabecera, pie, fichero_html, fichero_pdf)
        # logger.info(u'Ejecuta: %s' % (comando))
        # os.system(comando)
        options = {
            'page-size': 'A4',
            'margin-top': '52',
            'margin-right': '20',
            'margin-bottom': '20',
            'margin-left': '20',
            'encoding': "UTF-8",
            'no-outline': None,
            '--header-html': 'file://%s' % cabecera,
            '--footer-html': 'file://%s' % pie,
            '--header-spacing': '5',
            '--load-error-handling': 'ignore'
        }
        pdfkit.from_string(c, fichero_pdf, options)
    elif tipo == 'sin_cabecera':
        options = {'page-size': 'A4', 'margin-top': '20', 'margin-right': '20', 'margin-bottom': '20',
                   'margin-left': '20', 'encoding': "UTF-8", 'no-outline': None, '--header-spacing': '5',
                   '--load-error-handling': 'ignore'}
        pdfkit.from_string(c, fichero_pdf, options)

        # comando = 'wkhtmltopdf -q -L 20 -R 20 -B 20 --header-spacing 5 %s %s' % (fichero_html, fichero_pdf)
        # logger.info(u'Ejecuta: %s' % (comando))
        # os.system(comando)
    if attach:
        fichero_pdf2 = media + fichero + '_adjuntos.pdf'
        comando = 'pdftk %s attach_files %s output %s' % (fichero_pdf, attach, fichero_pdf2)
        os.system(comando)
        fichero_pdf = fichero_pdf2
    if pagecount:
        comando = 'pdftk %s dump_data | grep "NumberOfPages" | cut -d":" -f2' % fichero_pdf
        pagecount = int(os.system(comando))
        return pagecount, open(fichero_pdf)
    else:
        return open(fichero_pdf, 'rb')


# Generador de contraseñas
def pass_generator(size=6, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


# Obtención de los usuarios de la entidad que no están de baja:
def usuarios_ronda(ronda, subentidades=False, cargos=False, edad_min=-1, edad_max=120):
    bajas = Alta_Baja.objects.filter(entidad=ronda.entidad, fecha_baja__isnull=False).values_list('gauser__id',
                                                                                                  flat=True)
    nacimiento_early = date(date.today().year - edad_max, 1, 1)
    nacimiento_last = date(date.today().year - edad_min, 12, 31)
    if edad_min == -1 and edad_max == 120:
        filtro = ~Q(gauser__id__in=bajas) & ~Q(gauser__username='gauss') & Q(ronda=ronda) & (Q(
            gauser__nacimiento__gte=nacimiento_early) & Q(gauser__nacimiento__lte=nacimiento_last) | Q(
            gauser__nacimiento__isnull=True))
    else:
        filtro = ~Q(gauser__id__in=bajas) & ~Q(gauser__username='gauss') & Q(ronda=ronda) & Q(
            gauser__nacimiento__gte=nacimiento_early) & Q(gauser__nacimiento__lte=nacimiento_last)
    if cargos:
        filtro = filtro & Q(cargos__in=cargos)
    if subentidades:
        filtro = filtro & Q(subentidades__in=subentidades)

    return Gauser_extra.objects.filter(filtro).order_by('gauser__last_name', 'gauser__first_name')


def usuarios_de_gauss(entidad, subentidades=False, cargos=False, edad_min=-1, edad_max=120, ronda=False):
    bajas = Alta_Baja.objects.filter(entidad=entidad, fecha_baja__isnull=False).values_list('gauser__id', flat=True)
    nacimiento_early = date(date.today().year - edad_max, 1, 1)
    nacimiento_last = date(date.today().year - edad_min, 12, 31)
    if edad_min == -1 and edad_max == 120:
        filtro = ~Q(gauser__id__in=bajas) & ~Q(gauser__username='gauss') & Q(ronda__entidad=entidad) & (Q(
            gauser__nacimiento__gte=nacimiento_early) & Q(gauser__nacimiento__lte=nacimiento_last) | Q(
            gauser__nacimiento__isnull=True))
    else:
        filtro = ~Q(gauser__id__in=bajas) & ~Q(gauser__username='gauss') & Q(ronda__entidad=entidad) & Q(
            gauser__nacimiento__gte=nacimiento_early) & Q(gauser__nacimiento__lte=nacimiento_last)
    if ronda == 'all':
        filtro = filtro
    elif not ronda:
        filtro = filtro & Q(ronda=entidad.ronda)
    else:
        filtro = filtro & Q(ronda=ronda)
    if cargos:
        filtro = filtro & Q(cargos__in=cargos)
    if subentidades:
        filtro = filtro & Q(subentidades__in=subentidades)

    return Gauser_extra.objects.filter(filtro).order_by('gauser__last_name', 'gauser__first_name')

    # if cargos and subentidades:
    #     usuarios = Gauser_extra.objects.filter(
    #         Q(entidad=entidad) & Q(ronda=ronda) & ~Q(gauser__id__in=bajas) & Q(
    #             subentidades__in=subentidades) & Q(cargos__in=cargos) & ~Q(gauser__username='gauss')).order_by(
    #         'gauser__last_name', 'gauser__first_name')
    # elif subentidades:
    #     usuarios = Gauser_extra.objects.filter(
    #         Q(entidad=entidad) & Q(ronda=ronda) & ~Q(gauser__id__in=bajas) & Q(subentidades__in=subentidades) &
    #         ~Q(gauser__username='gauss')).order_by('gauser__last_name', 'gauser__first_name')
    # elif perfiles:
    #     usuarios = Gauser_extra.objects.filter(
    #         Q(entidad=entidad) & Q(ronda=ronda) & ~Q(gauser__id__in=bajas) & Q(perfiles__in=perfiles) & ~Q(
    #             gauser__username='gauss')).order_by('gauser__last_name', 'gauser__first_name')
    # elif cargos:
    #     usuarios = Gauser_extra.objects.filter(
    #         Q(entidad=entidad) & Q(ronda=ronda) & ~Q(gauser__id__in=bajas) & Q(cargos__in=cargos) & ~Q(
    #             gauser__username='gauss')).order_by('gauser__last_name', 'gauser__first_name')
    # else:
    #     usuarios = Gauser_extra.objects.filter(
    #         Q(entidad=entidad) & Q(ronda=ronda) & ~Q(gauser__id__in=bajas) & ~Q(
    #             gauser__username='gauss')).order_by('gauser__last_name', 'gauser__first_name')
    # if edad_max != 100:
    #     n_early = date(date.today().year - edad_max, 1, 1)  # nacimiento temprano
    #     usuarios = usuarios.filter(gauser__nacimiento__gte=n_early)
    # if edad_min != 0:
    #     n_last = date(date.today().year - edad_min, 12, 31)  # nacimiento tardío
    #     usuarios = usuarios.filter(gauser__nacimiento__lte=n_last)
    # return usuarios


# Devuelve las iniciales del nombre seguidas del primer apellido o el alias del usuario
def nombre_usuario(g_e, alias=False):
    # En primer lugar quitamos tildes, colocamos nombres en minúsculas y :
    def nombre(g_e):
        nombre = g_e.gauser.first_name.split()
        apellidos = g_e.gauser.last_name.split()
        iniciales_nombre = ''
        for parte in nombre:
            iniciales_nombre = iniciales_nombre + parte[0]
        iniciales_apellidos = apellidos[0]
        return u'%s %s' % (iniciales_nombre, iniciales_apellidos)

    if alias:
        return g_e.alias if g_e.alias else nombre(g_e)
    else:
        return nombre(g_e)
