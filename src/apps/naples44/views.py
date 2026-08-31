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
