# -*- coding: utf-8 -*-
from gauss.rutas import *
from celery import shared_task


@shared_task
def add(x, y):
    f=open(MEDIA_FILES + 'prueba_rabitt.txt', 'w+')
    f.write('Esta es el contenido %s y %s' % (x,y))
    f.close()
    return x + y


@shared_task
def mul(x, y):
    return x * y


@shared_task
def xsum(numbers):
    return sum(numbers)


# @shared_task
# def count_widgets():
#     return Widget.objects.count()


# @shared_task
# def rename_widget(widget_id, name):
#     w = Widget.objects.get(id=widget_id)
#     w.name = name
#     w.save()
