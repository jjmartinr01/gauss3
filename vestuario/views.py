# -*- coding: utf-8 -*-
from django.forms import ModelForm
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.template.loader import render_to_string

# from autenticar.models import Gauser_extra
from entidades.models import Gauser_extra

from gauss.funciones import html_to_pdf
from gauss.rutas import MEDIA_VESTUARIOS
from mensajes.models import Aviso
from mensajes.views import crear_aviso
from entidades.forms import Gauser_mis_datos_Form, Gauser_extra_mis_datos_Form
from django.db.models import Q

# class Uniforme(models.Model):
# solicitante = models.ForeignKey(Gauser_extra, related_name='solicitante')
# gauser_extra = models.ForeignKey(Gauser_extra, related_name='g_e')
#     talla = models.CharField("Talla del polo", max_length=10, choices=TALLAS)
#     tipo = models.CharField("Tipo", max_length=10, choices=(('corta', 'Manga corta'),('larga', 'Manga larga')))
#     pagado = models.NullBooleanField('¿Está pagado?')
#     entregado = models.NullBooleanField('¿Está entregado?')
#     campo1 = models.CharField("Campo 1", max_length=100)
#     campo2 = models.CharField("Campo 2", max_length=100)
#     campo3 = models.CharField("Campo 3", max_length=100)
#     fecha_pedido = models.DateField("Fecha del pedido", auto_now_add=True)
#
#     def __unicode__(self):
#         return u'%s (%s)' % (self.organization, self.iniciales)
from vestuario.models import Uniforme


class UniformeForm(ModelForm):
    class Meta:
        model = Uniforme
        exclude = ('solicitante', 'pagado', 'entregado')


@login_required()
def uniformes(request):
    g_e = request.session['gauser_extra']
    hijos = Gauser_extra.objects.filter(Q(ronda=g_e.ronda), Q(tutor1=g_e) | Q(tutor2=g_e))
    uniformes = Uniforme.objects.filter(Q(solicitante__entidad=g_e.ronda.entidad),
                                        Q(entregado=False) | Q(pagado=False)).order_by('tipo')
    uniformes_solicitados = Uniforme.objects.filter(Q(solicitante=g_e) | Q(gauser_extra__in=hijos)).distinct()

    if request.method == 'POST':
        if request.POST['action'] == 'aceptar':
            uniforme = Uniforme(solicitante=g_e, pagado=False, entregado=False)
            form = UniformeForm(request.POST, instance=uniforme)
            if form.is_valid():
                form.save()
                crear_aviso(request, False, 'Tu solicitud de uniforme ha sido guardada correctamente')
            else:
                crear_aviso(request, False, form.errors)
        if request.POST['action'] == 'mod_pedidos':
            pagados_id = request.POST.getlist('pagados')
            ids = map(int, filter(None, pagados_id))
            for uniforme in uniformes.filter(id__in=ids):
                uniforme.pagado = True
                uniforme.save()
            entregados_id = request.POST.getlist('entregados')
            ids = map(int, filter(None, entregados_id))
            for uniforme in uniformes.filter(id__in=ids):
                uniforme.entregado = True
                uniforme.save()

        if request.POST['action'] == 'genera_pdf':
            fichero = 'Uniformidad_%s_%s' % (g_e.ronda.entidad.id, g_e.ronda.id)
            c = render_to_string('uniformes2pdf.html', {'uniformes': uniformes},
                                 request=request)
            fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_VESTUARIOS, title=u'Solicitudes de uniformes')
            response = HttpResponse(fich, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            return response

        if request.POST['action'] == 'borrar_uniforme':
            uniformes_id = request.POST.getlist('uniforme_id')
            ids = map(int, filter(None, uniformes_id))
            Uniforme.objects.filter(id__in=ids).delete()

    form = UniformeForm()
    respuesta = {
        'iconos':
            ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'title': 'Aceptar los cambios realizados',
              'permiso': 'libre'},
             {'tipo': 'button', 'nombre': 'list-alt', 'texto': 'Solicitudes', 'title': 'Ver la lista de pedidos',
              'permiso': 've_lista_uniformes'},
             {'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF', 'title': 'Genera pdf con la lista de pedidos',
              'permiso': 've_lista_uniformes'},
             {'tipo': 'button', 'nombre': 'shopping-cart', 'texto': 'Pedido',
              'title': 'Mostrar el formulario para realizar pedido', 'permiso': 've_lista_uniformes'},
             {'tipo': 'button', 'nombre': 'trash-o', 'texto': 'Borrar',
              'title': 'Eliminar el pedido de uniforme indicado', 'permiso': 'libre'},
             ),
        'formname': 'uniformes',
        'form': form,
        'hijos': hijos,
        'uniformes': uniformes,
        'uniformes_solicitados': uniformes_solicitados,
        'avisos': Aviso.objects.filter(usuario=request.session["gauser_extra"],
                                       aceptado=False), }

    return render(request, "uniformes.html", respuesta)
