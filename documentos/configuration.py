# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_gestion_documental',
     'texto_menu': 'Gestión documental',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_documentos',
     'texto_menu': 'Documentos',
     'href': 'documentos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_gestion_documental'
     },
    {'code_menu': 'acceso_contrato_gauss',
     'texto_menu': 'Contrato GAUSS',
     'href': 'contrato_gauss',
     'nivel': 2,
     'tipo': 'Restringido',
     'pos': 2,
     'parent': 'acceso_gestion_documental'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_carpetas',
             'nombre': 'Tiene permiso para crear carpetas',
             'menu': 'acceso_documentos'
             },
            {'code_nombre': 'edita_carpetas',
             'nombre': 'Tiene permiso para editar cualquier carpeta',
             'menu': 'acceso_documentos'
             },
            {'code_nombre': 'sube_archivos',
             'nombre': 'Tiene permiso para subir archivos',
             'menu': 'acceso_documentos'
             },
            {'code_nombre': 've_todas_carpetas',
             'nombre': 'Tiene permiso para ver todas las carpetas de la entidad',
             'menu': 'acceso_documentos'
             },
            {'code_nombre': 'edita_todos_archivos',
             'nombre': 'Tiene permiso para editar cualquier archivo',
             'menu': 'acceso_documentos'
             },
            {'code_nombre': 'borra_cualquier_archivo',
             'nombre': 'Tiene permiso para borrar cualquier archivo',
             'menu': 'acceso_documentos'
             },
            {'code_nombre': 'borra_cualquier_carpeta',
             'nombre': 'Tiene permiso para borrar cualquier carpeta',
             'menu': 'acceso_documentos'
             },
            {'code_nombre': 'edita_contrato_gauss',
             'nombre': 'Tiene permiso para editar el contrato de GAUSS',
             'menu': 'acceso_contrato_gauss'
             },
            {'code_nombre': 'pdf_contrato_gauss',
             'nombre': 'Tiene permiso para crear pdf del contrato de GAUSS',
             'menu': 'acceso_contrato_gauss'
             },
            {'code_nombre': 'edita_contrato_gauss',
             'nombre': 'Tiene permiso para editar el contrato de GAUSS',
             'menu': 'acceso_contrato_gauss'
             },
            {'code_nombre': 'sube_contrato_gauss',
             'nombre': 'Tiene permiso para subir el contrato escaneado de GAUSS',
             'menu': 'acceso_contrato_gauss'
             },
            {'code_nombre': 'descarga_contrato_gauss',
             'nombre': 'Tiene permiso para descargar el contrato escaneado de GAUSS',
             'menu': 'acceso_contrato_gauss'
             }
            ]
