# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import simplejson as json
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from calendario.models import Vevent
from formularios.models import Gform, Ginput
from formularios.views import crea_ginputs_para_rellenador
from gtelegram.models import Update, Message, User, Chat, Genera_code

# from entidades.models import Subentidad, Cargo
# from autenticar.models import Gauser_extra, Gauser
from entidades.models import Subentidad, Cargo, Gauser_extra
from autenticar.models import Gauser

import random
import requests
import re
import time
import locale
locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')

key = '166888701:AAFMSZgh9GEL59mmOH_Gv91aibU5b-Eg13Q'
url_myBot = 'https://api.telegram.org/bot%s/' % (key)

# Comandos:
identificador = 'identificador'
eventos = ['actividades', 'calendario', 'eventos']
comandos = [('list_eventos', 'eventos'), ('list_eventos', 'actividades'), ('list_eventos', 'calendario'),
            ('identificador', 'identif'), ('list_cuestionarios', 'cuesti'), ('list_cuestionarios', 'formulario'),
            ('list_cuestionarios', 'pregunta')]

comando = {'/identificador': {'message_chat': 'Te he enviado tu identificador a nuestro chat privado', 'message_user':
    'user.id_telegram'}}

# Al añadir GAUSS Telegram a un grupo se genera el siguiente update:
{"update_id": 618393596,
 "message": {"message_id": 135, "from": {"id": 43985100, "first_name": "Juanjo", "last_name": "Mart\u00edn"},
             "chat": {"id": -91046669, "title": "Tropa Monte Clavijo", "type": "group"}, "date": 1451130588,
             "new_chat_participant": {"id": 166888701, "first_name": "GAUSS Telegram", "username": "GAUSS_bot"}}}

# El robot sólo recibe mensajes que comienzan por "/" (https://core.telegram.org/bots#privacy-mode)
{"update_id": 618393598,
 "message": {"message_id": 141, "from": {"id": 43985100, "first_name": "Juanjo", "last_name": "Mart\u00edn"},
             "chat": {"id": -91046669, "title": "Tropa Monte Clavijo", "type": "group"}, "date": 1451133962,
             "text": "\/identificador"}}


def envia_telegram(g_e, texto, gausers=Gauser.objects.none(), gauser_extras=Gauser_extra.objects.none(),
                   subentidades=Subentidad.objects.none(), cargos=Cargo.objects.none()):
    chats_sub = Chat.objects.filter(subentidad__in=subentidades).distinct()
    for chat in chats_sub:
        url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (chat.id_telegram, texto)
        requests.get(url)
    # g_es = Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, ronda=g_e.ronda)
    # g_cargos = list(g_es.filter(cargos__in=cargos).values_list('gauser__id', flat=True))
    # g_subentidades = list(g_es.filter(subentidades__in=subentidades).values_list('gauser__id', flat=True))
    g_gausers = list(gausers.values_list('id', flat=True))
    g_gauser_extras = list(gauser_extras.values_list('gauser__id', flat=True))
    todos = g_gausers + g_gauser_extras + [g_e.gauser.id]
    gausers = Gauser.objects.filter(id__in=todos).distinct()
    usuarios_telegram = User.objects.filter(gauser__in=gausers).distinct()
    for usuario in usuarios_telegram:
        url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (usuario.id_telegram, texto)
        requests.get(url)
        time.sleep(0.05)
    return True

def envia_telegram_gausers(gausers=Gauser.objects.none(), texto=''):
    usuarios_telegram = User.objects.filter(gauser__in=gausers).distinct()
    for usuario in usuarios_telegram:
        url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (usuario.id_telegram, texto)
        requests.get(url)
        time.sleep(0.1)
    return True

