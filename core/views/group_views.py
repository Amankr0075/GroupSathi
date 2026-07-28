"""
Group management views for GroupSathi.
"""

import os
import uuid
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from bson import ObjectId
from core.decorators import login_required_custom
from core.db import get_collection
from core.utils import (
    generate_group_id, get_user_profile,
    create_notification, get_member_role, get_group_balance,
    notify_group_members, check_and_send_all_active_reminders,
    format_currency
)
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit


def sync_to_waiver_history(req_id_or_obj):
    """Sync a fine waiver request document to the permanent 'fine_waiver_history' collection."""
    fwr = get_collection('fine_waiver_requests')
    fwh = get_collection('fine_waiver_history')
    if isinstance(req_id_or_obj, (str, ObjectId)):
        req = fwr.find_one({'_id': ObjectId(req_id_or_obj)})
    else:
        req = req_id_or_obj

    if req:
        req_id_str = str(req['_id'])
        history_entry = dict(req)
        history_entry['request_id'] = req_id_str
        if '_id' in history_entry:
            del history_entry['_id']
        fwh.update_one({'request_id': req_id_str}, {'$set': history_entry}, upsert=True)


def cleanup_old_waiver_requests():
    """Move waiver requests older than 7 days to history and delete them from active request pool."""
    fwr = get_collection('fine_waiver_requests')
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    old_requests = list(fwr.find({'created_at': {'$lt': seven_days_ago}}))
    for req in old_requests:
        sync_to_waiver_history(req)
        
    fwr.delete_many({'created_at': {'$lt': seven_days_ago}})


@login_required_custom
@ratelimit(key='ip', rate='5/m', block=True)
def create_group_view(request):
    """Create a new SHG group."""
    user_id = request.session['user_id']
    if request.method == 'POST':
        name = request.POST.get('group_name', '').strip()
        emi_amount = request.POST.get('emi_amount', '0').strip()
        interest_rate = request.POST.get('interest_rate', '0').strip()
        emi_date = request.POST.get('emi_date', '1').strip()
        fine_amount = request.POST.get('fine_amount', '0').strip()

        if not name:
            messages.error(request, 'Group name is required.')
            return render(request, 'groups/create_group.html')

        logo_path = ''
        if 'group_logo' in request.FILES:
            logo = request.FILES['group_logo']
            ext = os.path.splitext(logo.name)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'groups')
            os.makedirs(upload_dir, exist_ok=True)
            with open(os.path.join(upload_dir, filename), 'wb+') as f:
                for chunk in logo.chunks():
                    f.write(chunk)
            logo_path = f"groups/{filename}"

        group_id = generate_group_id()
        groups = get_collection('groups')
        groups.insert_one({
            'group_id': group_id, 'name': name, 'logo': logo_path,
            'emi_amount': float(emi_amount), 'interest_rate': float(interest_rate),
            'emi_date': int(emi_date), 'fine_amount': float(fine_amount),
            'created_by': user_id, 'created_at': datetime.now(),
            'updated_at': datetime.now(), 'is_active': True,
        })

        gm = get_collection('group_members')
        gm.insert_one({
            'group_id': group_id, 'user_id': user_id,
            'role': 'leader', 'status': 'active',
            'joined_at': datetime.now(),
        })

        cache.delete(f'my_groups_{user_id}')
        cache.delete(f'groups_count_{user_id}')

        messages.success(request, f'Group created! Group ID: {group_id}')
        return redirect('my_groups')

    return render(request, 'groups/create_group.html')


@login_required_custom
def edit_group_view(request, group_id):
    """Edit group details (leader only)."""
    user_id = request.session['user_id']
    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})

    if not group:
        messages.error(request, 'Group not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})

    if not membership or membership.get('role') != 'leader':
        messages.error(request, 'Only the group leader can edit group settings.')
        return redirect('group_detail', group_id=group_id)

    if request.method == 'POST':
        name = request.POST.get('group_name', '').strip()
        emi_amount = request.POST.get('emi_amount', '0').strip()
        interest_rate = request.POST.get('interest_rate', '0').strip()
        emi_date = request.POST.get('emi_date', '1').strip()
        fine_amount = request.POST.get('fine_amount', '0').strip()

        if not name:
            messages.error(request, 'Group name is required.')
            return render(request, 'groups/edit_group.html', {'group': group})

        update_data = {
            'name': name,
            'emi_amount': float(emi_amount),
            'interest_rate': float(interest_rate),
            'emi_date': int(emi_date),
            'fine_amount': float(fine_amount),
            'updated_at': datetime.now()
        }

        if 'group_logo' in request.FILES:
            logo = request.FILES['group_logo']
            ext = os.path.splitext(logo.name)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'groups')
            os.makedirs(upload_dir, exist_ok=True)
            with open(os.path.join(upload_dir, filename), 'wb+') as f:
                for chunk in logo.chunks():
                    f.write(chunk)
            update_data['logo'] = f"groups/{filename}"

        groups.update_one({'group_id': group_id}, {'$set': update_data})
        messages.success(request, 'Group details updated successfully!')
        return redirect('group_detail', group_id=group_id)

    return render(request, 'groups/edit_group.html', {'group': group})


@login_required_custom
@ratelimit(key='ip', rate='5/m', block=True)
def join_group_view(request):
    """Join an existing group using Group ID."""
    user_id = request.session['user_id']
    if request.method == 'POST':
        group_id = request.POST.get('group_id', '').strip()
        groups = get_collection('groups')
        group = groups.find_one({'group_id': group_id, 'is_active': True})

        if not group:
            messages.error(request, 'Invalid Group ID.')
            return render(request, 'groups/join_group.html')

        gm = get_collection('group_members')
        if gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'}):
            messages.warning(request, 'You are already a member of this group.')
            return render(request, 'groups/join_group.html')

        jr = get_collection('join_requests')
        if jr.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'pending'}):
            messages.warning(request, 'You already have a pending request.')
            return render(request, 'groups/join_group.html')

        profile = get_user_profile(user_id)
        jr.insert_one({
            'group_id': group_id, 'user_id': user_id,
            'member_name': profile.get('full_name', 'Unknown'),
            'status': 'pending',
            'leader_approved': False, 'co_leader_1_approved': False,
            'co_leader_2_approved': False,
            'created_at': datetime.now(),
        })

        # Notify leaders
        leaders = list(gm.find({'group_id': group_id, 'role': {'$in': ['leader', 'co-leader']}}))
        for leader in leaders:
            create_notification(
                leader['user_id'],
                'New Join Request',
                f'{profile.get("full_name", "Someone")} wants to join {group["name"]}.',
                'info', group_id
            )

        messages.success(request, f'Join request sent for "{group["name"]}"!')
        return redirect('dashboard')

    return render(request, 'groups/join_group.html')


@login_required_custom
def my_groups_view(request):
    """Show all groups the user belongs to."""
    user_id = request.session['user_id']
    
    user_groups = cache.get(f'my_groups_{user_id}')
    if user_groups is None:
        gm = get_collection('group_members')
        groups_col = get_collection('groups')

        memberships = list(gm.find({'user_id': user_id, 'status': 'active'}))
        user_groups = []
        for m in memberships:
            group = groups_col.find_one({'group_id': m['group_id']})
            if group:
                member_count = gm.count_documents({'group_id': m['group_id'], 'status': 'active'})
                balance = get_group_balance(m['group_id'])
                user_groups.append({
                    'group': group, 'role': m['role'],
                    'member_count': member_count, 'balance': balance,
                })
        cache.set(f'my_groups_{user_id}', user_groups, 300)

    return render(request, 'groups/my_groups.html', {'user_groups': user_groups})


