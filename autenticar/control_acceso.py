# -*- coding: utf-8 -*-
from django.shortcuts import render
import string
import random
import logging

logger = logging.getLogger('django')

def gauss_required(func):
    def decorator(request, *args, **kwargs):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[-1].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        try:
            g_e = request.session['gauser_extra']
            username = g_e.gauser.username
            if username == 'gauss':
                logger.info(u'gauss, acceso a %s desde %s' % (request.path_info, ip))
                return func(request, *args, **kwargs)
            else:
                logger.info(u'%s, acceso denegado a %s desde %s' % (g_e, request.path_info, ip))
                return render(request, "enlazar.html", {'page': '/principal/', })
        except:
            logger.info(u'Intento de acceso sin loggin a %s (exclusivo de gauss) desde %s' % (request.path_info, ip))
            return render(request, "enlazar.html", {'page': '/', })
    return decorator

def permiso_required2(permiso):
    def real_decorator(func):
        def wrapper(request, *args, **kwargs):
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[-1].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
            try:
                g_e = request.session['gauser_extra']
                if g_e.has_permiso(permiso):
                    logger.info(u'%s, acceso a %s desde %s' % (g_e, request.path_info, ip))
                    return func(request, *args, **kwargs)
                else:
                    logger.info(u'%s, acceso denegado a %s desde %s' % (g_e, request.path_info, ip))
                    return render(request, "enlazar.html", {'page': '/principal/', })
            except:
                logger.info(u'Intento de acceso sin loggin a %s desde %s' % (request.path_info, ip))
                return render(request, "enlazar.html", {'page': '/', })
        return wrapper
    return real_decorator

def permiso_required(permisos):
    def real_decorator(func):
        def wrapper(request, *args, **kwargs):
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[-1].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
            try:
                g_e = request.session['gauser_extra']
                has_permiso = False
                if isinstance(permisos, list):
                    for permiso in permisos:
                        has_permiso = has_permiso | g_e.has_permiso(permiso)
                else:
                    has_permiso = g_e.has_permiso(permisos)
                if has_permiso:
                    logger.info(u'%s, acceso a %s desde %s' % (g_e, request.path_info, ip))
                    return func(request, *args, **kwargs)
                else:
                    logger.info(u'%s, acceso denegado a %s desde %s' % (g_e, request.path_info, ip))
                    return render(request, "enlazar.html", {'page': '/principal/', })
            except:
                logger.info(u'Intento de acceso sin loggin a %s desde %s' % (request.path_info, ip))
                return render(request, "enlazar.html", {'page': '/', })
        return wrapper
    return real_decorator


def LogGauss(func):
    def decorator(request, *args, **kwargs):
        # logger = logging.getLogger('django')
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[-1].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        acceso = 'Acceso a %s' % request.path_info
        try:
            g_e = request.session['gauser_extra']
            logger.info(u"usuario: %s, entidad: %s, ronda: %s, %s, %s, %s, %s" % (g_e.gauser.username, g_e.ronda.entidad.id, g_e.ronda.id, request.path, request.method, ip, acceso))
        except:
            try:
                logger.info(u"%s, %s, %s, %s, %s" % (str(request.user), request.path, request.method, ip, acceso))
            except:
                logger.info(u"%s, %s, %s, %s, %s" % ('AnonymousUser', request.path, request.method, ip, acceso))
        return func(request, *args, **kwargs)

    return decorator


# Generador de contraseñas
def pass_generator(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))
