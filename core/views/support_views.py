"""
Support Ticketing System Views.
"""
import os
import uuid
from datetime import datetime
from bson import ObjectId
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from core.db import get_collection
from core.views.admin_views import admin_required

def handle_image_upload(request, file_key='image'):
    """Handles image upload and validation."""
    if file_key not in request.FILES:
        return None, None
        
    img = request.FILES[file_key]
    if img.size > 1024 * 1024:  # 1MB limit
        return None, "Screenshot size must be less than 1MB."
        
    ext = os.path.splitext(img.name)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png']:
        return None, "Only JPG and PNG images are allowed."
        
    filename = f"ticket_{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.MEDIA_ROOT, 'tickets', filename)
    with open(path, 'wb+') as dest:
        for chunk in img.chunks():
            dest.write(chunk)
            
    return f"tickets/{filename}", None

def login_required(view_func):
    """Simple decorator to ensure user is logged in."""
    from functools import wraps
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
def my_tickets_view(request):
    """Customer: View all their tickets."""
    user_id = request.session.get('user_id')
    tickets_col = get_collection('tickets')
    tickets = list(tickets_col.find({'user_id': user_id}).sort('created_at', -1))
    
    return render(request, 'support/my_tickets.html', {'tickets': tickets})

@login_required
def create_ticket_view(request):
    """Customer: Create a new support ticket."""
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip()
        member_id = request.POST.get('member_id', '').strip()
        mobile_number = request.POST.get('mobile_number', '').strip()
        
        if not subject or not description or not member_id or not mobile_number:
            messages.error(request, 'Subject, description, Member ID, and Mobile are required.')
            return redirect('create_ticket')
            
        img_path, error = handle_image_upload(request, 'screenshot')
        if error:
            messages.error(request, error)
            return redirect('create_ticket')
            
        user_id = request.session.get('user_id')
        
        ticket = {
            'user_id': user_id,
            'member_id': member_id,
            'mobile': mobile_number,
            'subject': subject,
            'status': 'open',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'messages': [
                {
                    'sender_role': 'customer',
                    'sender_id': user_id,
                    'text': description,
                    'image': img_path,
                    'timestamp': datetime.now()
                }
            ]
        }
        
        tickets_col = get_collection('tickets')
        tickets_col.insert_one(ticket)
        messages.success(request, 'Your support ticket has been submitted successfully.')
        return redirect('my_tickets')
        
    return render(request, 'support/create_ticket.html')

@login_required
def ticket_chat_view(request, ticket_id):
    """View and reply to a specific ticket. Shared by customer and staff/admin."""
    user_id = request.session.get('user_id')
    users_col = get_collection('users')
    user = users_col.find_one({'_id': ObjectId(user_id)})
    
    is_staff = user.get('is_admin', False) or user.get('role') == 'tech_staff'
    
    tickets_col = get_collection('tickets')
    ticket = tickets_col.find_one({'_id': ObjectId(ticket_id)})
    
    if not ticket:
        messages.error(request, 'Ticket not found.')
        return redirect('dashboard')
        
    # Ensure customers can only see their own tickets
    if not is_staff and ticket.get('user_id') != user_id:
        messages.error(request, 'Unauthorized access.')
        return redirect('my_tickets')
        
    if request.method == 'POST':
        reply_text = request.POST.get('reply', '').strip()
        new_status = request.POST.get('status') # Staff can update status
        
        img_path, error = handle_image_upload(request, 'screenshot')
        if error:
            messages.error(request, error)
            return redirect('ticket_chat', ticket_id=ticket_id)
            
        update_data = {'$set': {'updated_at': datetime.now()}}
        
        if reply_text or img_path:
            # Determine precise sender role
            if user.get('is_admin', False):
                role = 'admin'
            elif user.get('role') == 'tech_staff':
                role = 'staff'
            else:
                role = 'customer'
                
            msg = {
                'sender_role': role,
                'sender_id': user_id,
                'text': reply_text,
                'image': img_path,
                'timestamp': datetime.now()
            }
            if '$push' not in update_data:
                update_data['$push'] = {}
            update_data['$push']['messages'] = msg
            
        if is_staff and new_status and new_status in ['open', 'in_progress', 'resolved', 'escalated']:
            update_data['$set']['status'] = new_status
            
        tickets_col.update_one({'_id': ObjectId(ticket_id)}, update_data)
        messages.success(request, 'Ticket updated successfully.')
        return redirect('ticket_chat', ticket_id=ticket_id)
        
    return render(request, 'support/ticket_chat.html', {
        'ticket': ticket,
        'is_staff': is_staff,
        'current_user_id': user_id
    })

@admin_required
def admin_tickets_view(request):
    """Staff/Admin: List all tickets."""
    tickets_col = get_collection('tickets')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search', '').strip()
    
    query = {}
    if status_filter and status_filter in ['open', 'in_progress', 'resolved', 'escalated']:
        query['status'] = status_filter
        
    if search_query:
        query['$or'] = [
            {'mobile': {'$regex': search_query, '$options': 'i'}},
            {'member_id': {'$regex': search_query, '$options': 'i'}}
        ]
        
    tickets = list(tickets_col.find(query).sort('updated_at', -1))
    
    return render(request, 'admin/admin_tickets.html', {
        'tickets': tickets,
        'current_status': status_filter,
        'search_query': search_query
    })

@admin_required
def staff_create_escalation_view(request):
    """Staff/Admin: Create a ticket directly assigned to admin."""
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip()
        customer_mobile = request.POST.get('customer_mobile', '').strip()
        
        if not subject or not description:
            messages.error(request, 'Subject and description are required.')
            return redirect('staff_dashboard')
            
        img_path, err = handle_image_upload(request)
        if err:
            messages.error(request, err)
            return redirect('staff_dashboard')
            
        users_col = get_collection('users')
        staff_id = request.session.get('user_id')
        staff_user = users_col.find_one({'_id': ObjectId(staff_id)})
        
        target_user_id = staff_id
        
        if customer_mobile:
            customer = users_col.find_one({'phone': customer_mobile})
            if not customer:
                messages.error(request, f'No customer found with mobile {customer_mobile}.')
                return redirect('staff_dashboard')
            target_user_id = str(customer['_id'])
            
        is_super_admin = staff_user.get('is_admin', False)
        
        ticket = {
            'user_id': target_user_id,
            'subject': subject,
            'status': 'escalated',
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'messages': [
                {
                    'sender_role': 'admin' if is_super_admin else 'staff',
                    'sender_id': staff_id,
                    'text': description,
                    'image': img_path,
                    'timestamp': datetime.now()
                }
            ]
        }
        
        tickets_col = get_collection('tickets')
        result = tickets_col.insert_one(ticket)
        messages.success(request, 'Escalation ticket created successfully!')
        return redirect('ticket_chat', ticket_id=str(result.inserted_id))
        
    return redirect('staff_dashboard')
