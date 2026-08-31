from django.urls import path

from . import views

app_name = "naples44"

urlpatterns = [
    path("", views.index, name="index"),
    path("timeline/", views.timeline, name="timeline"),
    path("entries/<int:entry_id>/", views.entry_detail, name="entry"),
    path("places/<slug:slug>/", views.place_detail, name="place"),
    path("people/<slug:slug>/", views.person_detail, name="person"),
    path("folklore/<slug:slug>/", views.folklore_detail, name="folklore"),
    path("themes/<slug:slug>/", views.theme_detail, name="theme"),
]
