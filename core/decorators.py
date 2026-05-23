"""
Decorators for GroupSathi views.
"""

from functools import wraps
from django.shortcuts import redirect


def login_required_custom(view_func):
    """Custom login required decorator using session-based auth."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
