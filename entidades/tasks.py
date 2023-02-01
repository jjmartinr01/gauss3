# -*- coding: utf-8 -*-
import logging
import unicodedata
import string
import xlrd
import os
from difflib import get_close_matches
from celery import shared_task
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils.timezone import timedelta, datetime, now
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils.encoding import smart_text

from cupo.models import PlantillaOrganica, PlantillaXLS
from estudios.models import Grupo, Gauser_extra_estudios, Materia, Matricula, Curso
from entidades.models import Subentidad, Cargo, Gauser_extra, CargaMasiva, Entidad, EntidadExtra, \
    EntidadExtraExpediente, EntidadExtraExpedienteOferta, Ronda, Menu, GE_extra_field, DocConfEntidad, Organization
from entidades.menus_entidades import Menus_Centro_Educativo, TiposCentro
from autenticar.models import Gauser, Permiso, Menu_default
from gauss.constantes import PROVINCIAS, CODE_CONTENEDOR, CARGOS_CENTROS
from bancos.views import asocia_banco_ge
from mensajes.models import Aviso
from gauss.funciones import pass_generator, genera_nie, borra_cargas_masivas_antiguas
from django.http import HttpResponse, JsonResponse

logger = logging.getLogger('django')


def devuelve_fecha(string):
    DATE_FORMATS = ['%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y']
    for date_format in DATE_FORMATS:
        try:
            fecha = datetime.strptime(string, date_format)
            return fecha
        except:
            pass
    return datetime.strptime('01/01/1900', '%d/%m/%Y')


def get_provincia(p):  # Devuelve el código de la provincia cuyo nombre se parece más a la string p
    n_ps = [n[1] for n in PROVINCIAS]
    try:
        m = get_close_matches(p, n_ps, 1)[0]
        for n in PROVINCIAS:
            if n[1] == m:
                return n[0]
        return None
    except:
        return None


# Crear el nombre de usuario a partir del nombre real
def crear_nombre_usuario(nombre, apellidos):
    # En primer lugar quitamos tildes, colocamos nombres en minúsculas y :
    nombre = ''.join(
        (c for c in unicodedata.normalize('NFD', smart_text(nombre)) if
         unicodedata.category(c) != 'Mn')).lower().split()
    apellidos = ''.join(
        (c for c in unicodedata.normalize('NFD', smart_text(apellidos)) if
         unicodedata.category(c) != 'Mn')).lower().split()
    iniciales_nombre = ''
    for parte in nombre:
        iniciales_nombre = iniciales_nombre + parte[0]
    try:
        iniciales_apellidos = apellidos[0]
    except:  # Estas dos líneas están para crear usuarios cuando no tienen apellidos
        iniciales_apellidos = 'sin'
    for ind in range(len(apellidos))[1:]:
        try:  # Por si acaso el usuario sólo tuviera un apellido:
            iniciales_apellidos = iniciales_apellidos + apellidos[ind][0]
        except IndexError:
            pass
    usuario = iniciales_nombre + iniciales_apellidos
    valid_usuario = False
    n = 1
    while valid_usuario == False:
        username = usuario + str(n)
        try:
            user = Gauser.objects.get(username=username)
            n += 1
        except:
            valid_usuario = True
    return username


# 'username_tutor2': '', 'username_tutor1': '', 'username': ''
def create_usuario(datos, ronda, tipo):
    dni = genera_nie(datos['dni' + tipo]) if len(datos['dni' + tipo]) > 6 else 'DNI inventado generar error en el try'
    # El siguiente nombre de usuario servirá para comprobar si el username es correcto o no:
    username_inventado = 'usuario_inventado_%s' % pass_generator()
    username = datos['username' + tipo] if len(datos['username' + tipo]) > 2 else username_inventado
    try:
        # if not tipo, implica que es un alumno/a
        if not tipo:
            try:
                # Los tutores no tienen id_socio o noidracima por eso tipo es la cadena vacía.
                gauser = Gauser.objects.get(educa_pk=datos['id_socio'])
            except:
                try:
                    # Es posible que existan usuarios alumnos con username y que todavía no tengan grabados
                    # el noidracima en educa_pk. La siguiente línea corrige esta situación.
                    gauser = Gauser.objects.get(username=username)
                    gauser.educa_pk = datos['id_socio']
                    gauser.save()
                except MultipleObjectsReturned:
                    return 'Múltiples gauser con el mismo username: %s' % username
        else:
            gauser = Gauser.objects.get(username=username)
    except:
        try:
            gauser = Gauser.objects.get(dni=dni)
            # if username != username_inventado:
            #     gauser.username = username
            # Si username es igual a username_inventado es porque Racima no ha generado un usuario,
            # por tanto, asignaremos uno que no tenga la estructura de Racima y evitar confusiones.
            gauser.username = username
            if not tipo:
                gauser.educa_pk = datos['id_socio']
            gauser.save()
            logger.info('Existe Gauser con dni %s' % dni)
        except ObjectDoesNotExist:
            logger.warning('No existe Gauser con dni %s' % dni)
            try:
                gauser_extra = Gauser_extra.objects.get(id_entidad=datos['id_socio'], ronda=ronda)
                gauser = gauser_extra.gauser
                # if username != username_inventado:
                #     gauser.username = username
                # Si username es igual a username_inventado es porque Racima no ha generado un usuario,
                # por tanto, asignaremos uno que no tenga la estructura de Racima y evitar confusiones.
                logger.warning('Encontrado Gauser y Gauser_extra con id_socio %s' % (datos['id_socio']))
                try:
                    gauser.username = username
                    gauser.dni = dni
                    if not tipo:
                        gauser.educa_pk = datos['id_socio']
                    gauser.save()
                except:
                    m1 = 'Encontrado Gauser y Gauser_extra con id_socio %s. ' % (datos['id_socio'])
                    m2 = 'Error username %s ya esta en uso y no puede volver a asignarse' % username
                    return m1 + m2

            except ObjectDoesNotExist:
                gauser = None
                logger.warning('No existe Gauser con id_socio %s' % (datos['id_socio']))
            except MultipleObjectsReturned:
                gauser_extra = Gauser_extra.objects.filter(id_entidad=datos['id_socio'], ronda=ronda)[0]
                logger.warning(
                    'Existen varios Gauser_extra asociados al Gauser encontrado. Se elige %s' % (gauser_extra))
                gauser = gauser_extra.gauser
                # if username != username_inventado:
                #     gauser.username = username
                # Si username es igual a username_inventado es porque Racima no ha generado un usuario,
                # por tanto, asignaremos uno que no tenga la estructura de Racima y evitar confusiones.
                try:
                    gauser.username = username
                    gauser.dni = dni
                    if not tipo:
                        gauser.educa_pk = datos['id_socio']
                    gauser.save()
                except:
                    m1 = 'Existen varios Gauser_extra asociados al Gauser encontrado. Se elige %s. ' % gauser_extra
                    m2 = 'Error username %s ya esta en uso y no puede volver a asignarse' % username
                    return m1 + m2
        except MultipleObjectsReturned:
            gauser = Gauser.objects.filter(dni=dni)[0]
            logger.warning('Existen varios Gauser con el mismo DNI. Se elige %s' % (gauser))
            # if username != username_inventado:
            #     gauser.username = username
            # Si username es igual a username_inventado es porque Racima no ha generado un usuario,
            # por tanto, asignaremos uno que no tenga la estructura de Racima y evitar confusiones.
            try:
                gauser.username = username
                if not tipo:
                    gauser.educa_pk = datos['id_socio']
                gauser.save()
            except:
                m1 = 'Existen varios Gauser con el mismo DNI. Se elige %s. ' % gauser
                m2 = 'Error username %s ya esta en uso y no puede volver a asignarse' % username
                return m1 + m2
    if gauser:
        try:
            gauser_extra = Gauser_extra.objects.get(gauser=gauser, ronda=ronda)
            mensaje = 'Existe el g_e %s con el dni %s. No se vuelve a crear fff.' % (gauser, dni)
            logger.info(mensaje)
        except ObjectDoesNotExist:
            gauser_extra = None
            logger.warning('No existe Gauser_extra asociado al Gauser %s, deberemos crearlo fff' % (gauser))
        except MultipleObjectsReturned:
            ges = Gauser_extra.objects.filter(gauser=gauser, ronda=ronda)
            gauser_extra = ges[0]
            ## Podríamos escribir ges.exclude(id=gauser_extra.id).delete(), pero como hay un error porque
            ## falta el nregistro en vut_vivienda necesito hacer esta triquiñuela para no duplicar usuarios:
            # for ge_borrar in ges.exclude(id=gauser_extra.id):
            # try:
            #     ge_borrar.delete()
            # except:
            #     entidad, c = Entidad.objects.get_or_create(code=CODE_CONTENEDOR)
            #     ge_borrar.ronda = entidad.ronda
            #     ge_borrar.save()
            #     logger.warning('Gauser_extra asociados al Gauser %s, desplazado al contenedor.' % (gauser))
            # logger.warning('Varios Gauser_extra asociados al Gauser %s, se borran todos menos uno.' % (gauser))
            # mensaje = 'Varios Gauser_extra asociados al Gauser %s, se borran todos menos uno.' % (gauser)
            # logger.info(mensaje)
            error = 'Varios Gauser_extra asociados al Gauser: %s.<br>' % gauser
            for ge in ges:
                error += 'Gauser_extra: %s<br>' % ge
            return error
    else:
        gauser_extra = None

    if not gauser:
        if datos['nombre' + tipo] and datos['apellidos' + tipo]:
            nombre = datos['nombre' + tipo]
            apellidos = datos['apellidos' + tipo]
            # if username == username_inventado:
            #     username = crear_nombre_usuario(nombre, apellidos)
            dni = genera_nie(datos['dni' + tipo])
            gauser = Gauser.objects.create_user(username, email=datos['email' + tipo].lower(),
                                                password=pass_generator(), last_login=now())
            gauser.first_name = string.capwords(nombre.title()[0:28])
            gauser.last_name = string.capwords(apellidos.title()[0:28])
            gdata = {'dni': dni, 'telfij': datos['telefono_fijo' + tipo], 'sexo': datos['sexo' + tipo],
                     'telmov': datos['telefono_movil' + tipo], 'localidad': datos['localidad' + tipo],
                     'address': datos['direccion' + tipo], 'provincia': get_provincia(datos['provincia' + tipo]),
                     'nacimiento': devuelve_fecha(datos['nacimiento' + tipo]), 'postalcode': datos['cp' + tipo],
                     'fecha_alta': devuelve_fecha(datos['fecha_alta' + tipo])}
            for key, value in gdata.items():
                setattr(gauser, key, value)
            if not tipo:
                gauser.educa_pk = datos['id_socio']
            gauser.save()
        else:
            mensaje = 'No se ha podido crear un usuario porque no se han indicado nombre y apellidos'
            logger.warning(mensaje)
    if gauser and not gauser_extra:
        if 'id_organizacion' + tipo in datos:
            id_organizacion = datos['id_organizacion' + tipo]
        else:
            id_organizacion = datos['id_socio' + tipo]
        gauser_extra = Gauser_extra.objects.create(gauser=gauser, ronda=ronda, activo=True,
                                                   id_entidad=datos['id_socio' + tipo],
                                                   num_cuenta_bancaria=datos['iban' + tipo],
                                                   observaciones=datos['observaciones' + tipo],
                                                   id_organizacion=id_organizacion)
        try:
            asocia_banco_ge(gauser_extra)
        except:
            try:
                mensaje = 'El IBAN asociado a %s parece no ser correcto. No se ha podido asociar una entidad bancaria al mismo.' % (
                        gauser.first_name + ' ' + gauser.last_name)
            except:
                mensaje = 'El IBAN asociado a %s parece no ser correcto. No se ha podido asociar una entidad bancaria al mismo.' % (
                    'DESCONOCIDO')
            logger.info(mensaje)
    if gauser_extra:
        # logger.info('antes de subentidades')
        # if datos['subentidades' + tipo]:
        #     logger.info('entra en subentidades')
        #    # La siguientes dos líneas no se si funcionarán en python3 debido a que filter en python3 no devuelve
        #    # una lista. Incluida la conversión list() para evitar errores:
        #    # http://stackoverflow.com/questions/3845423/remove-empty-strings-from-a-list-of-strings
        #     subentidades_id = list(filter(None, datos['subentidades' + tipo].replace(' ', '').split(',')))
        #     logger.info('entra en subentidades %s' % subentidades_id)
        #     subentidades = Subentidad.objects.filter(id__in=subentidades_id, entidad=ronda.entidad,
        #                                              fecha_expira__gt=datetime.today())
        #     gauser_extra.subentidades.add(*subentidades)
        if datos['perfiles' + tipo]:
            logger.info('entra en perfiles')
            cargos_id = list(filter(None, datos['perfiles' + tipo].replace(' ', '').split(',')))
            cargos = Cargo.objects.filter(id__in=cargos_id, entidad=ronda.entidad)
            gauser_extra.cargos.add(*cargos)

    if gauser_extra:
        Gauser_extra_estudios.objects.get_or_create(ge=gauser_extra)
    return gauser_extra


