# -*- coding: utf-8 -*-
from __future__ import unicode_literals

TIPO = 'selectable'  # 'basic' or 'selectable'.  'basic': necesario para el funcionamiento del programa
#                           'selectable': No necesario. Añade nuevas funcionalidades al programa
# Por ejemplo autenticar es 'basic', pero actas es prescindible

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_domotica',
     'texto_menu': 'Domótica',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1,
     },
    {'code_menu': 'acceso_grupos_domotica',
     'texto_menu': 'Agrupaciones de dispositivos',
     'href': 'grupos_domotica',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_domotica'
     },
    {'code_menu': 'acceso_configura_domotica',
     'texto_menu': 'Configurar domótica',
     'href': 'configura_domotica',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_domotica'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_grupos_domotica',
             'nombre': 'Permiso para crear un grupo de dispositivos domóticos',
             'menu': 'acceso_grupos_domotica'
             },
            {'code_nombre': 'borra_grupos_domotica',
             'nombre': 'Permiso para borrar cualquier grupo que contiene domótica',
             'menu': 'acceso_grupos_domotica'
             },
            {'code_nombre': 'edita_grupos_domotica',
             'nombre': 'Permiso para modificar cualquier grupo que contiene domótica',
             'menu': 'acceso_grupos_domotica'
             },
            {'code_nombre': 'crea_dispositivos_domotica',
             'nombre': 'Permiso para crear un dispositivo domótico',
             'menu': 'acceso_configura_domotica'
             },
            {'code_nombre': 'borra_dispositivos_domotica',
             'nombre': 'Permiso para borrar cualquier dispositivo domótico',
             'menu': 'acceso_configura_domotica'
             },
            {'code_nombre': 'edita_dispositivos_domotica',
             'nombre': 'Permiso para editar cualquier dispositivo domótico',
             'menu': 'acceso_configura_domotica'
             },
            {'code_nombre': 'crea_secuencias_domotica',
             'nombre': 'Permiso para crear una secuencia domótica',
             'menu': 'acceso_configura_domotica'
             },
            {'code_nombre': 'borra_secuencias_domotica',
             'nombre': 'Permiso para borrar cualquier secuencia domótica',
             'menu': 'acceso_configura_domotica'
             },
            {'code_nombre': 'edita_secuencias_domotica',
             'nombre': 'Permiso para modificar cualquier secuencia domótica',
             'menu': 'acceso_configura_domotica'
             },
            {'code_nombre': 'crea_conjuntos_domotica',
             'nombre': 'Permiso para crear un conjunto de dispositivos domóticos',
             'menu': 'acceso_configura_domotica'
             },
            {'code_nombre': 'borra_conjuntos_domotica',
             'nombre': 'Permiso para borrar cualquier conjunto de dispositivos domóticos',
             'menu': 'acceso_configura_domotica'
             },
            {'code_nombre': 'edita_conjuntos_domotica',
             'nombre': 'Permiso para modificar cualquier conjunto de dispositivos domóticos',
             'menu': 'acceso_configura_domotica'
             }
            ]
