"""
APK Download view for GroupSathi.
"""

import os
from django.http import FileResponse, Http404
from django.conf import settings


def download_apk_view(request):
    """Serve the GroupSathi APK file as a download."""
    apk_path = os.path.join(settings.STATICFILES_DIRS[0], 'apk', 'GroupSathi.apk')

    if not os.path.exists(apk_path):
        raise Http404("APK file not found. Please contact the administrator.")

    response = FileResponse(
        open(apk_path, 'rb'),
        as_attachment=True,
        filename='GroupSathi.apk',
        content_type='application/vnd.android.package-archive'
    )
    return response
