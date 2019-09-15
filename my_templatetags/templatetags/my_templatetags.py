# -*- coding: utf-8 -*-
from dateutil.tz import tzlocal
from django.template import Library
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.utils.text import normalize_newlines

# from autenticar.models import Gauser_extra, Permiso
from autenticar.models import Permiso
from calendario.models import Vevent
from entidades.models import Gauser_extra, Menu, Ronda, Filtrado, Cargo, Subentidad, ge_id_patron_match, user_auto_id

import re
from datetime import date, datetime
from bancos.views import num_cuenta2iban
from compraventa.models import Comprador
from documentos.models import Permiso_Ges_documental, Ges_documental, Etiqueta_documental
from formularios.models import Gform
from gauss.funciones import usuarios_de_gauss, usuarios_ronda
from contabilidad.models import Remesa_emitida
from web.models import Html_web
from horarios.models import Falta_asistencia, Sesion
from cupo.models import Materia_cupo, Profesor_cupo
from programaciones.models import Gauser_extra_programaciones

MESES = (
    '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre',
    'diciembre',)
register = Library()

@register.filter
def auto_id(g_e):
    num = Gauser_extra.objects.filter(ronda=g_e.ronda, id_entidad=g_e.id_entidad).count()
    if num > 1 or not ge_id_patron_match(g_e):
        user_auto_id(g_e)
    return g_e.id_entidad


@register.filter
def number_range(n):
    return range(1, n + 1)


@register.filter
def cargos_entidad(entidad):
    return Cargo.objects.filter(entidad=entidad).order_by('nivel')

@register.filter
def subentidades_entidad(entidad):
    return Subentidad.objects.filter(entidad=entidad, fecha_expira__gt=datetime.now().date()).order_by('edad_min')

@register.filter
def is_campo_checked(filtrado, campo):
    campos = filtrado.campof_set.all().values_list('campo', flat=True)
    return 'checked' if (campo in campos) else ''


@register.filter
def value_dict(dict, key):
    return dict[key]


# Módulo de cupo
@register.filter
def interinos(cupo):
    return Profesor_cupo.objects.filter(profesorado__cupo=cupo, tipo='INT').order_by('profesorado__especialidad')

@register.filter
def profesores_especialidad(especialidad):
    return Profesor_cupo.objects.filter(profesorado__especialidad=especialidad)

@register.filter
def profesores_especialidad2(especialidad, ronda):
    return Gauser_extra_programaciones.objects.filter(ge__ronda=ronda, puesto=especialidad.nombre)

@register.filter
def materias_filtro(filtro):
    materias_cupo = Materia_cupo.objects.filter(cupo=filtro.cupo, nombre__icontains=filtro.filtro)
    return materias_cupo

###########

@register.filter
def edita_convocatoria(g_e, convocatoria):
    if g_e.gauser.username == 'gauss' or g_e.has_permiso('edita_convocatorias'):
        return True
    elif convocatoria.creador == g_e.gauser or convocatoria.convoca == g_e.gauser:
        return True
    elif g_e.has_permiso('edita_convocatorias'):
        subentidades_convocadas = convocatoria.convocados.all()
        for sub in g_e.subentidades.all():
            if sub in subentidades_convocadas:
                return True
    else:
        return False


@register.filter
def redacta_acta(g_e, acta):
    if g_e.gauser.username == 'gauss' or g_e.has_permiso('redacta_cualquier_acta'):
        return True
    elif acta.convocatoria.creador == g_e.gauser and acta.redacta == g_e.gauser:
        return True
    elif g_e.has_permiso('redacta_actas_subentidades'):
        subentidades_convocadas = acta.convocatoria.convocados.all()
        for sub in g_e.subentidades.all():
            if sub in subentidades_convocadas:
                return True
    else:
        return False


# Módulo de Horarios
@register.filter
def faltas_asistencia(g_e):
    return Falta_asistencia.objects.filter(g_e=g_e)


# Módulo de Formularios
@register.filter
def has_cuestionarios(g_e):
    subentidades = g_e.subentidades.all()
    cargos = g_e.cargos.all()
    cuestionarios = Gform.objects.filter(Q(subentidades_destino__in=subentidades) | Q(cargos_destino__in=cargos),
                                         propietario__entidad=g_e.ronda.entidad, activo=True)
    return True if cuestionarios.count() > 0 else False


