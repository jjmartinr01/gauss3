# -*- coding: utf-8 -*-
from celery import shared_task
import logging
from lxml import etree as ElementTree
from difflib import get_close_matches
from django.db.models import Q
from django.utils.timezone import datetime
from entidades.models import CargaMasiva, Gauser_extra, Dependencia, Subentidad
from estudios.models import Curso, Grupo, Materia, Gauser_extra_estudios
from horarios.models import Horario, Tramo_horario, Actividad, Sesion, Falta_asistencia, Guardia
from programaciones.models import Especialidad_entidad, Gauser_extra_programaciones, Departamento, \
    Especialidad_funcionario, crea_departamentos
from gauss.rutas import MEDIA_FILES

logger = logging.getLogger('django')

def get_coincidente(texto, lista_ids_textos):  # Devuelve el id del gauser_extra coincidente
    lista_textos = [n[1] for n in lista_ids_textos]
    try:
        m = get_close_matches(texto, lista_textos, 1)[0]
        for n in lista_ids_textos:
            if n[1] == m:
                return n[0]
        return None
    except:
        return None

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
                    docente = Gauser_extra.objects.get(ronda=carga.ronda, clave_ex=clave_docente)
                except:
                    logger.info('No se encuentra el docente con clave: %s' % clave_docente)
                    docente = None

                dia = dias[sesion.find('DIA').text]

                clave_tramo_horario = sesion.find('INTERVALO').text
                try:
                    tramo_horario = Tramo_horario.objects.get(horario=horario, clave_ex=clave_tramo_horario)
                except:
                    logger.info(u'No se encuentra el tramo horario con clave: %s' % clave_tramo_horario)
                    tramo_horario = None

                clave_materia = sesion.find('MATERIA').text
                if clave_materia:
                    try:
                        materia = Materia.objects.get(clave_ex=clave_materia, curso__ronda=carga.ronda)
                    except:
                        if '#' in clave_materia:
                            pass
                            logger.info('Encontrada materia con #. Se buscará la actividad equivalente de código %s' % (
                                            clave_materia))
                        else:
                            pass
                            logger.info('No se encuentra la materia con clave: %s. Clave del grupo: %s' % (
                                            clave_materia, sesion.find('GRUPO').text))
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
        elif carga.tipo == 'RACIMA':
            xml_file = ElementTree.XML(carga.fichero.read())
            # incidencias = {'especialidades': False}
            horario = Horario.objects.create(entidad=carga.ronda.entidad, ronda=carga.ronda,
                                             descripcion=u'Creado a través del xml obtenido de racima %s' % datetime.now())
            horarios = Horario.objects.filter(entidad=carga.ronda.entidad)
            for h in horarios:
                h.predeterminado = False
                h.save()
            horario.predeterminado = True
            horario.save()
            # for elemento in racima.xpath(".//grupo_datos[@seq='CURSOS_DEL_CENTRO']/grupo_datos"):
            for elemento in xml_file.findall(".//grupo_datos[@seq='CURSOS_DEL_CENTRO']/grupo_datos"):
                nombre = elemento.find('dato[@nombre_dato="D_OFERTAMATRIG"]').text
                curso_codigo = elemento.find('dato[@nombre_dato="X_OFERTAMATRIG"]').text
                try:
                    curso = Curso.objects.get(clave_ex=curso_codigo, ronda=carga.ronda)
                    curso.nombre = nombre
                    curso.observaciones += u'<br>Actualizado el %s' % datetime.now()
                    curso.save()
                    logger.info('Se actualiza el curso: %s' % curso)
                except:
                    observaciones = u'Creado el %s' % datetime.now()
                    Curso.objects.create(nombre=nombre, clave_ex=curso_codigo, observaciones=observaciones,
                                         ronda=carga.ronda)
                    logger.info('Se ha creado el curso %s, con código %s' % (nombre, curso_codigo))
            # for elemento in xml_file.xpath(".//grupo_datos[@seq='MATERIAS']/grupo_datos"):
            for elemento in xml_file.findall(".//grupo_datos[@seq='MATERIAS']/grupo_datos"):
                nombre = elemento.find('dato[@nombre_dato="D_MATERIAC"]').text
                materia_codigo = elemento.find('dato[@nombre_dato="X_MATERIAOMG"]').text
                curso_codigo = elemento.find('dato[@nombre_dato="X_OFERTAMATRIG"]').text
                try:
                    curso = Curso.objects.get(clave_ex=curso_codigo, ronda=carga.ronda)
                except:
                    observaciones = u'Creado el %s. Por no existir y tener asociada la materia %s' % (
                        datetime.now(), materia_codigo)
                    curso = Curso.objects.create(clave_ex=curso_codigo, ronda=carga.ronda, observaciones=observaciones,
                                                 nombre='Curso inventado')
                try:
                    horas = int(elemento.find('dato[@nombre_dato="N_HORASMIN"]').text) / 60
                except:
                    horas = 0
                try:
                    duracion = int(elemento.find('dato[@nombre_dato="N_HORAS"]').text)
                except:
                    duracion = 0

                materias = Materia.objects.filter(curso__clave_ex=curso_codigo, clave_ex=materia_codigo,
                                                  curso__ronda=carga.ronda)
                if materias.count() == 0:
                    try:
                        observaciones = u'Creada el %s' % datetime.now()
                        Materia.objects.create(curso=curso, nombre=nombre, clave_ex=materia_codigo,
                                               observaciones=observaciones,
                                               horas=horas, duracion=duracion)
                        logger.info('Se ha creado la materia %s, con código %s' % (nombre, materia_codigo))
                    except:
                        logger.warning('No se ha creado la materia %s. No existe curso %s' % (nombre, materia_codigo))
                elif materias.count() > 1:
                    materia = materias[0]
                    materias.exclude(pk__in=[materia.pk]).delete()
                    materia.curso = curso
                    materia.nombre = nombre
                    materia.horas = horas
                    materia.duracion = duracion
                    materia.observaciones += u'<br>Actualizada el %s' % datetime.now()
                    materia.save()
                    logger.info('Se actualiza la materia: %s' % nombre)
                else:
                    materia = materias[0]
                    materia.curso = curso
                    materia.nombre = nombre
                    materia.horas = horas
                    materia.duracion = duracion
                    materia.observaciones += u'<br>Actualizada el %s' % datetime.now()
                    materia.save()
                    logger.info('Se actualiza la materia: %s' % nombre)

                # try:
                #     materia = Materia.objects.get(curso__clave_ex=curso_codigo, clave_ex=materia_codigo,
                #                                   curso__ronda=carga.ronda)
                #     materia.curso = curso
                #     materia.nombre = nombre
                #     materia.horas = horas
                #     materia.duracion = duracion
                #     materia.observaciones += u'<br>Actualizada el %s' % datetime.now()
                #     materia.save()
                #     logger.info(u'Se actualiza la materia: %s' % nombre)
                # except:
                #     try:
                #         observaciones = u'Creada el %s' % datetime.now()
                #         Materia.objects.create(curso=curso, nombre=nombre, clave_ex=materia_codigo, observaciones=observaciones,
                #                                horas=horas, duracion=duracion)
                #         logger.info(u'Se ha creado la materia %s, con código %s' % (nombre, materia_codigo))
                #     except:
                #         logger.warning(u'No se ha creado la materia %s. No existe curso %s' % (nombre, materia_codigo))
                #         crear_aviso(request, False,
                #                     u'La materia %s, asignada al curso %s no ha podido ser creada ya que dicho curso no existe.' % (
                #                         nombre, curso_codigo))

            # for elemento in xml_file.xpath(".//grupo_datos[@seq='ACTIVIDADES']/grupo_datos"):
            for elemento in xml_file.findall(".//grupo_datos[@seq='ACTIVIDADES']/grupo_datos"):
                nombre = elemento.find('dato[@nombre_dato="D_ACTIVIDAD"]').text
                actividad_codigo = elemento.find('dato[@nombre_dato="X_ACTIVIDAD"]').text
                try:
                    actividad = Actividad.objects.get(clave_ex=actividad_codigo, entidad=carga.ronda.entidad)
                    actividad.nombre = nombre
                    actividad.observaciones += u'<br>Actualizada el %s' % datetime.now()
                    actividad.save()
                    logger.info('Se actualiza la actividad: %s' % nombre)
                except:
                    observaciones = u'Creada el %s' % datetime.now()
                    Actividad.objects.create(nombre=nombre, clave_ex=actividad_codigo, observaciones=observaciones,
                                             entidad=carga.ronda.entidad)
                    logger.info('Se ha creado la actividad "%s", con código %s' % (nombre, actividad_codigo))
            # for elemento in xml_file.xpath(".//grupo_datos[@seq='DEPENDENCIAS']/grupo_datos"):
            for elemento in xml_file.findall(".//grupo_datos[@seq='DEPENDENCIAS']/grupo_datos"):
                nombre = elemento.find('dato[@nombre_dato="D_DEPENDENCIA"]').text
                dependencia_codigo = elemento.find('dato[@nombre_dato="X_DEPENDENCIA"]').text
                abrev = elemento.find('dato[@nombre_dato="C_DEPENDENCIA"]').text

                dependencias = Dependencia.objects.filter(entidad=carga.ronda.entidad, clave_ex=dependencia_codigo)
                if dependencias.count() == 0:
                    observaciones = u'Creada el %s' % datetime.now()
                    dependencia = Dependencia.objects.create(entidad=carga.ronda.entidad, nombre=nombre, abrev=abrev,
                                                             clave_ex=dependencia_codigo, observaciones=observaciones)
                    logger.info('Se ha creado la dependencia "%s", con código %s' % (nombre, dependencia_codigo))
                elif dependencias.count() > 1:
                    dependencia = dependencias[0]
                    dependencias.exclude(pk__in=[dependencia.pk]).delete()
                    dependencia.nombre = nombre
                    dependencia.abrev = abrev
                    dependencia.observaciones += u'<br>Actualizada el %s' % datetime.now()
                    dependencia.save()
                    logger.info('Se actualiza la dependencia: %s' % nombre)
                else:
                    dependencia = dependencias[0]
                    dependencia.nombre = nombre
                    dependencia.abrev = abrev
                    dependencia.observaciones += u'<br>Actualizada el %s' % datetime.now()
                    dependencia.save()
                    logger.info('Se actualiza la dependencia: %s' % nombre)

                # try:
                #     dependencia = Dependencia.objects.get(entidad=carga.ronda.entidad, clave_ex=dependencia_codigo)
                #     dependencia.nombre = nombre
                #     dependencia.abrev = abrev
                #     materia.observaciones += u'<br>Actualizada el %s' % datetime.now()
                #     dependencia.save()
                #     logger.info(u'Se actualiza la dependencia: %s' % nombre)
                # except:
                #     observaciones = u'Creada el %s' % datetime.now()
                #     Dependencia.objects.create(entidad=carga.ronda.entidad, nombre=nombre, clave_ex=dependencia_codigo, abrev=abrev,
                #                                observaciones=observaciones)
                #     logger.info(u'Se ha creado la dependencia "%s", con código %s' % (nombre, dependencia_codigo))

            # for elemento in xml_file.xpath(".//grupo_datos[@seq='JORNADAS_ESCOLARES']/grupo_datos"):
            # for elemento in xml_file.findall(".//grupo_datos[@seq='JORNADAS_ESCOLARES']/grupo_datos"):
            #     jornada = elemento.find('dato[@nombre_dato="C_NOMBRE"]').text
            #     jornada_codigo = elemento.find('dato[@nombre_dato="X_PLAJORESCCEN"]').text
            #     try:
            #         jor_existe = Jornada_escolar.objects.get(entidad=g_e_entidad, curso_escolar=g_e_entidad.curso_escolar,
            #                                                  clave_ex=jornada_codigo)
            #         jor_existe.nombre = jornada
            #         jor_existe.save()
            #     except:
            #         Jornada_escolar.objects.create(entidad=g_e_entidad,
            #                                        curso_escolar=g_e_entidad.curso_escolar,
            #                                        nombre=jornada, clave_ex=jornada_codigo)
            #         crear_aviso(request, False, u'Se añade una nueva jornada escolar: ' + jornada)

            # for elemento in xml_file.xpath(".//grupo_datos[@seq='TRAMOS_HORARIOS']/grupo_datos"):
            for elemento in xml_file.findall(".//grupo_datos[@seq='TRAMOS_HORARIOS']/grupo_datos"):
                nombre = elemento.find('dato[@nombre_dato="T_HORCEN"]').text
                tramo_codigo = elemento.find('dato[@nombre_dato="X_TRAMO"]').text
                inicio = int(elemento.find('dato[@nombre_dato="N_INICIO"]').text)
                h_inicio = '%d:%d' % (int(inicio / 60), int(inicio % 60))
                fin = int(elemento.find('dato[@nombre_dato="N_FIN"]').text)
                h_fin = '%d:%d' % (int(fin / 60), int(fin % 60))
                # jornada_codigo = elemento.find('dato[@nombre_dato="X_PLAJORESCCEN"]').text
                # jornada = Jornada_escolar.objects.get(entidad=g_e_entidad,
                #                                       curso_escolar=g_e_entidad.curso_escolar,
                #                                       clave_ex=jornada_codigo)
                try:
                    tramo = Tramo_horario.objects.get(horario=horario, clave_ex=tramo_codigo)
                    tramo.nombre = nombre
                    tramo.inicio = h_inicio
                    tramo.fin = h_fin
                    tramo.save()
                    logger.info('Se actualiza el tramo horario: %s' % nombre)
                except:
                    Tramo_horario.objects.create(horario=horario, nombre=nombre,
                                                 clave_ex=tramo_codigo, inicio=h_inicio, fin=h_fin)
                    logger.info('Se ha creado el tramo horario "%s", con código %s' % (nombre, tramo_codigo))

            grupos = Grupo.objects.filter(ronda=carga.ronda)
            grupos_nombre = [(g.id, g.nombre) for g in grupos]
            # for elemento in xml_file.xpath(".//grupo_datos[@seq='UNIDADES']/grupo_datos"):
            for elemento in xml_file.findall(".//grupo_datos[@seq='UNIDADES']/grupo_datos"):
                nombre = elemento.find('dato[@nombre_dato="T_NOMBRE"]').text
                grupo_codigo = elemento.find('dato[@nombre_dato="X_UNIDAD"]').text
                curso_codigo = elemento.find('dato[@nombre_dato="X_OFERTAMATRIG"]').text
                curso = Curso.objects.get(clave_ex=curso_codigo, ronda=carga.ronda)
                # Este es el cargado de grupos como objetos tipo Grupo:
                try:
                    grupo = Grupo.objects.get(ronda=carga.ronda, clave_ex=grupo_codigo)
                    grupo.nombre = nombre
                    grupo.cursos.add(curso)
                    if not curso.nombre in grupo.observaciones:
                        grupo.observaciones += ', ' + curso.nombre
                    grupo.save()
                    logger.info('Se actualiza el grupo (Grupo): %s' % nombre)
                except:
                    grupo_id = get_coincidente(nombre, grupos_nombre)
                    if grupo_id:
                        try:
                            grupo = Grupo.objects.get(ronda=carga.ronda, id=grupo_id, clave_ex__isnull=True)
                            grupo.clave_ex = grupo_codigo
                            grupo.cursos.add(curso)
                            if grupo.observaciones:
                                if not curso.nombre in grupo.observaciones:
                                    grupo.observaciones += ', ' + curso.nombre
                            else:
                                grupo.observaciones = u'No creada por el xml de Racima'
                            grupo.save()
                            logger.info('Se actualiza el grupo (Grupo): %s' % nombre)
                        except:
                            observaciones = 'Creado el %s a través del xml de Racima (mixto)' % datetime.now()
                            grupo = Grupo.objects.create(ronda=carga.ronda, nombre=nombre, clave_ex=grupo_codigo,
                                                         observaciones=observaciones)
                            grupo.cursos.add(curso)
                            logger.warning('Se ha creado el grupo "%s", con código %s' % (nombre, grupo_codigo))
                    else:
                        observaciones = 'Creado el %s a través del xml de Racima' % datetime.now()
                        grupo = Grupo.objects.create(ronda=carga.ronda, nombre=nombre, clave_ex=grupo_codigo,
                                                     observaciones=observaciones)
                        grupo.cursos.add(curso)
                        logger.warning('Se ha creado el grupo "%s", con código %s' % (nombre, grupo_codigo))

            sub_docentes = Subentidad.objects.filter(Q(entidad=carga.ronda.entidad), Q(fecha_expira__gt=datetime.today()),
                                                     Q(nombre__icontains='docente') | Q(
                                                         nombre__icontains='profesor') | Q(
                                                         nombre__icontains='maestro'))
            docentes = Gauser_extra.objects.filter(subentidades__in=sub_docentes, ronda=carga.ronda)
            nombres_docentes = [(d.id, d.gauser.get_full_name()) for d in docentes]
            for elemento in xml_file.findall(".//grupo_datos[@seq='EMPLEADOS']/grupo_datos"):
                profesor_nombre = elemento.find('dato[@nombre_dato="NOMBRE"]').text
                profesor_apellido1 = elemento.find('dato[@nombre_dato="APELLIDO1"]').text
                profesor_apellido2 = elemento.find('dato[@nombre_dato="APELLIDO2"]').text
                nombre_docente = profesor_nombre + ' ' + profesor_apellido1 + ' ' + profesor_apellido2
                espec = elemento.find('dato[@nombre_dato="D_PUESTO"]').text
                if espec == "Pedagogía Terapeutica":
                    espec = "Pedagogía Terapéutica"
                profesor_codigo = elemento.find('dato[@nombre_dato="X_EMPLEADO"]').text
                crea_departamentos(carga.ronda)
                especialidades = Especialidad_entidad.objects.filter(especialidad__nombre__icontains=espec,
                                                                     ronda=carga.ronda)
                if especialidades.count() == 0:
                    esp_funcionario = Especialidad_funcionario.objects.filter(Q(nombre__icontains=espec),
                                                                              ~Q(cuerpo__nombre__icontains="catedr"))
                    if esp_funcionario.count() == 0:
                        especialidad = None
                        logger.warning('No se ha encontrado la especialidad asociada a: %s' % espec)
                    else:
                        especialidad = Especialidad_entidad.objects.create(especialidad=esp_funcionario[0],
                                                                           ronda=carga.ronda)
                else:
                    especialidad = especialidades[0]
                try:
                    gauser_extra = Gauser_extra.objects.get(clave_ex=profesor_codigo, ronda=carga.ronda)
                    logger.info('Se identifica al gauser_extra: %s' % gauser_extra.gauser.get_full_name())
                except:
                    gauser_extra_id = get_coincidente(nombre_docente, nombres_docentes)
                    if gauser_extra_id:
                        gauser_extra = Gauser_extra.objects.get(ronda=carga.ronda, id=gauser_extra_id)
                        gauser_extra.clave_ex = profesor_codigo
                        gauser_extra.save()
                        logger.info('Se actualiza el docente %s con la clave_ex %s' % (
                            gauser_extra.gauser.get_full_name(), profesor_codigo))
                    else:
                        logger.warning('Docente %s %s no encontrado' % (profesor_nombre, nombre_docente))
                if gauser_extra:
                    gep = Gauser_extra_programaciones.objects.get_or_create(ge=gauser_extra)
                    gep[0].especialidad = especialidad
                    try:
                        departamento = Departamento.objects.get(nombre__icontains=espec)
                        gep[0].departamento = departamento
                    except:
                        if not gep[0].departamento:
                            logger.warning('Docente %s sin departamento %s' % (nombre_docente, espec))
                        else:
                            logger.warning('Docente %s con departamento ya asignado' % (nombre_docente))

                    # if especialidades.count() == 1:
                    #     gep[0].especialidad = especialidades[0]
                    #     try:
                    #         departamento = Departamento.objects.get(nombre=espec)
                    #         gep[0].departamento = departamento
                    #     except:
                    #         logger.warning(u'Docente %s sin departamento %s' % (nombre_docente, espec))
                    # elif especialidades.count() == 0:
                    #     incidencias['especialidades'] = True
                    #     logger.warning(u'Docente %s sin especialidad %s' % (nombre_docente, espec))
                    #     crear_aviso(request, False, u'Es necesario asignar la especialidad %s a %s' % (espec, nombre_docente))
                    # else:
                    #     try:
                    #         departamento = Departamento.objects.get(nombre=espec)
                    #         gep[0].departamento = departamento
                    #     except:
                    #         logger.warning(u'Docente %s sin departamento %s' % (nombre_docente, espec))
                    #     incidencias['especialidades'] = True
                    #     logger.warning(u'Docente %s sin especialidad %s, existen coincidencias' % (nombre_docente, espec))
                    # incidencias['especialidades'] = True
                    gep[0].puesto = espec
                    gep[0].save()
    return True