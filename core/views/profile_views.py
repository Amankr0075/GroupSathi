"""
Profile views for GroupSathi.
"""

import os
import uuid
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from core.decorators import login_required_custom
from core.db import get_collection
from core.utils import generate_member_id, get_user_profile


@login_required_custom
def profile_complete_view(request):
    """Handle profile completion after first login."""
    user_id = request.session['user_id']
    profiles = get_collection('profiles')
    profile = profiles.find_one({'user_id': user_id})

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        gender = request.POST.get('gender', '').strip()
        address = request.POST.get('address', '').strip()
        pin_code = request.POST.get('pin_code', '').strip()

        errors = []
        if not full_name:
            errors.append('Full name is required.')
        if not gender:
            errors.append('Gender is required.')
        if not address:
            errors.append('Address is required.')
        if not pin_code or len(pin_code) != 6 or not pin_code.isdigit():
            errors.append('Valid 6-digit PIN code required.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'profile/complete_profile.html', {
                'profile': profile, 'full_name': full_name,
                'gender': gender, 'address': address, 'pin_code': pin_code,
            })

        photo_path = profile.get('profile_photo', '') if profile else ''
        if 'profile_photo' in request.FILES:
            photo = request.FILES['profile_photo']
            ext = os.path.splitext(photo.name)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            with open(os.path.join(upload_dir, filename), 'wb+') as f:
                for chunk in photo.chunks():
                    f.write(chunk)
            photo_path = f"profiles/{filename}"

        member_id = profile.get('member_id') if profile else None
        if not member_id:
            member_id = generate_member_id()

        profiles.update_one(
            {'user_id': user_id},
            {'$set': {
                'full_name': full_name, 'gender': gender,
                'address': address, 'pin_code': pin_code,
                'profile_photo': photo_path, 'member_id': member_id,
                'updated_at': datetime.now(),
            }},
            upsert=True
        )
        messages.success(request, f'Profile completed! Your Member ID is: {member_id}')
        return redirect('dashboard')

    return render(request, 'profile/complete_profile.html', {'profile': profile})


@login_required_custom
def profile_view(request):
    """View user profile."""
    user_id = request.session['user_id']
    profile = get_user_profile(user_id)
    from bson import ObjectId
    users = get_collection('users')
    user = users.find_one({'_id': ObjectId(user_id)})
    gm = get_collection('group_members')
    groups_count = gm.count_documents({'user_id': user_id, 'status': 'active'})
    return render(request, 'profile/view_profile.html', {
        'profile': profile, 'user': user, 'groups_count': groups_count,
    })


@login_required_custom
def profile_edit_view(request):
    """Edit user profile."""
    user_id = request.session['user_id']
    profiles = get_collection('profiles')
    profile = profiles.find_one({'user_id': user_id})

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        gender = request.POST.get('gender', '').strip()
        address = request.POST.get('address', '').strip()
        pin_code = request.POST.get('pin_code', '').strip()

        if not full_name:
            messages.error(request, 'Full name is required.')
            return render(request, 'profile/edit_profile.html', {'profile': profile})

        photo_path = profile.get('profile_photo', '')
        if 'profile_photo' in request.FILES:
            photo = request.FILES['profile_photo']
            ext = os.path.splitext(photo.name)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            with open(os.path.join(upload_dir, filename), 'wb+') as f:
                for chunk in photo.chunks():
                    f.write(chunk)
            photo_path = f"profiles/{filename}"

        profiles.update_one({'user_id': user_id}, {'$set': {
            'full_name': full_name, 'gender': gender,
            'address': address, 'pin_code': pin_code,
            'profile_photo': photo_path, 'updated_at': datetime.now(),
        }})
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile_view')

    return render(request, 'profile/edit_profile.html', {'profile': profile})