@register.filter
def gvalor(ginput):
    valor = getattr(ginput, ginput.tipo)
    return valor if valor else ''


@register.filter
def cuestionarios(g_e):
    cuestionarios = []
    g_es = g_e.unidad_familiar
    for ge in g_es:
        cues_ge = []
        if ge == g_e or ge.edad < 18:
            subentidades = ge.subentidades.all()
            cargos = ge.cargos.all()
            gforms = Gform.objects.filter(Q(subentidades_destino__in=subentidades) | Q(cargos_destino__in=cargos),
                                          propietario__entidad=g_e.ronda.entidad, activo=True,
                                          fecha_max_rellenado__gte=datetime.now()).distinct()
            cues_ge = [(gform, ge) for gform in gforms]
        cuestionarios += cues_ge

    # subentidades = g_e.subentidades.all()
    # cargos = g_e.cargos.all()
    # cuestionarios = Gform.objects.filter(Q(subentidades_destino__in=subentidades) | Q(cargos_destino__in=cargos),
    #                                      propietario__entidad=g_e.ronda.entidad, activo=True).distinct()
    return cuestionarios


# Módulo de Calendario

@register.filter
def evento_convocatoria(convocatoria):  # Returns True if it exists a vevent for convocatoria
    try:
        Vevent.objects.get(entidad=convocatoria.entidad, uid='convocatoria' + str(convocatoria.id))
        return True
    except:
        return False


@register.filter
def including_day(vevents, dia):
    dia_max = datetime.combine(dia, datetime.max.time())
    dia_min = datetime.combine(dia, datetime.min.time())
    return vevents.filter(Q(dtstart__lte=dia_max), Q(dtend__gte=dia_min) | Q(dtend__isnull=True)).order_by('dtstart')


@register.filter
def fecha_gte(fecha1, fecha2):
    fecha1 = fecha1.astimezone(tzlocal()).date() if type(fecha1) is datetime else fecha1
    fecha2 = fecha2.astimezone(tzlocal()).date() if type(fecha2) is datetime else fecha2
    if fecha1 >= fecha2:
        return True
    else:
        return False


@register.filter
def fecha_lte(fecha1, fecha2):
    fecha1 = fecha1.astimezone(tzlocal()).date() if type(fecha1) is datetime else fecha1
    fecha2 = fecha2.astimezone(tzlocal()).date() if type(fecha2) is datetime else fecha2
    if fecha1 <= fecha2:
        return True
    else:
        return False


@register.filter
def fecha_gt(fecha1, fecha2):
    fecha1 = fecha1.astimezone(tzlocal()).date() if type(fecha1) is datetime else fecha1
    fecha2 = fecha2.astimezone(tzlocal()).date() if type(fecha2) is datetime else fecha2
    if fecha1 > fecha2:
        return True
    else:
        return False


@register.filter
def fecha_lt(fecha1, fecha2):
    fecha1 = fecha1.astimezone(tzlocal()).date() if type(fecha1) is datetime else fecha1
    fecha2 = fecha2.astimezone(tzlocal()).date() if type(fecha2) is datetime else fecha2
    if fecha1 < fecha2:
        return True
    else:
        return False


@register.filter
def fecha_eq(fecha1, fecha2):
    fecha1 = fecha1.astimezone(tzlocal()).date() if type(fecha1) is datetime else fecha1
    fecha2 = fecha2.astimezone(tzlocal()).date() if type(fecha2) is datetime else fecha2
    if fecha1 == fecha2:
        return True
    else:
        return False


# Módulo de Contabilidad
@register.filter
def remesas_emitidas(politica):
    return Remesa_emitida.objects.filter(politica=politica, visible=True)[:3]


@register.filter
def total_remesas_emitidas(politica):
    return Remesa_emitida.objects.filter(politica=politica, visible=True).count()


@register.filter
def number_no_exentos(politica):
    exentos_id = politica.exentos.all().values_list('id', flat=True)
    return usuarios_de_gauss(politica.entidad, cargos=[politica.cargo]).exclude(gauser__id__in=exentos_id).count()


