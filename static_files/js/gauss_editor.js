function wysihtmleditor(id, options) {

    var settings = $.extend({
        bold: true,
        italic: true,
        underline: true,
        estilos: false,
        tamano: false,
        color: false,
        olist: true,
        ulist: true,
        indent: false,
        outdent: false,
        tcenter: false,
        tleft: false,
        tright: false,
        undo: true,
        redo: true,
        iimage: false,
        ilink: false,
        attach: false,
        changeview: true,
        height: 250
    }, options)

    var bold = (settings.bold) ? '<li><a data-wysihtml5-command="bold" data-tooltip title="Negrita (CTRL+B)" class="button secondary editor"><i class="fa fa-bold"></i></a></li>' : '';
    var italic = (settings.italic) ? '<li><a data-wysihtml5-command="italic" data-tooltip title="Cursiva (CTRL+I)" class="button secondary editor"><i class="fa fa-italic"></i></a></li>' : '';
    var underline = (settings.underline) ? '<li><a data-wysihtml5-command="underline" data-tooltip title="Subrayado (CTRL+U)" class="button secondary editor"><i class="fa fa-underline"></i></a></li>' : '';

    var id_estilos = 'estilos_texto-' + id;
    var estilos = (settings.estilos) ? '<li><a data-dropdown="' + id_estilos + '" class="secondary button dropdown editor" data-options="is_hover:true">Estilos</a><br>' +
        '<ul id="' + id_estilos + '" data-dropdown-content class="f-dropdown">' +
        '<li><a data-wysihtml5-command="formatBlock" data-wysihtml5-command-value="div"><span style="font-size: 100%"> Texto normal</span></a></li>' +
        '<li><a data-wysihtml5-command="formatBlock" data-wysihtml5-command-value="h1"><span style="font-size: 140%">Título de nivel 1</span></a></li>' +
        '<li><a data-wysihtml5-command="formatBlock" data-wysihtml5-command-value="h2"><span style="font-size: 130%">Título de nivel 2</span></a></li>' +
        '<li><a data-wysihtml5-command="formatBlock" data-wysihtml5-command-value="h3"><span style="font-size: 120%">Título de nivel 3</span></a></li>' +
        '<li><a data-wysihtml5-command="formatBlock" data-wysihtml5-command-value="h4"><span style="font-size: 110%">Título de nivel 4</span></a></li>' +
        '</ul></li>' : '';
    var id_tamano = 'size_texto-' + id;
    var tamano = (settings.tamano) ? '<li><a data-dropdown="' + id_tamano + '" class="secondary button dropdown editor" data-options="is_hover:true"><i class="fa fa-text-height"></i></a><br>' +
        '<ul id="size_texto-' + id + '" data-dropdown-content class="f-dropdown">' +
        '<li><a data-wysihtml5-command="fontSize" data-wysihtml5-command-value="x-small"><span style="font-size: 60%"> Muy pequeño</span></a></li>' +
        '<li><a data-wysihtml5-command="fontSize" data-wysihtml5-command-value="small"><span style="font-size: 80%">Pequeño</span></a></li>' +
        '<li><a data-wysihtml5-command="fontSize" data-wysihtml5-command-value="medium"><span style="font-size: 100%">Normal</span></a></li>' +
        '<li><a data-wysihtml5-command="fontSize" data-wysihtml5-command-value="large"><span style="font-size: 120%">Grande</span></a></li>' +
        '<li><a data-wysihtml5-command="fontSize" data-wysihtml5-command-value="x-large"><span style="font-size: 140%">Muy grande</span></a></li>' +
        '</ul></li>' : '';
    var id_color = 'color_texto-' + id;
    var color = (settings.color) ? '<li><a data-dropdown="' + id_color + '" class="secondary button dropdown  editor" data-options="is_hover:true"><i id="color_button" class="fa fa-font"></i></a>' +
        '<ul id="color_texto-' + id + '" data-dropdown-content class="f-dropdown">' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="black"><div id="black" class="elige_color" style="float: left;background-color: black;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="aqua"><div id="aqua" class="elige_color" style="float: left;background-color: aqua;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="blue"><div id="blue" class="elige_color" style="float: left;background-color: blue;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="gray"><div id="gray" class="elige_color" style="float: left;background-color: gray;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="green"><div id="green" class="elige_color" style="float: left;background-color: green;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="lime"><div id="lime" class="elige_color" style="float: left;background-color: lime;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="maroon"><div id="maroon" class="elige_color" style="float: left;background-color: maroon;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="navy"><div id="navy" class="elige_color" style="float: left;background-color: navy;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="olive"><div id="olive" class="elige_color" style="float: left;background-color: olive;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="purple"><div id="purple" class="elige_color" style="float: left;background-color: purple;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="red"><div id="red" class="elige_color" style="float: left;background-color: red;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="silver"><div id="silver" class="elige_color" style="float: left;background-color: #c0c0c0;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="teal"><div id="teal" class="elige_color" style="float: left;background-color: teal;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="white"><div id="white" class="elige_color" style="float: left;background-color: #ffffff;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '<li><a data-wysihtml5-command="foreColor" data-wysihtml5-command-value="yellow"><div id="yellow" class="elige_color" style="float: left;background-color: #ffff00;width: 15px;height: 15px;">&nbsp;</div></a></li>' +
        '</ul></li>' : '';

    var olist = (settings.olist) ? '<li><a data-wysihtml5-command="insertOrderedList" class="button secondary editor" data-tooltip title="Inserta lista ordenada"><i class="fa fa-list-ol"></i></a></li>' : '';
    var ulist = (settings.ulist) ? '<li><a data-wysihtml5-command="insertUnorderedList" class="button secondary editor" data-tooltip title="Inserta lista de items"><i class="fa fa-list-ul"></i></a></li>' : '';
    var indent = (settings.indent) ? '<li><a data-wysihtml5-command="Indent" class="button secondary editor" data-tooltip title="Crea indentación"><i class="fa fa-indent"></i></a></li>' : '';
    var outdent = (settings.outdent) ? '<li><a data-wysihtml5-command="Outdent" class="button secondary editor" data-tooltip title="Elimina indentación"><i class="fa fa-outdent"></i></a></li>' : '';

    var tcenter = (settings.tcenter) ? '<li><a data-wysihtml5-command="justifyCenter" class="button secondary editor" data-tooltip title="Centrar texto"><i class="fa fa-align-center"></i></a></li>' : '';
    var tleft = (settings.tleft) ? '<li><a data-wysihtml5-command="justifyLeft" class="button secondary editor" data-tooltip title="Alinear texto a la izquierda"><i class="fa fa-align-left"></i></a></li>' : '';
    var tright = (settings.tright) ? '<li><a data-wysihtml5-command="justifyRight" class="button secondary editor" data-tooltip title="Alinear texto a la derecha"><i class="fa fa-align-right"></i></a></li>' : '';

    var undo = (settings.undo) ? '<li><a data-wysihtml5-command="undo" class="button secondary editor" data-tooltip title="Deshacer la última operación"><i class="fa fa-undo"></i></a></li>' : '';
    var redo = (settings.redo) ? '<li><a data-wysihtml5-command="redo" class="button secondary editor" data-tooltip title="Rehacer la última operación"><i class="fa fa-repeat"></i></a></li>' : '';

    var iimage = (settings.iimage) ? '<li><a data-wysihtml5-command="insertImage" class="button secondary editor" data-tooltip title="Insertar imagen"><i class="fa fa-picture-o"></i></a></li>' : '';
    var ilink = (settings.ilink) ? '<li><a data-wysihtml5-command="createLink" class="button secondary editor" data-tooltip title="Insertar un link"><i class="fa fa-link"></i></a></li>' : '';
    var changeview = (settings.changeview) ? '<li><a data-wysihtml5-action="change_view" class="button secondary editor" data-tooltip title="Vista normal/Vista html"><i class="fa fa-code"></i></a></li>' : '';


    var attach = (settings.attach) ? '<li><a class="button editor" id="attach_file" data-tooltip title="Adjuntar archivos"><i class="fa fa-paperclip"></i>Adjuntar</a></li>' : '';


    id_toolbar = 'wysihtml5-toolbar-' + id;
    var editor = '<div class="row">' +
        '<div id="' + id_toolbar + '" style="display: none;" class="large-12 columns">' +
        '<div class="button-bar editor">' +
        '<ul class="button-group radius">' + bold + italic + underline + '</ul>' +
        '<ul class="button-group radius">' + estilos + tamano + color + '</ul>' +
        '<ul class="button-group radius">' + olist + ulist + indent + outdent + '</ul>' +
        '<ul class="button-group radius">' + tcenter + tleft + tright + '</ul>' +
        '<ul class="button-group radius">' + undo + redo + '</ul>' +
        '<ul class="button-group radius">' + iimage + ilink + changeview + '</ul>' +
        '<ul class="button-group radius">' + attach + '</ul>' +
        '</div>' +
        '<div data-wysihtml5-dialog="createLink" style="display: none;">' +
        '<label>' +
        'Link:' +
        '<input data-wysihtml5-dialog-field="href" value="http://">' +
        '</label>' +
        '<a data-wysihtml5-dialog-action="save">' +
        '<i class="fa fa-check"></i>' +
        'Aceptar</a>' +
        '&nbsp;&nbsp;' +
        '<a data-wysihtml5-dialog-action="cancel">' +
        '<i class="fa fa-times"></i>' +
        'Cancelar</a>' +
        '</div>' +
        '<div data-wysihtml5-dialog="insertImage" style="display: none;">' +
        '<label>' +
        'Image:' +
        '<input data-wysihtml5-dialog-field="src" value="http://">' +
        '</label>' +
        '<a data-wysihtml5-dialog-action="save">' +
        '<i class="fa fa-check"></i>' +
        'Aceptar</a>' +
        '&nbsp;&nbsp;' +
        '<a data-wysihtml5-dialog-action="cancel">' +
        '<i class="fa fa-times"></i>' +
        'Cancelar</a>' +
        '</div>' +
        '</div>' +
        '</div>'

    $('#' + id).css('height', settings.height);
    $(editor).insertBefore("#" + id);

    var editor = new wysihtml5.Editor(id, {
        toolbar: id_toolbar,
        stylesheets: "/static/css/wysiwyg.css",
        parserRules: wysihtml5ParserRules
    });

    if (settings.estilos) {
        $('#' + id_estilos).foundation({dropdown: {is_hover: true}});
    } else {
        if (settings.tamano) {
            $('#' + id_tamano).foundation({dropdown: {is_hover: true}});
        } else {
            if (settings.color) {
                $('#' + id_color).foundation({dropdown: {is_hover: true}});
            }
        }

    }
    $('.elige_color').click(function () {
        $('#color_button').css('color', this.id);
    })
    // Habilitar las acciones javascript foundation para el documento
    $(document).foundation();

    return editor; //Devolvemos el editor para hacer las operaciones que wysihtml5 permite hacer
}