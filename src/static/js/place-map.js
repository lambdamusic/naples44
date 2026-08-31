/* Small Leaflet map on place pages — centred on the place, with faint markers
   for the other places mentioned in the same diary entries. CARTO basemap,
   no API key; matches the light/dark theme. */
(function () {
  "use strict";

  var el = document.getElementById("place-map");
  var dataEl = document.getElementById("place-map-data");
  if (!el || !dataEl || !window.L) return;

  var data = JSON.parse(dataEl.textContent);
  var f = data.focus;

  var override = document.documentElement.getAttribute("data-theme");
  var dark = override
    ? override === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;

  var style = getComputedStyle(document.body);
  var accent = style.getPropertyValue("--accent").trim() || "#9c3327";
  var faint = style.getPropertyValue("--ink-faint").trim() || "#8a8073";

  var map = L.map(el, {
    scrollWheelZoom: false,
    zoomControl: true,
  }).setView([f.lat, f.lon], data.zoom || 13);

  // Esri "Gray Canvas" — muted, free with attribution, no API key, light + dark.
  var base = dark ? "World_Dark_Gray_Base" : "World_Light_Gray_Base";
  L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/" +
      base + "/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 16,
      attribution: 'Tiles &copy; <a href="https://www.esri.com/">Esri</a>',
    }
  ).addTo(map);

  (data.others || []).forEach(function (o) {
    var m = L.circleMarker([o.lat, o.lon], {
      radius: 4,
      color: faint,
      weight: 1,
      fillColor: faint,
      fillOpacity: 0.55,
    }).addTo(map);
    m.bindTooltip(o.name);
    m.on("click", function () {
      window.location.href = o.url;
    });
  });

  L.circleMarker([f.lat, f.lon], {
    radius: 8,
    color: accent,
    weight: 2,
    fillColor: accent,
    fillOpacity: 0.85,
  })
    .addTo(map)
    .bindTooltip(f.name, { direction: "top" });
})();
