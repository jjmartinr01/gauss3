# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_lopd',
     'texto_menu': 'Protencción de datos',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_documento_seguridad',
     'texto_menu': 'Documento de seguridad',
     'href': 'documento_seguridad',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_lopd'
     },
    {'code_menu': 'acceso_responsables_lopd',
     'texto_menu': 'Responsables LOPD',
     'href': 'responsables_lopd',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_lopd'
     },
    {'code_menu': 'acceso_derechos_arco',
     'texto_menu': 'Derechos ARCO',
     'href': 'derechos_arco',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_lopd'
     },
    {'code_menu': 'acceso_incidencias_lopd',
     'texto_menu': 'Incidencias LOPD',
     'href': 'incidencias_lopd',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_lopd'
     },
    {'code_menu': 'acceso_contratos_confidencialidad',
     'texto_menu': 'Contratos y confidencialidad',
     'href': 'confidencialidad',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 5,
     'parent': 'acceso_lopd'
     },
    {'code_menu': 'acceso_inventario_soportes',
     'texto_menu': 'Inventario de soportes',
     'href': 'inventario_soportes',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 6,
     'parent': 'acceso_lopd'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'modifica_responsables_lopd',
             'nombre': 'Tiene permiso para modificar los responsables LOPD de la entidad',
             'menu': 'acceso_responsables_lopd'
             },
            {'code_nombre': 'resuelve_incidencias_LOPD',
             'nombre': 'Tiene permiso para resolver las incidencias LOPD de la entidad',
             'menu': 'acceso_incidencias_lopd'
             },
            {'code_nombre': 'modifica_confidencialidad_tratamiento',
             'nombre': 'Tiene permiso para modificar contrato de confidencialidad en el tratamiento',
             'menu': 'acceso_contratos_confidencialidad'
             },
            {'code_nombre': 'modifica_proteccion_tratamiento',
             'nombre': 'Tiene permiso para modificar contrato de protección de datos en el tratamiento',
             'menu': 'acceso_contratos_confidencialidad'
             },
            {'code_nombre': 'modifica_confidencialidad_acceso',
             'nombre': 'Tiene permiso para modificar contrato de confidencialidad en el acceso',
             'menu': 'acceso_contratos_confidencialidad'
             },
            {'code_nombre': 'modifica_proteccion_acceso',
             'nombre': 'Tiene permiso para modificar contrato de protección de datos en el acceso',
             'menu': 'acceso_contratos_confidencialidad'
             },
            {'code_nombre': 'crea_inventario_soporte',
             'nombre': 'Tiene permiso para crear nuevos soportes en el inventario LOPD',
             'menu': 'acceso_inventario_soportes'
             },
            {'code_nombre': 'borra_inventario_soporte',
             'nombre': 'Tiene permiso para borrar soportes en el inventario LOPD',
             'menu': 'acceso_inventario_soportes'
             }
            ]
