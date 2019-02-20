(function ($) {
    $.fn.gaussFileAjaxUpload = function (options) {

        var id = $(this).attr('id');
        var id_a = id + 'gaussFileAjaxUpload';
        var gauss_fileList = id + 'gaussFileList';
        var gauss_file = id + 'gaussFile';
        var gauss_aviso = id + 'gauss_aviso';
        var a_click_posible = true;

        var settings = $.extend({
            texto_a: 'Pulsa aquí para subir ficheros',
            class_a: '',
            title_a: '',
            dinamic_a: false,
            id_a: id_a,
            action: 'FileUpload',
            accept: '',
            multiple: true,
            tipos: '*',
            ajaxFuncion: '',
            data1: '',
            data2: '',
            fileList: ''
        }, options);

        var a_tag = $('<a/>')
            .attr('id', settings.id_a)
            .html(settings.texto_a)
            .prop('title', settings.title_a);
        this.append(a_tag);

        var lista_ficheros = $('<div/>')
            .attr('id', gauss_fileList)
            .attr('style', 'list-style: none;')
            .html(settings.fileList);
        this.append(lista_ficheros);

        var aviso = $('<span/>')
            .attr('id', gauss_aviso)
            .attr('style', 'display: none;background-color: red;color: white;padding: 2px;');
        this.append(aviso);

        var input_file = $('<input/>').attr('type', 'file')
            .attr('name', gauss_file)
            .attr('id', gauss_file)
            .attr('multiple', settings.multiple)
            .attr('style', 'position:absolute; top:-3000px;')
            .attr('accept', settings.accept);
        this.append(input_file);

        a_tag.bind("click", function (e) {
            e.preventDefault();
            if (a_click_posible) {
                $('#' + gauss_file).trigger('click');
                a_click_posible = false;
            }
        });

        $('body').on('change', '#' + gauss_file, function () {
            var input_files = document.getElementById(gauss_file).files;
            $('#' + settings.id_a).html('Cargando ...');

            for (var i = 0; i < input_files.length; i++) {
                var file_xhr = input_files[i];
                if (settings.tipos.indexOf(file_xhr.type) > -1 || settings.tipos == '*') {
                    var formData = new FormData();
                    formData.append('fichero_xhr', file_xhr);
                    formData.append('action', settings.action);
                    formData.append('data1', settings.data1);
                    formData.append('data2', settings.data2);
                    formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
                    var xhr = new XMLHttpRequest();
                    xhr.open('POST', settings.ajaxFuncion, true);
                    xhr.onprogress = function (progreso) {
                        if (progreso.lengthComputable) {
                            window.console.log(progreso.loaded);
                            window.console.log(progreso.total);
                        }
                    };
                    xhr.onload = function () {
                        if (xhr.status === 200) {
                            if (settings.dinamic_a){
                                $('#' + settings.id_a).html(xhr.responseText);
                            }else{
                                $('#' + settings.id_a).html(settings.texto_a);
                                $('#' + gauss_fileList).html(xhr.responseText);
                            }
                        } else {
                            var mensaje = 'Error en la carga del archivo';
                            $('#' + gauss_aviso).html(mensaje).show();
                            setTimeout(function() { $('#' + gauss_aviso).hide(); }, 5000);
                        }
                        a_click_posible = true;
                    };
                    xhr.send(formData);
                } else {
                    a_click_posible = true;
                    $('#' + settings.id_a).html(settings.texto_a);
                    var mensaje = '<i class="fa fa-warning"></i> Sólo se aceptan ficheros: ' + settings.tipos;
                    $('#' + gauss_aviso).html(mensaje).show();
                    setTimeout(function() { $('#' + gauss_aviso).hide(); }, 5000);
                }
            }
        });
        return this;
    }
}(jQuery));


