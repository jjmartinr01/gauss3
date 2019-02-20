# -*- coding: utf-8 -*-
from django.contrib import admin
from bancos.models import Banco


class Banco_Admin(admin.ModelAdmin):
    search_fields = ['codigo','bic']

admin.site.register(Banco, Banco_Admin)