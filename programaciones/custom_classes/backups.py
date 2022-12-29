import logging

from django.template.loader import render_to_string
from django.db import transaction
from ..models import *
from defusedxml import ElementTree


class BkProgsec:  # sag
    def __init__(self, progsec_id=-1):
        self.id = progsec_id
        self.xmlContent = None
        self.gep_id = None
        self.new_progsec_id = None
        self.logger = logging.getLogger('django')

    def generarXML(self, progsec):
        progsec = ProgSec.objects.get(id=self.id)
        contexto = {
            'progsec': progsec,
        }
        self.xmlContent = render_to_string("bkprogsec.xml", context=contexto)
        return self.xmlContent

    #                                                                         #
    # Desde aquí en adelante, funciones para la importación de programaciones #
    #                                                                         #

    def importarXML(self, request):
        data = request.FILES['file_bkimportar'].read()
        tree = ElementTree.fromstring(data)
        result = ""
        try:
            with transaction.atomic():
                self.gep_id = request.session['gauser_extra'].gauser_extra_programaciones.id
                self.__crearProgramaciones(tree)
        except Exception as e:
            self.logger.info('Importación programación ==error==> %s' % e.__str__())
            result = "No se ha creado la programación = " + str(e)

        return "Importado el fichero. " + result

    def __crearProgramaciones(self, programaciones):
        # Recorre todas las programaciones que contenga el fichero
        for progsec in programaciones:
            if progsec.tag == 'programacion':
                self.__crearProgsec(progsec)

    def __crearProgsec(self, progsec):
        # Procesamos datos propios de progsec
        for prog in progsec:
            if prog.tag == 'datos':
                self.logger.info('Importación programación ==__crearProgsec==> ...')
                newProgsec = ProgSec.objects.create(
                    nombre=prog.find('nombre').text + " (Importada)",
                    tipo=prog.find('tipo').text,
                    inicio_clases=prog.find('inicio_clases').text,
                    fin_clases=prog.find('fin_clases').text,
                    procdiversidad=prog.find('procdiversidad').text,
                    creado=prog.find('creado').text,
                    modificado=prog.find('modificado').text,
                    departamento_id=prog.find('departamento_id').text,
                    es_copia_de_id=progsec.get('id'),
                    gep_id=self.gep_id,
                    materia_id=prog.find('materia_id').text,
                    pga_id=prog.find('pga_id').text
                )
                newProgsec.save()
                self.logger.info('Importación programación ==__crearProgsec==> OK')
                self.new_progsec_id = newProgsec.id
            elif prog.tag == 'cuadernos_prof':
                self.__crearCuadernosProf(cuadernos=prog)
            elif prog.tag == 'libros_recurso':
                self.__crearLibrosRecurso(libros=prog)  # ok
            elif prog.tag == 'saberes_basicos':
                self.__crearSaberesBasicos(saberes=prog)  # ok
            elif prog.tag == 'acts_excom':
                self.__crearActsExCom(acts=prog)  # ok
            elif prog.tag == 'ces_progsec':
                self.__crearCesProgsec(ces=prog)  # ok

    def __crearLibrosRecurso(self, libros):
        # Recorre todos los libros recurso que contenga la programación
        self.logger.info('Importación programación ==__crearLibrosRecurso==> ...')
        for libro in libros:
            if libro.tag == 'librorecurso':
                for elemento in libro:
                    if elemento.tag == 'datos':
                        newLibroRecurso = LibroRecurso.objects.create(
                            nombre=elemento.find('nombre').text,
                            isbn=elemento.find('isbn').text,
                            observaciones=elemento.find('observaciones').text,
                            doc_file=elemento.find('doc_file').text,
                            content_type=elemento.find('content_type').text,
                            modificado=elemento.find('modificado').text,
                            psec_id=self.new_progsec_id
                        )
                        newLibroRecurso.save()
        self.logger.info('Importación programación ==__crearLibrosRecurso==> OK')

    def __crearSaberesBasicos(self, saberes):
        # Recorre saberes que contenga la programación
        self.logger.info('Importación programación ==__crearSaberesBasicos==> Creando...')
        for saber in saberes:
            if saber.tag == 'saberbas':
                self.__crearSaberbas(saber=saber)
        self.logger.info('Importación programación ==__crearSaberesBasicos==> OK')

    def __crearSaberbas(self, saber):
        for elemento in saber:
            if elemento.tag == 'datos':
                newSaberbas = SaberBas.objects.create(
                    orden=elemento.find('orden').text,
                    nombre=elemento.find('nombre').text,
                    comienzo=elemento.find('comienzo').text,
                    periodos=elemento.find('periodos').text,
                    modificado=elemento.find('modificado').text,
                    psec_id=self.new_progsec_id
                )
                newSaberbas.save()
            elif elemento.tag == 'librorecurso':
                try:
                    lr = LibroRecurso.objects.get(id=elemento.text)
                except LibroRecurso.DoesNotExist:
                    self.logger.info('Importación programación ==error==> No existe Librorecurso: ' + elemento.text)

                newSaberbas.librorecursos.add(lr)

    def __crearActsExCom(self, acts):
        # Recorre saberes que contenga la programación
        self.logger.info('Importación programación ==__crearActsExCom==> Creando...')
        for actexcom in acts:
            if actexcom.tag == 'actexcom':
                self.__crearActexcom(actexcom)
        self.logger.info('Importación programación ==__crearActsExCom==> OK')

    def __crearActexcom(self, actexcom):
        for elemento in actexcom:
            if elemento.tag == 'datos':
                newActexcom = ActExCom.objects.create(
                    nombre=elemento.find('nombre').text,
                    observaciones=elemento.find('observaciones').text,
                    inicio=elemento.find('inicio').text,
                    fin=elemento.find('fin').text,
                    modificado=elemento.find('modificado').text,
                    psec_id=self.new_progsec_id
                )
                newActexcom.save()
            elif elemento.tag == 'saberesbas':
                for saberbas in elemento:
                    if saberbas.tag == 'saberbas':
                        try:
                            sb = SaberBas.objects.get(id=saberbas.text)
                        except SaberBas.DoesNotExist:
                            self.logger.info('Importación programación ==error==> No existe Saberbas: ' + saberbas.text)
                        newActexcom.saberbas_set.add(sb)

    def __crearCesProgsec(self, ces):
        # Recorre Ces_Progsec que contenga la programación
        self.logger.info('Importación programación ==__crearCesProgsec==> Creando...')
        for ceprogsec in ces:
            if ceprogsec.tag == 'ceprogsec':
                self.__crearCepProgsec(cep=ceprogsec)
        self.logger.info('Importación programación ==__crearCesProgsec==> OK')

    def __crearCepProgsec(self, cep):
        # Recorre cada ceprogsec de ces_progsec
        for elemento in cep:
            if elemento.tag == 'datos':
                newCEProgsec = CEProgSec(
                    valor=elemento.find('valor').text,
                    modificado=elemento.find('modificado').text,
                    ce_id=elemento.find('ce_id').text,
                    psec_id=self.new_progsec_id
                )
                newCEProgsec.save()
            elif elemento.tag == 'cevprogsec':
                for cevprogsec in elemento:
                    if cevprogsec.tag == 'datos':
                        newCEvProgsec = CEvProgSec(
                            valor=cevprogsec.find('valor').text,
                            modificado=cevprogsec.find('modificado').text,
                            cepsec_id=newCEProgsec.id,
                            cev_id=cevprogsec.find('cev_id').text
                        )
                        newCEvProgsec.save()
            elif elemento.tag == 'sitaprens':
                for sitapren in elemento:
                    if sitapren.tag == 'sitapren':
                        try:
                            sp = SitApren.objects.get(id=sitapren.text)
                        except SitApren.DoesNotExist:
                            self.logger.info('Importación programación ==error==> No existe SitApren: ' + sitapren.text)

                        newCEProgsec.sitapren_set.add(sp)

    def __crearCuadernosProf(self, cuadernos):
        # Recorre los cuadernos de una programación
        for cuaderno in cuadernos:
            for elemento in cuaderno:
                if elemento.tag == 'datos':
                    newCuadernoProf = CuadernoProf(
                        vmin=elemento.find('vmin').text,
                        vmax=elemento.find('vmax').text,
                        vista=elemento.find('vista').text,
                        borrado=elemento.find('borrado').text,
                        log=elemento.find('log').text,
                        grupo_id=elemento.find('grupo_id').text,
                        ge_id=self.gep_id,
                        psec_id=self.new_progsec_id
                    )
                    newCuadernoProf.save()

                elif elemento.tag == 'alumnos':
                    self.__crearAlumnosDeCuadernoProf(alumnos=elemento, newCuadernoProf=newCuadernoProf)  # OK
                elif elemento.tag == 'escalas_cp':
                    self.__crearEscalascpDeCuadernoProf(escalascp=elemento, newCuadernoProf=newCuadernoProf.id)  # OK
                elif elemento.tag == 'cal_alumnos':
                    self.__crearCalAlumnos(calalumnos=elemento)

    def __crearAlumnosDeCuadernoProf(self, alumnos, newCuadernoProf):
        # Crea los alumnos asociados al cuaderno del profesor de la programación
        for alumno in alumnos:
            for elemento in alumno:
                if elemento.tag == 'datos':
                    try:
                        newCuadernoProf.objects.add(
                            Gauser_extra_programaciones.objects.get(id=elemento.find('gauser_extra_id')))
                    except Gauser_extra_programaciones.DoesNotExist:
                        self.logger.info(
                            'Importación programación ==error==> No existe alumno para CuadernoProf: ' + elemento.find(
                                'gauser_extra_id'))

    def __crearEscalascpDeCuadernoProf(self, escalascp, newCuadernoProf_id):
        # Recorrer escalas_cp del cuadernoprof de la programación
        for escala in escalascp:
            for elemento in escala:
                if elemento.tag == 'datos':
                    newEscalaCP = EscalaCP(
                        tipo=elemento.find('tipo').text,
                        nombre=elemento.find('nombre').text,
                        cp_id=newCuadernoProf_id,
                        ieval_id=elemento.find('ieval_id').text
                    )
                    newEscalaCP.save()
                elif elemento.tag == 'escalacpvalores':
                    self.__crearEscalascpValores(escalascp=elemento, newEscalaCP_id=newEscalaCP.id)
                elif elemento.tag == 'cal_alumnos_valor':
                    self.__crearCalAlumnos(calalumnos=elemento, newEscalaCP_id=newEscalaCP.id, newCuadernoProf_id=newCuadernoProf_id)


    def __crearEscalascpValores(self, escalascp, newEscalaCP_id):
        # Recorrer Escalascp Valores de escalas del cuadernoprof de la programación
        for escala in escalascp:
            if escala.tag == 'escalacpvalor':
                for elemento in escala:
                    if elemento.tag == 'datos':
                        newEscalaCPValor = EscalaCPvalor(
                            x=elemento.find('x').text,
                            y=elemento.find('y').text,
                            texto_cualitativo=elemento.find('texto_cualitativo').text,
                            # valor=
                            ecp_id=newEscalaCP_id
                        )
                        newEscalaCPValor.save()

    def __crearCalAlumnos(self, calalumnos, newEscalaCP_id, newCuadernoProf_id):
        # Recorrer cal_alumnos del cuadernoprof de la programación
        for cal in calalumnos:
            if cal.tag == 'datos':
                datos += str(cal.find('obs').text) + '<br>' \
                         + str(cal.find('alumno_id').text) + '<br>' \
                         + str(cal.find('cie_id').text) + '<br>' \
                         + str(cal.find('cp_id').text) + '<br>' \
                         + str(cal.find('ecp_id').text) + '<br>'
            elif cal.tag == 'cal_alumnos_valor':
                datos += self.__crearCalAlumnosValor(calalumvalor=cal)


    def __crearCalAlumnosValor(self, calalumvalor):
        # Recorrer calalumvalor de calalum del cuadernoprof del al programación
        datos = calalumvalor.tag + ':' + calalumvalor.get('model') + '<br>'
        for valor in calalumvalor:
            datos += valor.tag + ': ' + valor.get('id') + '<br>'
            for elemento in valor:
                if elemento.tag == 'datos':
                    datos += str(elemento.find('obs').text) + '<br>' \
                             + str(elemento.find('ca_id').text) + '<br>' \
                             + str(elemento.find('ecpv_id').text) + '<br>'
        return datos
