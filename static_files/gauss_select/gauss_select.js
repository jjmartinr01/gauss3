(function ($) {
    $.fn.gauss_select = function (options) {

        var settings = $.extend({
            title_buscar: 'Búsqueda por texto',
            title_buscando: 'Cargando la búsqueda solicitada ...',
            id_action: 'action', //Es el id sobre el que se almacena val_action <input type='hidden' id='#{{id_action}}' value='{{val_action}}'>
            val_action: 'buscar_ajax',
            create_action: false, //Si se crea automáticamente o no el input hidden con el id_action
            placeholder: 'Escribe parte del texo para comenzar la búsqueda',
            minimumInputLength: 3,
            url: '',
            dataType: 'json',
            quietMillis: 100,
            action_get: '',
            f_resultado: function (item) {
                return {text: item.text, id: item.id }
            },
            olist: true,
            ulist: true,
            indent: true,
            outdent: true,
            tcenter: true,
            tleft: true,
            tright: true,
            undo: true,
            redo: true,
            iimage: false,
            ilink: false,
            attach: false,
            changeview: true,
            table: true,
            height: 250,
            width: '95%'
        }, options);

        var id = $(this).attr('id');

        var bold = (settings.bold) ? '<a data-wysihtml5-command="bold" title="Negrita (CTRL+B)" class="gauss_editor_button"><i class="fa fa-bold"></i></a>' : '';
        var italic = (settings.italic) ? '<a data-wysihtml5-command="italic" title="Cursiva (CTRL+I)" class="gauss_editor_button"><i class="fa fa-italic"></i></a>' : '';
        var underline = (settings.underline) ? '<a data-wysihtml5-command="underline" title="Subrayado (CTRL+U)" class="gauss_editor_button"><i class="fa fa-underline"></i></a>' : '';

        var id_estilos = 'style_texto-' + id;
        var estilos = (settings.estilos) ? '<a  title="Define estilos" id="' + id_estilos + '" class="gauss_editor_button desplegable">Estilos</a>' +
            '<div class="style_texto contenedor" ><ul>' +
            '<li><a class="select_option" data-wysihtml5-command="formatBlock" data-wysihtml5-command-value="div"><span style="font-size: 100%"> Texto normal</span></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="formatBlock" data-wysihtml5-command-value="h1"><span style="font-size: 140%">Título de nivel 1</span></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="formatBlock" data-wysihtml5-command-value="h2"><span style="font-size: 130%">Título de nivel 2</span></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="formatBlock" data-wysihtml5-command-value="h3"><span style="font-size: 120%">Título de nivel 3</span></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="formatBlock" data-wysihtml5-command-value="h4"><span style="font-size: 110%">Título de nivel 4</span></a></li>' +
            '</ul></div>' : '';
        var id_tamano = 'size_texto-' + id;
        var tamano = (settings.tamano) ? '<a title="Tamaño de la fuente" id="' + id_tamano + '" class="gauss_editor_button desplegable"><i class="fa fa-text-height"></i></a>' +
            '<div class="size_texto contenedor"><ul>' +
            '<li><a class="select_option" data-wysihtml5-command="fontSize" data-wysihtml5-command-value="x-small"><span style="font-size: 60%"> Muy pequeño</span></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="fontSize" data-wysihtml5-command-value="small"><span style="font-size: 80%">Pequeño</span></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="fontSize" data-wysihtml5-command-value="medium"><span style="font-size: 100%">Normal</span></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="fontSize" data-wysihtml5-command-value="large"><span style="font-size: 120%">Grande</span></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="fontSize" data-wysihtml5-command-value="x-large"><span style="font-size: 140%">Muy grande</span></a></li>' +
            '</ul></div>' : '';
        var id_color = 'color_texto-' + id;
        var color = (settings.color) ? '<a title="Color de la fuente" id="' + id_color + '" class="gauss_editor_button desplegable"><i id="color_gauss_editor_button" class="fa fa-font"></i></a>' +
            '<div class="color_texto contenedor"><ul>' +
            '<li><a><div style="float: left;background-color: white; width:90px;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="black"><div id="black" class="elige_color" style="float: left;background-color: black;">&nbsp;</div></a> <a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="aqua"><div id="aqua" class="elige_color" style="float: left;background-color: aqua;">&nbsp;</div></a><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="blue"><div id="blue" class="elige_color" style="float: left;background-color: blue;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="gray"><div id="gray" class="elige_color" style="float: left;background-color: gray;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="green"><div id="green" class="elige_color" style="float: left;background-color: green;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="lime"><div id="lime" class="elige_color" style="float: left;background-color: lime;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="maroon"><div id="maroon" class="elige_color" style="float: left;background-color: maroon;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="navy"><div id="navy" class="elige_color" style="float: left;background-color: navy;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="olive"><div id="olive" class="elige_color" style="float: left;background-color: olive;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="purple"><div id="purple" class="elige_color" style="float: left;background-color: purple;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="red"><div id="red" class="elige_color" style="float: left;background-color: red;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="silver"><div id="silver" class="elige_color" style="float: left;background-color: #c0c0c0;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="teal"><div id="teal" class="elige_color" style="float: left;background-color: teal;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="white"><div id="white" class="elige_color" style="float: left;background-color: #ffffff;">&nbsp;</div></a></li>' +
            '<li><a class="select_option" data-wysihtml5-command="foreColor" data-wysihtml5-command-value="yellow"><div id="yellow" class="elige_color" style="float: left;background-color: #ffff00;">&nbsp;</div></a></li>' +
            '</ul></div>' : '';

        var olist = (settings.olist) ? '<a data-wysihtml5-command="insertOrderedList" class="gauss_editor_button" title="Inserta lista ordenada"><i class="fa fa-list-ol"></i></a>' : '';
        var ulist = (settings.ulist) ? '<a data-wysihtml5-command="insertUnorderedList" class="gauss_editor_button" title="Inserta lista de items"><i class="fa fa-list-ul"></i></a>' : '';
        var indent = (settings.indent) ? '<a data-wysihtml5-command="Indent" class="gauss_editor_button" title="Crea indentación"><i class="fa fa-indent"></i></a>' : '';
        var outdent = (settings.outdent) ? '<a data-wysihtml5-command="Outdent" class="gauss_editor_button" title="Elimina indentación"><i class="fa fa-outdent"></i></a>' : '';

        var tcenter = (settings.tcenter) ? '<a data-wysihtml5-command="justifyCenter" class="gauss_editor_button" title="Centrar texto"><i class="fa fa-align-center"></i></a>' : '';
        var tleft = (settings.tleft) ? '<a data-wysihtml5-command="justifyLeft" class="gauss_editor_button" title="Alinear texto a la izquierda"><i class="fa fa-align-left"></i></a>' : '';
        var tright = (settings.tright) ? '<a data-wysihtml5-command="justifyRight" class="gauss_editor_button" title="Alinear texto a la derecha"><i class="fa fa-align-right"></i></a>' : '';

        var undo = (settings.undo) ? '<a data-wysihtml5-command="undo" class="gauss_editor_button" title="Deshacer la última operación"><i class="fa fa-undo"></i></a>' : '';
        var redo = (settings.redo) ? '<a data-wysihtml5-command="redo" class="gauss_editor_button" title="Rehacer la última operación"><i class="fa fa-repeat"></i></a>' : '';

        var iimage = (settings.iimage) ? '<a data-wysihtml5-command="insertImage" class="gauss_editor_button" title="Insertar imagen"><i class="fa fa-picture-o"></i></a>' : '';
        var ilink = (settings.ilink) ? '<a data-wysihtml5-command="createLink" class="gauss_editor_button" title="Insertar un link"><i class="fa fa-link"></i></a>' +
            '<div style="display: none;" data-wysihtml5-dialog="createLink">' +
            '<label> Link: <input class="text" type="text" value="http://" data-wysihtml5-dialog-field="href" /> </label>' +
            '<a data-wysihtml5-dialog-action="save">OK</a>' +
            '<a data-wysihtml5-dialog-action="cancel">Cancel</a></div>' : '';
        var changeview = (settings.changeview) ? '<a data-wysihtml5-action="change_view" class="gauss_editor_button_code" title="Vista normal/Vista html"><i class="fa fa-code"></i></a>' : '';


        var attach = (settings.attach) ? '<a class="gauss_editor_button editor" id="attach_file" title="Adjuntar archivos"><i class="fa fa-paperclip"></i>Adjuntar</a>' : '';


        var id_table = 'wysihtml_table-' + id;
        var table = (settings.table) ? '\
        <a data-wysihtml5-command="createTable" class="gauss_editor_button" title="Crear tabla"><i class="fa fa-table"></i> Tabla</a>\
            <div class="block block_secondary" data-wysihtml5-hiddentools="table" style="display: none;">\
                <a data-wysihtml5-command="mergeTableCells" class="gauss_editor_button gauss_editor_button_secondary">Unir celdas</a>\
                <a data-wysihtml5-command="addTableCells" class="gauss_editor_button gauss_editor_button_secondary" data-wysihtml5-command-value="above" title="Insertar una fila por encima">Insertar &nbsp;<i class="fa fa-sort-up"></i></a>\
                <a data-wysihtml5-command="addTableCells" class="gauss_editor_button gauss_editor_button_secondary" data-wysihtml5-command-value="below" title="Insertar una fila por debajo">Insertar &nbsp;<i class="fa fa-sort-desc"></i></a>\
                <a data-wysihtml5-command="addTableCells" class="gauss_editor_button gauss_editor_button_secondary" data-wysihtml5-command-value="before" title="Insertar una columna por la izquierda">Insertar &nbsp;<i class="fa fa-caret-left"></i></a>\
                <a data-wysihtml5-command="addTableCells" class="gauss_editor_button gauss_editor_button_secondary" data-wysihtml5-command-value="after" title="Insertar una columna por la derecha">Insertar &nbsp;<i class="fa fa-caret-right"></i></a>\
                <a data-wysihtml5-command="deleteTableCells" class="gauss_editor_button gauss_editor_button_secondary" data-wysihtml5-command-value="row" title="Borrar la fila">Borrar fila</a>\
                <a data-wysihtml5-command="deleteTableCells" class="gauss_editor_button gauss_editor_button_secondary" data-wysihtml5-command-value="column" title="Borrar la columna">Borrar columna</a>\
            </div>\
        <div class="block_secondary" data-wysihtml5-dialog="createTable" style="display: none;">\
          <table><tbody><tr>\
          <td><span style="color: #333333;">Filas:</span></td> <td><input size="3" type="text" data-wysihtml5-dialog-field="rows" /></td><td rowspan="2"><a class="gauss_editor_button" data-wysihtml5-dialog-action="save" title="Crear la tabla"><i class="fa fa-check-circle"></i></a>&nbsp;<a class="gauss_editor_button" data-wysihtml5-dialog-action="cancel" title="Cancelar la tabla"><i class="fa fa-times-circle"></i></a></td></tr>\
          <tr><td><span style="color: #333333;">Columnas:</span></td> <td><input size="3" type="text" data-wysihtml5-dialog-field="cols" /></td>\
          </tr></tbody></table>\
        </div>' : '';


        var id_toolbar = 'wysihtml5-toolbar-' + id;
        var editor = '<input type="hidden" id="current_color" name="current_color" value="black">' +
            '<input type="hidden" id="gauss_editor_button_code" name="gauss_editor_button_code" value="0">' +
            '<div id="' + id_toolbar + '" style="display: none;"  class="wysihtml5-toolbar">' +
            bold + italic + underline + estilos + tamano + color + olist + ulist +
            indent + outdent + tcenter + tleft + tright + undo + redo + iimage + ilink + changeview + attach + table +
            '<div data-wysihtml5-dialog="insertImage" style="display: none; padding-top:15px;">' +
            '<label>' +
            ' Imagen:' +
            '<input data-wysihtml5-dialog-field="src" size="40" value="http://">' +
            '</label>' +
            '<a class="ok_imagen" data-wysihtml5-dialog-action="save">Aceptar <i class="fa fa-check"></i></a>' +
            '&nbsp;&nbsp;&nbsp;' +
            '<a class="cancel_imagen" data-wysihtml5-dialog-action="cancel">Cancelar <i class="fa fa-times"></i></a>' +
            '</div>' +
            '</div>';

        $('#' + id).css('height', settings.height);
        $('#' + id).css({width: settings.width, margin: '0 5px 5px 5px', border: '1px solid #CCCCCC', padding: '10px'});
        $(editor).insertBefore("#" + id);

        return new wysihtml5.Editor(id, {
            toolbar: id_toolbar,
            stylesheets: ["/static/gauss_editor/wysiwyg.css", "/static/gauss_editor/gauss_editor.css"],
            parserRules: wysihtml5ParserRules  //Carga la variable del fichero "parser_rules_gauss_editor.js"
        });

//        return editor; //Devolvemos el editor para hacer las operaciones que wysihtml5 permite hacer
    }

    $.fn.gauss_select.prototype.enable = function () {
        $(editor.composer.iframe).contents().find('.wysihtml5-editor').attr('contenteditable', 'true');
        $(".gauss_editor_button").css('color', '#333333');
        $("#gauss_editor_button_code").val(0);
        $("#color_gauss_editor_button").css('color', $("#current_color").val());
        $(".no_desplegable").addClass('desplegable');
        $(".desplegable").removeClass('no_desplegable');
        $(".gauss_editor_button_code").show();
    }

    $.fn.gauss_select.prototype.disable = function () {
        $(editor.composer.iframe).contents().find('.wysihtml5-editor').attr('contenteditable', 'false');
        $(".gauss_editor_button").css('color', '#bbbbbb');
        $("#color_gauss_editor_button").css('color', '#bbbbbb');
        $("#gauss_editor_button_code").val(1);
        $(".desplegable").addClass('no_desplegable');
        $(".no_desplegable").removeClass('desplegable');
        $(".gauss_editor_button_code").hide();
    }

}(jQuery));


