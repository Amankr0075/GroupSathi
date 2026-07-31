"""
Middleware for GroupSathi.
"""

from django.shortcuts import redirect
from django.urls import reverse
from core.utils import is_profile_complete


class XForwardedForMiddleware:
    """
    Set REMOTE_ADDR to the client's real IP if X-Forwarded-For is present.
    Essential for django-ratelimit and other IP-based features behind a proxy.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, the first one is the client.
            ip = x_forwarded_for.split(',')[0].strip()
            request.META['REMOTE_ADDR'] = ip
        return self.get_response(request)


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


class MaintenanceModeMiddleware:
    """Block non-admin/staff users when maintenance is active."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        
        # Paths that are ALWAYS accessible even during maintenance
        ALLOWED_PATHS = [
            '/',
            '/auth/login/',
            '/auth/register/',
            '/auth/staff-login/',
            '/auth/logout/',
            '/static/',
            '/media/',
            '/download/app/',
        ]

        # Check if path is in allowed paths (prefix matching for static/media)
        is_allowed_path = any(path.startswith(p) for p in ['/static/', '/media/', '/download/app/']) or path in ALLOWED_PATHS

        from core.db import get_collection
        from core.utils import get_maintenance_status
        from bson import ObjectId
        users_col = get_collection('users')
        
        maintenance = get_maintenance_status()
        if maintenance and maintenance.get('is_active'):
            user_id = request.session.get('user_id')
            is_authorized = False
            
            if user_id:
                user = users_col.find_one({'_id': ObjectId(user_id)})
                if user:
                    # Allow if admin OR if their ID is in allowed_staff_ids
                    is_admin = user.get('is_admin', False)
                    allowed_staff = maintenance.get('allowed_staff_ids', [])
                    if is_admin or str(user_id) in allowed_staff:
                        is_authorized = True

            # If user is not authorized and trying to access a protected route
            if not is_authorized and not is_allowed_path:
                from django.shortcuts import render
                # Log them out if they had a session
                if 'user_id' in request.session:
                    request.session.flush()
                
                return render(request, 'maintenance.html', {
                    'message': maintenance.get('message', 'System is under maintenance.'),
                    'end_time': maintenance.get('end_time', '')
                }, status=503)

        return self.get_response(request)
