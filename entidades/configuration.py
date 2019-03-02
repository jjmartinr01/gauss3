# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_acciones_usuarios1',
     'texto_menu': 'Acciones usuarios 1',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 2
     },
    {'code_menu': 'acceso_acciones_usuarios2',
     'texto_menu': 'Acciones usuarios 2',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 3
     },
    {'code_menu': 'acceso_gestion_entidad',
     'texto_menu': 'Gestión de la entidad',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    {'code_menu': 'acceso_datos_entidad',
     'texto_menu': 'Datos de la entidad',
     'href': 'datos_entidad',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_gestion_entidad'
     },
    {'code_menu': 'acceso_crear_usuarios',
     'texto_menu': 'Añadir un nuevo usuario',
     'href': 'add_usuario',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_gestion_entidad'
     },
    {'code_menu': 'acceso_getion_bajas',
     'texto_menu': 'Gestión de bajas',
     'href': 'bajas_usuarios',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_gestion_entidad'
     },
    {'code_menu': 'acceso_reserva_plazas',
     'texto_menu': 'Reserva de plazas',
     'href': 'reserva_plazas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_gestion_entidad'
     },
    {'code_menu': 'acceso_miembros_entidad',
     'texto_menu': 'Miembros de la entidad',
     'href': 'usuarios_entidad',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 5,
     'parent': 'acceso_gestion_entidad'
     },
    {'code_menu': 'acceso_listados_usuarios',
     'texto_menu': 'Listados de usuarios',
     'href': 'listados_usuarios',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 6,
     'parent': 'acceso_gestion_entidad'
     },
    {'code_menu': 'acceso_dependencias_entidad',
     'texto_menu': 'Dependencias',
     'href': 'dependencias_entidad',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 7,
     'parent': 'acceso_gestion_entidad'
     },
    {'code_menu': 'acceso_gestionar_rondas',
     'texto_menu': 'Gestión de rondas',
     'href': 'configura_rondas', #'rondas_entidad'
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 8,
     'parent': 'acceso_gestion_entidad'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'modifica_datos_entidad',
             'nombre': 'Tiene permiso para modificar los datos de la entidad',
             'menu': 'acceso_datos_entidad'
             },
            {'code_nombre': 'crea_dependencias',
             'nombre': 'Tiene permiso para crear nuevos espacios/dependencias de la entidad',
             'menu': 'acceso_datos_entidad'
             },
            {'code_nombre': 'borra_dependencias',
             'nombre': 'Tiene permiso para borrar espacios/dependencias de la entidad',
             'menu': 'acceso_datos_entidad'
             },
            {'code_nombre': 'crea_rondas',
             'nombre': 'Tiene permiso para crear una nueva ronda para la entidad',
             'menu': 'acceso_datos_entidad'
             },
            {'code_nombre': 'crea_usuarios',
             'nombre': 'Tiene permiso para crear añadir nuevos usuarios a la entidad',
             'menu': 'acceso_crear_usuarios'
             },
            {'code_nombre': 'alta_usuarios',
             'nombre': 'Tiene permiso para dar de alta a los usuarios de la entidad',
             'menu': 'acceso_getion_bajas'
             },
            {'code_nombre': 'baja_usuarios',
             'nombre': 'Tiene permiso para dar de baja a los usuarios de la entidad',
             'menu': 'acceso_getion_bajas'
             },
            {'code_nombre': 'borra_usuarios',
             'nombre': 'Tiene permiso para borrar definitivamente a los usuarios de la entidad',
             'menu': 'acceso_getion_bajas'
             },
            {'code_nombre': 'reserva_usuarios',
             'nombre': 'Tiene permiso para crear reservas de plaza para futuros usuarios',
             'menu': 'acceso_reserva_plazas'
             },
            {'code_nombre': 'recibe_aviso_reserva',
             'nombre': 'Recibe un aviso cuando se produce una nueva solicitud de reserva',
             'menu': 'acceso_reserva_plazas'
             },
            {'code_nombre': 'listado_usuarios',
             'nombre': 'Tiene permiso para crear listados de usuarios de la entidad',
             'menu': 'acceso_miembros_entidad'
             },
            {'code_nombre': 'modifica_datos_usuarios',
             'nombre': 'Tiene permiso para modificar los datos de los usuarios de la entidad',
             'menu': 'acceso_miembros_entidad'
             },
            {'code_nombre': 'accede_otras_rondas',
             'nombre': 'Tiene permiso para entrar en los datos de otras rondas de la entidad',
             'menu': 'acceso_gestionar_rondas'
             },
            {'code_nombre': 'crea_rondas',
             'nombre': 'Tiene permiso para crear rondas de la entidad',
             'menu': 'acceso_gestionar_rondas'
             },
            {'code_nombre': 'configura_auto_id',
             'nombre': 'Tiene permiso para configurar auto identificadores de la entidad',
             'menu': 'acceso_miembros_entidad'
             }
            ]

FILTROS = [
    {'q':'gauser__first_name__icontains', 'texto': 'El nombre contiene el texto ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'gauser__last_name__icontains', 'texto': 'Los apellidos contienen el texto ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'subentidades__in', 'texto': 'Pertenece a las Secciones/Departamentos ...', 'form': 'input', 'type': 'select', 'options': 'filtro.filtrado.propietario.entidad.subentidad_set.all', 'clases': ''},
    {'q':'cargos__in', 'texto': 'Tiene alguno de los Cargos/Perfiles ...', 'form': 'input', 'type': 'text', 'options': 'filtro.filtrado.propietario.entidad.cargo_set.all', 'clases': ''},
    {'q':'observaciones__icontains', 'texto': 'En las observaciones pone ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'ronda__id', 'texto': 'Ha sido usuario en el año ...', 'form': 'input', 'type': 'text', 'options': 'filtro.filtrado.propietario.entidad|rondas', 'clases': ''},
    {'q':'tutor1__gauser__first_name__icontains', 'texto': 'El nombre del primer tutor contiene el texto ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'tutor1__gauser__last_name__icontains', 'texto': 'Los apellidos del primer tutor contienen el texto ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'tutor2__gauser__first_name__icontains', 'texto': 'El nombre del segundo tutor contiene el texto ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'tutor2__gauser__last_name__icontains', 'texto': 'Los apellidos del segundo tutor contienen el texto ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'ocupacion__icontains', 'texto': 'La ocupación/profesión es ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'banco__in', 'texto': 'El banco con el que trabaja es ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'gauser__localidad__icontains', 'texto': 'La localidad donde reside es ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'gauser__provincia__icontains', 'texto': 'La provincia donde reside es ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'gauser__nacimiento__gt', 'texto': 'La fecha de nacimiento es posterior a ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'gauser__nacimiento__lt', 'texto': 'La fecha de nacimiento es anterior a ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''},
    {'q':'gauser_extra_estudios__grupo__nombre__icontains', 'texto': 'El nombre del grupo del usuario contiene ...', 'form': 'input', 'type': 'text', 'options': '', 'clases': ''}
]
