# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
from django.db import models

# from autenticar.models import Gauser, Gauser_extra
# from entidades.models import Entidad
from autenticar.models import Gauser
from entidades.models import Entidad, Gauser_extra, Subentidad

from gauss.funciones import pass_generator
from django.utils.text import slugify
from django.utils import timezone


class Noticia_web(models.Model):
    autor = models.ForeignKey(Gauser_extra, blank=True, null=True, on_delete=models.CASCADE)
    subentidad = models.ForeignKey(Subentidad, blank=True, null=True, on_delete=models.CASCADE)
    titulo = models.CharField('Texto del botón', max_length=100, blank=True, null=True)
    texto = models.TextField('Texto de la noticia', blank=True, null=True)
    publicar_from = models.DateField('Publicar desde', blank=True, null=True)
    publicar_to = models.DateField('Publicar hasta', blank=True, null=True)
    modified = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.created = timezone.now()
        self.modified = timezone.now()
        return super(Noticia_web, self).save(*args, **kwargs)

    def __str__(self):
        return u'%s (%s)' % (self.titulo, self.autor)

# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_noticia_file(instance, filename):
    nombre = filename.rpartition('.')
    instance.fich_name = filename.rpartition('/')[2]
    fichero = '%s.%s' %(slugify(instance.fich_name), nombre[2])
    return '/'.join(['web', str(instance.noticia.autor.entidad.code), fichero])


