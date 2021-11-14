from django.db.models import Q

TC = {
    'I.E.S. - Instituto de Educación Secundaria': {
        'Educación Secundaria Obligatoria': {
            'Troncales': {
                'q': Q(actividad__clave_ex='1') & (Q(materia__grupo_materias__icontains='tronca') | Q(
                    materia__grupo_materias__icontains='extranj') | Q(
                    materia__grupo_materias__icontains='obligator')) & Q(
                    materia__curso__etapa_escolar__clave_ex='24') & ~Q(
                    materia__curso__clave_ex__in=['222074', '222075']) & ~Q(materia__nombre__icontains='mbito'),
                'horas_base': True,
                'codecol': 10005
            },
            'Específicas': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='espec'),
                'horas_base': True,
                'codecol': 10010
            },
            'Libre Conf. Aut.': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='libre conf') & ~Q(
                    materia__curso__clave_ex__in=['222074', '222075']) & ~Q(materia__nombre__icontains='mbito'),
                'horas_base': True,
                'codecol': 10015
            },
            'Rel./Val. Éticos': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='Rel. y Aten.'),
                'horas_base': True,
                'codecol': 10020
            },
            'Desdobles ESO': {
                'q': (Q(actividad__clave_ex='539') | Q(actividad__clave_ex='400') | Q(actividad__clave_ex='522')) & Q(
                    materia__curso__etapa_escolar__clave_ex='24'),
                'horas_base': True,
                'codecol': 10025
            },
        },
        'Bachillerato': {
            'Troncales': {
                'q': (Q(materia__grupo_materias__icontains='tronca') | Q(
                    materia__grupo_materias__icontains='extranj') | Q(
                    materia__grupo_materias__icontains='obligator')) & Q(
                    materia__curso__etapa_escolar__clave_ex='31') & Q(actividad__clave_ex='1'),
                'horas_base': True,
                'codecol': 10030
            },
            'Específicas': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='31') & Q(
                    materia__grupo_materias__icontains='espec'),
                'horas_base': True,
                'codecol': 10035
            },
            'Desdobles BACH': {
                'q': (Q(actividad__clave_ex='539') | Q(actividad__clave_ex='400') | Q(actividad__clave_ex='522')) & Q(
                    materia__curso__etapa_escolar__clave_ex='31'),
                'horas_base': True,
                'codecol': 10040
            },
        },
        'Formación Profesional': {
            'CFGM': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['1373', '23']),
                'horas_base': True,
                'codecol': 10045
            },
            'CFGS': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['2', '1375']),
                'horas_base': True,
                'codecol': 10050
            },
            'FPB': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='5504'),
                'horas_base': True,
                'codecol': 10055
            },
        },
        'Atención a la Diversidad y otras horas': {
            'PACG': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__clave_ex__in=['222074', '222075']),
                'horas_base': False,
                'codecol': 10060
            },
            'Refuerzo 1º ESO': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='170506'),
                'horas_base': False,
                'codecol': 10065
            },
            'PMAR1': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='101324'),
                'horas_base': False,
                'codecol': 10070
            },
            'PMAR2': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='101325'),
                'horas_base': False,
                'codecol': 10075
            },
            'Curso Prep. Acceso CCFF': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['3129', ]),
                'horas_base': False,
                'codecol': 10080
            },
            'Tutorías': {
                'q': Q(actividad__clave_ex='519') | Q(actividad__clave_ex='2') | Q(actividad__clave_ex='376'),
                'horas_base': True,
                'codecol': 10085
            },
            'Jefatura Depart./CCP': {
                'q': Q(actividad__clave_ex='547') | Q(actividad__clave_ex='545'),
                'horas_base': True,
                'codecol': 10090
            },
            'Mayor 55 años': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': False,
                'codecol': 10095
            },
            'Horas TIC': {
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(
                    actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 10096
            },
        },
    },
    'S.I.E.S. - Sección de Instituto de Educación Secundaria': {
        'Educación Secundaria Obligatoria': {
            'Troncales': {
                'q': Q(actividad__clave_ex='1') & (Q(materia__grupo_materias__icontains='tronca') | Q(
                    materia__grupo_materias__icontains='extranj') | Q(
                    materia__grupo_materias__icontains='obligator')) & Q(
                    materia__curso__etapa_escolar__clave_ex='24') & ~Q(
                    materia__curso__clave_ex__in=['222074', '222075']) & ~Q(materia__nombre__icontains='mbito'),
                'horas_base': True,
                'codecol': 20005
            },
            'Específicas': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='espec'),
                'horas_base': True,
                'codecol': 20010
            },
            'Libre Conf. Aut.': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='libre conf') & ~Q(
                    materia__curso__clave_ex__in=['222074', '222075']) & ~Q(materia__nombre__icontains='mbito'),
                'horas_base': True,
                'codecol': 20015
            },
            'Rel./Val. Éticos': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='Rel. y Aten.'),
                'horas_base': True,
                'codecol': 20020
            },
            'Desdobles ESO': {
                'q': (Q(actividad__clave_ex='539') | Q(actividad__clave_ex='400') | Q(actividad__clave_ex='522')) & Q(
                    materia__curso__etapa_escolar__clave_ex='24'),
                'horas_base': True,
                'codecol': 20025
            },
        },
        'Bachillerato': {
            'Troncales': {
                'q': (Q(materia__grupo_materias__icontains='tronca') | Q(
                    materia__grupo_materias__icontains='extranj') | Q(
                    materia__grupo_materias__icontains='obligator')) & Q(
                    materia__curso__etapa_escolar__clave_ex='31') & Q(actividad__clave_ex='1'),
                'horas_base': True,
                'codecol': 20030
            },
            'Específicas': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='31') & Q(
                    materia__grupo_materias__icontains='espec'),
                'horas_base': True,
                'codecol': 20035
            },
            'Desdobles BACH': {
                'q': (Q(actividad__clave_ex='539') | Q(actividad__clave_ex='400') | Q(actividad__clave_ex='522')) & Q(
                    materia__curso__etapa_escolar__clave_ex='31'),
                'horas_base': True,
                'codecol': 20040
            },
        },
        'Formación Profesional': {
            'CFGM': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['1373', '23']),
                'horas_base': True,
                'codecol': 20045
            },
            'CFGS': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['2', '1375']),
                'horas_base': True,
                'codecol': 20050
            },
            'FPB': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='5504'),
                'horas_base': True,
                'codecol': 20055
            },
        },
        'Atención a la Diversidad y otras horas': {
            'PACG': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__clave_ex__in=['222074', '222075']),
                'horas_base': False,
                'codecol': 20060
            },
            'Refuerzo 1º ESO': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='170506'),
                'horas_base': False,
                'codecol': 20065
            },
            'PMAR1': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='101324'),
                'horas_base': False,
                'codecol': 20070
            },
            'PMAR2': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='101325'),
                'horas_base': False,
                'codecol': 20075
            },
            'Curso Prep. Acceso CCFF': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex__in=['3129', ]),
                'horas_base': False,
                'codecol': 20080
            },
            'Tutorías': {
                'q': Q(actividad__clave_ex='519') | Q(actividad__clave_ex='2') | Q(actividad__clave_ex='376'),
                'horas_base': True,
                'codecol': 20085
            },
            'Jefatura Depart./CCP': {
                'q': Q(actividad__clave_ex='547') | Q(actividad__clave_ex='545'),
                'horas_base': True,
                'codecol': 20090
            },
            'Mayor 55 años': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': False,
                'codecol': 20095
            },
            'Horas TIC': {
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(
                    actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 20096
            },
        },
    },
    'C.E.P.A. - Centro Público de Educación de Personas Adultas': {
        'Educación Secundaria': {
            'ESPA Nivel I': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222076', '222077']),
                'horas_base': True,
                'codecol': 30100
            },
            'ESPA Nivel II': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222078', '222079']),
                'horas_base': True,
                'codecol': 30105
            },
            'ESPA Dist. Nivel I': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222080', '222081']),
                'horas_base': True,
                'codecol': 30110
            },
            'ESPA Dist. Nivel II': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222082', '222083']),
                'horas_base': True,
                'codecol': 30115
            },
        },
        'Enseñanzas Iniciales': {
            'Ens. Iniciales I': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3167') & Q(
                    materia__curso__clave_ex='121469'),
                'horas_base': True,
                'codecol': 30120
            },
            'Ens. Iniciales II': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3167') & Q(
                    materia__curso__clave_ex='121470'),
                'horas_base': True,
                'codecol': 30125
            },
        },
        'Educación no reglada': {
            'Competencias N-2': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__clave_ex='222071'),
                'horas_base': False,
                'codecol': 30130
            },
            'Alfab. Inmigrantes': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='nmigrantes'),
                'horas_base': False,
                'codecol': 30135
            },
            'Cursos de preparación': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='mayores de'),
                'horas_base': False,
                'codecol': 30140
            },
            'Ofimática': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='ofim'),
                'horas_base': False,
                'codecol': 30145
            },
            'Informática': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='inform'),
                'horas_base': False,
                'codecol': 30150
            },
            'Mecanografía': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='mecanog'),
                'horas_base': False,
                'codecol': 30155
            },
            'Inglés': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='ingl'),
                'horas_base': False,
                'codecol': 30160
            },
        },
        'Otras': {
            'Tutorías': {
                'q': Q(actividad__clave_ex='519') | Q(actividad__clave_ex='2') | Q(actividad__clave_ex='376'),
                'horas_base': True,
                'codecol': 30165
            },
            'Jefatura Depart./CCP': {
                'q': Q(actividad__clave_ex='547') | Q(actividad__clave_ex='545'),
                'horas_base': True,
                'codecol': 30170
            },
            'Mayor 55 años': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': False,
                'codecol': 30175
            },
            'Horas TIC': {
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(
                    actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 30176
            },
        },
    },
    'C.E.I.P. - Colegio de Educación Infantil y Primaria': {
        'Infantil': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100304'),
                'horas_base': True,
                'codecol': 40180
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100305'),
                'horas_base': True,
                'codecol': 40185
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100306'),
                'horas_base': True,
                'codecol': 40190
            },
        },
        'Primaria': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101317'),
                'horas_base': True,
                'codecol': 40200
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101318'),
                'horas_base': True,
                'codecol': 40205
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101319'),
                'horas_base': True,
                'codecol': 40210
            },
            '4º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101320'),
                'horas_base': True,
                'codecol': 40215
            },
            '5º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101321'),
                'horas_base': True,
                'codecol': 40220
            },
            '6º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101322'),
                'horas_base': True,
                'codecol': 40225
            },
        },
        'Otras horas': {
            'Apoyo': {
                'q': Q(actividad__clave_ex='522'),
                'horas_base': True,
                'codecol': 40230
            },
            'Atención ACNEE AL': {
                'q': Q(actividad__clave_ex='563'),
                'horas_base': True,
                'codecol': 40235
            },
            'Atención ACNEE PT': {
                'q': Q(actividad__clave_ex='562'),
                'horas_base': True,
                'codecol': 40240
            },
            'Coordinador Ciclo': {
                'q': Q(actividad__clave_ex='116'),
                'horas_base': True,
                'codecol': 40245
            },
            'Coor. Comedor/Transporte': {
                'q': Q(actividad__clave_ex='527'),
                'horas_base': True,
                'codecol': 40250
            },
            'Dirección/Jefatura/Secretaría': {
                'q': Q(actividad__clave_ex__in=['529', '530', '532']),
                'horas_base': True,
                'codecol': 40255
            },
            'Mayor 55': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': True,
                'codecol': 40260
            },
            'Horas TIC': {
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(
                    actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 40261
            },
        },
    },
    'C.R.A. - Colegio Rural Agrupado': {
        'Infantil': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100304'),
                'horas_base': True,
                'codecol': 50180
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100305'),
                'horas_base': True,
                'codecol': 50185
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100306'),
                'horas_base': True,
                'codecol': 50190
            },
        },
        'Primaria': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101317'),
                'horas_base': True,
                'codecol': 50200
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101318'),
                'horas_base': True,
                'codecol': 50205
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101319'),
                'horas_base': True,
                'codecol': 50210
            },
            '4º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101320'),
                'horas_base': True,
                'codecol': 50215
            },
            '5º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101321'),
                'horas_base': True,
                'codecol': 50220
            },
            '6º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101322'),
                'horas_base': True,
                'codecol': 50225
            },
        },
        'Otras horas': {
            'Apoyo': {
                'q': Q(actividad__clave_ex='522'),
                'horas_base': True,
                'codecol': 50230
            },
            'Atención ACNEE AL': {
                'q': Q(actividad__clave_ex='563'),
                'horas_base': True,
                'codecol': 50235
            },
            'Atención ACNEE PT': {
                'q': Q(actividad__clave_ex='562'),
                'horas_base': True,
                'codecol': 50240
            },
            'Coordinador Ciclo': {
                'q': Q(actividad__clave_ex='116'),
                'horas_base': True,
                'codecol': 50245
            },
            'Coor. Comedor/Transporte': {
                'q': Q(actividad__clave_ex='527'),
                'horas_base': True,
                'codecol': 50250
            },
            'Dirección/Jefatura/Secretaría': {
                'q': Q(actividad__clave_ex__in=['529', '530', '532']),
                'horas_base': True,
                'codecol': 50255
            },
            'Mayor 55': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': True,
                'codecol': 50260
            },
            'Horas TIC': {
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(
                    actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 50261
            },
        },
    },
    'C.E.O. - Centro de Educación Obligatoria': {
        'Infantil': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100304'),
                'horas_base': True,
                'codecol': 60180
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100305'),
                'horas_base': True,
                'codecol': 60185
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100306'),
                'horas_base': True,
                'codecol': 60190
            },
        },
        'Primaria': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101317'),
                'horas_base': True,
                'codecol': 60200
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101318'),
                'horas_base': True,
                'codecol': 60205
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101319'),
                'horas_base': True,
                'codecol': 60210
            },
            '4º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101320'),
                'horas_base': True,
                'codecol': 60215
            },
            '5º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101321'),
                'horas_base': True,
                'codecol': 60220
            },
            '6º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101322'),
                'horas_base': True,
                'codecol': 60225
            },
        },
        'Educación Secundaria Obligatoria': {
            'Troncales': {
                'q': Q(actividad__clave_ex='1') & (Q(materia__grupo_materias__icontains='tronca') | Q(
                    materia__grupo_materias__icontains='extranj') | Q(
                    materia__grupo_materias__icontains='obligator')) & Q(
                    materia__curso__etapa_escolar__clave_ex='24') & ~Q(
                    materia__curso__clave_ex__in=['222074', '222075']) & ~Q(materia__nombre__icontains='mbito'),
                'horas_base': True,
                'codecol': 60230
            },
            'Específicas': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='espec'),
                'horas_base': True,
                'codecol': 60235
            },
            'Libre Conf. Aut.': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='libre conf') & ~Q(
                    materia__curso__clave_ex__in=['222074', '222075']) & ~Q(materia__nombre__icontains='mbito'),
                'horas_base': True,
                'codecol': 60240
            },
            'Rel./Val. Éticos': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='24') & Q(
                    materia__grupo_materias__icontains='Rel. y Aten.'),
                'horas_base': True,
                'codecol': 60245
            },
            'Desdobles ESO': {
                'q': (Q(actividad__clave_ex='539') | Q(actividad__clave_ex='400') | Q(actividad__clave_ex='522')) & Q(
                    materia__curso__etapa_escolar__clave_ex='24'),
                'horas_base': True,
                'codecol': 60250
            },
        },
        'Atención a la Diversidad y otras horas': {
            'Refuerzo 1º ESO': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='170506'),
                'horas_base': False,
                'codecol': 60255
            },
            'PMAR1': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='101324'),
                'horas_base': False,
                'codecol': 60260
            },
            'PMAR2': {
                'q': Q(actividad__clave_ex='1') & Q(materia__nombre__icontains='mbito') & Q(
                    materia__curso__clave_ex='101325'),
                'horas_base': False,
                'codecol': 60265
            },
            'Tutorías': {
                'q': Q(actividad__clave_ex='519') | Q(actividad__clave_ex='2') | Q(actividad__clave_ex='376'),
                'horas_base': True,
                'codecol': 60270
            },
            'Jefatura Depart./CCP': {
                'q': Q(actividad__clave_ex='547') | Q(actividad__clave_ex='545'),
                'horas_base': True,
                'codecol': 60275
            },
            'Mayor 55 años': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': False,
                'codecol': 60280
            },
            'Horas TIC': {
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(
                    actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 60285
            },
            'Apoyo': {
                'q': Q(actividad__clave_ex='522'),
                'horas_base': True,
                'codecol': 60290
            },
            'Atención ACNEE AL': {
                'q': Q(actividad__clave_ex='563'),
                'horas_base': True,
                'codecol': 60295
            },
            'Atención ACNEE PT': {
                'q': Q(actividad__clave_ex='562'),
                'horas_base': True,
                'codecol': 60300
            },
            'Coordinador Ciclo': {
                'q': Q(actividad__clave_ex='116'),
                'horas_base': True,
                'codecol': 60305
            },
            'Coor. Comedor/Transporte': {
                'q': Q(actividad__clave_ex='527'),
                'horas_base': True,
                'codecol': 60310
            },
            'Dirección/Jefatura/Secretaría': {
                'q': Q(actividad__clave_ex__in=['529', '530', '532']),
                'horas_base': True,
                'codecol': 60315
            },
        },
    },
    'C.E.E. - Centro de Educación Especial': {
        'Infantil': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100304'),
                'horas_base': True,
                'codecol': 70180
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100305'),
                'horas_base': True,
                'codecol': 70185
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100306'),
                'horas_base': True,
                'codecol': 70190
            },
        },
        'Primaria': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101317'),
                'horas_base': True,
                'codecol': 70200
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101318'),
                'horas_base': True,
                'codecol': 70205
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101319'),
                'horas_base': True,
                'codecol': 70210
            },
            '4º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101320'),
                'horas_base': True,
                'codecol': 70215
            },
            '5º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101321'),
                'horas_base': True,
                'codecol': 70220
            },
            '6º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101322'),
                'horas_base': True,
                'codecol': 70225
            },
        },
        'Otras horas': {
            'Apoyo': {
                'q': Q(actividad__clave_ex='522'),
                'horas_base': True,
                'codecol': 70230
            },
            'Atención ACNEE AL': {
                'q': Q(actividad__clave_ex='563'),
                'horas_base': True,
                'codecol': 70235
            },
            'Atención ACNEE PT': {
                'q': Q(actividad__clave_ex='562'),
                'horas_base': True,
                'codecol': 70240
            },
            'Coordinador Ciclo': {
                'q': Q(actividad__clave_ex='116'),
                'horas_base': True,
                'codecol': 70245
            },
            'Coor. Comedor/Transporte': {
                'q': Q(actividad__clave_ex='527'),
                'horas_base': True,
                'codecol': 70250
            },
            'Dirección/Jefatura/Secretaría': {
                'q': Q(actividad__clave_ex__in=['529', '530', '532']),
                'horas_base': True,
                'codecol': 70255
            },
            'Mayor 55': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': True,
                'codecol': 70260
            },
            'Horas TIC': {
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(
                    actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 70261
            },
        },
    },
    'C.I.P.F.P. - Centro Público Integrado de Formación Profesional': {},
    'E.I.P.C. - Escuela Infantil': {},
    'E.S.D. - Escuela Superior de Diseño': {
        'Horas de dedicación y reducciones': {
            'Horas especialidad': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 78005
            },
            'Horas música de cámara': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 78010
            },
            'Jefatura Depart./CCP': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 78015
            },
            'Mayor 55 años': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': False,
                'codecol': 78020
            },
            'Horas TIC': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': False,
                'codecol': 78025
            },
        },
    },
    'E.O.I. - Escuela Oficial de Idiomas': {
        'Horas de dedicación y reducciones': {
            'Horas especialidad': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 76005
            },
            'Horas música de cámara': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 76010
            },
            'Jefatura Depart./CCP': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 76015
            },
            'Mayor 55 años': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': False,
                'codecol': 76020
            },
            'Horas TIC': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': False,
                'codecol': 76025
            },
        },
    },
    'C.E.M. - Conservatorio Elemental de Música': {
        'Horas de dedicación y reducciones': {
            'Horas especialidad': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 75005
            },
            'Horas música de cámara': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 75010
            },
            'Jefatura Depart./CCP': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 75015
            },
            'Mayor 55 años': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': False,
                'codecol': 75020
            },
            'Horas TIC': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': False,
                'codecol': 75025
            },
        },
    },
    'C.P.M. - Conservatorio Profesional de Música': {
        'Horas de dedicación y reducciones': {
            'Horas especialidad': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 75045
            },
            'Horas música de cámara': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 75050
            },
            'Jefatura Depart./CCP': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': True,
                'codecol': 75055
            },
            'Mayor 55 años': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': False,
                'codecol': 75060
            },
            'Horas TIC': {
                'clase': 'EspecialidadPlantilla',
                'q': '',
                'horas_base': False,
                'codecol': 75065
            },
        },
    }
}