def carga_masiva_alumnos(carga, entidad):
    entidad_inicial = entidad
    entidades = []
    f = carga.fichero.read()
    book = xlrd.open_workbook(file_contents=f)
    sheet = book.sheet_by_index(0)
    # Get the keys from line 5 of excel file:
    keys = [slugify(sheet.cell(4, col_index).value) for col_index in range(sheet.ncols)]
    key_columns = {col_index: slugify(sheet.cell(4, col_index).value) for col_index in range(sheet.ncols)}

    if int(sheet.ncols) == 55:  # Asegurar que el archivo tiene las columnas requeridas
        carga.log += '<p>Carga de alumnos. %s</p>' % carga.tipo
        # Un ejemplo de key_columns es:
        # {0: 'estado-matricula', 1: 'direccion', 2: 'codigo-postal', 3: 'localidad-de-residencia',
        # 4: 'provincia-de-residencia', 5: 'alumno', 6: 'telefono', 7: 'telefono-movil', 8: 'correo-electronico',
        # 9: 'noidracima', 10: 'grupo', 11: 'bilingue', 12: 'dnipasaporte-primer-tutor', 13: 'no-expte-en-el-centro',
        # 14: 'primer-apellido-primer-tutor', 15: 'segundo-apellido-primer-tutor', 16: 'nombre-primer-tutor',
        # 17: 'no-historial-academico', 18: 'tfno-primer-tutor', 19: 'tfno-movil-primer-tutor', 20: 'sexo-primer-tutor',
        # 21: 'dnipasaporte-segundo-tutor', 22: 'dnipasaporte', 23: 'primer-apellido-segundo-tutor',
        # 24: 'segundo-apellido-segundo-tutor', 25: 'nombre-segundo-tutor', 26: 'tfno-segundo-tutor',
        # 27: 'tfno-movil-segundo-tutor', 28: 'sexo-segundo-tutor', 29: 'localidad-de-nacimiento', 30: 'centro',
        # 31: 'codigo-pais-nacimiento', 32: 'pais-de-nacimiento', 33: 'codigo-provincia-nacimiento',
        # 34: 'pago-seguro-escolar', 35: 'nacionalidad', 36: 'no-de-matriculas-en-este-curso', 37: 'curso',
        # 38: 'observaciones-de-la-matricula', 39: 'numero-ss', 40: 'no-de-matriculas-expediente',
        # 41: 'repeticiones-en-el-curso', 42: 'familia-numerosa', 43: 'ano-de-la-matricula', 44: 'primer-apellido',
        # 45: 'segundo-apellido', 46: 'nombre', 47: 'fecha-de-la-matricula', 48: 'sexo', 49: 'fecha-de-nacimiento',
        # 50: 'usuario-alumnado', 51: 'usuario-primer-tutor', 52: 'usuario-segundo-tutor', 53: 'x_unidad',
        # 54: 'x_ofertamatrig'}
        # La relación entre los campos (slugified) de la hoja Excel con los de Gauss viene dada por kra:
        kra = {
            'estado-matricula': 'estado_matricula', 'direccion': 'direccion', 'codigo-postal': 'cp',
            'localidad-de-residencia': 'localidad', 'provincia-de-residencia': 'provincia', 'alumno': 'alumno',
            'telefono': 'telefono_fijo', 'telefono-movil': 'telefono_movil', 'correo-electronico': 'email',
            'noidracima': 'id_socio', 'grupo': 'grupo', 'bilingue': 'bilingue',
            'dnipasaporte-primer-tutor': 'dni_tutor1', 'no-expte-en-el-centro': 'num_exp',
            'primer-apellido-primer-tutor': 'last_name1_tutor1', 'segundo-apellido-primer-tutor': 'last_name2_tutor1',
            'nombre-primer-tutor': 'nombre_tutor1', 'no-historial-academico': 'id_organizacion',
            'tfno-primer-tutor': 'telefono_fijo_tutor1', 'tfno-movil-primer-tutor': 'telefono_movil_tutor1',
            'sexo-primer-tutor': 'sexo_tutor1', 'dnipasaporte-segundo-tutor': 'dni_tutor2', 'dnipasaporte': 'dni',
            'primer-apellido-segundo-tutor': 'last_name1_tutor2', 'segundo-apellido-segundo-tutor': 'last_name2_tutor2',
            'nombre-segundo-tutor': 'nombre_tutor2', 'tfno-segundo-tutor': 'telefono_fijo_tutor2',
            'tfno-movil-segundo-tutor': 'telefono_movil_tutor2', 'sexo-segundo-tutor': 'sexo_tutor2',
            'localidad-de-nacimiento': 'localidad_nacimiento', 'centro': 'centro',
            'codigo-pais-nacimiento': 'code_pais_nacimiento', 'pais-de-nacimiento': 'pais_nacimiento',
            'codigo-provincia-nacimiento': 'code_provincia_nacimiento', 'pago-seguro-escolar': 'pago_seguro_escolar',
            'nacionalidad': 'nacionalidad', 'no-de-matriculas-en-este-curso': 'num_matriculas', 'curso': 'curso',
            'observaciones-de-la-matricula': 'observaciones_matricula', 'numero-ss': 'num_ss',
            'no-de-matriculas-expediente': 'num_matriculas_exp', 'repeticiones-en-el-curso': 'rep_curso',
            'familia-numerosa': 'familia_numerosa', 'ano-de-la-matricula': 'year_matricula',
            'primer-apellido': 'last_name1', 'segundo-apellido': 'last_name2', 'nombre': 'nombre',
            'fecha-de-la-matricula': 'fecha_matricula', 'sexo': 'sexo', 'fecha-de-nacimiento': 'nacimiento',
            'usuario-alumnado': 'username', 'usuario-primer-tutor': 'username_tutor1',
            'usuario-segundo-tutor': 'username_tutor2', 'x_unidad': 'x_unidad', 'x_ofertamatrig': 'x_curso'}
        for row_index in range(5, sheet.nrows):
            d = {'alumno': '', 'estado_matricula': '', 'id_socio': '', 'dni': '', 'direccion': '', 'cp': '',
                 'localidad': '', 'nacimiento': '', 'provincia': '', 'telefono_fijo': '', 'telefono_movil': '',
                 'email': '', 'curso': '', 'id_organizacion': '', 'subentidades': '', 'last_name1': '',
                 'last_name2': '', 'nombre': '', 'dni_tutor1': '', 'last_name1_tutor1': '',
                 'last_name2_tutor1': '', 'nombre_tutor1': '', 'telefono_fijo_tutor1': '', 'fecha_alta': '',
                 'telefono_movil_tutor1': '', 'sexo_tutor1': '', 'dni_tutor2': '', 'last_name1_tutor2': '',
                 'last_name2_tutor2': '', 'nombre_tutor2': '', 'telefono_fijo_tutor2': '', 'perfiles': '',
                 'telefono_movil_tutor2': '', 'sexo_tutor2': '', 'localidad_nacimiento': '', 'nacionalidad': '',
                 'code_pais_nacimiento': '', 'pais_nacimiento': '', 'code_provincia_nacimiento': '',
                 'pago_seguro_escolar': '', 'sexo': '', 'year_matricula': '', 'num_matriculas': '',
                 'observaciones_matricula': '', 'num_ss': '', 'num_exp': '', 'fecha_matricula': '',
                 'num_matriculas_exp': '', 'rep_curso': '', 'familia_numerosa': '', 'lengua_materna': '',
                 'year_incorporacion': '', 'bilingue': '', 'email_tutor1': '', 'email_tutor2': '', 'iban': '',
                 'localidad_tutor1': '', 'localidad_tutor2': '', 'direccion_tutor1': '', 'direccion_tutor2': '',
                 'cp_tutor1': '', 'cp_tutor2': '', 'nacimiento_tutor1': '', 'nacimiento_tutor2': '',
                 'provincia_tutor1': '', 'provincia_tutor2': '', 'iban_tutor1': '', 'iban_tutor2': '',
                 'id_socio_tutor1': '', 'id_socio_tutor2': '', 'fecha_alta_tutor1': '', 'fecha_alta_tutor2': '',
                 'observaciones_tutor1': '', 'observaciones_tutor2': '', 'perfiles_tutor1': '', 'perfiles_tutor2': '',
                 'username_tutor2': '', 'username_tutor1': '', 'username': '', 'grupo': '', 'x_unidad': '',
                 'x_curso': '', 'centro': ''}
            for col_index in range(sheet.ncols):
                try:
                    d[kra[key_columns[col_index]]] = sheet.cell(row_index, col_index).value
                except Exception as msg:
                    carga.log += '<p>Lectura columnas: %s</p>' % str(msg)
                    carga.save()
            try:
                entidad_archivo = Entidad.objects.get(code=d['centro'].replace(')', '').split(sep='(')[1])
                if entidad_inicial:
                    if entidad != entidad_archivo:
                        carga.log += 'La entidad de carga y la información del archivo no coinciden.'
                        carga.cargado = True
                        carga.save()
                        return False
                if entidad_archivo not in entidades:
                    entidades.append(entidad_archivo)
                    carga.log += 'Se carga archivo para: %s.' % entidad_archivo.name
                    carga.save()
                entidad = entidad_archivo
                ronda = entidad.ronda
                try:
                    cargoa = Cargo.objects.get(entidad=entidad, borrable=False, clave_cargo='g_alumno')
                except:
                    cargoa = Cargo.objects.create(cargo='Alumno/a', entidad=entidad, borrable=False,
                                                  clave_cargo='g_alumno')
                    carga.log += '<p>Crear cargo g_alumno - %s</p>' % ronda
                    carga.save()
                try:
                    cargop = Cargo.objects.get(entidad=entidad, borrable=False, clave_cargo='g_madre_padre')
                except:
                    cargop = Cargo.objects.create(cargo='Madre/Padre/Tutor/a legal', entidad=entidad,
                                                  borrable=False, clave_cargo='g_madre_padre')
                    carga.log += '<p>Crear cargo g_madre_padre - %s</p>' % ronda
                    carga.save()
                try:
                    # Al leer el 'id' como string devuelve, por ejemplo, 2936.0 en lugar de 2936. Eliminar '.0' :
                    x_curso = str(d['x_curso']).split('.')[0]
                except:
                    x_curso = ''
                    carga.log += '<p>x_curso: %s - %s</p>' % (d['x_curso'], ronda)
                    carga.save()
                try:
                    curso = Curso.objects.get(ronda=ronda, clave_ex=x_curso)
                except Exception as msg:
                    carga.log += '<p>Error: %s</p>' % str(msg)
                    cursos = Curso.objects.filter(ronda=ronda, clave_ex=x_curso)
                    if cursos.count() > 0:
                        carga.log += '<p>cursos iguales (%s): %s - %s</p>' % (cursos.count(), d['x_curso'], ronda)
                        carga.save()
                        curso = cursos[0]
                    else:
                        curso = Curso.objects.create(clave_ex=x_curso, ronda=ronda)
                        logger.info('Carga masiva xls. Se crea curso %s' % curso.clave_ex)
                        carga.log += '<br>Carga masiva xls. Se crea curso %s' % curso.clave_ex
                        carga.save()
                curso.nombre = d['curso']
                curso.save()
                try:
                    x_unidad = str(d['x_unidad']).split('.')[0]
                except:
                    x_unidad = ''
                    carga.log += '<p>x_unidad: %s - %s</p>' % (d['x_unidad'], ronda)
                    carga.save()
                try:
                    grupo = Grupo.objects.get(ronda=ronda, clave_ex=x_unidad)
                except Exception as msg:
                    grupos = Grupo.objects.filter(ronda=ronda, clave_ex=x_unidad)
                    if grupos.count() > 0:
                        carga.log += '<p>grupos iguales (%s): %s - %s</p>' % (grupos.count(), d['x_unidad'], ronda)
                        carga.save()
                        grupo = grupos[0]
                    else:
                        grupo = Grupo.objects.create(ronda=ronda, clave_ex=x_unidad)
                        logger.info('Carga masiva xls. Se crea grupo %s-%s' % (grupo.clave_ex, d['grupo']))
                        carga.log += '<br>Se crea grupo %s (%s) - Curso: %s (%s)' % (d[grupo], grupo.clave_ex,
                                                                                     curso.nombre, curso.clave_ex)
                        carga.save()
                grupo.nombre = d['grupo']
                grupo.save()
                grupo.cursos.add(curso)
                # Definición de los datos que permiten definir los usuarios:
                d['apellidos'] = '%s %s' % (d['last_name1'], d['last_name2'])
                d['apellidos_tutor1'] = '%s %s' % (d['last_name1_tutor1'], d['last_name2_tutor1'])
                d['apellidos_tutor2'] = '%s %s' % (d['last_name1_tutor2'], d['last_name2_tutor2'])
                d['activo'] = True
                d['observaciones'] = '<b>Localidad de nacimiento:</b> %s<br><b>Nacionalidad:</b> %s<br>' \
                                     '<b>Código del país de nacimiento:</b> %s<br><b>País de nacimiento:</b> %s<br>' \
                                     '<b>Código de la provincia de nacimiento:</b> %s<br><b>Ha pagado el seguro escolar:</b> %s<br>' \
                                     '<b>Año de la matrícula:</b> %s<br><b>Número de matrículas en este curso:</b> %s<br>' \
                                     '<b>Observaciones de la matrícula:</b> %s<br><b>Número de SS:</b> %s<br>' \
                                     '<b>Nº de expediente en el centro:</b> %s<br><b>Fecha de matrícula:</b> %s<br>' \
                                     '<b>Nº de matrículas en el expediente:</b> %s<br><b>Repeticiones en el curso:</b> %s<br>' \
                                     '<b>Familia numerosa:</b> %s<br><b>Lengua materna:</b> %s<br><b>Año de incorporación al sistema educativo:</b> %s<br>' % (
                                         d['localidad_nacimiento'], d['nacionalidad'],
                                         d['code_pais_nacimiento'],
                                         d['pais_nacimiento'], d['code_provincia_nacimiento'],
                                         d['pago_seguro_escolar'], d['year_matricula'], d['num_matriculas'],
                                         d['observaciones_matricula'],
                                         d['num_ss'], d['num_exp'], d['fecha_matricula'],
                                         d['num_matriculas_exp'],
                                         d['rep_curso'], d['familia_numerosa'], d['lengua_materna'],
                                         d['year_incorporacion'])
                gauser_extra = create_usuario(d, ronda, '')
                if type(gauser_extra) == Gauser_extra:
                    tutor1 = create_usuario(d, ronda, '_tutor1')
                    if type(tutor1) == Gauser_extra:
                        tutor1.cargos.add(cargop)
                        tutor1.save()
                        gauser_extra.tutor1 = tutor1
                    elif type(tutor1) == str:
                        carga.log += '<p>%s</p>' % tutor1
                        carga.save()
                    tutor2 = create_usuario(d, ronda, '_tutor2')
                    if type(tutor2) == Gauser_extra:
                        tutor2.cargos.add(cargop)
                        tutor2.save()
                        gauser_extra.tutor2 = tutor2
                    elif type(tutor2) == str:
                        carga.log += '<p>%s</p>' % tutor2
                        carga.save()
                    gauser_extra.cargos.add(cargoa)
                    gauser_extra.save()
                    gauser_extra.gauser_extra_estudios.grupo = grupo
                    gauser_extra.gauser_extra_estudios.save()
                elif type(gauser_extra) == str:
                    carga.log += '<p>%s</p>' % gauser_extra
                    carga.save()
            except Exception as msg:
                carga.log += '<p>%s<br>Los datos que han generado el error: %s</p>' % (str(msg), str(d))
                carga.save()
    else:
        carga.log += '<p>Error. El número de columnas (%s) no es el requerido.</p>' % int(sheet.ncols)
    carga.cargado = True
    carga.save()
    return True


