"""
Loan management views for GroupSathi.
"""

from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from bson import ObjectId
from core.decorators import login_required_custom
from core.db import get_collection
from core.utils import (
    get_user_profile, create_notification,
    get_group_balance, calculate_simple_interest,
    notify_group_members
)


@login_required_custom
def loan_list_view(request):
    """List all loans for the user across groups."""
    user_id = request.session['user_id']
    loans = get_collection('loans')
    groups = get_collection('groups')
    profiles = get_collection('profiles')
    gm = get_collection('group_members')

    if_col = get_collection('imposed_fines')
    user_loans = list(loans.find({'user_id': user_id, 'status': {'$in': ['approved', 'active']}}).sort('created_at', -1))
    loan_data = []
    for loan in user_loans:
        group = groups.find_one({'group_id': loan['group_id']})
        group_fines = list(if_col.find({'group_id': loan['group_id'], 'user_id': user_id, 'status': 'unpaid'}))
        total_fines = sum(fine.get('amount', 0) for fine in group_fines)
        loan_data.append({
            'loan': loan,
            'group': group,
            'fines': group_fines,
            'total_fines': total_fines
        })

    # Get all active memberships of the user
    user_memberships = list(gm.find({'user_id': user_id, 'status': 'active'}))
    active_group_ids = [m['group_id'] for m in user_memberships]
    leader_group_ids = [m['group_id'] for m in user_memberships if m['role'] in ['leader', 'co-leader']]

    # Get all pending loans in user's active groups
    all_pending = list(loans.find({'group_id': {'$in': active_group_ids}, 'status': 'pending'}))
    pending_loans = []

    for loan in all_pending:
        amount = loan.get('amount', 0)
        group_id = loan['group_id']
        
        # Determine if user is authorized to approve this pending loan
        is_authorized = False
        if amount > 50000:
            # All active members must approve
            is_authorized = True
        else:
            # Only leaders/co-leaders can approve
            if group_id in leader_group_ids:
                is_authorized = True

        if is_authorized:
            group = groups.find_one({'group_id': group_id})
            p = profiles.find_one({'user_id': loan['user_id']})
            
            # Robust extraction of approved list
            approved_by = loan.get('approved_by', [])
            if isinstance(approved_by, str):
                approved_by = [approved_by] if approved_by else []
            elif not isinstance(approved_by, list):
                approved_by = []
                
            has_approved = user_id in approved_by
            total_active_members = gm.count_documents({'group_id': group_id, 'status': 'active'})
            approvals_count = len(approved_by)

            pending_loans.append({
                'loan': loan,
                'group': group,
                'profile': p,
                'has_approved': has_approved,
                'total_active': total_active_members,
                'approvals_count': approvals_count,
                'approved_list': approved_by,
                'is_leader': group_id in leader_group_ids
            })

    # Get all completed loans for the groups the user is in
    completed_loans_raw = list(loans.find({
        'group_id': {'$in': active_group_ids},
        'status': 'completed'
    }).sort('created_at', -1))
    completed_loans_history = []
    for loan in completed_loans_raw:
        group = groups.find_one({'group_id': loan['group_id']})
        p = profiles.find_one({'user_id': loan['user_id']})
        loan_fines = list(if_col.find({'group_id': loan['group_id'], 'user_id': loan['user_id']}))
        completed_loans_history.append({
            'loan': loan,
            'group': group,
            'profile': p,
            'fines': loan_fines,
            'total_fines': sum(f.get('amount', 0) for f in loan_fines)
        })

    # Paginate completed loans history by 4 items per page
    from django.core.paginator import Paginator
    paginator = Paginator(completed_loans_history, 4)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'loans/loan_list.html', {
        'loan_data': loan_data, 
        'pending_loans': pending_loans,
        'completed_loans_history': page_obj,
    })


