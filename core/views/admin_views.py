"""
Admin views for GroupSathi custom MongoDB Admin Dashboard.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from functools import wraps
from datetime import datetime
from core.db import get_collection

def admin_required(view_func):
    """Decorator to ensure the user is an admin."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            messages.error(request, 'Please login to access the admin panel.')
            return redirect('login')
        
        users = get_collection('users')
        from bson import ObjectId
        user = users.find_one({'_id': ObjectId(user_id)})
        
        # Check if is_admin is True or role is tech_staff
        if not user or (not user.get('is_admin', False) and user.get('role') != 'tech_staff'):
            messages.error(request, 'You do not have permission to access the admin panel.')
            return redirect('dashboard')
            
        request.admin_user = user
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def super_admin_required(view_func):
    """Decorator to ensure the user is a super admin (not just tech staff)."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('login')
        
        users = get_collection('users')
        from bson import ObjectId
        user = users.find_one({'_id': ObjectId(user_id)})
        
        if not user or not user.get('is_admin', False):
            messages.error(request, 'Super admin privileges required.')
            return redirect('custom_admin_dashboard')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@admin_required
def admin_dashboard_view(request):
    """Custom admin dashboard overview."""
    users = get_collection('users')
    groups = get_collection('groups')
    loans = get_collection('loans')
    
    total_users = users.count_documents({})
    total_groups = groups.count_documents({})
    total_loans = loans.count_documents({})
    active_loans = loans.count_documents({'status': {'$in': ['approved', 'active']}})
    
    # Get technical staff for maintenance modal
    technical_staff = list(users.find({'role': 'tech_staff'}))
    
    context = {
        'total_users': total_users,
        'total_groups': total_groups,
        'total_loans': total_loans,
        'active_loans': active_loans,
        'technical_staff': technical_staff,
    }
    return render(request, 'admin/admin_dashboard.html', context)

@admin_required
def admin_users_view(request):
    """List all users."""
    users_col = get_collection('users')
    profiles_col = get_collection('profiles')
    
    all_users = list(users_col.find().sort('created_at', -1).limit(100))
    user_list = []
    
    for u in all_users:
        prof = profiles_col.find_one({'user_id': str(u['_id'])})
        u['profile'] = prof
        user_list.append(u)
        
    context = {'users': user_list}
    return render(request, 'admin/admin_users.html', context)

@admin_required
def admin_groups_view(request):
    """List all groups."""
    groups_col = get_collection('groups')
    all_groups = list(groups_col.find().sort('created_at', -1).limit(100))
    
    context = {'groups': all_groups}
    return render(request, 'admin/admin_groups.html', context)


@admin_required
def admin_user_detail_view(request, user_id):
    """Show detailed info about a specific user."""
    from bson import ObjectId
    users_col = get_collection('users')
    profiles_col = get_collection('profiles')
    group_members_col = get_collection('group_members')
    groups_col = get_collection('groups')
    loans_col = get_collection('loans')
    fines_col = get_collection('fines')
    
    user_data = users_col.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        messages.error(request, 'User not found.')
        return redirect('custom_admin_users')
        
    profile_data = profiles_col.find_one({'user_id': user_id})
    
    # Get group memberships
    memberships = list(group_members_col.find({'user_id': user_id}))
    groups = []
    for m in memberships:
        g = groups_col.find_one({'group_id': m['group_id']})
        if g:
            g['member_role'] = m.get('role', 'member')
            groups.append(g)
            
    # Get loans
    loans = list(loans_col.find({'user_id': user_id}))
    
    # Get fines
    fines = list(fines_col.find({'user_id': user_id}))
    
    context = {
        'target_user': user_data,
        'target_profile': profile_data,
        'groups': groups,
        'loans': loans,
        'fines': fines,
        'is_super_admin': request.admin_user.get('is_admin', False)
    }
    return render(request, 'admin/admin_user_detail.html', context)


@super_admin_required
def admin_remove_user_view(request, user_id):
    """Soft delete a user."""
    from bson import ObjectId
    if request.method == 'POST':
        users_col = get_collection('users')
        # Soft delete: set is_active to False
        users_col.update_one({'_id': ObjectId(user_id)}, {'$set': {'is_active': False}})
        messages.success(request, 'User successfully deactivated.')
    return redirect('custom_admin_users')


@admin_required
def admin_user_pdf_view(request, user_id):
    """Generate a PDF report for a specific user's data."""
    from django.http import HttpResponse
    from bson import ObjectId
    import io
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
    except ImportError:
        messages.error(request, "reportlab is not installed.")
        return redirect('custom_admin_users')

    users_col = get_collection('users')
    profiles_col = get_collection('profiles')
    
    user_data = users_col.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        return HttpResponse("User not found", status=404)
        
    profile_data = profiles_col.find_one({'user_id': user_id})
    name = profile_data.get('full_name', 'Unknown') if profile_data else 'Unknown'
    mobile = user_data.get('mobile', 'N/A')

    # Build PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], alignment=1, spaceAfter=20, textColor=colors.HexColor('#0f172a'))
    elements.append(Paragraph(f"User Data Report: {name}", title_style))
    elements.append(Spacer(1, 12))
    
    # Profile Info
    data = [
        ['Mobile Number', mobile],
        ['Full Name', name],
        ['Member ID', profile_data.get('member_id', 'N/A') if profile_data else 'N/A'],
        ['Account Status', 'Active' if user_data.get('is_active') else 'Deactivated'],
        ['Joined At', str(user_data.get('created_at', ''))[:10]]
    ]
    
    t = Table(data, colWidths=[150, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#334155')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1'))
    ]))
    elements.append(t)
    
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="user_report_{mobile}.pdf"'
    return response


