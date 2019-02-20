# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_cuestionarios',
     'texto_menu': 'Cuestionarios',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_formularios',
     'texto_menu': 'Formularios',
     'href': 'formularios',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_cuestionarios'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_formularios',
             'nombre': 'Tiene permiso para crear formularios para la entidad',
             'menu': 'acceso_formularios'
             }
            ]
