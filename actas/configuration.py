# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_actas',
     'texto_menu': 'Actas',
     'href': '', 'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
{'code_menu': 'acceso_configurar_convocatorias',
     'texto_menu': 'Configurar convocatorias',
     'href': 'configurar_convocatorias',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_actas'
     },
    {'code_menu': 'acceso_convocatorias',
     'texto_menu': 'Convocatorias',
     'href': 'convocatorias',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_actas'
     },
    {'code_menu': 'acceso_ver_actas',
     'texto_menu': 'Ver actas',
     'href': 'ver_actas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_actas'
     },
    {'code_menu': 'acceso_redactar_actas',
     'texto_menu': 'Redactar actas',
     'href': 'redactar_actas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_actas'
     },
    {'code_menu': 'acceso_actillas2',
     'texto_menu': 'Actillas',
     'href': 'actillas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 5,
     'parent': 'acceso_actas'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 've_todas_convocatorias',
             'nombre': 'Tiene permiso para ver cualquier convocatoria',
             'menu': 'acceso_convocatorias'
             },
            {'code_nombre': 've_todas_actas',
             'nombre': 'Tiene permiso para ver cualquier acta',
             'menu': 'acceso_ver_actas'
             },
            {'code_nombre': 'crea_convocatorias',
             'nombre': 'Tiene permiso para crear convocatorias',
             'menu': 'acceso_convocatorias'
             },
            {'code_nombre': 'edita_convocatorias',
             'nombre': 'Tiene permiso para editar las convocatorias de la entidad',
             'menu': 'acceso_convocatorias'
             },
            {'code_nombre': 'edita_convocatorias_subentidades',
             'nombre': 'Edita las convocatorias de las subentidades a las que pertenece',
             'menu': 'acceso_convocatorias'
             },
            {'code_nombre': 'borra_convocatorias',
             'nombre': 'Tiene permiso para borrar convocatorias',
             'menu': 'acceso_convocatorias'
             },
            {'code_nombre': 'mail_convocatorias',
             'nombre': 'Tiene permiso para enviar por mail convocatorias',
             'menu': 'acceso_convocatorias'
             },
            {'code_nombre': 'evento_convocatorias',
             'nombre': 'Tiene permiso para crear eventos en el calendario de las convocatorias',
             'menu': 'acceso_convocatorias'
             },
            {'code_nombre': 'redacta_sus_actas',
             'nombre': 'Tiene permiso para redactar las actas de sus convocatorias',
             'menu': 'acceso_redactar_actas'
             },
            {'code_nombre': 'redacta_actas_subentidades',
             'nombre': 'Tiene permiso para redactar las actas de las subentidades a las que pertenece',
             'menu': 'acceso_redactar_actas'
             },
            {'code_nombre': 'redacta_cualquier_acta',
             'nombre': 'Tiene permiso para redactar cualquier acta de la entidad',
             'menu': 'acceso_redactar_actas'
             },
            {'code_nombre': 'genera_actillas2',
             'nombre': 'Tiene permiso para generar actillas de cualquier grupo de la entidad',
             'menu': 'acceso_actillas2'
             },
            {'code_nombre': 'crea_configuraciones_convocatorias',
             'nombre': 'Tiene permiso para crear configuraciones de convocatorias',
             'menu': 'acceso_configurar_convocatorias'
             },
            {'code_nombre': 'edita_configuraciones_convocatorias',
             'nombre': 'Tiene permiso para editar cualquier configuración de convocatorias de la entidad',
             'menu': 'acceso_configurar_convocatorias'
             },
            {'code_nombre': 'borra_configuraciones_convocatorias',
             'nombre': 'Tiene permiso para borrar cualquier configuración de convocatorias de la entidad',
             'menu': 'acceso_configurar_convocatorias'
             },
            {'code_nombre': 'mail_actas',
             'nombre': 'Tiene permiso para enviar por mail las actas',
             'menu': 'acceso_redactar_actas'
             }
            ]