@register.filter
def no_exentos(politica, total=1000):
    no_ex = []
    # importes = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", politica.descuentos)))
    # Hacemos una secuencia de importes añadiendo el último valor lo suficientemente grande como para
    # asegurar que el número de hermanos es superado. Por ejemplo si importes es [30,20,15], después
    # de la siguiente líneas sería [30,20,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15]
    # importes = importes + [importes[-1] for i in range(20)]
    importes = politica.array_cuotas
    exentos_id = politica.exentos.all().values_list('id', flat=True)
    usuarios = usuarios_de_gauss(politica.entidad, cargos=[politica.cargo]).exclude(gauser__id__in=exentos_id)[:total]
    usuarios_id = []
    n = 0
    for usuario in usuarios:
        n += 1
        if usuario.id not in usuarios_id:
            familiares = usuario.unidad_familiar
            deudores = familiares.filter(id__in=usuarios)
            concepto = 'Familia' if deudores.count() > 1 else deudores[0].gauser.first_name
            usuarios_id += list(deudores.values_list('id', flat=True))
            n_cs = familiares.values_list('num_cuenta_bancaria', flat=True)
            try:
                cuenta_banca = [n_c.replace(' ', '') for n_c in n_cs if len(str(n_c)) > 18][0]
                estilo, title = "", "Cuenta bancaria: " + str(cuenta_banca)
            except:
                estilo, title = "color:red", "No hay cuenta bancaria asignada"
            no_ex.append('<span title="%s" style="%s">%s %s (%s)</span>' % (
                title, estilo, concepto, deudores[0].gauser.last_name, str(sum(importes[:deudores.count()]))))
    return no_ex


# Entidades
@register.filter
def rondas(entidad):
    return Ronda.objects.filter(entidad=entidad)


@register.filter
def usuarios_con_cargo(cargo):
    entidad = cargo.entidad
    return usuarios_de_gauss(entidad=entidad, cargos=[cargo])


@register.filter
def usuarios_en_subentidad(subentidad):
    entidad = subentidad.entidad
    return usuarios_de_gauss(entidad=entidad, subentidades=[subentidad])


# Funciones para el diseño web:
@register.filter
def rows_web(hw, tipo_row):
    return hw.rows_web.filter(tipo=tipo_row)


@register.filter
def escribe_href(enlace, tipo=''):
    if enlace.externo:
        return enlace.href
    else:
        try:
            hw = Html_web.objects.get(id=enlace.href, entidad=enlace.entidad)
            if tipo == 'title':
                return '%s  hw-%s' % (hw.nombre, hw.id)
            else:
                return 'hw-%s' % (hw.id)
        except:
            return enlace.href


@register.filter
def last_objeto(queryset):
    return queryset.reverse()[0]


@register.filter
def invierte(cantidad, total):
    return (int(total) - int(cantidad))


@register.filter
def precio(articulo):
    ofertas = [float(i) for i in Comprador.objects.filter(articulo=articulo).values_list('oferta', flat=True)]
    ofertas.append(float(articulo.precio))
    return max(ofertas)


@register.filter
def menus(entidad):
    return Menu.objects.filter(entidad=entidad, menu_default__tipo='Accesible', menu_default__nivel=1).distinct()


@register.filter
def permisos_menu(menu):
    return Permiso.objects.filter(Q(tipo=menu.menu_default.code_menu) | Q(code_nombre=menu.menu_default.code_menu))


@register.filter
def permisos_menu_seleccionados(menu, objecto):
    try:  # Si se cumple esta línea es porque objeto es del tipo Gauser_extra
        per_ge = objecto.permisos.all().values_list('code_nombre')
    except:  # Si se cumple el except es porque objeto es un queryset de permisos
        per_ge = objecto
    per_me = Permiso.objects.filter(
        Q(tipo=menu.menu_default.code_menu) | Q(code_nombre=menu.menu_default.code_menu)).values_list('code_nombre')
    com = list(set(per_ge) & set(per_me))
    return '%s de %s' % (len(com), len(per_me))


@register.filter
def socios_cargo(cargo):
    return Gauser_extra.objects.filter(cargos__in=[cargo])


@register.filter
def socios_subentidad(subentidad):
    return Gauser_extra.objects.filter(subentidades__in=[subentidad])


@register.filter
def nombre_cargo(gauser_extra):
    return gauser_extra.cargos.all().order_by('nivel')[0]


