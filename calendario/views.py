# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q
from django import forms
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string

# from autenticar.models import Gauser_extra, Gauser
# from entidades.models import Subentidad
from autenticar.models import Gauser
from entidades.models import Subentidad, Gauser_extra

from gauss.rutas import *
from calendario.models import Vevent, Calendar
from gauss.funciones import html_to_pdf, usuarios_de_gauss
from mensajes.views import crear_aviso, crea_mensaje_cola
from mensajes.models import Aviso, Mensaje, Etiqueta
from gtelegram.views import envia_telegram
import calendar
from dateutil.relativedelta import relativedelta
from django.db.models.fields.related import ManyToManyField
import simplejson as json

logger = logging.getLogger('django')

def to_dict(instance):
    opts = instance._meta
    data = {}
    for f in opts.concrete_fields + opts.many_to_many:
        if isinstance(f, ManyToManyField):
            if instance.pk is None:
                data[f.name] = []
            else:
                data[f.name] = list(f.value_from_object(instance).values_list('pk', flat=True))
        else:
            data[f.name] = f.value_from_object(instance)
    return data


def vevents_month(g_e, fecha):
    return Vevent.objects.filter(
        Q(subentidades__in=g_e.subentidades_hijos()) | Q(invitados__in=[g_e.gauser]) | Q(propietarios__in=[g_e.gauser]),
        Q(dtstart__month=fecha.month) | Q(dtend__month=fecha.month)).distinct()

def vevents_agenda(g_e, fecha, meses):
    fecha = datetime.combine(fecha, datetime.min.time())
    return Vevent.objects.filter(Q(subentidades__in=g_e.subentidades_hijos()) | Q(invitados__in=[g_e.gauser]) | Q(
                    propietarios__in=[g_e.gauser]), dtend__gte=fecha, dtstart__lte=meses[-1][-1]).distinct()


