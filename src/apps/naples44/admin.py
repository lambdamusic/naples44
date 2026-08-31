from django.contrib import admin

from . import models


class ReflectionInline(admin.StackedInline):
    model = models.Reflection
    extra = 0


class EntryPersonInline(admin.TabularInline):
    model = models.EntryPerson
    extra = 0
    autocomplete_fields = ["person"]


class EntryFolkloreInline(admin.TabularInline):
    model = models.EntryFolklore
    extra = 0
    autocomplete_fields = ["folklore"]


@admin.register(models.Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ["id", "date_label", "year", "chapter", "short_summary"]
    list_filter = ["year", "themes"]
    search_fields = ["summary", "date_label"]
    filter_horizontal = ["themes", "places"]
    inlines = [ReflectionInline, EntryPersonInline, EntryFolkloreInline]
    exclude = ["people", "folklore"]

    @admin.display(description="summary")
    def short_summary(self, obj):
        return obj.summary[:90] + ("…" if len(obj.summary) > 90 else "")


@admin.register(models.Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ["label", "slug", "order", "entry_count"]
    ordering = ["order"]

    @admin.display(description="entries")
    def entry_count(self, obj):
        return obj.entries.count()


@admin.register(models.Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ["name", "place_type", "has_desc", "has_link", "geo", "entry_count"]
    list_filter = ["place_type", "geocode_source"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(boolean=True, description="desc")
    def has_desc(self, obj):
        return bool(obj.description)

    @admin.display(description="geo")
    def geo(self, obj):
        return obj.geocode_source or ("—" if not obj.has_coords else "?")

    @admin.display(boolean=True, description="wiki")
    def has_link(self, obj):
        return bool(obj.wikipedia_url)

    @admin.display(description="entries")
    def entry_count(self, obj):
        return obj.entries.count()


@admin.register(models.Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["name", "person_type", "has_desc", "entry_count"]
    list_filter = ["person_type"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(boolean=True, description="desc")
    def has_desc(self, obj):
        return bool(obj.description)

    @admin.display(description="entries")
    def entry_count(self, obj):
        return obj.entries.count()


@admin.register(models.FolkloreEntity)
class FolkloreEntityAdmin(admin.ModelAdmin):
    list_display = ["name", "has_desc", "has_link", "entry_count"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(boolean=True, description="desc")
    def has_desc(self, obj):
        return bool(obj.description)

    @admin.display(boolean=True, description="wiki")
    def has_link(self, obj):
        return bool(obj.wikipedia_url)

    @admin.display(description="entries")
    def entry_count(self, obj):
        return obj.entries.count()


@admin.register(models.OuterRingEvent)
class OuterRingEventAdmin(admin.ModelAdmin):
    list_display = ["date", "title", "category"]
    list_filter = ["category"]
    search_fields = ["title", "note"]
