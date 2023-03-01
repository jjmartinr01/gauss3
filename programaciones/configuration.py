# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_programaciones_didacticas',
     'texto_menu': 'Programación General Anual',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_programaciones_ccff',
     'texto_menu': 'Programaciones CCFF',
     'href': 'programaciones',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_cargar_programaciones',
     'texto_menu': 'Cargar programaciones',
     'href': 'cargar_programaciones',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_resultados_aprendizaje',
     'texto_menu': 'Resultados de aprendizaje',
     'href': 'objetivos_criterios',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_cuerpos_funcionarios',
     'texto_menu': 'Cuerpos de funcionarios',
     'href': 'cuerpos_funcionarios_entidad',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_departamentos_centro_educativo',
     'texto_menu': 'Departamentos del centro',
     'href': 'departamentos_centro_educativo',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 5,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_profesores_centro_educativo',
     'texto_menu': 'Profesores del centro',
     'href': 'profesores_centro_educativo',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 6,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_aspectos_pga',
     'texto_menu': 'Aspectos generales de la PGA',
     'href': 'aspectos_pga',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 7,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_pec',
     'texto_menu': 'Proyecto Educativo del Centro',
     'href': 'proyecto_educativo_centro',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 8,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_progsecundaria',
     'texto_menu': 'Programaciones secundaria',
     'href': 'progsecundaria',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 9,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_cuaderno_docente',
     'texto_menu': 'Cuadernos docentes',
     'href': 'cuadernodocente',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 10,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_repositorio_sap',
     'texto_menu': 'Situaciones de Aprendizaje',
     'href': 'repositorio_sap',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 11,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_repositorio_instrumento',
     'texto_menu': 'Banco instrumentos',
     'href': 'repoescalacp',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 12,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_calificaciones_competencias_clave',
     'texto_menu': 'Calificaciones CC',
     'href': 'calificacc',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 13,
     'parent': 'acceso_programaciones_didacticas'
     },
    {'code_menu': 'acceso_estadistica_programaciones',
     'texto_menu': 'Estadística Programaciones',
     'href': 'estadistica_prog',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 13,
     'parent': 'acceso_programaciones_didacticas'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_programaciones_ccff',
             'nombre': 'Tiene permiso para crear programaciones de CCFF',
             'menu': 'acceso_programaciones_ccff'
             },
            {'code_nombre': 'edita_programaciones_ccff',
             'nombre': 'Tiene permiso para editar cualquier programación de CCFF',
             'menu': 'acceso_programaciones_ccff'
             },
            {'code_nombre': 'copia_programaciones_ccff',
             'nombre': 'Tiene permiso para copiar cualquier programación de CCFF',
             'menu': 'acceso_programaciones_ccff'
             },
            {'code_nombre': 'borra_programaciones_ccff',
             'nombre': 'Tiene permiso para borrar cualquier programación de CCFF',
             'menu': 'acceso_programaciones_ccff'
             },
            {'code_nombre': 'crea_resultados_aprendizaje_ccff',
             'nombre': 'Tiene permiso para crear resultados de aprendizaje asociados a un Ciclo Formativo',
             'menu': 'acceso_resultados_aprendizaje'
             },
            {'code_nombre': 'borra_resultados_aprendizaje_ccff',
             'nombre': 'Tiene permiso para borrar resultados de aprendizaje asociados a un Ciclo Formativo',
             'menu': 'acceso_resultados_aprendizaje'
             },
            {'code_nombre': 'crea_objetivos_ccff',
             'nombre': 'Pued crear objetivos y criterios de evaluación asociados a un resultado de aprendizaje',
             'menu': 'acceso_resultados_aprendizaje'
             },
            {'code_nombre': 'borra_objetivos_ccff',
             'nombre': 'Puede borrar objetivos y criterios de evaluación asociados a un resultado de aprendizaje',
             'menu': 'acceso_resultados_aprendizaje'
             },
            {'code_nombre': 'borra_departamentos',
             'nombre': 'Puede borrar departamentos del centro educativo',
             'menu': 'acceso_departamentos_centro_educativo'
             },
            {'code_nombre': 'recarga_departamentos',
             'nombre': 'Puede recargar todos los departamentos posibles para el centro educativo',
             'menu': 'acceso_departamentos_centro_educativo'
             },
            {'code_nombre': 'add_miembros_departamento',
             'nombre': 'Puede añadir usuarios al departamento del centro educativo',
             'menu': 'acceso_departamentos_centro_educativo'
             },
            {'code_nombre': 'carga_programaciones',
             'nombre': 'Puede cargar programaciones del centro educativo',
             'menu': 'acceso_cargar_programaciones'
             },
            {'code_nombre': 'borra_programaciones_cargadas',
             'nombre': 'Puede borrar programaciones del centro educativo',
             'menu': 'acceso_cargar_programaciones'
             },
            {'code_nombre': 'descarga_programaciones',
             'nombre': 'Puede descargar programaciones del centro educativo',
             'menu': 'acceso_cargar_programaciones'
             },
            {'code_nombre': 'descarga_pga',
             'nombre': 'Puede descargar la programación general anual del centro educativo',
             'menu': 'acceso_cargar_programaciones'
             },
            {'code_nombre': 've_todas_programaciones',
             'nombre': 'Puede ver todas las programaciones del centro',
             'menu': 'acceso_progsecundaria'
             },
            {'code_nombre': 'crea_programaciones',
             'nombre': 'Puede crear programaciones en el centro',
             'menu': 'acceso_progsecundaria'
             },
            {'code_nombre': 'borra_instrumento_repositorio',
             'nombre': 'Puede borrar cualquier instrumento de evaluación del repositorio',
             'menu': 'acceso_repositorio_instrumento'
             }
            ]