@login_required()
def calendario(request):
    g_e = request.session["gauser_extra"]
    # vista = {'mes': 'calendario_month.html', 'agenda': 'calendario_agenda.html', 'semana': 'calendario_semana.html'}
    if request.method == 'POST':
        vista_actual = request.POST['vista_actual']
        fecha = datetime.strptime(request.POST['fecha_actual'], '%d/%m/%Y')

        if request.POST['action'] == 'borrar_evento':
            vevent = Vevent.objects.get(id=request.POST['id_evento'])
            if g_e.gauser in vevent.propietarios.all():
                vevent.delete()
            elif g_e.has_cargos([1]):  # Si es un cargo de nivel 1
                vevent.delete()
            elif g_e.gauser in vevent.invitados.all():
                vevent.invitados.remove(g_e.gauser)

        if vista_actual == 'month':
            mes = calendar.Calendar().monthdatescalendar(fecha.year, fecha.month)
            # vevents = Vevent.objects.filter(
            #     Q(subentidades__in=g_e.subentidades_hijos()) | Q(invitados__in=[g_e.gauser]) | Q(
            #         propietarios__in=[g_e.gauser]),
            #     Q(dtstart__month=fecha.month) | Q(dtend__month=fecha.month)).distinct()
            vevents = vevents_month(g_e, fecha)
            renderizado = render_to_string('calendario_month.html', {'mes': mes, 'vevents': vevents})

        elif vista_actual == 'agenda':
            mes = relativedelta(months=1)
            m1 = calendar.Calendar().monthdatescalendar(fecha.year, fecha.month)
            m2 = calendar.Calendar().monthdatescalendar((fecha + mes).year, (fecha + mes).month)[1:]
            meses = m1 + m2
            vevents = vevents_agenda(g_e, fecha, meses)
            # vevents = Vevent.objects.filter(
            #     Q(subentidades__in=g_e.subentidades_hijos()) | Q(invitados__in=[g_e.gauser]) | Q(
            #         propietarios__in=[g_e.gauser]), dtend__gte=fecha,
            #     dtstart__lte=meses[-1][-1]).distinct()
            renderizado = render_to_string('calendario_agenda.html', {'vevents': vevents, 'meses': meses})

        elif request.POST['action'] == 'pdf_documentos':
            # eventos = Evento.objects.filter(
            #     Q(gauser_extra=g_e) | Q(subentidades__in=g_e.subentidades.all()) | Q(invitados__in=[g_e]))
            # fichero = 'Eventos_%s' % (request.session["gauser_extra"].gauser.username)
            # c = render_to_string('calendario2pdf.html',
            #                      {'calendario': calendario,
            #                       'eventos': eventos, }, request=request)
            # fich = html_to_pdf(request, c, fichero=fichero, media=MEDIA_FILES, title=u'Calendario')
            # response = HttpResponse(fich, content_type='application/pdf')
            # response['Content-Disposition'] = 'attachment; filename=' + fichero + '.pdf'
            # return response
            pass
    else:
        try:
            fecha = datetime.strptime(request.GET['fecha'], '%d%m%Y')
        except:
            fecha = datetime.today()
        try:
            vista_actual = request.GET['v']
        except:
            vista_actual = 'month'
        if vista_actual == 'agenda':
            mes = relativedelta(months=1)
            m1 = calendar.Calendar().monthdatescalendar(fecha.year, fecha.month)
            m2 = calendar.Calendar().monthdatescalendar((fecha + mes).year, (fecha + mes).month)[1:]
            meses = m1 + m2
            vevents = vevents_agenda(g_e, fecha, meses)
            renderizado = render_to_string('calendario_agenda.html', {'vevents': vevents, 'meses': meses})
        else:
            mes = calendar.Calendar().monthdatescalendar(fecha.year, fecha.month)
            vevents = vevents_month(g_e, fecha)
            renderizado = render_to_string('calendario_month.html', {'mes': mes, 'vevents': vevents})

    return render(request, "base_calendario.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'permiso': 'm30',
                                        'title': 'Grabar el nuevo evento/acontecimiento'},
                                       {'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Cancelar',
                                        'title': 'Cancelar y volver a ver el calendario', 'permiso': 'm30'},
                                       {'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF', 'permiso': 'm30',
                                        'title': 'Genera documento PDF con tus eventos marcados en el calendario'},
                                       ),
                                  'formname': 'Calendario',
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                                  'renderizado': renderizado,
                                  'vista_actual': vista_actual,
                                  'fecha': fecha
                              })


class VeventForm(forms.ModelForm):
    class Meta:
        model = Vevent
        exclude = ('trans', 'propietario')


