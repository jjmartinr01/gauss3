# -*- coding: utf-8 -*-
from django.template import Library
from autenticar.models import Permiso
from absentismo.models import *
from entidades.models import Subentidad

register = Library()


@register.filter
def has_cargos(gauser_extra, cargos_comprobar):
    if gauser_extra.gauser.username == 'gauss':
        return True
    else:
        return len([cargo for cargo in gauser_extra.cargos.all() if cargo in cargos_comprobar]) > 0

@register.filter
def has_permiso(gauser_extra, permiso_comprobar):
    if gauser_extra.gauser.username == 'gauss' or permiso_comprobar == 'libre':
        return True
    else:
        try:
            permiso = Permiso.objects.get(code_nombre=permiso_comprobar)
        except:
            return False
        if permiso in gauser_extra.permisos.all():
            return True
        else:
            for cargo in gauser_extra.cargos.all():
                if permiso in cargo.permisos.all():
                    return True
            return False
