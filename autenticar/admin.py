# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django import forms

from autenticar.models import Enlace, Gauser, Permiso, Menu_default



class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Gauser

class MyUserAdmin(UserAdmin):

    form = MyUserChangeForm

    fieldsets = UserAdmin.fieldsets + (
            (None, {'fields': ('sexo', 'dni', 'address', 'postalcode', 'localidad', 'provincia', 'nacimiento', 'telfij', 'telmov', 'familia')}),
    )
    UserAdmin.ordering = ['-id']

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("user_permissions")
        ## Dynamically overriding
        #self.fieldsets[2][1]["fields"] = ('is_active', 'is_staff','is_superuser','groups')
        self.fieldsets[2][1]["fields"] = ('is_active',)
        form = super(MyUserAdmin,self).get_form(request, obj, **kwargs)
        return form


class PermisoAdmin(admin.ModelAdmin):
    search_fields = ['nombre', 'code_nombre']
    # list_filter = ['entidad', 'entidad__ronda']


admin.site.register(Gauser, MyUserAdmin)
admin.site.register(Permiso, PermisoAdmin)
admin.site.register(Enlace)
admin.site.register(Menu_default)