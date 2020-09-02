# -*- coding: utf-8 -*-

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_inspeccion_educativa',
     'texto_menu': 'Inspección Educativa',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_tareas_ie',
     'texto_menu': 'Tareas de Inspección',
     'href': 'tareas_ie',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_inspeccion_educativa'
     },
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_tareas_ie',
             'nombre': 'Tiene permiso para crear tareas de Inspección Educativa',
             'menu': 'acceso_inspeccion_educativa'
             },
            {'code_nombre': 'edita_tareas_ie',
             'nombre': 'Tiene permiso para editar tareas propias de Inspección Educativa',
             'menu': 'acceso_inspeccion_educativa'
             },
            {'code_nombre': 'copia_tareas_ie',
             'nombre': 'Tiene permiso para copiar tareas propias de Inspección Educativa',
             'menu': 'acceso_inspeccion_educativa'
             },
            {'code_nombre': 'borra_tareas_ie',
             'nombre': 'Tiene permiso para borrar tareas propias de Inspección Educativa',
             'menu': 'acceso_inspeccion_educativa'
             },
            {'code_nombre': 've_cualquier_tarea_ie',
             'nombre': 'Tiene permiso para ver cualquier tarea de Inspección Educativa',
             'menu': 'acceso_inspeccion_educativa'
             },
            {'code_nombre': 'edita_cualquier_tarea_ie',
             'nombre': 'Tiene permiso para editar cualquier tarea de Inspección Educativa',
             'menu': 'acceso_inspeccion_educativa'
             },
            {'code_nombre': 'copia_cualquier_tarea_ie',
             'nombre': 'Tiene permiso para copiar cualquier tarea de Inspección Educativa',
             'menu': 'acceso_inspeccion_educativa'
             },
            {'code_nombre': 'borra_cualquier_tarea_ie',
             'nombre': 'Tiene permiso para borrar cualquier tarea de Inspección Educativa',
             'menu': 'acceso_inspeccion_educativa'
             },
            ]
