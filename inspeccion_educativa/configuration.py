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
    {'code_menu': 'acceso_informes_ie',
     'texto_menu': 'Informes de Inspección',
     'href': 'informes_ie',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_inspeccion_educativa'
     },
    {'code_menu': 'acceso_plantillas_informes_ie',
     'texto_menu': 'Plantillas de Informes',
     'href': 'plantillas_ie',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_inspeccion_educativa'
     },
    {'code_menu': 'acceso_asignar_centros_inspeccion',
     'texto_menu': 'Asignación de centros',
     'href': 'asignar_centros_inspeccion',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_inspeccion_educativa'
     },
    {'code_menu': 'acceso_carga_masiva_inspeccion',
     'texto_menu': 'Carga masiva de archivos',
     'href': 'carga_masiva_inspeccion',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 5,
     'parent': 'acceso_inspeccion_educativa'
     },
    {'code_menu': 'acceso_actas_firmadas',
     'texto_menu': 'Actas de evaluación',
     'href': 'actas_firmadas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 6,
     'parent': 'acceso_inspeccion_educativa'
     },
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_tareas_ie',
             'nombre': 'Tiene permiso para crear tareas de Inspección Educativa',
             'menu': 'acceso_tareas_ie'
             },
            {'code_nombre': 'edita_tareas_ie',
             'nombre': 'Tiene permiso para editar tareas de Inspección Educativa',
             'menu': 'acceso_tareas_ie'
             },
            {'code_nombre': 'copia_tareas_ie',
             'nombre': 'Tiene permiso para copiar tareas de Inspección Educativa',
             'menu': 'acceso_tareas_ie'
             },
            {'code_nombre': 'borra_tareas_ie',
             'nombre': 'Tiene permiso para borrar tareas de Inspección Educativa',
             'menu': 'acceso_tareas_ie'
             },
            {'code_nombre': 've_cualquier_tarea_ie',
             'nombre': 'Tiene permiso para ver cualquier tarea de Inspección Educativa',
             'menu': 'acceso_tareas_ie'
             },
            {'code_nombre': 'edita_cualquier_tarea_ie',
             'nombre': 'Tiene permiso para editar cualquier tarea de Inspección Educativa',
             'menu': 'acceso_tareas_ie'
             },
            {'code_nombre': 'copia_cualquier_tarea_ie',
             'nombre': 'Tiene permiso para copiar cualquier tarea de Inspección Educativa',
             'menu': 'acceso_tareas_ie'
             },
            {'code_nombre': 'borra_cualquier_tarea_ie',
             'nombre': 'Tiene permiso para borrar cualquier tarea de Inspección Educativa',
             'menu': 'acceso_tareas_ie'
             },
            {'code_nombre': 'genera_informe_tareas_ie',
             'nombre': 'Tiene permiso para generar un informe de tareas de Inspección Educativa',
             'menu': 'acceso_tareas_ie'
             },
            {'code_nombre': 'genera_informe_tareas_ie_general',
             'nombre': 'Tiene permiso para generar un informe de las tareas de todos los inspectores',
             'menu': 'acceso_tareas_ie'
             },
            {'code_nombre': 'crea_informes_ie',
             'nombre': 'Tiene permiso para crear informes de Inspección Educativa',
             'menu': 'acceso_informes_ie'
             },
            {'code_nombre': 'edita_informes_ie',
             'nombre': 'Tiene permiso para editar informes de Inspección Educativa',
             'menu': 'acceso_informes_ie'
             },
            {'code_nombre': 'copia_informes_ie',
             'nombre': 'Tiene permiso para copiar informes de Inspección Educativa',
             'menu': 'acceso_informes_ie'
             },
            {'code_nombre': 'borra_informes_ie',
             'nombre': 'Tiene permiso para borrar informes de Inspección Educativa',
             'menu': 'acceso_informes_ie'
             },
            {'code_nombre': 'carga_datos_centros',
             'nombre': 'Tiene permiso para cargar archivo "Datos de los centros"',
             'menu': 'acceso_carga_masiva_inspeccion'
             },
            {'code_nombre': 'sube_actas_evaluacion',
             'nombre': 'Tiene permiso para subir actas de evaluación',
             'menu': 'acceso_actas_firmadas'
             },
            {'code_nombre': 'descarga_actas_evaluacion',
             'nombre': 'Tiene permiso para descargar actas de evaluación',
             'menu': 'acceso_actas_firmadas'
             },
            ]
