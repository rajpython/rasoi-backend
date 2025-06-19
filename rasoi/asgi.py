"""
ASGI config for LittleLemon project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rasoi.settings")


from django.core.asgi import get_asgi_application
application = get_asgi_application()
