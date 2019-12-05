# -*- coding: utf-8 -*-

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_faqs',
     'texto_menu': 'Preguntas frecuentes',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_configura_faqs',
     'texto_menu': 'Configuración de FAQs',
     'href': 'configura_faqs',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_faqs'
     },
    {'code_menu': 'acceso_faqs_gauss',
     'texto_menu': 'Preguntas sobre GAUSS',
     'href': 'faqs_gauss',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_faqs'
     },
    {'code_menu': 'acceso_faqs_entidad',
     'texto_menu': 'Preguntas de la entidad',
     'href': 'faqs_entidad',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_faqs'
     }
]

# Se añaden otros permisos para el usuario

PERMISOS = [
    {'code_nombre': 'crea_faqs_gauss',
     'nombre': 'Tiene permiso para crear preguntas frecuentes sobre gauss',
     'menu': 'acceso_configura_faqs'
     },
    {'code_nombre': 'crea_secciones_faqs',
     'nombre': 'Tiene permiso para crear secciones para las preguntas frecuentes',
     'menu': 'acceso_configura_faqs'
     },
    {'code_nombre': 'crea_faqs_entidad',
     'nombre': 'Tiene permiso para crear preguntas frecuentes de la entidad',
     'menu': 'acceso_configura_faqs'
     },
    {'code_nombre': 'edita_faqs_entidad',
     'nombre': 'Tiene permiso para editar las preguntas frecuentes de la entidad',
     'menu': 'acceso_configura_faqs'
     }
]
