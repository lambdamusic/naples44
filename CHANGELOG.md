# Changelog

## 2026-08-30 — Scaffold

- Initial project scaffold via the `init-django-static-site` skill.
- Python 3.13, Django 5.2 LTS, sqlite.
- Single app `src/apps/naples44/` with a placeholder index view + `base.html`.
- `tools/` workflow scripts, `docs/CNAME` → `naples44.michelepasin.org`.
- No `django-mptt`.

## 2026-08-30 — Phase 1: data layer

- Purpose confirmed: a radial-timeline visualisation of Norman Lewis's *Naples '44*.
- Content model (`src/apps/naples44/models.py`): `Entry` (108, pk = source id),
  `Theme` (11), `Place` (129), `Person` (39), `FolkloreEntity` (31),
  `EntryPerson` / `EntryFolklore` through-models with per-occurrence notes,
  `Reflection` (35), `OuterRingEvent` (20).
- Admin registered for all models with inlines and entity counts.
- Seed importer `manage.py import_naples_data` — idempotent, reads `plan-files/*.json`.
- `plan-files/` gitignored; `backups/django/dump.json` (479 objects) is now the
  committed source of the data. loaddata roundtrip verified.
- Django admin is the editor from here on.

## 2026-08-30 — Phase 2 PoC: the site

- Three views/URLs: `/` (landing), `/timeline/` (the visualisation), `/entries/<id>/`.
- `payload.py` builds one JSON blob embedded in the timeline page via `json_script`
  (no fetch — the wget mirror will work offline).
- Radial timeline in `src/static/js/timeline.js` with **D3 v7 vendored**
  (`src/static/js/d3.v7.min.js`): inner ring = 108 entries by date, outer ring =
  war events; axis scoped to the book's own span (Sept 1943 – Oct 1944, padded),
  out-of-range war events listed separately. Click an entry → detail panel; theme
  and tag filters dim/highlight the ring; `#entry-<id>` deep links.
- `Entry.get_absolute_url()` added.
- Archival visual design in `main.css` (warm paper / ink / brick-red, serif
  display), light + dark aware.
- Known rough edges: war-event labels collide near 12 o'clock when events fall a
  day or two apart (no collision detection yet); no per-entity pages for
  place/person/folklore/theme yet (planned).

## 2026-08-31 — Entity pages, filter fix, book links

- **Filter fix**: while a theme/tag filter is active, non-matching entry dots get
  `pointer-events: none` — only matching entries are clickable/hoverable
  (`timeline.js`).
- **Entity pages**: `/places/<slug>/`, `/people/<slug>/`, `/folklore/<slug>/`,
  `/themes/<slug>/`. Each shows the entity, an optional `description` (new
  `TextField`, admin-editable), and a vertical chronological timeline of its
  entries (with the per-occurrence note for people/folklore). Wikipedia is a
  "further reading" link at the foot of the entity page only.
- `slug` (unique) added to Place/Person/FolkloreEntity — migration `0002`
  populates them from names; `save()` auto-slugs new rows; admin has
  `prepopulated_fields`.
- **All internal links now point at entity pages first**, never external — entry
  pages, the timeline detail panel, and the vertical timelines. Payload emits
  `get_absolute_url()` for every tag.
- Arrow-key nav on entry pages (`←`/`→`, `entry.js`).
- Homepage: book cover (`src/static/img/naples-44-cover.jpg`, from Eland/
  travelbooks) linking to the publisher's shop. Footer: link to the book's
  Wikipedia page.
- `tools/db-dump` now dumps only the `naples44` app (keeps users out of the
  committed fixture). `backups/django/dump.json` re-generated with slugs.

## 2026-08-31 — Maps on place pages

- `Place` gains `latitude` / `longitude` / `geocode_source` (migration `0003`).
- `manage.py geocode_places` — Wikipedia coordinates for places with a
  `wikipedia_url`, Nominatim (1 req/s, Campania-biased) for the rest.
  `--dry-run` / `--refresh`; `geocode_source='manual'` rows are never overwritten.
- Result: 116/129 placed (55 Wikipedia, ~46 Nominatim, ~15 hand-fixed). The
  remaining 13 are un-mappable or ambiguous (e.g. "Zona di Camorra", two
  different "San Giorgio"s) — add via admin if wanted.
- Place pages render a small **Leaflet** map (vendored `leaflet.js` / `.css` +
  marker images) centred on the place, with faint clickable markers for the
  other places mentioned in the same entries. Basemap: **Esri Gray Canvas**
  (no API key, light + dark to match the theme). No map shown when a place has
  no coordinates.
- `tools/*` scripts assume the venv is active (`workon naples44_2026`) — running
  `tools/db-dump` without it silently uses the wrong Python.

## 2026-09-01 — Map labels + place descriptions

- Place maps now use the Esri Gray **base + reference** layers, so nearby place
  names, roads and boundaries are readable.