$("#Contenido").on('click', '.desplegable', function () {
    // .position() uses position relative to the offset parent,
    // so it supports position: relative parent elements
    var clase = $(this).attr('id').split('-')[0];
    var pos = $(this).position();

    // .outerWidth() takes into account border and padding.
    var width = $(this).outerWidth();
    console.log("." + clase);
    $(this).next("div." + clase).css({
        position: "absolute",
        top: pos.top + "px",
        left: (pos.left + width) + "px"
    }).toggle();
});

$("#Contenido").on('click', '.select_option', function () {
    $(this).parent().parent().parent().toggle();
});

$("#Contenido").on('mouseleave', '.contenedor', function () {
    $(this).hide();
});

$("#Contenido").on('mouseover', '.elige_color', function () {
    var color_div = $(this).attr('id');
    $("#color_gauss_editor_button").css({
        color: color_div
    });
});

$("#Contenido").on('mouseleave', '.elige_color', function () {
    $("#color_gauss_editor_button").css('color', $("#current_color").val());
});

$("#Contenido").on('click', '.elige_color', function () {
    var color_div = $(this).attr('id');
    $("#current_color").val(color_div);
    $("#color_gauss_editor_button").css('color', color_div);
});

$("#Contenido").on('click', '.gauss_editor_button_code', function () {
    var color_div = $(this).attr('id');
    if ($("#gauss_editor_button_code").val() == '0') {
        $(".gauss_editor_button").css('color', '#bbbbbb');
        $("#color_gauss_editor_button").css('color', '#bbbbbb');
        $("#gauss_editor_button_code").val(1);
        $(".desplegable").addClass('no_desplegable');
        $(".no_desplegable").removeClass('desplegable');
    } else {
        $(".gauss_editor_button").css('color', '#333333');
        $("#gauss_editor_button_code").val(0);
        $("#color_gauss_editor_button").css('color', $("#current_color").val());
        $(".no_desplegable").addClass('desplegable');
        $(".desplegable").removeClass('no_desplegable');
    }
});

function disable_editor(editor) {
    $(editor.composer.iframe).contents().find('.wysihtml5-editor').attr('contenteditable', 'false');
    $(".gauss_editor_button").css('color', '#bbbbbb');
    $("#color_gauss_editor_button").css('color', '#bbbbbb');
    $("#gauss_editor_button_code").val(1);
    $(".desplegable").addClass('no_desplegable');
    $(".no_desplegable").removeClass('desplegable');
    $(".gauss_editor_button_code").hide();
}

function enable_editor(editor) {
    $(editor.composer.iframe).contents().find('.wysihtml5-editor').attr('contenteditable', 'true');
    $(".gauss_editor_button").css('color', '#333333');
    $("#gauss_editor_button_code").val(0);
    $("#color_gauss_editor_button").css('color', $("#current_color").val());
    $(".no_desplegable").addClass('desplegable');
    $(".desplegable").removeClass('no_desplegable');
    $(".gauss_editor_button_code").show();
}