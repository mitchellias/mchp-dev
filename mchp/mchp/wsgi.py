"""
WSGI config for mchp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mchp.settings")

max_bg_images = os.popen('ls lib/static/lib/img/bgimages/bg-*.jpeg | wc -l').read().strip()
os.environ.setdefault("MAX_BG_IMAGES", max_bg_images)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
