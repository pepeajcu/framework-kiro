/*! Kiro motion: adaptador de GSAP y ScrollTrigger (nivel 9-10). Carga después de
 * motion.js, vendor/gsap.min.js y vendor/ScrollTrigger.min.js. Añade valores de
 * data-motion sin que la página escriba JavaScript:
 *
 *   parallax    el elemento se desplaza mientras cruza la pantalla
 *               data-motion-distance="40"    píxeles hacia cada lado
 *   progress    una barra (scaleX) que se llena con el scroll de la página
 *   pin         la sección se queda fija mientras se hace scroll
 *               data-motion-length="100"     % de la altura de la pantalla
 *   scrub       el texto se ilumina palabra a palabra con el scroll
 *   horizontal  una banda ancha se desplaza en horizontal mientras la sección
 *               está fija: <section data-motion="horizontal"><div class="flex w-max">…
 *   y, sobre un reveal:   data-motion="reveal" data-motion-ease="spring"
 *
 * `pin` y `horizontal` solo actúan desde 768 px: en móvil el contenido fluye
 * (la banda se recorre con su propio scroll horizontal). Todos limpian sus
 * disparadores cuando HTMX reemplaza el fragmento que los contiene.
 */
(function () {
  "use strict";

  var g = window.gsap;
  var ST = window.ScrollTrigger;
  var k = window.kiroMotion;
  if (!g || !ST || !k || k.disabled) return;

  g.registerPlugin(ST);
  var DESKTOP = "(min-width: 768px)";

  function number(el, name, fallback) {
    var value = parseFloat(el.getAttribute(name));
    return isFinite(value) ? value : fallback;
  }

  function killTween(tween) {
    if (tween.scrollTrigger) tween.scrollTrigger.kill();
    tween.kill();
  }

  k.register("parallax", function (el) {
    var distance = number(el, "data-motion-distance", 40);
    var tween = g.fromTo(
      el,
      { y: -distance },
      {
        y: distance,
        ease: "none",
        scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: true },
      }
    );
    k.onCleanup(el, function () {
      killTween(tween);
    });
  });

  k.register("progress", function (el) {
    var tween = g.fromTo(
      el,
      { scaleX: 0 },
      {
        scaleX: 1,
        ease: "none",
        transformOrigin: "0 50%",
        scrollTrigger: { start: 0, end: "max", scrub: true },
      }
    );
    k.onCleanup(el, function () {
      killTween(tween);
    });
  });

  k.register("pin", function (el) {
    var media = g.matchMedia();
    media.add(DESKTOP, function () {
      var length = number(el, "data-motion-length", 100);
      var trigger = ST.create({
        trigger: el,
        start: "top top",
        end: function () {
          return "+=" + (window.innerHeight * length) / 100;
        },
        pin: true,
        anticipatePin: 1,
      });
      return function () {
        trigger.kill();
      };
    });
    k.onCleanup(el, function () {
      media.revert();
    });
  });

  k.register("scrub", function (el) {
    if (el.children.length) return; // con etiquetas dentro se queda estático
    var words = k.splitWords(el);
    if (!words.length) return;
    g.set(words, { opacity: 0.15 });
    var tween = g.to(words, {
      opacity: 1,
      stagger: 0.1,
      ease: "none",
      scrollTrigger: { trigger: el, start: "top 80%", end: "bottom 45%", scrub: true },
    });
    k.onCleanup(el, function () {
      killTween(tween);
    });
  });

  k.register("horizontal", function (el) {
    var track = el.firstElementChild;
    if (!track) return;
    var media = g.matchMedia();
    media.add(DESKTOP, function () {
      function distance() {
        return Math.max(track.scrollWidth - el.clientWidth, 0);
      }
      el.style.overflowX = "hidden";
      var tween = g.to(track, {
        x: function () {
          return -distance();
        },
        ease: "none",
        scrollTrigger: {
          trigger: el,
          start: "top top",
          end: function () {
            return "+=" + distance();
          },
          pin: true,
          scrub: 1,
          anticipatePin: 1,
          invalidateOnRefresh: true,
        },
      });
      return function () {
        el.style.overflowX = "";
        killTween(tween);
        g.set(track, { clearProps: "transform" });
      };
    });
    k.onCleanup(el, function () {
      media.revert();
    });
  });

  k.spring = function (el, delay) {
    el.style.transition = "none";
    el.classList.add("is-in");
    g.fromTo(
      el,
      { opacity: 0, y: 28 },
      { opacity: 1, y: 0, duration: 1.1, delay: delay, ease: "back.out(1.7)", clearProps: "all" }
    );
  };

  // Las posiciones dependen del layout: al terminar de cargar (fuentes e
  // imágenes) y tras cada intercambio de HTMX hay que recalcularlas.
  var refreshing = 0;
  function refresh() {
    clearTimeout(refreshing);
    refreshing = setTimeout(ST.refresh, 100);
  }
  window.addEventListener("load", refresh);
  document.addEventListener("htmx:afterSettle", refresh);

  if (k.rescan) k.rescan();
})();
