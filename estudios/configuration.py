# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_estudios_centro_educativo',
     'texto_menu': 'Configuración de estudios',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_configura_cursos',
     'texto_menu': 'Configuración de cursos',
     'href': 'configura_cursos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_estudios_centro_educativo'
     },
    {'code_menu': 'acceso_configura_grupos',
     'texto_menu': 'Configuración de grupos',
     'href': 'configura_grupos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_estudios_centro_educativo'
     },
    {'code_menu': 'acceso_evaluar_materias',
     'texto_menu': 'Evaluación de materias',
     'href': 'evaluar_materias',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_acciones_usuarios1'
     },
    {'code_menu': 'acceso_configura_pendientes',
     'texto_menu': 'Configurar materias pendientes',
     'href': 'configura_materias_pendientes',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_estudios_centro_educativo'
     }
]

# Se añaden otros permisos para el usuario

PERMISOS = [
    {'code_nombre': 'crea_cursos',
     'nombre': 'Tiene permiso para crear cursos en la entidad',
     'menu': 'acceso_configura_cursos'
     },
    {'code_nombre': 'borra_cursos',
     'nombre': 'Tiene permiso para borrar cursos de la entidad',
     'menu': 'acceso_configura_cursos'
     },
    {'code_nombre': 'crea_grupos',
     'nombre': 'Tiene permiso para crear grupos en la entidad',
     'menu': 'acceso_configura_grupos'
     },
    {'code_nombre': 'borra_grupos',
     'nombre': 'Tiene permiso para borrar grupos de la entidad',
     'menu': 'acceso_configura_grupos'
     },
    # {'code_nombre': 'crea_materias',
    #  'nombre': 'Tiene permiso para crear materias en la entidad',
    #  'menu': 'acceso_define_materiasSSSSSSSSSSSSSSSSSSSSSSSSSS'
    #  },
    # {'code_nombre': 'borra_materias',
    #  'nombre': 'Tiene permiso para borrar materias de la entidad',
    #  'menu': 'acceso_define_materiasSSSSSSSSSSSSSSSSSSSSSSSSSS'
    #  },
    {'code_nombre': 'evalua_materias_asignadas',
     'nombre': 'Tiene permiso para evaluar las materias asignadas como evaluador',
     'menu': 'acceso_evaluar_materias'
     },
    {'code_nombre': 'evalua_cualquier_materia',
     'nombre': 'Tiene permiso para evaluar cualquier materia',
     'menu': 'acceso_evaluar_materias'
     }
    #             {'code_nombre': 'edita_programaciones_ccff',
    #              'nombre': 'Tiene permiso para editar cualquier programación de CCFF',
    #              'menu': 'acceso_programaciones_ccff'
    #              },
    #             {'code_nombre': 'copia_programaciones_ccff',
    #              'nombre': 'Tiene permiso para copiar cualquier programación de CCFF',
    #              'menu': 'acceso_programaciones_ccff'
    #              },
    #             {'code_nombre': 'crea_resultados_aprendizaje_ccff',
    #              'nombre': 'Tiene permiso para crear resultados de aprendizaje asociados a un Ciclo Formativo',
    #              'menu': 'acceso_resultados_aprendizaje'
    #              },
    #             {'code_nombre': 'borra_resultados_aprendizaje_ccff',
    #              'nombre': 'Tiene permiso para borrar resultados de aprendizaje asociados a un Ciclo Formativo',
    #              'menu': 'acceso_resultados_aprendizaje'
    #              },
    #             {'code_nombre': 'crea_objetivos_ccff',
    #              'nombre': 'Pued crear objetivos y criterios de evaluación asociados a un resultado de aprendizaje',
    #              'menu': 'acceso_resultados_aprendizaje'
    #              },
    #             {'code_nombre': 'borra_objetivos_ccff',
    #              'nombre': 'Puede borrar objetivos y criterios de evaluación asociados a un resultado de aprendizaje',
    #              'menu': 'acceso_resultados_aprendizaje'
    #              }
]