@login_required_custom
def group_detail_view(request, group_id):
    """View detailed group information."""
    import calendar
    user_id = request.session['user_id']
    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership:
        messages.error(request, 'You are not a member of this group.')
        return redirect('my_groups')

    members = list(gm.find({'group_id': group_id, 'status': 'active'}))
    profiles = get_collection('profiles')
    member_details = []
    for m in members:
        p = profiles.find_one({'user_id': m['user_id']})
        member_details.append({'member': m, 'profile': p})

    loans = get_collection('loans')
    active_loans = list(loans.find({'group_id': group_id, 'status': {'$in': ['approved', 'active']}}))
    loan_details = []
    for loan in active_loans:
        p = profiles.find_one({'user_id': loan['user_id']})
        paid_so_far = loan.get('total_repayment', 0) - loan.get('remaining_amount', 0)
        loan_details.append({
            'loan': loan,
            'profile': p,
            'paid_so_far': paid_so_far
        })

    total_completed_loans_count = loans.count_documents({'group_id': group_id, 'status': 'completed'})
    completed_loans = list(loans.find({'group_id': group_id, 'status': 'completed'}).sort('created_at', -1).limit(3))
    completed_loan_details = []
    for loan in completed_loans:
        p = profiles.find_one({'user_id': loan['user_id']})
        completed_loan_details.append({'loan': loan, 'profile': p})

    outstanding_loans = sum(loan.get('remaining_amount', 0) for loan in active_loans)

    balance = get_group_balance(group_id)

    # Get EMI and interest collected
    txns = get_collection('transactions')
    emi_collected = 0
    interest_collected = 0
    pipeline_emi = [
        {'$match': {'group_id': group_id, 'type': 'emi_payment'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    r = list(txns.aggregate(pipeline_emi))
    if r:
        emi_collected = r[0]['total']

    pipeline_int = [
        {'$match': {'group_id': group_id, 'type': 'interest_payment'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    r2 = list(txns.aggregate(pipeline_int))
    if r2:
        interest_collected = r2[0]['total']

    fine_collected = 0
    pipeline_fine = [
        {'$match': {'group_id': group_id, 'type': 'fine_payment'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    r3 = list(txns.aggregate(pipeline_fine))
    if r3:
        fine_collected = r3[0]['total']

    # Member-wise interest
    pipeline_member_int = [
        {'$match': {'group_id': group_id, 'type': 'interest_payment'}},
        {'$group': {'_id': '$user_id', 'total': {'$sum': '$amount'}}}
    ]
    r_member_int = list(txns.aggregate(pipeline_member_int))
    member_interest = []
    for item in r_member_int:
        p = profiles.find_one({'user_id': item['_id']})
        member_interest.append({
            'name': p.get('full_name', 'Unknown') if p else 'Unknown',
            'total': item['total']
        })

    # Monthly interest collection
    pipeline_monthly_int = [
        {'$match': {'group_id': group_id, 'type': 'interest_payment'}},
        {
            '$group': {
                '_id': {
                    'year': {'$year': '$created_at'},
                    'month': {'$month': '$created_at'}
                },
                'total': {'$sum': '$amount'}
            }
        },
        {'$sort': {'_id.year': -1, '_id.month': -1}}
    ]
    r_monthly_int = list(txns.aggregate(pipeline_monthly_int))
    monthly_interest = []
    for item in r_monthly_int:
        year = item['_id']['year']
        month_num = item['_id']['month']
        month_name = calendar.month_name[month_num]
        monthly_interest.append({
            'month': f"{month_name} {year}",
            'total': item['total']
        })

    # Recent Transactions (paginated by 6)
    recent_transactions_raw = []
    recent_txns_raw = list(txns.find({'group_id': group_id}).sort('created_at', -1))
    for txn in recent_txns_raw:
        p = profiles.find_one({'user_id': txn.get('user_id')})
        member_name = p.get('full_name', 'Unknown') if p else 'Group'
        txn_type = txn.get('type', '')
        badge_class = 'member'
        if txn_type == 'loan_disbursement':
            badge_class = 'danger'
        elif txn_type in ['emi_payment', 'loan_repayment', 'interest_payment']:
            badge_class = 'success'
        recent_transactions_raw.append({
            'created_at': txn.get('created_at'),
            'member_name': member_name,
            'type_display': txn_type.replace('_', ' ').title(),
            'badge_class': badge_class,
            'description': txn.get('description', ''),
            'amount_display': f"₹{abs(txn.get('amount', 0)):,.2f}",
            'is_negative': txn.get('amount', 0) < 0
        })

    from django.core.paginator import Paginator
    paginator_txn = Paginator(recent_transactions_raw, 6)
    page_txn = request.GET.get('page_txn')
    recent_transactions = paginator_txn.get_page(page_txn)

    # Pending join, leave, emi, and repayment requests (for leaders)
    jr = get_collection('join_requests')
    lr = get_collection('leave_requests')
    emi_reqs = get_collection('emi_requests')
    repayment_reqs = get_collection('repayment_requests')
    pending_requests = []
    pending_leave_requests = []
    pending_emi_requests = []
    pending_repayment_requests = []
    pending_fine_payments = []
    pending_loan_extensions = []
    fwr = get_collection('fine_waiver_requests')
    pending_waiver_requests = []
    
    # Query pending waiver requests for all active group members to approve
    pending_waiver_requests_raw = list(fwr.find({'group_id': group_id, 'status': 'pending'}))
    for req in pending_waiver_requests_raw:
        approved_by = req.get('approved_by', [])
        if isinstance(approved_by, str):
            approved_by = [approved_by] if approved_by else []
        elif not isinstance(approved_by, list):
            approved_by = []
            
        has_approved = user_id in approved_by
        total_active_members = gm.count_documents({'group_id': group_id, 'status': 'active'})
        approvals_count = len(approved_by)
        blocked_users = {req['user_id']}
        total_required = max(1, total_active_members - len(blocked_users))
        
        req_copy = dict(req)
        req_copy['has_approved'] = has_approved
        req_copy['total_active'] = total_active_members
        req_copy['total_required'] = total_required
        req_copy['approvals_count'] = approvals_count
        pending_waiver_requests.append(req_copy)

    if membership['role'] in ['leader', 'co-leader']:
        pending_requests = list(jr.find({'group_id': group_id, 'status': 'pending'}))
        
        leave_reqs_list = list(lr.find({'group_id': group_id, 'status': 'pending'}))
        for req in leave_reqs_list:
            p = profiles.find_one({'user_id': req['user_id']})
            req['member_name'] = p.get('full_name', 'Unknown') if p else 'Unknown'
            pending_leave_requests.append(req)
            
        pending_emi_requests = list(emi_reqs.find({'group_id': group_id, 'status': 'pending'}))
        pending_repayment_requests = list(repayment_reqs.find({'group_id': group_id, 'status': 'pending'}))
        
        if_col = get_collection('imposed_fines')
        pending_fine_payments = list(if_col.find({'group_id': group_id, 'status': 'payment_pending'}))
        total_leaders = gm.count_documents({'group_id': group_id, 'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'})
        
        for pf in pending_fine_payments:
            p_profile = get_user_profile(pf['user_id'])
            pf['member_name'] = p_profile.get('full_name', 'Unknown')
            approved_by = pf.get('approved_by', [])
            if isinstance(approved_by, str):
                approved_by = [approved_by] if approved_by else []
            elif not isinstance(approved_by, list):
                approved_by = []
            
            pf['has_approved'] = user_id in approved_by
            pf['approvals_count'] = len(approved_by)
            pf['total_leaders'] = total_leaders

        extend_reqs_col = get_collection('loan_extension_requests')
        pending_loan_extensions = list(extend_reqs_col.find({'group_id': group_id, 'status': 'pending'}))
        for req in pending_loan_extensions:
            approved_by = req.get('approved_by', [])
            if isinstance(approved_by, str):
                approved_by = [approved_by] if approved_by else []
            elif not isinstance(approved_by, list):
                approved_by = []
            
            req['has_approved'] = user_id in approved_by
            req['approvals_count'] = len(approved_by)
            req['total_leaders'] = total_leaders

    user_waiver_requests_raw = list(fwr.find({'group_id': group_id, 'user_id': user_id}).sort('created_at', -1))
    paginator_waiver = Paginator(user_waiver_requests_raw, 4)
    page_waiver = request.GET.get('page_waiver')
    user_waiver_requests = paginator_waiver.get_page(page_waiver)

    # 1. Fetch pending fine impositions (visible to all active members except the target member being fined)
    ifr_col = get_collection('impose_fine_requests')
    pending_fine_impositions = []
    raw_ifrs = list(ifr_col.find({'group_id': group_id, 'status': 'pending', 'target_user_id': {'$ne': user_id}}))
    for req in raw_ifrs:
        approved_by = req.get('approved_by', [])
        if isinstance(approved_by, str):
            approved_by = [approved_by] if approved_by else []
        elif not isinstance(approved_by, list):
            approved_by = []
            
        has_approved = user_id in approved_by
        total_active_members = gm.count_documents({'group_id': group_id, 'status': 'active'})
        # Required is all active members except the target member
        required_approvals = max(1, total_active_members - 1)
        approvals_count = len(approved_by)
        
        req_copy = dict(req)
        req_copy['has_approved'] = has_approved
        req_copy['required_approvals'] = required_approvals
        req_copy['approvals_count'] = approvals_count
        pending_fine_impositions.append(req_copy)

    # 2. Fetch outstanding imposed fines for the current user to pay
    if_col = get_collection('imposed_fines')
    
    # --- AUTOMATIC LATE FINE IMPOSITION ---
    now = datetime.now()
    emi_due_day = group.get('emi_date', 1)
    if now.day > emi_due_day:
        import calendar
        # Get start and end dates of the current month
        start_of_month = datetime(now.year, now.month, 1, 0, 0, 0)
        last_day = calendar.monthrange(now.year, now.month)[1]
        end_of_month = datetime(now.year, now.month, last_day, 23, 59, 59)
        
        # Check active members of the group
        group_members = list(gm.find({'group_id': group_id, 'status': 'active'}))
        emi_records = get_collection('emi_records')
        
        for member in group_members:
            # Check if this member has an approved EMI payment record for the current month
            has_paid = emi_records.find_one({
                'group_id': group_id,
                'user_id': member['user_id'],
                'payment_date': {'$gte': start_of_month, '$lte': end_of_month},
                'status': 'paid'
            })
            
            if not has_paid:
                # Check if automatic late fine has already been imposed for this specific month
                fine_reason = f"Automatic Late Fine for {now.strftime('%B %Y')}"
                existing_fine = if_col.find_one({
                    'group_id': group_id,
                    'user_id': member['user_id'],
                    'reason': fine_reason
                })
                
                # Impose automatic late fine if not already fined and group fine_amount is set
                fine_amt = group.get('fine_amount', 0.0)
                if not existing_fine and fine_amt > 0:
                    target_profile = profiles.find_one({'user_id': member['user_id']})
                    target_name = target_profile.get('full_name', 'Unknown') if target_profile else 'Unknown'
                    
                    if_col.insert_one({
                        'group_id': group_id,
                        'user_id': member['user_id'],
                        'member_name': target_name,
                        'amount': fine_amt,
                        'reason': fine_reason,
                        'status': 'unpaid',
                        'created_at': datetime.now()
                    })
                    
                    # Notify all members of the group
                    for m in group_members:
                        if m['user_id'] == member['user_id']:
                            create_notification(
                                member['user_id'], 'Automatic Late Fine Imposed',
                                f'An automatic late fine of ₹{fine_amt:,.2f} has been imposed on you for not paying the monthly EMI on time.',
                                'danger', group_id
                            )
                        else:
                            create_notification(
                                m['user_id'], 'Automatic Late Fine Imposed',
                                f'An automatic late fine of ₹{fine_amt:,.2f} has been imposed on {target_name} for not paying the monthly EMI on time.',
                                'warning', group_id
                            )
    
    outstanding_imposed_fines = list(if_col.find({'group_id': group_id, 'user_id': user_id, 'status': 'unpaid'}))

    # Cleanup old fine waiver requests (> 7 days) from active view
    cleanup_old_waiver_requests()

    # Automatically check and send any scheduled automated reminders
    check_and_send_all_active_reminders()

    current_day = datetime.now().day
    is_emi_day = (current_day == group.get('emi_date', 1))

    return render(request, 'groups/group_detail.html', {
        'group': group, 'membership': membership,
        'member_details': member_details, 'loan_details': loan_details,
        'completed_loans': completed_loan_details,
        'total_completed_loans_count': total_completed_loans_count,
        'outstanding_loans': outstanding_loans,
        'balance': balance, 'emi_collected': emi_collected,
        'interest_collected': interest_collected, 'fine_collected': fine_collected,
        'member_interest': member_interest,
        'monthly_interest': monthly_interest,
        'recent_transactions': recent_transactions,
        'pending_requests': pending_requests,
        'pending_leave_requests': pending_leave_requests,
        'pending_emi_requests': pending_emi_requests,
        'pending_repayment_requests': pending_repayment_requests,
        'pending_waiver_requests': pending_waiver_requests,
        'user_waiver_requests': user_waiver_requests,
        'pending_fine_impositions': pending_fine_impositions,
        'outstanding_imposed_fines': outstanding_imposed_fines,
        'pending_fine_payments': pending_fine_payments,
        'pending_loan_extensions': pending_loan_extensions,
        'user_role': membership['role'],
        'is_emi_day': is_emi_day,
    })


@login_required_custom
@ratelimit(key='ip', rate='2/h', block=True)
def send_emi_alert_view(request, group_id):
    """Send manual EMI notification alert to all active group members (leaders/co-leaders only, available on EMI day only)."""
    user_id = request.session['user_id']
    gm = get_collection('group_members')
    
    # Check if group exists and the user is leader or co-leader
    membership = gm.find_one({
        'group_id': group_id, 
        'user_id': user_id, 
        'status': 'active', 
        'role': {'$in': ['leader', 'co-leader']}
    })
    
    if not membership:
        messages.error(request, 'Permission denied. Only leaders or co-leaders can send alerts.')
        return redirect('group_detail', group_id=group_id)

    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('my_groups')

    current_day = datetime.now().day
    emi_date = group.get('emi_date', 1)

    if current_day != emi_date:
        messages.error(request, f'This alert system is available on the EMI day (Day {emi_date}) only.')
        return redirect('group_detail', group_id=group_id)

    # Notify all active members
    notify_group_members(
        group_id=group_id,
        title='Pending EMI Alert',
        message=f"Reminder from Group Leaders: Your monthly EMI of {format_currency(group.get('emi_amount', 0.0))} for {group['name']} is due today! Please pay it as soon as possible.",
        notification_type='warning'
    )

    messages.success(request, 'EMI notification alert sent to all group members.')
    return redirect('group_detail', group_id=group_id)



@login_required_custom
def approve_join_request(request, request_id):
    """Approve a join request (leader/co-leader)."""
    user_id = request.session['user_id']
    jr = get_collection('join_requests')
    join_req = jr.find_one({'_id': ObjectId(request_id)})
    if not join_req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': join_req['group_id'], 'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('my_groups')

    role = membership['role']
    update = {}
    if role == 'leader':
        update['leader_approved'] = True
    elif role == 'co-leader':
        if not join_req.get('co_leader_1_approved'):
            update['co_leader_1_approved'] = True
        else:
            update['co_leader_2_approved'] = True

    jr.update_one({'_id': ObjectId(request_id)}, {'$set': update})
    join_req.update(update)

    # Check if all approvals received
    if join_req.get('leader_approved') and (
        join_req.get('co_leader_1_approved') or
        gm.count_documents({'group_id': join_req['group_id'], 'role': 'co-leader', 'status': 'active'}) == 0
    ):
        jr.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'approved'}})
        gm.update_one(
            {'group_id': join_req['group_id'], 'user_id': join_req['user_id']},
            {
                '$set': {
                    'role': 'member',
                    'status': 'active',
                    'joined_at': datetime.now()
                }
            },
            upsert=True
        )
        cache.delete(f'my_groups_{join_req["user_id"]}')
        cache.delete(f'groups_count_{join_req["user_id"]}')
        cache.delete(f'my_groups_{user_id}') # clear leader's cache too
        
        groups = get_collection('groups')
        group = groups.find_one({'group_id': join_req['group_id']})
        create_notification(
            join_req['user_id'], 'Join Request Approved',
            f'You have been added to {group["name"]}!', 'success', join_req['group_id']
        )
        notify_group_members(
            join_req['group_id'], 'New Member Joined',
            f'{join_req.get("member_name", "A member")} has joined the group {group["name"]}!',
            'info', exclude_user_id=join_req['user_id']
        )

    messages.success(request, 'Request approved!')
    return redirect('group_detail', group_id=join_req['group_id'])


@login_required_custom
def reject_join_request(request, request_id):
    """Reject a join request (leader/co-leader)."""
    user_id = request.session['user_id']
    jr = get_collection('join_requests')
    join_req = jr.find_one({'_id': ObjectId(request_id)})
    if not join_req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': join_req['group_id'], 'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('my_groups')

    jr.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'rejected'}})
    groups = get_collection('groups')
    group = groups.find_one({'group_id': join_req['group_id']})
    create_notification(
        join_req['user_id'], 'Join Request Rejected',
        f'Your request to join {group["name"]} was rejected.', 'danger', join_req['group_id']
    )

    messages.success(request, 'Join request rejected.')
    return redirect('group_detail', group_id=join_req['group_id'])


@login_required_custom
def leave_group_view(request, group_id):
    """Request to leave a group."""
    user_id = request.session['user_id']
    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership:
        messages.error(request, 'You are not in this group.')
        return redirect('my_groups')

    loans = get_collection('loans')
    active_loan = loans.find_one({
        'group_id': group_id, 'user_id': user_id,
        'status': {'$in': ['approved', 'active']}
    })
    if active_loan:
        messages.error(request, 'Cannot leave: you have an active loan.')
        return redirect('group_detail', group_id=group_id)

    if_col = get_collection('imposed_fines')
    unpaid_fine = if_col.find_one({
        'group_id': group_id, 
        'user_id': user_id, 
        'status': {'$in': ['unpaid', 'payment_pending']}
    })
    if unpaid_fine:
        messages.error(request, 'Cannot leave: you have unpaid imposed fines.')
        return redirect('group_detail', group_id=group_id)

    if request.method == 'POST':
        lr = get_collection('leave_requests')
        if lr.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'pending'}):
            messages.warning(request, 'You already have a pending leave request.')
            return redirect('group_detail', group_id=group_id)
            
        lr.insert_one({
            'group_id': group_id, 'user_id': user_id,
            'status': 'pending', 'leader_approved': False,
            'created_at': datetime.now(),
        })

        leaders = list(gm.find({'group_id': group_id, 'role': {'$in': ['leader', 'co-leader']}}))
        profile = get_user_profile(user_id)
        for leader in leaders:
            create_notification(
                leader['user_id'], 'Leave Request',
                f'{profile.get("full_name", "A member")} wants to leave the group.',
                'warning', group_id
            )

        messages.success(request, 'Leave request submitted.')
        return redirect('my_groups')

    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})
    return render(request, 'groups/leave_group.html', {'group': group})


