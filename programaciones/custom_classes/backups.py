# from jinja2 import Environment, FileSystemLoader
from django.template.loader import render_to_string
from ..models import *


class BkProgsec:  # sag
    def __init__(self, progsec_id):
        self.id = progsec_id
        self.xmlContent = None

    def generarXML(self, progsec):
        progsec = ProgSec.objects.get(id=self.id)
        contexto = {
            'progsec': progsec,
        }
        self.xmlContent = render_to_string("bkprogsec.xml", context=contexto)
        return self.xmlContent