def gform_respuesta(m):
    # Si durante el tratamiento 'texto' toma un valor implicará que se ha producido un error:
    texto=''
    # Guardo en la variable user el usuario de Telegram por conveniencia
    user = m.user
    # Tomo la última ginput almacenada en user y que por tanto es la que va a ser contestada:
    ginput=user.last_answered_ginput
    if ginput.tipo == 'gtext':
        ginput.gtext == m.message
    elif ginput.tipo == 'gdate':
        try:
            ginput.gdate = datetime.strptime(m.message, '%d/%m/%Y')
        except:
            texto = 'Error. La fecha tiene que estar en formato dd/mm/YYYY'
    elif ginput.tipo == 'gdatetime':
        try:
            ginput.gdatetime = datetime.strptime(m.message, '%d/%m/%Y %H:%M')
        except:
            texto = 'Error. La fecha tiene que estar en formato dd/mm/YYYY HH:MM'
    elif ginput.tipo == 'gchar':
        ginput.gchar = m.message
    elif ginput.tipo == 'gint':
        try:
            ginput.gint = int(m.message)
        except:
            texto = u'Error. Debes introducir un número sin decimales (número entero).'
    elif ginput.tipo == 'gfloat':
        try:
            ginput.gfloat = float(m.message)
        except:
            texto = u'Error. Debes introducir un número.'
    elif ginput.tipo == 'gbool':
        if re.search(r'[sSyY].*', m.message):
            ginput.gbool = True
        elif re.search(r'[nN].*', m.message):
            ginput.gbool = False
        else:
            texto = u'Error. Debes contestar "Sí" o "No" (S o N también es válido).'
    if not texto:
        ginput.save()
        gform = ginput.gform
        try:
            texto = 'Intenta encontrar un gauser_extra'
            g_e = user.g_es.filter(entidad=gform.propietario.entidad)[0]
            ginput = gform.ginput_set.filter(ginput__isnull=False, id__gt=user.last_answered_ginput.id,
                                             rellenador=g_e).order_by('ginput__row', 'ginput__col')[0]
            user.last_answered_ginput = ginput
            user.save()
            texto = ginput.ginput.label
        except:
            user.answering_gform = False
            user.last_answered_ginput = None
            user.save()
            texto = 'Has terminado de rellenar el cuestionario.'
    # Si no es ok significa que la respuesta no ha sido dada en el formato adecuado y debe formularse de nuevo
    else:
        texto += '%0A' + '%s' % ginput.ginput.label
    return texto