@login_required_custom
def approve_leave_request(request, request_id):
    """Approve a leave request."""
    user_id = request.session['user_id']
    lr = get_collection('leave_requests')
    leave_req = lr.find_one({'_id': ObjectId(request_id)})
    if not leave_req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': leave_req['group_id'], 'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('my_groups')

    lr.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'approved', 'leader_approved': True}})
    gm.update_one(
        {'group_id': leave_req['group_id'], 'user_id': leave_req['user_id']},
        {'$set': {'status': 'inactive'}}
    )
    create_notification(
        leave_req['user_id'], 'Leave Approved',
        'Your leave request has been approved.', 'info', leave_req['group_id']
    )
    left_profile = get_user_profile(leave_req['user_id'])
    notify_group_members(
        leave_req['group_id'], 'Member Left Group',
        f'{left_profile.get("full_name", "A member")} has left the group.',
        'info', exclude_user_id=leave_req['user_id']
    )

    messages.success(request, 'Leave request approved.')
    return redirect('group_detail', group_id=leave_req['group_id'])


@login_required_custom
def reject_leave_request(request, request_id):
    """Reject a leave request."""
    user_id = request.session['user_id']
    lr = get_collection('leave_requests')
    leave_req = lr.find_one({'_id': ObjectId(request_id)})
    if not leave_req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': leave_req['group_id'], 'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('my_groups')

    lr.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'rejected', 'leader_approved': False}})
    create_notification(
        leave_req['user_id'], 'Leave Request Rejected',
        'Your request to leave the group has been rejected.', 'danger', leave_req['group_id']
    )

    messages.success(request, 'Leave request rejected.')
    return redirect('group_detail', group_id=leave_req['group_id'])


