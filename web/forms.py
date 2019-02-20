# -*- coding: utf-8 -*-

from django.forms import ModelForm, ModelMultipleChoiceField, ModelChoiceField, TextInput, DateField

from web.models import Template_web, T_Banded, Text_row, Cate_Blog, Post_Blog, T_Blog, File_web


class File_webForm(ModelForm):
    class Meta:
        model = File_web
        fields = ('fichero',)
        # Existing fields: entidad, fichero, content_type, fich_name

class Template_webForm(ModelForm):
    class Meta:
        model = Template_web
        fields = ('nombre', 'enlace_visible', 'home', 'publicar', 'html')
        # Existing fields: entidad, nombre, enlace_visible, home, publicar, html, creador

class Text_rowForm(ModelForm):
    class Meta:
        model = Text_row
        fields = ('title', 'imagen', 'texto', 'tipo')
        # Existing fields: title, image, texto, tipo


############# Banded #############
class T_BandedForm(ModelForm):
    class Meta:
        model = T_Banded
        fields = ('logo', 'imagen', 'copyr')
        # Existing fields: template_web, logo, image, text_rows, copyr


############# Blog #############
class Cate_BlogForm(ModelForm):
    class Meta:
        model = Cate_Blog
        fields = ('nombre',)
        # Existing fields: nombre, entidad

class Post_BlogForm(ModelForm):
    class Meta:
        model = Post_Blog
        fields = ('categoria', 'destacado')
        # Existing fields: categoria, autor, text_rows, destacado, creado

class T_BlogForm(ModelForm):
    class Meta:
        model = T_Blog
        fields = ('title', 'subtitle', 'copyr')
        # Existing fields: template_web, title, subtitle, post_blogs, copyr