def carga_masiva_personal(carga, entidad):
    centros_cargados = []
    docentes_cargados = {}
    carga.log += '<p>Comienza carga de docentes</p>'
    errores = {}
    f = carga.fichero.read()
    book = xlrd.open_workbook(file_contents=f)
    sheet = book.sheet_by_index(0)
    # Get the keys from line 5 of excel file:
    dict_names = {}
    for col_index in range(sheet.ncols):
        dict_names[sheet.cell(4, col_index).value] = col_index
    for row_index in range(5, sheet.nrows):
        try:
            code_entidad = int(sheet.cell(row_index, dict_names['Código']).value)
            entidad_archivo = Entidad.objects.get(code=code_entidad)
            if entidad:
                if entidad != entidad_archivo:
                    carga.cargado = True
                    carga.log += '<p>Se interrumpe la carga porque no corresponde al centro educativo.</p>'
                    carga.save()
                    return False
            entidad = entidad_archivo
            if code_entidad not in centros_cargados:
                centros_cargados.append(code_entidad)
            if code_entidad not in docentes_cargados:
                docentes_cargados[code_entidad] = []
            try:
                cargo_d = Cargo.objects.get(entidad=entidad, clave_cargo='g_docente', borrable=False)
            except:
                cargo_d = Cargo.objects.create(entidad=entidad, clave_cargo='g_docente', borrable=False,
                                               cargo='Docente')
            try:
                cargo_nd = Cargo.objects.get(entidad=entidad, clave_cargo='g_nodocente', borrable=False)
            except:
                cargo_nd = Cargo.objects.create(entidad=entidad, clave_cargo='g_nodocente', borrable=False,
                                                cargo='No docente')
            dni = genera_nie(str(sheet.cell(row_index, dict_names['DNI']).value))
            nombre = sheet.cell(row_index, dict_names['Nombre docente']).value
            apellidos = sheet.cell(row_index, dict_names['Apellidos docente']).value
            email = sheet.cell(row_index, dict_names['Correo-e']).value
            username = sheet.cell(row_index, dict_names['Usuario']).value
            clave_ex = str(sheet.cell(row_index, dict_names['X_DOCENTE']).value).strip().split('.')[0]
            puesto = str(sheet.cell(row_index, dict_names['Puesto']).value).strip()
            jornada_contratada = str(sheet.cell(row_index, dict_names['Jornada contratada']).value).strip()
            tipo_personal = str(sheet.cell(row_index, dict_names['Tipo personal']).value).strip()
            if 'No Docente' in tipo_personal:
                cargo = cargo_nd
            else:
                cargo = cargo_d
            try:
                try:
                    gauser = Gauser.objects.get(username=username)
                    gauser.dni = dni
                    gauser.email = email
                    gauser.first_name = nombre
                    gauser.last_name = apellidos[:30]
                    gauser.save()
                except Exception as msg:
                    carga.log += '<p>Error get Gauser por username: %s</p>\n' % (msg)
                    carga.save()
                    gauser = Gauser.objects.get(dni=dni)
                    gauser.email = email
                    gauser.username = username
                    gauser.first_name = nombre
                    gauser.last_name = apellidos
                    gauser.save()
                    carga.log += '<p>Se busca usuario %s por dni: %s</p>\n' % (username, dni)
                    carga.save()
            except:
                carga.log += '<p>Se intenta crear usuario con username: %s</p>\n' % username
                carga.save()
                gauser = Gauser.objects.create_user(username, email=email, last_login=now(), dni=dni,
                                                    password=pass_generator(size=9),
                                                    first_name=nombre, last_name=apellidos)
            gauser_extra, c = Gauser_extra.objects.get_or_create(ronda=entidad.ronda, gauser=gauser)
            gauser_extra.clave_ex = clave_ex
            gauser_extra.id_organizacion = clave_ex
            gauser_extra.activo = True
            gauser_extra.puesto = puesto
            gauser_extra.tipo_personal = tipo_personal
            gauser_extra.jornada_contratada = jornada_contratada
            gauser_extra.cargos.add(cargo)
            gauser_extra.save()
            docentes_cargados[code_entidad].append(clave_ex)
            # carga.log += '<p>Carga de %s - %s - %s</p>\n' % (username, dni, gauser_extra.id_organizacion)
            direc_apellidos, direc_nombre = entidad.entidadextra.director.split(', ')
            if gauser_extra.gauser.first_name == direc_nombre and gauser_extra.gauser.last_name == direc_apellidos:
                try:
                    cargo_director = Cargo.objects.get(entidad=entidad, clave_cargo='g_director_centro')
                except:
                    cargo_director = Cargo.objects.create(entidad=entidad, clave_cargo='g_director_centro',
                                                          borrable=False, cargo='Director/a')
                gauser_extra.cargos.add(cargo_director)
            if entidad.entidadextra.depende_de:
                nueva_entidad = entidad.entidadextra.depende_de
                carga.log += '<p>Entidad depende de: %s</p>' % (nueva_entidad)
                gauser_extra, c = Gauser_extra.objects.get_or_create(ronda=nueva_entidad.ronda, gauser=gauser)
                gauser_extra.clave_ex = 's-%s' % clave_ex
                gauser_extra.id_organizacion = 's-%s' % clave_ex
                gauser_extra.activo = True
                gauser_extra.puesto = puesto
                gauser_extra.tipo_personal = tipo_personal
                gauser_extra.jornada_contratada = jornada_contratada
                try:
                    cargo_docente = Cargo.objects.get(entidad=nueva_entidad, clave_cargo='g_docente', borrable=False)
                except:
                    cargo_docente = Cargo.objects.create(entidad=nueva_entidad, clave_cargo='g_docente', borrable=False,
                                                         cargo='Docente')
                gauser_extra.cargos.add(cargo_docente)
                gauser_extra.save()
                carga.log += '<p>Carga de %s - %s - s-%s</p>' % (username, dni, gauser_extra.id_organizacion)
                carga.save()
        except Exception as msg:
            apellidos = slugify(sheet.cell(row_index, dict_names['Apellidos docente']).value)
            errores[row_index] = {'error': str(msg), 'apellidos': apellidos}
            logger.info('Error carga general docentes %s -- %s' % (str(apellidos), msg))
            carga.log += '<p>Error carga general docentes %s -- %s</p>' % (str(apellidos), msg)
            carga.save()
    # Líneas de código para eliminar usuarios que no están en el archivo de carga:
    for centro_cargado in centros_cargados:
        entidad = Entidad.objects.get(code=centro_cargado)
        carga.log += '<p><b>%s</b></p>' % entidad
        carga.log += '<p>Lista: %s</p>' % ', '.join(docentes_cargados[entidad.code])
        cargo_d = Cargo.objects.get(entidad=entidad, clave_cargo='g_docente', borrable=False)
        cargo_nd = Cargo.objects.get(entidad=entidad, clave_cargo='g_nodocente', borrable=False)
        usuarios_activos = Gauser_extra.objects.filter(activo=True, cargos__in=[cargo_nd, cargo_d],
                                                       ronda=entidad.ronda)
        # Si se carga a un solo usuario implicaría la desactivación del resto. Por esta razón:
        # Evitamos que se desactiven usuarios:
        usuarios_activos = []
        for usuario_activo in usuarios_activos:
            if usuario_activo.clave_ex not in docentes_cargados[entidad.code]:
                # Puede que existan usuarios activos correctamente por pertenecer a una sección
                # Estos usuarios tienen una clave_ex que comienza por s-
                try:
                    if usuario_activo.clave_ex:
                        if 's-' not in usuario_activo.clave_ex:
                            usuario_activo.activo = False
                            usuario_activo.save()
                            carga.log += '<p>Desactivado usuario: %s con clave_ex: </p>\n' % (usuario_activo, clave_ex)
                    else:
                        usuario_activo.activo = False
                        usuario_activo.save()
                        carga.log += '<p>Desactivado usuario: %s, clave_ex: None</p>\n' % (usuario_activo)
                except Exception as msg:
                    carga.log += '<p>Error al desactivar a: %s - %s</p>\n' % (usuario_activo, str(msg))
    carga.cargado = True
    carga.save()
    return True


