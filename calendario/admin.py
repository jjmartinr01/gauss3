# -*- coding: utf-8 -*-
from django.contrib import admin
from calendario.models import Vevent, Calendar

admin.site.register(Vevent)
admin.site.register(Calendar)