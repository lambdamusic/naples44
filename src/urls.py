from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Administration"
admin.site.site_title = "naples44"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("naples44.urls")),
]