def carga_masiva_datos_centros(carga):
    gauss = Gauser.objects.get(username='gauss')
    f = carga.fichero.read()
    book = xlrd.open_workbook(file_contents=f)
    sheet = book.sheet_by_index(0)
    # Get the keys from line 5 of 'excel' file:
    dict_names = {}
    for col_index in range(sheet.ncols):
        dict_names[sheet.cell(4, col_index).value] = col_index
    entidades_creadas = []
    for row_index in range(5, sheet.nrows):
        code_entidad = int(sheet.cell(row_index, dict_names['Código']).value)
        # entidad, created = Entidad.objects.get_or_create(code=code_entidad)
        try:
            entidad = Entidad.objects.get(code=code_entidad)
        except:
            entidades = Entidad.objects.filter(code=code_entidad)
            if entidades.count() > 1:
                aviso = 'carga_centros12: Múltiples entidades con código %s' % str(code_entidad)
                carga.log = aviso
                Aviso.objects.create(usuario=carga.g_e, aviso=aviso, fecha=now())
                entidad = entidades[0]
                for e in entidades:
                    e.name = 'Entidad múltiple'
                    e.save()
            else:
                entidad = Entidad.objects.create(code=code_entidad)
                carga.log = 'Se crea entidad: %s<br>' % entidad
            carga.save()
        if entidad not in entidades_creadas:
            entidades_creadas.append(entidad)
            carga.log += '<hr><br>Se procesa: %s' % entidad
            entidad.name = sheet.cell(row_index, dict_names['Centro']).value
            entidad.organization = carga.g_e.ronda.entidad.organization
            entidad.address = sheet.cell(row_index, dict_names['Dirección postal']).value
            entidad.localidad = sheet.cell(row_index, dict_names['Localidad']).value
            entidad.provincia = carga.g_e.ronda.entidad.provincia
            entidad.postalcode = sheet.cell(row_index, dict_names['CP']).value
            entidad.tel = sheet.cell(row_index, dict_names['Teléfono']).value
            entidad.fax = sheet.cell(row_index, dict_names['FAX']).value
            entidad.mail = sheet.cell(row_index, dict_names['Correo-e']).value
            entidad.save()
            # Creación de cargos no borrables y asignación de inspectores a centros:
            mensaje = ejecutar_configurar_cargos_permisos_entidad(entidad)
            carga.log += '<br>%s' % mensaje
            carga.save()
            if entidad.ronda:  # Si existe una ronda, capturamos los g_es con perfiles de dirección
                q = Q(clave_cargo='g_miembro_equipo_directivo') | Q(clave_cargo='g_jefe_estudios') | Q(
                    clave_cargo='g_director_centro') | Q(clave_cargo='g_nodocente')
                cargos = Cargo.objects.filter(q, Q(entidad=entidad))
                g_es = Gauser_extra.objects.filter(ronda=entidad.ronda, cargos__in=cargos, activo=True)
            else:
                g_es = Gauser_extra.objects.none()
            if not entidad.ronda or entidad.ronda.fin < datetime.today().date():
                y1, y2 = datetime.today().year, datetime.today().year + 1
                inicio = datetime.strptime("1/9/%s" % y1, "%d/%m/%Y")
                fin = datetime.strptime("31/8/%s" % y2, "%d/%m/%Y")
                ronda, c = Ronda.objects.get_or_create(nombre="%s/%s" % (y1, y2), entidad=entidad, inicio=inicio,
                                                       fin=fin)
                carga.log = 'Se crea una nueva ronda: %s<br>' % ronda
                carga.save()
                entidad.ronda = ronda
                entidad.save()
                # Cargamos los usuarios capturados antes en la nueva ronda (miembros del equipo directivo):
                for g__e in g_es:
                    try:
                        Gauser_extra.objects.get(gauser=g__e.gauser, ronda=ronda)
                    except:
                        new_user = Gauser_extra.objects.create(gauser=g__e.gauser,
                                                               ronda=ronda,
                                                               id_entidad=g__e.id_entidad,
                                                               id_organizacion=g__e.id_organizacion,
                                                               alias=g__e.alias, activo=True,
                                                               observaciones=g__e.observaciones,
                                                               foto=g__e.foto,
                                                               tutor1=None, tutor2=None,
                                                               ocupacion=g__e.ocupacion,
                                                               num_cuenta_bancaria=g__e.num_cuenta_bancaria)
                        new_user.subentidades.add(*g__e.subentidades.all())
                        new_user.subsubentidades.add(*g__e.subsubentidades.all())
                        new_user.cargos.add(*g__e.cargos.all())
                        new_user.permisos.add(*g__e.permisos.all())
                        carga.log = 'Se crea un nuevo usuario para la ronda: %s' % new_user
                        carga.save()
                # Crear usuario gauss para la entidad:
                ge, c = Gauser_extra.objects.get_or_create(gauser=gauss, ronda=entidad.ronda, activo=True)
                if c:
                    permisos = Permiso.objects.all()
                    ge.permisos.add(*permisos)
                # Crear el usuario entidad:
                try:
                    gauser_entidad = Gauser.objects.get(username=entidad.code)
                except Exception as msg:
                    email = 'inventado@%s.com' % entidad.code
                    gauser_entidad = Gauser.objects.create_user(entidad.code, email, str(entidad.code),
                                                                last_login=now())
                    carga.log = 'Se crea el usuario de la entidad: %s<br>' % gauser_entidad
                    carga.save()
                    Aviso.objects.create(usuario=carga.g_e, aviso='carga_centros4: %s' % str(msg), fecha=now())
                try:
                    Gauser_extra.objects.get(gauser=gauser_entidad, ronda=entidad.ronda)
                except Exception as msg:
                    g_e_entidad = Gauser_extra.objects.create(gauser=gauser_entidad, ronda=entidad.ronda,
                                                              activo=True)
                    cargo_director, c = Cargo.objects.get_or_create(entidad=entidad,
                                                                    clave_cargo='g_director_centro')
                    g_e_entidad.permisos.add(*cargo_director.permisos.all())
                    carga.log = 'Se dan al usuario de la entidad (%s), los permisos del director<br>' % g_e_entidad
                    carga.save()
            # Menus:
            carga.log += '<br>Comienza carga de menús'
            carga.save()
            for m in Menus_Centro_Educativo:
                try:
                    md = Menu_default.objects.get(code_menu=m[0])
                    try:
                        Menu.objects.get(entidad=entidad, menu_default=md)
                    except:
                        Menu.objects.create(entidad=entidad, menu_default=md, texto_menu=m[1], pos=m[2])
                except Exception as msg:
                    Aviso.objects.create(usuario=carga.g_e, aviso='carga_centros2: %s' % str(msg), fecha=now())
                    carga.log = 'Se produce un error (carga_centros2): %s' % str(msg)
                    carga.save()
            ee, created = EntidadExtra.objects.get_or_create(entidad=entidad)
            ee.titularidad = sheet.cell(row_index, dict_names['Titularidad']).value
            ee.tipo_centro = sheet.cell(row_index, dict_names['Tipo centro']).value
            try:
                code_entidad_padre = int(sheet.cell(row_index, dict_names['IES del que depende']).value)
                ee.depende_de = Entidad.objects.get(code=code_entidad_padre)
            except Exception as msg:
                ee.depende_de = None
            if 'S' in sheet.cell(row_index, dict_names['Servicio comedor']).value:
                ee.comedor = True
            else:
                ee.comedor = False
            if 'S' in sheet.cell(row_index, dict_names['Transporte escolar']).value:
                ee.transporte = True
            else:
                ee.transporte = False
            ee.director = sheet.cell(row_index, dict_names['Dirección']).value
            ee.save()
        expediente = sheet.cell(row_index, dict_names['Expediente']).value
        eee, created = EntidadExtraExpediente.objects.get_or_create(eextra=ee, expediente=expediente)
        oferta = sheet.cell(row_index, dict_names['Oferta']).value
        EntidadExtraExpedienteOferta.objects.get_or_create(eeexpediente=eee, oferta=oferta)
    return True


def carga_masiva_horario_personal_centro(carga):
    try:
        f = carga.fichero.read()
        book = xlrd.open_workbook(file_contents=f)
        sheet = book.sheet_by_index(0)
        po = PlantillaOrganica.objects.create(g_e=carga.g_e)
        carga.log += 'Se crea Plantilla Orgánica por %s<br>' % po.g_e
        carga.save()
    except Exception as msg:
        carga.log += 'Error y parada de carga: %s' % str(msg)
        carga.save()
        return False
    keys = {"CENTRO": "centro", "DOCENTE": "docente", "X_DOCENTE": "x_docente", "DEPARTAMENTO": "departamento",
            "X_DEPARTAMENTO": "x_departamento", "FECHA INICIO": "fecha_inicio", "FECHA FIN": "fecha_fin",
            "DÍA": "dia", "HORA INICIO": "hora_inicio", "AÑO": "year",
            "HORA FIN": "hora_fin", "HORA INICIO CADENA": "hora_inicio_cadena",
            "HORA FIN CADENA": "hora_fin_cadena", "X_ACTIVIDAD": "x_actividad", "Localidad Unidad": 'localidad',
            "ACTIVIDAD": "actividad", "L_REQUNIDAD": "l_requnidad", "DOCENCIA": "docencia",
            "MINUTOS": "minutos", "X_DEPENDENCIA": "x_dependencia", "X_OFERTAMATRIG": "x_curso",
            "C_CODDEP": "c_coddep", "X_DEPENDENCIA2": "x_dependencia2", "C_CODDEP2": "c_coddep2",
            "X_UNIDAD": "x_unidad", "UNIDAD": "unidad", "Grupo de materias": "grupo_materias",
            "MATERIA": "materia", "X_MATERIOAOMG": "x_materiaomg", "CURSO": "curso", "OMC": "omc",
            "Horas Semana mínimo": "horas_semana_min", "Horas Semana máximo": "horas_semana_max",
            "DNI": "dni", "CORREO_E": "email", "PUESTO": "puesto", "X_PUESTO": "x_puesto",
            "X_SESION": "x_sesion", "X_ETAPA": "x_etapa_escolar", "ETAPA": "etapa_escolar"}

    for i, row_index in enumerate(range(5, sheet.nrows)):
        pxls = PlantillaXLS.objects.create(po=po)
        for col_index in range(sheet.ncols):
            column_header = str(sheet.cell(4, col_index).value)
            try:
                # Al cargar un campo con valor '2', la hoja excel la devuelve como '2.0'
                # para grabar exactamento '2' lo convertimos float -> int -> str :
                if column_header == 'DNI':
                    dni = genera_nie(sheet.cell(row_index, col_index).value)
                    setattr(pxls, 'dni', dni)
                elif column_header in ['X_DOCENTE', 'X_DEPARTAMENTO', 'DÍA', 'HORA INICIO', 'AÑO', 'HORA FIN',
                                       'X_ACTIVIDAD', 'MINUTOS', 'X_DEPENDENCIA', 'X_OFERTAMATRIG', 'X_DEPENDENCIA2',
                                       'X_UNIDAD', 'X_MATERIOAOMG', 'X_PUESTO', 'X_SESION', 'X_ETAPA']:
                    # Comprobar que existe valor y no es una celda vacía:
                    if sheet.cell(row_index, col_index).value:
                        setattr(pxls, keys[column_header], str(int(float(sheet.cell(row_index, col_index).value))))
                    else:
                        setattr(pxls, keys[column_header], sheet.cell(row_index, col_index).value)
                else:
                    setattr(pxls, keys[column_header], sheet.cell(row_index, col_index).value)
            except Exception as msg:
                setattr(pxls, keys[column_header], sheet.cell(row_index, col_index).value)
                carga.log += 'Error: %s' % str(msg)
                carga.save()
        pxls.save()
        if i == 0:  # Es la primera línea ejecutada del forloop. La primera fila leída del archivo XLS
            nombre_centro, dash, code_centro = pxls.centro.rpartition('-')
            entidad, c = Entidad.objects.get_or_create(code=int(code_centro))
            entidad.name = nombre_centro
            try:
                entidad.organization = Organization.objects.get(organization__icontains='Gobierno')
            except:
                carga.log += 'No encuentra Gobierno. %s - PO: %s' % (entidad.name, po.id)
                carga.save()
            entidad.save()
            con1 = entidad == carga.g_e.ronda.entidad
            con2 = carga.g_e.has_permiso('carga_horario_personal_centros_educativos')
            con3 = carga.g_e.has_permiso('carga_horario_personal_centro_educativo')
            if not (con2 or (con1 and con3)):
                carga.log += 'Error. Carga para %s - g_e de %s' % (entidad.name, carga.g_e.ronda.entidad.name)
                carga.cargado = True
                carga.save()
                return False
            po.ronda_centro = entidad.ronda
            po.save()
    carga.cargado = True
    carga.log += 'Comienza la carga de la plantilla orgánica: %s' % datetime.now().strftime('%d-%m-%Y %H:%M')
    carga.save()
    po.carga_plantilla_xls()
    po.carga_completa = True
    po.save()
    return True


