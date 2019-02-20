# -*- coding: utf-8 -*-
from __future__ import unicode_literals

TIPO = 'selectable'  # 'basic' or 'selectable'.  'basic': necesario para el funcionamiento del programa
#                           'selectable': No necesario. Añade nuevas funcionalidades al programa
# Por ejemplo autenticar es 'basic', pero actas es prescindible

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_registro',
     'texto_menu': 'Registro',
     'href': 'registro',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_gestion_entidad'
     },
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_registros',
             'nombre': 'Tiene permiso para crear registros en la entidad',
             'menu': 'acceso_registro'
             },
            {'code_nombre': 'borra_registros',
             'nombre': 'Tiene permiso para borrar registros en la entidad',
             'menu': 'acceso_registro'
             }
            ]
