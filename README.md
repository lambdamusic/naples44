# Naples '44: An Interactive Timelime

An interactive timeline of Naples ’44 - a [book](https://en.wikipedia.org/wiki/Naples_%2744) by Norman Lewis.

Norman Lewis was a British intelligence officer posted to Naples in the year after the Allied landings. His diary of that year — published in 1978 as Naples ’44 — is a spare, unsparing record of a city surviving occupation, hunger, the black market, bombardment and the everyday theatre of Neapolitan life. This site lets you move through the book by date.

> The site is live at https://naples44.michelepasin.org/

## Development

A static website built with the **Django-as-a-static-site-generator** pattern
([methodology](https://www.michelepasin.org/blog/2021/10/29/django-wget-static-site/index.html)).

Django is used purely as an authoring/templating/admin tool. Content is modelled
as Django models against a local **sqlite** DB, edited through the Django admin,
rendered by normal Django views/templates on the local dev server, then
`wget --mirror`'d into `docs/`, which **GitHub Pages** serves directly. There is
no production Django deployment.


## Layout

```
src/
  apps/naples44/       primary Django app (models, views, templates, admin)
  libs/                vendored non-pip code (sys.path-appended)
  static/              source CSS/JS/img (STATICFILES_DIRS)
  templates-global/    project-wide templates (base.html)
  fixtures/            hand-authored fixtures
  manage.py settings.py urls.py wsgi.py local_settings_example.py
build/                 disposable wget mirror target (gitignored)
docs/                  committed static output GitHub Pages publishes (/docs)
backups/django/        portable JSON fixtures (manage.py dumpdata) — the real backup
tools/                 shell scripts = the whole operational surface
```

`db.sqlite3` and `src/local_settings.py` are gitignored. Portability comes from
the JSON fixtures in `backups/django/`, not the sqlite file.

## Setup

```bash
# virtualenv (already created at ~/Envs/naples44_2026)
workon naples44_2026            # or: source ~/Envs/naples44_2026/bin/activate
pip install -r requirements.txt

cp src/local_settings_example.py src/local_settings.py   # then set a real SECRET_KEY
cp tools/db-bootstrap_EXAMPLE tools/db-bootstrap         # fill in superuser creds
./tools/db-bootstrap                                     # makemigrations + migrate + superuser
```

## Day-to-day loop

| Command | What it does |
| --- | --- |
| `./tools/run-dev-local-db` | Run the dev server (`runserver_plus`) on `127.0.0.1:8000` — author content in the Django admin, preview rendered views. |
| `./tools/db-dump` | Dump DB data to `backups/django/dump.json` (commit this). |
| `./tools/db-load backups/django/dump.json` | Load a JSON fixture into an empty DB. |
| `./tools/site-dump` | With the dev server running: wget-mirror it into `build/`, rsync into `docs/`. |
| `./tools/site-dump-and-publish` | `site-dump` + `git add -A && git commit && git push`. |
| `./tools/run-static-site` | Serve `docs/` at `127.0.0.1:9111` to preview the published output. |

## Publishing

GitHub Pages → deploy from **`/docs` on the default branch**. Custom domain is
set via `docs/CNAME` (`naples44.michelepasin.org`); `docs/.nojekyll` is present
so Pages serves files/paths starting with `_` untouched. Both are excluded from
the `site-dump` rsync so they survive regeneration.
