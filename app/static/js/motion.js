/*! Kiro motion: movimiento declarativo al hacer scroll. Sin dependencias.
 *
 * La página solo escribe atributos; nunca JavaScript propio:
 *
 *   <h1 data-motion="split-reveal">…</h1>
 *   <ul data-motion="stagger" data-motion-delay="0.08">…</ul>
 *
 * Valores de este archivo (nivel de motion 4 o más):
 *   reveal        aparece al entrar en pantalla        (data-motion-delay en s)
 *   stagger       los hijos entran en cascada          (data-motion-delay = paso)
 *   split-reveal  el titular sube palabra a palabra    (texto sin etiquetas dentro)
 *   count         cuenta hasta data-motion-to          (el elemento solo lleva el número)
 *   marquee       banda de contenido que corre         (data-motion-speed = segundos)
 * Los niveles 7+ añaden valores mediante adaptadores (motion-lib.js, motion-gsap.js)
 * que se registran con kiroMotion.register(nombre, función).
 *
 * Contrato (docs/decisions/0015-motion-vendorizado-por-niveles.md):
 *  - Un estado oculto solo existe bajo la clase `js-motion`, que pone este
 *    script. Sin JS, o con prefers-reduced-motion, todo el contenido se ve.
 *  - Funciona con HTMX: arma el contenido nuevo (htmx:load) y limpia el que sale
 *    (htmx:beforeCleanupElement).
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var api = (window.kiroMotion = window.kiroMotion || {});
  var handlers = (api.handlers = api.handlers || {});
  var cleanups = new Map();
  var pending = new Map();
  var armed = new WeakSet();

  /** Un adaptador registra aquí un valor de data-motion. */
  api.register = function (name, handler) {
    handlers[name] = handler;
  };

  /** Una función que se ejecutará cuando `el` salga del DOM (HTMX lo reemplaza). */
  api.onCleanup = function (el, fn) {
    if (!cleanups.has(el)) cleanups.set(el, []);
    cleanups.get(el).push(fn);
  };

  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)");
  if ((reduced && reduced.matches) || !("IntersectionObserver" in window)) {
    // Sin puerta `js-motion`: la página queda exactamente como la envió el servidor.
    api.disabled = true;
    return;
  }

  root.classList.add("js-motion");

  function number(el, name, fallback) {
    var value = parseFloat(el.getAttribute(name));
    return isFinite(value) ? value : fallback;
  }

  function seconds(el, name, fallback) {
    return Math.min(Math.max(number(el, name, fallback), 0), 10);
  }

  // Se dispara cuando el borde superior del elemento pasa el 90 % de la
  // pantalla. Umbral 0 y no un porcentaje del elemento: un bloque más alto que
  // la pantalla nunca llegaría a mostrar el 15 % de su área.
  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        var callback = pending.get(entry.target);
        pending.delete(entry.target);
        if (callback) callback(entry.target);
      });
    },
    { rootMargin: "0px 0px -10% 0px" }
  );

  /** Ejecuta `callback(el)` una vez, cuando `el` entra en pantalla. */
  api.whenVisible = function (el, callback) {
    pending.set(el, callback);
    observer.observe(el);
  };

  /** Parte un texto sin etiquetas en palabras. Devuelve los <span> internos. */
  api.splitWords = function (el) {
    var text = el.textContent.replace(/\s+/g, " ").trim();
    if (!text) return [];
    var label = document.createElement("span");
    label.className = "m-sr";
    label.textContent = text;
    var visual = document.createElement("span");
    visual.setAttribute("aria-hidden", "true");
    var inner = [];
    text.split(" ").forEach(function (word, index, all) {
      var outer = document.createElement("span");
      outer.className = "m-word";
      var span = document.createElement("span");
      span.textContent = word;
      span.style.setProperty("--i", index);
      outer.appendChild(span);
      visual.appendChild(outer);
      if (index < all.length - 1) visual.appendChild(document.createTextNode(" "));
      inner.push(span);
    });
    el.textContent = "";
    el.appendChild(label);
    el.appendChild(visual);
    return inner;
  };

  function enter(el) {
    el.classList.add("is-in");
  }

  var builtin = {
    reveal: function (el) {
      var delay = seconds(el, "data-motion-delay", 0);
      if (delay) el.style.setProperty("--motion-delay", delay + "s");
      // Un adaptador de nivel 7+ puede ofrecer física de muelle.
      if (el.getAttribute("data-motion-ease") === "spring" && api.spring) {
        api.whenVisible(el, function () {
          api.spring(el, delay);
        });
        return;
      }
      api.whenVisible(el, enter);
    },

    stagger: function (el) {
      el.style.setProperty("--motion-step", seconds(el, "data-motion-delay", 0.08) + "s");
      Array.prototype.forEach.call(el.children, function (child, index) {
        // Tope a 12: en una lista larga el último no puede tardar segundos.
        child.style.setProperty("--i", Math.min(index, 12));
      });
      api.whenVisible(el, enter);
    },

    "split-reveal": function (el) {
      if (el.children.length) {
        el.classList.add("m-ready"); // tiene etiquetas dentro: se queda estático
        return;
      }
      var delay = seconds(el, "data-motion-delay", 0);
      if (delay) el.style.setProperty("--motion-delay", delay + "s");
      if (!api.splitWords(el).length) return;
      el.classList.add("m-split", "m-ready");
      api.whenVisible(el, enter);
    },

    count: function (el) {
      var target = number(el, "data-motion-to", NaN);
      if (!isFinite(target)) {
        el.classList.add("m-ready"); // sin data-motion-to: se queda como está
        return;
      }
      var finalText = el.textContent;
      var decimals = Math.max(0, Math.min(number(el, "data-motion-decimals", 0), 6));
      var format = new Intl.NumberFormat(root.lang || undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
      var duration = seconds(el, "data-motion-duration", 1.6) * 1000;
      el.textContent = format.format(0);
      el.classList.add("m-ready");
      api.whenVisible(el, function () {
        var start = null;
        function tick(now) {
          if (start === null) start = now;
          var progress = Math.min((now - start) / duration, 1);
          el.textContent = format.format(target * (1 - Math.pow(1 - progress, 3)));
          if (progress < 1) requestAnimationFrame(tick);
          else el.textContent = finalText; // el texto del servidor, tal cual
        }
        requestAnimationFrame(tick);
      });
    },

    marquee: function (el) {
      var items = Array.prototype.slice.call(el.children);
      if (!items.length) return;
      var track = document.createElement("div");
      track.className = "m-marquee-track";
      items.forEach(function (item) {
        track.appendChild(item);
      });
      // Una copia idéntica detrás, para que el bucle no tenga salto. Oculta a
      // lectores de pantalla y sin ids duplicados.
      items.forEach(function (item) {
        var copy = item.cloneNode(true);
        copy.setAttribute("aria-hidden", "true");
        copy.removeAttribute("id");
        Array.prototype.forEach.call(copy.querySelectorAll("[id]"), function (node) {
          node.removeAttribute("id");
        });
        track.appendChild(copy);
      });
      el.appendChild(track);
      el.style.setProperty("--motion-duration", Math.max(seconds(el, "data-motion-speed", 30), 1) + "s");
      el.classList.add("m-ready");
    },
  };

  function reveal(el) {
    // Un fallo en un elemento no puede dejarlo invisible.
    el.classList.add("is-in", "m-ready");
  }

  function arm(el) {
    if (armed.has(el)) return;
    armed.add(el);
    var handler = builtin[el.getAttribute("data-motion")] || handlers[el.getAttribute("data-motion")];
    if (!handler) return; // valor desconocido, o de un nivel que este proyecto no tiene: estático
    try {
      handler(el);
    } catch (error) {
      reveal(el);
      if (window.console) console.warn("[kiro-motion]", error);
    }
  }

  function scan(scope) {
    if (!scope || scope.nodeType !== 1 && scope.nodeType !== 9) return;
    if (scope.nodeType === 1 && scope.hasAttribute("data-motion")) arm(scope);
    Array.prototype.forEach.call(scope.querySelectorAll("[data-motion]"), arm);
  }

  function start() {
    scan(document);
    // El script de un nivel superior puede registrarse después de este: lo que
    // no tenía manejador se arma ahora.
    api.rescan = function () {
      scan(document);
    };
  }

  // HTMX reemplaza trozos de la página: el contenido nuevo se arma y el que se
  // va deja sus observadores y disparadores limpios.
  document.addEventListener("htmx:load", function (event) {
    scan((event.detail && event.detail.elt) || event.target);
  });
  document.addEventListener("htmx:beforeCleanupElement", function (event) {
    // htmx lo lanza con cualquier nodo: solo un Element se puede observar.
    var el = (event.detail && event.detail.elt) || event.target;
    if (!el || el.nodeType !== 1) return;
    observer.unobserve(el);
    pending.delete(el);
    var fns = cleanups.get(el);
    if (fns) {
      fns.forEach(function (fn) {
        try {
          fn();
        } catch (error) {
          /* limpiar nunca debe romper el intercambio */
        }
      });
      cleanups.delete(el);
    }
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
