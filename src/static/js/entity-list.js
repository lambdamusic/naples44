/* Browse pages: re-sort the entity list by type / name / mention count.
   Progressive enhancement — without JS the server-rendered grouped list stands. */
(function () {
  "use strict";

  var list = document.querySelector(".ei-list");
  var sortBar = document.querySelector(".entity-sort");
  if (!list || !sortBar) return;

  var original = Array.prototype.slice.call(list.children);
  var items = original.filter(function (n) { return n.classList.contains("ei-item"); });

  function byName(a, b) { return a.dataset.name.localeCompare(b.dataset.name); }
  function byCount(a, b) {
    return (+b.dataset.count) - (+a.dataset.count) || byName(a, b);
  }

  function apply(mode) {
    while (list.firstChild) list.removeChild(list.firstChild);
    if (mode === "type") {
      list.classList.remove("flat");
      original.forEach(function (n) { list.appendChild(n); });
    } else {
      list.classList.add("flat");
      items.slice().sort(mode === "count" ? byCount : byName)
        .forEach(function (n) { list.appendChild(n); });
    }
    sortBar.querySelectorAll("button").forEach(function (b) {
      b.classList.toggle("is-active", b.dataset.sort === mode);
    });
  }

  sortBar.querySelectorAll("button").forEach(function (b) {
    b.addEventListener("click", function () { apply(b.dataset.sort); });
  });
  sortBar.hidden = false;
})();
