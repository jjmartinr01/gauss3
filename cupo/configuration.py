# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_cupos',
     'texto_menu': 'Plantilla/Cupo docentes',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_cupo_profesorado',
     'texto_menu': 'Cupo profesorado',
     'href': 'cupo',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_cupos'
     },
    {'code_menu': 'acceso_plantilla_organica',
     'texto_menu': 'Plantillas Orgánicas',
     'href': 'plantilla_organica',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_cupos'
     },
    {'code_menu': 'acceso_rrhh_cupos',
     'texto_menu': 'Cupos RRHH',
     'href': 'rrhh_cupos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_cupos'
     },
    {'code_menu': 'acceso_estadistica_cupos',
     'texto_menu': 'Estadística cupos',
     'href': 'estadistica_cupos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_cupos'
     }
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
             },
            {'code_nombre': 'carga_plantillas_por_funciones',
             'nombre': 'Tiene permiso para ejecutar la carga de una plantilla por partes',
             'menu': 'acceso_plantilla_organica'
             },
            {'code_nombre': 'carga_datos_casiopea',
             'nombre': 'Tiene permiso para cargar datos de Casiopea',
             'menu': 'acceso_plantilla_organica'
             },
            {'code_nombre': 'carga_plantillas_organicas',
             'nombre': 'Tiene permiso para cargar plantillas orgánicas desde Plantillas/Cupo',
             'menu': 'acceso_plantilla_organica'
             },
            {'code_nombre': 'publica_cupo_para_rrhh',
             'nombre': 'Tiene permiso para publicar el cupo y que sea leído en forma de csv por RRHH',
             'menu': 'acceso_cupo_profesorado'
             },
            {'code_nombre': 'cambia_ronda_cupos',
             'nombre': 'Tiene permiso para cambiar la ronda a los cupos que tiene acceso',
             'menu': 'acceso_cupo_profesorado'
             }
            ]