@login_required()
def edita_evento(request):
    g_e = request.session["gauser_extra"]
    vista_actual = request.GET['v']
    vevent = Vevent.objects.get(id=request.GET['vevent'], propietarios__in=[g_e.gauser])
    if request.method == 'POST':
        form = VeventForm(request.POST, instance=vevent)
        if form.is_valid():
            vevent = form.save()
            dtstart = datetime.strptime(request.POST['dtstart'], "%d/%m/%Y %H:%M")
            vevent.entidad = g_e.ronda.entidad
            if not vevent.dtend:
                vevent.dtend = datetime.combine(dtstart, datetime.max.time())
            else:
                vevent.dtend = datetime.strptime(request.POST['dtend'], "%d/%m/%Y %H:%M")
            vevent.dtstart = dtstart
            vevent.save()
            crear_aviso(request, True, "Se actualiza el evento con id %s" % (vevent.id))
            if request.POST['send_telegram'] == 'true':
                # Preparamos instrucciones para mandar un correo a los usuarios afectados
                try:
                    etiqueta = Etiqueta.objects.get(nombre='vevent' + str(vevent.id))
                except:
                    etiqueta = Etiqueta.objects.create(nombre='vevent' + str(vevent.id), propietario=g_e)
                asunto = u'Actualización del evento: ' + vevent.summary
                texto_html = render_to_string('evento_informar_mail.html',
                                              {'vevent': vevent, 'actualizador': g_e, 'tipo': 'Actualizado'})
                mensaje = Mensaje.objects.create(emisor=g_e, fecha=datetime.now(), asunto=asunto, mensaje=texto_html)
                mensaje.etiquetas.add(etiqueta)
                for g in vevent.invitados.all():
                    mensaje.receptores.add(g)
                for g in vevent.propietarios.all():
                    mensaje.receptores.add(g)
                for ge in Gauser_extra.objects.filter(ronda=g_e.ronda, subentidades__in=vevent.subentidades.all()):
                    mensaje.receptores.add(ge.gauser)
                crea_mensaje_cola(mensaje)
            if request.POST['send_correo'] == 'true':
                texto_telegram = render_to_string('evento_informar_telegram.html',
                                              {'vevent': vevent, 'actualizador': g_e, 'tipo': 'Actualizado'})
                envia_telegram(g_e, texto_telegram, gausers=vevent.invitados.all(), subentidades=vevent.subentidades.all())
            # envia_telegram(g_e, texto_telegram, gausers=vevent.propietarios.all())
            # En este punto se han encolado los correos electrónicos. Se enviarán según kronos
            return redirect('/calendario/?fecha=%s&v=%s' % (vevent.dtstart.strftime('%d%m%Y'), vista_actual))
        else:
            errores = form.errors
            data = ''
            if 'summary' in errores:
                data += '<b>Nombre del evento</b> es un campo obligatorio.<br>'
            if 'dtstart' in errores:
                data += '<b>Inicio</b> es un campo obligatorio con la forma: dd/mm/yyyy hh:mm<br>'
                data += '<i>Por ejemplo, un evento que comience el 3 de mayo de 2018 a las 9:35, debería '
                data += 'escribirse:<br></i> 03/05/2018 09:35<br>'
            crear_aviso(request, False, data)

    keys = ('id', 'text')
    invitados = [dict(zip(keys, [gauser.id, '%s, %s' % (gauser.last_name, gauser.first_name)])) for gauser in vevent.invitados.all()]
    propietarios = [dict(zip(keys, [gauser.id, '%s, %s' % (gauser.last_name, gauser.first_name)])) for gauser in vevent.propietarios.all()]
    return render(request, "edita_evento.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'permiso': 'm30',
                                        'title': 'Grabar el nuevo evento/acontecimiento'},
                                       {'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Cancelar',
                                        'title': 'Cancelar y volver a ver el calendario', 'permiso': 'm30'},
                                       {'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF', 'permiso': 'm30',
                                        'title': 'Genera documento PDF con tus eventos marcados en el calendario'},
                                       ),
                                  'formname': 'Calendario',
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                                  'form': VeventForm(initial=to_dict(vevent)),
                                  'vevent': vevent,
                                  'vista_actual': vista_actual,
                                  'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today()),
                                  'invitados': json.dumps(invitados),
                                  'propietarios': json.dumps(propietarios)
                              })