def carga_masiva_datos_casiopea(carga):
    return True


# La siguiente función habrá que borrarla cuando se estabilicen las nuevas cargas:
def carga_masiva_tipo_EXCEL(carga):
    f = carga.fichero.read()
    book = xlrd.open_workbook(file_contents=f)
    sheet = book.sheet_by_index(0)
    # Get the keys from line 5 of excel file:
    keys = [slugify(sheet.cell(4, col_index).value) for col_index in range(sheet.ncols)]
    key_columns = {col_index: slugify(sheet.cell(4, col_index).value) for col_index in range(sheet.ncols)}

    if int(sheet.ncols) > 50:  # En este caso es el archivo de los alumnos
        carga.log += '<p>Carga de alumnos</p>'
        # Un ejemplo de key_columns es:
        # {0: 'estado-matricula', 1: 'direccion', 2: 'codigo-postal', 3: 'localidad-de-residencia',
        # 4: 'provincia-de-residencia', 5: 'alumno', 6: 'telefono', 7: 'telefono-movil', 8: 'correo-electronico',
        # 9: 'noidracima', 10: 'grupo', 11: 'bilingue', 12: 'dnipasaporte-primer-tutor', 13: 'no-expte-en-el-centro',
        # 14: 'primer-apellido-primer-tutor', 15: 'segundo-apellido-primer-tutor', 16: 'nombre-primer-tutor',
        # 17: 'no-historial-academico', 18: 'tfno-primer-tutor', 19: 'tfno-movil-primer-tutor', 20: 'sexo-primer-tutor',
        # 21: 'dnipasaporte-segundo-tutor', 22: 'dnipasaporte', 23: 'primer-apellido-segundo-tutor',
        # 24: 'segundo-apellido-segundo-tutor', 25: 'nombre-segundo-tutor', 26: 'tfno-segundo-tutor',
        # 27: 'tfno-movil-segundo-tutor', 28: 'sexo-segundo-tutor', 29: 'localidad-de-nacimiento', 30: 'centro',
        # 31: 'codigo-pais-nacimiento', 32: 'pais-de-nacimiento', 33: 'codigo-provincia-nacimiento',
        # 34: 'pago-seguro-escolar', 35: 'nacionalidad', 36: 'no-de-matriculas-en-este-curso', 37: 'curso',
        # 38: 'observaciones-de-la-matricula', 39: 'numero-ss', 40: 'no-de-matriculas-expediente',
        # 41: 'repeticiones-en-el-curso', 42: 'familia-numerosa', 43: 'ano-de-la-matricula', 44: 'primer-apellido',
        # 45: 'segundo-apellido', 46: 'nombre', 47: 'fecha-de-la-matricula', 48: 'sexo', 49: 'fecha-de-nacimiento',
        # 50: 'usuario-alumnado', 51: 'usuario-primer-tutor', 52: 'usuario-segundo-tutor', 53: 'x_unidad',
        # 54: 'x_ofertamatrig'}
        # La relación entre los campos (slugified) de la hoja Excel con los de Gauss viene dada por kra:
        kra = {
            'estado-matricula': 'estado_matricula', 'direccion': 'direccion', 'codigo-postal': 'cp',
            'localidad-de-residencia': 'localidad', 'provincia-de-residencia': 'provincia', 'alumno': 'alumno',
            'telefono': 'telefono_fijo', 'telefono-movil': 'telefono_movil', 'correo-electronico': 'email',
            'noidracima': 'id_socio', 'grupo': 'grupo', 'bilingue': 'bilingue',
            'dnipasaporte-primer-tutor': 'dni_tutor1', 'no-expte-en-el-centro': 'num_exp',
            'primer-apellido-primer-tutor': 'last_name1_tutor1', 'segundo-apellido-primer-tutor': 'last_name2_tutor1',
            'nombre-primer-tutor': 'nombre_tutor1', 'no-historial-academico': 'id_organizacion',
            'tfno-primer-tutor': 'telefono_fijo_tutor1', 'tfno-movil-primer-tutor': 'telefono_movil_tutor1',
            'sexo-primer-tutor': 'sexo_tutor1', 'dnipasaporte-segundo-tutor': 'dni_tutor2', 'dnipasaporte': 'dni',
            'primer-apellido-segundo-tutor': 'last_name1_tutor2', 'segundo-apellido-segundo-tutor': 'last_name2_tutor2',
            'nombre-segundo-tutor': 'nombre_tutor2', 'tfno-segundo-tutor': 'telefono_fijo_tutor2',
            'tfno-movil-segundo-tutor': 'telefono_movil_tutor2', 'sexo-segundo-tutor': 'sexo_tutor2',
            'localidad-de-nacimiento': 'localidad_nacimiento', 'centro': 'centro',
            'codigo-pais-nacimiento': 'code_pais_nacimiento', 'pais-de-nacimiento': 'pais_nacimiento',
            'codigo-provincia-nacimiento': 'code_provincia_nacimiento', 'pago-seguro-escolar': 'pago_seguro_escolar',
            'nacionalidad': 'nacionalidad', 'no-de-matriculas-en-este-curso': 'num_matriculas', 'curso': 'curso',
            'observaciones-de-la-matricula': 'observaciones_matricula', 'numero-ss': 'num_ss',
            'no-de-matriculas-expediente': 'num_matriculas_exp', 'repeticiones-en-el-curso': 'rep_curso',
            'familia-numerosa': 'familia_numerosa', 'ano-de-la-matricula': 'year_matricula',
            'primer-apellido': 'last_name1', 'segundo-apellido': 'last_name2', 'nombre': 'nombre',
            'fecha-de-la-matricula': 'fecha_matricula', 'sexo': 'sexo', 'fecha-de-nacimiento': 'nacimiento',
            'usuario-alumnado': 'username', 'usuario-primer-tutor': 'username_tutor1',
            'usuario-segundo-tutor': 'username_tutor2', 'x_unidad': 'x_unidad', 'x_ofertamatrig': 'x_curso'}
        for row_index in range(5, sheet.nrows):
            d = {'alumno': '', 'estado_matricula': '', 'id_socio': '', 'dni': '', 'direccion': '', 'cp': '',
                 'localidad': '', 'nacimiento': '', 'provincia': '', 'telefono_fijo': '', 'telefono_movil': '',
                 'email': '', 'curso': '', 'id_organizacion': '', 'subentidades': '', 'last_name1': '',
                 'last_name2': '', 'nombre': '', 'dni_tutor1': '', 'last_name1_tutor1': '',
                 'last_name2_tutor1': '', 'nombre_tutor1': '', 'telefono_fijo_tutor1': '', 'fecha_alta': '',
                 'telefono_movil_tutor1': '', 'sexo_tutor1': '', 'dni_tutor2': '', 'last_name1_tutor2': '',
                 'last_name2_tutor2': '', 'nombre_tutor2': '', 'telefono_fijo_tutor2': '', 'perfiles': '',
                 'telefono_movil_tutor2': '', 'sexo_tutor2': '', 'localidad_nacimiento': '', 'nacionalidad': '',
                 'code_pais_nacimiento': '', 'pais_nacimiento': '', 'code_provincia_nacimiento': '',
                 'pago_seguro_escolar': '', 'sexo': '', 'year_matricula': '', 'num_matriculas': '',
                 'observaciones_matricula': '', 'num_ss': '', 'num_exp': '', 'fecha_matricula': '',
                 'num_matriculas_exp': '', 'rep_curso': '', 'familia_numerosa': '', 'lengua_materna': '',
                 'year_incorporacion': '', 'bilingue': '', 'email_tutor1': '', 'email_tutor2': '', 'iban': '',
                 'localidad_tutor1': '', 'localidad_tutor2': '', 'direccion_tutor1': '', 'direccion_tutor2': '',
                 'cp_tutor1': '', 'cp_tutor2': '', 'nacimiento_tutor1': '', 'nacimiento_tutor2': '',
                 'provincia_tutor1': '', 'provincia_tutor2': '', 'iban_tutor1': '', 'iban_tutor2': '',
                 'id_socio_tutor1': '', 'id_socio_tutor2': '', 'fecha_alta_tutor1': '', 'fecha_alta_tutor2': '',
                 'observaciones_tutor1': '', 'observaciones_tutor2': '', 'perfiles_tutor1': '', 'perfiles_tutor2': '',
                 'username_tutor2': '', 'username_tutor1': '', 'username': '', 'grupo': '', 'x_unidad': '',
                 'x_curso': '', 'centro': ''}
            for col_index in range(sheet.ncols):
                try:
                    d[kra[key_columns[col_index]]] = sheet.cell(row_index, col_index).value
                except:
                    pass
            try:
                entidad = Entidad.objects.get(code=d['centro'].replace(')', '').split(sep='(')[1])
                ronda = entidad.ronda
                try:
                    cargoa = Cargo.objects.get(entidad=entidad, borrable=False, clave_cargo='g_alumno')
                except:
                    cargoa = Cargo.objects.create(cargo='Alumno/a', entidad=entidad, borrable=False,
                                                  clave_cargo='g_alumno')
                    carga.log += '<p>Crear cargo g_alumno - %s</p>' % ronda
                try:
                    cargop = Cargo.objects.get(entidad=entidad, borrable=False, clave_cargo='g_madre_padre')
                except:
                    cargop = Cargo.objects.create(cargo='Madre/Padre/Tutor/a legal', entidad=entidad,
                                                  borrable=False, clave_cargo='g_madre_padre')
                    carga.log += '<p>Crear cargo g_madre_padre - %s</p>' % ronda
                # Definición de los datos que permiten definir los usuarios:
                d['apellidos'] = '%s %s' % (d['last_name1'], d['last_name2'])
                d['apellidos_tutor1'] = '%s %s' % (d['last_name1_tutor1'], d['last_name2_tutor1'])
                d['apellidos_tutor2'] = '%s %s' % (d['last_name1_tutor2'], d['last_name2_tutor2'])
                try:
                    # x_curso = str(int(float(d['x_curso'].replace(',', '.'))))
                    x_curso = str(d['x_curso']).split('.')[0]
                except:
                    x_curso = ''
                    carga.log += '<p>x_curso: %s - %s</p>' % (d['x_curso'], ronda)
                try:
                    curso = Curso.objects.get(ronda=ronda, clave_ex=x_curso)
                except:
                    cursos = Curso.objects.filter(ronda=ronda, clave_ex=x_curso)
                    if cursos.count() > 0:
                        carga.log += '<p>cursos iguales (%s): %s - %s</p>' % (cursos.count(), d['x_curso'], ronda)
                        curso = cursos[0]
                        # cursos.exclude(pk__in=[curso.pk]).delete()
                    else:
                        curso = Curso.objects.create(clave_ex=x_curso, ronda=ronda)
                        logger.info('Carga masiva xls. Se crea curso %s' % curso.clave_ex)
                        carga.log += '<br>Carga masiva xls. Se crea curso %s' % curso.clave_ex
                        carga.save()
                curso.nombre = d['curso']
                curso.save()
                try:
                    # x_unidad = str(int(float(d['x_unidad'].replace(',', '.'))))
                    x_unidad = str(d['x_unidad']).split('.')[0]
                except:
                    x_unidad = ''
                    carga.log += '<p>x_unidad: %s - %s</p>' % (d['x_unidad'], ronda)
                try:
                    grupo = Grupo.objects.get(ronda=ronda, clave_ex=x_unidad)
                except:
                    grupos = Grupo.objects.filter(ronda=ronda, clave_ex=x_unidad)
                    if grupos.count() > 0:
                        carga.log += '<p>grupos iguales (%s): %s - %s</p>' % (grupos.count(), d['x_unidad'], ronda)
                        grupo = grupos[0]
                        # grupos.exclude(pk__in=[grupo.pk]).delete()
                    else:
                        grupo = Grupo.objects.create(ronda=ronda, clave_ex=x_unidad)
                        logger.info('Carga masiva xls. Se crea grupo %s' % grupo.clave_ex)
                        carga.log += '<br>Carga masiva xls. Se crea grupo %s' % grupo.clave_ex
                        carga.save()
                grupo.nombre = d['grupo']
                grupo.save()
                grupo.cursos.add(curso)
                d['activo'] = True
                d['observaciones'] = '<b>Localidad de nacimiento:</b> %s<br><b>Nacionalidad:</b> %s<br>' \
                                     '<b>Código del país de nacimiento:</b> %s<br><b>País de nacimiento:</b> %s<br>' \
                                     '<b>Código de la provincia de nacimiento:</b> %s<br><b>Ha pagado el seguro escolar:</b> %s<br>' \
                                     '<b>Año de la matrícula:</b> %s<br><b>Número de matrículas en este curso:</b> %s<br>' \
                                     '<b>Observaciones de la matrícula:</b> %s<br><b>Número de SS:</b> %s<br>' \
                                     '<b>Nº de expediente en el centro:</b> %s<br><b>Fecha de matrícula:</b> %s<br>' \
                                     '<b>Nº de matrículas en el expediente:</b> %s<br><b>Repeticiones en el curso:</b> %s<br>' \
                                     '<b>Familia numerosa:</b> %s<br><b>Lengua materna:</b> %s<br><b>Año de incorporación al sistema educativo:</b> %s<br>' % (
                                         d['localidad_nacimiento'], d['nacionalidad'],
                                         d['code_pais_nacimiento'],
                                         d['pais_nacimiento'], d['code_provincia_nacimiento'],
                                         d['pago_seguro_escolar'], d['year_matricula'], d['num_matriculas'],
                                         d['observaciones_matricula'],
                                         d['num_ss'], d['num_exp'], d['fecha_matricula'],
                                         d['num_matriculas_exp'],
                                         d['rep_curso'], d['familia_numerosa'], d['lengua_materna'],
                                         d['year_incorporacion'])
                tutor1 = create_usuario(d, ronda, '_tutor1')
                if tutor1:
                    tutor1.cargos.add(cargop)
                    tutor1.save()
                tutor2 = create_usuario(d, ronda, '_tutor2')
                if tutor2:
                    tutor2.cargos.add(cargop)
                    tutor2.save()
                gauser_extra = create_usuario(d, ronda, '')
                gauser_extra.tutor1 = tutor1
                gauser_extra.tutor2 = tutor2
                gauser_extra.cargos.add(cargoa)
                gauser_extra.save()
                gauser_extra.gauser_extra_estudios.grupo = grupo
                gauser_extra.gauser_extra_estudios.save()
            except Exception as msg:
                Aviso.objects.create(usuario=carga.g_e, aviso='carga_centros0: %s - %s' % (str(msg), d['centro']),
                                     fecha=now())
    if int(sheet.ncols) < 15:  # En este caso es el archivo es del personal
        # Un ejemplo de key_columns es:
        # {0: 'ano', 1: 'centro', 2: 'codigo', 3: 'nombre-docente', 4: 'apellidos-docente', 5: 'dni', 6: 'x_docente',
        #  7: 'correo-e', 8: 'puesto', 9: 'x_puesto', 10: 'tipo-personal', 11: 'jornada-contratada', 12: 'usuario'}

        # krp = {'Empleado': 'empleado', 'DNI/Pasaporte': 'dni', 'Tipo de personal': 'subentidades',
        #        'Puesto': 'perfiles', 'Fecha de nacimiento': 'nacimiento', 'Activo': 'activo',
        #        'Fecha del último nombramiento': 'fecha_alta',
        #        'Fecha de cese': 'baja', 'Dirección': 'direccion', 'Código Postal': 'cp', 'Sexo': 'sexo',
        #        'Localidad': 'localidad', 'Provincia': 'provincia', 'Teléfono 1': 'telefono_fijo',
        #        'Teléfono 2': 'telefono_movil', 'Correo electrónico': 'email', 'Especialidad': 'especialidad'}
        # pdic = {'empleado': '', 'dni': '', 'subentidades': '', 'perfiles': '', 'nacimiento': '', 'activo': '',
        #         'fecha_alta': '', 'baja': '', 'direccion': '', 'cp': '', 'sexo': '', 'localidad': '', 'email': '',
        #         'iban': '', 'provincia': '', 'telefono_fijo': '', 'telefono_movil': '', 'especialidad': ''}
        # for row_index in range(5, sheet.nrows):
        #     d = pdic
        #     for col_index in range(sheet.ncols):
        #         d[krp[keys[col_index]]] = sheet.cell(row_index, col_index).value
        #     d['apellidos'] = d['empleado'].split(', ')[0]
        #     d['nombre'] = d['empleado'].split(', ')[1]
        #     d['id_socio'] = d['dni']
        #     clave_ex = d['subentidades'].replace(' ', '_').lower()
        #
        #     sub1s = Subentidad.objects.filter(entidad=carga.ronda.entidad, clave_ex=clave_ex)
        #     if sub1s.count() > 0:
        #         sub1 = sub1s[0]
        #     else:
        #         sub1 = Subentidad.objects.create(nombre=d['subentidades'], mensajes=True, edad_min=18,
        #                                          entidad=carga.ronda.entidad, clave_ex=clave_ex, edad_max=67)
        #     sub2s = Subentidad.objects.filter(nombre=d['perfiles'], entidad=carga.ronda.entidad)
        #     if sub2s.count() > 0:
        #         sub2 = sub2s[0]
        #     else:
        #         sub2 = Subentidad.objects.create(nombre=d['perfiles'], mensajes=True, edad_min=18,
        #                                          edad_max=67, entidad=carga.ronda.entidad, parent=sub1)
        #     cargo = Cargo.objects.get_or_create(entidad=carga.ronda.entidad, cargo=d['subentidades'])
        #     d['subentidades'] = str(sub1.id) + ',' + str(sub2.id)
        #     d['activo'] = True if 'S' in d['activo'] else False
        #     d['perfiles'] = str(cargo[0].id)
        #     d['observaciones'] = d['especialidad'] + '<br>Causa baja el ' + d['baja']
        #     create_usuario(d, carga, '')

        ####################################
        errores = {}
        # Get the keys from line 5 of excel file:
        dict_names = {}
        for col_index in range(sheet.ncols):
            dict_names[str(sheet.cell(4, col_index).value).strip()] = col_index
        for row_index in range(5, sheet.nrows):
            try:
                code_entidad = int(sheet.cell(row_index, dict_names['Código']).value)
                entidad = Entidad.objects.get(code=code_entidad)
                dni = genera_nie(str(sheet.cell(row_index, dict_names['DNI']).value))
                nombre = sheet.cell(row_index, dict_names['Nombre docente']).value
                apellidos = sheet.cell(row_index, dict_names['Apellidos docente']).value
                email = sheet.cell(row_index, dict_names['Correo-e']).value
                username = sheet.cell(row_index, dict_names['Usuario']).value
                clave_ex = str(sheet.cell(row_index, dict_names['X_DOCENTE']).value).strip()
                puesto = str(sheet.cell(row_index, dict_names['Puesto']).value).strip()
                xpuesto = str(sheet.cell(row_index, dict_names['X_PUESTO']).value).strip()
                tipo_personal = str(sheet.cell(row_index, dict_names['Tipo personal']).value).strip()
                jornada_contratada = str(sheet.cell(row_index, dict_names['Jornada contratada']).value).strip()

                if 'No Docente' in tipo_personal and jornada_contratada == '0:00':
                    try:
                        cargo = Cargo.objects.get(entidad=entidad, clave_cargo='g_nodocente', borrable=False)
                    except:
                        cargo = Cargo.objects.create(entidad=entidad, clave_cargo='g_nodocente', borrable=False,
                                                     cargo='No docente')
                else:
                    try:
                        cargo = Cargo.objects.get(entidad=entidad, clave_cargo='g_docente', borrable=False)
                    except:
                        cargo = Cargo.objects.create(entidad=entidad, clave_cargo='g_docente', borrable=False,
                                                     cargo='Docente')
                # for c in CARGOS:
                #     if cargo.clave_cargo == c['clave_cargo']:
                #         for code_nombre in c['permisos']:
                #             cargo.permisos.add(Permiso.objects.get(code_nombre=code_nombre))
                try:
                    try:
                        gauser = Gauser.objects.get(dni=dni)
                        gauser.email = email
                        gauser.username = username
                    except:
                        gauser = Gauser.objects.get(username=username)
                        gauser.email = email
                        gauser.dni = dni
                except:
                    gauser = Gauser.objects.create_user(username, email=email, last_login=now(), dni=dni,
                                                        password=pass_generator(size=9))
                gauser.first_name = nombre
                gauser.last_name = apellidos
                gauser.save()
                gauser_extra, c = Gauser_extra.objects.get_or_create(ronda=entidad.ronda, gauser=gauser)
                gauser_extra.clave_ex = clave_ex
                gauser_extra.activo = True
                gauser_extra.puesto = puesto
                gauser_extra.tipo_personal = tipo_personal
                gauser_extra.jornada_contratada = jornada_contratada
                gauser_extra.cargos.add(cargo)
                gauser_extra.save()
            except Exception as msg:
                apellidos = slugify(sheet.cell(row_index, dict_names['Apellidos docente']).value)
                errores[row_index] = {'error': str(msg), 'apellidos': apellidos}
                logger.info('Error carga general docentes %s -- %s' % (str(apellidos), msg))
    carga.cargado = True
    carga.save()


