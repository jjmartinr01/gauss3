# -*- coding: utf-8 -*-
import logging
from django.core.files.base import ContentFile
from time import sleep
from bs4 import BeautifulSoup
from celery import shared_task
from django.db.models import Q
import requests
from gauss.rutas import RUTA_BASE, MEDIA_VUT
from autenticar.models import Gauser, Permiso
from entidades.models import Gauser_extra
from mensajes.views import encolar_mensaje
from vut.models import RegistroPolicia, Viajero, Autorizado
from gtelegram.views import envia_telegram, envia_telegram_gausers

logger = logging.getLogger('django')


@shared_task
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
            gtexto = 'Error durante el proceso de registro. No existe viajero'
            envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
            return False
        if viajero.fichero_policia:
            gtexto = 'Se ha tratado de registrar un mismo viajero varias veces. Viajero: %s %s (%s)' % (
                viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
            envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
            return False
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
                    gtexto = 'Error al tratar de enviar el fichero de datos a la Guardia Civil. Viajero: %s %s (%s)' % (
                        viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                    envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
                        envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
                        envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
                    envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
                    viajero.save()
                    fichero.close()
                    return False
            elif vivienda.police == 'PN':
                logger.info("entra al registro PN. Viajero: %s" % viajero)
                # Iniciamos una sesión
                s = requests.Session()
                s.verify = False  # Para que los certificados ssl no sean verificados. Comunicación https confiada
                # Accedemos a la página de inicio y de la respuesta capturamos el token csrf
                try:
                    p1 = s.get('https://webpol.policia.es/e-hotel/', timeout=5)
                except:
                    gtexto = 'Error al tratar de acceder a la web de la Policía Nacional. Viajero: %s %s (%s)' % (
                        viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                    envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
                    gtexto = 'Error durante la obtención de etiquetas en la Policía Nacional. Viajero: %s %s (%s)' % (
                        viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                    envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
                    gtexto = 'Error durante el proceso de login en la Policía Nacional. Viajero: %s %s (%s)' % (
                        viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                    envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
                    gtexto = 'Error tras el proceso de login en la Policía Nacional. Viajero: %s %s (%s)' % (
                        viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                    envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
                        gtexto = 'Error durante el proceso de envío de los datos del huésped. Viajero: %s %s (%s)' % (
                            viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                        envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
                        gtexto = 'Error al entrar en el grabador manual de la Policía Nacional. Viajero: %s %s (%s)' % (
                            viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                        envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
                        gtexto = 'Error al enviar los datos del huésped. Viajero: %s %s (%s)' % (
                            viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                        envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
                        gtexto = 'Registrado en Policía el viajero: %s %s (%s)' % (
                        viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                        envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
                        return True
                    else:
                        logger.info('Error durante el grabado del viajero. Hacer el registro manualmente.')
                        viajero.observaciones += '<br><span style="color:red;">Error durante el grabado del viajero. Hacer el registro manualmente.</span>'
                        viajero.save()
                        s.close()
                        emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
                        gtexto = 'Error durante el grabado del viajero. Hacer el registro manualmente. Viajero: %s %s (%s)' % (
                            viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                        envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
                        return p4
                else:
                    logger.info(u'Error al hacer el login en webpol para el viajero: %s' % (viajero))
                    viajero.observaciones += 'Error al hacer el login en webpol para el viajero'
                    viajero.save()
                    s.close()
                    emisor = Gauser_extra.objects.get(gauser=vivienda.propietarios.all()[0], ronda=vivienda.entidad.ronda)
                    gtexto = 'Error al hacer el login en la web de la Policía Nacional. Viajero: %s %s (%s)' % (
                        viajero.nombre, viajero.apellido1, viajero.reserva.vivienda.nombre)
                    envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
            else:
                gtexto = 'Error. Debes indicar en GAUSS si el registro se hace en Policía Nacional o Guardia Civil. Vivienda: %s' % (
                    viajero.reserva.vivienda.nombre)
                envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
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
            envia_telegram_gausers(gausers=vivienda.propietarios.all(), texto=gtexto)
            return False