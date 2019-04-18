from django.contrib import admin
from domotica.models import *
# Register your models here.

admin.site.register(Grupo)
admin.site.register(Dispositivo)
admin.site.register(Secuencia)
admin.site.register(DispositivoSecuencia)
admin.site.register(GauserPermitidoGrupo)
admin.site.register(GauserPermitidoDispositivo)
