# -*- coding: utf-8 -*-
#from django.db.models.signals import post_syncdb
#from gauss.permisos import *
#import django.contrib.auth.models as modelos

#def add_permisos_grupos(sender, **kwargs):
    ##Cada vez que se ejecuta syncdb también se ejecuta esta función
    ##que se encarga de actualizar los permisos de cada grupo dependiendo
    ##de los almacenados en el fichero gauss/permisos.py
    #modelos = sender
    #permisos_grupos = ['',PERM_PRESIDENTE, PERM_SECRETARIO, PERM_TESORERO, PERM_JEFERAMA, PERM_SCOUTER, PERM_EDUCANDO, PERM_CONSEJO, PERM_COMITE, PERM_PADRE, PERM_ALMACENERO, PERM_COCINERO, PERM_FONTANERO, PERM_CARPINTERO, PERM_ELECTRICISTA]
    #grupos = modelos.Group.objects.all()
    #for grupo in grupos:
      #permisos_grupo = permisos_grupos[grupo.pk]
      #permisos_add = modelos.Permission.objects.filter(codename__in=permisos_grupo)
      #for permiso_add in permisos_add:
	#grupo.permissions.add(permiso_add)


#post_syncdb.connect(add_permisos_grupos, sender=modelos)
