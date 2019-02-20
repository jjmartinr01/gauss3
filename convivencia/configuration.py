# -*- coding: utf-8 -*-
from __future__ import unicode_literals

TIPO = 'selectable'  # 'basic' or 'selectable'.  'basic': necesario para el funcionamiento del programa
#                           'selectable': No necesario. Añade nuevas funcionalidades al programa
# Por ejemplo autenticar es 'basic', pero actas es prescindible

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_convivencia',
     'texto_menu': 'Convivencia',
     'href': '', 'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_gestionar_conductas',
     'texto_menu': 'Establecer conductas y sanciones',
     'href': 'gestionar_conductas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_convivencia'
     },
    {'code_menu': 'acceso_sancionar_conductas',
     'texto_menu': 'Sancionar conductas',
     'href': 'sancionar_conductas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_convivencia'
     },
    {'code_menu': 'acceso_expediente_sancionador',
     'texto_menu': 'Expediente sancionador',
     'href': 'expediente_sancionador',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_convivencia'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'sancionar_nivel_docente',
             'nombre': 'Tiene permiso para sancionar como docente',
             'menu': 'acceso_sancionar_conductas'
             },
            {'code_nombre': 'sancionar_nivel_tutor',
             'nombre': 'Tiene permiso para sancionar como tutor',
             'menu': 'acceso_sancionar_conductas'
             },
            {'code_nombre': 'sancionar_nivel_jefe_estudios',
             'nombre': 'Tiene permiso para sancionar como jefe de estudios',
             'menu': 'acceso_sancionar_conductas'
             },
            {'code_nombre': 'sancionar_nivel_director',
             'nombre': 'Tiene permiso para sancionar como director',
             'menu': 'acceso_sancionar_conductas'
             },
            {'code_nombre': 'aplica_cualquier_sancion',
             'nombre': 'Tiene permiso para aplicar cualquier sanción',
             'menu': 'acceso_sancionar_conductas'
             },
            {'code_nombre': 'borra_sanciones_tipificadas',
             'nombre': 'Tiene permiso para borrar sanciones tipificadas en la entidad',
             'menu': 'acceso_sancionar_conductas'
             },
            {'code_nombre': 'borra_conductas_tipificadas',
             'nombre': 'Tiene permiso para borrar conductas tipificadas en la entidad',
             'menu': 'acceso_sancionar_conductas'
             },
            {'code_nombre': 'edita_sanciones_tipificadas',
             'nombre': 'Tiene permiso para editar sanciones tipificadas en la entidad',
             'menu': 'acceso_gestionar_conductas'
             },
            {'code_nombre': 'edita_conductas_tipificadas',
             'nombre': 'Tiene permiso para editar conductas tipificadas en la entidad',
             'menu': 'acceso_gestionar_conductas'
             },
            {'code_nombre': 'genera_informe_sancionador',
             'nombre': 'Tiene permiso para generar informes sancionadores',
             'menu': 'acceso_sancionar_conductas'
             },
            {'code_nombre': 'elige_sancionador',
             'nombre': 'Tiene permiso para sancionar en nombre de otro docente',
             'menu': 'acceso_sancionar_conductas'
             },
            {'code_nombre': 'borra_informes_sancionadores',
             'nombre': 'Borra informes sancionadores creados por otros en la entidad',
             'menu': 'acceso_sancionar_conductas'
             },
            {'code_nombre': 'recibe_mensajes_aviso_informes_sancionadores',
             'nombre': 'Recibe mensajes cada vez que un alumno es sancionado',
             'menu': 'acceso_sancionar_conductas'
             },
            ]
