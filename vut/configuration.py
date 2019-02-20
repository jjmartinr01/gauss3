# -*- coding: utf-8 -*-
from __future__ import unicode_literals

TIPO = 'selectable'  # 'basic' or 'selectable'.  'basic': necesario para el funcionamiento del programa
#                           'selectable': No necesario. Añade nuevas funcionalidades al programa
# Por ejemplo autenticar es 'basic', pero actas es prescindible

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_vut',
     'texto_menu': 'Viviendas uso turístico',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1,
     },
    {'code_menu': 'acceso_viviendas',
     'texto_menu': 'Viviendas',
     'href': 'viviendas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 1,
     'parent': 'acceso_vut'
     },
    {'code_menu': 'acceso_reservas',
     'texto_menu': 'Reservas/Registro',
     'href': 'reservas_vut',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 2,
     'parent': 'acceso_vut'
     },
    {'code_menu': 'acceso_contabilidad_vut',
     'texto_menu': 'Contabilidad VUT',
     'href': 'contabilidad_vut',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 3,
     'parent': 'acceso_vut'
     },
    {'code_menu': 'acceso_domotica_vut',
     'texto_menu': 'Domótica VUT',
     'href': 'domotica_vut',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_vut'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [{'code_nombre': 'crea_viviendas',
             'nombre': 'Permiso para crear una vivienda para la entidad',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'borra_viviendas',
             'nombre': 'Permiso para borrar una vivienda de la entidad',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'edita_viviendas',
             'nombre': 'Permiso para editar los datos de una vivienda como propietario',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'crea_ayudantes',
             'nombre': 'Permiso para crear ayudantes para la gestión de la vut',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'edita_ayudantes',
             'nombre': 'Permiso para editar los datos de los ayudantes para la gestión de la vut',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'borra_ayudantes',
             'nombre': 'Permiso para borrar ayudantes creados para la gestión de la vut',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'comprueba_conexion_policia',
             'nombre': 'Permiso para comprobar la conexión con la policía',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'add_calendario_vut',
             'nombre': 'Permiso para añadir calendarios ical a una vut',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'edita_calendario_vut',
             'nombre': 'Permiso para editar los datos asociados a un calendario vut',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'delete_calendario_vut',
             'nombre': 'Permiso para borrar calendarios ical de una vut',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'add_autorizado_vut',
             'nombre': 'Permiso para añadir personas autorizadas a una vut',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'edita_autorizado_vut',
             'nombre': 'Permiso para editar los datos de una persona autorizada a una vut',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'delete_autorizado_vut',
             'nombre': 'Permiso para borrar personas autorizadas de una vut',
             'menu': 'acceso_viviendas'
             },
            {'code_nombre': 'autorizado_ver_reservas',
             'nombre': 'Permiso para ver reservas de una vivienda',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'crea_reservas',
             'nombre': 'Permiso para crear reservas para una vivienda',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'borra_reservas',
             'nombre': 'Permiso para borrar reservas de una vivienda',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'edita_reservas',
             'nombre': 'Permiso para editar las reservas de una vivienda',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'crea_pagos_ayudante',
             'nombre': 'Permiso para crear pagos para los ayudantes de gestión de la vut',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'edita_pagos_ayudante',
             'nombre': 'Permiso para editar pagos para los ayudantes de gestión de la vut',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'borra_pagos_ayudante',
             'nombre': 'Permiso para borrar pagos para los ayudantes de gestión de la vut',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'genera_libro_registro_policia',
             'nombre': 'Permiso para generar el libro de registros para la policía',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'autorizado_ver_viajeros',
             'nombre': 'Permiso para ver los viajeros de las reservas a las que está autorizado',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'recibe_errores_de_viajeros',
             'nombre': 'Recibe los mensajes con errores en el registro de viajeros',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'comunica_registro_policia',
             'nombre': 'Comunica a la policia el registro de viajeros',
             'menu': 'acceso_reservas'
             },
            {'code_nombre': 'crea_contabilidad_vut',
             'nombre': 'Permiso para crear registros de contabilidad para VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'borra_contabilidad_vut',
             'nombre': 'Permiso para borrar registros de contabilidad para VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'edita_contabilidad_vut',
             'nombre': 'Permiso para modificar registros de contabilidad para VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'crea_partida_vut',
             'nombre': 'Permiso para crear partidas de contabilidad para VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'borra_partida_vut',
             'nombre': 'Permiso para borrar partidas de contabilidad para VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'edita_partida_vut',
             'nombre': 'Permiso para modificar partidas de contabilidad para VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'crea_asiento_vut',
             'nombre': 'Permiso para crear asientos de contabilidad para VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'borra_asiento_vut',
             'nombre': 'Permiso para borrar asientos de contabilidad para VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'edita_asiento_vut',
             'nombre': 'Permiso para modificar asientos de contabilidad para VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'add_autorizado_contabilidad_vut',
             'nombre': 'Permiso para añadir personas autorizadas a gestionar una contabilidad VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'edita_autorizado_contabilidad_vut',
             'nombre': 'Permiso para editar los datos de una persona autorizada a gestionar una contabilidad VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'delete_autorizado_contabilidad_vut',
             'nombre': 'Permiso para borrar personas autorizadas a gestionar una contabilidad VUT',
             'menu': 'acceso_contabilidad_vut'
             },
            {'code_nombre': 'add_dispositivo_domotica',
             'nombre': 'Permiso para añadir dispositivos domóticos en viviendas autorizadas',
             'menu': 'acceso_domotica_vut'
             },
            {'code_nombre': 'delete_dispositivo_domotica',
             'nombre': 'Permiso para borrar dispositivos domóticos en viviendas autorizadas',
             'menu': 'acceso_domotica_vut'
             },
            {'code_nombre': 'edita_dispositivo_domotica',
             'nombre': 'Permiso para editar dispositivos domóticos en viviendas autorizadas',
             'menu': 'acceso_domotica_vut'
             },
            {'code_nombre': 'ver_dispositivo_domotica',
             'nombre': 'Permiso para ver dispositivos domóticos en viviendas autorizadas',
             'menu': 'acceso_domotica_vut'
             }
            ]
