#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

touch /var/www/python/gauss3/log/logGaussDomotica.log 
python /var/www/python/gauss3/manage.py collectstatic --noinput

exec /usr/local/bin/gunicorn gauss.wsgi -w 3 --threads 3 --bind 0.0.0.0:8000 --chdir=/var/www/python/gauss3 