@login_required_custom
def loan_request_view(request, group_id):
    """Request a loan from a group."""
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

    balance = get_group_balance(group_id)

    if request.method == 'POST':
        import os
        import uuid
        from django.conf import settings

        amount = float(request.POST.get('amount', 0))
        tenure = int(request.POST.get('tenure', 1))
        mortgage = request.POST.get('mortgage', '').strip()

        loans = get_collection('loans')
        if loans.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'pending'}):
            messages.warning(request, 'You already have a pending loan request.')
            return redirect('loan_list')

        if amount <= 0:
            messages.error(request, 'Invalid loan amount.')
            return render(request, 'loans/loan_request.html', {'group': group, 'balance': balance})

        if amount > balance:
            messages.error(request, f'Insufficient group balance. Available: ₹{balance:,.2f}')
            return render(request, 'loans/loan_request.html', {'group': group, 'balance': balance})

        signed_doc_path = ''
        guarantor_name = ''
        guarantor_mobile = ''
        guarantor_address = ''

        if amount > 50000:
            guarantor_name = request.POST.get('guarantor_name', '').strip()
            guarantor_mobile = request.POST.get('guarantor_mobile', '').strip()
            guarantor_address = request.POST.get('guarantor_address', '').strip()
            agree_terms = request.POST.get('agree_guarantor_terms', '').strip()

            if not guarantor_name or not guarantor_mobile or not guarantor_address or agree_terms != 'yes':
                messages.error(request, 'All guarantor details must be provided and terms must be agreed for loans > ₹50,000.')
                return render(request, 'loans/loan_request.html', {'group': group, 'balance': balance})

            if len(guarantor_mobile) != 10 or not guarantor_mobile.isdigit():
                messages.error(request, 'Please provide a valid 10-digit mobile number for the guarantor.')
                return render(request, 'loans/loan_request.html', {'group': group, 'balance': balance})

            if 'signed_doc' not in request.FILES:
                messages.error(request, 'Please upload a signed loan document.')
                return render(request, 'loans/loan_request.html', {'group': group, 'balance': balance})

            # Save uploaded document
            doc = request.FILES['signed_doc']
            ext = os.path.splitext(doc.name)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'signed_docs')
            os.makedirs(upload_dir, exist_ok=True)
            with open(os.path.join(upload_dir, filename), 'wb+') as f:
                for chunk in doc.chunks():
                    f.write(chunk)
            signed_doc_path = f"signed_docs/{filename}"

        interest = calculate_simple_interest(amount, group['interest_rate'], tenure)
        total_repayment = amount + interest

        loans = get_collection('loans')
        loan_data = {
            'group_id': group_id, 'user_id': user_id,
            'amount': amount, 'interest_rate': group['interest_rate'],
            'tenure_months': tenure, 'interest_amount': interest,
            'total_repayment': total_repayment,
            'remaining_amount': amount,
            'interest_paid': 0.0,
            'mortgage_details': mortgage, 'status': 'pending',
            'signed_doc_path': signed_doc_path,
            'guarantor_name': guarantor_name,
            'guarantor_mobile': guarantor_mobile,
            'guarantor_address': guarantor_address,
            'created_at': datetime.now(), 'updated_at': datetime.now(),
        }
        loans.insert_one(loan_data)

        leaders = list(gm.find({'group_id': group_id, 'role': {'$in': ['leader', 'co-leader']}}))
        profile = get_user_profile(user_id)
        for leader in leaders:
            create_notification(
                leader['user_id'], 'Loan Request',
                f'{profile.get("full_name", "A member")} requested ₹{amount:,.2f} loan.',
                'warning', group_id
            )

        # Notify all members
        all_members = list(gm.find({'group_id': group_id, 'status': 'active'}))
        for m in all_members:
            if m['user_id'] != user_id and m['user_id'] not in [l['user_id'] for l in leaders]:
                create_notification(
                    m['user_id'], 'Loan Request',
                    f'A loan request of ₹{amount:,.2f} has been made in {group["name"]}.',
                    'info', group_id
                )

        messages.success(request, 'Loan request submitted!')
        return redirect('loan_list')

    return render(request, 'loans/loan_request.html', {'group': group, 'balance': balance})


