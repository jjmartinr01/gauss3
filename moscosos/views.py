from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from autenticar.control_acceso import LogGauss, permiso_required, gauss_required
from entidades.models import Gauser_extra
from mensajes.models import Aviso
from moscosos.models import Moscoso, ConfiguraMoscosos, FechaNoPermitida

# Create your views here.

@permiso_required('acceso_moscosos')
def moscosos(request):
    g_e = request.session['gauser_extra']
    cm, c = ConfiguraMoscosos.objects.get_or_create(ronda=g_e.ronda)
    moscosos = Moscoso.objects.filter(cm=cm)

    if request.method == 'POST':
        miembro_unidad = Gauser_extra.objects.get(id=request.POST['miembro_unidad'])
        if request.POST['action'] != 'miembro_unidad':
            form2 = Gauser_extra_mis_datos_Form(request.POST, request.FILES, instance=miembro_unidad)
            if form2.is_valid():
                form2.save()
            else:
                crear_aviso(request, False, form2.errors)

    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nuevo', 'title': 'Solicitar un día de libre disposición',
              'permiso': 'acceso_moscosos'},
             ),
        'formname': 'moscosos',
        'cm': cm,
        'moscosos': moscosos,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)
    }
    return render(request, "moscosos.html", respuesta)


@login_required()
def ajax_moscosos(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        if request.POST['action'] == 'campo_gauser':
            try:
                ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge_id'])
                g = ge.gauser
                setattr(g, request.POST['campo'], request.POST['valor'])
                g.save()
                if ge == g_e:
                    request.session['gauser_extra'] = Gauser_extra.objects.get(id=ge.id)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'campo_gauser_extra':
            try:
                ge = Gauser_extra.objects.get(ronda=g_e.ronda, id=request.POST['ge_id'])
                setattr(ge, request.POST['campo'], request.POST['valor'])
                ge.save()
                if ge == g_e:
                    request.session['gauser_extra'] = Gauser_extra.objects.get(id=ge.id)
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})