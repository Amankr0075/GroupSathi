"""
Admin views for GroupSathi custom MongoDB Admin Dashboard.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from functools import wraps
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
    
    context = {
        'total_users': total_users,
        'total_groups': total_groups,
        'total_loans': total_loans,
        'active_loans': active_loans,
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
        mobile = request.POST.get('mobile', '').strip()
        password = request.POST.get('password', '').strip()
        name = request.POST.get('name', '').strip()
        
        users_col = get_collection('users')
        if users_col.find_one({'mobile': mobile}):
            messages.error(request, 'Mobile number already registered.')
            return redirect('admin_add_staff')
            
        import bcrypt
        from datetime import datetime
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        user_data = {
            'mobile': mobile,
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
            'mobile': mobile,
            'full_name': name,
            'member_id': generate_member_id(),
            'created_at': datetime.now()
        }
        profiles_col.insert_one(profile_data)
        
        messages.success(request, f'Technical Staff account for {name} created successfully.')
        return redirect('custom_admin_dashboard')
        
    return render(request, 'admin/admin_add_staff.html')


@admin_required
def admin_broadcast_view(request):
    """Send a broadcast notification to all users."""
    if request.method == 'POST':
        title = request.POST.get('title', 'System Broadcast').strip()
        message = request.POST.get('message', '').strip()
        notif_type = request.POST.get('type', 'info')
        
        if message:
            users_col = get_collection('users')
            active_users = users_col.find({'is_active': True})
            
            from core.utils import create_notification
            count = 0
            for u in active_users:
                create_notification(str(u['_id']), title, message, notif_type)
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
