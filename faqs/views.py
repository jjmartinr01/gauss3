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
    faqssections = FaqSection.objects.filter(entidad=g_e.ronda.entidad, borrada=False)

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'add_seccion' and g_e.has_permiso('crea_secciones_faqs'):
            try:
                fs = FaqSection.objects.create(entidad=g_e.ronda.entidad, nombre='Nueva sección')
                html = render_to_string('configura_faqs_secciones.html', {'s': fs})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'No se ha podido crear la sección.'})
        elif action == 'open_accordion_fsection':
            try:
                fs = FaqSection.objects.get(entidad=g_e.ronda.entidad, id=request.POST['fs'], borrada=False)
                html = render_to_string('configura_faqs_secciones_content.html', {'s': fs, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'No se puede abrir la sección solicitada.'})
        elif action == 'borrar_seccion' and g_e.has_permiso('crea_secciones_faqs'):
            try:
                fs = FaqSection.objects.get(id=request.POST['seccion'], entidad=g_e.ronda.entidad)
                if fs.num_preguntas == 0:
                    fs.borrada = True
                    fs.save()
                    return JsonResponse({'ok': True, 'fs_id': fs.id})
                else:
                    return JsonResponse(
                        {'ok': False, 'mensaje': 'No se puede borrar una sección si contiene preguntas.'})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha procido un error que ha impedido el borrado.'})
        elif action == 'edit_seccion' and g_e.has_permiso('crea_secciones_faqs'):
            try:
                fs = FaqSection.objects.get(entidad=g_e.ronda.entidad, id=request.POST['fs'], borrada=False)
                fs.nombre = request.POST['nombre']
                fs.save()
                return JsonResponse({'ok': True, 'nombre': fs.nombre, 'fs_id': fs.id})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'No se puede abrir la sección solicitada.'})
        elif action == 'add_faq' and g_e.has_permiso('crea_faqs_entidad'):
            try:
                fs = FaqSection.objects.get(entidad=g_e.ronda.entidad, id=request.POST['fs'], borrada=False)
                p = FaqEntidad.objects.create(faqsection=fs)
                html = render_to_string('configura_faqs_secciones_content_pregunta.html', {'g_e': g_e, 'p': p})
                return JsonResponse({'ok': True, 'html': html, 'fs': fs.id, 'num_preguntas': fs.num_preguntas})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'No has hecho la petición correctamente.'})
        elif action == 'del_faq' and g_e.has_permiso('crea_faqs_entidad'):
            try:
                p = FaqEntidad.objects.get(id=request.POST['id'], faqsection__entidad=g_e.ronda.entidad)
                fs = p.faqsection
                p.borrada = True
                p.publicada = False
                p.save()
                return JsonResponse({'ok': True, 'p_id': p.id, 'num_preguntas': fs.num_preguntas, 'fs': fs.id})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'No has hecho la petición correctamente.'})
        elif action == 'update_input_faq' and g_e.has_permiso('edita_faqs_entidad'):
            try:
                p = FaqEntidad.objects.get(id=request.POST['id'], faqsection__entidad=g_e.ronda.entidad, borrada=False)
                p.pregunta = request.POST['texto']
                p.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'update_respuesta' and g_e.has_permiso('edita_faqs_entidad'):
            try:
                p = FaqEntidad.objects.get(id=request.POST['id'], faqsection__entidad=g_e.ronda.entidad, borrada=False)
                p.respuesta = request.POST['texto']
                p.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif action == 'change_pub_faq' and g_e.has_permiso('publica_faqs_entidad'):
            try:
                p = FaqEntidad.objects.get(id=request.POST['id'], faqsection__entidad=g_e.ronda.entidad, borrada=False)
                p.publicada = not p.publicada
                p.save()
                fs = p.faqsection
                return JsonResponse({'ok': True, 'publicar': ['No', 'Sí'][p.publicada], 'p': p.id,
                                     'num_preguntas_pub': fs.num_preguntas_pub, 'fs': fs.id})
            except:
                return JsonResponse({'ok': False})
        else:
            return JsonResponse({'ok': False, 'mensaje': 'No se ha podido llevar a cabo la operación solicitada.'})

    return render(request, "configura_faqs.html",
                  {
                      'formname': 'configura_faqs',
                      'g_e': g_e,
                      'faqssections': faqssections,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@permiso_required('acceso_faqs_gauss')
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


@permiso_required('acceso_faqs_entidad')
def faqs_entidad(request):
    g_e = request.session['gauser_extra']
    faqssections = FaqSection.objects.filter(entidad=g_e.ronda.entidad, borrada=False)

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'open_accordion_fsection':
            try:
                fs = FaqSection.objects.get(entidad=g_e.ronda.entidad, id=request.POST['fs'], borrada=False)
                html = render_to_string('faqs_entidad_seccion_content.html', {'s': fs, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'No se puede abrir la sección solicitada.'})

    return render(request, "faqs_entidad.html",
                  {
                      'formname': 'faqs_entidad',
                      'faqssections': faqssections,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })


@permiso_required('acceso_faqs_borradas')
def faqs_borradas(request):
    g_e = request.session['gauser_extra']
    faqssections = FaqSection.objects.filter(entidad=g_e.ronda.entidad)

    if request.method == 'POST' and request.is_ajax():
        action = request.POST['action']
        if action == 'open_accordion_fsection':
            try:
                fs = FaqSection.objects.get(entidad=g_e.ronda.entidad, id=request.POST['fs'], borrada=False)
                html = render_to_string('configura_faqs_borradas_secciones_content.html', {'s': fs, 'g_e': g_e})
                return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'No se puede abrir la sección solicitada.'})
        elif action == 'unborrar_seccion':
            try:
                fs = FaqSection.objects.get(id=request.POST['seccion'], entidad=g_e.ronda.entidad)
                fs.borrada = False
                fs.save()
                return JsonResponse({'ok': True, 'fs_id': fs.id})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'Se ha procido un error que ha impedido el borrado.'})
        elif action == 'undel_faq' and g_e.has_permiso('crea_faqs_entidad'):
            try:
                p = FaqEntidad.objects.get(id=request.POST['id'], faqsection__entidad=g_e.ronda.entidad)
                fs = p.faqsection
                p.borrada = False
                p.publicada = False
                p.save()
                return JsonResponse({'ok': True, 'p': p.id, 'num_preguntas': fs.num_preguntas,
                                     'num_preguntas_pub': fs.num_preguntas_pub, 'fs': fs.id,
                                     'num_preguntas_borradas': fs.num_preguntas_borradas,})
            except:
                return JsonResponse({'ok': False, 'mensaje': 'No has hecho la petición correctamente.'})
        else:
            return JsonResponse({'ok': False, 'mensaje': 'No se ha podido llevar a cabo la operación solicitada.'})

    return render(request, "configura_faqs_borradas.html",
                  {
                      'formname': 'configura_faqs',
                      'g_e': g_e,
                      'faqssections': faqssections,
                      'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                  })