@login_required()
def crea_evento(request):
    g_e = request.session["gauser_extra"]
    vista_actual = request.GET['v']
    if request.method == 'POST':
        form = VeventForm(request.POST)
        if form.is_valid():
            vevent = form.save()
            dtstart = datetime.strptime(request.POST['dtstart'], "%d/%m/%Y %H:%M")
            vevent.entidad = g_e.ronda.entidad
            if not vevent.dtend:
                vevent.dtend = datetime.combine(dtstart, datetime.max.time())
            else:
                vevent.dtend = datetime.strptime(request.POST['dtend'], "%d/%m/%Y %H:%M")
            vevent.dtstart = dtstart
            vevent.save()
            crear_aviso(request, True, "Se graba un nuevo evento con id %s" % (vevent.id))
            if request.POST['send_telegram'] == 'true':
                # Preparamos instrucciones para mandar un correo a los usuarios afectados
                try:
                    etiqueta = Etiqueta.objects.get(nombre='vevent' + str(vevent.id))
                except:
                    etiqueta = Etiqueta.objects.create(nombre='vevent' + str(vevent.id), propietario=g_e)
                asunto = u'Nuevo evento: ' + vevent.summary
                texto_html = render_to_string('evento_informar_mail.html',
                                              {'vevent': vevent, 'actualizador': g_e, 'tipo': 'Nuevo'})
                mensaje = Mensaje.objects.create(emisor=g_e, fecha=datetime.now(), asunto=asunto, mensaje=texto_html)
                mensaje.etiquetas.add(etiqueta)
                for g in vevent.invitados.all():
                    mensaje.receptores.add(g)
                for g in vevent.propietarios.all():
                    mensaje.receptores.add(g)
                for ge in Gauser_extra.objects.filter(ronda=g_e.ronda, subentidades__in=vevent.subentidades.all()):
                    mensaje.receptores.add(ge.gauser)
                crea_mensaje_cola(mensaje)
            if request.POST['send_correo'] == 'true':
                texto_telegram = render_to_string('evento_informar_telegram.html',
                                              {'vevent': vevent, 'actualizador': g_e, 'tipo': 'Nuevo'})
                envia_telegram(g_e, texto_telegram, gausers=vevent.invitados.all(), subentidades=vevent.subentidades.all())

            # En este punto se han encolado los correos electrónicos y telegrams. Se enviarán según kronos
            return redirect('/calendario/?fecha=%s&v=%s' % (vevent.dtstart.strftime('%d%m%Y'), vista_actual))
        else:
            errores = form.errors
            data = errores
            if 'summary' in errores:
                data += '<b>Nombre del evento</b> es un campo obligatorio.<br>'
            if 'dtstart' in errores:
                data += '<b>Inicio</b> es un campo obligatorio con la forma: dd/mm/yyyy hh:mm<br>'
                data += '<i>Por ejemplo, un evento que comience el 3 de mayo de 2018 a las 9:35, debería '
                data += 'escribirse:<br></i> 03/05/2018 09:35<br>'
            crear_aviso(request, False, data)

    return render(request, "crea_evento.html",
                              {
                                  'iconos':
                                      ({'tipo': 'button', 'nombre': 'check', 'texto': 'Aceptar', 'permiso': 'crea_eventos',
                                        'title': 'Grabar el nuevo evento/acontecimiento'},
                                       {'tipo': 'button', 'nombre': 'arrow-left', 'texto': 'Cancelar',
                                        'title': 'Cancelar y volver a ver el calendario', 'permiso': 'crea_eventos'},
                                       {'tipo': 'button', 'nombre': 'file-pdf-o', 'texto': 'PDF', 'permiso': 'crea_eventos',
                                        'title': 'Genera documento PDF con tus eventos marcados en el calendario'},
                                       ),
                                  'formname': 'Crea_evento',
                                  'avisos': Aviso.objects.filter(usuario=g_e, aceptado=False),
                                  'form': VeventForm(),
                                  'vista_actual': vista_actual,
                                  'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today()),
                                  'fecha': datetime.strptime(request.GET['f'], '%d%m%Y')
                              })