@login_required_custom
def loan_approve_view(request, loan_id):
    """Approve a loan request."""
    user_id = request.session['user_id']
    loans = get_collection('loans')
    loan = loans.find_one({'_id': ObjectId(loan_id)})
    if not loan:
        messages.error(request, 'Loan not found.')
        return redirect('loan_list')

    amount = loan.get('amount', 0)
    gm = get_collection('group_members')

    # Authorization Check
    if amount > 50000:
        # Any active member of the group can approve
        membership = gm.find_one({'group_id': loan['group_id'], 'user_id': user_id, 'status': 'active'})
        if not membership:
            messages.error(request, 'Permission denied. Only active group members can approve this loan.')
            return redirect('loan_list')
    else:
        # Only leader/co-leader can approve
        membership = gm.find_one({
            'group_id': loan['group_id'], 'user_id': user_id,
            'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'
        })
        if not membership:
            messages.error(request, 'Permission denied. Only leaders or co-leaders can approve this loan.')
            return redirect('loan_list')

    # Get already approved list
    approved_by = loan.get('approved_by', [])
    if isinstance(approved_by, str):
        approved_by = [approved_by] if approved_by else []
    elif not isinstance(approved_by, list):
        approved_by = []

    if user_id in approved_by:
        messages.warning(request, 'You have already approved this loan request.')
        return redirect('loan_list')

    # Record current user's approval
    approved_by.append(user_id)

    # Check if fully approved
    is_fully_approved = False
    if amount > 50000:
        total_active = gm.count_documents({'group_id': loan['group_id'], 'status': 'active'})
        if len(approved_by) >= total_active:
            is_fully_approved = True
    else:
        # For loans <= 50,000, 1 leader approval is sufficient
        is_fully_approved = True

    if is_fully_approved:
        # Disburse the loan
        balance = get_group_balance(loan['group_id'])
        if loan['amount'] > balance:
            messages.error(request, 'Insufficient group balance to disburse this loan.')
            return redirect('loan_list')

        loans.update_one(
            {'_id': ObjectId(loan_id)},
            {'$set': {'status': 'approved', 'approved_by': approved_by, 'approved_at': datetime.now()}}
        )

        txns = get_collection('transactions')
        txns.insert_one({
            'group_id': loan['group_id'], 'user_id': loan['user_id'],
            'type': 'loan_disbursement', 'amount': -loan['amount'],
            'description': f'Loan disbursed: ₹{loan["amount"]:,.2f}',
            'created_at': datetime.now(),
        })

        create_notification(
            loan['user_id'], 'Loan Approved',
            f'Your loan of ₹{loan["amount"]:,.2f} has been fully approved by all members and disbursed!',
            'success', loan['group_id']
        )
        borrower_profile = get_user_profile(loan['user_id'])
        notify_group_members(
            loan['group_id'], 'Loan Disbursed',
            f'A loan of ₹{loan["amount"]:,.2f} has been disbursed to {borrower_profile.get("full_name", "a member")} after unanimous approval.',
            'success', exclude_user_id=loan['user_id']
        )
        messages.success(request, 'Loan fully approved and disbursed!')
    else:
        # Partially approved
        loans.update_one(
            {'_id': ObjectId(loan_id)},
            {'$set': {'approved_by': approved_by}}
        )
        total_active = gm.count_documents({'group_id': loan['group_id'], 'status': 'active'})
        messages.success(request, f'Your approval has been recorded! ({len(approved_by)} of {total_active} members have approved).')

    return redirect('loan_list')


@login_required_custom
def loan_reject_view(request, loan_id):
    """Reject a loan request."""
    user_id = request.session['user_id']
    loans = get_collection('loans')
    loan = loans.find_one({'_id': ObjectId(loan_id)})
    if not loan:
        messages.error(request, 'Loan not found.')
        return redirect('loan_list')

    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': loan['group_id'], 'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('loan_list')

    loans.update_one({'_id': ObjectId(loan_id)}, {'$set': {'status': 'rejected'}})
    create_notification(
        loan['user_id'], 'Loan Rejected',
        f'Your loan request of ₹{loan["amount"]:,.2f} was rejected.',
        'danger', loan['group_id']
    )

    messages.success(request, 'Loan rejected.')
    return redirect('loan_list')


