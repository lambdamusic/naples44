# naples44 — project context for Claude Code

## What this is

An interactive visualisation of the WWII memoir *Naples '44* by Norman Lewis
(British intelligence officer, Naples Sept 1943 – Oct 1944). Michele hand-built a
structured dataset of the book while reading it; this repo turns it into a
website.

**Planned UI:** a concentric **radial timeline** — inner ring = the book's 108
dated diary entries, outer ring = 20 broader WWII / Italian-campaign events, on a
shared date axis. Hover an entry → summary + themes + tags. Tag legend with
filtering. Wikipedia links on entities. Phase 2 also gives **each entity its own
URL** (entry, place, person, folklore entity, theme, event) alongside the
timeline navigation view. Phase 2 starts as a PoC.

## Architecture

This uses the **Django-as-a-static-site-generator** pattern (see `README.md` and
the `init-django-static-site` skill): Django + sqlite is an authoring/admin tool
only; the published output is `wget --mirror`'d into `docs/` and served by GitHub
Pages. No live Django deployment.

- App: `src/apps/naples44/` — `models.py`, `admin.py`, plus the seed importer
  `management/commands/import_naples_data.py`.
- venv: `~/Envs/naples44_2026` (`workon naples44_2026`).
- Custom domain: `naples44.michelepasin.org` (`docs/CNAME`).

## Data

- **`backups/django/dump.json`** is the committed source of truth for the data
  (479 objects). Load a fresh DB with `./tools/db-load backups/django/dump.json`.
- `plan-files/` (gitignored) holds the original hand-built JSON. It was a
  **one-time seed** via `import_naples_data`; **the Django admin is the editor
  now**, and `./tools/db-dump` re-snapshots to `dump.json` after admin edits.
- Model map: `Entry` (pk = source id 1–108, `chapter` ≈ id+1, `date` is a real
  DateField for the timeline angle) → M2M `themes` (11, controlled), `places`
  (129, typed, some `wikipedia_url`); through-models `EntryPerson` /
  `EntryFolklore` carry a per-occurrence `note`; `Reflection` rows belong to one
  entry. `OuterRingEvent` = the 20 outer-ring events.

## Workflow

| Command | Purpose |
| --- | --- |
| `./tools/run-dev-local-db` | dev server on `127.0.0.1:8000` (admin + views) |
| `./tools/db-dump` | snapshot DB → `backups/django/dump.json` (commit it) |
| `./tools/db-load backups/django/dump.json` | load fixture into an empty DB |
| `./tools/site-dump` | wget-mirror the running server into `docs/` |
| `./tools/site-dump-and-publish` | site-dump + commit + push |

No superuser is committed; run `tools/db-bootstrap` (copy from `_EXAMPLE`) to make one.

## Conventions

- Entry summaries are **paraphrased, never verbatim** (copyright) — keep it that way.
- Ambiguous identifications were deliberately left unlinked; don't guess Wikipedia URLs.
- Frontend viz (phase 2) uses **D3 v7 vendored** into `src/static/js/` — no CDN.