@csrf_exempt
def telegram_webhook(request):
    data_string = request.body
    # Example of data_string:
    # {"update_id": 618393558,
    #  "message": {"message_id": 52, "from": {"id": 43985100, "first_name": "Juanjo", "last_name": "Mart\u00edn"},
    #              "chat": {"id": 43985100, "first_name": "Juanjo", "last_name": "Mart\u00edn", "type": "private"},
    #              "date": 1450636046, "text": "Hola"}}
    # {"update_id": 618393558, "message": {"message_id": 52, "from": {"id": 43985100, "first_name": "Juanjo", "last_name": "Mart\u00edn"}, "chat": {"id": 43985100, "first_name": "Juanjo", "last_name": "Mart\u00edn", "type": "private"},"date": 1450636046, "text": "Hola"}}
    data = json.loads(data_string)
    update = Update.objects.create(id_telegram=data['update_id'], json=data_string)
    message = data['message']
    ahora = timezone.now()
    try:
        user = User.objects.get(id_telegram=message['from']['id'])

    except:
        user = User.objects.create(id_telegram=message['from']['id'], first_name=message['from']['first_name'],
                                   last_name=message['from']['last_name'])
    g_es = user.g_es  # Si no hay gauser, los g_es (Gauser_extra) devueltos será un conjunto vacío
    if g_es:
        texto = 'Mensaje sin ningún significado para mí'  # Mensaje que devolverá el bot si no entiende el mensaje
    else:
        texto = 'Tu usuario no está conectado con GAUSS.%0AEntra en GAUSS -> Mis datos y sigue las ' + \
                'instrucciones para conectar tus usuarios de GAUSS y Telegram.'

    if message['from']['id'] != message['chat']['id']:
        chat = message['chat']
        try:
            group = Chat.objects.get(id_telegram=chat['id'])
        except:
            group = Chat.objects.create(id_telegram=chat['id'], type=chat['type'], title=chat['type'])

    if 'new_chat_participant' in message:
        texto = 'Gauss Telegram forma parte del nuevo grupo'

    if 'text' in message:
        # Guardo el mensaje recibido en la base de datos de GAUSS
        m = Message.objects.create(id_telegram=message['message_id'], user=user, message=message['text'],
                                   date=datetime.fromtimestamp(message['date']), update=update)
        # Comparo si la cadena enviada coincide con alguno de los comandos definidos
        coincidencias = [c[0] for c in comandos if c[1] in m.message.lower()]
        # Selecciono la primera coincidencia de la lista, en el caso de que haya.
        comando = coincidencias[0] if len(coincidencias) > 0 else ''
        # Defino un teclado vacío por si es necesario incluirlo en la respuesta
        teclado = {'keyboard': [], 'one_time_keyboard': True}

        # En primer lugar compruebo si se está respondiendo a un formulario. En ese caso se ejecutan las órdenes
        # relacionadas con este tipo de acciones. Observa que una respuesta de texto podría contener una cadena que
        # se ajustara a un comando y que no debería ejecutarse como tal.
        if user.selecting_gform and (m.message == 'Cancelar' or m.message == 'cancelar'):
            texto = 'Se ha cancelado el rellenado del formulario.'
            user.selecting_gform = False
            user.last_answered_ginput = None
            user.save()
            url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (user.id_telegram, texto)
            requests.get(url)
            return HttpResponse(status=200)

        elif re.search(r'^[0-9]{4}$', message['text']):
            try:
                hace_5_minutos = timezone.now() - timedelta(seconds=300)
                genera = Genera_code.objects.get(creado__gte=hace_5_minutos, code=m.message)
                user.gauser = genera.gauser
                user.save()
                texto = 'Tus usuarios de GAUSS y Telegram se han conectado.'
            except:
                texto = 'No se ha podido conectar con ningún usuario. Comprueba que el código lo has ' + \
                        'generado hace menos de 5 minutos.%0APor favor vuelve a intentarlo.'

        elif user.answering_gform:
            if m.message == 'Cancelar' or m.message == 'cancelar':
                texto = 'Se ha cancelado el rellenado del formulario.'
                user.answering_gform = False
                user.last_answered_ginput = None
                user.save()
                url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (user.id_telegram, texto)
                requests.get(url)
                return HttpResponse(status=200)
            # Envío la última ginput almacenada en user y que por tanto es la que va a ser contestada.
            texto = gform_respuesta(m)

        # Si coincide la siguiente regex significa que el usuario ha seleccionado un formulario para responder
        elif re.search(r'^.*\([0-9]+\)$', message['text']) and user.selecting_gform:
            # Un botón de cuestionario coincidirá con la regex del 'if' anterior
            gform = Gform.objects.get(id=int(re.search(r'^.*\(([0-9]+)\)$', message['text']).group(1)))
            g_e = g_es.filter(entidad=gform.propietario.entidad)[0]
            crea_ginputs_para_rellenador(gform, g_e)
            ginput = gform.ginput_set.filter(ginput__isnull=False,
                                             rellenador=g_e).order_by('ginput__row', 'ginput__col')[0]
            user.answering_gform = True
            user.selecting_gform = False
            user.last_answered_ginput = ginput
            user.save()
            texto = ginput.ginput.label

        elif comando == 'identificador' and not user.selecting_gform:
            texto = user.id_telegram

        elif comando == 'list_eventos' and user.gauser and not user.selecting_gform:
            fecha_max = (ahora + timedelta(days=31)).date()
            subentidades = list()
            for g_e in g_es: subentidades += g_e.subentidades_hijos()
            vevents = Vevent.objects.filter(Q(subentidades__in=subentidades) | Q(invitados__in=[g_e.gauser]) | Q(
                    propietarios__in=[g_e.gauser]), dtend__gte=ahora, dtstart__lte=fecha_max).order_by('dtstart').distinct()
            texto = 'No tienes eventos programados en los próximos 30 días.' if vevents.count() == 0 else ''
            for vevent in vevents:
                f = datetime.strftime(vevent.dtstart, "%A, %d de %B de %Y, a las %H:%M")
                f = f if isinstance(f,str) else f.encode('utf-8')
                s = vevent.summary if isinstance(vevent.summary, str) else vevent.summary.encode('utf-8')
                n = vevent.entidad.name if isinstance(vevent.entidad.name, str) else vevent.entidad.name.encode('utf-8')
                texto += f + '-' + s + ' (' + n + ')%0A---------%0A'

        elif comando == 'list_cuestionarios' and user.gauser and not user.selecting_gform:
            cargos = g_es.values_list('cargos__id', flat=True).distinct()
            subentidades = g_es.values_list('subentidades__id', flat=True).distinct()
            formularios = Gform.objects.filter(Q(activo=True), Q(subentidades_destino__in=subentidades) | Q(
                    cargos_destino__in=cargos)).distinct()
            for gform in formularios:
                teclado['keyboard'].append(['%s (%s)' % (gform.nombre, gform.id)])
            if formularios.count() == 0:
                texto = 'No tienes ningún formulario/cuestionario que rellenar.'
            elif formularios.count() == 1:
                texto = 'Tienes un formulario/cuestionario que rellenar. Pulsa el botón para comenzar a responder.'
                teclado['keyboard'].append(['Cancelar'])
                user.selecting_gform = True
            elif formularios.count() > 1:
                texto = 'Selecciona el formulario/cuestionario que quieres empezar a responder.'
                teclado['keyboard'].append(['Cancelar'])
                user.selecting_gform = True
            user.save()



    if teclado['keyboard']:
        url = url_myBot + 'sendMessage?chat_id=%s&text=%s&reply_markup=%s' % (
            user.id_telegram, texto, json.dumps(teclado))
    else:
        url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (user.id_telegram, texto)
    requests.get(url)
    return HttpResponse(status=200)