@login_required()
def calendario_ajax(request):
    if request.is_ajax():
        g_e = request.session['gauser_extra']

        if request.POST['action'] == 'buscar_invitados':
            texto = request.POST['q']
            usuarios = usuarios_de_gauss(g_e.ronda.entidad)
            usuarios_contain_texto = usuarios.filter(
                Q(gauser__first_name__icontains=texto) | Q(gauser__last_name__icontains=texto)).values_list(
                'gauser__id',
                'gauser__last_name',
                'gauser__first_name')
            keys = ('id', 'last_name', 'first_name')
            return JsonResponse([dict(zip(keys, row)) for row in usuarios_contain_texto], safe=False)

        elif request.POST['action'] == 'show_evento':
            id = request.POST['id']
            vevent = Vevent.objects.get(id=id)
            usuario = ''
            if g_e.gauser in vevent.propietarios.all():
                usuario = 'Propietario'
            elif g_e.has_cargos([1]):
                usuario = 'Cargo'
            elif g_e.gauser in vevent.invitados.all():
                usuario = 'Invitado'
            informe = render_to_string('evento_informar.html', {'vevent': vevent, 'usuario': usuario})
            data = {'title': vevent.summary, 'texto': informe, 'usuario': usuario}
            return JsonResponse(data)

        elif request.POST['action'] == 'renderizado':
            fecha = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
            vista = request.POST['vista']
            direction = int(request.POST['direction'])
            if vista == 'month':
                # Dependiendo de nextslide será un mes positivo o negativo
                one_month = relativedelta(months=direction)
                fecha = fecha + one_month
                mes = calendar.Calendar().monthdatescalendar(fecha.year, fecha.month)
                vevents = vevents_month(g_e, fecha)
                # Vevent.objects.filter(
                #     Q(subentidades__in=g_e.subentidades_hijos()) | Q(invitados__in=[g_e.gauser]) | Q(
                #         propietarios__in=[g_e.gauser]),
                #     Q(dtstart__month=fecha.month) | Q(dtend__month=fecha.month)).distinct()
                renderizado = render_to_string('calendario_month.html', {'mes': mes, 'vevents': vevents})
            if vista == 'agenda':
                mes1 = relativedelta(months=direction)
                mes2 = relativedelta(months=(direction + 1))
                m1 = calendar.Calendar().monthdatescalendar((fecha + mes1).year, (fecha + mes1).month)
                m2 = calendar.Calendar().monthdatescalendar((fecha + mes2).year, (fecha + mes2).month)[1:]
                meses = m1 + m2
                fecha = fecha + mes1
                vevents = vevents_agenda(g_e, fecha, meses)
                # Vevent.objects.filter(
                #     Q(subentidades__in=g_e.subentidades_hijos()) | Q(invitados__in=[g_e.gauser]) | Q(
                #         propietarios__in=[g_e.gauser]), dtend__gte=fecha,
                #     dtstart__lte=meses[-1][-1]).distinct()
                renderizado = render_to_string('calendario_agenda.html', {'vevents': vevents, 'meses': meses})
            return JsonResponse({'renderizado': renderizado, 'fecha': fecha.strftime('%d/%m/%Y')})

        elif request.POST['action'] == 'more_vevents':
            one_day = relativedelta(days=1)
            fecha = datetime.strptime(request.POST['fecha'], '%d/%m/%Y') + one_day
            m1 = calendar.Calendar().monthdatescalendar(fecha.year, fecha.month)[1:]
            meses = m1
            vevents = vevents_agenda(g_e, fecha, meses)
            # Vevent.objects.filter(
            #     Q(subentidades__in=g_e.subentidades_hijos()) | Q(invitados__in=[g_e.gauser]) | Q(
            #         propietarios__in=[g_e.gauser]), dtend__gte=fecha,
            #     dtstart__lte=meses[-1][-1]).distinct()
            renderizado = render_to_string('calendario_agenda.html', {'vevents': vevents, 'meses': meses})
            return JsonResponse({'renderizado': renderizado, 'fecha': fecha.strftime('%d/%m/%Y')})

        # elif request.POST['action'] == 'crea_evento':
        #     dtstart = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
        #     data = render_to_string('evento_crear.html', {
        #         'form': VeventForm(initial={'dtstart': dtstart}),
        #         'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today()),
        #         'invitados': Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, ronda=g_e.ronda.entidad.ronda),
        #     }, request=request)
        #     return HttpResponse(data)

        # elif request.POST['action'] == 'edita_evento':
        #     vevent = Vevent.objects.get(id=request.POST['id'])
        #     data = render_to_string('evento_editar.html', {
        #         'form': VeventForm(initial=to_dict(vevent)),
        #         'subentidades': Subentidad.objects.filter(entidad=g_e.ronda.entidad, fecha_expira__gt=datetime.today()),
        #         'invitados': Gauser_extra.objects.filter(entidad=g_e.ronda.entidad, ronda=g_e.ronda.entidad.ronda),
        #     }, request=request)
        #     return HttpResponse(data)

        # elif request.POST['action'] == 'grabar_evento':
        #     form = VeventForm(request.POST)
        #     if form.is_valid():
        #         vevent = form.save()
        #         vevent.propietarios.add(g_e.gauser)
        #         crear_aviso(request, True, "Se crea el evento con id %s" % (vevent.id))
        #         invitados = Gauser.objects.filter(id__in=[g_e.gauser.id] + list(request.POST.getlist('invitados')))
        #         for invitado in invitados:
        #             vevent.invitados.add(invitado)
        #         subentidades = Subentidad.objects.filter(id__in=request.POST.getlist('subentidades'), fecha_expira__gt=datetime.today())
        #         for subentidad in subentidades:
        #             vevent.subentidades.add(subentidad)
        #         vevent.entidad = g_e.ronda.entidad
        #         vevent.save()
        #         # Preparamos instrucciones para mandar un correo a los usuarios afectados
        #         try:
        #             etiqueta = Etiqueta.objects.get(nombre='vevent' + str(vevent.id))
        #         except:
        #             etiqueta = Etiqueta.objects.create(nombre='vevent' + str(vevent.id), propietario=g_e)
        #         asunto = vevent.summary
        #         texto_html = render_to_string('evento_informar_mail.html',
        #                                       {'vevent': vevent, 'actualizador': g_e, 'tipo': 'Nuevo'})
        #         mensaje = Mensaje.objects.create(emisor=g_e, fecha=datetime.now(), asunto=asunto, mensaje=texto_html)
        #         mensaje.etiquetas.add(etiqueta)
        #         for g in vevent.invitados.all():
        #             mensaje.receptores.add(g)
        #         for g in vevent.propietarios.all():
        #             mensaje.receptores.add(g)
        #         for ge in Gauser_extra.objects.filter(ronda=g_e.ronda, subentidades__in=vevent.subentidades.all()):
        #             if ge.edad < 18:
        #                 for miembro_familia in ge.unidad_familiar:
        #                     if miembro_familia.edad > 18:
        #                         mensaje.receptores.add(miembro_familia.gauser)
        #                 mensaje.receptores.add(ge.gauser)
        #         crea_mensaje_cola(mensaje)
        #         # En este punto se han encolado los correos electrónicos. Se enviarán según kronos
        #         return HttpResponse('')
        #     else:
        #         errores = form.errors
        #         data = ''
        #         if 'summary' in errores:
        #             data += '<b>Nombre del evento</b> es un campo obligatorio.<br>'
        #         if 'dtstart' in errores:
        #             data += '<b>Inicio</b> es un campo obligatorio con la forma: dd/mm/yyyy hh:mm<br>'
        #             data += '<i>Por ejemplo, un evento que comience el 3 de mayo de 2018 a las 9:35, debería '
        #             data += 'escribirse:<br></i> 03/05/2018 09:35<br>'
        #         return HttpResponse(data)

        # elif request.POST['action'] == 'actualizar_evento':
        #     vevent = Vevent.objects.get(id=request.POST['id_evento'], propietarios__in=[g_e.gauser, ])
        #     form = VeventForm(request.POST, instance=vevent)
        #     if form.is_valid():
        #         for variable in ['summary', 'location', 'description']:
        #             setattr(vevent, variable, request.POST[variable])
        #         for variable in ['dtstart', 'dtend']:
        #             setattr(vevent, variable, datetime.strptime(request.POST[variable], '%d/%m/%Y %H:%M'))
        #         vevent.entidad = g_e.ronda.entidad
        #         vevent.save()
        #         crear_aviso(request, True, "Se actualiza el evento con id %s" % (vevent.id))
        #         invitados = Gauser.objects.filter(id__in=request.POST.getlist('invitados'))
        #         for invitado in invitados:
        #             vevent.invitados.add(invitado)
        #         subentidades = Subentidad.objects.filter(id__in=request.POST.getlist('subentidades'), fecha_expira__gt=datetime.today())
        #         for subentidad in subentidades:
        #             vevent.subentidades.add(subentidad)
        #         # Preparamos instrucciones para mandar un correo a los usuarios afectados
        #         try:
        #             etiqueta = Etiqueta.objects.get(nombre='vevent' + str(vevent.id))
        #         except:
        #             etiqueta = Etiqueta.objects.create(nombre='vevent' + str(vevent.id), propietario=g_e)
        #         asunto = u'Actualización del evento: ' + vevent.summary
        #         texto_html = render_to_string('evento_informar_mail.html',
        #                                       {'vevent': vevent, 'actualizador': g_e, 'tipo': 'Actualizado'})
        #         mensaje = Mensaje.objects.create(emisor=g_e, fecha=datetime.now(), asunto=asunto, mensaje=texto_html)
        #         mensaje.etiquetas.add(etiqueta)
        #         for g in vevent.invitados.all():
        #             mensaje.receptores.add(g)
        #         for g in vevent.propietarios.all():
        #             mensaje.receptores.add(g)
        #         for ge in Gauser_extra.objects.filter(ronda=g_e.ronda, subentidades__in=vevent.subentidades.all()):
        #             mensaje.receptores.add(ge.gauser)
        #         crea_mensaje_cola(mensaje)
        #         # En este punto se han encolado los correos electrónicos. Se enviarán según kronos
        #         return HttpResponse('')
        #     else:
        #         errores = form.errors
        #         data = ''
        #         if 'summary' in errores:
        #             data += '<b>Nombre del evento</b> es un campo obligatorio.<br>'
        #         if 'dtstart' in errores:
        #             data += '<b>Inicio</b> es un campo obligatorio con la forma: dd/mm/yyyy hh:mm<br>'
        #             data += '<i>Por ejemplo, un evento que comience el 3 de mayo de 2018 a las 9:35, debería '
        #             data += 'escribirse:<br></i> 03/05/2018 09:35<br>'
        #         return HttpResponse(data)

        elif request.POST['action'] == 'mes':
            fecha = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
            mes = calendar.Calendar().monthdatescalendar(fecha.year, fecha.month)
            vevents = vevents_month(g_e, fecha)
            # Vevent.objects.filter(
            #     Q(subentidades__in=g_e.subentidades_hijos()) | Q(invitados__in=[g_e.gauser]),
            #     Q(dtstart__month=fecha.month) | Q(dtend__month=fecha.month)).distinct()
            renderizado = render_to_string('calendario_month.html', {'mes': mes, 'vevents': vevents})
            return HttpResponse(renderizado)

        elif request.POST['action'] == 'agenda':
            fecha = datetime.strptime(request.POST['fecha'], '%d/%m/%Y')
            mes = relativedelta(months=1)
            m1 = calendar.Calendar().monthdatescalendar(fecha.year, fecha.month)
            m2 = calendar.Calendar().monthdatescalendar((fecha + mes).year, (fecha + mes).month)[1:]
            meses = m1 + m2
            vevents = vevents_agenda(g_e, fecha, meses)
            # Vevent.objects.filter(
            #     Q(subentidades__in=g_e.subentidades_hijos()) | Q(invitados__in=[g_e.gauser]), dtend__gte=fecha,
            #     dtstart__lte=meses[-1][-1]).distinct()
            renderizado = render_to_string('calendario_agenda.html', {'vevents': vevents, 'meses': meses})
            return HttpResponse(renderizado)
