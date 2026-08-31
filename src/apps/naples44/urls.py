from django.urls import path

from . import views

app_name = "naples44"

urlpatterns = [
    path("", views.index, name="index"),
    path("timeline/", views.timeline, name="timeline"),
    path("entries/<int:entry_id>/", views.entry_detail, name="entry"),
]
