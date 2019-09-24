# -*- coding: utf-8 -*-
from __future__ import unicode_literals

TIPO = 'selectable'  # 'basic' or 'selectable'.  'basic': necesario para el funcionamiento del programa
#                           'selectable': No necesario. Añade nuevas funcionalidades al programa
# Por ejemplo autenticar es 'basic', pero actas es prescindible

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_moscosos',
     'texto_menu': 'Moscosos',
     'href': 'moscosos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_acciones_usuarios1'
     },
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'configura_moscosos',
             'nombre': 'Tiene permiso para configurar los moscosos',
             'menu': 'acceso_moscosos'
             }
            ]
