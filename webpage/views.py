# -*- coding: utf-8 -*-
from django.shortcuts import render

# Create your views here.

def inicioweb(request):
    return render(request, "inicioweb.html",
                  {
                      'formname': 'inicioweb',
                  })

def avisolegal(request):
    return render(request, "avisolegal.html",
                  {
                      'formname': 'avisolegal',
                  })

def privacidad(request):
    return render(request, "privacidad.html",
                  {
                      'formname': 'privacidad',
                  })

def condiciones(request):
    return render(request, "condiciones.html",
                  {
                      'formname': 'condiciones',
                  })
