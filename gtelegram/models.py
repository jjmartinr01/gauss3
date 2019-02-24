from django.db import models

# from autenticar.models import Gauser, Gauser_extra
# from entidades.models import Subentidad
from autenticar.models import Gauser
from entidades.models import Subentidad, Gauser_extra

from django.utils import timezone
import simplejson as json
from datetime import datetime, timedelta

from formularios.models import Gform, Ginput


class Update(models.Model):
    id_telegram = models.CharField('Identificador del update de Telegram', max_length=40)
    json = models.TextField('La respuesa JSON enviada por Telegram', blank=True, null=True)

    def __str__(self):
        data = json.loads(self.json)
        if data['message']['from']['id'] == data['message']['chat']['id']:
            ids = '%s (%s)' % (data['message']['from']['first_name'], data['message']['from']['id'])
        else:
            try:
                ids = '%s (%s), chat: %s (%s)' %(data['message']['from']['first_name'], data['message']['from']['id'], data['message']['chat']['title'], data['message']['chat']['id'])
            except:
                ids = '%s (%s), new_chat: %s (%s)' %(data['message']['from']['first_name'], data['message']['from']['id'], data['message']['new_chat_participant']['first_name'], data['message']['new_chat_participant']['id'])
        f = datetime.fromtimestamp(data['message']['date']).strftime('%d/%m/%Y %H:%M')
        try:
            texto = data['message']['text']
        except:
            texto = ''
        m_id = data['message']['message_id']
        return u'%s, Message: %s (%s) -- %s -- %s' % (self.id_telegram, m_id, f, ids, texto)

"""
{'update_id': 821066347, 'message': {'text': 'asd', 'message_id': 7, 'from': {'first_name': 'Orlando', 'last_name': 'Fiol', 'id': 61208967, 'username': 'overf1ow'}, 'chat': {'first_name': 'Orlando', 'last_name': 'Fiol', 'id': 61208967, 'username': 'overf1ow'}, 'date': 1438263658}}
{'update_id': 821066348, 'message': {'reply_to_message': {'text': 'Aaarghhh!!!', 'message_id': 8, 'from': {'first_name': 'asomaote', 'username': 'asomaoBot', 'id': 117225746}, 'chat': {'first_name': 'Orlando', 'last_name': 'Fiol', 'id': 61208967, 'username': 'overf1ow'}, 'date': 1438263660}, 'text': 'gay', 'message_id': 9, 'from': {'first_name': 'Orlando', 'last_name': 'Fiol', 'id': 61208967, 'username': 'overf1ow'}, 'date': 1438263667, 'chat': {'first_name': 'Orlando', 'last_name': 'Fiol', 'id': 61208967, 'username': 'overf1ow'}}}
"""

class Location(models.Model):
    longitude = models.FloatField() # 	Float 	Longitude as defined by sender
    latitude = models.FloatField() # 	Float 	Latitude as defined by sender

    def __str__(self):
        return u'Longitud: %s -- Latitud: %s' % (self.longitude, self.latitude)

class User (models.Model):
    id_telegram = models.IntegerField('Identificador del usuario de Telegram', blank=True, null=True)
    gauser = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    username = models.CharField('Username de Telegram', max_length=200, blank=True, null=True)
    first_name = models.CharField('First Name de Telegram', max_length=200, blank=True, null=True)
    last_name = models.CharField('Last Name de Telegram', max_length=200, blank=True, null=True)
    selecting_gform = models.BooleanField('Seleccionando un formulario', default=False)
    answering_gform = models.BooleanField('Respondiendo a un formulario con Telegram', default=False)
    #answered_ginputs = models.ManyToManyField(Ginput, blank=True)
    last_answered_ginput = models.ForeignKey(Ginput, blank=True, null=True, on_delete=models.CASCADE)

    @property
    def g_es(self):
        ahora = timezone.now()
        if self.gauser:
            return Gauser_extra.objects.filter(gauser=self.gauser, ronda__fin__gte=ahora.date())
        else:
            return Gauser_extra.objects.none()

    def __str__(self):
        if self.gauser:
            texto = 'identificado con %s' % self.gauser.get_full_name()
        else:
            texto = 'sin identificar con un usuario de GAUSS'
        return u'%s %s, %s' % (self.first_name, self.last_name, texto)

class Chat (models.Model):
    id_telegram = models.IntegerField('Identificador del chat de Telegram', blank=True, null=True)
    subentidad = models.ForeignKey(Subentidad, blank=True, null=True, on_delete=models.CASCADE)
    type = models.CharField('Tipo de chat', max_length=40, blank=True, null=True) #Type of chat, can be either "private", "group", "supergroup" or "channel"
    title = models.CharField('Nombre del chat', max_length=60, blank=True, null=True) #Optional. Title, for channels and group chats
    username = models.CharField('Username (para chats privados)', max_length=60, blank=True, null=True) #Optional. Username, for private chats and channels if available
    first_name = models.CharField('Firstname (para chats privados)', max_length=60, blank=True, null=True) #Optional. First name of the other party in a private chat
    last_name = models.CharField('Lastname (para chats privados)', max_length=60, blank=True, null=True) #Optional. Last name of the other party in a private chat

    def __str__(self):
        return u'%s (%s)' % (self.title, self.id_telegram)


class Message(models.Model):
    id_telegram = models.IntegerField('Identificador del mensaje de Telegram', blank=True, null=True)
    update = models.ForeignKey(Update, blank=True, null=True, on_delete=models.CASCADE)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    message = models.TextField('Texto del mensaje enviado por Telegram', blank=True, null=True)
    creado = models.DateTimeField('Fecha y hora en la que se crea', auto_now_add=True)
    modificado = models.DateTimeField('Fecha y hora en la que se modifica', auto_now=True)
    date = models.DateTimeField('Fecha y hora de Telegram para el mensaje enviado', blank=True, null=True)

    def __str__(self):
        texto = '...' if len(self.message) > 30 else ''
        return u'%s %s (%s - %s) -- %s' % (self.message[:30], texto, self.id_telegram, self.date, self.user)

class Response(models.Model):
    message = models.ForeignKey(Message, blank=True, null=True, on_delete=models.CASCADE)
    reply_to = models.ForeignKey(Message, related_name='reply_to', blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('message', 'reply_to')

    def __str__(self):
        return u'%s |<->| %s' % (self.message, self.reply_to)

class Genera_code(models.Model):
    code = models.CharField('Codigo para enlazar Gauser y Telegram', max_length=20, blank=True, null=True)
    gauser = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    creado = models.DateTimeField('Fecha y hora en la que se crea', auto_now_add=True)

    def __str__(self):
        return u'%s - %s (%s)' % (self.gauser.get_full_name(), self.code, self.creado)
