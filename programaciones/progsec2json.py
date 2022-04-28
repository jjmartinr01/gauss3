import json
from django.utils.timezone import datetime


def progsec2json(progsec):
    p = {
        'progsec': progsec.id,
        'pga': progsec.pga.id,
        'nombre': progsec.nombre,
        'gep': progsec.gep.id,
        'areamateria': progsec.areamateria.id,
        'departamento': progsec.departamento.id,
        'inicio_clases': datetime.strftime(progsec.inicio_clases, "%Y-%m-%d"),
        'fin_clases': datetime.strftime(progsec.fin_clases, "%Y-%m-%d"),
        'es_copia_de': progsec.es_copia_de.id,
        'procdiversidad': progsec.procdiversidad,
        'docprogsec': [],
        'ceprogsec': [],
        'librorecurso': [],
        'actexcom': [],
        'saberbas': []
    }

    for dp in progsec.docprogsec_set.all():
        p['docprogsec'].append({'gep': dp.gep.id, 'permiso': ' dp.permiso '})

    for ceps in progsec.ceprogsec_set.all():
        cevprogsec = []
        for cevps in ceps.cevprogsec_set.all():
            cevprogsec.append({'cev': cevps.cev.id, 'valor': cevps.valor})
        p['ceprogsec'].append({'ce': ceps.ce.id, 'valor': ceps.valor, 'cevprogsec': cevprogsec})

    for lr in progsec.librorecurso_set.all():
        p['librorecurso'].append(
            {'nombre': lr.nombre, 'isbn': lr.isbn, 'observaciones': lr.observaciones,
             'doc_file': lr.doc_file.url, 'content_type': lr.content_type})

    for aexc in progsec.actexcom_set.all():
        p['actexcom'].append({
            'nombre': aexc.nombre,
            'observaciones': aexc.observaciones,
            'inicio': datetime.strftime(aexc.inicio, "%Y-%m-%d"),
            'fin': datetime.strftime(aexc.fin, "%Y-%m-%d")})

    for sb in progsec.saberbas_set.all():
        sb_dic = {'psec': sb.psec.id, 'orden': sb.orden, 'nombre': sb.nombre, 'comienzo': sb.comienzo,
                  'periodos': sb.periodos, 'librorecursos': [], 'actexcoms': [], 'saprens': []}
        for lr in sb.librorecursos.all():
            sb_dic['librorecursos'].append(lr.id)
        for aexc in sb.actexcoms.all():
            sb_dic['actexcoms'].append(aexc.id)
        for sap in sb.sitapren_set.all():
            sap_dic = {'nombre': sap.nombre, 'objetivo': sap.objetivo, 'ceps': [], 'asaprens': []}
            for cep in sap.ceps.all():
                sap_dic['ceps'].append(cep.id)
            for asapren in sap.actsitapren_set.all():
                asapren_dic = {'nombre': asapren.nombre, 'descripcion': asapren.descripcion,
                               'producto': asapren.producto, 'instrevals': []}
                for ieval in asapren.instreval_set.all():
                    ieval_dic = {'tipo': ieval.tipo, 'nombre': ieval.nombre, 'criinstrevals': []}
                    for crieval in ieval.criinstreval_set.all():
                        ieval_dic['criinstrevals'].append({'cevps': crieval.cevps.id, 'peso': crieval.peso})
                    asapren_dic['instrevals'].append(ieval_dic)
                sap_dic['asaprens'].append(asapren_dic)
            sb_dic['saprens'].append(sap_dic)
        p['saberbas'].append(sb_dic)

    return json.dumps(p)