@register.filter
def has_cargos(gauser_extra, cargos_comprobar):
    if gauser_extra.gauser.username == 'gauss':
        return True
    else:
        cargos_comprobar = map(int, cargos_comprobar.split(','))
        p_ids = gauser_extra.cargos.all().values_list('nivel', flat=True)
        return len([nivel for nivel in p_ids if nivel in cargos_comprobar]) > 0


@register.filter
def documentos_carpeta(g_e, carpeta_id):  # Documentos de la carpeta indicada
    if carpeta_id == 'todas':
        doc_ids = Permiso_Ges_documental.objects.filter(gauser=g_e.gauser,
                                                        documento__propietario__entidad=g_e.ronda.entidad).values_list(
            'documento__id', flat=True)
        documentos = Ges_documental.objects.filter(
            Q(acceden__in=g_e.subentidades.all()) | Q(id__in=doc_ids)).distinct().order_by('creado')
    else:
        etiqueta = Etiqueta_documental.objects.get(id=carpeta_id)
        doc_ids = Permiso_Ges_documental.objects.filter(gauser=g_e.gauser, documento__etiqueta=etiqueta).values_list(
            'documento__id', flat=True)
        documentos = Ges_documental.objects.filter(Q(etiqueta=etiqueta),
                                                   Q(acceden__in=g_e.subentidades.all()) | Q(
                                                       id__in=doc_ids)).distinct().order_by('creado')

    return documentos


@register.filter
def permiso_documento(documento, g_e):  # Documentos de la carpeta indicada
    try:
        p = Permiso_Ges_documental.objects.get(gauser=g_e.gauser, documento=documento).permiso
    except:
        p = 'r'
    return p


@register.filter
def lista_loop(fecha):
    return range(fecha.weekday())


# @register.filter
# def has_perfiles(gauser_extra, perfiles_comprobar):
# if gauser_extra.gauser.username == 'gauss':
# return True
#     else:
#         perfiles_comprobar = map(int, perfiles_comprobar.split(','))
#         p_ids = gauser_extra.perfiles.all().values_list('pk', flat=True)
#         return len([perfil for perfil in p_ids if perfil in perfiles_comprobar]) > 0


@register.filter
def has_permiso(gauser_extra, permiso_comprobar):
    if gauser_extra.gauser.username == 'gauss' or permiso_comprobar == 'libre':
        return True
    else:
        try:
            permiso = Permiso.objects.get(code_nombre=permiso_comprobar)
        except:
            return False
        if permiso in gauser_extra.permisos.all():
            return True
        else:
            for cargo in gauser_extra.cargos.all():
                if permiso in cargo.permisos.all():
                    return True
        return False
        # permisos1 = gauser_extra.permisos.all().values_list('id', flat=True)
        # permisos2 = []  # gauser_extra.perfiles.all().values_list('permisos__id', flat=True)
        # permisos3 = gauser_extra.cargos.all().values_list('permisos__id', flat=True)
        # permisos = Permiso.objects.filter(id__in=list(set(list(permisos1) + list(permisos2) + list(permisos3))))
        # acceso = len([p for p in permisos if p.code_nombre == permiso_comprobar]) > 0
        # return acceso


@register.filter
def lista_hermanos(g_e):  # Devuelve la lista de hermanos que tiene gauser_extra (g_e)
    return Gauser_extra.objects.filter(
        Q(tutor1=g_e.tutor1) | Q(tutor2=g_e.tutor1) | Q(tutor1=g_e.tutor2) | Q(
            tutor2=g_e.tutor2), tutor1__isnull=False, tutor2__isnull=False).exclude(
        id=g_e.id).distinct()


@register.filter
def edad(g_e):  # Devuelve la edad que tiene gauser_extra (g_e)
    born = g_e.gauser.nacimiento
    today = date.today()
    try:
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except:
        return 300  # Este entero será devuelto cuando el gauser no tenga definido nacimiento


# -------------------------------------------------------------------------------------------------------------#
# TEMPLATETAGS PARA ACTIVIDADES

# @register.filter
# def participantes_actividad(actividad):  # Devuelve la lista de participantes en la actividad
#     return Participante.objects.filter(actividad=actividad).order_by('educando__subentidad__nombre')


