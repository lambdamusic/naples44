"""
Builds the single JSON payload the timeline front-end consumes.

Kept deliberately flat and self-contained: the whole dataset is small (~108
entries), so the timeline page embeds it via {{ ... |json_script }} rather than
fetching it — which also means the wget-mirrored static copy works offline.
"""

from django.db.models import Prefetch

from . import models


def _entry_dict(e):
    # tag `url`s point at the on-site entity page, never an external resource
    people = [
        {
            "name": ep.person.name,
            "type": ep.person.person_type,
            "type_label": ep.person.get_person_type_display(),
            "note": ep.note,
            "url": ep.person.get_absolute_url(),
        }
        for ep in e.entryperson_set.all()
    ]
    folklore = [
        {
            "name": ef.folklore.name,
            "note": ef.note,
            "url": ef.folklore.get_absolute_url(),
        }
        for ef in e.entryfolklore_set.all()
    ]
    places = [
        {
            "name": p.name,
            "type": p.place_type,
            "type_label": p.get_place_type_display(),
            "url": p.get_absolute_url(),
        }
        for p in e.places.all()
    ]
    reflections = [{"title": r.title, "note": r.note} for r in e.reflections.all()]
    return {
        "id": e.id,
        "chapter": e.chapter,
        "year": e.year,
        "date_label": e.date_label,
        "date": e.date.isoformat(),
        "summary": e.summary,
        "url": e.get_absolute_url(),
        "themes": list(e.themes.values_list("slug", flat=True)),
        "places": places,
        "people": people,
        "folklore": folklore,
        "reflections": reflections,
    }


def build_payload():
    entries_qs = (
        models.Entry.objects.all()
        .prefetch_related(
            "themes",
            "places",
            "reflections",
            Prefetch(
                "entryperson_set",
                queryset=models.EntryPerson.objects.select_related("person").order_by(
                    "person__name"
                ),
            ),
            Prefetch(
                "entryfolklore_set",
                queryset=models.EntryFolklore.objects.select_related("folklore").order_by(
                    "folklore__name"
                ),
            ),
        )
        .order_by("date", "id")
    )
    entries = [_entry_dict(e) for e in entries_qs]

    events = [
        {
            "date": ev.date.isoformat(),
            "title": ev.title,
            "category": ev.category,
            "note": ev.note,
            "link": ev.link,
        }
        for ev in models.OuterRingEvent.objects.all()
    ]

    themes = [
        {
            "slug": t.slug,
            "label": t.label,
            "description": t.description,
            "url": t.get_absolute_url(),
        }
        for t in models.Theme.objects.all()
    ]

    entry_dates = [e["date"] for e in entries]
    event_dates = [ev["date"] for ev in events]
    return {
        "entries": entries,
        "events": events,
        "themes": themes,
        "meta": {
            # the timeline axis is driven by the book's own span, not the war events
            "entry_date_min": min(entry_dates),
            "entry_date_max": max(entry_dates),
            "event_date_min": min(event_dates),
            "event_date_max": max(event_dates),
            "entry_count": len(entries),
        },
    }
