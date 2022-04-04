from django.utils.timezone import datetime


def progsec2json(progsec):
    p = {
        'progsec': progsec.id,
        'pga': progsec.pga.id,
        'nombre': ' progsec.nombre ',
        'gep': progsec.gep.id,
        'areamateria': progsec.areamateria.id,
        'departamento': progsec.departamento.id,
        'inicio_clases': ' progsec.inicio_clases|date:"Y-m-d" ',
        'fin_clases': ' progsec.fin_clases|date:"Y-m-d" ',
        'es_copia_de': ' progsec.es_copia_de.id ',
        'procdiversidad': ' progsec.procdiversidad ',
        'docprogsec': [],
        'ceprogsec': [],
        'librorecurso': [],
        'actexcom': [],
        'saberbas': []
    }

    for dp in progsec.docprogsec_set.all():
        p.docprogsec.append({'gep': dp.gep.id, 'permiso': ' dp.permiso '})

    for ceps in progsec.ceprogsec_set.all():
        cevprogsec = []
        for cevps in ceps.cevprogsec_set.all():
            cevprogsec.append({'cev': cevps.cev.id, 'valor': cevps.valor})
        p.ceprogsec.append({'ce': ceps.ce.id, 'valor': ceps.valor, 'cevprogsec': cevprogsec})

    for lr in progsec.librorecurso_set.all():
        p.librorecurso.append(
            {'nombre': lr.nombre, 'isbn': lr.isbn, 'observaciones': lr.observaciones,
             'doc_file': lr.doc_file.url, 'content_type': lr.content_type})

    for aexc in progsec.actexcom_set.all():
        p.librorecurso.append({
            'nombre': aexc.nombre,
            'observaciones': aexc.observaciones,
            'inicio': datetime.strftime(aexc.inicio, "Y-m-d"),
            'fin': datetime.strftime(aexc.fin, "Y-m-d")})


    for sb in progsec.saberbas_set.all():
        sitaprens=[]
        for sap in sb.sitapren_set.all():
            asaprens = []
            for asapren in sap.actsitapren_set.all():
            sitaprens.append({'nombre':sap.nombre, 'objetivo': sap.objetivo,
                              'ceps': list(sap.ceps.all().values_list('id', flat=True))})
        librorecursos = list(sb.librorecursos.all().values_list('id', flat=True))
        actexcoms = list(sb.actexcoms.all().values_list('id', flat=True))
        p.saberbas.append()
    {
        'orden': sb.orden,
        'nombre': ' sb.nombre ',
        'comienzo': ' sb.comienzo|date:"Y-m-d" ',
        'periodos': sb.periodos,
        'librorecursos': librorecursos,
        'actexcoms': actexcoms,
    'sitaprens': [
        for sap in sb.sitapren_set.all():
    {
        'nombre': ' sap.nombre ',
        'objetivo': ' sap.objetivo ',
        'ceps': [
            for c in sap.ceps.all():
    c.id,

    ],
    'actsitaprens': [
        for asapren in sap.actsitapren_set.all():
    {
        'nombre': ' asapren.nombre ',
        'description': ' asapren.description ',
        'producto': ' asapren.producto ',
        'instrevals': [
            for ieval in asapren.instreval_set.all():
    {
        'tipo': ' ieval.tipo ',
        'nombre': ' ieval.nombre '
                  'criinstrevals': [
        for cieval in ieval.criinstreval_set.all():
    {
        'peso': cieval.peso,
        'cevps': cieval.cevps.id
    },