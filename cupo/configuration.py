# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_cupos',
     'texto_menu': 'Cupos de la entidad',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_cupo_profesorado',
     'texto_menu': 'Cupo de profesores',
     'href': 'cupo',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_cupos'
     },
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_cupos',
             'nombre': 'Tiene permiso para crear cupos',
             'menu': 'acceso_cupo_profesorado'
             },
            {'code_nombre': 'edita_cupos',
             'nombre': 'Tiene permiso para editar un cupo de la entidad',
             'menu': 'acceso_cupo_profesorado'
             },
            {'code_nombre': 'copia_cupo_profesorado',
             'nombre': 'Tiene permiso para copiar un cupo de la entidad',
             'menu': 'acceso_cupo_profesorado'
             },
            {'code_nombre': 'borra_cupo_profesorado',
             'nombre': 'Tiene permiso para borrar un cupo de la entidad',
             'menu': 'acceso_cupo_profesorado'
             },
            {'code_nombre': 'crea_materias_cupo',
             'nombre': 'Tiene permiso para crear/borrar materias en el cupo',
             'menu': 'acceso_cupo_profesorado'
             },
            {'code_nombre': 'pdf_cupo',
             'nombre': 'Tiene permiso para crear un informe pdf del cupo',
             'menu': 'acceso_cupo_profesorado'
             },
            {'code_nombre': 'bloquea_cupos',
             'nombre': 'Tiene permiso para bloquear y desbloquear un cupo',
             'menu': 'acceso_cupo_profesorado'
             }
            ]
