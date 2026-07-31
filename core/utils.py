"""
Utility functions for GroupSathi.
"""

import random
import string
from datetime import datetime
from bson import ObjectId
from core.db import get_collection


def generate_member_id():
    """Generate a unique 5-digit numeric Member ID."""
    profiles = get_collection('profiles')
    while True:
        member_id = str(random.randint(10000, 99999))
        if not profiles.find_one({'member_id': member_id}):
            return member_id


def generate_group_id():
    """Generate a unique numeric Group ID."""
    groups = get_collection('groups')
    while True:
        group_id = str(random.randint(100000, 999999))
        if not groups.find_one({'group_id': group_id}):
            return group_id


def get_user_profile(user_id):
    """Get user profile by user_id."""
    profiles = get_collection('profiles')
    return profiles.find_one({'user_id': user_id})


def get_user_by_id(user_id):
    """Get user by ObjectId string."""
    users = get_collection('users')
    return users.find_one({'_id': ObjectId(user_id)})


def is_profile_complete(user_id):
    """Check if user profile is complete."""
    profile = get_user_profile(user_id)
    if not profile:
        return False
    required_fields = ['full_name', 'gender', 'address', 'pin_code']
    for field in required_fields:
        if not profile.get(field):
            return False
    return True


def create_notification(user_id, title, message, notification_type='info', group_id=None, **kwargs):
    """Create a notification for a user."""
    notifications = get_collection('notifications')
    notification = {
        'user_id': user_id,
        'title': title,
        'message': message,
        'type': notification_type,  # info, success, warning, danger
        'group_id': group_id,
        'is_read': False,
        'created_at': datetime.now(),
    }
    notification.update(kwargs)
    notifications.insert_one(notification)


def get_unread_notification_count(user_id):
    """Get count of unread notifications."""
    notifications = get_collection('notifications')
    return notifications.count_documents({'user_id': user_id, 'is_read': False})


def calculate_simple_interest(principal, rate, time_months):
    """Calculate simple interest where rate is % per month and time is in months."""
    interest = (principal * rate * time_months) / 100
    return round(interest, 2)


def calculate_emi(principal, rate, tenure_months):
    """Calculate EMI using flat rate method."""
    if rate == 0:
        return round(principal / tenure_months, 2) if tenure_months > 0 else 0
    monthly_rate = rate / (12 * 100)
    emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (((1 + monthly_rate) ** tenure_months) - 1)
    return round(emi, 2)


def get_group_balance(group_id):
    """Calculate available balance for a group by summing all transaction amounts."""
    transactions = get_collection('transactions')
    pipeline = [
        {'$match': {'group_id': group_id}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    result = list(transactions.aggregate(pipeline))
    return round(result[0]['total'] if result else 0, 2)


def get_maintenance_status():
    """Get the current maintenance mode settings and auto-disable if end time is reached."""
    settings_col = get_collection('system_settings')
    maintenance = settings_col.find_one({'_id': 'maintenance_mode'})
    
    if maintenance and maintenance.get('is_active'):
        end_time_str = maintenance.get('end_time')
        if end_time_str:
            try:
                # Parse datetime-local string (e.g. "2026-07-31T18:00")
                end_time = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M")
                if datetime.now() >= end_time:
                    # Auto-disable
                    settings_col.update_one(
                        {'_id': 'maintenance_mode'},
                        {'$set': {'is_active': False}}
                    )
                    maintenance['is_active'] = False
            except ValueError:
                pass
                
    return maintenance if maintenance else {'is_active': False, 'message': ''}


def get_member_role(group_id, user_id):
    """Get member role in a group."""
    members = get_collection('group_members')
    member = members.find_one({'group_id': group_id, 'user_id': user_id})
    if member:
        return member.get('role', 'member')
    return None


def format_currency(amount):
    """Format amount as Indian currency."""
    return f"₹{amount:,.2f}"


def notify_group_members(group_id, title, message, notification_type='info', exclude_user_id=None):
    """Notify all active members of a group."""
    gm = get_collection('group_members')
    query = {'group_id': group_id, 'status': 'active'}
    if exclude_user_id:
        query['user_id'] = {'$ne': exclude_user_id}
    members = list(gm.find(query))
    for m in members:
        create_notification(m['user_id'], title, message, notification_type, group_id)


def send_automated_reminders_for_group(group, target_date=None):
    """
    Check if target_date (defaults to today) is 24 hours before the group's EMI date.
    If so, send the automated EMI and Loan reminders to members.
    Utilizes a log collection to ensure reminders are sent only once per group per month.
    """
    from datetime import timedelta
    if target_date is None:
        target_date = datetime.now()
        
    group_id = group['group_id']
    emi_date = group.get('emi_date', 1)
    
    # 24 hours before means tomorrow's day of month is the EMI date
    tomorrow = target_date + timedelta(days=1)
    if tomorrow.day != emi_date:
        return False
        
    # Check if already sent for this month and year
    reminder_logs = get_collection('reminder_logs')
    log_query = {
        'group_id': group_id,
        'reminder_type': '24h_before',
        'year': target_date.year,
        'month': target_date.month
    }
    
    if reminder_logs.find_one(log_query):
        # Already sent
        return False
        
    # Fetch all active group members
    gm = get_collection('group_members')
    active_members = list(gm.find({'group_id': group_id, 'status': 'active'}))
    
    loans = get_collection('loans')
    
    for member in active_members:
        user_id = member['user_id']
        
        # 1. Send general EMI reminder
        create_notification(
            user_id=user_id,
            title='Upcoming EMI Reminder',
            message=f"Reminder: The monthly EMI of {format_currency(group.get('emi_amount', 0.0))} for group {group['name']} is due tomorrow (Day {emi_date}).",
            notification_type='info',
            group_id=group_id
        )
        
        # 2. Check if they have an active loan and interest due
        active_loan = loans.find_one({
            'group_id': group_id,
            'user_id': user_id,
            'status': {'$in': ['approved', 'active']},
            'remaining_amount': {'$gt': 0}
        })
        
        if active_loan:
            remaining_principal = active_loan.get('remaining_amount', 0.0)
            
            create_notification(
                user_id=user_id,
                title='Loan Payment Reminder',
                message=f"Loan Reminder: You have an active loan with a remaining principal of {format_currency(remaining_principal)} in group {group['name']}. Please ensure you make loan and interest payments on time.",
                notification_type='warning',
                group_id=group_id
            )
            
    # Insert log to prevent duplication
    log_data = log_query.copy()
    log_data['created_at'] = datetime.now()
    reminder_logs.insert_one(log_data)
    return True


def check_and_send_all_active_reminders(target_date=None):
    """Check and send automated reminders for all active groups."""
    groups_col = get_collection('groups')
    active_groups = list(groups_col.find({'is_active': True}))
    for group in active_groups:
        send_automated_reminders_for_group(group, target_date)