@super_admin_required
def admin_add_staff_view(request):
    """Create a new technical staff account."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        name = request.POST.get('name', '').strip()
        
        users_col = get_collection('users')
        if users_col.find_one({'email': email}):
            messages.error(request, 'Email address already registered.')
            return redirect('admin_add_staff')
            
        import bcrypt
        from datetime import datetime
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        import uuid
        user_data = {
            'email': email,
            'mobile': 'staff_' + str(uuid.uuid4())[:8],
            'password': hashed,
            'is_active': True,
            'role': 'tech_staff',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
        }
        res = users_col.insert_one(user_data)
        
        profiles_col = get_collection('profiles')
        from core.utils import generate_member_id
        profile_data = {
            'user_id': str(res.inserted_id),
            'email': email,
            'full_name': name,
            'member_id': generate_member_id(),
            'created_at': datetime.now()
        }
        profiles_col.insert_one(profile_data)
        
        messages.success(request, f'Technical Staff account for {name} created successfully.')
        return redirect('admin_staff_list')
        
    return render(request, 'admin/admin_add_staff.html')


@admin_required
def admin_staff_list_view(request):
    """View to list all technical staff."""
    users_col = get_collection('users')
    profiles_col = get_collection('profiles')
    
    staff_users = list(users_col.find({'role': 'tech_staff'}))
    staff_data = []
    
    for user in staff_users:
        profile = profiles_col.find_one({'user_id': str(user['_id'])})
        name = profile.get('full_name', 'Unknown') if profile else 'Unknown'
        staff_data.append({
            'id': str(user['_id']),
            'email': user.get('email'),
            'name': name,
            'is_active': user.get('is_active', True),
            'created_at': user.get('created_at')
        })
        
    context = {
        'staff_list': staff_data,
        'staff_count': len(staff_data)
    }
    return render(request, 'admin/admin_staff_list.html', context)


@admin_required
def admin_edit_staff_view(request, staff_id):
    """View to edit technical staff details."""
    users_col = get_collection('users')
    profiles_col = get_collection('profiles')
    
    try:
        from bson import ObjectId
        user = users_col.find_one({'_id': ObjectId(staff_id), 'role': 'tech_staff'})
    except Exception as e:
        print(f"ERROR FINDING STAFF: {e}")
        user = None
        
    if not user:
        messages.error(request, 'Staff member not found.')
        return redirect('admin_staff_list')
        
    profile = profiles_col.find_one({'user_id': str(user['_id'])})
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        
        if email != user.get('email'):
            if users_col.find_one({'email': email}):
                messages.error(request, 'Email address already in use.')
                return render(request, 'admin/admin_edit_staff.html', {'staff_user': user, 'staff_profile': profile})
        
        update_user = {'email': email, 'updated_at': datetime.now()}
        
        if password:
            import bcrypt
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            update_user['password'] = hashed
            
        users_col.update_one({'_id': user['_id']}, {'$set': update_user})
        profiles_col.update_one({'user_id': str(user['_id'])}, {'$set': {'full_name': name, 'email': email}})
        
        messages.success(request, f'Staff member {name} updated successfully.')
        return redirect('admin_staff_list')
        
    return render(request, 'admin/admin_edit_staff.html', {
        'staff_user': user,
        'staff_profile': profile
    })


@admin_required
def admin_delete_staff_view(request, staff_id):
    """Delete technical staff."""
    if request.method == 'POST':
        users_col = get_collection('users')
        profiles_col = get_collection('profiles')
        
        try:
            from bson import ObjectId
            user = users_col.find_one({'_id': ObjectId(staff_id), 'role': 'tech_staff'})
        except Exception as e:
            print(f"ERROR DELETING STAFF: {e}")
            user = None
            
        if not user:
            messages.error(request, 'Staff member not found.')
        elif str(user['_id']) == request.session.get('user_id'):
            messages.error(request, 'You cannot delete yourself.')
        else:
            users_col.delete_one({'_id': user['_id']})
            profiles_col.delete_many({'user_id': str(user['_id'])})
            messages.success(request, 'Staff member deleted successfully.')
            
    return redirect('admin_staff_list')


@admin_required
def admin_broadcast_view(request):
    """Send a broadcast notification to all users."""
    if request.method == 'POST':
        title = request.POST.get('title', 'System Broadcast').strip()
        message = request.POST.get('message', '').strip()
        notif_type = request.POST.get('type', 'info')
        
        if message:
            image_path = request.POST.get('generated_image_path')
            
            img = request.FILES.get('image')
            if img:
                import os, uuid
                from django.conf import settings
                ext = os.path.splitext(img.name)[1] if img.name else '.png'
                filename = f"{uuid.uuid4().hex}{ext}"
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'broadcasts')
                os.makedirs(upload_dir, exist_ok=True)
                with open(os.path.join(upload_dir, filename), 'wb+') as f:
                    for chunk in img.chunks():
                        f.write(chunk)
                image_path = f"broadcasts/{filename}"

            users_col = get_collection('users')
            active_users = users_col.find({'is_active': True})
            
            from core.utils import create_notification
            count = 0
            for u in active_users:
                kwargs = {}
                if image_path:
                    kwargs['image_path'] = image_path
                create_notification(str(u['_id']), title, message, notif_type, **kwargs)
                count += 1
                
            messages.success(request, f'Broadcast sent successfully to {count} users.')
            return redirect('custom_admin_dashboard')
            
    return render(request, 'admin/admin_broadcast.html')

@admin_required
def staff_dashboard_view(request):
    """Dedicated dashboard for technical staff to assist customers."""
    if request.method == 'POST':
        search_query = request.POST.get('search_query', '').strip()
        if search_query:
            users_col = get_collection('users')
            user_data = users_col.find_one({'mobile': search_query})
            if user_data:
                return redirect('admin_user_detail', user_id=str(user_data['_id']))
            else:
                messages.error(request, 'No user found with that mobile number.')
                
    return render(request, 'admin/staff_dashboard.html')

@super_admin_required
def admin_edit_user_view(request, user_id):
    """Edit user details (mobile, pin, name)."""
    from bson import ObjectId
    import bcrypt
    from datetime import datetime

    if request.method == 'POST':
        mobile = request.POST.get('mobile', '').strip()
        pin = request.POST.get('pin', '').strip()
        full_name = request.POST.get('full_name', '').strip()

        users_col = get_collection('users')
        profiles_col = get_collection('profiles')

        # Check if mobile exists for another user
        if mobile:
            existing = users_col.find_one({'mobile': mobile, '_id': {'$ne': ObjectId(user_id)}})
            if existing:
                messages.error(request, 'Mobile number already exists for another user.')
                return redirect('admin_user_detail', user_id=user_id)

        update_data = {'updated_at': datetime.now()}
        if mobile:
            update_data['mobile'] = mobile
            
        if pin:
            if len(pin) != 5 or not pin.isdigit():
                messages.error(request, 'PIN must be exactly 5 digits.')
                return redirect('admin_user_detail', user_id=user_id)
            hashed = bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt())
            update_data['password'] = hashed

        users_col.update_one({'_id': ObjectId(user_id)}, {'$set': update_data})

        profile_update = {'updated_at': datetime.now()}
        if full_name:
            profile_update['full_name'] = full_name
        if mobile:
            profile_update['mobile'] = mobile

        profiles_col.update_one({'user_id': str(user_id)}, {'$set': profile_update})

        messages.success(request, 'User details updated successfully.')
        return redirect('admin_user_detail', user_id=user_id)

    return redirect('admin_user_detail', user_id=user_id)


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

@super_admin_required
def admin_chatbot_train_view(request):
    """View to allow admin to provide custom instructions to the chatbot."""
    chatbot_config = get_collection('chatbot_config')
    
    if request.method == 'POST':
        instructions = request.POST.get('instructions', '').strip()
        # Save or update the instructions
        chatbot_config.update_one(
            {'_id': 'config'}, 
            {'$set': {'instructions': instructions}}, 
            upsert=True
        )
        messages.success(request, 'Chatbot instructions updated successfully!')
        return redirect('admin_chatbot_train')
        
    config = chatbot_config.find_one({'_id': 'config'})
    current_instructions = config.get('instructions', '') if config else ''
    
    return render(request, 'admin/admin_chatbot_train.html', {'current_instructions': current_instructions})

@super_admin_required
def admin_db_explorer_view(request):
    """View to list all collections in the MongoDB database."""
    from core.db import get_db
    db = get_db()
    collections = db.list_collection_names()
    collections.sort()
    
    collection_stats = []
    for coll in collections:
        count = db[coll].count_documents({})
        collection_stats.append({'name': coll, 'count': count})
        
    return render(request, 'admin/admin_db_collections.html', {'collections': collection_stats})

@super_admin_required
def admin_db_collection_view(request, collection_name):
    """View to list all documents inside a collection."""
    from core.db import get_db
    import bson.json_util
    db = get_db()
    
    # Simple pagination or limit
    limit = 50
    documents_cursor = db[collection_name].find().sort('_id', -1).limit(limit)
    
    documents = []
    for doc in documents_cursor:
        doc_json = bson.json_util.dumps(doc, indent=2)
        doc_id = str(doc.get('_id', ''))
        documents.append({
            'doc_id': doc_id,
            'json_preview': doc_json[:200] + ('...' if len(doc_json) > 200 else '')
        })
        
    return render(request, 'admin/admin_db_documents.html', {
        'collection_name': collection_name,
        'documents': documents,
        'limit': limit
    })

@super_admin_required
def admin_db_document_edit_view(request, collection_name, doc_id):
    """View to edit a specific document using JSON."""
    from core.db import get_db
    from bson import ObjectId
    import bson.json_util
    import json
    
    db = get_db()
    
    try:
        obj_id = ObjectId(doc_id)
    except Exception:
        # Some collections (like chatbot_config) might use string IDs instead of ObjectIds
        obj_id = doc_id
        
    document = db[collection_name].find_one({'_id': obj_id})
    if not document:
        messages.error(request, 'Document not found.')
        return redirect('admin_db_collection', collection_name=collection_name)
        
    if request.method == 'POST':
        json_data = request.POST.get('json_data', '')
        try:
            # Parse the JSON string back to a Python dict with proper BSON types
            updated_doc = bson.json_util.loads(json_data)
            
            # Ensure the _id remains unchanged
            updated_doc['_id'] = obj_id
            
            # Replace the document in the database
            db[collection_name].replace_one({'_id': obj_id}, updated_doc)
            
            messages.success(request, 'Document updated successfully.')
            return redirect('admin_db_document_edit', collection_name=collection_name, doc_id=doc_id)
        except Exception as e:
            messages.error(request, f'Invalid JSON format or BSON error: {str(e)}')
            
    # Serialize to JSON with 4 spaces indent for editing
    document_json = bson.json_util.dumps(document, indent=4)
    
    return render(request, 'admin/admin_db_document_edit.html', {
        'collection_name': collection_name,
        'doc_id': doc_id,
        'document_json': document_json
    })

@super_admin_required
def admin_db_document_delete_view(request, collection_name, doc_id):
    """View to delete a specific document."""
    from core.db import get_db
    from bson import ObjectId
    
    if request.method == 'POST':
        db = get_db()
        try:
            obj_id = ObjectId(doc_id)
        except Exception:
            obj_id = doc_id
            
        result = db[collection_name].delete_one({'_id': obj_id})
        
        if result.deleted_count > 0:
            messages.success(request, 'Document deleted successfully.')
        else:
            messages.error(request, 'Document not found or already deleted.')
            
    return redirect('admin_db_collection', collection_name=collection_name)

@super_admin_required
def admin_db_document_bulk_delete_view(request, collection_name):
    """View to delete multiple documents at once."""
    from core.db import get_db
    from bson import ObjectId
    
    if request.method == 'POST':
        db = get_db()
        doc_ids = request.POST.getlist('doc_ids')
        
        if not doc_ids:
            messages.warning(request, 'No documents selected for deletion.')
            return redirect('admin_db_collection', collection_name=collection_name)
            
        obj_ids = []
        for doc_id in doc_ids:
            try:
                obj_ids.append(ObjectId(doc_id))
            except Exception:
                obj_ids.append(doc_id)
                
        result = db[collection_name].delete_many({'_id': {'$in': obj_ids}})
        
        if result.deleted_count > 0:
            messages.success(request, f'Successfully deleted {result.deleted_count} document(s).')
        else:
            messages.error(request, 'No documents were deleted. They may have already been removed.')
            
    return redirect('admin_db_collection', collection_name=collection_name)

@admin_required
def admin_maintenance_toggle(request):
    """Toggle maintenance mode settings."""
    if request.method == 'POST':
        is_active = request.POST.get('is_active') == 'on'
        message = request.POST.get('message', '').strip()
        allowed_staff_ids = request.POST.getlist('allowed_staff')
        end_time = request.POST.get('end_time', '').strip()
        
        settings_col = get_collection('system_settings')
        settings_col.update_one(
            {'_id': 'maintenance_mode'},
            {
                '$set': {
                    'is_active': is_active,
                    'message': message,
                    'allowed_staff_ids': allowed_staff_ids,
                    'end_time': end_time,
                    'updated_at': datetime.now()
                }
            },
            upsert=True
        )
        
        if is_active:
            messages.warning(request, 'Maintenance Mode enabled! Only admins and selected staff can log in.')
        else:
            messages.success(request, 'Maintenance Mode disabled. System is open.')
            
    return redirect('custom_admin_dashboard')
