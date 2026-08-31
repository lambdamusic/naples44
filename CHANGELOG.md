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
