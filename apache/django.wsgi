import os
import sys

from django.core.wsgi import get_wsgi_application

#path a donde esta el manage.py de nuestro proyecto Django
sys.path.append(‘/home/juanjo/django/gauss/’)


os.environ.setdefault('LANG', 'en_US.UTF-8')
os.environ.setdefault('LC_ALL', 'en_US.UTF-8')

#activamos nuestro virtualenv
#activate_this = ‘pathToVirtualenv/bin/activate_this.py’
#execfile(activate_this, dict(__file__=activate_this))

os.environ['DJANGO_SETTINGS_MODULE'] = 'gauss.settings'
application = get_wsgi_application()



#import os
#import sys
#
#path = '/home/juanjo/django/gauss_asocia'
#if path not in sys.path:
#    sys.path.append(path)
#
#os.environ['DJANGO_SETTINGS_MODULE'] = 'gauss.settings'
#
#import django.core.handlers.wsgi
#application = django.core.handlers.wsgi.WSGIHandler()