def carga_masiva_tipo_PENDIENTES(carga):
    f = carga.fichero.read()
    book = xlrd.open_workbook(file_contents=f)
    sheet = book.sheet_by_index(0)

    # Get the keys from line 5 of excel file:
    dict_names = {}
    for col_index in range(sheet.ncols):
        dict_names[sheet.cell(4, col_index).value] = col_index
    errores_ge = []
    errores_materia = []
    for row_index in range(5, sheet.nrows):
        try:
            alumno_matricula = sheet.cell(row_index, dict_names['Nº Racima']).value
            ge = Gauser_extra.objects.get(id_entidad=alumno_matricula, ronda=carga.ronda)
        except:
            ge = None
            if alumno_matricula not in errores_ge:
                if Gauser_extra.objects.filter(id_entidad=alumno_matricula, ronda=carga.ronda).count() > 1:
                    carga.log += '<p>Duplicidad con alumno  %s (Nº de Racima: %s)</p>' % (
                        sheet.cell(row_index, dict_names['Alumno']).value, alumno_matricula)
                else:
                    carga.log += '<p>No existe el alumno %s con Nº de Racima: %s</p>' % (
                        sheet.cell(row_index, dict_names['Alumno']).value, alumno_matricula)
                carga.save()
                errores_ge.append(alumno_matricula)
        try:
            materia_matricula = str(int(sheet.cell(row_index, dict_names['X_MATERIAOMG']).value))
            materia = Materia.objects.get(clave_ex=materia_matricula, curso__ronda=carga.ronda)
        except:
            materia = None
            if materia_matricula not in errores_materia:
                if Materia.objects.filter(clave_ex=materia_matricula, curso__ronda=carga.ronda).count() > 1:
                    carga.log += '<p>Duplicidad con materia %s (código: %s)</p>' % (
                        sheet.cell(row_index, dict_names['Materia']).value, materia_matricula)
                else:
                    carga.log += '<p>No se encuentra materia con código: %s</p>' % (materia_matricula)
                carga.save()
                errores_materia.append(materia_matricula)
        estado_matricula = sheet.cell(row_index, dict_names['Estado materia']).value
        if 'Matriculada' in estado_matricula:
            estado = 'MA'
        elif 'Convalidada' in estado_matricula:
            estado = 'CV'
        elif 'Pendiente' in estado_matricula:
            estado = 'PE'
        else:
            estado = 'AP'
        if materia and ge:
            m, c = Matricula.objects.get_or_create(ge=ge, materia=materia)
            m.estado = estado
            m.save()


