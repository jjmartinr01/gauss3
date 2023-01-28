# -*- coding: utf-8 -*-
from __future__ import unicode_literals
TIPO = 'basic'  # 'basic' or 'selectable'.  'basic': necesario para el funcionamiento del programa
#                           'selectable': No necesario. Añade nuevas funcionalidades al programa
# Por ejemplo autenticar es 'basic', pero actas es prescindible

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_configuracion',
     'texto_menu': 'Configuración',
     'href': '', 'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_perfiles_permisos',
     'texto_menu': 'Establecer perfiles y permisos a usuarios',
     'href': 'perfiles_permisos',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_configuracion'
     },
    {'code_menu': 'acceso_gestionar_perfiles',
     'texto_menu': 'Crear Perfiles/Cargos/Organigrama',
     'href': 'organigrama',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_configuracion'
     },
    {'code_menu': 'acceso_carga_masiva',
     'texto_menu': 'Carga masiva',
     'href': 'carga_masiva',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_configuracion'
     },
    {'code_menu': 'acceso_gestionar_subentidades',
     'texto_menu': 'Departamentos/Secciones',
     'href': 'subentidades',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_configuracion'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'sube_archivo_csv',
             'nombre': 'Tiene permiso para subir archivos csv de carga masiva',
             'menu': 'acceso_carga_masiva'
             },
            {'code_nombre': 'carga_masiva_racima',
             'nombre': 'Tiene permiso para cargar usuarios a través de archivos obtenidos de Racima',
             'menu': 'acceso_carga_masiva'
             },
            {'code_nombre': 'asigna_perfiles',
             'nombre': 'Tiene permiso para asignar perfiles a los usuarios',
             'menu': 'acceso_perfiles_permisos'
             },
            {'code_nombre': 'asigna_permisos',
             'nombre': 'Tiene permiso para asignar permisos a los usuarios',
             'menu': 'acceso_perfiles_permisos'
             },
            {'code_nombre': 'crea_perfiles',
             'nombre': 'Tiene permiso para crear nuevos perfiles/cargos',
             'menu': 'acceso_gestionar_perfiles'
             },
            {'code_nombre': 'borra_perfiles',
             'nombre': 'Tiene permiso para borrar perfiles/cargos',
             'menu': 'acceso_gestionar_perfiles'
             },
            {'code_nombre': 'edita_perfiles',
             'nombre': 'Tiene permiso para editar perfiles/cargos',
             'menu': 'acceso_gestionar_perfiles'
             },
            {'code_nombre': 'crea_subentidades',
             'nombre': 'Tiene permiso para crear nuevos subentidades/secciones',
             'menu': 'acceso_gestionar_subentidades'
             },
            {'code_nombre': 'borra_subentidades',
             'nombre': 'Tiene permiso para borrar subentidades/secciones',
             'menu': 'acceso_gestionar_subentidades'
             },
            {'code_nombre': 'edita_subentidades',
             'nombre': 'Tiene permiso para editar subentidades/secciones',
             'menu': 'acceso_gestionar_subentidades'
             },
            {'code_nombre': 'modifica_texto_menu',
             'nombre': 'Tiene permiso para modificar el texto de los menús de la entidad',
             'menu': 'acceso_perfiles_permisos'
             },
            {'code_nombre': 'modifica_pos_menu',
             'nombre': 'Tiene permiso para modificar la posición de un menú de la entidad',
             'menu': 'acceso_perfiles_permisos'
             },
            {'code_nombre': 'carga_alumnos_centro_educativo',
             'nombre': 'Tiene permiso para cargar los alumnos de un centro educativo',
             'menu': 'acceso_carga_masiva'
             },
            {'code_nombre': 'carga_alumnos_centros_educativos',
             'nombre': 'Tiene permiso para cargar los alumnos de varios centros educativos a la vez',
             'menu': 'acceso_carga_masiva'
             },
            {'code_nombre': 'carga_personal_centro_educativo',
             'nombre': 'Tiene permiso para cargar al personal de un centro educativo',
             'menu': 'acceso_carga_masiva'
             },
            {'code_nombre': 'carga_personal_centros_educativos',
             'nombre': 'Tiene permiso para cargar al personal de varios centros educativos a la vez',
             'menu': 'acceso_carga_masiva'
             },
            {'code_nombre': 'carga_datos_centros_educativos',
             'nombre': 'Tiene permiso para cargar los datos de los centros educativos',
             'menu': 'acceso_carga_masiva'
             },
            {'code_nombre': 'carga_horario_personal_centro_educativo',
             'nombre': 'Tiene permiso para cargar los horarios del personal de su centro educativo',
             'menu': 'acceso_carga_masiva'
             },
            {'code_nombre': 'carga_horario_personal_centros_educativos',
             'nombre': 'Tiene permiso para cargar los horarios del personal de cualquier centro educativo',
             'menu': 'acceso_carga_masiva'
             },
            {'code_nombre': 'carga_plantilla_organica_casiopea',
             'nombre': 'Tiene permiso para cargar los datos de plantilla del servidor Casiopea',
             'menu': 'acceso_carga_masiva'
             }
            ]