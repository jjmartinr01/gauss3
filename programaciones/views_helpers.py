from programaciones.models import *
from entidades.models import EntidadExtra
from django.http import HttpResponse

def set_ge_gep_ies_pga(request):
    
    g_e = request.session['gauser_extra']

    try:
        ies = request.session['ronda'].entidad.entidadextra.depende_de
    except:
        # Esta excepción ocurre en centros que no se cargan de Racima, por ejemplo el CRIE
        EntidadExtra.objects.get_or_create(entidad=g_e.ronda.entidad)
        ies = request.session['ronda'].entidad.entidadextra.depende_de
    if ies:
        try:
            g_eies = Gauser_extra.objects.get(gauser=g_e.gauser, ronda=ies.ronda)
            g_ep, c = Gauser_extra_programaciones.objects.get_or_create(ge=g_eies)
            request.session['es_sies'] = True
        except:
            return HttpResponse('Error. No tienes usuario en tu IES. Comunica incidencia al Administrador')
    else:
        g_ep, c = Gauser_extra_programaciones.objects.get_or_create(ge=g_e)
        request.session['es_sies'] = False
    if c:
        g_ep.puesto = g_e.puesto
        g_ep.save()
    
    if ies:
        pga, c = PGA.objects.get_or_create(ronda=ies.ronda)
    else:
        pga, c = PGA.objects.get_or_create(ronda=g_e.ronda)
    
    return (g_e, g_ep, ies, pga)