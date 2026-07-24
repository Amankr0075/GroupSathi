"""
Dashboard view for GroupSathi.
"""

from django.shortcuts import render
from django.core.cache import cache
from core.decorators import login_required_custom
from core.db import get_collection
from core.utils import get_unread_notification_count, check_and_send_all_active_reminders


@login_required_custom
def dashboard_view(request):
    """Render the main dashboard with card-based navigation."""
    # Automatically check and send any scheduled automated reminders
    check_and_send_all_active_reminders()

    user_id = request.session['user_id']

    # Get user's groups count
    groups_count = cache.get(f'groups_count_{user_id}')
    if groups_count is None:
        group_members = get_collection('group_members')
        groups_count = group_members.count_documents({'user_id': user_id, 'status': 'active'})
        cache.set(f'groups_count_{user_id}', groups_count, 300)

    # Get pending notifications
    unread_count = cache.get(f'unread_count_{user_id}')
    if unread_count is None:
        unread_count = get_unread_notification_count(user_id)
        cache.set(f'unread_count_{user_id}', unread_count, 60)

    # Get active loans count
    active_loans = cache.get(f'active_loans_{user_id}')
    if active_loans is None:
        loans = get_collection('loans')
        active_loans = loans.count_documents({'user_id': user_id, 'status': {'$in': ['approved', 'active']}})
        cache.set(f'active_loans_{user_id}', active_loans, 300)
        
    # Get active ticket status
    active_ticket_status = cache.get(f'active_ticket_status_{user_id}')
    if active_ticket_status is None:
        tickets = get_collection('tickets')
        latest_ticket = tickets.find_one({'user_id': user_id}, sort=[('updated_at', -1)])
        active_ticket_status = latest_ticket.get('status') if latest_ticket else ''
        cache.set(f'active_ticket_status_{user_id}', active_ticket_status, 60)

    # Dashboard items - sorted alphabetically
    dashboard_items = [
        {'name': 'Alert', 'icon': 'bi-bell-fill', 'url': 'alerts', 'color': '#FF6B6B', 'badge': unread_count},
        {'name': 'Calculator', 'icon': 'bi-calculator-fill', 'url': 'calculator', 'color': '#FF8C00'},
        {'name': 'Create Group', 'icon': 'bi-plus-circle-fill', 'url': 'create_group', 'color': '#45B7D1'},
        {'name': 'Guide', 'icon': 'bi-journal-bookmark-fill', 'url': 'help', 'color': '#20B2AA'},
        {'name': 'Join Group', 'icon': 'bi-box-arrow-in-right', 'url': 'join_group', 'color': '#FFEAA7'},
        {'name': 'Loan', 'icon': 'bi-cash-stack', 'url': 'loan_list', 'color': '#DDA0DD'},
        {'name': 'My Groups', 'icon': 'bi-people-fill', 'url': 'my_groups', 'color': '#98D8C8'},
        {'name': 'Profile', 'icon': 'bi-person-circle', 'url': 'profile_view', 'color': '#F7DC6F'},
        {'name': 'Report', 'icon': 'bi-file-earmark-bar-graph-fill', 'url': 'reports', 'color': '#BB8FCE'},
        {'name': 'Search Member', 'icon': 'bi-search', 'url': 'search_member', 'color': '#85C1E9'},
        {'name': 'Settings', 'icon': 'bi-gear-fill', 'url': 'settings', 'color': '#AEB6BF'},
    ]

    context = {
        'dashboard_items': dashboard_items,
        'groups_count': groups_count,
        'active_loans': active_loans,
        'active_ticket_status': active_ticket_status,
    }
    return render(request, 'dashboard/dashboard.html', context)