def carga_masiva_tipo_CENTROSRACIMA(carga):
    gauss = Gauser.objects.get(username='gauss')
    f = carga.fichero.read()
    book = xlrd.open_workbook(file_contents=f)
    sheet = book.sheet_by_index(0)
    # Get the keys from line 5 of excel file:
    dict_names = {}
    for col_index in range(sheet.ncols):
        dict_names[sheet.cell(4, col_index).value] = col_index
    entidades_creadas = []
    for row_index in range(5, sheet.nrows):
        code_entidad = int(sheet.cell(row_index, dict_names['Código']).value)
        # entidad, created = Entidad.objects.get_or_create(code=code_entidad)
        try:
            entidad = Entidad.objects.get(code=code_entidad)
        except:
            entidades = Entidad.objects.filter(code=code_entidad)
            if entidades.count() > 1:
                aviso = 'carga_centros12: Múltiples entidades con código %s' % str(code_entidad)
                Aviso.objects.create(usuario=carga.g_e, aviso=aviso, fecha=now())
                entidad = entidades[0]
                for e in entidades:
                    e.name = 'Entidad múltiple'
                    e.save()
            else:
                entidad = Entidad.objects.create(code=code_entidad)
        if entidad not in entidades_creadas:
            entidades_creadas.append(entidad)
            carga.log += '<hr><br>Se procesa: %s' % entidad
            entidad.name = sheet.cell(row_index, dict_names['Centro']).value
            entidad.organization = carga.g_e.ronda.entidad.organization
            entidad.address = sheet.cell(row_index, dict_names['Dirección postal']).value
            entidad.localidad = sheet.cell(row_index, dict_names['Localidad']).value
            entidad.provincia = carga.g_e.ronda.entidad.provincia
            entidad.postalcode = sheet.cell(row_index, dict_names['CP']).value
            entidad.tel = sheet.cell(row_index, dict_names['Teléfono']).value
            entidad.fax = sheet.cell(row_index, dict_names['FAX']).value
            entidad.mail = sheet.cell(row_index, dict_names['Correo-e']).value
            entidad.save()
            # Creación de cargos no borrables y asignación de inspectores a centros:
            mensaje = ejecutar_configurar_cargos_permisos_entidad(entidad)
            carga.log += '<br>%s' % mensaje
            carga.save()
            if entidad.ronda:  # Si existe una ronda, capturamos los g_es con perfiles de dirección
                q = Q(clave_cargo='g_miembro_equipo_directivo') | Q(clave_cargo='g_jefe_estudios') | Q(
                    clave_cargo='g_director_centro') | Q(clave_cargo='g_nodocente')
                # q = Q(cargo__icontains='director') | Q(cargo__icontains='estudios') | Q(cargo__icontains='secretar')
                cargos = Cargo.objects.filter(q, Q(entidad=entidad))
                g_es = Gauser_extra.objects.filter(ronda=entidad.ronda, cargos__in=cargos, activo=True)
            else:
                g_es = Gauser_extra.objects.none()
            if not entidad.ronda or entidad.ronda.fin < datetime.today().date():
                y1, y2 = datetime.today().year, datetime.today().year + 1
                inicio = datetime.strptime("1/9/%s" % y1, "%d/%m/%Y")
                fin = datetime.strptime("31/8/%s" % y2, "%d/%m/%Y")
                ronda, c = Ronda.objects.get_or_create(nombre="%s/%s" % (y1, y2), entidad=entidad, inicio=inicio,
                                                       fin=fin)
                entidad.ronda = ronda
                entidad.save()
                # Cargamos los usuarios capturados antes en la nueva ronda (miembros del equipo directivo):
                for g__e in g_es:
                    try:
                        Gauser_extra.objects.get(gauser=g__e.gauser, ronda=ronda)
                    except:
                        new_user = Gauser_extra.objects.create(gauser=g__e.gauser,
                                                               ronda=ronda,
                                                               id_entidad=g__e.id_entidad,
                                                               id_organizacion=g__e.id_organizacion,
                                                               alias=g__e.alias, activo=True,
                                                               observaciones=g__e.observaciones,
                                                               foto=g__e.foto,
                                                               tutor1=None, tutor2=None,
                                                               ocupacion=g__e.ocupacion,
                                                               num_cuenta_bancaria=g__e.num_cuenta_bancaria)
                        new_user.subentidades.add(*g__e.subentidades.all())
                        new_user.subsubentidades.add(*g__e.subsubentidades.all())
                        new_user.cargos.add(*g__e.cargos.all())
                        new_user.permisos.add(*g__e.permisos.all())
                # Crear usuario gauss para la entidad:
                ge, c = Gauser_extra.objects.get_or_create(gauser=gauss, ronda=entidad.ronda, activo=True)
                if c:
                    permisos = Permiso.objects.all()
                    ge.permisos.add(*permisos)
                # Crear el usuario entidad:
                try:
                    gauser_entidad = Gauser.objects.get(username=entidad.code)
                except Exception as msg:
                    email = 'inventado@%s.com' % entidad.code
                    gauser_entidad = Gauser.objects.create_user(entidad.code, email, str(entidad.code),
                                                                last_login=now())
                    Aviso.objects.create(usuario=carga.g_e, aviso='carga_centros4: %s' % str(msg), fecha=now())
                try:
                    Gauser_extra.objects.get(gauser=gauser_entidad, ronda=entidad.ronda)
                except Exception as msg:
                    g_e_entidad = Gauser_extra.objects.create(gauser=gauser_entidad, ronda=entidad.ronda,
                                                              activo=True)
                    cargo_director, c = Cargo.objects.get_or_create(entidad=entidad,
                                                                    clave_cargo='g_director_centro')
                    g_e_entidad.permisos.add(*cargo_director.permisos.all())
            # Menus:
            carga.log += '<br>Comienza carga de menús'
            carga.save()
            for m in Menus_Centro_Educativo:
                try:
                    md = Menu_default.objects.get(code_menu=m[0])
                    try:
                        Menu.objects.get(entidad=entidad, menu_default=md)
                    except:
                        Menu.objects.create(entidad=entidad, menu_default=md, texto_menu=m[1], pos=m[2])
                except Exception as msg:
                    Aviso.objects.create(usuario=carga.g_e, aviso='carga_centros2: %s' % str(msg), fecha=now())
            ee, created = EntidadExtra.objects.get_or_create(entidad=entidad)
            ee.titularidad = sheet.cell(row_index, dict_names['Titularidad']).value
            ee.tipo_centro = sheet.cell(row_index, dict_names['Tipo centro']).value
            try:
                code_entidad_padre = int(sheet.cell(row_index, dict_names['IES del que depende']).value)
                ee.depende_de = Entidad.objects.get(code=code_entidad_padre)
            except Exception as msg:
                ee.depende_de = None
            if 'S' in sheet.cell(row_index, dict_names['Servicio comedor']).value:
                ee.comedor = True
            else:
                ee.comedor = False
            if 'S' in sheet.cell(row_index, dict_names['Transporte escolar']).value:
                ee.transporte = True
            else:
                ee.transporte = False
            ee.director = sheet.cell(row_index, dict_names['Dirección']).value
            ee.save()
        expediente = sheet.cell(row_index, dict_names['Expediente']).value
        eee, created = EntidadExtraExpediente.objects.get_or_create(eextra=ee, expediente=expediente)
        oferta = sheet.cell(row_index, dict_names['Oferta']).value
        EntidadExtraExpedienteOferta.objects.get_or_create(eeexpediente=eee, oferta=oferta)


def carga_masiva_tipo_DOCENTES_RACIMA(carga):
    gauss = Gauser.objects.get(username='gauss')
    centros_cargados = []
    docentes_cargados = {}
    carga.log += '<p>Comienza carga de docentes</p>'
    errores = {}
    f = carga.fichero.read()
    book = xlrd.open_workbook(file_contents=f)
    sheet = book.sheet_by_index(0)
    # Get the keys from line 5 of excel file:
    dict_names = {}
    for col_index in range(sheet.ncols):
        dict_names[sheet.cell(4, col_index).value] = col_index
    for row_index in range(5, sheet.nrows):
        try:
            code_entidad = int(sheet.cell(row_index, dict_names['Código']).value)
            entidad = Entidad.objects.get(code=code_entidad)
            if code_entidad not in centros_cargados:
                centros_cargados.append(code_entidad)
            if code_entidad not in docentes_cargados:
                docentes_cargados[code_entidad] = []
            try:
                cargo_d = Cargo.objects.get(entidad=entidad, clave_cargo='g_docente', borrable=False)
            except:
                cargo_d = Cargo.objects.create(entidad=entidad, clave_cargo='g_docente', borrable=False,
                                               cargo='Docente')
            try:
                cargo_nd = Cargo.objects.get(entidad=entidad, clave_cargo='g_nodocente', borrable=False)
            except:
                cargo_nd = Cargo.objects.create(entidad=entidad, clave_cargo='g_nodocente', borrable=False,
                                                cargo='No docente')
            dni = genera_nie(str(sheet.cell(row_index, dict_names['DNI']).value))
            nombre = sheet.cell(row_index, dict_names['Nombre docente']).value
            apellidos = sheet.cell(row_index, dict_names['Apellidos docente']).value
            email = sheet.cell(row_index, dict_names['Correo-e']).value
            username = sheet.cell(row_index, dict_names['Usuario']).value
            clave_ex = str(sheet.cell(row_index, dict_names['X_DOCENTE']).value).strip().split('.')[0]
            puesto = str(sheet.cell(row_index, dict_names['Puesto']).value).strip()
            tipo_personal = str(sheet.cell(row_index, dict_names['Tipo personal']).value).strip()
            if 'No Docente' in tipo_personal:
                cargo = cargo_nd
            else:
                cargo = cargo_d
            jornada_contratada = str(sheet.cell(row_index, dict_names['Jornada contratada']).value).strip()
            try:
                try:
                    gauser = Gauser.objects.get(username=username)
                    gauser.dni = dni
                    gauser.email = email
                    gauser.first_name = nombre
                    gauser.last_name = apellidos[:30]
                    gauser.save()
                except Exception as msg:
                    carga.log += '<p>Error: %s</p>\n' % (msg)
                    carga.save()
                    gauser = Gauser.objects.get(dni=dni)
                    gauser.email = email
                    gauser.username = username
                    gauser.first_name = nombre
                    gauser.last_name = apellidos
                    gauser.save()
                    carga.log += '<p>Se busca usuario %s por dni: %s</p>\n' % (username, dni)
                    carga.save()
            except:
                carga.log += '<p>Se intenta crear usuario con username: %s</p>\n' % username
                carga.save()
                gauser = Gauser.objects.create_user(username, email=email, last_login=now(), dni=dni,
                                                    password=pass_generator(size=9))
            gauser_extra, c = Gauser_extra.objects.get_or_create(ronda=entidad.ronda, gauser=gauser)
            gauser_extra.clave_ex = clave_ex
            gauser_extra.id_organizacion = clave_ex
            gauser_extra.activo = True
            gauser_extra.puesto = puesto
            gauser_extra.tipo_personal = tipo_personal
            gauser_extra.jornada_contratada = jornada_contratada
            gauser_extra.cargos.add(cargo)
            gauser_extra.save()
            docentes_cargados[code_entidad].append(clave_ex)
            # carga.log += '<p>Carga de %s - %s - %s</p>\n' % (username, dni, gauser_extra.id_organizacion)
            direc_apellidos, direc_nombre = entidad.entidadextra.director.split(', ')
            if gauser_extra.gauser.first_name == direc_nombre and gauser_extra.gauser.last_name == direc_apellidos:
                cargo_director, c = Cargo.objects.get_or_create(entidad=entidad, clave_cargo='g_director_centro')
                gauser_extra.cargos.add(cargo_director)
            if entidad.entidadextra.depende_de:
                nueva_entidad = entidad.entidadextra.depende_de
                carga.log += '<p>Entidad depende de: %s</p>\n' % (nueva_entidad)
                gauser_extra, c = Gauser_extra.objects.get_or_create(ronda=nueva_entidad.ronda, gauser=gauser)
                gauser_extra.clave_ex = 's-%s' % clave_ex
                gauser_extra.id_organizacion = 's-%s' % clave_ex
                gauser_extra.activo = True
                gauser_extra.puesto = puesto
                gauser_extra.tipo_personal = tipo_personal
                gauser_extra.jornada_contratada = jornada_contratada
                gauser_extra.cargos.add(cargo)
                gauser_extra.save()
                carga.log += '<p>Carga de %s - %s - s-%s</p>\n' % (username, dni, gauser_extra.id_organizacion)
        except Exception as msg:
            apellidos = slugify(sheet.cell(row_index, dict_names['Apellidos docente']).value)
            errores[row_index] = {'error': str(msg), 'apellidos': apellidos}
            logger.info('Error carga general docentes %s -- %s' % (str(apellidos), msg))
            carga.log += '<p>Error carga general docentes %s -- %s</p>' % (str(apellidos), msg)
    for centro_cargado in centros_cargados:
        # Líneas de código para eliminar usuarios que no están en el archivo de carga:
        entidad = Entidad.objects.get(code=centro_cargado)
        carga.log += '<p><b>%s</b></p>' % entidad
        carga.log += '<p>Lista: %s</p>' % ', '.join(docentes_cargados[entidad.code])
        cargo_d = Cargo.objects.get(entidad=entidad, clave_cargo='g_docente', borrable=False)
        cargo_nd = Cargo.objects.get(entidad=entidad, clave_cargo='g_nodocente', borrable=False)
        usuarios_activos = Gauser_extra.objects.filter(activo=True, cargos__in=[cargo_nd, cargo_d],
                                                       ronda=entidad.ronda)
        for usuario_activo in usuarios_activos:
            if usuario_activo.clave_ex not in docentes_cargados[entidad.code]:
                # Puede que existan usuarios activos correctamente por pertenecer a una sección
                # Estos usuarios tienen una clave_ex que comienza por s-
                try:
                    if usuario_activo.clave_ex:
                        if 's-' not in usuario_activo.clave_ex:
                            usuario_activo.activo = False
                            usuario_activo.save()
                            carga.log += '<p>Desactivado usuario: %s con clave_ex: </p>\n' % (usuario_activo, clave_ex)
                    else:
                        usuario_activo.activo = False
                        usuario_activo.save()
                        carga.log += '<p>Desactivado usuario: %s, clave_ex: None</p>\n' % (usuario_activo)
                except Exception as msg:
                    carga.log += '<p>Error al desactivar a: %s - %s</p>\n' % (usuario_activo, str(msg))
    carga.save()
    return True


