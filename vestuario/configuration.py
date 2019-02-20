# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_vestuario',
     'texto_menu': 'Vestuario',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_define_vestuario',
     'texto_menu': 'Crea vestuario',
     'href': 'crea_vestuario',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_vestuario'
     },
    {'code_menu': 'acceso_solicitudes_vestuario',
     'texto_menu': 'Solicitudes vestuario',
     'href': 'solicitudes_vestuario',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_vestuario'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_item_vestuario',
             'nombre': 'Tiene permiso para crear items del vestuario de la entidad',
             'menu': 'acceso_define_vestuario'
             },
            {'code_nombre': 'borra_item_vestuario',
             'nombre': 'Tiene permiso para borrar items del vestuario de la entidad',
             'menu': 'acceso_define_vestuario'
             },
            {'code_nombre': 'solicita_item_vestuario',
             'nombre': 'Tiene permiso para solicitar items del vestuario de la entidad',
             'menu': 'acceso_solicitudes_vestuario'
             },
            {'code_nombre': 've_solicitudes_vestuario',
             'nombre': 'Tiene permiso para ver las solicitudes de vestuario de la entidad',
             'menu': 'acceso_solicitudes_vestuario'
             },
            {'code_nombre': 'gestiona_solicitudes_vestuario',
             'nombre': 'Tiene permiso para gestionar las solicitudes del vestuario de la entidad',
             'menu': 'acceso_solicitudes_vestuario'
             }
            ]
