FROM python:3.7.17-slim-bullseye
RUN mkdir -p /var/www/python
RUN apt update
RUN apt install -y git
COPY / /var/www/python/gauss3
RUN mkdir -p /var/www/python/gauss3/log 
RUN touch /var/www/python/gauss3/log/logGaussDomotica.log
WORKDIR /var/www/python/gauss3

#Python needs to compile some dependencies
RUN apt install gcc libpq-dev -y
#Hace falta descarga el locale de es-ES
RUN apt-get install -y locales locales-all

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt /var/www/python/gauss3/requirements.txt
RUN python -m pip install -r requirements.txt

COPY gauss/settings.py /var/www/python/gauss3/gauss/settings.py

COPY ./scripts/cleanMigration.sh /cleanMigration.sh
RUN sed -i 's/\r$//g' /cleanMigration.sh
RUN chmod +x /cleanMigration.sh

COPY ./scripts/worker_start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker

COPY ./scripts/beat_start /start-celerybeat
RUN sed -i 's/\r$//g' /start-celerybeat
RUN chmod +x /start-celerybeat

COPY ./scripts/django_start /start-django
RUN sed -i 's/\r$//g' /start-django
RUN chmod +x /start-django

RUN mkdir /var/www/python/gauss3/sitestatic
RUN python /var/www/python/gauss3/manage.py collectstatic --noinput
# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /var/www/python/gauss3/
USER appuser