@login_required_custom
def promote_member_view(request, group_id, member_user_id):
    """Promote a member to co-leader (leader only)."""
    user_id = request.session['user_id']
    gm = get_collection('group_members')
    leader = gm.find_one({'group_id': group_id, 'user_id': user_id, 'role': 'leader', 'status': 'active'})
    if not leader:
        messages.error(request, 'Only the group leader can promote members.')
        return redirect('group_detail', group_id=group_id)

    gm.update_one(
        {'group_id': group_id, 'user_id': member_user_id},
        {'$set': {'role': 'co-leader'}}
    )
    create_notification(member_user_id, 'Promoted!', 'You have been promoted to Co-Leader.', 'success', group_id)
    promoted_profile = get_user_profile(member_user_id)
    notify_group_members(
        group_id, 'New Co-Leader Promoted',
        f'{promoted_profile.get("full_name", "A member")} has been promoted to Co-Leader!',
        'success', exclude_user_id=member_user_id
    )
    messages.success(request, 'Member promoted to Co-Leader.')
    return redirect('group_detail', group_id=group_id)


@login_required_custom
def demote_member_view(request, group_id, member_user_id):
    """Demote a co-leader back to a regular member (leader only)."""
    user_id = request.session['user_id']
    gm = get_collection('group_members')
    
    # Only leader can demote
    leader = gm.find_one({'group_id': group_id, 'user_id': user_id, 'role': 'leader', 'status': 'active'})
    if not leader:
        messages.error(request, 'Only the group leader can demote co-leaders.')
        return redirect('group_detail', group_id=group_id)
        
    target_membership = gm.find_one({
        'group_id': group_id,
        'user_id': member_user_id,
        'status': 'active',
        'role': 'co-leader'
    })
    
    if not target_membership:
        messages.error(request, 'Target member is not a Co-Leader.')
        return redirect('group_detail', group_id=group_id)
        
    gm.update_one(
        {'group_id': group_id, 'user_id': member_user_id},
        {'$set': {'role': 'member'}}
    )
    
    # Notify the user
    create_notification(member_user_id, 'Demoted to Member', 'Your role has been updated to Member.', 'warning', group_id)
    
    # Notify other members
    p = get_user_profile(member_user_id)
    notify_group_members(
        group_id, 'Co-Leader Role Updated',
        f'{p.get("full_name", "A co-leader")} has been updated to Member.',
        'warning', exclude_user_id=member_user_id
    )
    
    messages.success(request, 'Co-Leader successfully demoted to Member.')
    return redirect('group_detail', group_id=group_id)


