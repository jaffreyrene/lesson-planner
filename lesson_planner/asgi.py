"""
ASGI config for lesson_planner project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lesson_planner.settings')

application = get_asgi_application()

# touched on 2025-06-13T18:49:54.502067Z
# touched on 2025-06-13T18:50:26.026901Z
# touched on 2025-06-13T18:51:02.881928Z
# touched on 2025-06-13T18:51:19.342186Z