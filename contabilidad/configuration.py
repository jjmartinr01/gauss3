# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_gestion_economica',
     'texto_menu': 'Gestión económica',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_presupuestos',
     'texto_menu': 'Presupuestos',
     'href': 'presupuestos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_gestion_economica'
     },
    {'code_menu': 'acceso_gastos_ingresos',
     'texto_menu': 'Gastos-Ingresos',
     'href': 'gastos_ingresos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_gestion_economica'
     },
    {'code_menu': 'acceso_politica_cuotas',
     'texto_menu': 'Política de cuotas',
     'href': 'politica_cuotas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_gestion_economica'
     },
    {'code_menu': 'acceso_ordenes_adeudo',
     'texto_menu': 'Órdenes de adeudo',
     'href': 'ordenes_adeudo',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_gestion_economica'
     },
    {'code_menu': 'acceso_mis_ordenes_adeudo',
     'texto_menu': 'Firmar órdenes de adeudo',
     'href': 'mis_ordenes_adeudo',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_gestion_economica'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_presupuestos',
             'nombre': 'Tiene permiso para crear presupuestos',
             'menu': 'acceso_presupuestos'
             },
            {'code_nombre': 'edita_presupuestos',
             'nombre': 'Tiene permiso para editar un presupuesto de la entidad',
             'menu': 'acceso_presupuestos'
             },
            {'code_nombre': 'crea_partidas',
             'nombre': 'Tiene permiso para añadir partidas a los presupuestos',
             'menu': 'acceso_presupuestos'
             },
            {'code_nombre': 'genera_pdf_presupuesto',
             'nombre': 'Tiene permiso para generar pdf informativo de los presupuestos',
             'menu': 'acceso_presupuestos'
             },
            {'code_nombre': 'archiva_presupuestos',
             'nombre': 'Tiene permiso para archivar presupuestos',
             'menu': 'acceso_presupuestos'
             },
            {'code_nombre': 'desarchiva_presupuestos',
             'nombre': 'Tiene permiso para des-archivar presupuestos',
             'menu': 'acceso_presupuestos'
             },
            {'code_nombre': 'copia_presupuestos',
             'nombre': 'Tiene permiso para copiar presupuestos',
             'menu': 'acceso_presupuestos'
             },
            {'code_nombre': 'borra_presupuestos',
             'nombre': 'Tiene permiso para borrar presupuestos',
             'menu': 'acceso_presupuestos'
             },
            {'code_nombre': 'crea_gastos_ingresos',
             'nombre': 'Tiene permiso para añadir un gasto o ingreso a una partida',
             'menu': 'acceso_gastos_ingresos'
             },
            {'code_nombre': 'edita_gastos_ingresos',
             'nombre': 'Tiene permiso para editar un gasto o ingreso de una partida',
             'menu': 'acceso_gastos_ingresos'
             },
            {'code_nombre': 'borra_gastos_ingresos',
             'nombre': 'Tiene permiso para borrar un gasto o ingreso de una partida',
             'menu': 'acceso_gastos_ingresos'
             },
            {'code_nombre': 'pdf_gastos_ingresos',
             'nombre': 'Tiene permiso para crear un pdf de los gastos o ingresos',
             'menu': 'acceso_gastos_ingresos'
             },
            {'code_nombre': 'crea_politica_cuotas',
             'nombre': 'Tiene permiso para crear políticas de cuotas',
             'menu': 'acceso_politica_cuotas'
             },
            {'code_nombre': 'edita_politica_cuotas',
             'nombre': 'Tiene permiso para editar políticas de cuotas',
             'menu': 'acceso_politica_cuotas'
             },
            {'code_nombre': 'borra_politica_cuotas',
             'nombre': 'Tiene permiso para borrar políticas de cuotas',
             'menu': 'acceso_politica_cuotas'
             },
            {'code_nombre': 'crea_remesas',
             'nombre': 'Tiene permiso para crear remesas',
             'menu': 'acceso_politica_cuotas'
             }
            ]
