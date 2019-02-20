# -*- coding: utf-8 -*-
from __future__ import unicode_literals
TIPO = 'selectable'  # 'basic' or 'selectable'.  'basic': necesario para el funcionamiento del programa
#                           'selectable': No necesario. Añade nuevas funcionalidades al programa
# Por ejemplo autenticar es 'basic', pero actas es prescindible

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_actividades',
     'texto_menu': 'Actividades',
     'href': 'gestionar_actividades',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_acciones_usuarios1'
     },
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_actividad',
             'nombre': 'Tiene permiso para crear una actividad para la entidad',
             'menu': 'acceso_actividades'
             },
            {'code_nombre': 'borra_actividad',
             'nombre': 'Tiene permiso para borrar una actividad de la entidad',
             'menu': 'acceso_actividades'
             },
            {'code_nombre': 'edita_actividades',
             'nombre': 'Tiene permiso para editar cualquier actividad de la entidad',
             'menu': 'acceso_actividades'
             },
            {'code_nombre': 'crea_informe_actividades',
             'nombre': 'Tiene permiso para crear un informe de las actividades realizadas',
             'menu': 'acceso_actividades'
             },
            {'code_nombre': 'aprueba_actividades',
             'nombre': 'Tiene permiso para aprobar actividades de la entidad',
             'menu': 'acceso_actividades'
             }
            ]
