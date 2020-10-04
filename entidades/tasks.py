# -*- coding: utf-8 -*-
import logging
import unicodedata
import string
import xlrd
from difflib import get_close_matches
from celery import shared_task
from django.utils.timezone import timedelta, datetime, now
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils.encoding import smart_text
from estudios.models import Grupo, Gauser_extra_estudios, Materia, Matricula
from entidades.models import Subentidad, Cargo, Gauser_extra, CargaMasiva, Entidad, EntidadExtra, \
    EntidadExtraExpediente, EntidadExtraExpedienteOferta, Ronda, Menu
from autenticar.models import Gauser, Permiso, Menu_default
from gauss.constantes import PROVINCIAS, CODE_CONTENEDOR
from bancos.views import asocia_banco_ge

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


def create_usuario(datos, carga, tipo):
    dni = datos['dni' + tipo] if len(datos['dni' + tipo]) > 6 else 'DNI inventado para generar error en el try'
    try:
        gauser = Gauser.objects.get(dni=dni)
        logger.info('Existe Gauser con dni %s' % dni)
    except ObjectDoesNotExist:
        logger.warning('No existe Gauser con dni %s' % dni)
        try:
            gauser_extra = Gauser_extra.objects.get(id_entidad=datos['id_socio'], ronda=carga.ronda)
            gauser = gauser_extra.gauser
            logger.warning('Encontrado Gauser y Gauser_extra con id_socio %s' % (datos['id_socio']))
        except ObjectDoesNotExist:
            gauser = None
            logger.warning('No existe Gauser con id_socio %s' % (datos['id_socio']))
        except MultipleObjectsReturned:
            gauser_extra = Gauser_extra.objects.filter(id_entidad=datos['id_socio'], ronda=carga.ronda)[0]
            logger.warning('Existen varios Gauser_extra asociados al Gauser encontrado. Se elige %s' % (gauser_extra))
            gauser = gauser_extra.gauser
    except MultipleObjectsReturned:
        gauser = Gauser.objects.filter(dni=dni)[0]
        logger.warning('Existen varios Gauser con el mismo DNI. Se elige %s' % (gauser))

    if gauser:
        try:
            gauser_extra = Gauser_extra.objects.get(gauser=gauser, ronda=carga.ronda)
            mensaje = 'Existe el g_e %s con el dni %s. No se vuelve a crear fff.' % (gauser, dni)
            logger.info(mensaje)
        except ObjectDoesNotExist:
            gauser_extra = None
            logger.warning('No existe Gauser_extra asociado al Gauser %s, deberemos crearlo fff' % (gauser))
        except MultipleObjectsReturned:
            ges = Gauser_extra.objects.filter(gauser=gauser, ronda=carga.ronda)
            gauser_extra = ges[0]
            # Podríamos escribir ges.exclude(id=gauser_extra.id).delete(), pero como hay un error porque
            # falta el nregistro en vut_vivienda necesito hacer esta triquiñuela para no duplicar usuarios:
            for ge_borrar in ges.exclude(id=gauser_extra.id):
                try:
                    ge_borrar.delete()
                except:
                    entidad, c = Entidad.objects.get_or_create(code=CODE_CONTENEDOR)
                    ge_borrar.ronda = entidad.ronda
                    ge_borrar.save()
                    logger.warning('Gauser_extra asociados al Gauser %s, desplazado al contenedor.' % (gauser))
            logger.warning('Varios Gauser_extra asociados al Gauser %s, se borran todos menos uno.' % (gauser))
            mensaje = 'Varios Gauser_extra asociados al Gauser %s, se borran todos menos uno.' % (gauser)
            logger.info(mensaje)
    else:
        gauser_extra = None

    if not gauser:
        if datos['nombre' + tipo] and datos['apellidos' + tipo]:
            nombre = datos['nombre' + tipo]
            apellidos = datos['apellidos' + tipo]
            usuario = crear_nombre_usuario(nombre, apellidos)
            gauser = Gauser.objects.create_user(usuario, email=datos['email' + tipo].lower(),
                                                password=datos['dni' + tipo], last_login=now())
            gauser.first_name = string.capwords(nombre.title()[0:28])
            gauser.last_name = string.capwords(apellidos.title()[0:28])
            gdata = {'dni': datos['dni' + tipo], 'telfij': datos['telefono_fijo' + tipo], 'sexo': datos['sexo' + tipo],
                     'telmov': datos['telefono_movil' + tipo], 'localidad': datos['localidad' + tipo],
                     'address': datos['direccion' + tipo], 'provincia': get_provincia(datos['provincia' + tipo]),
                     'nacimiento': devuelve_fecha(datos['nacimiento' + tipo]), 'postalcode': datos['cp' + tipo],
                     'fecha_alta': devuelve_fecha(datos['fecha_alta' + tipo])}
            for key, value in gdata.items():
                setattr(gauser, key, value)
            gauser.save()
        else:
            mensaje = 'No se ha podido crear un usuario porque no se han indicado nombre y apellidos'
            logger.warning(mensaje)
    if gauser and not gauser_extra:
        if 'id_organizacion' + tipo in datos:
            id_organizacion = datos['id_organizacion' + tipo]
        else:
            id_organizacion = datos['id_socio' + tipo]
        gauser_extra = Gauser_extra.objects.create(gauser=gauser, ronda=carga.ronda, activo=True,
                                                   id_entidad=datos['id_socio' + tipo],
                                                   num_cuenta_bancaria=datos['iban' + tipo],
                                                   observaciones=datos['observaciones' + tipo],
                                                   id_organizacion=id_organizacion)
        try:
            asocia_banco_ge(gauser_extra)
        except:
            mensaje = 'El IBAN asociado a %s parece no ser correcto. No se ha podido asociar una entidad bancaria al mismo.' % (
                    gauser.first_name.decode('utf8') + ' ' + gauser.last_name.decode('utf8'))
            logger.info(mensaje)
    if gauser_extra:
        logger.info('antes de subentidades')
        if datos['subentidades' + tipo]:
            logger.info('entra en subentidades')
            # La siguientes dos líneas no se si funcionarán en python3 debido a que filter en python3 no devuelve
            # una lista. Incluida la conversión list() para evitar errores:
            # http://stackoverflow.com/questions/3845423/remove-empty-strings-from-a-list-of-strings
            subentidades_id = list(filter(None, datos['subentidades' + tipo].replace(' ', '').split(',')))
            logger.info('entra en subentidades %s' % subentidades_id)
            subentidades = Subentidad.objects.filter(id__in=subentidades_id, entidad=carga.ronda.entidad,
                                                     fecha_expira__gt=datetime.today())
            gauser_extra.subentidades.add(*subentidades)
        if datos['perfiles' + tipo]:
            logger.info('entra en perfiles')
            cargos_id = list(filter(None, datos['perfiles' + tipo].replace(' ', '').split(',')))
            cargos = Cargo.objects.filter(id__in=cargos_id, entidad=carga.ronda.entidad)
            gauser_extra.cargos.add(*cargos)

    if gauser_extra:
        Gauser_extra_estudios.objects.get_or_create(ge=gauser_extra)
    return gauser_extra


