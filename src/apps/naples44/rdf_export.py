"""
Builds an RDF graph of the whole Naples '44 dataset, using a deliberately small
schema.org-based model, for export as Turtle (see the `export_rdf` command).

The model, in one paragraph:

* the book is a ``schema:Book`` (``id:naples-44``);
* each diary entry is a ``schema:Chapter`` of it — ``schema:abstract`` carries the
  paraphrased summary, ``schema:dateCreated`` the diary date, ``schema:position``
  the chapter number;
* an entry is linked to its tags: ``schema:about`` → themes, ``schema:contentLocation``
  → places, ``schema:mentions`` → people and folklore entities.  Where a
  person/folklore tag carries a per-occurrence note, that note is also attached
  via a ``schema:Role`` blank node (the entry keeps the plain ``schema:mentions``
  link too, so consumers that ignore roles lose nothing);
* themes and folklore entities are ``schema:DefinedTerm`` s in a
  ``schema:DefinedTermSet``; places are ``schema:Place`` (with ``schema:geo`` when
  geocoded); people are ``schema:Person``; the two Wikipedia-seeded prose fields
  map to ``schema:description`` (what it is) and ``schema:disambiguatingDescription``
  (what it does in the book);
* reflections are ``schema:CreativeWork`` s ``schema:isPartOf`` their entry;
* outer-ring war events are ``schema:Event`` s under a single ``id:world-war-ii``
  super-event;
* one ``schema:Dataset`` node describes the export itself.
"""

from datetime import date

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from . import models

SITE = "https://naples44.michelepasin.org"
ID = Namespace(f"{SITE}/id/")
SCHEMA = Namespace("https://schema.org/")

BOOK = ID["naples-44"]
WWII = ID["world-war-ii"]
DATASET = ID["dataset"]
THEME_SET = ID["themes"]
FOLKLORE_SET = ID["folklore"]


def _abs(path):
    """Absolute https URL for an on-site path like ``/entries/15/``."""
    return URIRef(f"{SITE}{path}")


def entry_uri(pk):
    return ID[f"entry/{pk}"]


def theme_uri(slug):
    return ID[f"theme/{slug}"]


def place_uri(slug):
    return ID[f"place/{slug}"]


def person_uri(slug):
    return ID[f"person/{slug}"]


def folklore_uri(slug):
    return ID[f"folklore/{slug}"]


def _lit_en(value):
    return Literal(value, lang="en")


def _add_prose(g, subject, description, book_role):
    """description → schema:description; book_role → schema:disambiguatingDescription."""
    if description:
        g.add((subject, SCHEMA.description, _lit_en(description.strip())))
    if book_role:
        g.add((subject, SCHEMA.disambiguatingDescription, _lit_en(book_role.strip())))


def build_graph():
    g = Graph()
    g.bind("schema", SCHEMA)
    g.bind("id", ID)
    # per-type prefixes so the Turtle reads as entry:1, place:salerno, …
    for prefix in ("entry", "theme", "place", "person", "folklore", "reflection", "event"):
        g.bind(prefix, Namespace(f"{SITE}/id/{prefix}/"))

    _add_book(g)
    _add_dataset(g)
    _add_themes(g)
    _add_places(g)
    _add_people(g)
    _add_folklore(g)
    _add_entries(g)
    _add_events(g)

    return g


def _add_book(g):
    entry_dates = list(models.Entry.objects.values_list("date", flat=True))
    coverage = f"{min(entry_dates).isoformat()}/{max(entry_dates).isoformat()}"

    g.add((BOOK, RDF.type, SCHEMA.Book))
    g.add((BOOK, SCHEMA.name, Literal("Naples '44")))
    g.add((BOOK, SCHEMA.author, Literal("Norman Lewis")))
    g.add((BOOK, SCHEMA.datePublished, Literal("1978", datatype=XSD.gYear)))
    g.add((BOOK, SCHEMA.inLanguage, Literal("en")))
    g.add((BOOK, SCHEMA.genre, Literal("wartime diary")))
    g.add((BOOK, SCHEMA.about, Literal("Naples under Allied occupation, 1943–1944")))
    g.add((BOOK, SCHEMA.temporalCoverage, Literal(coverage)))
    g.add((BOOK, SCHEMA.contentLocation, Literal("Naples, Italy")))
    g.add((BOOK, SCHEMA.url, _abs("/")))


