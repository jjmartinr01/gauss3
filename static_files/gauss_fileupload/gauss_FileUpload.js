    (function ($) {
    $.fn.gaussFileUpload = function (options) {

        var settings = $.extend({
            tag_a: 'Pulsa aquí para subir ficheros',
            accept: '',
            multiple: true,
            tipos:'*'
        }, options);

        var id = $(this).attr('id');
        var gauss_SubirFichero = id + 'gauss_SubirFichero';
        var gauss_filesContainer = id + 'gauss_filesContainer';
        var gauss_list_file_inputs = id + 'gauss_list_file_inputs';
        var gauss_fileList = id + 'gauss_fileList';
        var gauss_files_created = id + 'gauss_files_created';
        var gauss_delete_file = id + 'gauss_delete_file';
        var gauss_file = id + 'gauss_file';
        var gauss_aviso = id + 'gauss_aviso';

        var a_tag = $('<a/>')
            .attr('id', gauss_SubirFichero)
            .html(settings.tag_a);
        this.append(a_tag);

        this.append($('<div/>')
                .attr('id', gauss_filesContainer)
        );
        this.append($('<input/>')
                .attr('type', 'hidden')
                .attr('name', gauss_list_file_inputs)
                .attr('id', gauss_list_file_inputs)
                .attr('value', '0')
        );
        this.append($('<ul/>')
                .attr('id', gauss_fileList)
                .attr('style', 'list-style: none;')
        );
        var aviso = $('<span/>')
                    .attr('id', gauss_aviso)
                    .attr('style', 'display: none;background-color: red;color: white;')
                    .html('&nbsp;<i class="fa fa-warning"></i> Sólo se aceptan ficheros: ' + settings.tipos + '&nbsp;');
        this.append(aviso
        );

        a_tag.bind("click", function (e) {
            e.preventDefault();
            // Es necesario que exista un input hidden con id="gauss_list_file_inputs":
            var new_element = parseInt($('#' + gauss_list_file_inputs).val()) + 1;
            $('#' + gauss_list_file_inputs).val(new_element);

            // En primer lugar se crea el nuevo input type file dentro de gauss_filesContainer
            $('#' + gauss_filesContainer).append(
                $('<input/>').attr('type', 'file')
                    .attr('name', gauss_file + new_element)
                    .attr('class', gauss_files_created)
                    .attr('id', gauss_file + new_element)
                    .attr('multiple', settings.multiple)
                    .attr('style', 'position:absolute; top:-3000px;')
                    .attr('accept',settings.accept)
            );

            $('#' + gauss_file + new_element).trigger('click');
        });

        $('body').on('change', '.' + gauss_files_created, function () {
            var id = $(this).attr('id');
            var input_file = document.getElementById(id);
            var ul = document.getElementById(gauss_fileList);
            var valido = true;
            while (ul.hasChildNodes()) {
                ul.removeChild(ul.firstChild);
            }
            $('.' + gauss_files_created).each(function () {
                    var id = $(this).attr('id');
                    var input = document.getElementById(id);
                    if (input.files.length > 0 && settings.tipos != '*' && input == input_file){
                        for (var i = 0; i < input.files.length; i++) {
                            var extension = input.files[i].name.split('.').pop();
                            window.console.log(settings.tipos);
                            window.console.log(extension);
                            if (settings.tipos.indexOf(extension) == -1){
                                valido = false;
                                $('#' + id).remove();
                                $('#' + gauss_aviso).show();
                                setTimeout(function() {
                                    $('#' + gauss_aviso).hide('blind', {}, 500)
                                }, 5000);
                            }
                        }
                    }
                    if (input.files.length > 0 && valido){
                        var tag_a = document.createElement('a');
                        tag_a.id = 'delete____' + id;
                        tag_a.className = gauss_delete_file;
                        var tag_i = document.createElement('i');
                        tag_i.className = 'fa fa-times';
                        var li = document.createElement("li");
                        li.className = id; //Para poder borrar el li a traves de la clase
                        var contenido_li = [];
                        for (var i = 0; i < input.files.length; i++) {
                            contenido_li.push(input.files[i].name + ' (' + input.files[i].size + ' bytes)');
                        }
                        tag_a.title = 'Elimar ' + contenido_li.join(', ');
                        var text_li = document.createTextNode(' ' + contenido_li.join(', '));
                        tag_a.appendChild(tag_i);
                        li.appendChild(tag_a);
                        li.appendChild(text_li);
                        ul.appendChild(li);
                    }
                }
            )
        });

        $('#' + id).on('click', '.' + gauss_delete_file, function (e) {
            e.preventDefault();
            var input_file_id = $(this).attr('id').split('____')[1];
            $('#' + input_file_id).remove();
            $('.' + input_file_id).remove();
            var new_element = parseInt($('#' + gauss_list_file_inputs).val()) - 1;
            $('#' + gauss_list_file_inputs).val(new_element);
        });

        return this;

    }
}(jQuery))