@login_required_custom
def remove_member_view(request, group_id, member_user_id):
    """Remove (kick) a member from the group (leaders and co-leaders)."""
    user_id = request.session['user_id']
    gm = get_collection('group_members')
    
    # Check if current user is an active leader or co-leader
    current_membership = gm.find_one({
        'group_id': group_id,
        'user_id': user_id,
        'status': 'active',
        'role': {'$in': ['leader', 'co-leader']}
    })
    
    if not current_membership:
        messages.error(request, 'Permission denied. Only leaders and co-leaders can remove members.')
        return redirect('group_detail', group_id=group_id)
        
    target_membership = gm.find_one({
        'group_id': group_id,
        'user_id': member_user_id,
        'status': 'active'
    })
    
    if not target_membership:
        messages.error(request, 'Member not found in this group.')
        return redirect('group_detail', group_id=group_id)
        
    # Role-based restriction:
    # Co-leaders cannot remove other co-leaders or the leader
    if current_membership['role'] == 'co-leader' and target_membership['role'] in ['co-leader', 'leader']:
        messages.error(request, 'Permission denied. Co-leaders cannot remove other co-leaders or the leader.')
        return redirect('group_detail', group_id=group_id)
        
    # Remove the member by setting status to 'removed' and resetting role
    gm.update_one(
        {'group_id': group_id, 'user_id': member_user_id},
        {'$set': {'status': 'removed', 'role': 'member'}}
    )
    
    # Notify the user
    create_notification(member_user_id, 'Removed from Group', 'You have been removed from the group.', 'danger', group_id)
    
    # Notify other members
    p = get_user_profile(member_user_id)
    notify_group_members(
        group_id, 'Member Removed',
        f'{p.get("full_name", "A member")} has been removed from the group.',
        'danger', exclude_user_id=member_user_id
    )
    
    messages.success(request, f'Member successfully removed.')
    return redirect('group_detail', group_id=group_id)


@login_required_custom
def delete_group_view(request, group_id):
    """Destroy the group completely (leader only)."""
    user_id = request.session['user_id']
    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active', 'role': 'leader'})
    if not membership:
        messages.error(request, 'Only the group leader can destroy the group.')
        return redirect('group_detail', group_id=group_id)

    # Delete all traces of the group
    get_collection('join_requests').delete_many({'group_id': group_id})
    get_collection('leave_requests').delete_many({'group_id': group_id})
    get_collection('loans').delete_many({'group_id': group_id})
    get_collection('transactions').delete_many({'group_id': group_id})
    get_collection('emi_records').delete_many({'group_id': group_id})
    get_collection('emi_requests').delete_many({'group_id': group_id})
    gm.delete_many({'group_id': group_id})
    groups.delete_one({'group_id': group_id})

    messages.success(request, f'Group "{group.get("name")}" has been completely destroyed.')
    return redirect('my_groups')


@login_required_custom
def waive_fine_request_view(request, group_id):
    """Allow active members (including leaders for their own late fines) to request their own late fine waiver."""
    user_id = request.session['user_id']
    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id, 'is_active': True})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership:
        messages.error(request, 'You are not an active member of this group.')
        return redirect('my_groups')

    if_col = get_collection('imposed_fines')

    # Check if the member has their own unpaid automatic late fine
    has_unpaid_late_fine = if_col.find_one({
        'group_id': group_id,
        'user_id': user_id,
        'status': 'unpaid',
        'reason': {'$regex': '^Automatic Late Fine'}
    })
    if not has_unpaid_late_fine:
        messages.error(request, 'You do not have any unpaid late fines to waive.')
        return redirect('group_detail', group_id=group_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        voice_data = request.POST.get('voice_data', '').strip()

        if not reason:
            messages.error(request, 'Please provide a reason.')
            return render(request, 'groups/waive_fine_request.html', {
                'group': group
            })

        fwr = get_collection('fine_waiver_requests')

        if fwr.find_one({
            'group_id': group_id,
            'user_id': user_id,
            'status': 'pending',
            'is_imposed_fine_waiver': {'$ne': True}
        }):
            messages.warning(request, 'You already have a pending fine waiver request.')
            return redirect('group_detail', group_id=group_id)

        profile = get_user_profile(user_id)
        ins = fwr.insert_one({
            'group_id': group_id,
            'user_id': user_id,
            'member_name': profile.get('full_name', 'Unknown'),
            'reason': reason,
            'voice_data': voice_data,
            'status': 'pending',
            'requester_user_id': user_id,
            'is_imposed_fine_waiver': False,
            'approved_by': [],
            'created_at': datetime.now(),
        })
        sync_to_waiver_history(ins.inserted_id)

        # Notify leaders and co-leaders
        leaders = list(gm.find({
            'group_id': group_id,
            'role': {'$in': ['leader', 'co-leader']},
            'status': 'active'
        }))
        for leader in leaders:
            create_notification(
                leader['user_id'], 'Late Fine Waiver Request',
                f'{profile.get("full_name", "A member")} has submitted a late fine waiver request.',
                'warning', group_id
            )

        messages.success(request, 'Late fine waiver request submitted successfully!')
        return redirect('group_detail', group_id=group_id)

    return render(request, 'groups/waive_fine_request.html', {
        'group': group
    })


@login_required_custom
def waive_imposed_fine_request_view(request, group_id):
    """Allow leaders/co-leaders to request waiving off any unpaid fine in the group (both manual imposed and late fines)."""
    user_id = request.session['user_id']
    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id, 'is_active': True})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership:
        messages.error(request, 'Permission denied. Only active members can access this page.')
        return redirect('group_detail', group_id=group_id)

    user_role = membership.get('role', 'member')
    if_col = get_collection('imposed_fines')

    # Fetch all unpaid fines in the group (available to leaders/co-leaders to waive for anyone; members can only waive for themselves)
    query = {
        'group_id': group_id,
        'status': 'unpaid'
    }
    if user_role == 'member':
        query['user_id'] = user_id

    unpaid_fines = []
    profiles = get_collection('profiles')
    raw_fines = list(if_col.find(query))
    for fine in raw_fines:
        target_profile = profiles.find_one({'user_id': fine['user_id']})
        target_name = target_profile.get('full_name', 'Unknown') if target_profile else 'Unknown'
        is_late_fine = fine['reason'].startswith('Automatic Late Fine')
        fine_type_lbl = "Late Fine" if is_late_fine else "Imposed Fine"
        fine['display_label'] = f"{target_name} - ₹{fine['amount']:.2f} ({fine_type_lbl}: \"{fine['reason']}\")"
        unpaid_fines.append(fine)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        voice_data = request.POST.get('voice_data', '').strip()
        fine_id = request.POST.get('fine_id', '').strip()

        if not reason:
            messages.error(request, 'Please provide a reason.')
            return render(request, 'groups/waive_imposed_fine_request.html', {
                'group': group, 'unpaid_fines': unpaid_fines
            })

        if not fine_id:
            messages.error(request, 'Please select a fine to waive.')
            return render(request, 'groups/waive_imposed_fine_request.html', {
                'group': group, 'unpaid_fines': unpaid_fines
            })

        fine_doc = if_col.find_one({'_id': ObjectId(fine_id)})
        if not fine_doc:
            messages.error(request, 'Selected fine not found.')
            return render(request, 'groups/waive_imposed_fine_request.html', {
                'group': group, 'unpaid_fines': unpaid_fines
            })

        fwr = get_collection('fine_waiver_requests')

        # Check if leader has a pending request for this specific fine
        if fwr.find_one({'fine_id': ObjectId(fine_id), 'status': 'pending'}):
            messages.warning(request, 'A waiver request is already pending for this fine.')
            return redirect('group_detail', group_id=group_id)

        target_profile = profiles.find_one({'user_id': fine_doc['user_id']})
        target_name = target_profile.get('full_name', 'Unknown') if target_profile else 'Unknown'
        leader_profile = get_user_profile(user_id)
        is_imposed = not fine_doc['reason'].startswith('Automatic Late Fine')

        ins = fwr.insert_one({
            'group_id': group_id,
            'user_id': fine_doc['user_id'],
            'member_name': target_name,
            'reason': f"Waiver request by leader ({leader_profile.get('full_name')}): {reason}",
            'voice_data': voice_data,
            'status': 'pending',
            'is_imposed_fine_waiver': is_imposed,
            'fine_id': ObjectId(fine_id),
            'fine_amount': fine_doc['amount'],
            'fine_reason': fine_doc['reason'],
            'requester_user_id': user_id,
            'approved_by': [],
            'created_at': datetime.now(),
        })
        sync_to_waiver_history(ins.inserted_id)

        # Notify all active members
        all_active = list(gm.find({'group_id': group_id, 'status': 'active'}))
        for member in all_active:
            if member['user_id'] != user_id:
                create_notification(
                    member['user_id'], 'Fine Waiver Request',
                    f'Leader {leader_profile.get("full_name")} requested to waive ₹{fine_doc["amount"]:,.2f} fine on {target_name}.',
                    'warning', group_id
                )

        messages.success(request, 'Waiver request submitted successfully!')
        return redirect('group_detail', group_id=group_id)

    return render(request, 'groups/waive_imposed_fine_request.html', {
        'group': group, 'unpaid_fines': unpaid_fines
    })


