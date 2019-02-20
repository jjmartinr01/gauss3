# -*- coding: utf-8 -*-
from __future__ import unicode_literals
TIPO = 'selectable'  # 'basic' or 'selectable'.  'basic': necesario para el funcionamiento del programa
#                           'selectable': No necesario. Añade nuevas funcionalidades al programa
# Por ejemplo autenticar es 'basic', pero actas es prescindible

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_reparaciones',
     'texto_menu': 'Reparaciones',
     'href': 'gestionar_reparaciones',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_acciones_usuarios1'
     },
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_solicitud_reparacion',
             'nombre': 'Tiene permiso para crear una solicitud de reparación',
             'menu': 'acceso_reparaciones'
             },
            {'code_nombre': 'borra_solicitud_reparacion',
             'nombre': 'Tiene permiso para borrar cualquier solicitud de reparación',
             'menu': 'acceso_reparaciones'
             },
            {'code_nombre': 'controla_reparaciones_alb',
             'nombre': 'Tiene permiso para controlar las reparaciones de albañilería',
             'menu': 'acceso_reparaciones'
             },
            {'code_nombre': 'controla_reparaciones_car',
             'nombre': 'Tiene permiso para controlar las reparaciones de carpintería',
             'menu': 'acceso_reparaciones'
             },
            {'code_nombre': 'controla_reparaciones_ele',
             'nombre': 'Tiene permiso para controlar las reparaciones de electricidad',
             'menu': 'acceso_reparaciones'
             },
            {'code_nombre': 'controla_reparaciones_inf',
             'nombre': 'Tiene permiso para controlar las reparaciones de informática',
             'menu': 'acceso_reparaciones'
             },
            {'code_nombre': 'controla_reparaciones_fon',
             'nombre': 'Tiene permiso para controlar las reparaciones de fontanería',
             'menu': 'acceso_reparaciones'
             },
            {'code_nombre': 'controla_reparaciones_gen',
             'nombre': 'Tiene permiso para controlar las reparaciones de tipo general',
             'menu': 'acceso_reparaciones'
             },
            {'code_nombre': 'controla_reparaciones',
             'nombre': 'Tiene permiso para controlar cualquier reparación en la entidad',
             'menu': 'acceso_reparaciones'
             },
            {'code_nombre': 'genera_informe_reparaciones',
             'nombre': 'Tiene permiso para generar un informe con las reparaciones de la entidad',
             'menu': 'acceso_reparaciones'
             }
            ]
