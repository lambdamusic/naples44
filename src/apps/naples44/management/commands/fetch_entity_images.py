"""
Download the Wikipedia lead image for any Place / Person / FolkloreEntity that has
a `wikipedia_url` (and, for each Theme, the hand-picked file in THEME_IMAGES), into src/static/img/entities/<model>/<slug>.<ext>, and record
its path, source page and credit (author + licence, from Commons metadata).

Images are fetched once and stored locally — the static site never hotlinks.
Only rows with no image are touched, unless --refresh is given.

    ./src/manage.py fetch_entity_images
    ./src/manage.py fetch_entity_images --model folklore --refresh
    ./src/manage.py fetch_entity_images --model person --only vito-genovese
"""

import html
import json
import os
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand

from naples44 import models

UA = "naples44-static-site/1.0 (https://naples44.michelepasin.org; personal reading project)"
API = "https://en.wikipedia.org/w/api.php"
THUMB_WIDTH = 800
IMG_DIR = "img/entities"
# flags, locator maps and logos make poor page pictures: on Commons they are
# nearly always SVG (or GIF), so those are skipped outright
SKIP_FILE = re.compile(r"\.(svg|gif)$|logo", re.I)
PNG_TO_JPEG_OVER = 400 * 1024

MODELS = {
    "place": models.Place,
    "person": models.Person,
    "folklore": models.FolkloreEntity,
    "theme": models.Theme,
}

# Themes have no Wikipedia article of their own, so each gets a hand-picked
# Commons file — period photographs of Naples 1943–44 where one fits.
THEME_IMAGES = {
    "war_violence": "Un ragazzo italiano sostiene il suo amico ferito gravemente durante il bombardamento alleato su Napoli nel 1943.jpg",
    "black_market": "Wayne Miller - Giovane venditrice.jpg",
    "poverty_hunger": "Children of Naples, Italy - NARA - 520941.jpg",
    "sex_relationships": "The Skin poster.jpg",
    "superstition_religion": "CornicelloCharm.jpg",
    "crime_banditry": "GiulianoGenovese1.jpg",
    "bureaucracy_absurdity": "Napoli, Gran Dogana Marittima (nel 1943).jpg",
    "naples_character": "Pulcinella - stampa ottocento.jpg",
    "disease_health": "SC 190591 - 23rd Gen. Hospital view of operating room. Naples, Italy, 10 September, 1944. (49764764041).jpg",
    "allied_conduct": "Napoli 1943, entrata degli alleati (1).jpg",
    "personal_reflection": "Norman Lewis (1908–2003).jpg",
}


def _get_json(params):
    url = API + "?" + urllib.parse.urlencode({"format": "json", **params})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def _first_page(data):
    pages = data.get("query", {}).get("pages", {})
    return next(iter(pages.values()), {})


def _plain(value):
    """Commons extmetadata values are HTML fragments; keep the first paragraph."""
    text = html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()
    text = re.split(r"\n\s*\n", text)[0]
    text = re.sub(r"\s+", " ", text).strip()
    m = re.fullmatch(r"(.+?)\1", text)  # "Unknown authorUnknown author"
    return m.group(1) if m else text


def _short(text, n):
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def lead_image(wikipedia_url):
    """{"src", "file_page", "credit"} for the article's lead image, or None."""
    try:
        title = urllib.parse.unquote(wikipedia_url.rstrip("/").split("/wiki/", 1)[1])
    except IndexError:
        return None

    page = _first_page(_get_json({
        "action": "query", "redirects": 1, "titles": title,
        "prop": "pageimages", "piprop": "name", "pilicense": "any",
    }))
    name = page.get("pageimage")
    if not name or SKIP_FILE.search(name):
        return None
    return commons_file(name)


