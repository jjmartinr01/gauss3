# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# El code_menu debe ser único y se configurará como un permiso del sistema
MENU_DEFAULT = [
    {'code_menu': 'acceso_horarios',
     'texto_menu': 'Horarios',
     'href': '',
     'nivel': 1,
     'tipo': 'Accesible',
     'pos': 1
     },
    # {'code_menu': 'acceso_define_cursos',
    #  'texto_menu': 'Crea/Modifica cursos',
    #  'href': 'define_curso',
    #  'nivel': 2,
    #  'tipo': 'Accesible',
    #  'pos': 1,
    #  'parent': 'acceso_horarios'
    #  },
    # {'code_menu': 'acceso_define_grupos',
    #  'texto_menu': 'Crea/Modifica grupos',
    #  'href': 'define_grupo',
    #  'nivel': 2,
    #  'tipo': 'Accesible',
    #  'pos': 1,
    #  'parent': 'acceso_horarios'
    #  },
    # {'code_menu': 'acceso_define_materias',
    #  'texto_menu': 'Crea/Modifica materias',
    #  'href': 'define_materia',
    #  'nivel': 2,
    #  'tipo': 'Accesible',
    #  'pos': 3,
    #  'parent': 'acceso_horarios'
    #  },
    {'code_menu': 'acceso_define_horarios',
     'texto_menu': 'Crea/Modifica horarios',
     'href': 'define_horario',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 4,
     'parent': 'acceso_horarios'
     },
    {'code_menu': 'acceso_horario_usuarios',
     'texto_menu': 'Horarios usuarios',
     'href': 'horario_ge',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 5,
     'parent': 'acceso_horarios'
     },
    {'code_menu': 'acceso_horario_aulas',
     'texto_menu': 'Horarios aulas',
     'href': 'horario_aulas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 6,
     'parent': 'acceso_horarios'
     },
    {'code_menu': 'acceso_horarios_subentidades',
     'texto_menu': 'Horarios grupos',
     'href': 'horario_subentidad',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 7,
     'parent': 'acceso_horarios'
     },
    {'code_menu': 'acceso_carga_masiva_horarios',
     'texto_menu': 'Carga masiva horarios',
     'href': 'carga_masiva_horarios',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 8,
     'parent': 'acceso_horarios'
     },
    {'code_menu': 'acceso_actividades_horarios',
     'texto_menu': 'Actividades del horario',
     'href': 'actividades_horarios',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 9,
     'parent': 'acceso_horarios'
     },
    {'code_menu': 'acceso_guardias_horarios',
     'texto_menu': 'Guardias horario',
     'href': 'guardias_horario',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 10,
     'parent': 'acceso_horarios'
     },
    {'code_menu': 'acceso_horarios_alumnos',
     'texto_menu': 'Alumnos',
     'href': 'alumnos_horarios',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 11,
     'parent': 'acceso_horarios'
     },
    {'code_menu': 'acceso_actillas',
     'texto_menu': 'Actillas',
     'href': 'actillas',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 12,
     'parent': 'acceso_horarios'
     },
    # {'code_menu': 'acceso_redactar_actas',
    #  'texto_menu': 'Redactar actas',
    #  'href': 'redactar_actas',
    #  'nivel': 2,
    #  'tipo': 'Accesible',
    #  'pos': 3,
    #  'parent': 'acceso_actas'
    #  },
    {'code_menu': 'acceso_tutores_entidad',
     'texto_menu': 'Tutores',
     'href': 'tutores_entidad',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 13,
     'parent': 'acceso_horarios'
     },
    {'code_menu': 'acceso_seguimiento_educativo',
     'texto_menu': 'Seguimiento educativo',
     'href': 'seguimiento_educativo',
     'nivel': 2,
     'tipo': 'Accesible',
     'pos': 14,
     'parent': 'acceso_horarios'
     }
]
# Se añaden otros permisos para el usuario

