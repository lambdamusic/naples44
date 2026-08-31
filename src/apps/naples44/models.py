"""
Content model for the Naples '44 radial-timeline site.

The dataset was hand-built while reading Norman Lewis's memoir and seeded once via
`manage.py import_naples_data`. From then on the Django admin is the editor and
`tools/db-dump` (backups/django/dump.json) is the committed source of the data.
"""

from django.db import models
from django.urls import reverse
from django.utils.text import slugify


def unique_slug(model, value, pk=None):
    """A slugified `value` that doesn't collide with an existing row of `model`."""
    base = slugify(value)[:130] or "item"
    slug = base
    n = 2
    qs = model.objects.all()
    if pk is not None:
        qs = qs.exclude(pk=pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Theme(models.Model):
    """One of the 11 controlled-vocabulary themes tagged on entries."""

    slug = models.SlugField(primary_key=True, max_length=40)
    label = models.CharField(max_length=60)
    description = models.CharField(max_length=300)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "slug"]

    def __str__(self):
        return self.label

    @property
    def name(self):
        return self.label

    def get_absolute_url(self):
        return reverse("naples44:theme", args=[self.slug])


class Place(models.Model):
    PLACE_TYPES = [
        ("street", "Street"),
        ("piazza", "Piazza"),
        ("landmark", "Landmark"),
        ("district", "District"),
        ("religious_site", "Religious site"),
        ("town", "Town"),
        ("region", "Region"),
        ("natural_feature", "Natural feature"),
    ]

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    place_type = models.CharField(max_length=20, choices=PLACE_TYPES)
    description = models.TextField(blank=True, help_text="Shown on the place's page. Optional.")
    wikipedia_url = models.URLField(blank=True, help_text="Further reading — linked only from the place's own page.")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    geocode_source = models.CharField(
        max_length=20, blank=True,
        help_text="Where latitude/longitude came from (wikipedia, nominatim, manual).",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Place, self.name, self.pk)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("naples44:place", args=[self.slug])

    @property
    def has_coords(self):
        return self.latitude is not None and self.longitude is not None


class Person(models.Model):
    PERSON_TYPES = [
        ("camorrista_bandit", "Camorrista / bandit"),
        ("police_official", "Police official"),
        ("informant_contact", "Informant / contact"),
        ("companion", "Companion"),
        ("aristocrat", "Aristocrat"),
        ("allied_colleague", "Allied colleague"),
        ("civilian_friend", "Civilian friend"),
        ("notable_civilian", "Notable civilian"),
    ]

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    person_type = models.CharField(max_length=20, choices=PERSON_TYPES)
    description = models.TextField(blank=True, help_text="Shown on the person's page. Optional.")
    wikipedia_url = models.URLField(blank=True, help_text="Further reading — linked only from the person's own page.")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "people"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Person, self.name, self.pk)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("naples44:person", args=[self.slug])


class FolkloreEntity(models.Model):
    """A named saint, feast, superstition or folk custom recurring in the book."""

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Shown on the entity's page. Optional.")
    wikipedia_url = models.URLField(blank=True, help_text="Further reading — linked only from the entity's own page.")

    class Meta:
        ordering = ["name"]
        verbose_name = "folklore entity"
        verbose_name_plural = "folklore entities"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(FolkloreEntity, self.name, self.pk)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("naples44:folklore", args=[self.slug])


class Entry(models.Model):
    """One dated diary entry from the book (108 total). PK = the source id."""

    id = models.PositiveSmallIntegerField(primary_key=True)
    chapter = models.PositiveSmallIntegerField(
        help_text="Chapter number in Mikele's reading app (usually id + 1)."
    )
    year = models.PositiveSmallIntegerField()
    date_label = models.CharField(
        max_length=40, help_text='As printed in the book, e.g. "September 8" or "May 7 (i)".'
    )
    date = models.DateField(help_text="Resolved calendar date, used for the timeline angle.")
    summary = models.TextField(help_text="Paraphrased summary — never a verbatim quote.")

    themes = models.ManyToManyField(Theme, blank=True, related_name="entries")
    places = models.ManyToManyField(Place, blank=True, related_name="entries")
    people = models.ManyToManyField(
        Person, through="EntryPerson", blank=True, related_name="entries"
    )
    folklore = models.ManyToManyField(
        FolkloreEntity, through="EntryFolklore", blank=True, related_name="entries"
    )

    class Meta:
        ordering = ["date", "id"]
        verbose_name_plural = "entries"

    def __str__(self):
        return f"#{self.id} — {self.date_label} {self.year}"

    def get_absolute_url(self):
        return reverse("naples44:entry", args=[self.id])


class EntryPerson(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    note = models.CharField(max_length=400, blank=True, help_text="Context for this entry.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["entry", "person"], name="uniq_entry_person")
        ]

    def __str__(self):
        return f"{self.person} in {self.entry_id}"


class EntryFolklore(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE)
    folklore = models.ForeignKey(FolkloreEntity, on_delete=models.CASCADE)
    note = models.CharField(max_length=500, blank=True, help_text="Context for this entry.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["entry", "folklore"], name="uniq_entry_folklore")
        ]

    def __str__(self):
        return f"{self.folklore} in {self.entry_id}"


class Reflection(models.Model):
    """A standout passage where Lewis steps back to make a broader observation."""

    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="reflections")
    title = models.CharField(max_length=120)
    note = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class OuterRingEvent(models.Model):
    """A broader WWII / Italian-campaign event for the timeline's outer ring."""

    CATEGORIES = [
        ("global", "Global"),
        ("italian_campaign", "Italian campaign"),
    ]

    date = models.DateField()
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    note = models.TextField()
    link = models.URLField(blank=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date.isoformat()} — {self.title}"
