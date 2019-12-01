from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.utils.timezone import datetime, timedelta
from django.db.models import Q
from autenticar.control_acceso import LogGauss, permiso_required, gauss_required
from mensajes.models import Aviso
from federaciones.models import Federacion, Federado


# Create your views here.


# @permiso_required('acceso_configura_federacion')
def configura_federacion(request):
    g_e = request.session['gauser_extra']
    federaciones = Federacion.objects.filter(entidad=g_e.ronda.entidad)

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'crear_federacion':
            f = Federacion.objects.create(entidad=g_e.ronda.entidad)
            html = render_to_string('configura_federacion_accordion.html', {'federacion': f})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'borra_federacion':
            if g_e.has_permiso('borra_sus_federaciones'):
                f = Federacion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['federacion'])
                federacion = f.id
                f.delete()
                return JsonResponse({'ok': True, 'federacion': federacion})
            else:
                return JsonResponse({'ok': False})
        elif action == 'open_accordion_federacion':
            f = Federacion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['federacion'])
            html = render_to_string('configura_federacion_accordion_content.html', {'federacion': f, 'g_e': g_e})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'update_campo':
            try:
                federacion = Federacion.objects.get(id=request.POST['federacion'])
                if g_e.has_permiso('edita_sus_federaciones'):
                    campo = request.POST['campo']
                    valor = request.POST['valor']
                    setattr(federacion, campo, valor)
                    federacion.save()
                    return JsonResponse({'ok': True, 'campo': campo, 'valor': valor})
                else:
                    return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la federacion."})
            except:
                return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la federacion."})

    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'title': 'Aceptar los cambios realizados',
              'permiso': 'libre'},
             ),
        'formname': 'configura_federacion',
        'g_e': g_e,
        'federaciones': federaciones,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)
    }
    return render(request, "configura_federacion.html", respuesta)


@permiso_required('acceso_configura_federacion')
def ajax_configura_federacion(request):
    pass


@permiso_required('acceso_inscribir_federacion')
def inscribir_federacion(request):
    g_e = request.session['gauser_extra']
    federados = Federado.objects.filter(entidad=g_e.ronda.entidad)
    for federado in federados.filter(Q(acepta_entidad=False) | Q(acepta_federacion=False)):
        if (datetime.today() - federado.modificado) > timedelta(7):
            federado.delete()

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'solicitud_inscripcion':
            try:
                federacion = Federacion.objects.get(code_inscribir=request.POST['code'].strip())
                if federacion.entidad != g_e.ronda.entidad:
                    federado, c = Federado.objects.get_or_create(federacion=federacion, entidad=g_e.ronda.entidad)
                    federado.acepta_entidad = True
                    federado.observaciones += '<br>Se solicita federarse en %s' % federacion
                    federado.save()
                else:
                    return JsonResponse({'ok': False, 'mensaje': 'No es posible federarse a la propia entidad.'})
                federados = Federado.objects.filter(entidad=g_e.ronda.entidad)
                html = render_to_string('inscribir_federacion_federados.html', {'federados': federados})
                return JsonResponse({'ok': True, 'html': html, 'federacion': federacion.entidad.name})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'El código no pertenece a una federación.'})
        elif action == 'open_accordion_federacion':
            f = Federacion.objects.get(entidad=g_e.ronda.entidad, id=request.POST['federacion'])
            html = render_to_string('configura_federacion_accordion_content.html', {'federacion': f, 'g_e': g_e})
            return JsonResponse({'ok': True, 'html': html})
        elif action == 'acepta_entidad':
            try:
                federado = Federado.objects.get(id=request.POST['federado'])
                acepta = {'true': True, 'false': False}[request.POST['acepta']]
                if g_e.has_permiso('edita_sus_federaciones'):
                    federado.acepta_entidad = acepta
                    federado.save()
                    return JsonResponse({'ok': True, 'acepta_entidad': federado.acepta_entidad})
                else:
                    return JsonResponse({'ok': False, 'mensaje': "No tienes permisos para hacer esta operación."})
            except:
                return JsonResponse({'ok': False, 'mensaje': "Error al tratar de editar la federacion."})

    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'title': 'Aceptar los cambios realizados',
              'permiso': 'libre'},
             ),
        'formname': 'inscribir_federacion',
        'g_e': g_e,
        'federados': federados,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)
    }
    return render(request, "inscribir_federacion.html", respuesta)


#################### ------------------------------ ####################
@permiso_required('acceso_cuotas_federacion')
def cuotas_federacion(request):
    pass


@permiso_required('acceso_cuotas_federacion')
def ajax_cuotas_federacion(request):
    pass


#################### ------------------------------ ####################
@permiso_required('acceso_documentos_federacion')
def documentos_federacion(request):
    pass


@permiso_required('acceso_documentos_federacion')
def ajax_documentos_federacion(request):
    pass