def _add_dataset(g):
    creator = BNode()
    g.add((creator, RDF.type, SCHEMA.Person))
    g.add((creator, SCHEMA.name, Literal("Michele Pasin")))
    g.add((creator, SCHEMA.url, URIRef("https://www.michelepasin.org")))

    g.add((DATASET, RDF.type, SCHEMA.Dataset))
    g.add((DATASET, SCHEMA.name, Literal("Naples '44 — a structured reading")))
    g.add((DATASET, SCHEMA.description, _lit_en(
        "A hand-built dataset of Norman Lewis's memoir Naples '44: its 108 dated "
        "diary entries, each with a paraphrased summary and tagged by theme, "
        "place, person and folklore motif, plus 20 broader events of the war."
    )))
    g.add((DATASET, SCHEMA.creator, creator))
    g.add((DATASET, SCHEMA.about, BOOK))
    g.add((DATASET, SCHEMA.isBasedOn, BOOK))
    g.add((DATASET, SCHEMA.url, _abs("/")))
    g.add((DATASET, SCHEMA.dateModified,
           Literal(date.today().isoformat(), datatype=XSD.date)))


def _add_themes(g):
    g.add((THEME_SET, RDF.type, SCHEMA.DefinedTermSet))
    g.add((THEME_SET, SCHEMA.name, Literal("Naples '44 themes")))
    for t in models.Theme.objects.all():
        uri = theme_uri(t.slug)
        g.add((uri, RDF.type, SCHEMA.DefinedTerm))
        g.add((uri, SCHEMA.name, Literal(t.label)))
        if t.description:
            g.add((uri, SCHEMA.description, _lit_en(t.description)))
        g.add((uri, SCHEMA.inDefinedTermSet, THEME_SET))
        g.add((uri, SCHEMA.url, _abs(t.get_absolute_url())))


def _add_places(g):
    for p in models.Place.objects.all():
        uri = place_uri(p.slug)
        g.add((uri, RDF.type, SCHEMA.Place))
        g.add((uri, SCHEMA.name, Literal(p.name)))
        g.add((uri, SCHEMA.additionalType, Literal(p.get_place_type_display())))
        _add_prose(g, uri, p.description, p.book_role)
        if p.has_coords:
            geo = BNode()
            g.add((geo, RDF.type, SCHEMA.GeoCoordinates))
            g.add((geo, SCHEMA.latitude, Literal(repr(p.latitude), datatype=XSD.decimal)))
            g.add((geo, SCHEMA.longitude, Literal(repr(p.longitude), datatype=XSD.decimal)))
            g.add((uri, SCHEMA.geo, geo))
        if p.wikipedia_url:
            g.add((uri, SCHEMA.sameAs, URIRef(p.wikipedia_url)))
        g.add((uri, SCHEMA.url, _abs(p.get_absolute_url())))


def _add_people(g):
    for person in models.Person.objects.all():
        uri = person_uri(person.slug)
        g.add((uri, RDF.type, SCHEMA.Person))
        g.add((uri, SCHEMA.name, Literal(person.name)))
        g.add((uri, SCHEMA.additionalType, Literal(person.get_person_type_display())))
        _add_prose(g, uri, person.description, person.book_role)
        if person.wikipedia_url:
            g.add((uri, SCHEMA.sameAs, URIRef(person.wikipedia_url)))
        g.add((uri, SCHEMA.url, _abs(person.get_absolute_url())))


