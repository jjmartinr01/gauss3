# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_web',
     'texto_menu': 'Diseño WEB',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_contenidos_web',
     'texto_menu': 'Contenidos WEB',
     'href': 'web_design',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_web'
     },
    {'code_menu': 'acceso_noticias_web',
     'texto_menu': 'Noticias WEB',
     'href': 'noticias_web',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_web'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_paginas_web',
             'nombre': 'Tiene permiso para crear páginas web de la entidad',
             'menu': 'acceso_contenidos_web'
             },
            {'code_nombre': 'edita_paginas_web',
             'nombre': 'Tiene permiso para editar páginas web de la entidad',
             'menu': 'acceso_contenidos_web'
             },
            {'code_nombre': 'borra_paginas_web',
             'nombre': 'Tiene permiso para borrar páginas web de la entidad',
             'menu': 'acceso_contenidos_web'
             },
            {'code_nombre': 'escribe_noticias_web',
             'nombre': 'Tiene permiso para escribir noticias web de la entidad',
             'menu': 'acceso_noticias_web'
             },
            {'code_nombre': 'borra_noticias_web',
             'nombre': 'Tiene permiso para borrar cualquier noticia web de la entidad',
             'menu': 'acceso_noticias_web'
             },
            {'code_nombre': 'edita_noticias_web',
             'nombre': 'Tiene permiso para editar cualquier noticia web de la entidad',
             'menu': 'acceso_noticias_web'
             }
            ]
