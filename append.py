code = '''
@super_admin_required
def admin_hard_delete_user_view(request, user_id):
    """Permanently delete a user and all related data."""
    if request.method == 'POST':
        from bson import ObjectId
        obj_id = ObjectId(user_id)
        get_collection('users').delete_one({'_id': obj_id})
        get_collection('profiles').delete_one({'user_id': user_id})
        get_collection('group_members').delete_many({'user_id': user_id})
        get_collection('loans').delete_many({'user_id': user_id})
        get_collection('fines').delete_many({'user_id': user_id})
        get_collection('imposed_fines').delete_many({'target_user_id': user_id})
        get_collection('transactions').delete_many({'user_id': user_id})
        get_collection('notifications').delete_many({'user_id': user_id})
        get_collection('tickets').delete_many({'user_id': user_id})
        get_collection('join_requests').delete_many({'user_id': user_id})
        get_collection('leave_requests').delete_many({'user_id': user_id})
        messages.success(request, 'User and all related data permanently deleted.')
    return redirect('custom_admin_users')

@super_admin_required
def admin_hard_delete_group_view(request, group_id):
    """Permanently delete a group and all its related data."""
    if request.method == 'POST':
        get_collection('groups').delete_one({'group_id': group_id})
        get_collection('group_members').delete_many({'group_id': group_id})
        get_collection('loans').delete_many({'group_id': group_id})
        get_collection('fines').delete_many({'group_id': group_id})
        get_collection('imposed_fines').delete_many({'group_id': group_id})
        get_collection('emi_requests').delete_many({'group_id': group_id})
        get_collection('emi_records').delete_many({'group_id': group_id})
        get_collection('transactions').delete_many({'group_id': group_id})
        get_collection('join_requests').delete_many({'group_id': group_id})
        get_collection('leave_requests').delete_many({'group_id': group_id})
        get_collection('loan_extension_requests').delete_many({'group_id': group_id})
        messages.success(request, 'Group and all related data permanently deleted.')
    return redirect('custom_admin_groups')

@super_admin_required
def admin_edit_group_view(request, group_id):
    """Super admin view to edit group details directly."""
    groups_col = get_collection('groups')
    group = groups_col.find_one({'group_id': group_id})
    if not group:
        messages.error(request, 'Group not found.')
        return redirect('custom_admin_groups')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        emi_amount = request.POST.get('emi_amount', '').strip()
        interest_rate = request.POST.get('interest_rate', '').strip()
        emi_date = request.POST.get('emi_date', '').strip()
        fine_amount = request.POST.get('fine_amount', '').strip()
        update_data = {}
        if name: update_data['name'] = name
        if emi_amount: update_data['emi_amount'] = float(emi_amount)
        if interest_rate: update_data['interest_rate'] = float(interest_rate)
        if emi_date: update_data['emi_date'] = int(emi_date)
        if fine_amount: update_data['fine_amount'] = float(fine_amount)
        if update_data:
            from datetime import datetime
            update_data['updated_at'] = datetime.now()
            groups_col.update_one({'group_id': group_id}, {'$set': update_data})
            messages.success(request, 'Group details updated successfully.')
        return redirect('custom_admin_groups')
    return render(request, 'admin/admin_edit_group.html', {'group': group})
'''
with open('core/views/admin_views.py', 'a') as f:
    f.write('\n' + code)