@login_required_custom
def emi_payment_view(request, group_id):
    """Record an EMI payment request."""
    user_id = request.session['user_id']
    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership:
        messages.error(request, 'Not a member.')
        return redirect('my_groups')

    groups = get_collection('groups')
    group = groups.find_one({'group_id': group_id})

    if request.method == 'POST':
        # Block payment if it's not the specific EMI day of the month
        if datetime.now().day != group.get('emi_date', 1):
            messages.error(request, f'EMI payments are only allowed on the scheduled EMI day (Day {group.get("emi_date", 1)}).')
            return redirect('group_detail', group_id=group_id)

        amount = float(request.POST.get('amount', 0))
        if amount <= 0:
            messages.error(request, 'Invalid amount.')
            return redirect('group_detail', group_id=group_id)

        total_amount = amount

        emi_reqs = get_collection('emi_requests')
        if emi_reqs.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'pending'}):
            messages.warning(request, 'You already have a pending EMI payment request.')
            return redirect('group_detail', group_id=group_id)

        profile = get_user_profile(user_id)
        
        emi_reqs.insert_one({
            'group_id': group_id, 'user_id': user_id,
            'member_name': profile.get('full_name', 'Unknown'),
            'emi_amount': amount, 'fine_amount': 0.0,
            'total_amount': total_amount, 'status': 'pending',
            'created_at': datetime.now(),
        })

        leaders = list(gm.find({'group_id': group_id, 'role': {'$in': ['leader', 'co-leader']}}))
        for leader in leaders:
            create_notification(
                leader['user_id'], 'EMI Payment Request',
                f'{profile.get("full_name", "A member")} has submitted an EMI payment of ₹{total_amount:,.2f}.',
                'info', group_id
            )

        messages.success(request, 'EMI payment request submitted to leaders for approval.')
        return redirect('group_detail', group_id=group_id)

    return redirect('group_detail', group_id=group_id)


@login_required_custom
def approve_emi_request(request, request_id):
    """Approve an EMI payment request."""
    user_id = request.session['user_id']
    emi_reqs = get_collection('emi_requests')
    emi_req = emi_reqs.find_one({'_id': ObjectId(request_id)})
    if not emi_req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': emi_req['group_id'], 'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('my_groups')

    emi_reqs.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'approved'}})

    txns = get_collection('transactions')
    txns.insert_one({
        'group_id': emi_req['group_id'], 'user_id': emi_req['user_id'],
        'type': 'emi_payment', 'amount': emi_req['total_amount'],
        'description': f'EMI payment: ₹{emi_req["total_amount"]:,.2f}',
        'created_at': datetime.now(),
    })

    emi_records = get_collection('emi_records')
    emi_records.insert_one({
        'group_id': emi_req['group_id'], 'user_id': emi_req['user_id'],
        'amount': emi_req['total_amount'], 'payment_date': datetime.now(),
        'status': 'paid',
    })

    create_notification(
        emi_req['user_id'], 'EMI Payment Approved',
        f'Your EMI payment of ₹{emi_req["total_amount"]:,.2f} has been approved!',
        'success', emi_req['group_id']
    )
    notify_group_members(
        emi_req['group_id'], 'EMI Collected',
        f'{emi_req.get("member_name", "A member")} paid an EMI of ₹{emi_req["total_amount"]:,.2f}.',
        'success', exclude_user_id=emi_req['user_id']
    )
    messages.success(request, 'EMI payment approved!')
    return redirect('group_detail', group_id=emi_req['group_id'])


