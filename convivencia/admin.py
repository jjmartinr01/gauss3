from django.contrib import admin
from convivencia.models import *

# Register your models here.

admin.site.register(Sancion)
admin.site.register(Conducta)
admin.site.register(Informe_sancionador)
admin.site.register(Expulsar)
admin.site.register(ConfiguraConvivencia)