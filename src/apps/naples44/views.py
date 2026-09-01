from urllib.parse import quote_plus

from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

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
            "folklore_count": models.FolkloreEntity.objects.count(),
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
        {
            "entry": entry,
            "prev_entry": prev_entry,
            "next_entry": next_entry,
            "icon": "entry",
        },
    )


# --- entity pages ---------------------------------------------------------

def _google_url(name):
    return "https://www.google.com/search?q=" + quote_plus(f'"{name}" naples 44')


def _neighbours(model, obj):
    """(previous, next) sibling in the model's default ordering."""
    pks = list(model.objects.values_list("pk", flat=True))
    try:
        i = pks.index(obj.pk)
    except ValueError:
        return None, None
    prev = model.objects.get(pk=pks[i - 1]) if i > 0 else None
    nxt = model.objects.get(pk=pks[i + 1]) if i < len(pks) - 1 else None
    return prev, nxt


_ENTITY_INDEX = {
    "place": ("naples44:place_list", "All places"),
    "person": ("naples44:person_list", "All people"),
    "folklore": ("naples44:folklore_list", "All saints & folklore"),
    "theme": ("naples44:theme_list", "All themes"),
}


def _render_entity(request, *, kind, icon, entity, subtitle, rows, extra=None):
    prev_entity, next_entity = _neighbours(type(entity), entity)
    idx = _ENTITY_INDEX.get(icon)
    ctx = {
        "kind": kind,
        "icon": icon,
        "entity": entity,
        "subtitle": subtitle,
        "rows": rows,
        "google_url": _google_url(entity.name),
        "prev_entity": prev_entity,
        "next_entity": next_entity,
        "index_url": reverse(idx[0]) if idx else None,
        "index_label": idx[1] if idx else "",
    }
    ctx.update(extra or {})
    return render(request, "naples44/entity_detail.html", ctx)


def _plain_rows(entries):
    return [{"entry": e, "note": ""} for e in entries]


_MAP_ZOOM = {
    "street": 15, "piazza": 15, "landmark": 14, "religious_site": 14,
    "district": 14, "town": 12, "region": 10, "natural_feature": 11,
}


def place_detail(request, slug):
    place = get_object_or_404(models.Place, slug=slug)
    entries = list(place.entries.order_by("date", "id").prefetch_related("themes"))

    place_map = None
    if place.has_coords:
        others = (
            models.Place.objects.filter(entries__in=entries, latitude__isnull=False)
            .exclude(pk=place.pk)
            .distinct()
        )
        place_map = {
            "focus": {"name": place.name, "lat": place.latitude, "lon": place.longitude},
            "zoom": _MAP_ZOOM.get(place.place_type, 13),
            "others": [
                {
                    "name": o.name,
                    "lat": o.latitude,
                    "lon": o.longitude,
                    "url": o.get_absolute_url(),
                }
                for o in others
            ],
        }

    return _render_entity(
        request,
        kind="Place",
        icon="place",
        entity=place,
        subtitle=place.get_place_type_display(),
        rows=_plain_rows(entries),
        extra={"place_map": place_map},
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
        icon="person",
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
        request,
        kind="Saint / folklore",
        icon="folklore",
        entity=ent,
        subtitle="",
        rows=rows,
    )


def theme_detail(request, slug):
    theme = get_object_or_404(models.Theme, slug=slug)
    entries = theme.entries.order_by("date", "id").prefetch_related("themes")
    return _render_entity(
        request,
        kind="Theme",
        icon="theme",
        entity=theme,
        subtitle="",
        rows=_plain_rows(entries),
    )


# --- entity index pages -------------------------------------------------

def _item(obj, count):
    return {"name": obj.name, "url": obj.get_absolute_url(), "count": count,
            "description": getattr(obj, "description", "")}


def _render_index(request, *, kind, icon, groups, total, blurb,
                  first_sort_label, wide=False):
    return render(
        request,
        "naples44/entity_list.html",
        {
            "kind": kind,
            "icon": icon,
            "groups": groups,               # [{"label": str|None, "items": [...]}]
            "total": total,
            "blurb": blurb,
            "wide": wide,                   # one-column rows (items with a description)
            # label for the button that restores the server-rendered order
            "first_sort_label": first_sort_label,
        },
    )


_PLACE_GROUP_LABELS = {
    "street": "Streets", "piazza": "Piazzas", "landmark": "Landmarks",
    "district": "Districts", "religious_site": "Religious sites",
    "town": "Towns", "region": "Regions", "natural_feature": "Natural features",
}
_PERSON_GROUP_LABELS = {
    "camorrista_bandit": "Camorristi & bandits",
    "police_official": "Police officials",
    "informant_contact": "Informants & contacts",
    "companion": "Companions",
    "aristocrat": "Aristocrats",
    "allied_colleague": "Allied colleagues",
    "civilian_friend": "Civilian friends",
    "notable_civilian": "Notable civilians",
}


def _grouped_by(qs, field, labels):
    by_value = {}
    for obj in qs:
        by_value.setdefault(getattr(obj, field), []).append(obj)
    groups = []
    for value, label in labels.items():
        items = by_value.get(value)
        if items:
            groups.append({
                "label": label,
                "items": [_item(o, o.n) for o in sorted(items, key=lambda o: o.name.lower())],
            })
    return groups


def place_list(request):
    qs = models.Place.objects.annotate(n=Count("entries"))
    groups = _grouped_by(qs, "place_type", _PLACE_GROUP_LABELS)
    return _render_index(
        request, kind="Places", icon="place", groups=groups, total=qs.count(),
        first_sort_label="By type",
        blurb="Every place Lewis names in the diary, grouped by kind. "
        "Sort A–Z or by how often each is mentioned.",
    )


def person_list(request):
    qs = models.Person.objects.annotate(n=Count("entries"))
    groups = _grouped_by(qs, "person_type", _PERSON_GROUP_LABELS)
    return _render_index(
        request, kind="People", icon="person", groups=groups, total=qs.count(),
        first_sort_label="By type",
        blurb="The recurring figures of Naples ’44, grouped by their role.",
    )


def folklore_list(request):
    qs = models.FolkloreEntity.objects.annotate(n=Count("entries")).order_by("name")
    groups = [{"label": None, "items": [_item(o, o.n) for o in qs]}]
    return _render_index(
        request, kind="Saints & folklore", icon="folklore", groups=groups,
        total=qs.count(), first_sort_label="A–Z",
        blurb="Saints, feasts, miracles and superstitions recorded in the book.",
    )


def theme_list(request):
    qs = models.Theme.objects.annotate(n=Count("entries")).order_by("order", "slug")
    groups = [{"label": None, "items": [_item(o, o.n) for o in qs]}]
    return _render_index(
        request, kind="Themes", icon="theme", groups=groups, total=qs.count(),
        first_sort_label="In order", wide=True,
        blurb="The eleven threads running through the diary.",
    )
