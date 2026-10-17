/* Overview map on the places index — one dot per geocoded place, sized by how
   many diary entries mention it. Scope buttons jump between Naples, Campania and
   everything (the diary reaches from Matlock to the Persian Gulf). Same Esri
   Gray Canvas basemap as the single-place map (place-map.js). */
(function () {
  "use strict";

  var el = document.getElementById("places-map");
  var dataEl = document.getElementById("places-map-data");
  if (!el || !dataEl || !window.L) return;

  var places = JSON.parse(dataEl.textContent).places || [];
  if (!places.length) return;

  var override = document.documentElement.getAttribute("data-theme");
  var dark = override
    ? override === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;

  var style = getComputedStyle(document.body);
  var accent = style.getPropertyValue("--accent").trim() || "#9c3327";

  var SCOPES = {
    naples: [[40.80, 14.16], [40.90, 14.32]],
    campania: [[40.35, 13.85], [41.35, 15.10]],
  };

  var map = L.map(el, { scrollWheelZoom: false, zoomControl: true });

  var variant = dark ? "Dark" : "Light";
  var esri = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_";
  L.tileLayer(esri + variant + "_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 16,
    attribution: 'Tiles &copy; <a href="https://www.esri.com/">Esri</a>',
  }).addTo(map);
  L.tileLayer(esri + variant + "_Gray_Reference/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 16,
  }).addTo(map);

  // largest first, so small dots stay clickable on top of big ones
  var all = [];
  places.forEach(function (p) {
    all.push([p.lat, p.lon]);
    var m = L.circleMarker([p.lat, p.lon], {
      radius: 3 + 2.2 * Math.sqrt(p.n || 0),
      color: accent,
      weight: 1,
      fillColor: accent,
      fillOpacity: 0.45,
    }).addTo(map);
    m.bindTooltip(
      p.name + " · " + p.n + " entr" + (p.n === 1 ? "y" : "ies"),
      { direction: "top" }
    );
    m.on("click", function () { window.location.href = p.url; });
  });
  SCOPES.all = L.latLngBounds(all).pad(0.05);

  var bar = document.querySelector(".map-scope");
  function show(scope) {
    map.fitBounds(SCOPES[scope]);
    if (!bar) return;
    bar.querySelectorAll("button").forEach(function (b) {
      b.classList.toggle("is-active", b.dataset.scope === scope);
    });
  }
  if (bar) {
    bar.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () { show(b.dataset.scope); });
    });
    bar.hidden = false;
  }
  show("campania");
})();