@login_required_custom
def reject_emi_request(request, request_id):
    """Reject an EMI payment request."""
    user_id = request.session['user_id']
    emi_reqs = get_collection('emi_requests')
    emi_req = emi_reqs.find_one({'_id': ObjectId(request_id)})
    if not emi_req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': emi_req['group_id'], 'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('my_groups')

    emi_reqs.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'rejected'}})

    create_notification(
        emi_req['user_id'], 'EMI Payment Rejected',
        f'Your EMI payment of ₹{emi_req["total_amount"]:,.2f} was rejected.',
        'danger', emi_req['group_id']
    )

    messages.success(request, 'EMI payment rejected.')
    return redirect('group_detail', group_id=emi_req['group_id'])


@login_required_custom
def loan_repay_view(request, loan_id):
    """Submit a loan repayment request for leader approval."""
    user_id = request.session['user_id']
    loans = get_collection('loans')
    loan = loans.find_one({'_id': ObjectId(loan_id), 'user_id': user_id})
    if not loan:
        messages.error(request, 'Loan not found.')
        return redirect('loan_list')

    if request.method == 'POST':
        repayment_reqs = get_collection('repayment_requests')
        if repayment_reqs.find_one({'loan_id': ObjectId(loan_id), 'status': 'pending'}):
            messages.warning(request, 'You already have a pending repayment request for this loan.')
            return redirect('loan_list')

        repay_type = request.POST.get('repay_type', 'principal').strip()
        profile = get_user_profile(user_id)
        
        if repay_type == 'principal':
            principal_amount = float(request.POST.get('principal_amount', 0))
            if principal_amount <= 0 or principal_amount > loan['remaining_amount']:
                messages.error(request, 'Invalid principal amount.')
                return redirect('loan_list')
                
            interest_amount = 0.0
            total_amount = principal_amount
            
            repayment_reqs.insert_one({
                'group_id': loan['group_id'], 'user_id': user_id, 'loan_id': ObjectId(loan_id),
                'member_name': profile.get('full_name', 'Unknown'),
                'type': 'principal', 'principal_amount': principal_amount,
                'interest_amount': interest_amount, 'total_amount': total_amount,
                'status': 'pending', 'created_at': datetime.now(),
            })
            
            # Notify leaders
            gm = get_collection('group_members')
            leaders = list(gm.find({'group_id': loan['group_id'], 'role': {'$in': ['leader', 'co-leader']}}))
            for leader in leaders:
                create_notification(
                    leader['user_id'], 'Loan Principal Repayment Request',
                    f'{profile.get("full_name", "A member")} requested to pay ₹{principal_amount:,.2f} Principal.',
                    'info', loan['group_id']
                )
                
            messages.success(request, f'Principal repayment request of ₹{principal_amount:,.2f} submitted to leaders for approval.')
            
        elif repay_type == 'interest':
            interest_amount = float(request.POST.get('interest_amount', 0))
            if interest_amount <= 0:
                messages.error(request, 'Invalid interest amount.')
                return redirect('loan_list')
                
            repayment_reqs.insert_one({
                'group_id': loan['group_id'], 'user_id': user_id, 'loan_id': ObjectId(loan_id),
                'member_name': profile.get('full_name', 'Unknown'),
                'type': 'interest', 'principal_amount': 0.0,
                'interest_amount': interest_amount, 'total_amount': interest_amount,
                'status': 'pending', 'created_at': datetime.now(),
            })
            
            # Notify leaders
            gm = get_collection('group_members')
            leaders = list(gm.find({'group_id': loan['group_id'], 'role': {'$in': ['leader', 'co-leader']}}))
            for leader in leaders:
                create_notification(
                    leader['user_id'], 'Loan Interest Repayment Request',
                    f'{profile.get("full_name", "A member")} requested to pay ₹{interest_amount:,.2f} Interest.',
                    'info', loan['group_id']
                )
                
            messages.success(request, f'Interest repayment request of ₹{interest_amount:,.2f} submitted to leaders for approval.')
            
        return redirect('loan_list')
        
    return redirect('loan_list')


