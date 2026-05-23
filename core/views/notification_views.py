"""
Notification/Alert views for GroupSathi.
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from bson import ObjectId
from core.decorators import login_required_custom
from core.db import get_collection


@login_required_custom
def alerts_view(request):
    """Show all notifications for the user."""
    user_id = request.session['user_id']
    notifications = get_collection('notifications')
    all_notifs = list(notifications.find({'user_id': user_id}).sort('created_at', -1).limit(50))
    unread = notifications.count_documents({'user_id': user_id, 'is_read': False})
    return render(request, 'notifications/alerts.html', {
        'notifications': all_notifs, 'unread_count': unread,
    })


@login_required_custom
def mark_read_view(request, notif_id):
    """Mark a notification as read."""
    notifications = get_collection('notifications')
    notifications.update_one(
        {'_id': ObjectId(notif_id), 'user_id': request.session['user_id']},
        {'$set': {'is_read': True}}
    )
    return redirect('alerts')


@login_required_custom
def mark_all_read_view(request):
    """Mark all notifications as read."""
    notifications = get_collection('notifications')
    notifications.update_many(
        {'user_id': request.session['user_id'], 'is_read': False},
        {'$set': {'is_read': True}}
    )
    messages.success(request, 'All notifications marked as read.')
    return redirect('alerts')


@login_required_custom
def delete_notification_view(request, notif_id):
    """Delete a single notification."""
    notifications = get_collection('notifications')
    notifications.delete_one(
        {'_id': ObjectId(notif_id), 'user_id': request.session['user_id']}
    )
    messages.success(request, 'Notification deleted successfully!')
    return redirect('alerts')


@login_required_custom
def delete_all_notifications_view(request):
    """Delete all notifications for the user."""
    notifications = get_collection('notifications')
    notifications.delete_many(
        {'user_id': request.session['user_id']}
    )
    messages.success(request, 'All notifications deleted successfully!')
    return redirect('alerts')
