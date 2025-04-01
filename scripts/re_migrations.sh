# Borramos las migraciones de las app del core de Django
find /usr/local/lib/python3.7/site-packages/django/contrib -path "*/migrations/*.py" -not -name "__init__.py" -delete
find /usr/local/lib/python3.7/site-packages/django/contrib -path "*/migrations/*.pyc" -delete

# Borramos las migraciones de las app de Gauss
find /var/www/python/gauss3 -path "*/migrations/*.py" -not -name "__init__.py" -delete
find /var/www/python/gauss3 -path "*/migrations/*.pyc" -delete

for app in bancos autenticar entidades mensajes calendario contabilidad actas documentos lopd vestuario apariencia compraventa web formularios gtelegram horarios cupo convivencia absentismo registro reparaciones actividades tutorados programaciones estudios competencias_clave vut domotica reuniones moscosos inspeccion_educativa federaciones faqs admin auth contenttypes sessions sites
do
    rm -Rf /var/www/python/gauss3/$app/migrations/ 
done

# Generamos
for app in bancos autenticar entidades mensajes calendario contabilidad actas documentos lopd vestuario apariencia compraventa web formularios gtelegram horarios cupo convivencia absentismo registro reparaciones actividades tutorados programaciones estudios competencias_clave vut domotica reuniones moscosos inspeccion_educativa federaciones faqs admin auth contenttypes sessions sites
do
    python /var/www/python/gauss3/manage.py makemigrations $app
done

python /var/www/python/gauss3/manage.py migrate --fake-initial
