# -*- coding: utf-8 -*-
from celery import shared_task
import logging
from lxml import etree as ElementTree
from django.db.models import Q
from entidades.models import CargaMasiva, Gauser_extra, Dependencia
from estudios.models import Curso, Grupo, Materia, Gauser_extra_estudios
from horarios.models import Horario, Tramo_horario, Actividad, Sesion, Falta_asistencia, Guardia
from gauss.rutas import MEDIA_FILES

logger = logging.getLogger('django')

@shared_task
def carga_masiva_from_file():
    # f = open(MEDIA_FILES + 'prueba_rabitt.txt', 'w+')
    # f.write('Esta es el contenido PLUMIER')
    # f.close()
    cargas_necesarias = CargaMasiva.objects.filter(cargado=False)
    for carga in cargas_necesarias:
        if carga.tipo == 'PLUMIER':
            xml_file = ElementTree.XML(carga.fichero.read())
            horario = Horario.objects.get(entidad=carga.ronda.entidad, predeterminado=True)
            dias = {'L': 1, 'M': 2, 'X': 3, 'J': 4, 'V': 5, 'S': 6, 'D': 7}

            for sesion in xml_file.findall('.//SESION'):
                clave_docente = sesion.find('DOCENTE').text
                try:
                    docente = Gauser_extra.objects.get(entidad=carga.ronda.entidad, ronda=carga.ronda,
                                                       clave_ex=clave_docente)
                except:
                    # logger.info(u'No se encuentra el docente con clave: %s' % clave_docente)
                    docente = None

                dia = dias[sesion.find('DIA').text]

                clave_tramo_horario = sesion.find('INTERVALO').text
                try:
                    tramo_horario = Tramo_horario.objects.get(horario=horario, clave_ex=clave_tramo_horario)
                except:
                    # logger.info(u'No se encuentra el tramo horario con clave: %s' % clave_tramo_horario)
                    tramo_horario = None

                clave_materia = sesion.find('MATERIA').text
                if clave_materia:
                    try:
                        materia = Materia.objects.get(clave_ex=clave_materia, curso__ronda=carga.ronda)
                    except:
                        if '#' in clave_materia:
                            pass
                            # logger.info('Encontrada materia con #. Se buscará la actividad equivalente de código %s' % (
                            #                 clave_materia))
                        else:
                            pass
                            # logger.info('No se encuentra la materia con clave: %s. Clave del grupo: %s' % (
                            #                 clave_materia, sesion.find('GRUPO').text))
                        materia = None
                else:
                    materia = None

                grupo_c = sesion.find('GRUPO').text
                if grupo_c:
                    if '-' in grupo_c:  # Si no tiene '-' es porque es un grupo no definido en RACIMA. Por ejemplo 1COMP, 2COMP, ...
                        grupo_c = grupo_c.split('-')
                        try:
                            grupo = Grupo.objects.get(Q(ronda=carga.ronda), Q(clave_ex=grupo_c[1]) | Q(nombre=grupo_c[1]))
                        except:
                            # crear_aviso(request, False, u'No se encuentra el grupo con clave: ' + grupo_c[1])
                            grupo = None
                        try:
                            curso = Curso.objects.get(ronda=carga.ronda, clave_ex=grupo_c[0])
                            grupo.cursos.add(curso)
                            grupo.save()
                        except:
                            # crear_aviso(request, False, u'No se encuentra el curso con clave: ' + grupo_c[0])
                            pass
                    else:
                        try:
                            grupo = Grupo.objects.get(ronda=carga.ronda, clave_ex=grupo_c, nombre=grupo_c)
                        except:
                            grupo = Grupo.objects.create(ronda=carga.ronda, clave_ex=grupo_c, nombre=grupo_c)
                            # crear_aviso(request, False, u'Se ha creado un grupo nuevo: ' + grupo_c)
                else:
                    grupo = None

                dependencia = sesion.find('AULA').text
                if dependencia:
                    try:
                        dependencia = Dependencia.objects.get(entidad=carga.ronda.entidad, clave_ex=dependencia)
                    except:
                        # crear_aviso(request, False, u'Se crea el aula: ' + dependencia)
                        dependencia = Dependencia.objects.create(entidad=carga.ronda.entidad, nombre=dependencia,
                                                                 clave_ex=dependencia)

                actividad = sesion.find('TAREA').text
                materia_sostenido = sesion.find('MATERIA').text
                if actividad:
                    try:
                        actividad = Actividad.objects.get(clave_ex=actividad, entidad=carga.ronda.entidad)
                    except:
                        try:
                            if '#' in materia_sostenido:
                                materia_sostenido = materia_sostenido.replace('#', '')
                                # crear_aviso(request, False, u'Tratando de encontrar la actividad: ' + materia_sostenido)
                                actividad = Actividad.objects.get(clave_ex=materia_sostenido, entidad=carga.ronda.entidad)
                            else:
                                # crear_aviso(request, False, u'Se crea la actividad: ' + actividad)
                                actividad = Actividad.objects.create(nombre=actividad, clave_ex=actividad,
                                                                     entidad=carga.ronda.entidad)
                        except:
                            # crear_aviso(request, False, u'Se crea la actividad: ' + actividad)
                            actividad = Actividad.objects.create(nombre=actividad, clave_ex=actividad,
                                                                 entidad=carga.ronda.entidad)

                if docente:
                    Sesion.objects.create(nombre=tramo_horario.nombre, inicio=tramo_horario.inicio,
                                          fin=tramo_horario.fin,
                                          g_e=docente, dia=dia, materia=materia, grupo=grupo, dependencia=dependencia,
                                          actividad=actividad, horario=horario)

            carga.cargado = True
            carga.save()
    return True