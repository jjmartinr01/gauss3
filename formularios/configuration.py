# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_cuestionarios',
     'texto_menu': 'Cuestionarios',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_formularios',
     'texto_menu': 'Diseñar y Crear',
     'href': 'formularios',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_cuestionarios'
     },
    {'code_menu': 'acceso_mis_formularios',
     'texto_menu': 'Mis Formularios',
     'href': 'mis_formularios',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_cuestionarios'
     },
    {'code_menu': 'acceso_formularios_disponibles',
     'texto_menu': 'Formularios Disponibles',
     'href': 'formularios_disponibles',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_cuestionarios'
     },
    {'code_menu': 'acceso_funcionarios_practicas',
     'texto_menu': 'Funcionarios en prácticas',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_procesos_evalpract',
     'texto_menu': 'Procesos de Evaluación',
     'href': 'procesos_evaluacion_funcpract',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_funcionarios_practicas'
     },
    {'code_menu': 'acceso_mis_evalpract',
     'texto_menu': 'Mis evaluaciones',
     'href': 'mis_evalpract',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_funcionarios_practicas'
     },
    {'code_menu': 'acceso_evaluacion_funcpract',
     'texto_menu': 'Cuestionarios evaluación',
     'href': 'evaluacion_funcpract',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_funcionarios_practicas'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_formularios',
             'nombre': 'Tiene permiso para crear formularios para la entidad',
             'menu': 'acceso_formularios'
             },
            {'code_nombre': 'copia_formularios',
             'nombre': 'Tiene permiso para copiar otros formularios para la entidad',
             'menu': 'acceso_formularios'
             },
            {'code_nombre': 'borra_formularios',
             'nombre': 'Tiene permiso para borrar formularios de la entidad',
             'menu': 'acceso_formularios'
             },
            {'code_nombre': 've_todas_efpas',
             'nombre': 'Tiene permiso para ver todas las evaluaciones de funcionarios en prácticas',
             'menu': 'acceso_funcionarios_practicas'
             },
            {'code_nombre': 'borra_pefps',
             'nombre': 'Tiene permiso para borrar cualquier proceso de evaluación de funcionarios en prácticas',
             'menu': 'acceso_procesos_evalpract'
             },
            {'code_nombre': 'crea_evaluacion_funcpract',
             'nombre': 'Tiene permiso para crear cuestionarios de evaluación de funcionarios en prácticas',
             'menu': 'acceso_evaluacion_funcpract'
             },
            {'code_nombre': 'borra_efps',
             'nombre': 'Tiene permiso para borrar cualquier cuestionario de evaluación de funcionarios en prácticas',
             'menu': 'acceso_evaluacion_funcpract'
             }
            ]