@login_required_custom
def approve_repayment_request(request, request_id):
    """Approve a loan repayment request."""
    user_id = request.session['user_id']
    repayment_reqs = get_collection('repayment_requests')
    req = repayment_reqs.find_one({'_id': ObjectId(request_id)})
    if not req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': req['group_id'], 'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('my_groups')

    # Update request status
    repayment_reqs.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'approved'}})

    # Load and update the loan
    loans = get_collection('loans')
    loan = loans.find_one({'_id': req['loan_id']})
    if loan:
        new_remaining = loan['remaining_amount'] - req['principal_amount']
        # Status becomes completed if remaining principal is 0
        status = 'completed' if new_remaining <= 0 else loan['status']
        
        loans.update_one(
            {'_id': req['loan_id']},
            {
                '$set': {'remaining_amount': max(0, new_remaining), 'status': status, 'updated_at': datetime.now()},
                '$inc': {'interest_paid': req['interest_amount']}
            }
        )

        # Log transactions
        txns = get_collection('transactions')
        if req['principal_amount'] > 0:
            txns.insert_one({
                'group_id': req['group_id'], 'user_id': req['user_id'],
                'type': 'loan_repayment', 'amount': req['principal_amount'],
                'description': f'Loan principal repayment: ₹{req["principal_amount"]:,.2f}',
                'created_at': datetime.now(),
            })
            
        if req['interest_amount'] > 0:
            txns.insert_one({
                'group_id': req['group_id'], 'user_id': req['user_id'],
                'type': 'interest_payment', 'amount': req['interest_amount'],
                'description': f'Loan interest payment: ₹{req["interest_amount"]:,.2f}',
                'created_at': datetime.now(),
            })

        if status == 'completed':
            create_notification(req['user_id'], 'Loan Completed', 'Your loan has been fully repaid!', 'success', req['group_id'])

    create_notification(
        req['user_id'], 'Repayment Approved',
        f'Your repayment request of ₹{req["total_amount"]:,.2f} has been approved!',
        'success', req['group_id']
    )
    notify_group_members(
        req['group_id'], 'Loan Repayment Received',
        f'{req.get("member_name", "A member")} repaid ₹{req["total_amount"]:,.2f} of their loan.',
        'success', exclude_user_id=req['user_id']
    )
    messages.success(request, 'Repayment request approved and balance updated!')
    return redirect('group_detail', group_id=req['group_id'])


@login_required_custom
def reject_repayment_request(request, request_id):
    """Reject a loan repayment request."""
    user_id = request.session['user_id']
    repayment_reqs = get_collection('repayment_requests')
    req = repayment_reqs.find_one({'_id': ObjectId(request_id)})
    if not req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({
        'group_id': req['group_id'], 'user_id': user_id,
        'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'
    })
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('my_groups')

    repayment_reqs.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'rejected'}})

    create_notification(
        req['user_id'], 'Repayment Rejected',
        f'Your repayment request of ₹{req["total_amount"]:,.2f} was rejected.',
        'danger', req['group_id']
    )

    messages.success(request, 'Repayment request rejected.')
    return redirect('group_detail', group_id=req['group_id'])


@login_required_custom
def extend_loan_request_view(request, loan_id):
    user_id = request.session['user_id']
    loans = get_collection('loans')
    loan = loans.find_one({'_id': ObjectId(loan_id)})
    if not loan or loan['status'] not in ['approved', 'active']:
        messages.error(request, 'Loan not found or not active.')
        return redirect('loan_list')

    group_id = loan['group_id']
    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'status': 'active'})
    if not membership:
        messages.error(request, 'You must be an active member of the group.')
        return redirect('group_detail', group_id=group_id)

    if request.method == 'POST':
        extend_reqs = get_collection('loan_extension_requests')
        if extend_reqs.find_one({'loan_id': str(loan_id), 'status': 'pending'}):
            messages.warning(request, 'You already have a pending loan extension request.')
            return redirect('loan_list')

        extra_months = int(request.POST.get('extra_months', 0))
        if extra_months <= 0:
            messages.error(request, 'Invalid number of months.')
            return redirect('loan_list')

        extend_reqs = get_collection('loan_extension_requests')
        profile = get_user_profile(user_id)
        
        # Determine if consensus is reached immediately (e.g. only 1 leader)
        total_leaders = gm.count_documents({'group_id': group_id, 'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'})
        
        extend_reqs.insert_one({
            'group_id': group_id,
            'user_id': user_id,
            'loan_id': loan_id,
            'member_name': profile.get('full_name', 'Unknown'),
            'extra_months': extra_months,
            'status': 'pending',
            'approved_by': [],
            'created_at': datetime.now(),
        })

        # Notify leaders
        leaders = list(gm.find({'group_id': group_id, 'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'}))
        for leader in leaders:
            create_notification(
                leader['user_id'], 'Loan Extension Request',
                f'{profile.get("full_name")} has requested to extend their loan tenure by {extra_months} months.',
                'info', group_id
            )

        messages.success(request, 'Loan extension request submitted successfully!')
        return redirect('loan_list')

    return redirect('loan_list')

