"""
Middleware for GroupSathi.
"""

from django.shortcuts import redirect
from django.urls import reverse
from core.utils import is_profile_complete


# URLs that don't require profile completion
EXEMPT_URLS = [
    '/auth/login/',
    '/auth/register/',
    '/auth/logout/',
    '/auth/forgot-pin/',
    '/profile/complete/',
    '/static/',
    '/media/',
    '/download/app/',
    '/api/auth/check/',
]


class ProfileCompletionMiddleware:
    """Redirect users to profile completion if profile is incomplete."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.session.get('user_id'):
            path = request.path
            
            # Allow root landing page exactly
            is_exempt = (path == '/')
            
            # Check if path starts with any of the exempt prefixes
            if not is_exempt:
                is_exempt = any(path.startswith(url) for url in EXEMPT_URLS)

            if not is_exempt:
                user_id = request.session['user_id']
                if not is_profile_complete(user_id):
                    return redirect('profile_complete')

        response = self.get_response(request)
        return response
