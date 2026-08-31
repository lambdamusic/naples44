"""
WSGI config — used only for local `runserver` / `runserver_plus`.
This project has no production Django deployment (see README).
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

application = get_wsgi_application()