- `Place.book_role` field (migration `0004`) — a hand-written note on how the
  place figures in the book, shown as an "In the book" block on the page.
  Seeded for 33 places from the entry summaries; the rest are Michele's to write.
- `Place.description` seeded from Wikipedia article intros (2–3 sentences) via
  `manage.py seed_place_descriptions` (`--refresh` / `--only`). 74 of 78 places
  with a `wikipedia_url` filled; 4 have stale URLs (404) to fix by hand.
- Fixed ~10 more Nominatim mis-hits found while reviewing (Naples streets that
  matched same-named streets elsewhere in Campania — Santa Lucia was landing
  near Sorrento). 114/129 placed; "Via Gravina" / "Via San Felice" cleared as
  unidentifiable.

## 2026-09-01 — Entity page polish

- Each entity/entry page now shows a line-art **type icon** (book / map-pin /
  person / evil-eye / tag), colour-coded per type — `_entity_icon.html`.
- **Markdown** in `description` and `book_role` (all entity types) via a
  `markdownify` filter (`templatetags/naples44_extras.py`, `Markdown` package).
  Content is admin-only so the HTML is not sanitised.
- Every entity page links to a Google search: `"<name>" naples 44`.
- **← / → arrow keys** and a prev/next nav now move between sibling entity pages
  (places → places, people → people, …) in the model's default order, reusing
  `entry.js` and the `.entry-nav` markup.

## 2026-09-01 — Place book_role: second pass from the full text

- Read the epub (`plan-files/…Naples '44….epub`) and wrote `book_role` for 90
  more places, grounded in the actual passages where each is mentioned
  (paraphrased, project house style; ≤1 short quoted phrase each). **123/129**
  places now have a book_role.
- Still empty (all look like thin or mis-applied tags — leave or reconsider):
  Altamura (actually *Marshal* Altamura, a person), Castel Sant'Elmo,
  Castellammare di Stabia, Palazzo Carracciolo, Rione Sant'Antonio Abate,
  San Giorgio (near Benevento).
- Fixed one geocode from the text: "Corso Umberto" is Benevento's, not Naples's.

## 2026-09-01 — Analytics

- `naples44/ga.html` (Google Analytics gtag, G-T4B4FDV3TR) is now included in
  `<head>` of `base.html`, so it loads on every page.

## 2026-09-01 — Descriptions for people & folklore

- `book_role` added to `Person` and `FolkloreEntity` (migration `0005`); both
  models now carry the same `description` + `book_role` pair as `Place`, rendered
  the same way on the entity page.
- `seed_place_descriptions` → **`seed_wikipedia_descriptions`**, generalised to
  Place / Person / FolkloreEntity (`--model` flag). Ran it: 14 folklore + 1
  person (Vito Genovese) descriptions from Wikipedia.
- Wrote `description` + `book_role` for **all 39 people and all 31 folklore
  entities** from the epub — identity line + a grounded "In the book" note,
  paraphrased house style.
- Noted duplicates to reconcile: `bernard-durham` / `durham` are the same man;
  `sergeant-major-john-dashwood` / `sergeant-major-dashwood` likewise.
- Admin: `has_role` indicator column on Person and FolkloreEntity.

## 2026-09-01 — Timeline: entry-page link + outer-ring spacing

- Detail panel: a prominent "Read the full entry →" button now sits right after
  the summary, before Themes; the subtler "Open the full entry page →" link stays
  at the bottom too.
- Outer-ring events: dots are nudged apart with a minimum ~5.5° angular gap
  (forward + backward relaxation pass) so clustered events (e.g. the four
  mid-August 1944 liberations, the Sept 1943 armistice/Salerno pair) no longer
  overlap. A faint tick + connector marks a nudged event's true date on the ring.

## 2026-09-01 — Entry page: two-column layout, reflections made prominent

- `entry_detail.html` restructured into `.entry-layout` (main + sidebar) — main
  column: summary, Themes, Reflections; sidebar: Places, People, Saints & folklore.
  Nav/key-hint stay full-width below. Stacks to one column under 46rem.
- Reflections get real visual weight: each is a pull-quote card (accent left
  border, decorative quote mark, serif title, italic body) instead of a plain
  tag-block entry.

## 2026-09-01 — Browse / index pages

- New listing pages: `/places/`, `/people/`, `/folklore/`, `/themes/`
  (`entity_list.html`, four thin views). Places & people are grouped by type
  (place_type / person_type) with per-group counts; folklore is A–Z; themes keep
  the taxonomy order and show their descriptions.
- Client-side sort toggle (`entity-list.js`) — restore the server order, A–Z, or
  most-mentioned — as progressive enhancement (the grouped list stands without JS).
- Landing page: the stats row is now a labelled "Browse" set of links to these
  pages (+ a folklore count); the "How it was built" copy links to the indexes.
- Each entity detail page's centre nav link now points at its index
  ("All places", "All people", …).
- Note: `Theme.objects.annotate(Count(...))` drops `Meta.ordering` — the theme
  list re-applies `.order_by("order", "slug")` explicitly.
