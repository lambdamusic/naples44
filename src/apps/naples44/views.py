from django.shortcuts import get_object_or_404, render

from . import models
from .payload import build_payload


def index(request):
    return render(
        request,
        "naples44/index.html",
        {
            "entry_count": models.Entry.objects.count(),
            "place_count": models.Place.objects.count(),
            "people_count": models.Person.objects.count(),
            "theme_count": models.Theme.objects.count(),
            "event_count": models.OuterRingEvent.objects.count(),
        },
    )


def timeline(request):
    return render(request, "naples44/timeline.html", {"payload": build_payload()})


def entry_detail(request, entry_id):
    entry = get_object_or_404(
        models.Entry.objects.prefetch_related(
            "themes", "places", "reflections",
            "entryperson_set__person", "entryfolklore_set__folklore",
        ),
        pk=entry_id,
    )
    # ids are sequential in reading/date order (1..108), so neighbours are pk±1
    prev_entry = models.Entry.objects.filter(pk__lt=entry.pk).order_by("-pk").first()
    next_entry = models.Entry.objects.filter(pk__gt=entry.pk).order_by("pk").first()
    return render(
        request,
        "naples44/entry_detail.html",
        {"entry": entry, "prev_entry": prev_entry, "next_entry": next_entry},
    )


# --- entity pages ---------------------------------------------------------

def _render_entity(request, *, kind, entity, subtitle, rows):
    return render(
        request,
        "naples44/entity_detail.html",
        {"kind": kind, "entity": entity, "subtitle": subtitle, "rows": rows},
    )


def _plain_rows(entries):
    return [{"entry": e, "note": ""} for e in entries]


def place_detail(request, slug):
    place = get_object_or_404(models.Place, slug=slug)
    entries = place.entries.order_by("date", "id").prefetch_related("themes")
    return _render_entity(
        request,
        kind="Place",
        entity=place,
        subtitle=place.get_place_type_display(),
        rows=_plain_rows(entries),
    )


def person_detail(request, slug):
    person = get_object_or_404(models.Person, slug=slug)
    links = (
        models.EntryPerson.objects.filter(person=person)
        .select_related("entry")
        .order_by("entry__date", "entry__id")
    )
    rows = [{"entry": link.entry, "note": link.note} for link in links]
    return _render_entity(
        request,
        kind="Person",
        entity=person,
        subtitle=person.get_person_type_display(),
        rows=rows,
    )


def folklore_detail(request, slug):
    ent = get_object_or_404(models.FolkloreEntity, slug=slug)
    links = (
        models.EntryFolklore.objects.filter(folklore=ent)
        .select_related("entry")
        .order_by("entry__date", "entry__id")
    )
    rows = [{"entry": link.entry, "note": link.note} for link in links]
    return _render_entity(
        request, kind="Saint / folklore", entity=ent, subtitle="", rows=rows
    )


def theme_detail(request, slug):
    theme = get_object_or_404(models.Theme, slug=slug)
    entries = theme.entries.order_by("date", "id").prefetch_related("themes")
    return _render_entity(
        request,
        kind="Theme",
        entity=theme,
        subtitle="",
        rows=_plain_rows(entries),
    )