PERMISOS = [
    {'code_nombre': 'crea_horarios',
     'nombre': 'Tiene permiso para crear horarios en la entidad',
     'menu': 'acceso_define_horarios'
     },
    {'code_nombre': 'borra_horarios',
     'nombre': 'Tiene permiso para borrar horarios de la entidad',
     'menu': 'acceso_define_horarios'
     },
    {'code_nombre': 've_horarios_usuarios',
     'nombre': 'Tiene permiso para ver horarios de los usuarios',
     'menu': 'acceso_horario_usuarios'
     },
    {'code_nombre': 've_horarios_entidad',
     'nombre': 'Tiene permiso para ver horarios de las subentidades',
     'menu': 'acceso_horarios_subentidades'
     },
    {'code_nombre': 'crea_horarios_usuarios',
     'nombre': 'Tiene permiso para crear horarios para los usuarios',
     'menu': 'acceso_horario_usuarios'
     },
    {'code_nombre': 'crea_sesiones_horario',
     'nombre': 'Tiene permiso para crear sesiones en los horarios de los usuarios',
     'menu': 'acceso_horario_usuarios'
     },
    {'code_nombre': 'borra_sesiones_horario',
     'nombre': 'Tiene permiso para borrar sesiones en los horarios de los usuarios',
     'menu': 'acceso_horario_usuarios'
     },
    {'code_nombre': 'modifica_sesiones_horario',
     'nombre': 'Tiene permiso para modificar sesiones en los horarios de los usuarios',
     'menu': 'acceso_horario_usuarios'
     },
    {'code_nombre': 'alumnos_sesiones_horario',
     'nombre': 'Tiene permiso para asignar alumnos a las sesiones en los horarios de los usuarios',
     'menu': 'acceso_horario_usuarios'
     },
    {'code_nombre': 'crea_actividades_horario',
     'nombre': 'Tiene permiso para crear actividades para los horarios',
     'menu': 'acceso_actividades_horarios'
     },
    {'code_nombre': 'borra_actividades_horario',
     'nombre': 'Tiene permiso para borrar para los horarios',
     'menu': 'acceso_actividades_horarios'
     },
    {'code_nombre': 'edita_actividades_horario',
     'nombre': 'Tiene permiso para editar las actividades para los horarios',
     'menu': 'acceso_actividades_horarios'
     },
    {'code_nombre': 'crea_guardias_horario',
     'nombre': 'Tiene permiso para crear guardias de cualquier usuario en el horario',
     'menu': 'acceso_guardias_horarios'
     },
    {'code_nombre': 'borra_guardias_horario',
     'nombre': 'Tiene permiso para borrar guardias de cualquier usuario en el horario',
     'menu': 'acceso_guardias_horarios'
     },
    {'code_nombre': 'edita_guardias_horario',
     'nombre': 'Tiene permiso para editar guardias de cualquier usuario en el horario',
     'menu': 'acceso_guardias_horarios'
     },
    {'code_nombre': 'genera_actillas',
     'nombre': 'Tiene permiso para generar actillas de cualquier grupo de la entidad',
     'menu': 'acceso_actillas'
     },
    {'code_nombre': 'asigna_grupo_alumnos',
     'nombre': 'Tiene permiso para asignar grupo a los alumnos',
     'menu': 'acceso_horarios_alumnos'
     },
    {'code_nombre': 'asigna_tutor_alumnos',
     'nombre': 'Tiene permiso para asignar tutor a los alumnos',
     'menu': 'acceso_horarios_alumnos'
     },
    {'code_nombre': 'hace_seguimiento_alumnos',
     'nombre': 'Tiene permiso para ver el seguimiento educativo realizado a todos los alumnos',
     'menu': 'acceso_seguimiento_educativo'
     },
    {'code_nombre': 'hace_seguimiento_materias',
     'nombre': 'Tiene permiso para ver el seguimiento educativo realizado por los profesores',
     'menu': 'acceso_seguimiento_educativo'
     }
]
