"""
WSGI config for groupsathi project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupsathi.settings')
application = get_wsgi_application()
