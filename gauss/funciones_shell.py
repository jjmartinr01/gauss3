# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.core import serializers
import json, requests
from entidades.models import Entidad, Gauser_extra
from django.db.models import Q


def load_fichero_data_json(fichero, url=''):
    """
    :param fichero: String. Texto con la ruta del fichero. Ejemplo: './media/data_ficheros_registros.json'
    :return: Boolean. Si todo ha ido bien devuelve True

    ejemplo:
    load_fichero_data_json('data_reparaciones.json', url='http://localhost:8000/reparaciones_ge_id2ge_dni')

    La idea es crear en cada app a exportar, por ejemplo en reparaciones, una función que devuelva el dni del
    gauser_extra, buscar ese dni en gauss_asocia y asignarle su correspondiente id.
    Es posible que el proceso finalice sin asignar algunos usuarios a los objetos. Habrá que buscar aquellos objetos sin
    la asignación adecuada y asignarles uno por defecto. Ejemplo:
        rs=Reparacion.objects.filter(reparador__isnull=True)
        for r in rs:
            r.detecta=ge #Donde ge es un gauser_extra elegido anteriormente
            r.save()


    """
    if len(url) > 4:
        with open(fichero, 'r') as myfile:
            data = myfile.read().replace('\n', '')
        data = json.loads(data)
        for d in data:
            resp = requests.get(url='%s?id=%s' % (url, d['pk']))
            data_json = json.loads(resp.text)
            try:
                q_entidad = Q(entidad=Entidad.objects.get(code=data_json['entidad_code']))
            except:
                q_entidad = Q(entidad__isnull=False)
            for key in data_json.keys():
                if key != 'entidad_code':
                    try:
                        q_dni = Q(gauser__dni__icontains=data_json[key])
                        ge = Gauser_extra.objects.filter(q_entidad, q_dni).reverse()[0]
                        d['fields'][key] = ge.id
                    except:
                        d['fields'][key] = None
        with open(fichero, 'w') as outfile:
            json.dump(data, outfile)

    with open(fichero) as json_data:
        for deserialized_object in serializers.deserialize("json", json_data):
            try:
                deserialized_object.save()
            except:
                pass
    return True


# Proceso para recuperar las reparaciones de Gauss_educa:

# Esta función se ejecuta en la raíz de Gauss_educa
def load_reparaciones_from_gauss_educa():
    from reparaciones.models import Reparacion
    import json
    try:
        from autenticar.models import Gauser_extra
    except:
        from centros_educativos.models import Gauser_extra
    data = serializers.serialize('json', Reparacion.objects.all())
    data_json = json.load(data)
    for d in data_json:
        if d['fields']['detecta']:
            d['fields']['detecta'] = Gauser_extra.objects.get(id=d['fields']['detecta']).gauser.dni
            d['fields']['detecta']
    # data = json.dumps(data_json)
    with open('data_reparaciones.json', 'w') as outfile:
        json.dump(data, outfile)
        # outfile.write(data)


def load_reparaciones_data_json(fichero):
    """
    :param fichero: String. Texto con la ruta del fichero. Ejemplo: './media/data_ficheros_registros.json'
    :return: Boolean. Si todo ha ido bien devuelve True
    El fichero se puede crear mediante la serialización de datos. Ejemplo:

    """
    with open(fichero) as json_data:
        for deserialized_object in serializers.deserialize("json", json_data):
            deserialized_object.save()
    return True


def serialize_gauser():
    from django.core import serializers
    from autenticar.models import Gauser
    # data = serializers.serialize("json", Gauser.objects.all(), fields=(
    # 'sexo', 'dni', 'address', 'postalcode', 'localidad', 'provincia', 'nacimiento', 'telfij', 'telmov', 'familia'))
    data = serializers.serialize("json", Gauser.objects.all())
    with open('data_gausers.json', 'w') as outfile:
        outfile.write(data)
