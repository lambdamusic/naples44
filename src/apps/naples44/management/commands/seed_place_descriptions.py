"""
Seed Place.description with a 2–3 sentence factual blurb from Wikipedia.

Uses the article named in each place's `wikipedia_url`. Only touches places whose
description is currently empty, unless --refresh is given. `book_role` is never
touched here — that field is hand-written.

    ./src/manage.py seed_place_descriptions
    ./src/manage.py seed_place_descriptions --refresh
    ./src/manage.py seed_place_descriptions --only afragola benevento
"""

import re
import time
import urllib.parse
import urllib.request
import json

from django.core.management.base import BaseCommand

from naples44 import models

UA = "naples44-static-site/1.0 (https://naples44.michelepasin.org; personal reading project)"
MAX_SENTENCES = 3
MAX_CHARS = 500

# don't split on the dot in these
_ABBR = re.compile(r"\b(?:St|Mt|Mr|Mrs|Ms|Dr|c|ca|no|vs|approx)\.$", re.I)


def first_sentences(text, n=MAX_SENTENCES):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?]) +", text)
    out = []
    for p in parts:
        out.append(p)
        joined = " ".join(out)
        if len(out) >= n and not _ABBR.search(out[-1]):
            break
        if len(joined) > MAX_CHARS:
            break
    return " ".join(out).strip()


def wikipedia_summary(wikipedia_url):
    try:
        title = wikipedia_url.rstrip("/").split("/wiki/", 1)[1]
    except IndexError:
        return None
    api = "https://en.wikipedia.org/api/rest_v1/page/summary/" + title
    req = urllib.request.Request(api, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    if data.get("type") == "disambiguation":
        return None
    return data.get("extract") or ""


class Command(BaseCommand):
    help = "Fill Place.description from Wikipedia (2–3 sentences)."

    def add_arguments(self, parser):
        parser.add_argument("--refresh", action="store_true",
                            help="Overwrite descriptions that are already set.")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--only", nargs="*", metavar="SLUG",
                            help="Limit to these place slugs.")

    def handle(self, *args, **opts):
        qs = models.Place.objects.exclude(wikipedia_url="").order_by("name")
        if opts["only"]:
            qs = qs.filter(slug__in=opts["only"])
        if not opts["refresh"]:
            qs = qs.filter(description="")

        done = skipped = failed = 0
        for place in qs:
            try:
                extract = wikipedia_summary(place.wikipedia_url)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.stderr.write(f"  {place.name}: {exc}")
                continue
            time.sleep(0.2)

            blurb = first_sentences(extract)
            if not blurb:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"  no usable extract: {place.name}"))
                continue

            self.stdout.write(f"  {place.name}: {blurb[:110]}{'…' if len(blurb) > 110 else ''}")
            if not opts["dry_run"]:
                place.description = blurb
                place.save(update_fields=["description"])
            done += 1

        self.stdout.write("")
        self.stdout.write(f"set: {done}   skipped: {skipped}   failed: {failed}")
        if opts["dry_run"]:
            self.stdout.write(self.style.NOTICE("(dry run — nothing saved)"))
        elif done:
            self.stdout.write(self.style.SUCCESS("Run tools/db-dump to snapshot."))