@login_required_custom
def approve_waive_request(request, request_id):
    """Approve fine waiver request. Requires approval of all active group members."""
    user_id = request.session['user_id']
    fwr = get_collection('fine_waiver_requests')
    req = fwr.find_one({'_id': ObjectId(request_id)})
    if not req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    group_id = req['group_id']
    gm = get_collection('group_members')
    
    # Check if current user is active member of the group
    membership = gm.find_one({
        'group_id': group_id,
        'user_id': user_id,
        'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied. Only active group members can approve this request.')
        return redirect('group_detail', group_id=group_id)

    # Block self-approval: only the target user whose fine it is is blocked from approving
    blocked_users = {req['user_id']}
    if user_id in blocked_users:
        messages.error(request, 'You cannot approve your own fine waiver request.')
        return redirect('group_detail', group_id=group_id)

    approved_by = req.get('approved_by', [])
    if isinstance(approved_by, str):
        approved_by = [approved_by] if approved_by else []
    elif not isinstance(approved_by, list):
        approved_by = []

    if user_id in approved_by:
        messages.warning(request, 'You have already approved this request.')
        return redirect('group_detail', group_id=group_id)

    # Add user to approved list
    approved_by.append(user_id)
    update = {'approved_by': approved_by}

    # Update database
    fwr.update_one({'_id': ObjectId(request_id)}, {'$set': update})

    # Get active members count
    total_active_members = gm.count_documents({
        'group_id': group_id,
        'status': 'active'
    })
    
    # Exclude only blocked target user from the required approvals count
    required_approvals = max(1, total_active_members - len(blocked_users))

    # Check if all other active members have approved
    if len(approved_by) >= required_approvals:
        fwr.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'approved'}})
        
        if_col = get_collection('imposed_fines')
        
        if req.get('is_imposed_fine_waiver') == True:
            # Waive only this specific manually imposed consensus fine
            if_col.update_one(
                {'_id': ObjectId(req['fine_id'])},
                {'$set': {'status': 'waived'}}
            )
            messages.success(request, 'Request fully approved! The manual imposed fine has been waived.')
        else:
            # Remove fine from any pending EMI requests
            emi_reqs = get_collection('emi_requests')
            for emi in emi_reqs.find({'group_id': group_id, 'user_id': req['user_id'], 'status': 'pending'}):
                emi_reqs.update_one(
                    {'_id': emi['_id']},
                    {'$set': {'fine_amount': 0.0, 'total_amount': emi['emi_amount']}}
                )

            # Waive only the automatic late fine in imposed_fines collection
            if_col.update_many(
                {
                    'group_id': group_id, 
                    'user_id': req['user_id'], 
                    'status': {'$in': ['unpaid', 'payment_pending']},
                    'reason': {'$regex': '^Automatic Late Fine'}
                },
                {'$set': {'status': 'waived'}}
            )
            messages.success(request, 'Request fully approved! The automatic late fine has been waived.')

        # Notify the user
        create_notification(
            req['user_id'], 'Fine Waiver Approved',
            'Your fine waiver request has been fully approved by all group members! The fine has been waived and removed.',
            'success', group_id
        )
    else:
        remaining = required_approvals - len(approved_by)
        messages.success(request, f'Approval recorded! ({len(approved_by)} of {required_approvals} required other members have approved).')

    sync_to_waiver_history(request_id)
    return redirect('group_detail', group_id=group_id)


@login_required_custom
def reject_waive_request(request, request_id):
    """Reject a fine waiver request."""
    user_id = request.session['user_id']
    fwr = get_collection('fine_waiver_requests')
    req = fwr.find_one({'_id': ObjectId(request_id)})
    if not req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    group_id = req['group_id']
    gm = get_collection('group_members')
    
    # Check if current user is active leader/co-leader of the group
    membership = gm.find_one({
        'group_id': group_id,
        'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']},
        'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('group_detail', group_id=group_id)

    fwr.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'rejected'}})
    sync_to_waiver_history(request_id)

    # Notify user
    create_notification(
        req['user_id'], 'Fine Waiver Rejected',
        'Your fine waiver request was rejected by leaders.',
        'danger', group_id
    )
    messages.error(request, 'Fine waiver request has been rejected.')
    return redirect('group_detail', group_id=group_id)


@login_required_custom
def impose_fine_request_view(request, group_id, target_user_id):
    """Allow active leaders/co-leaders to initiate a fine on an active member."""
    user_id = request.session['user_id']
    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id, 'is_active': True})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership or membership.get('role') not in ['leader', 'co-leader']:
        messages.error(request, 'Permission denied. Only leaders and co-leaders can impose fines.')
        return redirect('group_detail', group_id=group_id)

    target_membership = gm.find_one({'group_id': group_id, 'user_id': target_user_id, 'status': 'active'})
    if not target_membership:
        messages.error(request, 'Target member not found in this group.')
        return redirect('group_detail', group_id=group_id)

    target_profile = get_user_profile(target_user_id)

    if request.method == 'POST':
        fine_amount_str = request.POST.get('fine_amount', '0').strip()
        reason = request.POST.get('reason', '').strip()

        try:
            fine_amount = float(fine_amount_str)
        except ValueError:
            fine_amount = 0.0

        if fine_amount <= 0:
            messages.error(request, 'Please provide a valid fine amount greater than 0.')
            return render(request, 'groups/impose_fine_request.html', {'group': group, 'target_profile': target_profile})

        if not reason:
            messages.error(request, 'Please provide a reason for the fine.')
            return render(request, 'groups/impose_fine_request.html', {'group': group, 'target_profile': target_profile})

        ifr = get_collection('impose_fine_requests')

        # Determine if consensus is reached immediately (e.g. only 2 active members)
        total_active_members = gm.count_documents({'group_id': group_id, 'status': 'active'})
        required_approvals = max(1, total_active_members - 1)

        status = 'pending'
        if required_approvals <= 1:
            status = 'approved'

        ifr.insert_one({
            'group_id': group_id,
            'user_id': user_id,
            'target_user_id': target_user_id,
            'target_member_name': target_profile.get('full_name', 'Unknown'),
            'fine_amount': fine_amount,
            'reason': reason,
            'status': status,
            'approved_by': [user_id],
            'created_at': datetime.now(),
        })

        if status == 'approved':
            # Record outstanding imposed fine immediately
            get_collection('imposed_fines').insert_one({
                'group_id': group_id,
                'user_id': target_user_id,
                'member_name': target_profile.get('full_name', 'Unknown'),
                'amount': fine_amount,
                'reason': reason,
                'status': 'unpaid',
                'created_at': datetime.now()
            })

            # Notify all active group members
            all_active = list(gm.find({'group_id': group_id, 'status': 'active'}))
            for member in all_active:
                if member['user_id'] == target_user_id:
                    create_notification(
                        target_user_id, 'Fine Imposed on You',
                        f'A consensus fine of ₹{fine_amount:,.2f} has been imposed on you for: {reason}',
                        'danger', group_id
                    )
                else:
                    create_notification(
                        member['user_id'], 'Consensus Fine Imposed',
                        f'A consensus fine of ₹{fine_amount:,.2f} has been imposed on {target_profile.get("full_name")} for: {reason}',
                        'warning', group_id
                    )
            messages.success(request, f'Fine of ₹{fine_amount:,.2f} has been successfully imposed immediately (Consensus reached automatically)!')
        else:
            # Notify other active members (excluding the target member)
            other_members = list(gm.find({
                'group_id': group_id,
                'status': 'active',
                'user_id': {'$nin': [target_user_id, user_id]}
            }))
            for m in other_members:
                create_notification(
                    m['user_id'], 'Fine Imposition Review',
                    f'Leader has requested to fine {target_profile.get("full_name")} - ₹{fine_amount:.2f}. Please vote.',
                    'warning', group_id
                )
            messages.success(request, 'Fine imposition request generated and sent for consensus approval.')
        return redirect('group_detail', group_id=group_id)

    return render(request, 'groups/impose_fine_request.html', {'group': group, 'target_profile': target_profile})


