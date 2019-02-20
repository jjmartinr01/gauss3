# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_mensajes',
     'texto_menu': 'Correo y mensajería',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_redactar_mensaje',
     'texto_menu': 'Redactar mensaje',
     'href': 'correo',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_mensajes'
     },
    {'code_menu': 'acceso_mensajes_enviados',
     'texto_menu': 'Mensajes enviados',
     'href': 'enviados',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_mensajes'
     },
    {'code_menu': 'acceso_mensajes_recibidos',
     'texto_menu': 'Mensajes recibidos',
     'href': 'recibidos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_mensajes'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'redacta_cualquier_usuario',
             'nombre': 'Tiene permiso para redactar mensajes a cualquier usuario de la entidad',
             'menu': 'acceso_redactar_mensaje'
             },
            {'code_nombre': 'redacta_usuarios_departamentos',
             'nombre': 'Tiene permiso para redactar mensajes a cualquier usuario de sus secciones/departamentos',
             'menu': 'acceso_redactar_mensaje'
             },
            {'code_nombre': 'redacta_usuarios_1',
             'nombre': 'Tiene permiso para redactar mensajes usuarios con cargos/perfiles de nivel 1',
             'menu': 'acceso_redactar_mensaje'
             },
            {'code_nombre': 'redacta_usuarios_2',
             'nombre': 'Tiene permiso para redactar mensajes usuarios con cargos/perfiles de nivel 2',
             'menu': 'acceso_redactar_mensaje'
             },
            {'code_nombre': 'redacta_usuarios_3',
             'nombre': 'Tiene permiso para redactar mensajes usuarios con cargos/perfiles de nivel 3',
             'menu': 'acceso_redactar_mensaje'
             },
            {'code_nombre': 'redacta_usuarios_4',
             'nombre': 'Tiene permiso para redactar mensajes usuarios con cargos/perfiles de nivel 4',
             'menu': 'acceso_redactar_mensaje'
             }
            ]
