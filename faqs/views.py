from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string

from autenticar.control_acceso import permiso_required
from mensajes.models import Aviso
from faqs.models import FaqSection, FaqGauss, FaqEntidad


# Create your views here.

@permiso_required('acceso_configura_faqs')
def configura_faqs(request):
    g_e = request.session['gauser_extra']
    faqssections = FaqSection.objects.filter(entidad=g_e.ronda.entidad)

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'add_seccion' and g_e.has_permiso('crea_faqs_gauss'):
            try:
                fs = FaqSection.objects.create(entidad=g_e.ronda.entidad, nombre='Nueva sección')
                html = render_to_string('configura_faqs_secciones_tr.html', {'s': fs})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'No se ha podido crear la sección.'})
        elif action == 'borrar_seccion' and g_e.has_permiso('crea_faqs_gauss'):
            try:
                fs = FaqSection.objects.get(id=request.POST['seccion'], entidad=g_e.ronda.entidad)
                if fs.num_preguntas == 0:
                    fs_id = fs.id
                    fs.delete()
                    return JsonResponse({'ok': True, 'fs_id': fs_id})
                else:
                    return JsonResponse(
                        {'ok': False, 'mensaje': 'No se puede borrar una sección si contiene preguntas.'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha procido un error que ha impedido el borrado.'})
        else:
            return JsonResponse({'ok': False, 'mensaje': 'No se ha podido llevar a cabo la operación solicitada.'})

    return render(request, "configura_faqs.html",
                  {
                      'formname': 'configura_faqs',
                      'g_e': g_e,
                      'faqssections': faqssections,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


# @permiso_required('acceso_faqs_gauss')
def faqs_gauss(request):
    g_e = request.session['gauser_extra']

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'libro_registros':
            pass

    return render(request, "faqs_gauss.html",
                  {
                      'formname': 'faqs_gauss',
                      'g_e': g_e,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


# @permiso_required('acceso_faqs_entidad')
def faqs_entidad(request):
    g_e = request.session['gauser_extra']

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'libro_registros':
            pass

    return render(request, "faqs_entidad.html",
                  {
                      'formname': 'faqs_entidad',
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })
