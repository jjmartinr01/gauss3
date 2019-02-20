# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_calendario',
     'texto_menu': 'Calendario',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_vista_calendario',
     'texto_menu': 'Vista calendario',
     'href': 'calendario',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_calendario'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_eventos',
             'nombre': 'Tiene permiso para crear eventos',
             'menu': 'acceso_vista_calendario'
             },
            {'code_nombre': 've_todos_eventos',
             'nombre': 'Tiene permiso para ver cualquier evento de la entidad',
             'menu': 'acceso_vista_calendario'
             },
            {'code_nombre': 'borra_cualquier_evento',
             'nombre': 'Tiene permiso para borrar cualquier evento',
             'menu': 'acceso_vista_calendario'
             }
            ]
