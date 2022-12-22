echo "Iniciando script"
echo "******** Borrando migraciones core Django ********"
find ../venv/lib/python3.10/site-packages/django/contrib -path "*/migrations/*.py" -not -name "__init__.py" -delete
find ../venv/lib/python3.10/site-packages/django/contrib -path "*/migrations/*.pyc" -delete
echo "**************************************************"
echo

echo "******** Borrando migraciones core Django: captcha ********"
find ../venv/lib/python3.10/site-packages/captcha -path "*/migrations/*.py" -not -name "__init__.py" -delete
find ../venv/lib/python3.10/site-packages/captcha -path "*/migrations/*.pyc" -delete
echo "**************************************************"
echo

echo "******** Borrando migraciones Gauss ********"
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
echo "**************************************************"
echo

echo "******** Ejecutando: python manage.py makemigrations --empty \$app ********"
for app in 'auth' 'contenttypes' 'sessions' 'sites' 'messages' 'staticfiles' 'admin' 'bancos' 'autenticar' 'entidades' 'mensajes' 'my_templatetags' 'calendario' 'contabilidad' 'actas' 'documentos' 'lopd' 'vestuario' 'apariencia' 'compraventa' 'web' 'kronos' 'captcha' 'gauss_conf' 'formularios' 'gtelegram' 'horarios' 'cupo' 'convivencia' 'absentismo' 'registro' 'reparaciones' 'actividades' 'tutorados' 'programaciones' 'estudios' 'competencias_clave' 'vut' 'domotica' 'reuniones' 'moscosos' 'inspeccion_educativa' 'federaciones' 'faqs' 'corsheaders' 'webpage'
do
  python manage.py makemigrations --empty $app
done
echo "**************************************************"
echo

echo "******** Ejecutando: python manage.py makemigrations ********"
python manage.py makemigrations
echo "**************************************************"
echo

echo "******** Ejecutando: python manage.py makemigrations ********"
python manage.py migrate
echo "**************************************************"
echo
echo "Script finalizado"