@login_required()
def gtelegram_ajax(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']

        if request.POST['action'] == 'genera_code':
            code = str(random.randint(1000, 9999))
            Genera_code.objects.create(code=code, gauser=g_e.gauser)
            return JsonResponse({'title': '<i class="fa fa-warning"></i> Error', 'code': code})
        elif request.POST['action'] == 'user_identificador':
            id_telegram = request.POST['user_id'].replace(' ', '')
            try:
                user = User.objects.get(gauser=g_e.gauser)
                if str(user.id_telegram) == id_telegram:
                    texto = 'Tu usuario de Telegram esta conectado con tu usuario de GAUSS. Muchas Gracias.'
                    url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (user.id_telegram, texto)
                    r = requests.get(url)
                    return JsonResponse({'estado': 'ok', 'title': '<i class="fa fa-thumbs-o-up"></i> Correcto',
                                         'mensaje': 'Tu identificador ya estaba grabado y no se ha modificado.'})
                else:
                    try:
                        men_id = Message.objects.filter(message=identificador, user=user).order_by('id').reverse()[0]
                        if str(json.loads(men_id.update.json)['message']['from']['id']) == id_telegram:
                            secs = (timezone.now() - men_id.date).seconds
                        else:
                            secs = 1000
                    except:
                        secs = 1000
                    if secs < 300:  # Para cambiar el identificador la ejecucion de /identificador y la grabacion en Gauss no debe exceder los cinco minutos
                        user.id_telegram = int(id_telegram)
                        user.save()
                        texto = 'Tu nuevo identificador se ha grabado. Tus usuarios de GAUSS y Telegram están ' + \
                                'conectados entre sí.'
                        url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (user.id_telegram, texto)
                        r = requests.get(url)
                        return JsonResponse({'estado': 'ok', 'title': '<i class="fa fa-thumbs-o-up"></i> Correcto',
                                             'mensaje': texto})
                    else:
                        texto = 'Desde que pides el identificador a GAUSS Telegram (comando /identificador) ' + \
                                'hasta el momento en el que lo introduces en GAUSS no deben pasar más de 5 ' + \
                                'minutos. Tu identificador no se ha grabado porque, o bien no has pedido ese ' + \
                                'identificador o lo has hecho hace más de 5 minutos.'
                        url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (user.id_telegram, texto)
                        r = requests.get(url)
                        return JsonResponse({'title': '<i class="fa fa-warning"></i> Error', 'mensaje': texto})
            except:
                try:
                    user = User.objects.get(id_telegram=int(id_telegram))
                    try:
                        men_id = Message.objects.filter(message=identificador, user=user).order_by('id').reverse()[0]
                        secs = (timezone.now() - men_id.date).seconds
                    except:
                        secs = 1000
                    if secs < 300:  # Para cambiar el identificador la ejecucion de /identificador y la grabacion en Gauss no debe exceder los cinco minutos
                        user.gauser = g_e.gauser
                        user.save()
                        texto = 'Tus usuarios de GAUSS y de Telegram se han conectado entre sí.'
                        url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (user.id_telegram, texto)
                        r = requests.get(url)
                        return JsonResponse({'title': '<i class="fa fa-thumbs-o-up"></i> Correcto',
                                             'mensaje': texto})
                    else:
                        texto = 'Desde que pides el identificador a GAUSS Telegram (comando /identificador) ' + \
                                'hasta el momento en el que lo introduces en GAUSS no deben pasar más de 5 ' + \
                                'minutos. Tu usuario de GAUSS y tu usuario de Telegram no se han conectado ' + \
                                'entre sí por una de estas dos razones: no has pedido tu identificador ' + \
                                'correctamente o lo has hecho hace más de 5 minutos.'
                        url = url_myBot + 'sendMessage?chat_id=%s&text=%s' % (user.id_telegram, texto)
                        r = requests.get(url)
                        return JsonResponse({'title': '<i class="fa fa-warning"></i> Error', 'mensaje': texto})
                except:
                    texto = 'El código que has introducido no es correcto. '
                    return JsonResponse({'title': '<i class="fa fa-warning"></i> Error', 'mensaje': texto})


                    # try:
                    #     user = User.objects.get(gauser__isnull=True, id_telegram=id_telegram)
                    # except:
                    #     return JsonResponse({'estado': 'ok'})
                    # gform = Gform.objects.get(pk=request.POST['id_telegram'], propietario__entidad=g_e.ronda.entidad)
                    # if gform.activo == False:
                    #     gform.delete()
                    # gforms = Gform.objects.filter(propietario__entidad=g_e.ronda.entidad)
                    # data = render_to_string('formularios_accordion.html', {'gforms': gforms})
                    # return HttpResponse(data)
