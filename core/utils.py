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


def calculate_settlement_plan(group_id):
    """
    Calculate the deterministic, single-pass final distribution plan for a group.
    """
    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})
    if not group:
        return None
        
    gm = get_collection('group_members')
    active_members = list(gm.find({'group_id': group_id, 'status': 'active'}))
    if not active_members:
        return None

    txns = get_collection('transactions')
    loans = get_collection('loans')
    if_col = get_collection('imposed_fines')
    profiles = get_collection('profiles')
    
    from core.utils import get_group_balance
    total_cash = get_group_balance(group_id)
    
    emi_amount = group.get('emi_amount', 0.0)
    now = datetime.now()
    
    member_plans = []
    total_group_contributions = 0.0
    
    # Calculate group profit (actually realized before settlement)
    # Profit = Collected Interest + Collected Fines
    pipeline_int = [
        {'$match': {'group_id': group_id, 'type': 'interest_payment'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    res_int = list(txns.aggregate(pipeline_int))
    collected_interest = res_int[0]['total'] if res_int else 0.0
    
    pipeline_fine = [
        {'$match': {'group_id': group_id, 'type': 'fine_payment'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    res_fine = list(txns.aggregate(pipeline_fine))
    collected_fines = res_fine[0]['total'] if res_fine else 0.0
    
    # We might also have other distributable income, but for now we'll stick to interest + fines
    group_profit = collected_interest + collected_fines
    
    # Step 1: Calculate contributions and find totals
    for m in active_members:
        user_id = m['user_id']
        joined_at = m.get('joined_at', now)
        
        # Calculate paid contributions (EMI payments)
        pipeline_emi = [
            {'$match': {'group_id': group_id, 'user_id': user_id, 'type': 'emi_payment'}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ]
        res_emi = list(txns.aggregate(pipeline_emi))
        paid_contribution = res_emi[0]['total'] if res_emi else 0.0
        
        total_group_contributions += paid_contribution
        
        # Calculate unpaid contribution based on months active
        months_active = (now.year - joined_at.year) * 12 + (now.month - joined_at.month)
        if months_active < 0:
            months_active = 0
            
        expected_contribution = months_active * emi_amount
        unpaid_contribution = max(0.0, expected_contribution - paid_contribution)
        
        p = profiles.find_one({'user_id': user_id})
        name = p.get('full_name', 'Unknown') if p else 'Unknown'
        
        member_plans.append({
            'user_id': user_id,
            'name': name,
            'role': m.get('role', 'member'),
            'paid_contribution': paid_contribution,
            'expected_contribution': expected_contribution,
            'unpaid_contribution': unpaid_contribution,
        })
        
    # Steps 2-7 for each member
    for plan in member_plans:
        user_id = plan['user_id']
        
        # Step 3: Profit Share
        if total_group_contributions > 0:
            profit_share = group_profit * (plan['paid_contribution'] / total_group_contributions)
        else:
            profit_share = group_profit / len(active_members) if active_members else 0.0
            
        # Step 4: Gross Settlement
        gross_settlement = plan['paid_contribution'] + profit_share
        
        # Calculate Outstanding Dues
        active_loans = list(loans.find({'group_id': group_id, 'user_id': user_id, 'status': {'$in': ['approved', 'active']}}))
        loan_principal_due = sum(l.get('remaining_amount', 0.0) for l in active_loans)
        
        # We don't have a reliable 'loan_interest_due' in DB yet, but if it exists we'd add it. 
        # Assuming remaining_amount represents total due for loan, or interest is handled separately. 
        # I'll add a 0 placeholder for now to match the algorithm steps.
        loan_interest_due = 0.0 
        
        unpaid_fines_list = list(if_col.find({'group_id': group_id, 'user_id': user_id, 'status': 'unpaid'}))
        fine_due = sum(f.get('amount', 0.0) for f in unpaid_fines_list)
        other_due = 0.0
        
        # Step 5: Total Deduction (Fixed Order: Principal, Interest, Unpaid EMI, Fines, Other)
        total_deduction = loan_principal_due + loan_interest_due + plan['unpaid_contribution'] + fine_due + other_due
        
        plan['profit_share'] = profit_share
        plan['gross_settlement'] = gross_settlement
        plan['loan_principal_due'] = loan_principal_due
        plan['loan_interest_due'] = loan_interest_due
        plan['fine_due'] = fine_due
        plan['other_due'] = other_due
        plan['total_deduction'] = total_deduction
        
        # Step 6 & 7: Final Amount & Remaining Due
        plan['final_payout'] = max(0.0, gross_settlement - total_deduction)
        plan['remaining_due'] = max(0.0, total_deduction - gross_settlement)
        
        # Step 8 & 9: Determine specifically what was recovered (for record keeping, NOT redistribution)
        available_for_deduction = gross_settlement
        
        recovered_loan_principal = min(available_for_deduction, loan_principal_due)
        available_for_deduction -= recovered_loan_principal
        
        recovered_loan_interest = min(available_for_deduction, loan_interest_due)
        available_for_deduction -= recovered_loan_interest
        
        recovered_unpaid_emi = min(available_for_deduction, plan['unpaid_contribution'])
        available_for_deduction -= recovered_unpaid_emi
        
        recovered_fines = min(available_for_deduction, fine_due)
        available_for_deduction -= recovered_fines
        
        recovered_other_dues = min(available_for_deduction, other_due)
        available_for_deduction -= recovered_other_dues
        
        plan['recovered_loan_principal'] = recovered_loan_principal
        plan['recovered_loan_interest'] = recovered_loan_interest
        plan['recovered_unpaid_emi'] = recovered_unpaid_emi
        plan['recovered_fines'] = recovered_fines
        plan['recovered_other_dues'] = recovered_other_dues

    total_final_payout = sum(p['final_payout'] for p in member_plans)
    
    return {
        'group_id': group_id,
        'total_cash': total_cash,
        'group_profit': group_profit,
        'total_group_contributions': total_group_contributions,
        'total_final_payout': total_final_payout,
        'member_plans': member_plans
    }