@register.filter
def posibles_participantes_actividad(actividad):  # Devuelve la lista de posibles participantes en la actividad
    return Gauser_extra.objects.filter(entidad=actividad.organizador.entidad,
                                       subentidad__in=actividad.subentidades.all()).order_by('subentidad__nombre')


# @register.filter
# def puede_asistir(reunion, g_e):  # Devuelve True si puede asistir a la reunión (el usuario)
#     u_p = g_e.perfiles.all().values_list('id', flat=True)  #u_p -> User_Perfiles
#     if len([p for p in u_p if p in [20, 25, 30]]) > 0:
#         return (not reunion.is_finished)
#     else:
#         reu_sub = [reunion.subentidad.id, ]
#         subentidades = Gauser_extra.objects.filter(Q(tutor1=g_e) | Q(tutor2=g_e) | Q(gauser=g_e.gauser)).values_list(
#             'subentidad__id', flat=True)
#         return (len([s for s in subentidades if s in reu_sub]) > 0) and (not reunion.is_finished)


# @register.filter
# def puede_participar(actividad, g_e):  # Devuelve True si puede participar en la actividad (el usuario o sus hijos)
#     u_p = g_e.perfiles.all().values_list('id', flat=True)  #u_p -> User_Perfiles
#     if len([p for p in u_p if p in [20, 25, 30]]) > 0:
#         return (not actividad.is_finished)
#     else:
#         act_sub = actividad.subentidades.all().values_list('id', flat=True)
#         subentidades = Gauser_extra.objects.filter(Q(tutor1=g_e) | Q(tutor2=g_e) | Q(gauser=g_e.gauser)).values_list(
#             'subentidad__id', flat=True)
#         return (len([s for s in subentidades if s in act_sub]) > 0) and (not actividad.is_deadlined)


# @register.filter
# def puede_colaborar(actividad, g_e):  # Devuelve True si puede colaborar en la actividad (el usuario o sus hijos)
#     u_p = g_e.perfiles.all().values_list('id', flat=True)  #u_p -> User_Perfiles
#     if len([p for p in u_p if
#             p in [20, 25, 30]]) > 0:  #Si es el coordinador(20), secretario(30) o administrador informático(25)
#         return (not actividad.is_finished)
#     elif len([p for p in u_p if p in [75, 80, 85]]) > 0:  #Si es el voluntario(75), padre(80) o socio adulto(85)
#         return (not actividad.is_deadlined)
#     else:
#         return False


# @register.filter
# def participante_actividad(actividad, gauser_extra):  # Devuelve True si gauser_extra participa, False en caso contrario
#     return Participante.objects.filter(actividad=actividad, educando=gauser_extra).count() > 0

@register.filter
def num_usuarios_ronda(ronda):
    g_es = Gauser_extra.objects.filter(ronda=ronda)
    return g_es.count()

@register.filter
def list_usuarios_ronda(ronda):
    g_es = Gauser_extra.objects.filter(ronda=ronda)
    return g_es

@register.filter
def num_usuarios_entidad(entidad):
    g_es = Gauser_extra.objects.filter(ronda__entidad=entidad)
    return g_es.count()

@register.filter
def has_usuarios_ronda(subentidad, ronda):  # Comprueba si la subentidad tiene ususarios de esta ronda
    g_es = usuarios_ronda(ronda, subentidades=[subentidad])
    return g_es.count() > 0


@register.filter
def actividad_alumnos_incluidos_grupo(actividad,
                                      idgrupo):  # Devuelve los alumnos incluidos en una actividad pertenecientes a un grupo
    return actividad.alumnos_incluidos.filter(grupo__id=idgrupo)


@register.filter
def alumnos_in_grupo(grupo):  # Devuelve los alumnos en un grupo
    return Gauser_extra.objects.filter(grupo=grupo)


@register.filter
def solo_tramo_horario(sesiones, idtramo):  # Devuelve los alumnos incluidos en una actividad pertenecientes a un grupo
    return sesiones.filter(tramo_horario__id=idtramo)


# -------------------------------------------------------------------------------------------------------------#
# TEMPLATETAGS PARA DOCUMENTOS

@register.filter
def tabular(number):  # Devuelve tantas tabulaciones como indicada en number
    return '&nbsp;&nbsp;' * int((number - 1))


