"""
Copy this file to local_settings.py (gitignored) and adjust as needed.
"""

import os
import django

SECRET_KEY = "CHANGE-ME-generate-a-real-secret-key"

DJANGO_ROOT = os.path.dirname(os.path.realpath(django.__file__))
# settings.py lives in src/, so the project root is one level up
SITE_ROOT = os.path.dirname(os.path.realpath(__file__)).rsplit("/", 1)[0]

ENVIRONMENT = "local"

print("Environment: %s" % ENVIRONMENT)

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Static files — sourced from src/static, collected into collectstatic/ for local use
STATIC_URL = "/media/static/"
STATIC_ROOT = os.path.join(SITE_ROOT, "collectstatic/naples44")
STATICFILES_DIRS = (os.path.join(SITE_ROOT, "src/static"),)

# sqlite always — see the init-django-static-site skill's METHODOLOGY.md for why.
# Portability comes from `tools/db-dump` (JSON fixtures in backups/django/),
# not from committing this file — db.sqlite3 stays gitignored.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(SITE_ROOT, "db.sqlite3"),
    }
}
