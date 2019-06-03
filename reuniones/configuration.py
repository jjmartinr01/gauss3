# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_reuniones',
     'texto_menu': 'Reuniones',
     'href': '', 'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_conv_template',
     'texto_menu': 'Plantillas de convocatorias',
     'href': 'conv_template',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_reuniones'
     },
    {'code_menu': 'acceso_conv_reunion',
     'texto_menu': 'Realizar convocatorias',
     'href': 'conv_reunion',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_reuniones'
     },
    # {'code_menu': 'acceso_ver_actas_reunion_reunion',
    #  'texto_menu': 'Ver actas',
    #  'href': 'ver_actas',
    #  'nivel': 2,
    #  'tipo': 'Accesible',
    #  'pos': 3,
    #  'parent': 'acceso_reuniones'
    #  },
    {'code_menu': 'acceso_redactar_actas_reunion',
     'texto_menu': 'Redactar actas',
     'href': 'redactar_actas_reunion',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_reuniones'
     },
    {'code_menu': 'acceso_control_asistencia_reunion',
     'texto_menu': 'Control de asistencia',
     'href': 'control_asistencia_reunion',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 5,
     'parent': 'acceso_reuniones'
     },
    # {'code_menu': 'acceso_actillas2',
    #  'texto_menu': 'Actillas',
    #  'href': 'actillas',
    #  'nivel': 2,
    #  'tipo': 'Accesible',
    #  'pos': 5,
    #  'parent': 'acceso_reuniones'
    #  }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'c_conv_template',
             'nombre': 'Tiene permiso para crear configuraciones de convocatorias',
             'menu': 'acceso_conv_template'
             },
            {'code_nombre': 'w_conv_template',
             'nombre': 'Tiene permiso para editar cualquier configuración de convocatorias de la entidad',
             'menu': 'acceso_conv_template'
             },
            {'code_nombre': 'd_conv_template',
             'nombre': 'Tiene permiso para borrar cualquier configuración de convocatorias de la entidad',
             'menu': 'acceso_conv_template'
             },
            {'code_nombre': 'r_conv_reunion',
             'nombre': 'Tiene permiso para ver cualquier convocatoria',
             'menu': 'acceso_conv_reunion'
             },
            {'code_nombre': 'c_conv_reunion',
             'nombre': 'Tiene permiso para crear convocatorias',
             'menu': 'acceso_conv_reunion'
             },
            {'code_nombre': 'w_conv_reunion',
             'nombre': 'Tiene permiso para editar las convocatorias de la entidad',
             'menu': 'acceso_conv_reunion'
             },
            {'code_nombre': 'd_conv_reunion',
             'nombre': 'Tiene permiso para borrar convocatorias',
             'menu': 'acceso_conv_reunion'
             },
            {'code_nombre': 'm_conv_reunion',
             'nombre': 'Tiene permiso para enviar por mail convocatorias',
             'menu': 'acceso_conv_reunion'
             },
            {'code_nombre': 'w_sus_actas_reunion',
             'nombre': 'Tiene permiso para redactar las actas de sus convocatorias',
             'menu': 'acceso_redactar_actas_reunion'
             },
            {'code_nombre': 'w_actas_subentidades_reunion',
             'nombre': 'Tiene permiso para redactar las actas de las subentidades a las que pertenece',
             'menu': 'acceso_redactar_actas_reunion'
             },
            {'code_nombre': 'w_cualquier_acta_reunion',
             'nombre': 'Tiene permiso para redactar cualquier acta de la entidad',
             'menu': 'acceso_redactar_actas_reunion'
             },
            {'code_nombre': 'mail_actas_reunion',
             'nombre': 'Tiene permiso para enviar por mail las actas',
             'menu': 'acceso_redactar_actas_reunion'
             },
            # {'code_nombre': 'r_actas_reunion',
            #  'nombre': 'Tiene permiso para ver cualquier acta',
            #  'menu': 'acceso_ver_actas_reunion'
            #  }
            ]
