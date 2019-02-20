# -*- coding: utf-8 -*-
from __future__ import unicode_literals

TIPO = 'basic'  # 'basic' or 'selectable'.  'basic': necesario para el funcionamiento del programa
#                           'selectable': No necesario. Añade nuevas funcionalidades al programa
# Por ejemplo autenticar es 'basic', pero actas es prescindible

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_competencias_clave',
     'texto_menu': 'Competencias clave',
     'href': '', 'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'cc_valorar_mis_alumnos',
     'texto_menu': 'Valorar a mis alumnos',
     'href': 'cc_valorar_mis_alumnos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_competencias_clave'
     },
    {'code_menu': 'cc_valorar_cualquier_alumno',
     'texto_menu': 'Valorar a cualquier alumno',
     'href': 'cc_valorar_cualquier_alumno',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_competencias_clave'
     },
    {'code_menu': 'configura_ccs',
     'texto_menu': 'Ponderar competencias clave',
     'href': 'cc_configuracion',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_competencias_clave'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'valora_ccs_a_cualquier_alumno',
             'nombre': 'Tiene permiso para valorar las competencias clave a cualquier alumno',
             'menu': 'acceso_competencias_clave'
             },
            {'code_nombre': 'genera_informe_ccs',
             'nombre': 'Tiene permiso para generar el informe de valoración de las competencias clave',
             'menu': 'acceso_competencias_clave'
             },
            ]
