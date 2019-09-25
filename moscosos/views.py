from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.timezone import datetime
from django.template.loader import render_to_string

from autenticar.control_acceso import LogGauss, permiso_required, gauss_required
from entidades.models import Gauser_extra, Ronda
from mensajes.models import Aviso
from moscosos.models import Moscoso, ConfiguraMoscosos, FechaNoPermitida

# Create your views here.

@permiso_required('acceso_moscosos')
def moscosos(request):
    g_e = request.session['gauser_extra']
    cm, c = ConfiguraMoscosos.objects.get_or_create(ronda=g_e.ronda)
    mes = datetime.today().month
    if cm.autoriza == g_e:
        propios = Moscoso.objects.filter(cm=cm, fecha__month=mes).order_by('fecha')
    else:
        propios = Moscoso.objects.filter(cm=cm, solicita=g_e)

    if request.method == 'POST':
        pass

    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nuevo', 'title': 'Solicitar un día de libre disposición',
              'permiso': 'acceso_moscosos'},
             ),
        'formname': 'moscosos',
        'cm': cm,
        'moscosos': Moscoso.objects.filter(cm=cm, fecha__month=mes).order_by('fecha'),
        'propios': propios,
        'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False)
    }
    return render(request, "moscosos.html", respuesta)


@login_required()
def ajax_moscosos(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        autorizado = g_e.has_permiso(request.POST['p'])
        if request.POST['action'] == 'campo_update' and autorizado:
            try:
                clase = eval(request.POST['objname'])
                objeto = clase.objects.get(id=request.POST['objid'])
                campo = request.POST['campo']
                valor = request.POST['valor']
                if campo == 'autoriza':
                    valor = Gauser_extra.objects.get(id=valor)
                elif campo == 'fecha':
                    valor = datetime.strptime(valor, "%d/%m/%Y")
                    num_moscosos_fecha = Moscoso.objects.filter(cm=objeto.cm, fecha=valor, estado='ACE').count()
                    if num_moscosos_fecha >= objeto.cm.max_personas_day:
                        mensaje = 'Fecha no posible. Ya se ha concedido a %s personas.' % (objeto.cm.num_moscosos_fecha)
                        return JsonResponse({'ok': True, 'mensaje': mensaje})
                    objeto.estado = 'PEN'
                setattr(objeto, campo, valor)
                objeto.save()
                return JsonResponse({'ok': True})
            except:
                return JsonResponse({'ok': False})
        elif request.POST['action'] == 'add_moscoso' and g_e.has_permiso('acceso_moscosos'):
            try:
                cm = ConfiguraMoscosos.objects.get(ronda=g_e.ronda)
                Moscoso.objects.filter(cm=cm, solicita=g_e, estado='PRO').delete()
                num_solicitudes = Moscoso.objects.filter(cm=cm, solicita=g_e).count()
                if num_solicitudes < cm.max_persona:
                    moscoso = Moscoso.objects.create(cm=cm, solicita=g_e, observaciones='', fecha=datetime.today())
                    html = render_to_string('moscosos_content.html', {'moscoso': moscoso})
                    return JsonResponse({'ok': True, 'html': html})
                else:
                    html = '<h2>No es posible cursar la petición.</h2><h3>Ya has solicitado el máximo número de días posible.</h3>'
                    return JsonResponse({'ok': True, 'html': html})
            except:
                return JsonResponse({'ok': False})

@permiso_required('acceso_moscosos')
def calendario_moscosos(request):
    if request.method == 'GET':
        ronda = Ronda.objects.get(id=request.GET['r'])
        cm = ConfiguraMoscosos.objects.get(ronda=ronda)
        mes = datetime.today().month
    elif request.method == 'POST':
        ronda = Ronda.objects.get(id=request.POST['r'])
        cm = ConfiguraMoscosos.objects.get(ronda=ronda)
        mes = datetime.today().month

    respuesta = {
        'moscosos': Moscoso.objects.filter(cm=cm, fecha__month=mes).order_by('fecha'),
    }
    return render(request, "moscosos.html", respuesta)