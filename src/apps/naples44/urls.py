from django.urls import path

from . import views

app_name = "naples44"

urlpatterns = [
    path("", views.index, name="index"),
    path("timeline/", views.timeline, name="timeline"),
    path("entries/<int:entry_id>/", views.entry_detail, name="entry"),

    path("places/", views.place_list, name="place_list"),
    path("places/<slug:slug>/", views.place_detail, name="place"),
    path("people/", views.person_list, name="person_list"),
    path("people/<slug:slug>/", views.person_detail, name="person"),
    path("folklore/", views.folklore_list, name="folklore_list"),
    path("folklore/<slug:slug>/", views.folklore_detail, name="folklore"),
    path("themes/", views.theme_list, name="theme_list"),
    path("themes/<slug:slug>/", views.theme_detail, name="theme"),
]