def _add_folklore(g):
    g.add((FOLKLORE_SET, RDF.type, SCHEMA.DefinedTermSet))
    g.add((FOLKLORE_SET, SCHEMA.name, Literal("Naples '44 saints, feasts and folklore")))
    for f in models.FolkloreEntity.objects.all():
        uri = folklore_uri(f.slug)
        g.add((uri, RDF.type, SCHEMA.DefinedTerm))
        g.add((uri, SCHEMA.name, Literal(f.name)))
        _add_prose(g, uri, f.description, f.book_role)
        if f.wikipedia_url:
            g.add((uri, SCHEMA.sameAs, URIRef(f.wikipedia_url)))
        g.add((uri, SCHEMA.inDefinedTermSet, FOLKLORE_SET))
        g.add((uri, SCHEMA.url, _abs(f.get_absolute_url())))


def _add_entries(g):
    entries = (
        models.Entry.objects.all()
        .prefetch_related(
            "themes", "places", "reflections",
            "entryperson_set__person", "entryfolklore_set__folklore",
        )
        .order_by("date", "id")
    )
    for e in entries:
        uri = entry_uri(e.id)
        g.add((uri, RDF.type, SCHEMA.Chapter))
        g.add((uri, SCHEMA.name, Literal(f"{e.date_label}, {e.year}")))
        g.add((uri, SCHEMA.isPartOf, BOOK))
        g.add((uri, SCHEMA.position, Literal(e.chapter, datatype=XSD.integer)))
        g.add((uri, SCHEMA.dateCreated, Literal(e.date.isoformat(), datatype=XSD.date)))
        g.add((uri, SCHEMA.abstract, _lit_en(e.summary)))
        g.add((uri, SCHEMA.url, _abs(e.get_absolute_url())))

        for t in e.themes.all():
            g.add((uri, SCHEMA.about, theme_uri(t.slug)))
        for p in e.places.all():
            g.add((uri, SCHEMA.contentLocation, place_uri(p.slug)))
        for ep in e.entryperson_set.all():
            target = person_uri(ep.person.slug)
            g.add((uri, SCHEMA.mentions, target))
            _add_occurrence_note(g, uri, target, ep.note)
        for ef in e.entryfolklore_set.all():
            target = folklore_uri(ef.folklore.slug)
            g.add((uri, SCHEMA.mentions, target))
            _add_occurrence_note(g, uri, target, ef.note)

        for r in e.reflections.all():
            r_uri = ID[f"reflection/{r.pk}"]
            g.add((r_uri, RDF.type, SCHEMA.CreativeWork))
            g.add((r_uri, SCHEMA.name, Literal(r.title)))
            g.add((r_uri, SCHEMA.text, _lit_en(r.note)))
            g.add((r_uri, SCHEMA.isPartOf, uri))
            g.add((uri, SCHEMA.hasPart, r_uri))


def _add_occurrence_note(g, entry, target, note):
    """The hand-written per-entry context for a person / folklore tag."""
    if not note:
        return
    role = BNode()
    g.add((role, RDF.type, SCHEMA.Role))
    g.add((role, SCHEMA.description, _lit_en(note)))
    g.add((role, SCHEMA.mentions, target))
    g.add((entry, SCHEMA.mentions, role))


def _add_events(g):
    g.add((WWII, RDF.type, SCHEMA.Event))
    g.add((WWII, SCHEMA.name, Literal("Second World War")))
    g.add((WWII, SCHEMA.alternateName, Literal("World War II")))

    for ev in models.OuterRingEvent.objects.all():
        uri = ID[f"event/{ev.pk}"]
        g.add((uri, RDF.type, SCHEMA.Event))
        g.add((uri, SCHEMA.name, Literal(ev.title)))
        g.add((uri, SCHEMA.startDate, Literal(ev.date.isoformat(), datatype=XSD.date)))
        g.add((uri, SCHEMA.additionalType, Literal(ev.get_category_display())))
        if ev.note:
            g.add((uri, SCHEMA.description, _lit_en(ev.note)))
        if ev.link:
            g.add((uri, SCHEMA.sameAs, URIRef(ev.link)))
        g.add((uri, SCHEMA.superEvent, WWII))
