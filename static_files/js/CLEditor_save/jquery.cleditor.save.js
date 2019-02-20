(function($) {
  //Cuando se emplea este plugin es necesario que en el documento que lo carga se defina un input oculto:
  //  <input type="hidden" name="save_documento" id="save_documento" value="">
  //  Al pulsar el botón de guardado se producirá un evento change sobre '#save_documento' que permitirá hacer
  //  la acción que corresponda.
  
  // Definimos el icono que hará de botón
  $.cleditor.buttons.save = {
    name: "save",
    css: {
      backgroundImage: "URL(/static/images/document-save.gif)",
      backgroundPosition: "2px 2px",
      backgroundRepeat: "no-repeat",
    },
    title: "Guardar documento",
    command: "insertimage",
    buttonClick: function(e, data) { $('#save_documento').val('grabar').change();} };

  // Añadimos el botón a los controles existentes. Para que funcione es necesario que exista "| cut"
  $.cleditor.defaultOptions.controls = $.cleditor.defaultOptions.controls
    .replace("| cut", "save | cut");

})(jQuery);