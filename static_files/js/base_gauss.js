function visualizar(identificadores) {
    for (i in identificadores) {
        $('#' + identificadores[i]).removeClass('oculto');
    }
}

// removes MS Office generated guff
// code from Mark Brown: http://www.sitepoint.com/forums/showthread.php?858386-Strip-Unwanted-Formatting-from-Pasted-Content
function removeWordTags(string) {
    var input = string;
    // 1. remove line breaks / Mso classes
    var stringStripper = /(\n|\r| class=(")?Mso[a-zA-Z]+(")?)/g;
    var output = input.replace(stringStripper, '');
    // 2. strip Word generated HTML comments
    var commentSripper = new RegExp('<!--(.*?)-->', 'g');
    var output = output.replace(commentSripper, ' ');
    var tagStripper = new RegExp('<(/)*(meta|link|span|\\?xml:|st1:|o:|font)(.*?)>', 'gi');
    // 3. remove tags leave content if any
    output = output.replace(tagStripper, ' ');
    // 4. Remove everything in between and including tags style, ...
    var badTags = ['style', 'script', 'applet', 'embed', 'noframes', 'noscript'];
    for (var i = 0; i < badTags.length; i++) {
        tagStripper = new RegExp('<' + badTags[i] + '.*?' + badTags[i] + '(.*?)>', 'gi');
        output = output.replace(tagStripper, ' ');
    }
    // 5. remove attributes ' style="..."'
    var badAttributes = ['style', 'start'];
    for (var i = 0; i < badAttributes.length; i++) {
        var attributeStripper = new RegExp(' ' + badAttributes[i] + '="(.*?)"', 'gi');
        output = output.replace(attributeStripper, ' ');
    }
    // 6. remove multiple space by only one space
    output = output.replace('/ \s + / g', ' '); //Reemplazar los dobles espacios que se pudieran haber producido.
    //this.textarea.value = output;
    return output;
}

function charge_on_ready() {

    $(document).ajaxStart(function () {
        $('#ajax-loader').show();
    }).ajaxStop(function () {
        $('#ajax-loader').hide();
    });

    var csrftoken = $.cookie('csrftoken');

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    $('#volver').click(function () {
        javascript:history.go(-1);
    });
}

function habilita(iconos) {
    for (var i in iconos) {
        var p = iconos[i].split('_');
        if (p[0] == 'h') {
            $('#' + p[1] + '_sign').addClass('disabled');
            $('#' + p[1] + '_li').addClass('hide');
        } else {
            $('#' + p[1] + '_sign').removeClass('disabled');
            $('#' + p[1] + '_li').removeClass('hide');
        }
    }
}

function show_avisos() {
    return $.post('/get_avisos/', {}, function (data) {
        if (data != '') {
            $('#reveal_lista_avisos').html(data);
            $('#reveal_modal_aviso').foundation('reveal', 'open');
        }
    });
}

function    show_mensajes(options) {
    var settings = $.extend({title: '', texto: '', bajo_texto: '', buttons: false, size: 'small'}, options);
    $('#mensajes_gauss_title').html(settings.title);
    $('#mensajes_gauss_texto').html(settings.texto);
    $('#mensajes_gauss_bajo_texto').html(settings.bajo_texto);

    var botones = '';
    if (settings.buttons) {
        for (b in settings.buttons) {
            botones += '<a id="' + b.replace(/\W/g, '') + '" data-reveal-id="secondModal" class="secondary button">' +
            b + '</a>&nbsp;&nbsp;&nbsp;' + '<script>$("#' + b.replace(/\W/g, '') + '").click(' + settings.buttons[b] + ')</script>'
        }

    }
    $('#mensajes_gauss_buttons').html(botones);
    $('#mensajes_gauss').addClass(settings.size);
    $('#mensajes_gauss').foundation('reveal', 'open');
    window.console.log('Mostrando mensaje');
}

function hide_mensajes() {
    $('#mensajes_gauss').foundation('reveal', 'close');
    window.console.log('Ocultando mensaje');
}

function descarga_archivo(options) {
    var settings = $.extend({
        url: '',
        pre_texto: '',
        pre_title: '',
        fail_texto: 'Se ha producido un error en la descarga, inténtalo de nuevo más tarde',
        fail_title: 'Error de descarga',
        formname: ''
    }, options)
    $.fileDownload(settings.url, {
        prepareCallback: function () {
            $('#ajax-loader').show();
            if (settings.pre_title.length > 1 || settings.pre_texto.length > 1) {
                show_mensajes({title: settings.pre_title, texto: settings.pre_texto});
            }
        },
        successCallback: function () {
            $('#ajax-loader').hide();
            hide_mensajes();
            show_avisos();
        },
        failCallback: function () {
            $('#ajax-loader').hide();
            if (settings.fail_title.length > 1 || settings.fail_texto.length > 1) {
                show_mensajes({title: settings.fail_title, texto: settings.fail_texto});
            }
        },
        httpMethod: "POST",
        data: $('#' + settings.formname).serialize()
    })
}

function sube_archivo(options) {
    var settings = $.extend({
        gauss_file:'',
        cargando: 'Cargando ...',
        action: 'FileUpload',
        tipos: '*',
        ajaxFuncion: '',
        data1: '',
        data2: '',
        onOk: function (data){alert(data);},
        onError: function (data){alert(data);}
    }, options);

    var input_files = document.getElementById(settings.gauss_file).files;
    show_mensajes({title: settings.cargando});
    window.console.log('Cargando...');
    for (var i = 0; i < input_files.length; i++) {
        var file_xhr = input_files[i];
        if (settings.tipos.indexOf(file_xhr.type) > -1 || settings.tipos == '*') {
            window.console.log('Tipos correctos');
            var formData = new FormData();
            formData.append('fichero_xhr', file_xhr);
            formData.append('action', settings.action);
            window.console.log('Action: ' + settings.action);
            formData.append('data1', settings.data1);
            formData.append('data2', settings.data2);
            formData.append('tipos', settings.tipos);
            formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
            var xhr = new XMLHttpRequest();
            xhr.open('POST', settings.ajaxFuncion, false);
            window.console.log('Función Ajax: ' + settings.ajaxFuncion);
            xhr.onprogress = function (progreso) {
                if (progreso.lengthComputable) {
                    window.console.log(progreso.loaded);
                    window.console.log(progreso.total);
                }
            };
            xhr.onload = function () {
                if (xhr.status === 200) {
                    window.console.log('Carga correcta');
                    if (settings.onOK != ''){
                        settings.onOk(xhr.responseText);
                        window.console.log('onOK ejecutado');
                        hide_mensajes();
                    }else{
                        hide_mensajes();
                        settings.onError(xhr.responseText);
                    }
                } else {
                    hide_mensajes();
                    window.console.log('Error en la carga');
                    var mensaje = 'Error en la carga del archivo';
                    show_mensajes({title: mensaje});
                    setTimeout(function () {
                        hide_mensajes();
                    }, 5000);
                }
            };
            xhr.send(formData);
        } else {
            window.console.log('Tipo de archivo erróneo');
            hide_mensajes();
            var mensaje = '<i class="fa fa-warning"></i> Sólo se aceptan ficheros: ' + settings.tipos;
            show_mensajes({title:mensaje})
            setTimeout(function () {
                hide_mensajes();
            }, 5000);
        }
    }
    window.console.log('LLega el final');
}