def commons_file(name):
    """{"src", "file_page", "credit"} for a named file (Commons or local), or None."""
    info = _first_page(_get_json({
        "action": "query", "titles": "File:" + name,
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": THUMB_WIDTH,
    }))
    ii = (info.get("imageinfo") or [{}])[0]
    thumb = ii.get("thumburl")
    if not thumb:
        return None
    meta = ii.get("extmetadata", {})
    artist = _short(_plain(meta.get("Artist", {}).get("value")), 120)
    licence = _plain(meta.get("LicenseShortName", {}).get("value"))
    credit = " · ".join(x for x in (artist, licence) if x)[:300]

    return {
        "src": thumb,
        "file_page": ii.get("descriptionurl") or ("https://en.wikipedia.org/wiki/File:" + name),
        "credit": credit or "Wikimedia",
    }


def download(url, dest):
    """Save `url` to `dest`; a heavy PNG becomes a JPEG if macOS `sips` is around.
    Returns the path actually written."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as fh:
        fh.write(body)
    if dest.endswith(".png") and len(body) > PNG_TO_JPEG_OVER and shutil.which("sips"):
        jpg = dest[:-4] + ".jpg"
        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "80",
                        dest, "--out", jpg], check=True, capture_output=True)
        os.remove(dest)
        return jpg
    return dest


class Command(BaseCommand):
    help = "Download Wikipedia lead images for Place / Person / FolkloreEntity / Theme."

    def add_arguments(self, parser):
        parser.add_argument("--model", choices=sorted(MODELS), action="append",
                            help="Limit to this model (repeatable). Default: all four.")
        parser.add_argument("--refresh", action="store_true",
                            help="Re-fetch images that are already set.")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--only", nargs="*", metavar="SLUG",
                            help="Limit to these slugs.")

    def handle(self, *args, **opts):
        static_root = settings.STATICFILES_DIRS[0]
        names = opts["model"] or list(MODELS)
        done = skipped = failed = 0

        for name in names:
            Model = MODELS[name]
            if Model is models.Theme:
                qs = Model.objects.filter(slug__in=THEME_IMAGES)
            else:
                qs = Model.objects.exclude(wikipedia_url="").order_by("name")
            if opts["only"]:
                qs = qs.filter(slug__in=opts["only"])
            if not opts["refresh"]:
                qs = qs.filter(image="")
            if not qs.exists():
                continue

            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{name}:"))
            for obj in qs:
                try:
                    if Model is models.Theme:
                        img = commons_file(THEME_IMAGES[obj.slug])
                    else:
                        img = lead_image(obj.wikipedia_url)
                    if not img:
                        if obj.image and not opts["dry_run"]:  # --refresh dropped it
                            obj.image = obj.image_source_url = obj.image_credit = ""
                            obj.save(update_fields=["image", "image_source_url", "image_credit"])
                        skipped += 1
                        self.stdout.write(self.style.WARNING(f"  no lead image: {obj.name}"))
                        continue
                    ext = os.path.splitext(urllib.parse.urlparse(img["src"]).path)[1].lower() or ".jpg"
                    rel = f"{IMG_DIR}/{name}/{obj.slug}{ext}"
                    size = 0
                    if not opts["dry_run"]:
                        path = download(img["src"], os.path.join(static_root, rel))
                        rel = os.path.relpath(path, static_root)
                        size = os.path.getsize(path)
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    self.stderr.write(f"  {obj.name}: {exc}")
                    continue
                time.sleep(0.2)

                self.stdout.write(f"  {obj.name}: {rel} ({size // 1024} KB) — {img['credit'][:70]}")
                if not opts["dry_run"]:
                    obj.image = rel
                    obj.image_source_url = img["file_page"]
                    obj.image_credit = img["credit"]
                    obj.save(update_fields=["image", "image_source_url", "image_credit"])
                done += 1

        self.stdout.write("")
        self.stdout.write(f"set: {done}   skipped: {skipped}   failed: {failed}")
        if opts["dry_run"]:
            self.stdout.write(self.style.NOTICE("(dry run — nothing saved)"))
        elif done:
            self.stdout.write(self.style.SUCCESS("Run tools/db-dump to snapshot."))