@login_required_custom
def approve_extend_loan_view(request, request_id):
    user_id = request.session['user_id']
    extend_reqs = get_collection('loan_extension_requests')
    req = extend_reqs.find_one({'_id': ObjectId(request_id)})
    if not req or req['status'] != 'pending':
        messages.error(request, 'Request not found or not pending.')
        return redirect('my_groups')

    group_id = req['group_id']
    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': group_id, 'user_id': user_id, 'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'})
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('group_detail', group_id=group_id)

    approved_by = req.get('approved_by', [])
    if user_id in approved_by:
        messages.warning(request, 'You have already approved this.')
        return redirect('group_detail', group_id=group_id)

    approved_by.append(user_id)
    total_leaders = gm.count_documents({'group_id': group_id, 'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'})
    
    if len(approved_by) >= total_leaders:
        extend_reqs.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'approved', 'approved_by': approved_by}})
        
        loans = get_collection('loans')
        loan = loans.find_one({'_id': ObjectId(req['loan_id'])})
        if loan:
            groups = get_collection('groups')
            group = groups.find_one({'group_id': group_id})
            
            new_tenure = loan['tenure_months'] + req['extra_months']
            new_interest = calculate_simple_interest(loan['amount'], group['interest_rate'], new_tenure)
            new_total_repayment = loan['amount'] + new_interest
            
            loans.update_one({'_id': ObjectId(req['loan_id'])}, {
                '$set': {
                    'tenure_months': new_tenure,
                    'interest_amount': new_interest,
                    'total_repayment': new_total_repayment
                }
            })
            
            create_notification(
                req['user_id'], 'Loan Extension Approved',
                f'Your request to extend loan tenure by {req["extra_months"]} months was approved. New interest is calculated.',
                'success', group_id
            )
        messages.success(request, 'Loan extension fully approved.')
    else:
        extend_reqs.update_one({'_id': ObjectId(request_id)}, {'$set': {'approved_by': approved_by}})
        messages.success(request, f'Approval recorded! ({len(approved_by)} of {total_leaders} leaders approved).')

    return redirect('group_detail', group_id=group_id)

@login_required_custom
def reject_extend_loan_view(request, request_id):
    user_id = request.session['user_id']
    extend_reqs = get_collection('loan_extension_requests')
    req = extend_reqs.find_one({'_id': ObjectId(request_id)})
    if not req:
        messages.error(request, 'Request not found.')
        return redirect('my_groups')

    gm = get_collection('group_members')
    membership = gm.find_one({'group_id': req['group_id'], 'user_id': user_id, 'role': {'$in': ['leader', 'co-leader']}, 'status': 'active'})
    if not membership:
        messages.error(request, 'Permission denied.')
        return redirect('my_groups')

    extend_reqs.update_one({'_id': ObjectId(request_id)}, {'$set': {'status': 'rejected'}})

    create_notification(
        req['user_id'], 'Loan Extension Rejected',
        f'Your loan extension request was rejected by leadership.',
        'danger', req['group_id']
    )

    messages.success(request, 'Loan extension request rejected.')
    return redirect('group_detail', group_id=req['group_id'])