@login_required_custom
def approve_impose_fine_view(request, request_id):
    """Approve fine imposition request. Excluding the fined member, 100% consensus is required."""
    user_id = request.session['user_id']
    ifr = get_collection('impose_fine_requests')
    req = ifr.find_one({'_id': ObjectId(request_id)})
    if not req:
        messages.error(request, 'Imposition request not found.')
        return redirect('my_groups')

    group_id = req['group_id']
    if req['status'] != 'pending':
        messages.warning(request, 'This imposition request has already been processed.')
        return redirect('group_detail', group_id=group_id)

    target_user_id = req['target_user_id']

    if user_id == target_user_id:
        messages.error(request, 'Permission denied. You cannot vote on a fine against yourself.')
        return redirect('group_detail', group_id=group_id)

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership:
        messages.error(request, 'Only active members can vote on this request.')
        return redirect('group_detail', group_id=group_id)

    approved_by = req.get('approved_by', [])
    if user_id in approved_by:
        messages.warning(request, 'You have already approved this request.')
        return redirect('group_detail', group_id=group_id)

    approved_by.append(user_id)
    ifr.update_one({'_id': ObjectId(request_id)}, {'$set': {'approved_by': approved_by}})

    total_active = gm.count_documents({'group_id': group_id, 'status': 'active'})
    required_approvals = max(1, total_active - 1)

    if len(approved_by) >= required_approvals:
        ifr.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'approved'}})

        # Record outstanding imposed fine
        get_collection('imposed_fines').insert_one({
            'group_id': group_id,
            'user_id': target_user_id,
            'member_name': req['target_member_name'],
            'amount': req['fine_amount'],
            'reason': req['reason'],
            'status': 'unpaid',
            'created_at': datetime.now()
        })

        # Notify all active group members
        all_active_members = list(gm.find({'group_id': group_id, 'status': 'active'}))
        for member in all_active_members:
            if member['user_id'] == target_user_id:
                create_notification(
                    target_user_id, 'Fine Imposed on You',
                    f'A consensus fine of ₹{req["fine_amount"]:,.2f} has been imposed on you for: {req["reason"]}',
                    'danger', group_id
                )
            else:
                create_notification(
                    member['user_id'], 'Consensus Fine Imposed',
                    f'A consensus fine of ₹{req["fine_amount"]:,.2f} has been imposed on {req["target_member_name"]} for: {req["reason"]}',
                    'warning', group_id
                )

        messages.success(request, '100% consensus reached! The fine has been successfully imposed.')
    else:
        messages.success(request, f'Approval recorded! ({len(approved_by)} of {required_approvals} required approvals).')

    return redirect('group_detail', group_id=group_id)


@login_required_custom
def reject_impose_fine_view(request, request_id):
    """Reject fine imposition request."""
    user_id = request.session['user_id']
    ifr = get_collection('impose_fine_requests')
    req = ifr.find_one({'_id': ObjectId(request_id)})
    if not req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    group_id = req['group_id']
    if req['status'] != 'pending':
        messages.warning(request, 'This request has already been processed.')
        return redirect('group_detail', group_id=group_id)

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'})
    if not membership:
        messages.error(request, 'Permission denied. Only leaders/co-leaders can reject this request.')
        return redirect('group_detail', group_id=group_id)

    ifr.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'rejected'}})

    # Notify creator
    create_notification(
        req['user_id'], 'Fine Imposition Rejected',
        f'Your fine request against {req["target_member_name"]} has been rejected by leadership.',
        'info', group_id
    )

    messages.error(request, 'Fine imposition request has been rejected.')
    return redirect('group_detail', group_id=group_id)


@login_required_custom
def pay_imposed_fine_view(request, fine_id):
    """Submit a fine payment request for leader/co-leader approval."""
    user_id = request.session['user_id']
    if_col = get_collection('imposed_fines')
    fine = if_col.find_one({'_id': ObjectId(fine_id), 'user_id': user_id, 'status': 'unpaid'})
    if not fine:
        messages.error(request, 'Fine not found, already paid, or pending approval.')
        return redirect('my_groups')

    group_id = fine['group_id']

    # Update fine status to pending approval
    if_col.update_one({'_id': ObjectId(fine_id)}, {'$set': {'status': 'payment_pending', 'payment_submitted_at': datetime.now()}})

    # Notify leaders and co-leaders
    gm = get_collection('group_members')
    leaders = list(gm.find({'group_id': group_id, 'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'}))
    profile = get_user_profile(user_id)
    for leader in leaders:
        create_notification(
            leader['user_id'], 'Fine Payment Approval Requested',
            f'{profile.get("full_name")} has submitted a fine payment of ₹{fine["amount"]:,.2f} for approval.',
            'info', group_id
        )

    # Notify the fined member that it is submitted
    create_notification(
        user_id, 'Fine Payment Submitted',
        f'Your fine payment request of ₹{fine["amount"]:,.2f} has been submitted for leadership approval.',
        'warning', group_id
    )

    messages.success(request, 'Fine payment request submitted successfully! Waiting for leaders to approve.')
    return redirect('group_detail', group_id=group_id)


@login_required_custom
def approve_fine_payment_view(request, fine_id):
    """Allow active leaders/co-leaders to approve a pending fine payment request."""
    user_id = request.session['user_id']
    if_col = get_collection('imposed_fines')
    fine = if_col.find_one({'_id': ObjectId(fine_id)})
    if not fine:
        messages.error(request, 'Fine record not found.')
        return redirect('my_groups')

    group_id = fine['group_id']
    
    # Check if current user is active leader/co-leader of the group
    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': group_id,
        'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']},
        'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied. Only leaders and co-leaders can approve fine payments.')
        return redirect('group_detail', group_id=group_id)

    if fine['status'] != 'payment_pending':
        messages.warning(request, 'This fine payment is not pending approval.')
        return redirect('group_detail', group_id=group_id)

    approved_by = fine.get('approved_by', [])
    if isinstance(approved_by, str):
        approved_by = [approved_by] if approved_by else []
    elif not isinstance(approved_by, list):
        approved_by = []

    if user_id in approved_by:
        messages.warning(request, 'You have already approved this fine payment.')
        return redirect('group_detail', group_id=group_id)

    approved_by.append(user_id)

    total_leaders = gm.count_documents({'group_id': group_id, 'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'})
    
    if len(approved_by) >= total_leaders:
        # Mark as paid
        if_col.update_one({'_id': ObjectId(fine_id)}, {'$set': {'status': 'paid', 'paid_at': datetime.now(), 'approved_by': approved_by}})

        # Record group transaction
        txns = get_collection('transactions')
        txns.insert_one({
            'group_id': group_id,
            'user_id': fine['user_id'],
            'type': 'fine_payment',
            'amount': fine['amount'],
            'description': f'Imposed fine payment: ₹{fine["amount"]:,.2f} (Reason: {fine["reason"]})',
            'created_at': datetime.now(),
        })

        # Notify the fined member
        create_notification(
            fine['user_id'], 'Fine Paid Successfully',
            f'Your fine payment of ₹{fine["amount"]:,.2f} has been fully approved by leadership!',
            'success', group_id
        )

        messages.success(request, 'Fine payment fully approved and processed!')
    else:
        if_col.update_one({'_id': ObjectId(fine_id)}, {'$set': {'approved_by': approved_by}})
        messages.success(request, f'Approval recorded! ({len(approved_by)} of {total_leaders} leaders approved).')

    return redirect('group_detail', group_id=group_id)


