# -*- coding: utf-8 -*-

from gauss.settings import RUTA_DJANGO_SETTINGS, RUTA_BASE_SETTINGS

RUTA_DJANGO = RUTA_DJANGO_SETTINGS

RUTA_BASE = RUTA_BASE_SETTINGS

RUTA_STATIC = "%s/sitestatic/" % RUTA_BASE

RUTA_MEDIA = "%s/media/" % RUTA_BASE

RUTA_STATIC_WEB = "%s/sitestatic/images/web/" % RUTA_BASE

# Rutas para los archivos estáticos de GAUSS:

PATH_IMAGES = RUTA_STATIC + "images/"

PATH_FILES = RUTA_STATIC + "files/"

PATH_FOTOS = RUTA_STATIC + "fotos/"

PATH_AVISOS = RUTA_STATIC + "avisos/"

PATH_MENSAJES = RUTA_STATIC + "mensajes/"

# Rutas para los archivos subidos y generados a través de GAUSS:

MEDIA_LOG = RUTA_MEDIA + "log/"

MEDIA_FOTOS = RUTA_MEDIA + "fotos/"

MEDIA_FILES = RUTA_MEDIA + "files/"

MEDIA_ANAGRAMAS = RUTA_MEDIA + "anagramas/"

MEDIA_ADJUNTOS = RUTA_MEDIA + "adjuntos/"

MEDIA_EVENTOS = RUTA_MEDIA + "eventos/"

MEDIA_CONTABILIDAD = RUTA_MEDIA + "contabilidad/"

MEDIA_PRESUPUESTO = RUTA_MEDIA + "presupuestos/"

MEDIA_ACTAS = RUTA_MEDIA + "actas/"

MEDIA_DOCUMENTOS = RUTA_MEDIA + "documentos/"

MEDIA_LOPD = RUTA_MEDIA + "lopd/"

MEDIA_INCIDENCIAS_LOPD = RUTA_MEDIA + "incidencias_lopd/"

MEDIA_MENSAJES = RUTA_MEDIA + "mensajes/"

MEDIA_TMP = RUTA_MEDIA + "tmp/"

MEDIA_VESTUARIOS = RUTA_MEDIA + "vestuarios/"

MEDIA_FORMULARIOS = RUTA_MEDIA + "formularios/"

MEDIA_LISTADOS = RUTA_MEDIA + "listados/"

MEDIA_CUPO = RUTA_MEDIA + "cupo/"

MEDIA_CONVIVENCIA = RUTA_MEDIA + "convivencia/"

MEDIA_ABSENTISMO = RUTA_MEDIA + "absentismo/"

MEDIA_REPARACIONES = RUTA_MEDIA + "reparaciones/"

MEDIA_INFORMES = RUTA_MEDIA + "informes/"

MEDIA_FICHEROS_TAREAS = RUTA_MEDIA + "ficheros_tareas/"

MEDIA_ACTILLAS = RUTA_MEDIA + "actillas/"

MEDIA_PROGRAMACIONES = RUTA_MEDIA + "programaciones/"

MEDIA_CC = RUTA_MEDIA + "competencias_clave/"

MEDIA_VUT = RUTA_MEDIA + "vut/"

MEDIA_REUNIONES = RUTA_MEDIA + "reuniones/"

MEDIA_PENDIENTES = RUTA_MEDIA + "pendientes/"

MEDIA_INSPECCION = RUTA_MEDIA + "inspeccion/"

def buscar_identificador(request, href):
    for menu_creado in request.session['lateral']:
        if menu_creado['href'] == href:
            identificador = menu_creado['id']
            return identificador
