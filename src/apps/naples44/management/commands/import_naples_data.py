"""
One-time seed importer for the Naples '44 dataset.

Reads the hand-built JSON in `plan-files/` (gitignored) and populates the DB.
Idempotent: re-running updates existing rows and clears/reassigns entry tags.
After a successful run, snapshot the data with `tools/db-dump`.

    ./src/manage.py import_naples_data
"""

import datetime
import json
import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from naples44 import models

MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        start=1,
    )
}

# Display labels for the 11 controlled themes (keys must match the source vocab).
THEME_LABELS = {
    "war_violence": "War & violence",
    "black_market": "Black market",
    "poverty_hunger": "Poverty & hunger",
    "sex_relationships": "Sex & relationships",
    "superstition_religion": "Superstition & religion",
    "crime_banditry": "Crime & banditry",
    "bureaucracy_absurdity": "Bureaucracy & absurdity",
    "naples_character": "Naples's character",
    "disease_health": "Disease & health",
    "allied_conduct": "Allied conduct",
    "personal_reflection": "Personal reflection",
}

DATE_RE = re.compile(r"^([A-Za-z]+)\s+(\d{1,2})")


def resolve_date(date_label: str, year: int) -> datetime.date:
    m = DATE_RE.match(date_label.strip())
    if not m or m.group(1) not in MONTHS:
        raise CommandError(f"Cannot parse date label: {date_label!r}")
    return datetime.date(year, MONTHS[m.group(1)], int(m.group(2)))


class Command(BaseCommand):
    help = "Seed the DB from plan-files/*.json (one-time import; admin is the editor afterwards)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default=os.path.join(settings.SITE_ROOT, "plan-files"),
            help="Folder holding the source JSON files (default: <repo>/plan-files).",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        base = opts["dir"]
        entries_path = os.path.join(base, "naples-44-entries.json")
        events_path = os.path.join(base, "naples-44-outer-ring-events.json")
        for p in (entries_path, events_path):
            if not os.path.exists(p):
                raise CommandError(f"Missing source file: {p}")

        data = json.load(open(entries_path))
        events = json.load(open(events_path))
        links = data.get("links", {})
        taxonomy = data.get("taxonomy", {})

        self._import_themes(taxonomy.get("themes", {}))
        self._import_events(events["events"])
        self._import_entries(data["entries"], links)

        self.stdout.write(self.style.SUCCESS("Import complete. Run tools/db-dump to snapshot."))

    def _import_themes(self, themes: dict):
        for order, (slug, description) in enumerate(themes.items()):
            models.Theme.objects.update_or_create(
                slug=slug,
                defaults={
                    "label": THEME_LABELS.get(slug, slug.replace("_", " ").title()),
                    "description": description,
                    "order": order,
                },
            )
        self.stdout.write(f"themes: {models.Theme.objects.count()}")

    def _import_events(self, events: list):
        for ev in events:
            models.OuterRingEvent.objects.update_or_create(
                title=ev["title"],
                date=datetime.date.fromisoformat(ev["date"]),
                defaults={
                    "category": ev["category"],
                    "note": ev.get("note", ""),
                    "link": ev.get("link", "") or "",
                },
            )
        self.stdout.write(f"outer-ring events: {models.OuterRingEvent.objects.count()}")

    def _import_entries(self, entries: list, links: dict):
        for raw in entries:
            entry, _ = models.Entry.objects.update_or_create(
                id=raw["id"],
                defaults={
                    "chapter": raw["chapter"],
                    "year": int(raw["year"]),
                    "date_label": raw["date"],
                    "date": resolve_date(raw["date"], int(raw["year"])),
                    "summary": raw["summary"],
                },
            )
            tags = raw["tags"]

            entry.themes.set(
                models.Theme.objects.filter(slug__in=tags.get("themes", []))
            )

            places = []
            for p in tags.get("places", []):
                place, _ = models.Place.objects.get_or_create(
                    name=p["name"],
                    defaults={"place_type": p["type"]},
                )
                self._maybe_link(place, links)
                places.append(place)
            entry.places.set(places)

            # reflections belong to the entry — rebuild them
            entry.reflections.all().delete()
            for order, r in enumerate(tags.get("reflections", [])):
                models.Reflection.objects.create(
                    entry=entry, title=r["title"], note=r["note"], order=order
                )

            # people / folklore carry a per-occurrence note -> through rows
            models.EntryPerson.objects.filter(entry=entry).delete()
            for p in tags.get("named_people", []):
                person, _ = models.Person.objects.get_or_create(
                    name=p["name"], defaults={"person_type": p["type"]}
                )
                self._maybe_link(person, links)
                models.EntryPerson.objects.create(
                    entry=entry, person=person, note=p.get("note", "") or ""
                )

            models.EntryFolklore.objects.filter(entry=entry).delete()
            for f in tags.get("saints_folklore", []):
                ent, _ = models.FolkloreEntity.objects.get_or_create(name=f["name"])
                self._maybe_link(ent, links)
                models.EntryFolklore.objects.create(
                    entry=entry, folklore=ent, note=f.get("note", "") or ""
                )

        self.stdout.write(
            "entries: {e}  places: {p}  people: {pe}  folklore: {f}  reflections: {r}".format(
                e=models.Entry.objects.count(),
                p=models.Place.objects.count(),
                pe=models.Person.objects.count(),
                f=models.FolkloreEntity.objects.count(),
                r=models.Reflection.objects.count(),
            )
        )

    @staticmethod
    def _maybe_link(obj, links: dict):
        url = links.get(obj.name)
        if url and getattr(obj, "wikipedia_url", None) != url:
            obj.wikipedia_url = url
            obj.save(update_fields=["wikipedia_url"])