# -------------------------------------------------------------------------------------------------------------#
# TEMPLATETAGS PARA IMPRIMIR CORRECTAMENTE LA LOCALIDAD EN LUGARES DONDE HAY VARIOS CÓDIGOS POSTALES

@register.filter
def nombre_mes(entero):  # Devuelve tantas tabulaciones como indicada en number
    return MESES[entero]


# -------------------------------------------------------------------------------------------------------------#
# TEMPLATETAGS PARA IMPRIMIR CORRECTAMENTE LA LOCALIDAD EN LUGARES DONDE HAY VARIOS CÓDIGOS POSTALES

@register.filter
def only_localidad(texto):  # Devuelve tantas tabulaciones como indicada en number
    return texto.split('-')[0]


# -------------------------------------------------------------------------------------------------------------#
# TEMPLATETAGS PARA REEMPLAZAR ESPACIOS CON UN CARACTER

@register.filter
def unir(texto, caracter):  # Devuelve el texto reemplazando los espacios en blanco por "caracter"
    return texto.replace(' ', caracter)


# -------------------------------------------------------------------------------------------------------------#
# TEMPLATETAGS PARA OBTENER ÚNICAMENTE EL NOMBRE DEL FICHERO EN LOS ADJUNTOS

@register.filter
def get_adjunto_name(adjunto):  # Devuelve el texto reemplazando los espacios en blanco por "caracter"
    prop_id = adjunto.propietario.id
    return adjunto.filename().replace('%s_' % (prop_id), '', 1)


# -------------------------------------------------------------------------------------------------------------#
# TEMPLATETAGS PARA POLÍTICAS DE CUOTAS Y REMESAS

@register.filter
def primera_cuota(descuentos):
    d = re.findall(r"[-+]?\d*\.\d+|\d+", descuentos)[0]
    if d == '&#8364;':
        d = 'Sin descuentos'
    return d

@register.filter
def desglosar_descuentos(descuentos):
    d = '&#8364;, '.join(re.findall(r"[-+]?\d*\.\d+|\d+", descuentos)[1:]) + '&#8364;'
    if d == '&#8364;':
        d = 'Sin descuentos'
    return d


@register.filter
def at_02(nif):  # Diseñado a partir del documento "adeudos_sepa.pdf"
    tabla = {'A': '10', 'G': '16', 'M': '22', 'S': '28', 'Y': '34', 'B': '11', 'H': '17', 'N': '23', 'T': '29',
             'Z': '35', 'C': '12', 'I': '18', 'O': '24', 'U': '30', 'D': '13', 'J': '19', 'P': '25', 'V': '31',
             'E': '14', 'K': '20', 'Q': '26', 'W': '32', 'F': '15', 'L': '21', 'R': '27', 'X': '33', '0': '0', '1': '1',
             '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9'}
    a = 'ES'  # Primera parte de la identificación devuelta y correspondiente a España
    d = nif
    cad = re.sub('[^0-9a-zA-Z]+', '', d) + a + '00'
    for k, v in tabla.items():
        cad = cad.replace(k, v)
    cad = str(98 - int(cad) % 97)
    b = cad if len(cad) == 2 else '0' + cad
    c = '001'
    return a + b + c + d


@register.filter
def float2string(n):
    i = int(n)
    d = str((n - i) * 100).split('.')[0]
    d = d if len(d) > 1 else d + '0'
    return str(i) + '.' + d


# -------------------------------------------------------------------------------------------------------------#
# TEMPLATETAGS PARA CORREOS

@register.filter
def dominio_correo(g_e):  # si email = fede@gmail.com devuelve GMAIL, con email = fede@cossio.net devuelve COSSIO
    try:
        return g_e.gauser.email.split('@')[1].split('.')[0].upper()
    except:
        return g_e.email.split('@')[1].split('.')[0].upper()


# -------------------------------------------------------------------------------------------------------------#
# TEMPLATETAGS PARA MENSAJES

@register.filter
def remove_newlines(texto):
    normalized_text = normalize_newlines(texto)
    normalized_text = normalized_text.replace("'", "\'")
    normalized_text = normalized_text.replace('"', '\"')
    # Then simply remove the newlines like so.
    return mark_safe(normalized_text.replace('\n', ' '))
