"""Export the whole dataset as a schema.org-based RDF graph, serialized as Turtle.

    manage.py export_rdf              # writes backups/rdf/naples44.ttl
    manage.py export_rdf --output /tmp/x.ttl

Committed alongside backups/django/dump.json as a portable snapshot of the data.
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand
from rdflib.namespace import RDF

from naples44.rdf_export import build_graph

DEFAULT_OUTPUT = os.path.join(settings.SITE_ROOT, "backups", "rdf", "naples44.ttl")


class Command(BaseCommand):
    help = "Export the site's data as RDF (schema.org / Turtle)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=DEFAULT_OUTPUT,
            help=f"Path to write the .ttl file to (default: {DEFAULT_OUTPUT})",
        )

    def handle(self, *args, **options):
        output_path = options["output"]
        graph = build_graph()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        graph.serialize(destination=output_path, format="turtle")

        counts = {}
        for _, _, obj in graph.triples((None, RDF.type, None)):
            counts[str(obj)] = counts.get(str(obj), 0) + 1

        self.stdout.write(
            self.style.SUCCESS(f"Wrote {len(graph)} triples to {output_path}")
        )
        for key, count in sorted(counts.items()):
            self.stdout.write(f"  {key}: {count}")