class File_noticia_web(models.Model):
    noticia = models.ForeignKey(Noticia_web, on_delete=models.CASCADE)
    code = models.CharField("Código del archivo que coincide con el nombre", max_length=50, blank=True, null=True)
    fichero = models.FileField("Fichero con información", upload_to=update_noticia_file, blank=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def __str__(self):
        return u'%s (%s - %s)' % (self.noticia.titulo, self.fichero, self.noticia.autor)


# Manejo de los ficheros subidos para que se almacenen con el nombre que deseo y no con el que originalmente tenían
def update_fichero(instance, filename):
    nombre = filename.rpartition('.')
    instance.fich_name = filename.rpartition('/')[2]
    fichero = pass_generator(size=20) + '.' + nombre[2]
    return '/'.join(['web', str(instance.entidad.code), fichero])


class File_web(models.Model):
    entidad = models.ForeignKey(Entidad, on_delete=models.CASCADE)
    fichero = models.FileField("Fichero con información", upload_to=update_fichero, blank=True)
    content_type = models.CharField("Tipo de archivo", max_length=200, blank=True, null=True)
    fich_name = models.CharField("Nombre del archivo", max_length=200, blank=True, null=True)

    def filename(self):
        f = os.path.basename(self.fichero.name)
        return os.path.split(f)[1]

    def __str__(self):
        return u'%s (%s - %s)' % (self.fichero, self.fich_name, self.entidad.name)


class Enlace_web(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    autor = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    texto = models.CharField('Texto del botón', max_length=100, blank=True, null=True)
    href = models.CharField('url a la que enlaza', max_length=200, blank=True, null=True)
    descripcion = models.CharField('Descripción informativa del enlace', max_length=300, blank=True, null=True)
    activo = models.BooleanField('Es tipo active?', default=False)
    padre = models.ForeignKey('self', null=True, blank=True, related_name='enlace_padre', on_delete=models.CASCADE)
    externo = models.BooleanField('Es un enlace a web externa?', default=False)
    orden = models.IntegerField('Orden en el que aparece', blank=True, null=True)

    class Meta:
        ordering = ['orden']

    def hijos(self):
        return Enlace_web.objects.filter(padre=self, entidad=self.entidad)
    def hermanos(self):
        return Enlace_web.objects.filter(padre=self.padre, entidad=self.entidad)

    def __str__(self):
        return u'%s (%s-%s)' % (self.entidad.name, self.texto, self.href)


class Top_bar(models.Model):
    TIPOS = (('', 'Normal'), ('fixed', 'Fija'), ('sticky', 'Pegada cuando se hace scroll'))
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    autor = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre de la top-bar', max_length=100, blank=True, null=True)
    href_nombre = models.CharField('url de enlace al hacer click en nombre', max_length=200, blank=True, null=True)
    buttons_web = models.ManyToManyField(Enlace_web, blank=True)
    contain_to_grid = models.BooleanField('La top-bar se ajusta a la rejilla', default=False)
    tipo = models.CharField('Tipo de posicionamiento', max_length=20, choices=TIPOS, blank=True, null=True)

    def __str__(self):
        return u'%s (%s)' % (self.entidad.name, self.nombre)


class Content_div(models.Model):
    NUM_COL = [[a, a] for a in range(1, 13)]
    TIPO = (('tipo_12t', 'Texto dispuesto en una columna'),
            ('tipo_6t6t', 'Texto dispuesto en dos columnas'),
            ('tipo_tipo_4t4t4t', 'Texto dispuesto en tres columnas'),
            ('tipo_12i', 'Imagen'),
            ('tipo_links_tab_h', 'Lista de enlaces horizontal'),
            ('tipo_links_button_h', 'Lista de enlaces a través de botones horizontal'),
            ('tipo_links_tab_v', 'Lista de enlaces vertical'),
            ('tipo_links_button_v', 'Lista de enlaces a través de botones vertical'),
            ('tipo_form_mail', 'Formulario de contacto a través de mail'),
            ('tipo_title_links', 'Cabecera: Título, subtítulo y enlaces'),
            ('tipo_image_links', 'Cabecera: Título, subtítulo y enlaces'),
            ('tipo_footer', 'Pie de página'),
            ('tipo_gauss', 'Login y password a tipo_gauss'),
    )
    ALIGN = (('text-justify', 'Alineación justificada'),
            ('text-center', 'Centrado'),
            ('text-left', 'Alineado a la izquierda'),
            ('text-right', 'Alineado a la derecha'),
    )
    PANEL = (('no-panel', 'Sin resaltar'),
            ('panel', 'Resaltado panel'),
            ('panel callout', 'Resaltado panel callout'),
    )
    ESQUINA = (('esquina', 'Esquinas cuadradas'),
            ('radius', 'Esquinas suaves'),
            ('round', 'Esquinas redondas'),
    )
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    autor = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    modificadores = models.TextField('Personas que han modificado este contenido', blank=True, null=True)
    large_columns = models.IntegerField("Número de columnas ocupadas en pantallas grandes", choices=NUM_COL, blank=True,
                                        null=True)
    medium_columns = models.IntegerField("Número de columnas ocupadas en pantallas grandes", choices=NUM_COL,
                                         blank=True, null=True)
    small_columns = models.IntegerField("Número de columnas ocupadas en pantallas grandes", choices=NUM_COL, blank=True,
                                        null=True)
    on_click = models.TextField('Javascript a ejecutar on-click', null=True, blank=True, default='')
    imagen = models.ForeignKey(File_web, blank=True, null=True, on_delete=models.CASCADE)
    caption = models.CharField("Texto pie de foto", max_length=300, blank=True, null=True, default='')
    title = models.CharField("Título del contenedor", max_length=300, blank=True, null=True, default='')
    subtitle = models.CharField("Subtítulo del contenedor", max_length=300, blank=True, null=True, default='')
    header_post = models.BooleanField('Este content_div es la cabecera de un post?', default=False)
    texto = models.TextField("Texto del párrafo", blank=True, null=True, default='')
    align = models.CharField("Alineación", blank=True, null=True, choices=ALIGN, max_length=20, default='text-justify')
    enlaces = models.ManyToManyField(Enlace_web, blank=True)
    tipo = models.CharField("Tipo de content_div", blank=True, null=True, choices=TIPO, max_length=20)
    orden = models.IntegerField("Número de orden dentro del Row_web", blank=True, null=True)
    panel = models.CharField("Tipo de panel", choices=PANEL, max_length=20, default='no-panel')
    esquinas =  models.CharField("Tipo de panel", choices=ESQUINA, max_length=20, default='esquina')
    creado = models.DateTimeField('Fecha y hora de creación', auto_now_add=True, null=True)

    @property
    def last(self):
        row_web = Row_web.objects.get(contents_div__in=[self])
        return row_web.contents_div.count() == self.orden
    @property
    def first(self):
        return self.orden == 1

    def enlaces_ordenados(self):
        return self.enlaces.all().order_by('orden')
        # return Enlace_web.objects.filter(id__in=self.enlaces.all()).order_by('orden')

    class Meta:
        ordering = ['orden']

    def __str__(self):
        row_web = Row_web.objects.get(contents_div__in=[self.id])
        if self.texto:
            texto = self.texto[:30] + '...'
        else:
            texto = ''
        return u'%s (%s), row: %s' % (texto, self.tipo, row_web)


class Row_web(models.Model):
    TIPOS_R = (('NORMAL', 'Fila central'), ('CABECERA', 'Fila en cabecera de página'), ('PIE', 'Fila en pie de página'),
               ('IZQUIERDA', 'Fila en lateral izquierdo'), ('DERECHA', 'Fila en lateral derecho'))
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    autor = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    contents_div = models.ManyToManyField(Content_div, blank=True)
    hr_before = models.BooleanField("Colocar una línea de separación antes del contenido", default=False)
    hr_after = models.BooleanField("Colocar una línea de separación después del contenido", default=False)
    orden = models.IntegerField("Número de orden dentro del Html_web", blank=True, null=True)
    tipo = models.CharField("Tipo de fila", max_length=20, choices=TIPOS_R, default='NORMAL')
    # cabecera = models.BooleanField("Es la fila cabecera de la web", default=False)
    # pie = models.BooleanField("Es el pie de página de la web", default=False)

    @property
    def row_mail_exists(self):
        html_web = Html_web.objects.get(rows_web__in=[self])
        return  Content_div.objects.filter(row_web__html_web=html_web, tipo='tipo_form_mail').count() > 0
    @property
    def row_tipo_gauss_exists(self):
        html_web = Html_web.objects.get(rows_web__in=[self])
        return  Content_div.objects.filter(row_web__html_web=html_web, tipo='tipo_gauss').count() > 0
    @property
    def row_topbar_exists(self):
        html_web = Html_web.objects.get(rows_web__in=[self])
        return html_web.rows_web.filter(tipo='top_bar').count() > 0
    @property
    def last(self):
        html_web = Html_web.objects.get(rows_web__in=[self])
        return html_web.rows_web.filter(tipo=self.tipo).count() == self.orden
    @property
    def first(self):
        return self.orden == 1

    class Meta:
        ordering = ['orden']

    def __str__(self):
        html_web = Html_web.objects.get(rows_web__in=[self.id])
        return u'orden: %s, html_web: %s' % (self.orden, html_web)


class Categoria_web(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField("Nombre de la categoría", max_length=100, blank=True, null=True)

    def __str__(self):
        return u'%s (%s)' % (self.nombre, self.entidad.name)


class Legal_web(models.Model):
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    editores_legales = models.ManyToManyField(Gauser, blank=True)
    aviso_legal = models.TextField('Aviso legal', blank=True, null=True)
    privacidad = models.TextField('Política de privacidad', blank=True, null=True)

    def __str__(self):
        return u'Documentos legales de %s' % (self.entidad.name)

TIPOS_dict = {'NORMAL': 'Página normal', 'POST': 'Es un post', 'POST_LIST': 'Es la lista de post',
              'COMPRAVENTA': 'Venta de productos'}
class Html_web(models.Model):
    TIPOS = [[a, b] for a, b in TIPOS_dict.items()]
    entidad = models.ForeignKey(Entidad, blank=True, null=True, on_delete=models.CASCADE)
    autor = models.ForeignKey(Gauser, blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField('Nombre de la página', max_length=100, blank=True, null=True)
    home = models.BooleanField("Es el Home?", default=False)
    publicar = models.BooleanField("Lista para publicar?", default=False)
    html = models.OneToOneField(File_web, blank=True, null=True, on_delete=models.CASCADE)
    css = models.ManyToManyField(File_web, blank=True, related_name='ficheros_css')
    js = models.ManyToManyField(File_web, blank=True, related_name='ficheros_js')
    editores = models.ManyToManyField(Gauser, blank=True, related_name='editores')
    rows_web = models.ManyToManyField(Row_web, blank=True)
    contents_right = models.ManyToManyField(Content_div, blank=True)
    top_bar = models.ForeignKey(Top_bar, blank=True, null=True, on_delete=models.CASCADE)
    categorias = models.ManyToManyField(Categoria_web, blank=True)
    tipo = models.CharField("Tipo de página", max_length=20, choices=TIPOS, default='NORMAL')
    col_izq = models.IntegerField('Número de columnas en el lateral izquierdo', default=0)
    col_cen = models.IntegerField('Número de columnas en el centro', default=12)
    col_der = models.IntegerField('Número de columnas en el lateral derecho', default=0)
    creado = models.DateTimeField('Fecha y hora de creación', auto_now_add=True, null=True)
    modificado = models.DateTimeField('Fecha y hora de modificación', auto_now=True, null=True)

    def __str__(self):
        return u'%s (%s)-%s' % (self.nombre, ['No es home', 'Es el home'][self.home], self.entidad.name)