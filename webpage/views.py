# -*- coding: utf-8 -*-
from django.shortcuts import render

# Create your views here.

def inicioweb(request):
    return render(request, "inicioweb.html",
                  {
                      'iconos':
                          ({'tipo': 'button', 'nombre': 'plus', 'texto': 'Añadir',
                            'title': 'Crear una nueva configuración de convocatoria',
                            'permiso': 'c_conv_template'},
                           ),
                      'configura': True,
                      'formname': 'inicioweb',
                  })