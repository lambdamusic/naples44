/* Naples '44 — radial timeline.
   Inner ring: the 108 diary entries. Outer ring: broader WWII events.
   Shared date axis running clockwise from the top, with a small gap at 12 o'clock. */
(function () {
  "use strict";

  var data = JSON.parse(document.getElementById("naples-data").textContent);
  var entries = data.entries;
  var events = data.events;
  var themes = data.themes;

  entries.forEach(function (e) { e._date = new Date(e.date + "T00:00:00"); });
  events.forEach(function (e) { e._date = new Date(e.date + "T00:00:00"); });

  var fmtFull = d3.timeFormat("%B %-d, %Y");
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // The axis follows the book's own span (Sept 1943 – Oct 1944), with a short
  // pad, so the entries spread around the whole circle. War events outside that
  // window are listed separately rather than squashed onto the ring.
  var entryMin = new Date(data.meta.entry_date_min + "T00:00:00");
  var entryMax = new Date(data.meta.entry_date_max + "T00:00:00");
  var dmin = d3.timeDay.offset(entryMin, -21);
  var dmax = d3.timeDay.offset(entryMax, 21);

  // ---- geometry -----------------------------------------------------------
  var SIZE = 1000, cx = SIZE / 2, cy = SIZE / 2;
  var R_ENTRY = 300, R_MONTH = 360, R_EVENT = 400;
  var TAU = 2 * Math.PI;
  var gap = (14 * Math.PI) / 180;
  var a0 = -Math.PI / 2 + gap / 2;
  var a1 = -Math.PI / 2 + TAU - gap / 2;

  var angle = d3.scaleTime().domain([dmin, dmax]).range([a0, a1]);
  function inRange(date) { return date >= dmin && date <= dmax; }
  function pt(date, r) {
    var a = angle(date < dmin ? dmin : date > dmax ? dmax : date);
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  }

  var color = d3.scaleOrdinal()
    .domain(themes.map(function (t) { return t.slug; }))
    .range(d3.schemeTableau10.concat(["#6b4c9a", "#b5651d"]));

  // ---- svg scaffold ------------------------------------------------------
  var svg = d3.select("#viz").append("svg")
    .attr("viewBox", "0 0 " + SIZE + " " + SIZE)
    .attr("preserveAspectRatio", "xMidYMid meet");

  var gGuides = svg.append("g");
  var gMonths = svg.append("g");
  var gYears = svg.append("g");
  var gEvents = svg.append("g");
  var gEntries = svg.append("g");

  // ring guides
  [R_ENTRY, R_EVENT].forEach(function (r) {
    gGuides.append("circle").attr("class", "ring-guide")
      .attr("cx", cx).attr("cy", cy).attr("r", r);
  });

  // month ticks + labels
  var months = [];
  var m = d3.timeMonth.floor(dmin);
  while (m <= dmax) { months.push(m); m = d3.timeMonth.offset(m, 1); }
  var fmtMonth = d3.timeFormat("%b");

  months.forEach(function (mo) {
    var p1 = pt(mo, R_ENTRY - 8), p2 = pt(mo, R_MONTH);
    gMonths.append("line").attr("class", "month-tick")
      .attr("x1", p1[0]).attr("y1", p1[1]).attr("x2", p2[0]).attr("y2", p2[1]);
    var mid = d3.timeDay.offset(mo, 15);
    var lp = pt(mid, R_MONTH + 12);
    var a = (angle(mid) * 180) / Math.PI;
    var flip = a > 90 && a < 270;
    gMonths.append("text").attr("class", "month-label")
      .attr("transform", "translate(" + lp[0] + "," + lp[1] + ") rotate(" + (flip ? a + 180 : a) + ")")
      .attr("text-anchor", flip ? "end" : "start")
      .attr("dominant-baseline", "middle")
      .text(fmtMonth(mo));
  });

  // year labels at the mid-angle of each year's covered span
  d3.groups(months, function (d) { return d.getFullYear(); }).forEach(function (grp) {
    var ms = grp[1];
    var midDate = new Date((ms[0].getTime() + d3.timeMonth.offset(ms[ms.length - 1], 1).getTime()) / 2);
    var lp = pt(midDate, R_ENTRY - 46);
    gYears.append("text").attr("class", "year-label")
      .attr("x", lp[0]).attr("y", lp[1])
      .attr("text-anchor", "middle").attr("dominant-baseline", "middle")
      .text(grp[0]);
  });

  // ---- outer ring: war events ------------------------------------------
  var tip = d3.select("body").append("div").attr("class", "tooltip").style("display", "none");
  function showTip(html, ev) {
    tip.style("display", "block").html(html);
    var x = ev.clientX + 14, y = ev.clientY + 14;
    var bb = tip.node().getBoundingClientRect();
    if (x + bb.width > window.innerWidth) x = ev.clientX - bb.width - 14;
    if (y + bb.height > window.innerHeight) y = ev.clientY - bb.height - 14;
    tip.style("left", x + "px").style("top", y + "px");
  }
  function hideTip() { tip.style("display", "none"); }

  var eventsInRange = events.filter(function (d) { return inRange(d._date); });
  var eventsBefore = events.filter(function (d) { return d._date < dmin; });
  var eventsAfter = events.filter(function (d) { return d._date > dmax; });

  eventsInRange.sort(function (a, b) { return a._date - b._date; });

  // Keep every event dot at least MIN_GAP apart around the ring so labels don't
  // collide. Start from each event's true date-angle, then nudge clustered ones
  // apart with a forward + backward relaxation pass (a few iterations centres
  // each cluster near its true position rather than shoving it all one way).
  var MIN_GAP = (5.5 * Math.PI) / 180;
  var ang = eventsInRange.map(function (d) { return angle(d._date); });
  for (var pass = 0; pass < 4; pass++) {
    for (var i = 1; i < ang.length; i++) {
      if (ang[i] - ang[i - 1] < MIN_GAP) ang[i] = ang[i - 1] + MIN_GAP;
    }
    for (var j = ang.length - 2; j >= 0; j--) {
      if (ang[j + 1] - ang[j] < MIN_GAP) ang[j] = ang[j + 1] - MIN_GAP;
    }
  }

  function ptA(a, r) { return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; }

  eventsInRange.forEach(function (d, i) {
    var a = ang[i];
    var trueA = angle(d._date);
    var nudged = Math.abs(a - trueA) > 0.015;
    var g = gEvents.append("g").attr("class", "event");
    var deg = (a * 180) / Math.PI;
    var flip = deg > 90 && deg < 270;
    var lead = i % 2 ? 26 : 12;   // 2-level radial stagger for the label text

    // faint tick at the event's real date; slanted connector if the dot was nudged
    if (nudged) {
      g.append("line").attr("class", "event-truetick")
        .attr("x1", ptA(trueA, R_EVENT - 4)[0]).attr("y1", ptA(trueA, R_EVENT - 4)[1])
        .attr("x2", ptA(a, R_EVENT)[0]).attr("y2", ptA(a, R_EVENT)[1]);
    }
    g.append("line").attr("class", "event-leader")
      .attr("x1", ptA(a, R_EVENT)[0]).attr("y1", ptA(a, R_EVENT)[1])
      .attr("x2", ptA(a, R_EVENT + lead - 3)[0]).attr("y2", ptA(a, R_EVENT + lead - 3)[1]);
    g.append("circle").attr("class", "event-dot")
      .attr("cx", ptA(a, R_EVENT)[0]).attr("cy", ptA(a, R_EVENT)[1]).attr("r", 3.5);
    var lp = ptA(a, R_EVENT + lead);
    g.append("text").attr("class", "event-label")
      .attr("transform", "translate(" + lp[0] + "," + lp[1] + ") rotate(" + (flip ? deg + 180 : deg) + ")")
      .attr("text-anchor", flip ? "end" : "start")
      .attr("dominant-baseline", "middle")
      .text(d.title.length > 30 ? d.title.slice(0, 29) + "…" : d.title);
    g.on("mousemove", function (ev) {
      showTip("<strong>" + esc(d.title) + "</strong>" + fmtFull(d._date) + " — " + esc(d.note), ev);
    }).on("mouseleave", hideTip);
  });

  // war events outside the book's window — shown as short lists, not on the ring
  function renderOOR(id, label, list) {
    if (!list.length) return;
    var box = document.getElementById(id);
    box.hidden = false;
    box.innerHTML = "<h3>" + label + "</h3><ul>" + list.map(function (d) {
      var inner = esc(fmtFull(d._date)) + " — " + esc(d.title);
      return "<li>" + (d.link
        ? '<a href="' + esc(d.link) + '" target="_blank" rel="noopener">' + inner + "</a>"
        : inner) + "</li>";
    }).join("") + "</ul>";
  }
  renderOOR("oor-before", "Before the diary begins", eventsBefore);
  renderOOR("oor-after", "After the diary ends", eventsAfter);

  // ---- inner ring: diary entries --------------------------------------
  var selected = null;

  function onEnter(ev, d) {
    showTip("<strong>" + esc(d.date_label) + " " + d.year + "</strong>" +
      esc(d.summary.length > 130 ? d.summary.slice(0, 129) + "…" : d.summary), ev);
  }

  var entryG = gEntries.selectAll("g.entry").data(entries).join("g").attr("class", "entry");
  var hit = entryG.append("circle")   // generous transparent hit target
    .attr("class", "entry-hit")
    .attr("cx", function (d) { return pt(d._date, R_ENTRY)[0]; })
    .attr("cy", function (d) { return pt(d._date, R_ENTRY)[1]; })
    .attr("r", 9)
    .on("mousemove", onEnter)
    .on("mouseleave", hideTip)
    .on("click", function (ev, d) { select(d); });
  var dot = entryG.append("circle")
    .attr("class", "entry-dot")
    .attr("id", function (d) { return "entry-" + d.id; })
    .attr("cx", function (d) { return pt(d._date, R_ENTRY)[0]; })
    .attr("cy", function (d) { return pt(d._date, R_ENTRY)[1]; })
    .attr("r", 4);

  // ---- selection / detail panel --------------------------------------
  var detailEl = document.getElementById("detail");

  function select(d) {
    selected = d.id;
    dot.classed("selected", function (x) { return x.id === d.id; });
    detailEl.classList.remove("is-empty");
    detailEl.innerHTML = renderDetail(d);
    if (history.replaceState) history.replaceState(null, "", "#entry-" + d.id);
  }

  function renderDetail(d) {
    var h = "";
    h += '<p class="d-date">' + esc(d.date_label) + " " + d.year + "</p>";
    h += '<p class="d-meta">Entry ' + d.id + " · Book chapter " + d.chapter + "</p>";
    h += '<p class="d-summary">' + esc(d.summary) + "</p>";
    h += '<a class="d-open d-open-top" href="' + d.url + '">Read the full entry →</a>';
    if (d.themes.length) {
      h += '<p class="d-section">Themes</p><p>' +
        d.themes.map(themeLink).join(", ") + "</p>";
    }
    if (d.places.length) {
      h += '<p class="d-section">Places</p><p>' +
        d.places.map(function (p) { return link(p) + ' <span class="tag-type">' + esc(p.type_label) + "</span>"; }).join("<br>") + "</p>";
    }
    if (d.people.length) {
      h += '<p class="d-section">People</p><p>' +
        d.people.map(function (p) {
          return link(p) + ' <span class="tag-type">' + esc(p.type_label) + "</span>" +
            (p.note ? '<br><span class="tag-note">' + esc(p.note) + "</span>" : "");
        }).join("<br>") + "</p>";
    }
    if (d.folklore.length) {
      h += '<p class="d-section">Saints &amp; folklore</p><p>' +
        d.folklore.map(function (p) {
          return link(p) + (p.note ? '<br><span class="tag-note">' + esc(p.note) + "</span>" : "");
        }).join("<br>") + "</p>";
    }
    if (d.reflections.length) {
      h += '<p class="d-section">Reflections</p>' +
        d.reflections.map(function (r) {
          return "<p><strong>" + esc(r.title) + "</strong><br>" + esc(r.note) + "</p>";
        }).join("");
    }
    h += '<a class="d-open" href="' + d.url + '">Open the full entry page →</a>';
    return h;
  }

  function link(o) {
    return o.url ? '<a href="' + esc(o.url) + '" rel="noopener">' + esc(o.name) + "</a>" : esc(o.name);
  }

  // ---- theme filter ---------------------------------------------------
  var activeThemes = new Set();
  var activeTags = new Set();

  var themeCounts = {};
  themes.forEach(function (t) { themeCounts[t.slug] = 0; });
  entries.forEach(function (e) { e.themes.forEach(function (s) { themeCounts[s]++; }); });

  var themeList = d3.select("#theme-list");
  themeList.selectAll("li").data(themes).join("li")
    .attr("data-slug", function (t) { return t.slug; })
    .html(function (t) {
      return '<span class="swatch" style="background:' + color(t.slug) + '"></span>' +
        esc(t.label) + '<span class="count">' + themeCounts[t.slug] + "</span>";
    })
    .on("click", function (ev, t) {
      toggle(activeThemes, t.slug);
      d3.select(this).classed("active", activeThemes.has(t.slug));
      applyFilter();
    });

  // ---- tag filter ---------------------------------------------------
  var tagIndex = {};   // key -> {name, kind, count, entryIds:Set}
  function addTag(name, kind, id) {
    var key = kind + "::" + name;
    if (!tagIndex[key]) tagIndex[key] = { name: name, kind: kind, count: 0, ids: new Set() };
    if (!tagIndex[key].ids.has(id)) { tagIndex[key].ids.add(id); tagIndex[key].count++; }
  }
  entries.forEach(function (e) {
    e.places.forEach(function (p) { addTag(p.name, "place", e.id); });
    e.people.forEach(function (p) { addTag(p.name, "person", e.id); });
    e.folklore.forEach(function (p) { addTag(p.name, "folklore", e.id); });
  });
  var allTags = Object.keys(tagIndex).map(function (k) {
    return Object.assign({ key: k }, tagIndex[k]);
  }).sort(function (a, b) { return b.count - a.count || a.name.localeCompare(b.name); });

  var tagListEl = d3.select("#tag-list");
  function renderTagList(q) {
    q = (q || "").trim().toLowerCase();
    var rows = allTags.filter(function (t) {
      return !q || t.name.toLowerCase().indexOf(q) !== -1;
    }).slice(0, 60);
    tagListEl.selectAll("li").data(rows, function (d) { return d.key; }).join("li")
      .attr("data-key", function (d) { return d.key; })
      .classed("active", function (d) { return activeTags.has(d.key); })
      .html(function (d) {
        return esc(d.name) + '<span class="count">' + d.count + '</span>' +
          '<span class="tag-kind">' + d.kind + "</span>";
      })
      .on("click", function (ev, d) {
        toggle(activeTags, d.key);
        d3.select(this).classed("active", activeTags.has(d.key));
        applyFilter();
      });
  }
  document.getElementById("tag-search").addEventListener("input", function (e) {
    renderTagList(e.target.value);
  });
  renderTagList("");

  // ---- filtering ---------------------------------------------------
  var clearBtn = document.getElementById("clear-filters");
  clearBtn.addEventListener("click", function () {
    activeThemes.clear(); activeTags.clear();
    themeList.selectAll("li").classed("active", false);
    tagListEl.selectAll("li").classed("active", false);
    applyFilter();
  });

  function matches(d) {
    if (!activeThemes.size && !activeTags.size) return true;
    for (var s of activeThemes) if (d.themes.indexOf(s) !== -1) return true;
    for (var k of activeTags) if (tagIndex[k] && tagIndex[k].ids.has(d.id)) return true;
    return false;
  }

  function applyFilter() {
    var filtering = activeThemes.size + activeTags.size > 0;
    clearBtn.hidden = !filtering;
    dot.classed("dim", function (d) { return filtering && !matches(d); })
      .classed("hit", function (d) { return filtering && matches(d); })
      .attr("r", function (d) { return filtering && matches(d) ? 5.5 : 4; });
    // while filtering, only matching entries stay clickable / hoverable
    hit.style("pointer-events", function (d) {
      return filtering && !matches(d) ? "none" : null;
    });
  }

  // ---- helpers ---------------------------------------------------
  function toggle(set, v) { set.has(v) ? set.delete(v) : set.add(v); }
  function themeLink(slug) {
    var t = themes.find(function (x) { return x.slug === slug; });
    if (!t) return esc(slug);
    return '<a href="' + esc(t.url) + '">' + esc(t.label) + "</a>";
  }
  // ---- deep link ------------------------------------------------
  var hm = /^#entry-(\d+)$/.exec(location.hash || "");
  if (hm) {
    var target = entries.find(function (e) { return e.id === +hm[1]; });
    if (target) select(target);
  }
})();
