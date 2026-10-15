/* Avisos de HTMX que el servidor no puede dar.
 *
 * Un fallo de red, una petición que caduca o la página de error de un proxy (502, 503,
 * 504) no llegan al manejador de errores de la app, así que no traen el toast del
 * servidor (app/hypermedia.py). Sin esto, el botón "no hace nada". Aquí se escucha lo
 * que htmx ya avisa y se pinta el mismo toast de Basecoat en #toaster.
 *
 * Reglas:
 *  - Solo lo que el servidor NO cubre: un código que htmx intercambia
 *    (htmx.config.responseHandling, ver el <meta name="htmx-config"> de base.html) ya
 *    trae su propio toast, y repetirlo sería ruido.
 *  - El texto se escribe con textContent, nunca con innerHTML: la API de toasts de
 *    Basecoat no escapa, y esto tampoco debe poder inyectar nada.
 *  - Un mismo aviso no se repite mientras el anterior siga a la vista.
 * Sin dependencias ni estado: un archivo por proyecto, no un script por página.
 */
(function () {
  "use strict";

  var ERROR_ICON =
    '<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" ' +
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/>' +
    '<path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>';

  var MESSAGES = {
    network: ["Sin conexión", "No hemos podido contactar con el servidor. Comprueba tu conexión e inténtalo de nuevo."],
    timeout: ["La petición tardó demasiado", "Inténtalo de nuevo en unos segundos."],
    server: ["El servidor no responde", "Inténtalo de nuevo en unos minutos."],
    other: ["No se pudo completar la acción", "Inténtalo de nuevo."],
  };

  function showError(kind) {
    var toaster = document.getElementById("toaster");
    if (!toaster) return;
    var message = MESSAGES[kind] || MESSAGES.other;

    // The same notice, still on screen: do not stack copies of it.
    var shown = toaster.querySelectorAll('.toast:not([aria-hidden="true"]) h2');
    for (var i = 0; i < shown.length; i++) {
      if (shown[i].textContent === message[0]) return;
    }

    var toast = document.createElement("div");
    toast.className = "toast";
    toast.setAttribute("role", "alert");
    toast.setAttribute("aria-atomic", "true");
    toast.setAttribute("aria-hidden", "false");
    toast.setAttribute("data-category", "error");

    var content = document.createElement("div");
    content.className = "toast-content";
    content.innerHTML = ERROR_ICON; // a constant of this file, never user text

    var section = document.createElement("section");
    var title = document.createElement("h2");
    title.textContent = message[0];
    var detail = document.createElement("p");
    detail.textContent = message[1];
    section.appendChild(title);
    section.appendChild(detail);
    content.appendChild(section);
    toast.appendChild(content);
    toaster.appendChild(toast); // Basecoat initialises it and closes it after a few seconds
  }

  /* Whether htmx swaps this status: if it does, the server already answered with a toast
     or a fragment, and there is nothing to add. */
  function isSwapped(status) {
    var rules = (window.htmx && window.htmx.config && window.htmx.config.responseHandling) || [];
    for (var i = 0; i < rules.length; i++) {
      if (new RegExp(rules[i].code).test(String(status))) return !!rules[i].swap;
    }
    return false;
  }

  document.addEventListener("htmx:sendError", function () {
    showError("network");
  });

  document.addEventListener("htmx:timeout", function () {
    showError("timeout");
  });

  document.addEventListener("htmx:responseError", function (event) {
    var xhr = event.detail && event.detail.xhr;
    var status = xhr ? xhr.status : 0;
    if (isSwapped(status)) return;
    showError(status >= 500 ? "server" : "other");
  });
})();
