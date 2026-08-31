"""
Fill in Place.latitude / Place.longitude for the map on place pages.

Two sources, tried in order:
  1. Wikipedia — for places that already have a `wikipedia_url` (precise, canonical).
  2. Nominatim (OpenStreetMap) — everything else, biased toward Campania.

By default only places with no coordinates are touched, so manual corrections in
the admin are never overwritten. Nominatim's usage policy caps us at 1 req/s.

    ./src/manage.py geocode_places            # fill in what's missing
    ./src/manage.py geocode_places --dry-run
    ./src/manage.py geocode_places --refresh  # re-geocode everything (except manual)
"""

import time
import urllib.parse
import urllib.request
import json

from django.core.management.base import BaseCommand

from naples44 import models

UA = "naples44-static-site/1.0 (https://naples44.michelepasin.org; personal reading project)"

# rough Campania bounding box — coords outside are reported for a manual eyeball,
# not treated as errors (Rome, Cassino, Anzio, Paestum etc. are legitimately outside)
CAMPANIA = {"lat": (39.9, 41.7), "lon": (13.6, 16.1)}

NAPLES_LOCAL_TYPES = {"street", "piazza", "district"}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def wikipedia_coords(wikipedia_url):
    """(lat, lon) from the article named in a wikipedia URL, or None."""
    try:
        title = urllib.parse.unquote(wikipedia_url.rstrip("/").split("/wiki/", 1)[1])
    except IndexError:
        return None
    api = (
        "https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1"
        "&prop=coordinates&coprimary=primary&titles=" + urllib.parse.quote(title)
    )
    data = _get(api)
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        coords = page.get("coordinates")
        if coords:
            return coords[0]["lat"], coords[0]["lon"]
    return None


def nominatim_coords(place):
    queries = []
    if place.place_type in NAPLES_LOCAL_TYPES:
        queries.append(f"{place.name}, Naples, Italy")
    queries.append(f"{place.name}, Campania, Italy")
    queries.append(f"{place.name}, Italy")
    for q in queries:
        url = (
            "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1"
            "&viewbox=13.6,41.7,16.1,39.9"  # bias toward Campania, not bounded
            "&q=" + urllib.parse.quote(q)
        )
        results = _get(url)
        time.sleep(1.1)  # Nominatim: max 1 request/second
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"]), q
    return None


class Command(BaseCommand):
    help = "Geocode Place rows (Wikipedia first, then Nominatim)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--refresh", action="store_true",
            help="Re-geocode places even if they already have coordinates "
            "(rows with geocode_source='manual' are still skipped).",
        )

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        qs = models.Place.objects.all().order_by("name")
        if not opts["refresh"]:
            qs = qs.filter(latitude__isnull=True)
        else:
            qs = qs.exclude(geocode_source="manual")

        from_wiki = from_nominatim = failed = 0
        outside = []

        for place in qs:
            hit = None
            if place.wikipedia_url:
                try:
                    wc = wikipedia_coords(place.wikipedia_url)
                except Exception as exc:  # noqa: BLE001
                    wc = None
                    self.stderr.write(f"  wiki error for {place.name}: {exc}")
                if wc:
                    hit = (wc[0], wc[1], "wikipedia")
                    from_wiki += 1
                time.sleep(0.1)

            if hit is None:
                try:
                    nc = nominatim_coords(place)
                except Exception as exc:  # noqa: BLE001
                    nc = None
                    self.stderr.write(f"  nominatim error for {place.name}: {exc}")
                if nc:
                    hit = (nc[0], nc[1], "nominatim")
                    from_nominatim += 1
                    self.stdout.write(f"  {place.name}: nominatim via '{nc[2]}'")

            if hit is None:
                failed += 1
                self.stdout.write(self.style.WARNING(f"  NO MATCH: {place.name} ({place.place_type})"))
                continue

            lat, lon, source = hit
            if not (CAMPANIA["lat"][0] <= lat <= CAMPANIA["lat"][1]
                    and CAMPANIA["lon"][0] <= lon <= CAMPANIA["lon"][1]):
                outside.append(f"{place.name} -> {lat:.4f},{lon:.4f} ({source})")

            if not dry:
                place.latitude = lat
                place.longitude = lon
                place.geocode_source = source
                place.save(update_fields=["latitude", "longitude", "geocode_source"])

        self.stdout.write("")
        self.stdout.write(f"from wikipedia: {from_wiki}")
        self.stdout.write(f"from nominatim: {from_nominatim}")
        self.stdout.write(f"no match:       {failed}")
        if outside:
            self.stdout.write(self.style.WARNING(
                "\nOutside Campania (eyeball these — some are correct, e.g. Rome/Cassino):"
            ))
            for line in outside:
                self.stdout.write(f"  {line}")
        if dry:
            self.stdout.write(self.style.NOTICE("\n(dry run — nothing saved)"))
        else:
            self.stdout.write(self.style.SUCCESS("\nSaved. Run tools/db-dump to snapshot."))
