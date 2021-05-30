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
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
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
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 10096
            },
        },
    },
    'C.E.P.A. - Centro Público de Educación de Personas Adultas': {
        'Educación Secundaria': {
            'ESPA Nivel I': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222076', '222077']),
                'horas_base': True,
                'codecol': 10100
            },
            'ESPA Nivel II': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222078', '222079']),
                'horas_base': True,
                'codecol': 10105
            },
            'ESPA Dist. Nivel I': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222080', '222081']),
                'horas_base': True,
                'codecol': 10110
            },
            'ESPA Dist. Nivel II': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='2561') & Q(
                    materia__curso__clave_ex__in=['222082', '222083']),
                'horas_base': True,
                'codecol': 10115
            },
        },
        'Enseñanzas Iniciales': {
            'Ens. Iniciales I': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3167') & Q(
                    materia__curso__clave_ex='121469'),
                'horas_base': True,
                'codecol': 10120
            },
            'Ens. Iniciales II': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3167') & Q(
                    materia__curso__clave_ex='121470'),
                'horas_base': True,
                'codecol': 10125
            },
        },
        'Educación no reglada': {
            'Competencias N-2': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__clave_ex='222071'),
                'horas_base': False,
                'codecol': 10130
            },
            'Alfab. Inmigrantes': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='nmigrantes'),
                'horas_base': False,
                'codecol': 10135
            },
            'Cursos de preparación': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='mayores de'),
                'horas_base': False,
                'codecol': 10140
            },
            'Ofimática': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='ofim'),
                'horas_base': False,
                'codecol': 10145
            },
            'Informática': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='inform'),
                'horas_base': False,
                'codecol': 10150
            },
            'Mecanografía': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='mecanog'),
                'horas_base': False,
                'codecol': 10155
            },
            'Inglés': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3170') & Q(
                    materia__curso__nombre__icontains='ingl'),
                'horas_base': False,
                'codecol': 10160
            },
        },
        'Otras': {
            'Tutorías': {
                'q': Q(actividad__clave_ex='519') | Q(actividad__clave_ex='2') | Q(actividad__clave_ex='376'),
                'horas_base': True,
                'codecol': 10165
            },
            'Jefatura Depart./CCP': {
                'q': Q(actividad__clave_ex='547') | Q(actividad__clave_ex='545'),
                'horas_base': True,
                'codecol': 10170
            },
            'Mayor 55 años': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': False,
                'codecol': 10175
            },
            'Horas TIC': {
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 10176
            },
        },
    },
    'C.E.I.P. - Colegio de Educación Infantil y Primaria': {
        'Infantil': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100304'),
                'horas_base': True,
                'codecol': 10180
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100305'),
                'horas_base': True,
                'codecol': 10185
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100306'),
                'horas_base': True,
                'codecol': 10190
            },
        },
        'Primaria': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101317'),
                'horas_base': True,
                'codecol': 10200
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101318'),
                'horas_base': True,
                'codecol': 10205
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101319'),
                'horas_base': True,
                'codecol': 10210
            },
            '4º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101320'),
                'horas_base': True,
                'codecol': 10215
            },
            '5º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101321'),
                'horas_base': True,
                'codecol': 10220
            },
            '6º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101322'),
                'horas_base': True,
                'codecol': 10225
            },
        },
        'Otras horas': {
            'Apoyo': {
                'q': Q(actividad__clave_ex='522'),
                'horas_base': True,
                'codecol': 10230
            },
            'Atención ACNEE AL': {
                'q': Q(actividad__clave_ex='563'),
                'horas_base': True,
                'codecol': 10235
            },
            'Atención ACNEE PT': {
                'q': Q(actividad__clave_ex='562'),
                'horas_base': True,
                'codecol': 10240
            },
            'Coordinador Ciclo': {
                'q': Q(actividad__clave_ex='116'),
                'horas_base': True,
                'codecol': 10245
            },
            'Coor. Comedor/Transporte': {
                'q': Q(actividad__clave_ex='527'),
                'horas_base': True,
                'codecol': 10250
            },
            'Dirección/Jefatura/Secretaría': {
                'q': Q(actividad__clave_ex__in=['529', '530', '532']),
                'horas_base': True,
                'codecol': 10255
            },
            'Mayor 55': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': True,
                'codecol': 10260
            },
            'Horas TIC': {
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 10261
            },
        },
    },
    'C.R.A. - Colegio Rural Agrupado': {
        'Infantil': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100304'),
                'horas_base': True,
                'codecol': 10180
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100305'),
                'horas_base': True,
                'codecol': 10185
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='3') & Q(
                    materia__curso__clave_ex='100306'),
                'horas_base': True,
                'codecol': 10190
            },
        },
        'Primaria': {
            '1º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101317'),
                'horas_base': True,
                'codecol': 10200
            },
            '2º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101318'),
                'horas_base': True,
                'codecol': 10205
            },
            '3º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101319'),
                'horas_base': True,
                'codecol': 10210
            },
            '4º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101320'),
                'horas_base': True,
                'codecol': 10215
            },
            '5º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101321'),
                'horas_base': True,
                'codecol': 10220
            },
            '6º': {
                'q': Q(actividad__clave_ex='1') & Q(materia__curso__etapa_escolar__clave_ex='12') & Q(
                    materia__curso__clave_ex='101322'),
                'horas_base': True,
                'codecol': 10225
            },
        },
        'Otras horas': {
            'Apoyo': {
                'q': Q(actividad__clave_ex='522'),
                'horas_base': True,
                'codecol': 10230
            },
            'Atención ACNEE AL': {
                'q': Q(actividad__clave_ex='563'),
                'horas_base': True,
                'codecol': 10235
            },
            'Atención ACNEE PT': {
                'q': Q(actividad__clave_ex='562'),
                'horas_base': True,
                'codecol': 10240
            },
            'Coordinador Ciclo': {
                'q': Q(actividad__clave_ex='116'),
                'horas_base': True,
                'codecol': 10245
            },
            'Coor. Comedor/Transporte': {
                'q': Q(actividad__clave_ex='527'),
                'horas_base': True,
                'codecol': 10250
            },
            'Dirección/Jefatura/Secretaría': {
                'q': Q(actividad__clave_ex__in=['529', '530', '532']),
                'horas_base': True,
                'codecol': 10255
            },
            'Mayor 55': {
                'q': Q(actividad__clave_ex='176'),
                'horas_base': True,
                'codecol': 10260
            },
            'Horas TIC': {
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 10261
            },
        },
    },
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
                'q': Q(actividad__clave_ex='542') | Q(actividad__clave_ex='512') | Q(actividad__clave_ex='528') | Q(actividad__clave_ex='506') | Q(actividad__clave_ex='507') | Q(actividad__clave_ex='552'),
                'horas_base': False,
                'codecol': 10096
            },
        },
    },
}