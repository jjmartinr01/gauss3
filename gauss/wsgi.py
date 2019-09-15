"""
WSGI config for gauss project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import sys
import site
try:
    from gauss.settings import RUTA_PYTHON_HOME
except:
    RUTA_PYTHON_HOME = '/home/gauss/django/gauss3'

# Calculate path to site-packages directory.
python_version = '.'.join(map(str, sys.version_info[:2]))
site_packages = RUTA_PYTHON_HOME + '/lib/python%s/site-packages' % python_version
# Add the site-packages directory.
site.addsitedir(site_packages)

# Remember original sys.path.
prev_sys_path = list(sys.path)
# Add the site-packages directory.
site.addsitedir(site_packages)
# Reorder sys.path so new directories at the front.
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path

path = '/home/gauss/django/gauss3'
if path not in sys.path:
    sys.path.append(path)

import os
from django.core.wsgi import get_wsgi_application

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gauss.settings")
os.environ["DJANGO_SETTINGS_MODULE"] = "gauss.settings"

application = get_wsgi_application()
