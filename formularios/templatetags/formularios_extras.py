# -*- coding: utf-8 -*-
from django.template import Library
from formularios.models import GSITIPOS, GformSection, GformSectionInput, GformResponde, GformRespondeInput, \
    EvalFunPract

register = Library()


@register.filter
def get_cal_dim(efpa, dim):
    return efpa.cal_dim(dim)

@register.filter
def get_cal_subdim(efpa, subdim):
    return efpa.cal_subdim(subdim)

@register.filter
def get_efps(pefp):
    return EvalFunPract.objects.filter(entidad=pefp.evalfunpract.entidad)

@register.filter
def cuestiones_grupo(ginputs, grupo):
    return ginputs.filter(grupo=grupo)


@register.filter
def hay_preguntas(gform, grupo):
    return gform.ginput_set.filter(grupo=grupo).count() > 0


@register.filter
def gsitipos(gfsi):
    return GSITIPOS


@register.filter
def totalgfsis(gfsi):
    return GformSectionInput.objects.filter(gformsection__gform=gfsi.gformsection.gform).count()


@register.filter
def elvalues(gfsi):
    return ['%s' % i for i in range(int(gfsi.elmin), int(gfsi.elmax + 1))]


@register.filter
def get_rfirma(gfsi, gformresponde):
    try:
        return GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rfirma
    except:
        return ''


@register.filter
def get_rentero(gfsi, gformresponde):
    try:
        if str(GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rentero).isdigit():
            return GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rentero
        else:
            return 0
    except:
        return 0

@register.filter
def get_rtexto(gfsi, gformresponde):
    try:
        return GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rtexto
    except:
        return ''


@register.filter
def get_ifchecked(gfsio, gformresponde):
    gfsi = gfsio.gformsectioninput
    try:
        if gfsio in GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).ropciones.all():
            return 'checked'
        else:
            return ''
    except:
        return ''


@register.filter
def get_fich_name(gfsi, gformresponde):
    try:
        filename = GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rarchivo.name
        return filename.rpartition('/')[2]
    except:
        return ''


@register.filter
def get_el_value(gfsi, gformresponde):
    try:
        return GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rentero
    except:
        return ''

@register.filter
def efpr_observaciones(efpr, actor):
    return getattr(efpr, 'obs%s' % actor)

@register.filter
def respuesta(efpr, actor):
    return getattr(efpr, actor)

@register.filter
def checked_if_igual_a(a, b):
    try:
        if int(a) == int(b):
            return 'checked=checked'
        else:
            return ''
    except:
        return ''


@register.filter
def get_fin(gfsi, gformresponde):
    try:
        return GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rfirma_nombre
    except:
        return ''


@register.filter
def get_fic(gfsi, gformresponde):
    try:
        return GformRespondeInput.objects.get(gfsi=gfsi, gformresponde=gformresponde).rfirma_cargo
    except:
        return ''



@register.filter
def get_gfrs_eval(gfd):
    gfrs = GformResponde.objects.filter(g_e=gfd.destinatario, gform=gfd.gform)
    if gfrs.count() == 0:
        gfrs = [GformResponde.objects.create(g_e=gfd.destinatario, gform=gfd.gform)]
    return gfrs


@register.filter
def get_gfrs(gfrs, gform):
    return gfrs.filter(gform=gform)


@register.filter
def get_chartlabels(gfsi):
    return [gfsio.opcion for gfsio in gfsi.gformsectioninputops_set.all()]


@register.filter
def get_chartdata(gfsi):
    backgroundColor_list = ['rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(255, 206, 86, 0.2)',
                            'rgba(75, 192, 192, 0.2)', 'rgba(153, 102, 255, 0.2)', 'rgba(255, 159, 64, 0.2)']
    borderColor_list = ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)', 'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)']
    labels = []
    data = []
    backgroundColor = []
    borderColor = []
    n = 0
    for gfsio in gfsi.gformsectioninputops_set.all():
        labels.append(gfsio.opcion.strip())
        data.append(gfsi.gformrespondeinput_set.filter(ropciones__in=[gfsio]).count())
        backgroundColor.append(backgroundColor_list[n % len(backgroundColor_list)])
        borderColor.append(borderColor_list[n % len(borderColor_list)])
        n += 1
    return {'labels': labels, 'datasets': [{'label': '', 'data': data, 'backgroundColor': backgroundColor,
                                            'borderColor': borderColor, 'borderWidth': 1}]}

@register.filter
def get_chartdatalinear(gfsi):
    backgroundColor_list = ['rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(255, 206, 86, 0.2)',
                            'rgba(75, 192, 192, 0.2)', 'rgba(153, 102, 255, 0.2)', 'rgba(255, 159, 64, 0.2)']
    borderColor_list = ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)', 'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)']
    if gfsi.tipo == 'EL':
        labels = [i for i in range(gfsi.elmin, gfsi.elmax + 1)]
    else:
        gfris = gfsi.gformrespondeinput_set.all().order_by('rentero')
        labels = list(set([gfri.rentero for gfri in gfris if str(gfri.rentero).isdigit()]))
        # labels = list(set([gfri.rentero for gfri in gfsi.gformrespondeinput_set.all().order_by('rentero')]))
        # labels = []
        # valores = list(set([respuesta.rentero for respuesta in gfsi.gformrespondeinput_set.all().order_by('rentero')]))
        # for valor in valores:
        #     labels.append(valor)
    data = []
    backgroundColor = []
    borderColor = []
    n = 0
    for valor in labels:
        data.append(gfsi.gformrespondeinput_set.filter(rentero=valor).count())
        backgroundColor.append(backgroundColor_list[n % len(backgroundColor_list)])
        borderColor.append(borderColor_list[n % len(borderColor_list)])
        n += 1
    return {'labels': labels, 'datasets': [{'label': 'Respuestas a la pregunta %s' % gfsi.orden, 'data': data, 'backgroundColor': backgroundColor,
                                            'borderColor': borderColor, 'borderWidth': 1}]}