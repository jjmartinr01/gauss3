# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_mercadillo',
     'texto_menu': 'Mercadillo',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_productos_mercadillo',
     'texto_menu': 'Productos y servicios',
     'href': 'comprar_y_vender',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_mercadillo'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_productos_mercadillo',
             'nombre': 'Tiene permiso para crear productos para el mercadillo',
             'menu': 'acceso_productos_mercadillo'
             }
            ]