def carga_masiva_tipo_EXCEL(carga):
    f = carga.fichero.read()
    book = xlrd.open_workbook(file_contents=f)
    sheet = book.sheet_by_index(0)
    # Get the keys from line 5 of excel file:
    keys0 = [sheet.cell(4, col_index).value for col_index in range(sheet.ncols)]
    # Get the keys removing accents:
    # keys = [filter(lambda x: x in set(string.printable), k) for k in keys0]
    keys = keys0
    # Join the two earlier lines in one:
    # kk = [filter(lambda x: x in set(string.printable), sheet.cell(4, col_index).value) for col_index in xrange(sheet.ncols)]

    # Keys Reference for Personal:
    krp = {'Empleado': 'empleado', 'DNI/Pasaporte': 'dni', 'Tipo de personal': 'subentidades',
           'Puesto': 'perfiles',
           'Fecha de nacimiento': 'nacimiento', 'Activo': 'activo',
           'Fecha del último nombramiento': 'fecha_alta',
           'Fecha de cese': 'baja', 'Dirección': 'direccion', 'Código Postal': 'cp', 'Sexo': 'sexo',
           'Localidad': 'localidad', 'Provincia': 'provincia', 'Teléfono 1': 'telefono_fijo',
           'Teléfono 2': 'telefono_movil', 'Correo electrónico': 'email', 'Especialidad': 'especialidad'}
    pdic = {'empleado': '', 'dni': '', 'subentidades': '', 'perfiles': '', 'nacimiento': '', 'activo': '',
            'fecha_alta': '', 'baja': '', 'direccion': '', 'cp': '', 'sexo': '', 'localidad': '',
            'iban': '',
            'provincia': '', 'telefono_fijo': '', 'telefono_movil': '', 'email': '', 'especialidad': ''}
    # Keys Reference for Alumnos:
    kra = {'Alumno': 'alumno', 'Estado Matrícula': 'estado_matricula', 'Nº id. Racima': 'id_socio',
           'DNI/Pasaporte': 'dni', 'Dirección': 'direccion', 'Código postal': 'cp',
           'Localidad de residencia': 'localidad', 'Fecha de nacimiento': 'nacimiento',
           'Provincia de residencia': 'provincia', 'Teléfono': 'telefono_fijo',
           'Teléfono móvil': 'telefono_movil',
           'Correo electrónico': 'email', 'Curso': 'curso', 'Nº historial académico': 'id_organizacion',
           'Grupo': 'subentidades', 'Primer apellido': 'last_name1', 'Segundo apellido': 'last_name2',
           'Nombre': 'nombre', 'DNI/Pasaporte Primer tutor': 'dni_tutor1',
           'Primer apellido Primer tutor': 'last_name1_tutor1',
           'Segundo apellido Primer tutor': 'last_name2_tutor1', 'Nombre Primer tutor': 'nombre_tutor1',
           'Tfno. Primer tutor': 'telefono_fijo_tutor1',
           'Tfno. Móvil Primer tutor': 'telefono_movil_tutor1',
           'Sexo Primer tutor': 'sexo_tutor1', 'DNI/Pasaporte Segundo tutor': 'dni_tutor2',
           'Primer apellido Segundo tutor': 'last_name1_tutor2',
           'Segundo apellido Segundo tutor': 'last_name2_tutor2',
           'Nombre Segundo tutor': 'nombre_tutor2', 'Tfno. Segundo tutor': 'telefono_fijo_tutor2',
           'Tfno. Móvil Segundo tutor': 'telefono_movil_tutor2', 'Sexo Segundo tutor': 'sexo_tutor2',
           'Localidad de nacimiento': 'localidad_nacimiento', 'Nacionalidad': 'nacionalidad',
           'Código País nacimiento': 'code_pais_nacimiento', 'País de nacimiento': 'pais_nacimiento',
           'Código Provincia nacimiento': 'code_provincia_nacimiento',
           'Pago   Seguro escolar': 'pago_seguro_escolar', 'Sexo': 'sexo',
           'Año de la matrícula': 'year_matricula', 'Nº de matrículas en este curso': 'num_matriculas',
           'Observaciones de la matrícula': 'observaciones_matricula', 'Número SS': 'num_ss',
           'Nº expte. en el centro': 'num_exp', 'Fecha de la matrícula': 'fecha_matricula',
           'Nº de matrículas en el expediente': 'num_matriculas_exp',
           'Repeticiones en el curso': 'rep_curso',
           'Familia numerosa': 'familia_numerosa', 'Lengua materna': 'lengua_materna',
           'Año incorporación al sistema educativo': 'year_incorporacion', 'Bilingüe': 'bilingue',
           'Correo electrónico Primer tutor': 'email_tutor1',
           'Correo electrónico Segundo tutor': 'email_tutor2',
           'Autoriza el uso de imagenes': 'uso_imagenes'}

    adic = {'alumno': '', 'estado_matricula': '', 'id_socio': '', 'dni': '', 'direccion': '', 'cp': '',
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
            'observaciones_tutor1': '', 'observaciones_tutor2': '',
            'perfiles_tutor1': '', 'perfiles_tutor2': '', }

    if len(keys) < 30:  # This implies the file is from Personal (RegInfPerCen.xls)
        for row_index in range(5, sheet.nrows):
            d = pdic
            # d = {krp[keys[col_index]]: sheet.cell(row_index, col_index).value for col_index in
            #      xrange(sheet.ncols)}
            for col_index in range(sheet.ncols):
                d[krp[keys[col_index]]] = sheet.cell(row_index, col_index).value
            d['apellidos'] = d['empleado'].split(', ')[0]
            d['nombre'] = d['empleado'].split(', ')[1]
            d['id_socio'] = d['dni']
            clave_ex = d['subentidades'].replace(' ', '_').lower()

            sub1s = Subentidad.objects.filter(entidad=carga.ronda.entidad, clave_ex=clave_ex)
            if sub1s.count() > 0:
                sub1 = sub1s[0]
            else:
                sub1 = Subentidad.objects.create(nombre=d['subentidades'], mensajes=True, edad_min=18,
                                                 entidad=carga.ronda.entidad, clave_ex=clave_ex, edad_max=67)
            # try:
            #     sub1 = Subentidad.objects.get(entidad=carga.ronda.entidad, clave_ex=clave_ex)
            # except:
            #     sub1 = Subentidad.objects.create(nombre=d['subentidades'], mensajes=True, edad_min=18,
            #                                      entidad=carga.ronda.entidad, clave_ex=clave_ex, edad_max=67)

            sub2s = Subentidad.objects.filter(nombre=d['perfiles'], entidad=carga.ronda.entidad)
            if sub2s.count() > 0:
                sub2 = sub2s[0]
            else:
                sub2 = Subentidad.objects.create(nombre=d['perfiles'], mensajes=True, edad_min=18,
                                                 edad_max=67, entidad=carga.ronda.entidad, parent=sub1)
            # try:
            #     sub2 = Subentidad.objects.get(nombre=d['perfiles'], entidad=carga.ronda.entidad)
            # except:
            #     sub2 = Subentidad.objects.create(nombre=d['perfiles'], mensajes=True, edad_min=18,
            #                                      edad_max=67, entidad=carga.ronda.entidad, parent=sub1)
            cargo = Cargo.objects.get_or_create(entidad=carga.ronda.entidad, cargo=d['subentidades'])
            d['subentidades'] = str(sub1.id) + ',' + str(sub2.id)
            d['activo'] = True if 'S' in d['activo'] else False
            d['perfiles'] = str(cargo[0].id)
            d['observaciones'] = d['especialidad'] + '<br>Causa baja el ' + d['baja']
            create_usuario(d, carga, '')
    else:
        fecha_expira = carga.ronda.entidad.ronda.fin + timedelta(days=5)  # Expiración para los grupos
        subas = Subentidad.objects.filter(clave_ex='alumnos', entidad=carga.ronda.entidad)
        if subas.count() > 0:
            suba = subas[0]
        else:
            suba = Subentidad.objects.create(nombre='Alumnos', mensajes=True, clave_ex='alumnos',
                                             entidad=carga.ronda.entidad, edad_min=12, edad_max=67)
        # try:
        #     suba = Subentidad.objects.get(clave_ex='alumnos', entidad=carga.ronda.entidad)
        # except:
        #     suba = Subentidad.objects.create(nombre='Alumnos', mensajes=True, clave_ex='alumnos',
        #                                      entidad=carga.ronda.entidad, edad_min=12, edad_max=67)

        subps = Subentidad.objects.filter(clave_ex='madres_padres', entidad=carga.ronda.entidad)
        if subps.count() > 0:
            subp = subps[0]
        else:
            subp = Subentidad.objects.create(nombre='Madres/Padres', mensajes=True,
                                             entidad=carga.ronda.entidad,
                                             clave_ex='madres_padres', edad_min=18, edad_max=67)
        # try:
        #     subp = Subentidad.objects.get(clave_ex='madres_padres', entidad=carga.ronda.entidad)
        # except:
        #     subp = Subentidad.objects.create(nombre='Madres/Padres', mensajes=True, entidad=carga.ronda.entidad,
        #                                      clave_ex='madres_padres', edad_min=18, edad_max=67)
        cargoa = Cargo.objects.get_or_create(cargo='Alumno/a', entidad=carga.ronda.entidad, nivel=6)
        cargop = Cargo.objects.get_or_create(cargo='Padre/Madre', entidad=carga.ronda.entidad, nivel=6)
        for row_index in range(5, sheet.nrows):
            try:
                d = adic
                # d = {kra[keys[col_index]]: sheet.cell(row_index, col_index).value for col_index in
                #      xrange(sheet.ncols)}
                for col_index in range(sheet.ncols):
                    d[kra[keys[col_index]]] = sheet.cell(row_index, col_index).value
                d['apellidos'] = '%s %s' % (d['last_name1'], d['last_name2'])
                d['apellidos_tutor1'] = '%s %s' % (d['last_name1_tutor1'], d['last_name2_tutor1'])
                d['apellidos_tutor2'] = '%s %s' % (d['last_name1_tutor2'], d['last_name2_tutor2'])
                # sub = Subentidad.objects.get_or_create(nombre=d['subentidades'], mensajes=True,
                #                                        entidad=carga.ronda.entidad, parent=suba,
                #                                        edad_min=12, edad_max=67, fecha_expira=fecha_expira)
                # d['subentidades'] = str(sub[0].id) + ',' + str(suba.id)
                grupo, c = Grupo.objects.get_or_create(nombre=d['subentidades'], ronda=carga.ronda)
                if c:
                    logger.info('Carga masiva xls. Se crea grupo %s' % grupo.nombre)
                d['subentidades'] = str(suba.id)
                d['subentidades_tutor1'] = str(subp.id)
                d['subentidades_tutor2'] = str(subp.id)
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

                tutor1 = create_usuario(d, carga, '_tutor1')
                if tutor1:
                    tutor1.cargos.add(cargop[0])
                    tutor1.save()
                tutor2 = create_usuario(d, carga, '_tutor2')
                if tutor2:
                    tutor2.cargos.add(cargop[0])
                    tutor2.save()
                gauser_extra = create_usuario(d, carga, '')
                gauser_extra.tutor1 = tutor1
                gauser_extra.tutor2 = tutor2
                gauser_extra.subentidades.add(suba)
                gauser_extra.cargos.add(cargoa[0])
                gauser_extra.save()
                gauser_extra.gauser_extra_estudios.grupo = grupo
                gauser_extra.gauser_extra_estudios.save()
            except:
                logger.info('Error: %s -- %s' % (d['apellidos'], d['apellidos_tutor1']))
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
                    carga.incidencias += '<p>Duplicidad con alumno  %s (Nº de Racima: %s)</p>' % (
                        sheet.cell(row_index, dict_names['Alumno']).value, alumno_matricula)
                else:
                    carga.incidencias += '<p>No existe el alumno %s con Nº de Racima: %s</p>' % (
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
                    carga.incidencias += '<p>Duplicidad con materia %s (código: %s)</p>' % (
                        sheet.cell(row_index, dict_names['Materia']).value, materia_matricula)
                else:
                    carga.incidencias += '<p>No se encuentra materia con código: %s</p>' % (materia_matricula)
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

    entidades_no_existen = []
    entidades_existen = []
    # Get the keys from line 5 of excel file:
    dict_names = {}
    for col_index in range(sheet.ncols):
        dict_names[sheet.cell(4, col_index).value] = col_index
    for row_index in range(5, sheet.nrows):
        code_entidad = int(sheet.cell(row_index, dict_names['Código']).value)
        entidad, created = Entidad.objects.get_or_create(code=code_entidad)
        # Copiar los permisos que tiene el director del Ciudad de Haro
        permisos_director = Cargo.objects.get(entidad__code=26008475, cargo__icontains='Director').permisos.all()
        if created:
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
            cargo_director = Cargo.objects.create(entidad=entidad, cargo='Director/a', nivel=1)
            cargo_director.permisos.add(*permisos_director)
            Cargo.objects.create(entidad=entidad, nombre='Jefe/a de Estudios', nivel=2)
            Cargo.objects.create(entidad=entidad, nombre='Profesor/a', nivel=3)
            Cargo.objects.create(entidad=entidad, nombre='Maestro/a', nivel=3)
            Cargo.objects.create(entidad=entidad, nombre='Alumno/a')
            Cargo.objects.create(entidad=entidad, nombre='Madre/Padre')
        if not entidad.ronda:
            y1, y2 = datetime.today().year, datetime.today().year + 1
            inicio = datetime.strptime("1/9/%s" % y1, "%d/%m/%Y")
            fin = datetime.strptime("31/8/%s" % y2, "%d/%m/%Y")
            ronda = Ronda.objects.create(nombre="%s/%s" % (y1, y2), entidad=entidad, inicio=inicio, fin=fin)
            entidad.ronda = ronda
            entidad.save()
        # Menus:
        menus = [('acceso_configuracion', 'Configuración', 1),
                 ('acceso_perfiles_permisos', 'Establecer perfiles y permisos a usuarios', 1),
                 ('acceso_datos_entidad', 'Datos de la entidad', 1), ('acceso_redactar_mensaje', 'Redactar mensaje', 1),
                 ('acceso_vista_calendario', 'Vista calendario', 1), ('acceso_documentos', 'Documentos', 1),
                 ('acceso_carga_masiva_horarios', 'Carga masiva horarios', 1),
                 ('acceso_cupo_profesorado', 'Cupo de profesores', 1), ('acceso_absentismo', 'Absentismo', 1),
                 ('acceso_gestionar_conductas', 'Establecer conductas y sanciones', 1),
                 ('acceso_informes_seguimiento', 'Informe de seguimiento', 1),
                 ('acceso_noticias_web', 'Noticias WEB', 1), ('acceso_configura_cursos', 'Configuración de cursos', 1),
                 ('cc_valorar_mis_alumnos', 'Valorar a mis alumnos', 1),
                 ('acceso_programaciones_ccff', 'Programaciones CCFF', 1),
                 ('acceso_conv_template', 'Plantillas de convocatorias', 1),
                 ('acceso_grupos_domotica', 'Agrupaciones de dispositivos', 1),
                 ('acceso_gestionar_perfiles', 'Crear Perfiles/Cargos/Organigrama', 2),
                 ('acceso_gestion_entidad', 'Equipo directivo\n ', 2),
                 ('acceso_crear_usuarios', 'Añadir un nuevo usuario', 2),
                 ('acceso_mensajes_enviados', 'Mensajes enviados', 2),
                 ('acceso_define_horarios', 'editar horarios\n ', 2), ('acceso_reparaciones', 'Reparaciones', 2),
                 ('acceso_sancionar_conductas', 'Sancionar conductas', 2),
                 ('acceso_informes_tareas', 'Informe con tareas', 2),
                 ('acceso_configura_grupos', 'Configuración de grupos', 2),
                 ('cc_valorar_cualquier_alumno', 'Valorar a cualquier alumno', 2),
                 ('acceso_resultados_aprendizaje', 'Resultados de aprendizaje', 2),
                 ('acceso_conv_reunion', 'Realizar convocatorias', 2),
                 ('acceso_configura_domotica', 'Configurar domótica', 2), ('acceso_carga_masiva', 'Carga masiva', 3),
                 ('acceso_getion_bajas', 'Gestión de bajas', 3), ('acceso_mensajes', 'Correo y mensajería', 3),
                 ('acceso_mensajes_recibidos', 'Mensajes recibidos', 3),
                 ('acceso_actividades_horarios', 'Actividades del horario', 3),
                 ('acceso_expediente_sancionador', 'Expediente sancionador', 3),
                 ('acceso_actividades', 'Actividades extraescolares', 3),
                 ('acceso_cuerpos_funcionarios', 'Cuerpos de funcionarios', 3),
                 ('acceso_configura_pendientes', 'Configurar materias pendientes', 3),
                 ('configura_ccs', 'Ponderar competencias clave', 3),
                 ('acceso_redactar_actas_reunion', 'Redactar actas', 3),
                 ('acceso_gestionar_subentidades', 'Departamentos/Secciones', 4),
                 ('acceso_reserva_plazas', 'Reserva de plazas', 4), ('acceso_calendario', 'Calendario', 4),
                 ('acceso_cargar_programaciones', 'Cargar programaciones', 4),
                 ('acceso_evaluar_materias', 'Evaluación de pendientes\n ', 4),
                 ('acceso_control_asistencia_reunion', 'Control de asistencia', 4),
                 ('acceso_miembros_entidad', 'Personas en el iES\n ', 5),
                 ('acceso_gestion_documental', 'Gestión documental', 5),
                 ('acceso_profesores_centro_educativo', 'Profesores del centro', 5),
                 ('acceso_firmar_actas_reunion', 'Firmar actas', 5),
                 ('acceso_listados_usuarios', 'Listados de usuarios', 6), ('acceso_horarios', 'Horarios', 6),
                 ('acceso_lectura_actas_reunion', 'Leer actas', 6),
                 ('acceso_aspectos_pga', 'Aspectos generales de la PGA', 6),
                 ('acceso_horario_usuarios', 'Horarios profesores\n ', 7), ('acceso_cupos', 'Cupos IES\n ', 7),
                 ('acceso_dependencias_entidad', 'Dependencias', 7), ('acceso_pec', 'Proyecto Educativo del Centro', 7),
                 ('acceso_horarios_subentidades', 'Horarios grupos', 8),
                 ('acceso_gestionar_rondas', 'cursos escolares', 8),
                 ('acceso_acciones_usuarios1', 'Acciones DOCENTES\n ', 8),
                 ('acceso_departamentos_centro_educativo', 'Departamentos del centro', 8),
                 ('acceso_registro', 'Registro', 9), ('acceso_convivencia', 'Convivencia', 9),
                 ('acceso_horario_aulas', 'Horarios aulas', 9),
                 ('acceso_guardias_horarios', 'Guardias profesores\n ', 10),
                 ('acceso_informes_usuarios', 'Informes', 10), ('acceso_tutores_entidad', 'Tutores', 11),
                 ('acceso_web', 'página WEB\n ', 11), ('acceso_seguimiento_educativo', 'Seguimiento educativo', 11),
                 ('acceso_actillas', 'Actillas', 12),
                 ('acceso_estudios_centro_educativo', 'Configuración de estudios', 12),
                 ('acceso_horarios_alumnos', 'Alumnos', 13), ('acceso_competencias_clave', 'Competencias clave', 13),
                 ('acceso_programaciones_didacticas', 'Programaciones didácticas', 14),
                 ('acceso_reuniones', 'Reuniones', 15), ('acceso_domotica', 'Domótica', 16)]
        for m in menus:
            md = Menu_default.objects.get(code_menu=m[0])
            Menu.objects.get_or_create(entidad=entidad, menu_default=md, texto_menu=m[1], pos=m[2])
        ee, created = EntidadExtra.objects.get_or_create(entidad=entidad)
        ee.titularidad = sheet.cell(row_index, dict_names['Titularidad']).value
        ee.tipo_centro = sheet.cell(row_index, dict_names['Tipo centro']).value
        try:
            code_entidad_padre = int(sheet.cell(row_index, dict_names['IES del que depende']).value)
            ee.depende_de = Entidad.objects.get(code=code_entidad_padre)
        except:
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

        # Crear usuario gauss para la entidad
        ge, c = Gauser_extra.objects.get_or_create(gauser=gauss, ronda=entidad.ronda, activo=True)
        if c:
            permisos = Permiso.objects.all()
            ge.permisos.add(*permisos)
        # Crear el usuario entidad:
        # Código para crear usuario con todos los permisos disponibles a través de los cargos:
        try:
            gauser_entidad = Gauser.objects.get(username=entidad.code)
        except:
            email = 'inventado@%s.com' % entidad.code
            gauser_entidad = Gauser.objects.create_user(entidad.code, email, entidad.code, last_login=now())
        try:
            Gauser_extra.objects.get(gauser=gauser_entidad, ronda=entidad.ronda)
        except:
            g_e_entidad = Gauser_extra.objects.create(gauser=gauser_entidad, ronda=entidad.ronda, activo=True)
            g_e_entidad.permisos.add(*permisos_director)
    print('Entidades existen:\n')
    print(entidades_existen)
    print('Entidades no existen:\n')
    print(entidades_no_existen)


@shared_task
def carga_masiva_from_excel():
    cargas_necesarias = CargaMasiva.objects.filter(cargado=False)
    for carga in cargas_necesarias:
        try:
            if carga.tipo == 'EXCEL':
                carga_masiva_tipo_EXCEL(carga)
            elif carga.tipo == 'PENDIENTES':
                carga_masiva_tipo_PENDIENTES(carga)
            elif carga.tipo == 'CENTROSRACIMA':
                carga_masiva_tipo_CENTROSRACIMA(carga)
            elif carga.tipo == 'EXCELMDB':
                carga_masiva_tipo_CENTROSRACIMA(carga)
        except:
            logger.info('Carga masiva xls se produce error con carga.id=%s' % carga.id)
            carga.error = True
            carga.cargado = True
            carga.save()
        carga.cargado = True
        carga.save()
    return True
