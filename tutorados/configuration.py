# -*- coding: utf-8 -*-
from __future__ import unicode_literals

TIPO = 'selectable'  # 'basic' or 'selectable'.  'basic': necesario para el funcionamiento del programa
#                           'selectable': No necesario. Añade nuevas funcionalidades al programa
# Por ejemplo autenticar es 'basic', pero actas es prescindible

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_informes_usuarios',
     'texto_menu': 'Informes',
     'href': '', 'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_informes_seguimiento',
     'texto_menu': 'Informe de seguimiento',
     'href': 'informes_seguimiento',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_informes_usuarios'
     },
    # {'code_menu': 'acceso_generar_actillas',
    #  'texto_menu': 'Actillas',
    #  'href': 'generar_actillas',
    #  'nivel': 2,
    #  'tipo': 'Accesible',
    #  'pos': 2,
    #  'parent': 'acceso_informes_usuarios'
    #  },
    {'code_menu': 'acceso_informes_tareas',
     'texto_menu': 'Informe con tareas',
     'href': 'informes_tareas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_informes_usuarios'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'solicita_informes_seguimiento',
             'nombre': 'Tiene permiso para solicitar informes de seguimiento de los usuarios de la entidad',
             'menu': 'acceso_informes_seguimiento'
             },
            {'code_nombre': 'borra_informes_seguimiento',
             'nombre': 'Tiene permiso para borrar informes de seguimiento de los usuarios de la entidad',
             'menu': 'acceso_informes_seguimiento'
             },
            {'code_nombre': 'edita_informes_seguimiento',
             'nombre': 'Tiene permiso para editar informes de seguimiento de los usuarios de la entidad',
             'menu': 'acceso_informes_seguimiento'
             },
            {'code_nombre': 've_informes_seguimiento',
             'nombre': 'Tiene permiso para ver informes de seguimiento de los usuarios de la entidad',
             'menu': 'acceso_informes_seguimiento'
             },
            {'code_nombre': 'borra_preguntas_informes_seguimiento',
             'nombre': 'Tiene permiso para borrar preguntas de los informes de seguimiento de la entidad',
             'menu': 'acceso_informes_seguimiento'
             },
            # {'code_nombre': 'genera_actillas_grupos_usuarios',
            #  'nombre': 'Tiene permiso para sancionar como director',
            #  'menu': 'acceso_sancionar_conductas'
            #  },
            {'code_nombre': 'solicita_informes_tareas',
             'nombre': 'Tiene permiso para solicitar informes con tareas de los usuarios de la entidad',
             'menu': 'acceso_informes_tareas'
             },
            {'code_nombre': 'borra_informes_tareas',
             'nombre': 'Tiene permiso para borrar informes con tareas de los usuarios de la entidad',
             'menu': 'acceso_informes_tareas'
             },
            {'code_nombre': 'edita_informes_tareas',
             'nombre': 'Tiene permiso para editar informes con tareas de los usuarios de la entidad',
             'menu': 'acceso_informes_tareas'
             },
            {'code_nombre': 've_informes_tareas',
             'nombre': 'Tiene permiso para ver informes con tareas de los usuarios de la entidad',
             'menu': 'acceso_informes_tareas'
             }
            ]
