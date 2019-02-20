# -*- coding: utf-8 -*-
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
# from django.template import RequestContext
from django import forms
from django.forms import ModelForm
from django.db.models import Q
from django.template.loader import render_to_string
from registro.models import Registro, Fichero
from gauss.rutas import *
# from django.views.decorators.csrf import csrf_exempt
# import simplejson as json
from django.http import HttpResponse
# from django.forms.formsets import formset_factory
from datetime import datetime
# from django.core.mail import EmailMessage
from autenticar.control_acceso import permiso_required
import mimetypes

mimetypes.add_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx')


class RegistroForm(ModelForm):
    class Meta:
        model = Registro
        fields = ('asunto', 'texto', 'receptor', 'tipo', 'emisor', 'fecha')
        widgets = {
            'asunto': forms.TextInput(attrs={'size': '100', 'class': 'detectar'}),
            'receptor': forms.TextInput(attrs={'size': '50', 'class': 'detectar'}),
            'emisor': forms.TextInput(attrs={'size': '50', 'class': 'detectar'}),
            'tipo': forms.Select(attrs={'class': 'detectar'}),
            'texto': forms.Textarea(attrs={'cols': 80, 'rows': 8}),
            'fecha': forms.TextInput(attrs={'size': '10', 'value': datetime.today().strftime("%d/%m/%Y")}),
        }


# @permiso_required('acceso_absentismo')
def registro(request):
    g_e = request.session['gauser_extra']
    registros = Registro.objects.filter(entidad=g_e.ronda.entidad).order_by('num_id').reverse()[:8]

    if request.method == 'POST':
        if request.POST['action'] == 'save_registro' and g_e.has_permiso('crea_registros'):
            try:
                num_id = Registro.objects.filter(entidad=g_e.ronda.entidad).latest('num_id').num_id + 1
            except:
                num_id = 1000
            # Rellenamos en un nuevo registro los datos que no se piden en el formulario
            nuevo_registro = Registro(entidad=g_e.ronda.entidad, num_id=num_id, registrador=g_e.gauser)
            # Completamos el formulario con la instancia del nuevo registro creada
            form1 = RegistroForm(request.POST, prefix="texto", instance=nuevo_registro)
            if form1.is_valid():
                registro = form1.save()
                for input_file, object_file in request.FILES.items():
                    for fichero in request.FILES.getlist(input_file):
                        archivo = Fichero.objects.create(fichero=fichero, content_type=fichero.content_type,
                                                         entidad=g_e.ronda.entidad)
                        registro.ficheros.add(archivo)

        if request.POST['action'] == 'pdf_registro':
            id_fich = request.POST['id_registro']
            fichero = Fichero.objects.get(id=id_fich)
            response = HttpResponse(open(RUTA_BASE + fichero.fichero.url), content_type=fichero.content_type)
            response['Content-Disposition'] = 'attachment; filename=%s' % (fichero.fich_name)
            return response

    return render(request, "registro.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Nuevo',
                            'title': 'Crear un nuevo registro', 'permiso': 'crea_registros'},
                           {'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar',
                            'title': 'Grabar el nuevo registro',
                            'permiso': 'crea_registros'}),
                      'formname': 'registro',
                      'registros': registros,
                  })


@login_required()
def ajax_registros(request):
    g_e = request.session['gauser_extra']
    if request.is_ajax():
        action = request.POST['action']
        if action == 'busca_registros':
            texto = request.POST['texto']
            tipo = request.POST['tipo_busqueda']
            try:
                inicio = datetime.strptime(request.POST['id_fecha_inicio'], '%d-%m-%Y')
            except:
                inicio = datetime.strptime(request.POST['id_fecha_inicio'], '%d/%m/%Y')
            try:
                fin = datetime.strptime(request.POST['id_fecha_fin'], '%d-%m-%Y')
            except:
                fin = datetime.strptime(request.POST['id_fecha_fin'], '%d/%m/%Y')
            registros = Registro.objects.filter(entidad=g_e.ronda.entidad, fecha__gte=inicio, fecha__lte=fin)
            registros_contain_texto = registros.filter(
                Q(asunto__icontains=texto) | Q(texto__icontains=texto) | Q(emisor__icontains=texto) | Q(
                    receptor__icontains=texto), ~Q(tipo=tipo))
            num_registros = registros_contain_texto.count()
            max_num_registros = 100
            if num_registros > max_num_registros:
                html = '<b style="color:red;">Se han encontrado %s coincidencias.</b><b><br>' \
                       'El sistema está configurado para no mostrar los resultados cuando la cantidad ' \
                       'de coincidencias excede de</b> <b style="color:red;">%s</b>.<b><br>Escribe más texto para' \
                       ' mejorar la búsqueda.</b>' % (
                           num_registros, max_num_registros)
                return JsonResponse({'html': html, 'ok': True})
            else:
                html = render_to_string('registro_append.html', {'registros': registros_contain_texto})
                return JsonResponse({'html': html, 'ok': True})
        elif action == 'registro_append':
            registro = Registro.objects.get(id=request.POST['id_registro'])
            accordion = render_to_string('registro_append.html', {'registros': [registro]})
            return HttpResponse(accordion)
        elif action == 'delete_registro' and g_e.has_permiso('borra_registros'):
            registro = Registro.objects.get(id=request.POST['id'])
            crear_aviso(request, True, u'Ejecuta borrar registro: %s' % (registro.asunto))
            registro.delete()
            return HttpResponse(True)
        elif action == 'add_registro' and g_e.has_permiso('crea_registros'):
            form1 = RegistroForm(prefix="texto")
            formulario = render_to_string('registro_add.html', {'form1': form1})
            return HttpResponse(formulario)