@login_required_custom
def reject_fine_payment_view(request, fine_id):
    """Allow active leaders/co-leaders to reject a pending fine payment request, resetting it to unpaid."""
    user_id = request.session['user_id']
    if_col = get_collection('imposed_fines')
    fine = if_col.find_one({'_id': ObjectId(fine_id)})
    if not fine:
        messages.error(request, 'Fine record not found.')
        return redirect('my_groups')

    group_id = fine['group_id']
    
    # Check if current user is active leader/co-leader of the group
    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': group_id,
        'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']},
        'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied. Only leaders and co-leaders can reject fine payments.')
        return redirect('group_detail', group_id=group_id)

    if fine['status'] != 'payment_pending':
        messages.warning(request, 'This fine payment is not pending approval.')
        return redirect('group_detail', group_id=group_id)

    # Reset back to unpaid
    if_col.update_one({'_id': ObjectId(fine_id)}, {'$set': {'status': 'unpaid', 'rejected_at': datetime.now(), 'rejected_by': user_id}})

    # Notify the member
    create_notification(
        fine['user_id'], 'Fine Payment Request Rejected',
        f'Your fine payment of ₹{fine["amount"]:,.2f} was rejected by leadership. Please resubmit or contact leaders.',
        'danger', group_id
    )

    messages.error(request, 'Fine payment request has been rejected.')
    return redirect('group_detail', group_id=group_id)


@login_required_custom
def group_settlement_preview_view(request, group_id):
    """Show the distribution plan of the group's assets to members."""
    user_id = request.session['user_id']
    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership:
        messages.error(request, 'You are not a member of this group.')
        return redirect('my_groups')

    # Get active members
    active_members = list(gm.find({'group_id': group_id, 'status': 'active'}))
    num_members = len(active_members)

    total_cash = get_group_balance(group_id)

    loans = get_collection('loans')
    if_col = get_collection('imposed_fines')
    profiles = get_collection('profiles')

    member_plans = []
    total_loan_dues = 0
    total_fine_dues = 0

    # Calculate dues for each member first to find total_dues
    for m in active_members:
        m_user_id = m['user_id']
        p = profiles.find_one({'user_id': m_user_id})
        name = p.get('full_name', 'Unknown') if p else 'Unknown'

        # Sum of active/approved loans
        active_loans = list(loans.find({'group_id': group_id, 'user_id': m_user_id, 'status': {'$in': ['approved', 'active']}}))
        loan_dues = sum(l.get('remaining_amount', 0.0) for l in active_loans)

        # Sum of unpaid fines
        unpaid_fines = list(if_col.find({'group_id': group_id, 'user_id': m_user_id, 'status': 'unpaid'}))
        fine_dues = sum(f.get('amount', 0.0) for f in unpaid_fines)

        total_loan_dues += loan_dues
        total_fine_dues += fine_dues

        member_plans.append({
            'user_id': m_user_id,
            'name': name,
            'role': m.get('role', 'member'),
            'loan_dues': loan_dues,
            'fine_dues': fine_dues,
        })

    total_dues = total_loan_dues + total_fine_dues
    total_wealth = total_cash + total_dues
    base_share = total_wealth / num_members if num_members > 0 else 0.0

    # Fill in base share and net payout for each member
    for plan in member_plans:
        plan['base_share'] = base_share
        plan['net_payout'] = base_share - plan['loan_dues'] - plan['fine_dues']

    context = {
        'group': group,
        'total_cash': total_cash,
        'total_dues': total_dues,
        'total_wealth': total_wealth,
        'base_share': base_share,
        'member_plans': member_plans,
        'user_role': membership.get('role', 'member'),
    }
    return render(request, 'groups/settlement_preview.html', context)


@login_required_custom
def execute_group_settlement_view(request, group_id):
    """Execute the final settlement distribution plan (leaders only)."""
    if request.method != 'POST':
        return redirect('group_settlement_preview', group_id=group_id)

    user_id = request.session['user_id']
    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership or membership.get('role') not in ['leader', 'co-leader']:
        messages.error(request, 'Permission denied. Only leaders and co-leaders can execute settlement.')
        return redirect('group_detail', group_id=group_id)

    active_members = list(gm.find({'group_id': group_id, 'status': 'active'}))
    num_members = len(active_members)
    if num_members == 0:
        messages.error(request, 'No active members to distribute assets to.')
        return redirect('group_detail', group_id=group_id)

    total_cash = get_group_balance(group_id)

    loans = get_collection('loans')
    if_col = get_collection('imposed_fines')
    txns = get_collection('transactions')

    # Gather totals
    total_loan_dues = 0
    total_fine_dues = 0
    member_data = []

    for m in active_members:
        m_user_id = m['user_id']
        active_loans = list(loans.find({'group_id': group_id, 'user_id': m_user_id, 'status': {'$in': ['approved', 'active']}}))
        loan_dues = sum(l.get('remaining_amount', 0.0) for l in active_loans)

        unpaid_fines = list(if_col.find({'group_id': group_id, 'user_id': m_user_id, 'status': 'unpaid'}))
        fine_dues = sum(f.get('amount', 0.0) for f in unpaid_fines)

        total_loan_dues += loan_dues
        total_fine_dues += fine_dues

        member_data.append({
            'user_id': m_user_id,
            'loan_dues': loan_dues,
            'fine_dues': fine_dues,
        })

    total_dues = total_loan_dues + total_fine_dues
    total_wealth = total_cash + total_dues
    base_share = total_wealth / num_members

    # Process each member
    for item in member_data:
        m_user_id = item['user_id']
        net_payout = base_share - item['loan_dues'] - item['fine_dues']

        # Record payout transaction
        txns.insert_one({
            'group_id': group_id,
            'user_id': m_user_id,
            'type': 'settlement_payout',
            'amount': -net_payout,
            'description': f'Settlement distribution payout: {format_currency(net_payout)}',
            'created_at': datetime.now(),
        })

        # Mark all pending/active loans of this member in this group as completed
        loans.update_many(
            {'group_id': group_id, 'user_id': m_user_id, 'status': {'$in': ['approved', 'active']}},
            {'$set': {'status': 'completed', 'remaining_amount': 0.0, 'settled_at': datetime.now()}}
        )

        # Mark all unpaid fines as paid
        if_col.update_many(
            {'group_id': group_id, 'user_id': m_user_id, 'status': 'unpaid'},
            {'$set': {'status': 'paid', 'settled_at': datetime.now()}}
        )

        # Notify member
        create_notification(
            m_user_id,
            'Group Settlement Executed',
            f'The final distribution plan has been executed. Your net payout is {format_currency(net_payout)}.',
            'success',
            group_id
        )

    messages.success(request, 'Group settlement executed successfully! All dues cleared and cash distributed.')
    return redirect('group_detail', group_id=group_id)



