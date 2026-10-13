/*! Kiro motion: adaptador de Motion (nivel 7-8). Carga después de motion.js y de
 * vendor/motion.min.js (Motion One). Añade valores de data-motion sin que la
 * página escriba JavaScript:
 *
 *   parallax   el elemento se desplaza mientras cruza la pantalla
 *              data-motion-distance="40"   píxeles hacia cada lado
 *   progress   una barra (scaleX) que se llena con el scroll de la página
 *   y, sobre un reveal:   data-motion="reveal" data-motion-ease="spring"
 *              entra con física de muelle en vez de una curva
 */
(function () {
  "use strict";

  var M = window.Motion;
  var k = window.kiroMotion;
  if (!M || !k || k.disabled) return;

  function number(el, name, fallback) {
    var value = parseFloat(el.getAttribute(name));
    return isFinite(value) ? value : fallback;
  }

  k.register("parallax", function (el) {
    var distance = number(el, "data-motion-distance", 40);
    var stop = M.scroll(
      M.animate(el, {
        transform: ["translateY(" + -distance + "px)", "translateY(" + distance + "px)"],
      }),
      { target: el, offset: ["start end", "end start"] }
    );
    k.onCleanup(el, stop);
  });

  k.register("progress", function (el) {
    el.style.transformOrigin = "0 50%";
    var stop = M.scroll(M.animate(el, { transform: ["scaleX(0)", "scaleX(1)"] }));
    k.onCleanup(el, stop);
  });

  k.spring = function (el, delay) {
    // La clase deja el estado final en CSS; la animación parte del oculto.
    el.style.transition = "none";
    el.classList.add("is-in");
    var controls = M.animate(
      el,
      { opacity: [0, 1], transform: ["translateY(28px)", "translateY(0px)"] },
      { delay: delay, easing: M.spring({ stiffness: 140, damping: 16 }) }
    );
    controls.finished
      .then(function () {
        el.style.removeProperty("opacity");
        el.style.removeProperty("transform");
        el.style.removeProperty("transition");
      })
      .catch(function () {});
  };

  // El contenido nuevo (HTMX) tiene que armarse con los valores recién registrados.
  if (k.rescan) k.rescan();
})();
