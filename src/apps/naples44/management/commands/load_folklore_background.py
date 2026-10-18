"""
Load the reviewed folklore background draft into FolkloreEntity.background /
background_sources.

The draft is markdown with one section per entity, headed `## <slug> — <Name>`.
Each paragraph is followed by a `Sources: [label](url) · …` line; the paragraphs
become `background`, and their links (deduplicated, in order) become a single
`background_sources` line. `**[check …]**` review flags are dropped. A section with
no paragraphs clears the entity's background.

    ./src/manage.py load_folklore_background plan-files/folklore-background.md
    ./src/manage.py load_folklore_background plan-files/folklore-background.md --dry-run
"""

import re

from django.core.management.base import BaseCommand, CommandError

from naples44 import models

HEADING = re.compile(r"(?m)^## (\S+)")
CHECK_FLAG = re.compile(r"\s*\*\*\[check[^\]]*\]\*\*")
LINK = re.compile(r"\[([^\]]+)\]\((\S+?)\)")


def parse(text):
    """{slug: (background, sources)} from the draft."""
    parts = HEADING.split(text)
    out = {}
    for slug, body in zip(parts[1::2], parts[2::2]):
        blocks = [b.strip() for b in re.split(r"\n\s*\n", body)]
        blocks = [b for b in blocks[1:] if b and b != "---"]  # [0] is the rest of the heading line
        paras, links = [], {}
        for b in blocks:
            if b.startswith("Sources:"):
                for label, url in LINK.findall(b):
                    links.setdefault(url, label)
            else:
                paras.append(CHECK_FLAG.sub("", b))
        sources = " · ".join(f"[{label}]({url})" for url, label in links.items())
        out[slug] = ("\n\n".join(paras), sources)
    return out


class Command(BaseCommand):
    help = "Load folklore background paragraphs + sources from a reviewed markdown draft."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        with open(opts["path"], encoding="utf-8") as fh:
            sections = parse(fh.read())
        if not sections:
            raise CommandError("No `## <slug>` sections found.")

        by_slug = {f.slug: f for f in models.FolkloreEntity.objects.all()}
        unknown = sorted(set(sections) - set(by_slug))
        if unknown:
            raise CommandError("Unknown slugs: " + ", ".join(unknown))

        changed = 0
        for slug, (background, sources) in sections.items():
            ent = by_slug[slug]
            if (ent.background, ent.background_sources) == (background, sources):
                continue
            changed += 1
            self.stdout.write(f"  {ent.name}: {len(background.split())} words, "
                              f"{sources.count('](')} sources")
            if not opts["dry_run"]:
                ent.background, ent.background_sources = background, sources
                ent.save(update_fields=["background", "background_sources"])

        missing = sorted(set(by_slug) - set(sections))
        if missing:
            self.stdout.write(self.style.WARNING("Not in the draft: " + ", ".join(missing)))
        self.stdout.write(f"updated: {changed}")
        if opts["dry_run"]:
            self.stdout.write(self.style.NOTICE("(dry run — nothing saved)"))
        elif changed:
            self.stdout.write(self.style.SUCCESS("Run tools/db-dump to snapshot."))
