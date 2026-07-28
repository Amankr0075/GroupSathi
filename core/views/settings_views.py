"""
Settings views for GroupSathi.
"""

import bcrypt
from django.shortcuts import render, redirect
from django.contrib import messages
from bson import ObjectId
from core.decorators import login_required_custom
from core.db import get_collection


@login_required_custom
def settings_view(request):
    """Settings page."""
    return render(request, 'settings/settings.html')


@login_required_custom
def change_password_view(request):
    """Change password."""
    if request.method == 'POST':
        current = request.POST.get('current_password', '').strip()
        new_pass = request.POST.get('new_password', '').strip()
        confirm = request.POST.get('confirm_password', '').strip()

        users = get_collection('users')
        user = users.find_one({'_id': ObjectId(request.session['user_id'])})

        stored_password = user['password']
        if isinstance(stored_password, str):
            stored_password = stored_password.encode('utf-8')

        if not bcrypt.checkpw(current.encode('utf-8'), stored_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('settings')

        if len(new_pass) != 5 or not new_pass.isdigit():
            messages.error(request, 'New password must be exactly 5 digits.')
            return redirect('settings')

        if new_pass != confirm:
            messages.error(request, 'Passwords do not match.')
            return redirect('settings')

        hashed = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt())
        users.update_one({'_id': user['_id']}, {'$set': {'password': hashed}})
        messages.success(request, 'Password changed successfully!')
        return redirect('settings')

    return redirect('settings')
