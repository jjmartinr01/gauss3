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
from vut.models import Vivienda

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

register = Library()


MESES = (
    '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre',
    'diciembre',)

@register.filter
def nombre_mes(entero):  # Devuelve tantas tabulaciones como indicada en number
    return MESES[entero]

# Módulo de Contabilidad

@register.filter
def desglosar_descuentos(descuentos):
    d = '&#8364;, '.join(re.findall(r"[-+]?\d*\.\d+|\d+", descuentos)[1:]) + '&#8364;'
    if d == '&#8364;':
        d = 'Sin descuentos'
    return d

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
    usuarios = usuarios_ronda(politica.entidad.ronda, cargos=[politica.cargo]).exclude(gauser__id__in=exentos_id)
    usuarios_id = []
    n = 0
    for usuario in usuarios:
        if usuario.id not in usuarios_id:
            n += 1
            if politica.tipo == 'hermanos':
                familiares = usuario.unidad_familiar
                deudores = familiares.filter(id__in=usuarios)
                if deudores.count() > 1:
                    deudor = 'Familia %s' % deudores[0].gauser.last_name
                else:
                    deudor = deudores[0].gauser.get_full_name()
                usuarios_id += list(deudores.values_list('id', flat=True))
                n_cs = familiares.values_list('num_cuenta_bancaria', flat=True)
                deudores_str = ', '.join(deudores.values_list('gauser__first_name', flat=True))
            elif politica.tipo == 'fija':
                deudores = [usuario]
                deudor = usuario.gauser.get_full_name()
                usuarios_id += [usuario.id]
                n_cs = [usuario.num_cuenta_bancaria]
                # deudores_str = ', '.join(deudores.values_list('gauser__first_name', flat=True))
            elif politica.tipo == 'vut':
                viviendas = Vivienda.objects.filter(propietarios__in=[usuario.gauser],
                                                    entidad=usuario.ronda.entidad)
                deudores = [usuario] * viviendas.count()
                usuarios_id += [usuario.id]
                n_cs = [usuario.num_cuenta_bancaria]
                deudores_str = '%s viviendas gestionadas por %s' % (viviendas.count(),
                                                                    usuario.gauser.get_full_name())
                deudor = usuario.gauser.get_full_name()
            else:
                deudores = []
                usuarios_id += [usuario.id]
                n_cs = []
                deudores_str = ''
                concepto = ''
                deudor = ''

            try:
                cuenta_banca = [n_c.replace(' ', '') for n_c in n_cs if len(str(n_c)) > 18][0]
                estilo, title = "", "Cuenta bancaria: " + str(cuenta_banca)
            except:
                estilo, title = "color:red", "No hay cuenta bancaria asignada"
            if len(deudores) > 0:
                no_ex.append({'title': title, 'estilo': estilo, 'concepto': politica.concepto,
                              'deudor': deudor, 'cantidad': str(sum(importes[:len(deudores)]))})
                # no_ex.append('<span title="%s" style="%s">%s %s (%s)dddd</span>' % (
                #     title, estilo, concepto, deudores[0].gauser.last_name, str(sum(importes[:len(deudores)]))))
            if n == total:
                break
    return no_ex