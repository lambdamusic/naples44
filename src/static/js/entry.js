/* Entry pages: ← / → arrow keys walk to the previous / next diary entry. */
(function () {
  "use strict";

  var nav = document.querySelector(".entry-nav");
  if (!nav) return;
  var prev = nav.querySelector("a.prev");
  var next = nav.querySelector("a.next");

  document.addEventListener("keydown", function (e) {
    if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
    var t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;

    if (e.key === "ArrowLeft" && prev) {
      e.preventDefault();
      window.location.href = prev.href;
    } else if (e.key === "ArrowRight" && next) {
      e.preventDefault();
      window.location.href = next.href;
    }
  });
})();