@shared_task
def carga_masiva_from_excel(carga_id=None):
    try:
        # Es improbable, sino imposible que se pase un carga_id inexistente, pero en el caso de que así fuera
        # es necesario detectarlo y dejarlo grabado en un log
        carga = CargaMasiva.objects.get(id=carga_id)
    except Exception as msg:
        # Tomamos un Gauser_extra correspondiente al usuario 'gauss' que será el que regitre el Aviso
        ge_gauss = Gauser_extra.objects.filter(gauser__username='gauss')[0]
        msg = 'Se ha pasado un carga_id que no corresponde a ninguna carga masiva'
        Aviso.objects.create(usuario=carga.g_e, aviso=msg, fecha=now())
        return False
    borra_cargas_masivas_antiguas(carga)
    try:
        inicio_carga = datetime.now()
        if carga.tipo == 'EXCEL':
            carga_masiva_tipo_EXCEL(carga)  # Función cambiada el 18/04/2021. Nuevos ficheros Racima
        elif carga.tipo == 'PENDIENTES':
            carga_masiva_tipo_PENDIENTES(carga)
        elif carga.tipo == 'CENTROSRACIMA':
            carga_masiva_tipo_CENTROSRACIMA(carga)
        elif carga.tipo == 'DOCENTES_RACIMA':
            carga_masiva_tipo_DOCENTES_RACIMA(carga)
        # Las anteriores cargas habrá que borrarlas. Los nuevos tipos de cargas son:
        # ['ALUMN_CENTRO', 'ALUMN_CENTROS', 'PERSONAL_CENTRO', 'PERSONAL_CENTROS', 'DATOS_CENTROS', 'HORARIO_PERSONAL_CENTRO', 'DATOS_CASIOPEA']
        elif carga.tipo == 'ALUMN_CENTRO':
            carga_masiva_alumnos(carga=carga, entidad=carga.g_e.ronda.entidad)
        elif carga.tipo == 'ALUMN_CENTROS':
            carga_masiva_alumnos(carga=carga, entidad=False)
        elif carga.tipo == 'PERSONAL_CENTRO':
            carga_masiva_personal(carga=carga, entidad=carga.g_e.ronda.entidad)
        elif carga.tipo == 'PERSONAL_CENTROS':
            carga_masiva_personal(carga=carga, entidad=None)
        elif carga.tipo == 'DATOS_CENTROS':
            carga_masiva_datos_centros(carga=carga)
        elif carga.tipo == 'HORARIO_PERSONAL_CENTRO':
            carga.log += 'Carga de tipo: HORARIO_PERSONAL_CENTRO<br>'
            carga.save()
            carga_masiva_horario_personal_centro(carga=carga)
        elif carga.tipo == 'DATOS_CASIOPEA':
            carga_masiva_datos_casiopea(carga=carga)
        fin_carga = datetime.now()
        carga.log += '<p><b>Proceso de carga iniciado (%s) terminado (%s)</b></p>' % (inicio_carga, fin_carga)
        carga.log += '<p><b>Tiempo empleado en la carga: %s</b></p>' % (fin_carga - inicio_carga)
        carga.cargado = True
        carga.save()
    except Exception as msg:
        logger.info('Carga masiva xls se produce error con carga.id=%s' % carga.id)
        logger.info('El mensaje de error es: %s' % str(msg))
        carga.log += '<br>%s' % str(msg)
        carga.error = True
        carga.cargado = True
        carga.save()


# --------------------------------------------------------------------------#
# DEFINICIÓN DE FUNCIONES ACTUALIZAR MENUS Y PERMISOS EN ENTIDADES Y CARGOS
# --------------------------------------------------------------------------#

def ejecutar_configurar_cargos_permisos_entidad(e):
    # e: class Entidad
    mensaje = 'ejecutar_configurar_cargos_permisos_entidad<br>'
    try:
        if e.entidadextra.tipo_centro in TiposCentro:
            for c in CARGOS_CENTROS:
                cargo, creado = Cargo.objects.get_or_create(entidad=e, borrable=False, clave_cargo=c['clave_cargo'])
                cargo.cargo = c['cargo']
                cargo.nivel = c['nivel']
                cargo.save()
                cargo.permisos.clear()
                for code_nombre in c['permisos']:
                    try:
                        cargo.permisos.add(Permiso.objects.get(code_nombre=code_nombre))
                    except Exception as msg:
                        mensaje += '<br>Permiso: %s -- %s' % (code_nombre, str(msg))
            try:
                insp_g = e.centroinspeccionado.inspectorasignado_set.all()[0].inspector.gauser
                # Inicialmente se hicieron pruebas únicamente para María Villanueva
                insp_ge, c = Gauser_extra.objects.get_or_create(gauser=insp_g, ronda=e.ronda)
                insp_ge.activo = True
                insp_ge.puesto = 'Inspector de Educación'
                insp_ge.save()
                insp_ge.cargos.add(Cargo.objects.get(entidad=e, clave_cargo='g_inspector_educacion'))
            except Exception as msg:
                mensaje += '<br>Cargo: g_inspector_educacion -- %s' % str(msg)
    except Exception as msg:
        mensaje += '<br>Entidad: %s -- %s' % (e, str(msg))
    return mensaje


@shared_task
def ejecutar_configurar_cargos_permisos():
    mensaje_final = 'Hecho.'
    for e in Entidad.objects.all():
        mensaje = ejecutar_configurar_cargos_permisos_entidad(e)
        mensaje_final += mensaje
    Aviso.objects.create(aviso=mensaje_final, fecha=now(), aceptado=True)
    return True


@shared_task
def ejecutar_configurar_menus_centros_educativos():
    from gauss.constantes import Menus_Centro_Educativo
    from entidades.menus_entidades import TiposCentro
    mensaje = 'Hecho.'
    for e in Entidad.objects.all():
        try:
            if e.entidadextra.tipo_centro in TiposCentro:
                Menu.objects.filter(entidad=e).delete()
                for m in Menus_Centro_Educativo:
                    try:
                        md = Menu_default.objects.get(code_menu=m[0])
                        try:
                            Menu.objects.get(entidad=e, menu_default=md)
                        except:
                            Menu.objects.create(entidad=e, menu_default=md, texto_menu=m[1], pos=m[2])
                    except Exception as msg:
                        mensaje += '<br>Menu: %s -- %s' % (m, str(msg))
                        Aviso.objects.create(aviso=mensaje, fecha=now())
        except Exception as msg:
            mensaje += '<br>Entidad: %s -- %s' % (e, str(msg))
            Aviso.objects.create(aviso=mensaje, fecha=now(), aceptado=True)
    return True


@shared_task
def ejecutar_configurar_docs_conf_educarioja():
    from entidades.menus_entidades import TiposCentro
    mensaje = 'Hecho.'
    for e in Entidad.objects.all():
        try:
            if e.entidadextra.tipo_centro in TiposCentro:
                header = render_to_string('cabecera_general_rioja.html', {'entidad': e})
                doc_confs = DocConfEntidad.objects.filter(entidad=e)
                if doc_confs.count() == 0:
                    doc_confs = [DocConfEntidad.objects.create(entidad=e, predeterminado=True, header=header,
                                                               footer='', nombre='Configuración predeterminada',
                                                               margintop=35)]
                else:
                    for doc_conf in doc_confs:
                        doc_conf.header = header
                        doc_conf.footer = ''
                        doc_conf.margintop = 40
                        doc_conf.marginleft = 20
                        doc_conf.marginright = 20
                        doc_conf.headerspacing = 15
                        doc_conf.save()
        except Exception as msg:
            mensaje += '<br>Entidad: %s -- %s' % (e, str(msg))
            Aviso.objects.create(aviso=mensaje, fecha=now(), aceptado=True)
    return True


@shared_task
def ejecutar_crea_calalumce_cev():
    from programaciones.models import CalAlumValor, CalAlumCE, CalAlumCEv
    cavs = CalAlumValor.objects.all()
    errores = ''
    for cav in cavs:
        try:
            alumno = cav.ca.alumno
            cuaderno = cav.ca.cp
            cevps = cav.ca.cie.cevps
            cev = cevps.cev
            # Comprobamos que no hay más de un calalumce por alumno y cep. Borramos si hay más de uno.
            calalumces = CalAlumCE.objects.filter(cp=cuaderno, alumno=alumno, cep=cevps.cepsec)
            if calalumces.count() > 1:
                for calalumce in calalumces:
                    calalumce.calalumcev_set.all().delete()
                calalumces.delete()
            # Fin de la comprobación
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
        except Exception as msg:
            errores += '<br>%s' % str(msg)
    Aviso.objects.create(aviso='ejecutar_crea_calalumce_cev terminado.<br>%s' % errores, fecha=now(), aceptado=True)
    return True
