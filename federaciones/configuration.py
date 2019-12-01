# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_federaciones',
     'texto_menu': 'Federación',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_configura_federacion',
     'texto_menu': 'Configuración de Federación',
     'href': 'configura_federacion',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_federaciones'
     },
    {'code_menu': 'acceso_cuotas_federacion',
     'texto_menu': 'Configuración de cuotas',
     'href': 'cuotas_federacion',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_federaciones'
     },
    {'code_menu': 'acceso_documentos_federacion',
     'texto_menu': 'Documentos federación',
     'href': 'documentos_federacion',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_federaciones'
     },
    {'code_menu': 'acceso_inscribir_federacion',
     'texto_menu': 'Inscripción federación',
     'href': 'inscribir_federacion',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_federaciones'
     }
]

# Se añaden otros permisos para el usuario

PERMISOS = [
    {'code_nombre': 'crea_federaciones',
     'nombre': 'Tiene permiso para crear federaciones vinculadas a su entidad',
     'menu': 'acceso_configura_federacion'
     },
    {'code_nombre': 'borra_sus_federaciones',
     'nombre': 'Tiene permiso para borrar las federaciones vinculadas a su entidad',
     'menu': 'acceso_configura_federacion'
     },
    {'code_nombre': 'edita_sus_federaciones',
     'nombre': 'Tiene permiso para editar las federaciones vinculadas a su entidad',
     'menu': 'acceso_configura_federacion'
     }
]
