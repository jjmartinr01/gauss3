for app in bancos autenticar entidades mensajes calendario contabilidad actas documentos lopd vestuario apariencia compraventa web formularios gtelegram horarios cupo convivencia absentismo registro reparaciones actividades tutorados programaciones estudios competencias_clave vut domotica reuniones webpage
do
    rm -Rf ./$app/migrations/
done

for app in bancos autenticar entidades mensajes calendario contabilidad actas documentos lopd vestuario apariencia compraventa web formularios gtelegram horarios cupo convivencia absentismo registro reparaciones actividades tutorados programaciones estudios competencias_clave vut domotica reuniones webpage
do
    python manage.py makemigrations $app
done

python manage.py migrate --fake-initial
