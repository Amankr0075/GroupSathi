"""
Context processors for GroupSathi.
"""

from core.db import get_collection
from core.utils import get_unread_notification_count


def user_context(request):
    """Add user data to template context."""
    context = {}
    user_id = request.session.get('user_id')
    if user_id:
        profiles = get_collection('profiles')
        users = get_collection('users')
        from bson import ObjectId
        user = users.find_one({'_id': ObjectId(user_id)})
        profile = profiles.find_one({'user_id': user_id})
        context['current_user'] = user
        context['current_profile'] = profile
        context['is_logged_in'] = True
    else:
        context['is_logged_in'] = False
    return context


def notification_context(request):
    """Add notification count to template context."""
    context = {'unread_count': 0}
    user_id = request.session.get('user_id')
    if user_id:
        context['unread_count'] = get_unread_notification_count(user_id)
    return context
