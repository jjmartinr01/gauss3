# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.utils import timezone
from django.core.files.base import ContentFile
from time import sleep
from bs4 import BeautifulSoup
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db.models import Q
import kronos
import requests
from gauss.rutas import RUTA_BASE, MEDIA_VUT
from autenticar.models import Gauser, Permiso
from entidades.models import Gauser_extra
from mensajes.views import encolar_mensaje
from vut.models import RegistroPolicia, Viajero, Autorizado
from gtelegram.views import envia_telegram
from vut.seleniumPN import RegistraViajeroPN

logger = logging.getLogger('django')


# @kronos.register('*/2 * * * *')
def comunica_viajero2PNGC():
    registros = RegistroPolicia.objects.filter(enviado=False)[:5]
    for registro in registros:
        sleep(1)
        registro.enviado = True  # Esto evitará que se ejecute de nuevo el reenvío del registro
        registro.save()
        viajero = registro.viajero
        vivienda = registro.viajero.reserva.vivienda
        logger.info("1")
        if type(viajero) is not Viajero:
            return False
        if viajero.fichero_policia:
            return (False, 'ya enviado')
        if not viajero.observaciones:
            viajero.observaciones = ''
            viajero.save()
        try:
            if vivienda.police == 'GC':
                fichero = open(RUTA_BASE + registro.parte.url)
                logger.info("4")
                url = 'https://%s:%s@hospederias.guardiacivil.es/hospederias/servlet/ControlRecepcionFichero' % (
                    vivienda.police_code, vivienda.police_pass)
                try:
                    r = requests.post(url, files={'fichero': fichero}, data={}, verify=False, timeout=5)
                except:
                    return False
                if r.status_code == 200:
                    if 'Errores' in r.text:
                        gauser_autorizados = Autorizado.objects.filter(vivienda=vivienda).values_list('gauser__id',
                                                                                                      flat=True)
                        receptores = Gauser.objects.filter(
                            Q(id__in=gauser_autorizados) | Q(id__in=vivienda.propietarios.all()))
                        mensaje = '<p>En el registro de %s, reserva %s</p><p>La Guardia Civil dice:</p>%s' % (
                            viajero.nombre_completo, viajero.reserva, r.text.replace('\r\n', '<br>'))
                        viajero.observaciones += mensaje
                        emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
                        encolar_mensaje(emisor=emisor, receptores=receptores,
                                        asunto='Error en comunicación a la Guardia Civil', html=mensaje,
                                        etiqueta='guardia_civl%s' % vivienda.id)
                        gtexto = 'Error con registro en Guardia Civil del viajero: %s %s (%s)' % (
                            viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                        envia_telegram(emisor, gtexto)
                    else:
                        viajero.fichero_policia = True
                        mensaje = '<p>En el registro de %s, reserva %s</p><p>La Guardia Civil dice:</p>%s' % (
                            viajero.nombre_completo, viajero.reserva, r.text.replace('\r\n', '<br>'))
                        viajero.observaciones += mensaje
                        emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
                        encolar_mensaje(emisor=emisor, receptores=[vivienda.propietarios.all()],
                                        asunto='Comunicación a la Guardia Civil', html=mensaje,
                                        etiqueta='guardia_civl%s' % vivienda.id)
                        gtexto = 'Registrado en Guardia Civil el viajero: %s %s (%s)' % (
                            viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                        envia_telegram(emisor, gtexto)
                    viajero.save()
                    fichero.close()
                    return True
                else:
                    gauser_autorizados = Autorizado.objects.filter(vivienda=vivienda).values_list('gauser__id',
                                                                                                  flat=True)
                    receptores = Gauser.objects.filter(id__in=gauser_autorizados)
                    mensaje = '<p>No se ha podido establecer comunicación con la Guardia Civil.</p>'
                    viajero.observaciones += mensaje
                    emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
                    encolar_mensaje(emisor=emisor, receptores=receptores,
                                    asunto='Error en comunicación a la Guardia Civil', html=mensaje,
                                    etiqueta='guardia_civl%s' % vivienda.id)
                    gtexto = 'Error con registro en Guardia Civil del viajero: %s %s (%s)' % (
                        viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                    envia_telegram(emisor, gtexto)
                    viajero.save()
                    fichero.close()
                    return False
            elif vivienda.police == 'PN':
                logger.info("entra al registro PN. Viajero: %s" % viajero)
                RegistraViajeroPN(viajero)
                return True
                # Iniciamos una sesión
                s = requests.Session()
                s.verify = False  # Para que los certificados ssl no sean verificados. Comunicación https confiada
                # Accedemos a la página de inicio y de la respuesta capturamos el token csrf
                try:
                    p1 = s.get('https://webpol.policia.es/e-hotel/', timeout=5)
                except:
                    return False
                # Escribimos las cookies en una cadena de texto, para introducirlas en las distintas cabeceras
                cookies_header = ''
                for c in dict(s.cookies):
                    cookies_header += '%s=%s;' % (c, dict(s.cookies)[c])
                # Debemos salvar el token csrf de la sesión, que utilizaremos en los diferentes enlaces
                soup1 = BeautifulSoup(p1.content.decode(p1.encoding), 'html.parser')
                csrf_token = soup1.find('input', {'name': '_csrf'})['value']
                # El siguiente paso que da el sistema es la obtención de etiquetas de su sistema "ARGOS"
                obtener_etiquetas_url = 'https://webpol.policia.es/e-hotel/obtenerEtiquetas'
                obtener_etiquetas_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                                             'Accept-Encoding': 'gzip, deflate, br',
                                             'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                             'Ajax-Referer': '/e-hotel/obtenerEtiquetas', 'Connection': 'keep-alive',
                                             'Content-Length': '0',
                                             'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                             'Cookie': cookies_header,
                                             'Host': 'webpol.policia.es',
                                             'Referer': 'https://webpol.policia.es/e-hotel/',
                                             'User-Agent': 'python-requests/2.21.0',
                                             'X-CSRF-TOKEN': csrf_token,
                                             'X-Requested-With': 'XMLHttpRequest'}
                try:
                    p11 = s.post(obtener_etiquetas_url, headers=obtener_etiquetas_headers, timeout=5)
                except:
                    return False
                # Cargamos los valores de los inputs demandados para hacer el login y enviamos el post con el payload
                # En este caso enviamos: headers, cookies y parámetros (payload)
                payload = {'username': vivienda.police_code, '_csrf': csrf_token, 'password': vivienda.police_pass}
                execute_login_headers = {'Accept': 'text/html,  application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8',
                                         'Accept-Encoding': 'gzip, deflate, br',
                                         'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                         'Connection': 'keep-alive',
                                         'Content-Type': 'application/x-www-form-urlencoded',
                                         'Cookie': cookies_header,
                                         'Host': 'webpol.policia.es', 'Referer': 'https://webpol.policia.es/e-hotel/',
                                         'Upgrade-Insecure-Requests': '1', 'User-Agent': 'python-requests/2.21.0'}
                try:
                    p2 = s.post('https://webpol.policia.es/e-hotel/execute_login', data=payload,
                                headers=execute_login_headers, timeout=5)
                except:
                    return False
                # A continuación hacemos una petición GET a inicio sin ningún parámetro
                execute_inicio_headers = {
                    'Accept': 'text/html,  application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                    'Connection': 'keep-alive', 'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                    'Referer': 'https://webpol.policia.es/e-hotel/', 'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'python-requests/2.21.0'}
                try:
                    p21 = s.get('https://webpol.policia.es/e-hotel/inicio', headers=execute_inicio_headers,
                                cookies=dict(s.cookies), timeout=5)
                except:
                    return False
                # Hacemos una comprabción para asegurarnos de que se ha accedido correctamente a la webpol.
                # Si la respuesta es correcta la respuesta contendrá el usuario:
                if vivienda.police_code in p21.content.decode(p2.encoding):
                    # El siguiente paso es obtener etiquetas. Esta es una solicitud POST sin payload
                    # obtener_etiquetas_url = 'https://webpol.policia.es/e-hotel/obtenerEtiquetas'
                    # obtener_etiquetas_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                    #                              'Accept-Encoding': 'gzip, deflate, br',
                    #                              'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                    #                              'Ajax-Referer': '/e-hotel/obtenerEtiquetas',
                    #                              'Connection': 'keep-alive',
                    #                              'Content-Length': '0',
                    #                              'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    #                              'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                    #                              'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                    #                              'User-Agent': 'python-requests/2.21.0',
                    #                              'X-CSRF-TOKEN': '92a4cc08-b50b-4be3-8a98-8adf8bb1db2e',
                    #                              'X-Requested-With': 'XMLHttpRequest'}
                    # try:
                    #     p22 = s.post(obtener_etiquetas_url, headers=obtener_etiquetas_headers, cookies=dict(s.cookies),
                    #                  timeout=5)
                    # except:
                    #     return False
                    # A continuación debemos ir a la grabación manual. Antes se hace una llamada para limpiar la sesión
                    limpiar_sesion_temporal_url = 'https://webpol.policia.es/e-hotel/limpiarSesionTemporal'
                    limpiar_sesion_temporal_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                                                       'Accept-Encoding': 'gzip, deflate, br',
                                                       'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                                       'Ajax-Referer': '/e-hotel/limpiarSesionTemporal',
                                                       'Connection': 'keep-alive', 'Content-Length': '0',
                                                       'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                                       'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                                       'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                                       'User-Agent': 'python-requests/2.21.0',
                                                       'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                    try:
                        p23 = s.post(limpiar_sesion_temporal_url, headers=limpiar_sesion_temporal_headers, timeout=5)
                    except:
                        return False
                    # Ahora es cuando se hace otra petición POST para llegar a la grabación manual sin payload
                    logger.info("5")
                    grabador_manual_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/vista/grabadorManual'
                    grabador_manual_headers = {'Accept': 'text/html, */*; q=0.01',
                                               'Accept-Encoding': 'gzip, deflate, br',
                                               'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                               'Ajax-Referer': '/e-hotel/hospederia/manual/vista/grabadorManual',
                                               'Connection': 'keep-alive',
                                               'Content-Length': '0',
                                               'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                               'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                               'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                               'User-Agent': 'python-requests/2.21.0',
                                               'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                    try:
                        p3 = s.post(grabador_manual_url, headers=grabador_manual_headers, timeout=5)
                        logger.info("Entrada en grabador manual")
                        sleep(10)
                    except:
                        logger.info("Error al entrar en grabador manual")
                        return False
                    # En esta petición nos han devuelto el id de la hospedería. Lo tenemos que guardar:
                    soup3 = BeautifulSoup(p3.content.decode(p3.encoding), 'html.parser')
                    idHospederia = soup3.find('input', {'id': 'idHospederia'})['value']
                    logger.info('idHospederia %s' % idHospederia)
                    # Pasamos a rellenar el parte del viajero. Necesitamos algunos campos como sexoStr o tipoDocumentoStr.
                    # En el caso de sexoStr debemos asignar el texto MASCULINO o FEMENINO, que es diferente de
                    # get_sexo_display() y por eso definimos el siguiente diccionario.
                    sexo = {'M': 'MASCULINO', 'F': 'FEMENINO'}
                    data_viajero = {'nombre': viajero.nombre, 'apellido1': viajero.apellido1,
                                    'apellido2': viajero.apellido2, 'nacionalidad': viajero.pais,
                                    'tipoDocumento': viajero.tipo_ndi, 'numIdentificacion': viajero.ndi,
                                    'fechaExpedicionDoc': viajero.fecha_exp.strftime('%d/%m/%Y'),
                                    'dia': '%s' % viajero.nacimiento.day, 'mes': '%s' % viajero.nacimiento.month,
                                    'ano': '%s' % viajero.nacimiento.year, 'idHospederia': idHospederia,
                                    'fechaEntrada': viajero.fecha_entrada.strftime('%d/%m/%Y'), 'sexo': viajero.sexo,
                                    'fechaNacimiento': viajero.nacimiento.strftime('%d/%m/%Y'), '_csrf': csrf_token,
                                    'jsonHiddenComunes': '',
                                    'nacionalidadStr': viajero.get_pais_display().encode('utf-8'),
                                    # 'nacionalidadStr': viajero.get_pais_display().encode('iso-8859-1'),
                                    'sexoStr': sexo[viajero.sexo], 'tipoDocumentoStr': viajero.get_tipo_ndi_display()}
                    logger.info("Definido data_viajero")
                    huesped_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/insertar/huesped'
                    huesped_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                       'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                       'Ajax-Referer': '/e-hotel/hospederia/manual/insertar/huesped',
                                       'Connection': 'keep-alive',
                                       'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                       'Cookie': cookies_header,
                                       'Host': 'webpol.policia.es',
                                       'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                       'User-Agent': 'python-requests/2.21.0',
                                       'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                    logger.info("Definido huesped_headers")
                    try:
                        p4 = s.post(huesped_url, data=data_viajero, headers=huesped_headers, timeout=5)
                        logger.info("Enviados datos del huesped")
                        sleep(4)
                    except:
                        logger.info("Error al enviar datos del huesped")
                        return False
                    # En esta petición nos devuelven datos que no vamos a necesitar, pero que almacenamos para guarar en
                    # la información del registro.
                    soup4 = BeautifulSoup(p4.content.decode(p4.encoding), 'html.parser')
                    logger.info("Se ha recibido respuesta de la policia")
                    mensaje = soup4.find('em')
                    logger.info("Parseado mensaje de correcto o incorrecto")
                    huespedJson = soup4.find('input', {'name': 'huespedJson'})['value']
                    logger.info("Parseado huespedJson")
                    idHuesped = soup4.find('input', {'name': 'idHuesped'})['value']
                    logger.info("Parseado idHuesped")
                    viajero.observaciones += "Mensaje de la Policía: %s<br>idHuesped: %s<br>idHospederia: %s" % (
                        mensaje, idHuesped, idHospederia)
                    logger.info("Se han grabado las observaciones")
                    # Para completar la grabación es necesario llamar a parteViajero a través de una petición GET:
                    parte_viajero_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/vista/parteViajero'
                    parte_viajero_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                             'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                             'Ajax-Referer': '/e-hotel/hospederia/manual/insertar/huesped',
                                             'Connection': 'keep-alive',
                                             'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                             'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                             'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                             'User-Agent': 'python-requests/2.21.0',
                                             'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                    try:
                        p5 = s.get(parte_viajero_url, headers=parte_viajero_headers, cookies=dict(s.cookies), timeout=5)
                        logger.info("Enviado GET a parteViajero")
                        sleep(4)
                    except:
                        logger.info("Error al procesar parteViajero")
                    # En siguiente paso dado a través de un navegador es llamar a tipoDocumentoNacionalidad con una
                    # petición POST enviando como parámetro la "nacionalidad":
                    nacionalidad_url = 'https://webpol.policia.es/e-hotel/combo/tipoDocumentoNacionalidad'
                    nacionalidad_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                            'Ajax-Referer': '/e-hotel/combo/tipoDocumentoNacionalidad',
                                            'Connection': 'keep-alive',
                                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                            'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                            'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                            'User-Agent': 'python-requests/2.21.0',
                                            'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                    payload = {'nacionalidad': viajero.pais}
                    try:
                        p6 = s.post(nacionalidad_url, headers=nacionalidad_headers, cookies=dict(s.cookies),
                                    data=payload,
                                    timeout=5)
                        logger.info("Enviado POST a tipoDocumentoNacionalidad")
                    except:
                        logger.info("Error al enviar POST a tipoDocumentoNacionalidad")

                    generar_parte_url = 'https://webpol.policia.es/e-hotel/hospederia/generarParteHuesped'
                    generar_parte_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                             'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                             'Ajax-Referer': '/e-hotel/hospederia/generarParteHuesped',
                                             'Connection': 'keep-alive',
                                             'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                             'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                             'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                             'User-Agent': 'python-requests/2.21.0',
                                             'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                    payload = {'huespedJson': huespedJson, 'idHuesped': idHuesped}

                    try:
                        p7 = s.post(generar_parte_url, headers=generar_parte_headers, data=payload, timeout=5)
                        logger.info("Solicitud generar PDF")
                    except:
                        logger.info("Error al solicitar generar PDF")

                    previsualiza_url = 'https://webpol.policia.es/e-hotel/previsualizacionPdf/'
                    previsualiza_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                            'Ajax-Referer': '/e-hotel/hospederia/generarParteHuesped',
                                            'Connection': 'keep-alive',
                                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                            'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                            'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                            'User-Agent': 'python-requests/2.21.0',
                                            'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                    try:
                        p8 = s.get(previsualiza_url, headers=previsualiza_headers, timeout=5)
                        logger.info("Solicitud previsualizar PDF")
                    except:
                        logger.info("Error al solicitar previsualizar PDF")

                    genera_url = 'https://webpol.policia.es/e-hotel/hospederia/generarPDFparteHuesped'
                    genera_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
                                      'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                                      'Connection': 'keep-alive',
                                      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                      'Cookie': cookies_header, 'Host': 'webpol.policia.es',
                                      'Referer': 'https://webpol.policia.es/e-hotel/inicio',
                                      'User-Agent': 'python-requests/2.21.0',
                                      'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
                    try:
                        p9 = s.get(genera_url, headers=genera_headers, timeout=5)
                        fPN = ContentFile(p9.content)
                        fPN.name = '%s.pdf' % viajero.id
                        registro.pdf_PN = fPN
                        registro.save()
                        logger.info("Solicitud generar parte PDF ejecutada")
                    except:
                        logger.info("Error al solicitar generar parte PDF")
                    # En este punto termina el proceso de grabación
                    if p4.status_code == 200:
                        logger.info(u'Todo correcto')
                        s.close()
                        viajero.fichero_policia = True
                        viajero.observaciones += '<br><span style="color:green;">Registro finalizado con todas las comunicaciones correctas.</span>'
                        viajero.observaciones += '<hr>Información JSON: <br> %s' % huespedJson
                        viajero.save()
                        emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
                        gtexto = 'Se ha registrado en Policía el viajero: %s %s (%s)' % (
                        viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                        envia_telegram(emisor, gtexto)
                        return True
                    else:
                        logger.info('Error durante el grabado del viajero. Hacer el registro manualmente.')
                        viajero.observaciones += '<br><span style="color:red;">Error durante el grabado del viajero. Hacer el registro manualmente.</span>'
                        viajero.save()
                        s.close()
                        emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
                        gtexto = 'Error durante el grabado del viajero. Hacer el registro manualmente. Viajero: %s %s (%s)' % (
                            viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                        envia_telegram(emisor, gtexto)
                        return p4
                else:
                    logger.info(u'Error al hacer el login en webpol para el viajero: %s' % (viajero))
                    viajero.observaciones += 'Error al hacer el login en webpol para el viajero'
                    viajero.save()
                    s.close()
                    emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
                    gtexto = 'Error al hacer el login en la web de la Policía Nacional. Viajero: %s %s (%s)' % (
                        viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                    envia_telegram(emisor, gtexto)
            else:
                return False
        except:
            logger.info("6")
            mensaje = 'Error en la comunicación con Policía/Guardia Civil. Se debe hacer el registro manualmente.'
            ronda = viajero.reserva.vivienda.entidad.ronda
            permiso = Permiso.objects.get(code_nombre='recibe_errores_de_viajeros')
            receptores_ge = Gauser_extra.objects.filter(ronda=ronda, permisos__in=[permiso])
            receptores = Gauser.objects.filter(id__in=receptores_ge.values_list('gauser__id', flat=True))
            emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
            encolar_mensaje(emisor=emisor, receptores=receptores,
                            asunto='Error en RegistroPolicia', html=mensaje, etiqueta='error%s' % ronda.id)
            gtexto = 'Error en la comunicación con Policía/Guardia Civil. Se debe hacer el registro manualmente. Viajero: %s %s (%s)' % (
                viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
            envia_telegram(emisor, gtexto)
            return False


# def comunica_viajero2PNGC2(registro):
#     registros = [registro]
#     for registro in registros:
#         registro.enviado = True  # Esto evitará que se ejecute de nuevo el reenvío del registro
#         registro.save()
#         viajero = registro.viajero
#         vivienda = registro.viajero.reserva.vivienda
#         logger.info("1")
#         if type(viajero) is not Viajero:
#             return False
#         if not viajero.observaciones:
#             viajero.observaciones = ''
#             viajero.save()
#         try:
#             if vivienda.police == 'GC':
#                 fichero = open(RUTA_BASE + registro.parte.url)
#                 logger.info("4")
#                 url = 'https://%s:%s@hospederias.guardiacivil.es/hospederias/servlet/ControlRecepcionFichero' % (
#                     vivienda.police_code, vivienda.police_pass)
#                 try:
#                     r = requests.post(url, files={'fichero': fichero}, data={}, verify=False, timeout=5)
#                 except:
#                     return False
#                 if r.status_code == 200:
#                     if 'Errores' in r.text:
#                         gauser_autorizados = Autorizado.objects.filter(vivienda=vivienda).values_list('gauser__id',
#                                                                                                       flat=True)
#                         receptores = Gauser.objects.filter(
#                             Q(id__in=gauser_autorizados) | Q(id=vivienda.gpropietario.id))
#                         mensaje = '<p>En el registro de %s, reserva %s</p><p>La Guardia Civil dice:</p>%s' % (
#                             viajero.nombre_completo, viajero.reserva, r.text.replace('\r\n', '<br>'))
#                         viajero.observaciones += mensaje
#                         emisor = Gauser_extra.objects.get(gauser=vivienda.gpropietario, ronda=vivienda.entidad.ronda)
#                         encolar_mensaje(emisor=emisor, receptores=receptores,
#                                         asunto='Error en comunicación a la Guardia Civil', html=mensaje,
#                                         etiqueta='guardia_civl%s' % vivienda.id)
#                     else:
#                         viajero.fichero_policia = True
#                         mensaje = '<p>En el registro de %s, reserva %s</p><p>La Guardia Civil dice:</p>%s' % (
#                             viajero.nombre_completo, viajero.reserva, r.text.replace('\r\n', '<br>'))
#                         viajero.observaciones += mensaje
#                         emisor = Gauser_extra.objects.get(gauser=vivienda.gpropietario, ronda=vivienda.entidad.ronda)
#                         encolar_mensaje(emisor=emisor, receptores=[vivienda.gpropietario],
#                                         asunto='Comunicación a la Guardia Civil', html=mensaje,
#                                         etiqueta='guardia_civl%s' % vivienda.id)
#                     viajero.save()
#                     fichero.close()
#                     return True
#                 else:
#                     gauser_autorizados = Autorizado.objects.filter(vivienda=vivienda).values_list('gauser__id',
#                                                                                                   flat=True)
#                     receptores = Gauser.objects.filter(id__in=gauser_autorizados)
#                     mensaje = '<p>No se ha podido establecer comunicación con la Guardia Civil.</p>'
#                     viajero.observaciones += mensaje
#                     emisor = Gauser_extra.objects.get(gauser=vivienda.gpropietario, ronda=vivienda.entidad.ronda)
#                     encolar_mensaje(emisor=emisor, receptores=receptores,
#                                     asunto='Error en comunicación a la Guardia Civil', html=mensaje,
#                                     etiqueta='guardia_civl%s' % vivienda.id)
#                     viajero.save()
#                     fichero.close()
#                     return False
#             elif vivienda.police == 'PN':
#                 logger.info("entra al registro PN. Viajero: %s" % viajero)
#                 # Iniciamos una sesión
#                 s = requests.Session()
#                 s.verify = False  # Para que los certificados ssl no sean verificados. Comunicación https confiada
#                 # Accedemos a la página de inicio y de la respuesta capturamos el token csrf
#                 try:
#                     p1 = s.get('https://webpol.policia.es/e-hotel/', timeout=5)
#                 except:
#                     return False
#                 # Escribimos las cookies en una cadena de texto, para introducirlas en las distintas cabeceras
#                 cookies_header = ''
#                 for c in dict(s.cookies):
#                     cookies_header += '%s=%s;' % (c, dict(s.cookies)[c])
#                 # Debemos salvar el token csrf de la sesión, que utilizaremos en los diferentes enlaces
#                 soup1 = BeautifulSoup(p1.content.decode(p1.encoding), 'html.parser')
#                 csrf_token = soup1.find('input', {'name': '_csrf'})['value']
#                 # El siguiente paso que da el sistema es la obtención de etiquetas de su sistema "ARGOS"
#                 obtener_etiquetas_url = 'https://webpol.policia.es/e-hotel/obtenerEtiquetas'
#                 obtener_etiquetas_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
#                                              'Accept-Encoding': 'gzip, deflate, br',
#                                              'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                              'Ajax-Referer': '/e-hotel/obtenerEtiquetas', 'Connection': 'keep-alive',
#                                              'Content-Length': '0',
#                                              'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                              'Cookie': cookies_header,
#                                              'Host': 'webpol.policia.es',
#                                              'Referer': 'https://webpol.policia.es/e-hotel/',
#                                              'User-Agent': 'python-requests/2.21.0',
#                                              'X-CSRF-TOKEN': csrf_token,
#                                              'X-Requested-With': 'XMLHttpRequest'}
#                 try:
#                     p11 = s.post(obtener_etiquetas_url, headers=obtener_etiquetas_headers, cookies=dict(s.cookies),
#                                  timeout=5)
#                 except:
#                     return False
#                 # Cargamos los valores de los inputs demandados para hacer el login y enviamos el post con el payload
#                 # En este caso enviamos: headers, cookies y parámetros (payload)
#                 payload = {'username': vivienda.police_code, '_csrf': csrf_token, 'password': vivienda.police_pass}
#                 execute_login_headers = {'Accept': 'text/html,  application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8',
#                                          'Accept-Encoding': 'gzip, deflate, br',
#                                          'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                          'Connection': 'keep-alive',
#                                          'Content-Type': 'application/x-www-form-urlencoded',
#                                          'Cookie': cookies_header,
#                                          'Host': 'webpol.policia.es', 'Referer': 'https://webpol.policia.es/e-hotel/',
#                                          'Upgrade-Insecure-Requests': '1', 'User-Agent': 'python-requests/2.21.0'}
#                 try:
#                     p2 = s.post('https://webpol.policia.es/e-hotel/execute_login', data=payload,
#                                 headers=execute_login_headers, cookies=dict(s.cookies), timeout=5)
#                 except:
#                     return False
#                 # A continuación hacemos una petición GET a inicio sin ningún parámetro
#                 execute_inicio_headers = {
#                     'Accept': 'text/html,  application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8',
#                     'Accept-Encoding': 'gzip, deflate, br',
#                     'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                     'Connection': 'keep-alive', 'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                     'Referer': 'https://webpol.policia.es/e-hotel/', 'Upgrade-Insecure-Requests': '1',
#                     'User-Agent': 'python-requests/2.21.0'}
#                 try:
#                     p21 = s.get('https://webpol.policia.es/e-hotel/inicio', headers=execute_inicio_headers,
#                                 cookies=dict(s.cookies), timeout=5)
#                 except:
#                     return False
#                 # Hacemos una comprabción para asegurarnos de que se ha accedido correctamente a la webpol.
#                 # Si la respuesta es correcta la respuesta contendrá el usuario:
#                 if vivienda.police_code in p21.content.decode(p2.encoding):
#                     # El siguiente paso es obtener etiquetas. Esta es una solicitud POST sin payload
#                     obtener_etiquetas_url = 'https://webpol.policia.es/e-hotel/obtenerEtiquetas'
#                     obtener_etiquetas_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
#                                                  'Accept-Encoding': 'gzip, deflate, br',
#                                                  'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                                  'Ajax-Referer': '/e-hotel/obtenerEtiquetas',
#                                                  'Connection': 'keep-alive',
#                                                  'Content-Length': '0',
#                                                  'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                                  'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                                                  'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                                  'User-Agent': 'python-requests/2.21.0',
#                                                  'X-CSRF-TOKEN': '92a4cc08-b50b-4be3-8a98-8adf8bb1db2e',
#                                                  'X-Requested-With': 'XMLHttpRequest'}
#                     try:
#                         p22 = s.post(obtener_etiquetas_url, headers=obtener_etiquetas_headers, cookies=dict(s.cookies),
#                                      timeout=5)
#                     except:
#                         return False
#                     # A continuación debemos ir a la grabación manual. Antes se hace una llamada para limpiar la sesión
#                     limpiar_sesion_temporal_url = 'https://webpol.policia.es/e-hotel/limpiarSesionTemporal'
#                     limpiar_sesion_temporal_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
#                                                        'Accept-Encoding': 'gzip, deflate, br',
#                                                        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                                        'Ajax-Referer': '/e-hotel/limpiarSesionTemporal',
#                                                        'Connection': 'keep-alive', 'Content-Length': '0',
#                                                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                                        'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                                                        'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                                        'User-Agent': 'python-requests/2.21.0',
#                                                        'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
#                     try:
#                         p23 = s.post(limpiar_sesion_temporal_url, headers=limpiar_sesion_temporal_headers,
#                                      cookies=dict(s.cookies), timeout=5)
#                     except:
#                         return False
#                     # Ahora es cuando se hace otra petición POST para llegar a la grabación manual sin payload
#                     logger.info("5")
#                     grabador_manual_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/vista/grabadorManual'
#                     grabador_manual_headers = {'Accept': 'text/html, */*; q=0.01',
#                                                'Accept-Encoding': 'gzip, deflate, br',
#                                                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                                'Ajax-Referer': '/e-hotel/hospederia/manual/vista/grabadorManual',
#                                                'Connection': 'keep-alive',
#                                                'Content-Length': '0',
#                                                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                                'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                                                'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                                'User-Agent': 'python-requests/2.21.0',
#                                                'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
#                     try:
#                         p3 = s.post(grabador_manual_url, headers=grabador_manual_headers, cookies=dict(s.cookies),
#                                     timeout=5)
#                         logger.info("Entrada en grabador manual")
#                         sleep(10)
#                     except:
#                         logger.info("Error al entrar en grabador manual")
#                         return False
#                     # En esta petición nos han devuelto el id de la hospedería. Lo tenemos que guardar:
#                     soup3 = BeautifulSoup(p3.content.decode(p3.encoding), 'html.parser')
#                     idHospederia = soup3.find('input', {'id': 'idHospederia'})['value']
#                     logger.info('idHospederia %s' % idHospederia)
#                     # Pasamos a rellenar el parte del viajero. Necesitamos algunos campos como sexoStr o tipoDocumentoStr.
#                     # En el caso de sexoStr debemos asignar el texto MASCULINO o FEMENINO, que es diferente de
#                     # get_sexo_display() y por eso definimos el siguiente diccionario.
#                     sexo = {'M': 'MASCULINO', 'F': 'FEMENINO'}
#                     data_viajero = {'nombre': viajero.nombre, 'apellido1': viajero.apellido1,
#                                     'apellido2': viajero.apellido2, 'nacionalidad': viajero.pais,
#                                     'tipoDocumento': viajero.tipo_ndi, 'numIdentificacion': viajero.ndi,
#                                     'fechaExpedicionDoc': viajero.fecha_exp.strftime('%d/%m/%Y'),
#                                     'dia': '%s' % viajero.nacimiento.day, 'mes': '%s' % viajero.nacimiento.month,
#                                     'ano': '%s' % viajero.nacimiento.year, 'idHospederia': idHospederia,
#                                     'fechaEntrada': viajero.fecha_entrada.strftime('%d/%m/%Y'), 'sexo': viajero.sexo,
#                                     'fechaNacimiento': viajero.nacimiento.strftime('%d/%m/%Y'), '_csrf': csrf_token,
#                                     'jsonHiddenComunes': '',
#                                     'nacionalidadStr': viajero.get_pais_display().encode('utf-8'),
#                                     'sexoStr': sexo[viajero.sexo], 'tipoDocumentoStr': viajero.get_tipo_ndi_display()}
#                     logger.info("Definido data_viajero")
#                     huesped_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/insertar/huesped'
#                     huesped_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
#                                        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                        'Ajax-Referer': '/e-hotel/hospederia/manual/insertar/huesped',
#                                        'Connection': 'keep-alive',
#                                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                        'Cookie': cookies_header,
#                                        'Host': 'webpol.policia.es',
#                                        'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                        'User-Agent': 'python-requests/2.21.0',
#                                        'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
#                     logger.info("Definido huesped_headers")
#                     try:
#                         p4 = s.post(huesped_url, data=data_viajero, headers=huesped_headers, cookies=dict(s.cookies),
#                                     timeout=5)
#                         logger.info("Enviados datos del huesped")
#                         sleep(4)
#                     except:
#                         logger.info("Error al enviar datos del huesped")
#                         return False
#                     # En esta petición nos devuelven datos que no vamos a necesitar, pero que almacenamos para guarar en
#                     # la información del registro.
#                     soup4 = BeautifulSoup(p4.content.decode(p4.encoding), 'html.parser')
#                     logger.info("Se ha recibido respuesta de la policia")
#                     mensaje = soup4.find('em')
#                     logger.info("Parseado mensaje de correcto o incorrecto")
#                     huespedJson = soup4.find('input', {'name': 'huespedJson'})['value']
#                     logger.info("Parseado huespedJson")
#                     idHuesped = soup4.find('input', {'name': 'idHuesped'})['value']
#                     logger.info("Parseado idHuesped")
#                     viajero.observaciones += "Mensaje de la Policía: %s<br>idHuesped: %s<br>idHospederia: %s" % (
#                         mensaje, idHuesped, idHospederia)
#                     logger.info("Se han grabado las observaciones")
#                     # Para completar la grabación es necesario llamar a parteViajero a través de una petición GET:
#                     parte_viajero_url = 'https://webpol.policia.es/e-hotel/hospederia/manual/vista/parteViajero'
#                     parte_viajero_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
#                                              'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                              'Ajax-Referer': '/e-hotel/hospederia/manual/insertar/huesped',
#                                              'Connection': 'keep-alive',
#                                              'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                              'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                                              'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                              'User-Agent': 'python-requests/2.21.0',
#                                              'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
#                     try:
#                         p5 = s.get(parte_viajero_url, headers=parte_viajero_headers, cookies=dict(s.cookies), timeout=5)
#                         logger.info("Enviado GET a parteViajero")
#                         sleep(4)
#                     except:
#                         logger.info("Error al procesar parteViajero")
#                         return False
#                     # En siguiente paso dado a través de un navegador es llamar a tipoDocumentoNacionalidad con una
#                     # petición POST enviando como parámetro la "nacionalidad":
#                     nacionalidad_url = 'https://webpol.policia.es/e-hotel/combo/tipoDocumentoNacionalidad'
#                     nacionalidad_headers = {'Accept': 'text/html, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate, br',
#                                             'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
#                                             'Ajax-Referer': '/e-hotel/combo/tipoDocumentoNacionalidad',
#                                             'Connection': 'keep-alive',
#                                             'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
#                                             'Cookie': cookies_header, 'Host': 'webpol.policia.es',
#                                             'Referer': 'https://webpol.policia.es/e-hotel/inicio',
#                                             'User-Agent': 'python-requests/2.21.0',
#                                             'X-CSRF-TOKEN': csrf_token, 'X-Requested-With': 'XMLHttpRequest'}
#                     payload = {'nacionalidad': viajero.pais}
#                     try:
#                         p6 = s.post(nacionalidad_url, headers=nacionalidad_headers, cookies=dict(s.cookies),
#                                     data=payload,
#                                     timeout=5)
#                         logger.info("Enviado POST a tipoDocumentoNacionalidad")
#                     except:
#                         logger.info("Error al enviar POST a tipoDocumentoNacionalidad")
#                         return False
#                     # En este punto termina el proceso de grabación
#                     if p6.status_code == 200:
#                         logger.info(u'Todo correcto')
#                         s.close()
#                         viajero.fichero_policia = True
#                         viajero.observaciones += '<br><span style="color:green;">Registro finalizado con todas las comunicaciones correctas.</span>'
#                         viajero.observaciones += '<hr>Información JSON: <br> %s' % huespedJson
#                         viajero.save()
#                         return True
#                     else:
#                         logger.info('Error durante el grabado del viajero. Hacer el registro manualmente.')
#                         viajero.observaciones += '<br><span style="color:red;">Error durante el grabado del viajero. Hacer el registro manualmente.</span>'
#                         viajero.save()
#                         s.close()
#                         return p4
#                 else:
#                     logger.info(u'Error al hacer el login en webpol para el viajero: %s' % (viajero))
#                     viajero.observaciones += 'Error al hacer el login en webpol para el viajero'
#                     viajero.save()
#                     s.close()
#             else:
#                 return False
#         except:
#             logger.info("6")
#             mensaje = 'Error en la comunicación con Policía/Guardia Civil. Se debe hacer el registro manualmente.'
#             ronda = viajero.reserva.vivienda.entidad.ronda
#             permiso = Permiso.objects.get(code_nombre='recibe_errores_de_viajeros')
#             receptores_ge = Gauser_extra.objects.filter(ronda=ronda, permisos__in=[permiso])
#             receptores = Gauser.objects.filter(id__in=receptores_ge.values_list('gauser__id', flat=True))
#             emisor = Gauser_extra.objects.get(gauser=vivienda.gpropietario, ronda=vivienda.entidad.ronda)
#             encolar_mensaje(emisor=emisor, receptores=receptores,
#                             asunto='Error en RegistroPolicia', html=mensaje, etiqueta='error%s' % ronda.id)
#             return False


from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options


def registra_viajero_policia(viajero):
    hoy = timezone.now().date()
    ayer = hoy - timezone.timedelta(1)

    # options = webdriver.ChromeOptions()
    # options.add_argument('--ignore-certificate-errors')
    # driver = webdriver.Chrome(chrome_options=options)

    options = Options()
    # options.add_argument("--headless")
    # display = Display(visible=0, size=(800, 600))
    # display.start()

    profile = webdriver.FirefoxProfile()
    profile.accept_untrusted_certs = True
    driver = webdriver.Firefox(firefox_profile=profile, firefox_options=options,
                               log_path='%sgeckodriver.log' % MEDIA_VUT)
    driver.delete_all_cookies()
    wait = WebDriverWait(driver, 10)
    driver.get("https://webpol.policia.es/e-hotel/login")
    driver.find_element_by_name("username").send_keys(viajero.reserva.vivienda.police_code)
    driver.find_element_by_name("password").send_keys(viajero.reserva.vivienda.police_pass)
    driver.find_element_by_id('loginButton').click()
    driver.find_element_by_id('grabadorManual').click()
    # wait.until(EC.presence_of_element_located((By.ID, 'nombre')))
    wait.until(lambda gdriver: driver.execute_script("return jQuery.active == 0"))
    sleep(2)
    # ------------- nombre
    driver.execute_script("$('#nombre').focus()")
    driver.execute_script("$('#nombre').val('%s')" % viajero.nombre)
    driver.execute_script("$('#nombre').keyup()")
    driver.execute_script("$('#nombre').blur()")
    # ------------- apellido1
    driver.execute_script("$('#apellido1').focus()")
    driver.execute_script("$('#apellido1').val('%s')" % viajero.apellido1)
    driver.execute_script("$('#apellido1').keyup()")
    driver.execute_script("$('#apellido1').blur()")
    # ------------- apellido2
    driver.execute_script("$('#apellido2').focus()")
    driver.execute_script("$('#apellido2').val('%s')" % viajero.apellido2)
    driver.execute_script("$('#apellido2').keyup()")
    driver.execute_script("$('#apellido2').blur()")
    # ------------- nacionalidad
    driver.execute_script("$('#nacionalidad').focus()")
    driver.execute_script("$('#nacionalidad').val('%s')" % viajero.pais)
    driver.execute_script("$('#nacionalidad').trigger('chosen:updated').change()")
    driver.execute_script("$('#nacionalidad').keyup()")
    driver.execute_script("$('#nacionalidad').blur()")
    # Al actualizar la nacionalidad se hace una petición ajax para actualizar el 'tipoDocumento'
    # http://www.mahsumakbas.net/selenium-webdrvier-wait-jquery-ajax-request-complete-in-python/
    # Esperaremos a que esta petición finalice:
    wait.until(lambda gdriver: driver.execute_script("return jQuery.active == 0"))
    sleep(2)
    # ------------- tipoDocumento
    driver.execute_script("$('#tipoDocumento').focus()")
    driver.execute_script("$('#tipoDocumento').val('%s')" % viajero.tipo_ndi)
    driver.execute_script("$('#tipoDocumento').trigger('chosen:updated').change()")
    driver.execute_script("$('#tipoDocumento').keyup()")
    driver.execute_script("$('#tipoDocumento').blur()")
    # ------------- numIdentificacion
    driver.execute_script("$('#numIdentificacion').focus()")
    driver.execute_script("$('#numIdentificacion').val('%s')" % viajero.ndi)
    driver.execute_script("$('#numIdentificacion').keyup()")
    driver.execute_script("$('#numIdentificacion').blur()")
    # ------------- fechaExpedicionDoc
    driver.execute_script("$('#fechaExpedicionDoc').focus()")
    driver.execute_script(
        "$('#fechaExpedicionDoc').datepicker('update', '%s')" % viajero.fecha_exp.strftime('%d/%m/%Y'))
    driver.execute_script("$('#fechaExpedicionDoc').keyup()")
    driver.execute_script("$('#fechaExpedicionDoc').blur()")
    # -------------  dia
    driver.execute_script("$('#dia').focus()")
    driver.execute_script("$('#dia').val('%s')" % viajero.nacimiento.day)
    driver.execute_script("$('#dia').keyup()")
    driver.execute_script("$('#dia').blur()")
    # ------------- mes
    driver.execute_script("$('#mes').focus()")
    driver.execute_script("$('#mes').val('%s')" % viajero.nacimiento.month)
    driver.execute_script("$('#mes').keyup()")
    driver.execute_script("$('#mes').blur()")
    # ------------- año
    driver.execute_script("$('#ano').focus()")
    driver.execute_script("$('#ano').val('%s')" % viajero.nacimiento.year)
    driver.execute_script("$('#ano').keyup()")
    driver.execute_script("$('#ano').blur()")
    # ------------- sexo
    driver.execute_script("$('#sexo').focus()")
    driver.execute_script("$('#sexo').val('%s')" % viajero.sexo)
    driver.execute_script("$('#sexo').trigger('chosen:updated').change()")
    driver.execute_script("$('#sexo').keyup()")
    driver.execute_script("$('#sexo').blur()")
    if viajero.reserva.entrada == hoy or viajero.reserva.entrada == ayer:
        fechaEntrada = viajero.reserva.entrada.strftime('%d/%m/%Y')
    else:
        fechaEntrada = hoy.strftime('%d/%m/%Y')
    # ------------- fechaEntrada
    driver.execute_script("$('#fechaEntrada').focus()")
    driver.execute_script("$('#fechaEntrada').datepicker('update', '%s')" % fechaEntrada)
    driver.execute_script("$('#fechaEntrada').keyup()")
    driver.execute_script("$('#fechaEntrada').blur()")

    # #----------------------------------------------------------------#
    # # -----Esta parte debería utilizarse si no funcionara 'wait'-----#
    # # ---------------------------------------------------------------#
    # # Queda por rellenar el tipo de documento. Al cambiar la nacionalidad se borran tanto
    # # el tipo de documento como el número de documento
    # intentos = 10
    # n = 0
    # while n < intentos:
    #     n += 1
    #     sleep(0.5)
    #     tipo_documento = driver.find_element_by_id('tipoDocumento').get_attribute('value')
    #     if tipo_documento == viajero.tipo_ndi:
    #         n = 11
    #     else:
    #         driver.execute_script("$('#tipoDocumento').val('%s')" % viajero.tipo_ndi)
    #         driver.execute_script("$('#tipoDocumento').trigger('chosen:updated').change()")
    # if driver.find_element_by_id('tipoDocumento').get_attribute('value') == viajero.tipo_ndi:
    #     driver.find_element_by_id('numIdentificacion').send_keys(viajero.ndi)
    # else:
    #     viajero.observaciones += '<p>Registro cancelado. No se puede establecer el tipo de ndi</p>'
    #     viajero.save()
    #     return False
    # # ----------------------------------------------------------------#

    # Si la grabación de datos ha ido bien el siguiente paso es pulsar en 'btnGuardar':
    sleep(2)
    guardar = wait.until(EC.presence_of_element_located((By.ID, 'btnGuardar')))
    guardar.click()
    # sleep(5)
    # driver.close()
    # return False
    sleep(2)
    # Si esta acción funciona correctamente se mostrará un reval modal
    wait.until(lambda gdriver: driver.execute_script("return jQuery.active == 0"))
    try:
        modal = wait.until(EC.presence_of_element_located((By.ID, 'modal-parteHuesped')))
        # modal = driver.find_element_by_id('modal-parteHuesped')
        # Si existe el modal es porque se ha registrado correctamente el viajero
        # El siguiente paso sería buscar el botón de cancelar (la 'x' superior derecha)
        x = modal.find_element_by_xpath('//button')  # Botón 'x' para Cancelar
        x.click()  # Pulsamos para eliminar el modal
        # A continuación esperamos a que se recargue la página y salimos:
        wait.until(lambda gdriver: driver.execute_script("return jQuery.active == 0"))
        sleep(2)
        salir = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'fa-sign-out')))
        driver.find_element_by_class_name("fa-sign-out").click()
        salir.click()
        sleep(1)
        driver.close()
        return True
    except:
        # Si se produce una excepción aparecerá un mensaje genérico indicando los errores:
        try:
            e = driver.find_element_by_id('divMensajeGenerico')
            viajero.observaciones = e.text
            viajero.save()
            driver.find_element_by_class_name("fa-sign-out").click()
            driver.close()
            return False
        except:
            error = wait.until(EC.presence_of_element_located((By.ID, 'contenedor-error')))
            viajero.observaciones = error.text
            viajero.save()
            driver.find_element_by_class_name("fa-sign-out").click()
            driver.close()
            return False
