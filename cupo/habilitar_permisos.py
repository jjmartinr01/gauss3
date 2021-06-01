from autenticar.models import Permiso
from entidades.models import Cargo, Gauser_extra

Miembro_Equipo_Directivo = ['acceso_configuracion', 'acceso_perfiles_permisos', 'asigna_perfiles', 'asigna_permisos',
                            'modifica_texto_menu', 'modifica_pos_menu', 'acceso_datos_entidad',
                            'modifica_datos_entidad', 'crea_dependencias', 'borra_dependencias', 'acceso_mensajes',
                            'acceso_redactar_mensaje', 'redacta_cualquier_usuario', 'redacta_usuarios_departamentos',
                            'redacta_usuarios_1', 'redacta_usuarios_2', 'redacta_usuarios_3', 'redacta_usuarios_4',
                            'acceso_calendario', 'acceso_vista_calendario', 'crea_eventos', 've_todos_eventos',
                            'borra_cualquier_evento', 'acceso_gestion_documental', 'acceso_documentos', 'crea_carpetas',
                            'sube_archivos', 've_todas_carpetas', 'edita_todos_archivos', 'borra_cualquier_archivo',
                            'borra_cualquier_carpeta', 'acceso_cuestionarios', 'acceso_formularios', 'crea_formularios',
                            'acceso_horarios', 'acceso_cupos', 'acceso_cupo_profesorado', 'crea_cupos', 'edita_cupos',
                            'copia_cupo_profesorado', 'borra_cupo_profesorado', 'crea_materias_cupo', 'pdf_cupo',
                            'bloquea_cupos', 'acceso_acciones_usuarios1', 'acceso_convivencia',
                            'acceso_gestionar_conductas', 'edita_sanciones_tipificadas', 'edita_conductas_tipificadas',
                            'acceso_absentismo', 'crea_actuacion_absentismo', 'borra_actuacion_absentismo',
                            'edita_actuacion_absentismo', 'crea_informe_absentismo', 'configura_expediente_absentismo',
                            'acceso_registro', 'crea_registros', 'borra_registros', 'acceso_reparaciones',
                            'crea_solicitud_reparacion', 'borra_solicitud_reparacion', 'controla_reparaciones_alb',
                            'controla_reparaciones_car', 'controla_reparaciones_ele', 'controla_reparaciones_inf',
                            'controla_reparaciones_fon', 'controla_reparaciones_gen', 'controla_reparaciones',
                            'genera_informe_reparaciones', 'acceso_actividades', 'crea_actividad', 'borra_actividad',
                            'edita_actividades', 'crea_informe_actividades', 'aprueba_actividades',
                            'acceso_informes_usuarios', 'acceso_informes_seguimiento', 'solicita_informes_seguimiento',
                            'borra_informes_seguimiento', 'edita_informes_seguimiento', 've_informes_seguimiento',
                            'borra_preguntas_informes_seguimiento', 'acceso_estudios_centro_educativo',
                            'acceso_configura_cursos', 'crea_cursos', 'borra_cursos', 'acceso_competencias_clave',
                            'valora_ccs_a_cualquier_alumno', 'genera_informe_ccs', 'acceso_programaciones_didacticas',
                            'acceso_programaciones_ccff', 'crea_programaciones_ccff', 'edita_programaciones_ccff',
                            'copia_programaciones_ccff', 'borra_programaciones_ccff', 'acceso_evaluar_materias',
                            'evalua_materias_asignadas', 'evalua_cualquier_materia', 'acceso_reuniones',
                            'acceso_conv_template', 'c_conv_template', 'w_conv_template', 'd_conv_template',
                            'acceso_gestionar_perfiles', 'crea_perfiles', 'borra_perfiles', 'edita_perfiles',
                            'acceso_crear_usuarios', 'crea_usuarios', 'acceso_mensajes_enviados',
                            'acceso_sancionar_conductas', 'sancionar_nivel_docente', 'sancionar_nivel_tutor',
                            'sancionar_nivel_jefe_estudios', 'sancionar_nivel_director', 'borra_sanciones_tipificadas',
                            'borra_conductas_tipificadas', 'genera_informe_sancionador', 'elige_sancionador',
                            'borra_informes_sancionadores', 'aplica_cualquier_sancion',
                            'recibe_mensajes_aviso_informes_sancionadores', 'acceso_configura_grupos', 'crea_grupos',
                            'borra_grupos', 'cc_valorar_mis_alumnos', 'acceso_cargar_programaciones',
                            'carga_programaciones', 'borra_programaciones_cargadas', 'descarga_programaciones',
                            'descarga_pga', 'acceso_configura_pendientes', 'acceso_conv_reunion', 'r_conv_reunion',
                            'c_conv_reunion', 'w_conv_reunion', 'd_conv_reunion', 'm_conv_reunion',
                            'acceso_carga_masiva', 'sube_archivo_csv', 'carga_masiva_racima', 'acceso_gestion_entidad',
                            'acceso_getion_bajas', 'alta_usuarios', 'baja_usuarios', 'borra_usuarios',
                            'acceso_mensajes_recibidos', 'acceso_informes_tareas', 'solicita_informes_tareas',
                            'borra_informes_tareas', 'edita_informes_tareas', 've_informes_tareas',
                            'cc_valorar_cualquier_alumno', 'acceso_resultados_aprendizaje',
                            'crea_resultados_aprendizaje_ccff', 'borra_resultados_aprendizaje_ccff',
                            'crea_objetivos_ccff', 'borra_objetivos_ccff', 'acceso_redactar_actas_reunion',
                            'w_sus_actas_reunion', 'w_actas_subentidades_reunion', 'w_cualquier_acta_reunion',
                            'mail_actas_reunion', 'acceso_gestionar_subentidades', 'crea_subentidades',
                            'borra_subentidades', 'edita_subentidades', 'acceso_reserva_plazas', 'reserva_usuarios',
                            'recibe_aviso_reserva', 'acceso_define_horarios', 'crea_horarios', 'borra_horarios',
                            'acceso_cuerpos_funcionarios', 'configura_ccs', 'acceso_miembros_entidad',
                            'listado_usuarios', 'modifica_datos_usuarios', 'configura_auto_id',
                            'acceso_horario_usuarios', 've_horarios_usuarios', 'crea_sesiones_horario',
                            'borra_sesiones_horario', 'modifica_sesiones_horario', 'alumnos_sesiones_horario',
                            'crea_horarios_usuarios', 'acceso_departamentos_centro_educativo', 'borra_departamentos',
                            'recarga_departamentos', 'add_miembros_departamento', 'acceso_control_asistencia_reunion',
                            'acceso_firmar_actas_reunion', 'acceso_listados_usuarios', 'acceso_horario_aulas',
                            'acceso_profesores_centro_educativo', 'acceso_lectura_actas_reunion', 'r_actas_reunion',
                            'acceso_horarios_subentidades', 've_horarios_entidad', 'acceso_dependencias_entidad',
                            'acceso_aspectos_pga', 'acceso_carga_masiva_horarios', 'crea_rondas',
                            'acceso_gestionar_rondas', 'accede_otras_rondas', 'acceso_pec',
                            'acceso_actividades_horarios', 'crea_actividades_horario', 'borra_actividades_horario',
                            'edita_actividades_horario', 'acceso_guardias_horarios', 'crea_guardias_horario',
                            'borra_guardias_horario', 'edita_guardias_horario', 'acceso_horarios_alumnos',
                            'asigna_grupo_alumnos', 'asigna_tutor_alumnos', 'acceso_actillas', 'genera_actillas',
                            'acceso_tutores_entidad']

# def habilitar_miembros_equipo_directivo(po):
#     permisos = Permiso.objects.filter(code_nombre__in=Miembro_Equipo_Directivo)
#     try:
#         miembro_equipo_directivo = Cargo.objects.get(entidad=po.ronda_centro.entidad, clave_cargo='202006011113')
#     except:
#         miembro_equipo_directivo = Cargo.objects.create(entidad=po.ronda_centro.entidad, borrable=False,
#                                                         cargo='Miembro del Equipo Directivo',
#                                                         nivel=1, clave_cargo='202006011113')
#         miembro_equipo_directivo.permisos.add(*permisos)
#     for pxls in po.plantillaxls_set.filter(x_actividad='529'):
#         try:
#             gex = Gauser_extra.objects.get(ronda=po.ronda_centro, clave_ex=pxls.x_docente)
#             gex.cargos.add(miembro_equipo_directivo)
#         except:
#             pass