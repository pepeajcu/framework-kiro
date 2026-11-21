/* Interacciones locales declarativas (data-ui-*).
 *
 * Para pestañas, paneles plegables, cajones/diálogos y copiar al portapapeles
 * que no necesitan un viaje al servidor (HTMX) ni justifican un <script> por
 * página (prohibido por J5). Usa delegación de eventos en `document`, así que
 * funciona también en fragmentos recién insertados por HTMX.
 *
 * Atributos soportados:
 *  - data-ui-toggle="<id|#selector>"   alterna `hidden` y `aria-expanded`
 *  - data-ui-tabs                      contenedor de pestañas:
 *      [data-ui-tab="<clave>"]           botón de pestaña (soporta flechas ←/→)
 *      [data-ui-panel="<clave>"]         panel asociado
 *  - data-ui-open="<id>"               abre un <dialog> (showModal) o drawer
 *  - data-ui-close                     cierra el <dialog> o [data-ui-drawer] ancestro
 *  - data-ui-copy="<texto|#id>"        copia al portapapeles y marca data-copied="true"
 */
(function () {
  "use strict";

  function resolveTarget(spec) {
    if (!spec) return null;
    if (spec.charAt(0) === "#" || spec.charAt(0) === ".") {
      return document.querySelector(spec);
    }
    return document.getElementById(spec);
  }

  function handleToggle(button) {
    var target = resolveTarget(button.getAttribute("data-ui-toggle"));
    if (!target) return;
    var willHide = !target.hasAttribute("hidden");
    if (willHide) {
      target.setAttribute("hidden", "");
    } else {
      target.removeAttribute("hidden");
    }
    button.setAttribute("aria-expanded", willHide ? "false" : "true");
  }

  function activateTab(tab) {
    var container = tab.closest("[data-ui-tabs]");
    if (!container) return;
    var key = tab.getAttribute("data-ui-tab");
    var tabs = container.querySelectorAll("[data-ui-tab]");
    for (var i = 0; i < tabs.length; i++) {
      var active = tabs[i] === tab;
      tabs[i].setAttribute("aria-selected", active ? "true" : "false");
      tabs[i].setAttribute("tabindex", active ? "0" : "-1");
    }
    var panels = container.querySelectorAll("[data-ui-panel]");
    for (var j = 0; j < panels.length; j++) {
      if (panels[j].getAttribute("data-ui-panel") === key) {
        panels[j].removeAttribute("hidden");
      } else {
        panels[j].setAttribute("hidden", "");
      }
    }
  }

  function setDrawerOpen(el, open) {
    if (typeof el.showModal === "function" && typeof el.close === "function") {
      if (open && !el.open) el.showModal();
      else if (!open && el.open) el.close();
      return;
    }
    if (open) {
      el.removeAttribute("hidden");
      el.setAttribute("aria-hidden", "false");
    } else {
      el.setAttribute("hidden", "");
      el.setAttribute("aria-hidden", "true");
    }
  }

  function handleCopy(button) {
    var spec = button.getAttribute("data-ui-copy") || "";
    var source = spec.charAt(0) === "#" ? resolveTarget(spec) : null;
    var text = source ? source.textContent || "" : spec;
    if (!navigator.clipboard || !text) return;
    navigator.clipboard.writeText(text).then(function () {
      button.setAttribute("data-copied", "true");
      window.setTimeout(function () {
        button.removeAttribute("data-copied");
      }, 1800);
    });
  }

  document.addEventListener("click", function (event) {
    var el = event.target instanceof Element ? event.target : null;
    if (!el) return;

    var toggle = el.closest("[data-ui-toggle]");
    if (toggle) {
      event.preventDefault();
      handleToggle(toggle);
      return;
    }

    var tab = el.closest("[data-ui-tab]");
    if (tab) {
      event.preventDefault();
      activateTab(tab);
      return;
    }

    var opener = el.closest("[data-ui-open]");
    if (opener) {
      var dialog = resolveTarget(opener.getAttribute("data-ui-open"));
      if (dialog) {
        event.preventDefault();
        setDrawerOpen(dialog, true);
      }
      return;
    }

    var closer = el.closest("[data-ui-close]");
    if (closer) {
      var host = closer.closest("dialog, [data-ui-drawer]");
      if (host) {
        event.preventDefault();
        setDrawerOpen(host, false);
      }
      return;
    }

    var copier = el.closest("[data-ui-copy]");
    if (copier) {
      event.preventDefault();
      handleCopy(copier);
    }
  });

  document.addEventListener("keydown", function (event) {
    var el = event.target instanceof Element ? event.target : null;
    if (!el) return;

    if (event.key === "Escape") {
      var openDrawers = document.querySelectorAll('[data-ui-drawer]:not([hidden])');
      for (var i = 0; i < openDrawers.length; i++) {
        setDrawerOpen(openDrawers[i], false);
      }
      return;
    }

    var tab = el.closest("[data-ui-tab]");
    if (!tab || (event.key !== "ArrowRight" && event.key !== "ArrowLeft")) return;
    var container = tab.closest("[data-ui-tabs]");
    if (!container) return;
    var tabs = Array.prototype.slice.call(container.querySelectorAll("[data-ui-tab]"));
    var idx = tabs.indexOf(tab);
    if (idx === -1) return;
    event.preventDefault();
    var next = tabs[(idx + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
    next.focus();
    activateTab(next);
  });
})();
