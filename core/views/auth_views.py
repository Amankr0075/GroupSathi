"""
Authentication views for GroupSathi.
Handles registration, login, logout with MongoDB-backed user storage.
"""

import bcrypt
from datetime import datetime
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from core.db import get_collection
from core.utils import generate_member_id
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)


@ratelimit(key='ip', rate='10/5m', block=True)
def register_view(request):
    """Handle user registration with mobile number and 5-digit numeric password."""
    if request.session.get('user_id'):
        return redirect('dashboard')

    if request.method == 'POST':
        mobile = request.POST.get('mobile', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        # Validation
        errors = []
        if not mobile or len(mobile) != 10 or not mobile.isdigit():
            errors.append('Please enter a valid 10-digit mobile number.')

        if not password or len(password) != 5 or not password.isdigit():
            errors.append('Password must be exactly 5 digits (numeric only).')

        if password != confirm_password:
            errors.append('Passwords do not match.')

        users = get_collection('users')
        if users.find_one({'mobile': mobile}):
            errors.append('This mobile number is already registered.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'auth/register.html', {'mobile': mobile})

        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Create user
        user_data = {
            'mobile': mobile,
            'password': hashed,
            'is_active': True,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
        }
        result = users.insert_one(user_data)
        user_id = str(result.inserted_id)

        # Create empty profile
        profiles = get_collection('profiles')
        profile_data = {
            'user_id': user_id,
            'mobile': mobile,
            'full_name': '',
            'gender': '',
            'address': '',
            'pin_code': '',
            'profile_photo': '',
            'member_id': generate_member_id(),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
        }
        profiles.insert_one(profile_data)

        messages.success(request, 'Registration successful! Please login.')
        return redirect('login')

    return render(request, 'auth/register.html')


@ratelimit(key='ip', rate='10/5m', block=True)
def login_view(request):
    """Handle user login."""
    if request.session.get('user_id'):
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            mobile = request.POST.get('mobile', '').strip()
            password = request.POST.get('password', '').strip()

            users = get_collection('users')
            user = users.find_one({'mobile': mobile})

            if user:
                stored_password = user['password']
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')
                
                try:
                    is_valid = bcrypt.checkpw(password.encode('utf-8'), stored_password)
                except ValueError as e:
                    logger.error(f"Bcrypt error for user {mobile}: {str(e)}")
                    messages.error(request, 'System error verifying credentials.')
                    return render(request, 'auth/login.html')

                if is_valid:
                    if not user.get('is_active', True):
                        messages.error(request, 'Your account has been deactivated.')
                        return render(request, 'auth/login.html')

                    # --- Maintenance Mode Check ---
                    from core.utils import get_maintenance_status
                    maintenance = get_maintenance_status()
                    if maintenance and maintenance.get('is_active'):
                        is_admin = user.get('is_admin', False)
                        allowed_staff = maintenance.get('allowed_staff_ids', [])
                        if not is_admin and str(user['_id']) not in allowed_staff:
                            msg = maintenance.get('message', 'System is under maintenance. Please try again later.')
                            if maintenance.get('end_time'):
                                msg += f" Expected end time: {maintenance['end_time']}."
                            messages.error(request, msg)
                            return render(request, 'auth/login.html')
                    # -----------------------------

                    # Set session
                    request.session['user_id'] = str(user['_id'])
                    request.session['mobile'] = user['mobile']
                    
                    # Force session save to catch SQLite write permission errors early
                    request.session.save()

                    # Update last login
                    users.update_one(
                        {'_id': user['_id']},
                        {'$set': {'last_login': datetime.now()}}
                    )

                    messages.success(request, 'Login successful!')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Invalid mobile number or password.')
            else:
                messages.error(request, 'Invalid mobile number or password.')
                
        except Exception as e:
            logger.exception("Error during normal login process:")
            messages.error(request, f'An unexpected error occurred: {str(e)}')
            return render(request, 'auth/login.html', status=500)

    return render(request, 'auth/login.html')


@ratelimit(key='ip', rate='10/5m', block=True)
def admin_login_view(request):
    """Handle admin and technical staff login via email."""
    if request.session.get('user_id'):
        return redirect('dashboard')

    if request.method == 'POST':
        try:
            import os
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password', '').strip()

            admin_email = os.environ.get('ADMIN_PORTAL_EMAIL')
            admin_password = os.environ.get('ADMIN_PORTAL_PASSWORD')
            
            is_env_admin = False
            if admin_email and admin_password and email == admin_email.lower() and password == admin_password:
                is_env_admin = True

            users = get_collection('users')
            user = users.find_one({'email': email})

            if is_env_admin:
                if not user:
                    import uuid
                    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    user_data = {
                        'email': email,
                        'mobile': 'admin_' + str(uuid.uuid4())[:8],
                        'password': hashed,
                        'is_active': True,
                        'is_admin': True,
                        'role': 'super_admin',
                        'created_at': datetime.now(),
                        'updated_at': datetime.now(),
                    }
                    result = users.insert_one(user_data)
                    user = users.find_one({'_id': result.inserted_id})
                elif not user.get('is_admin'):
                    users.update_one({'_id': user['_id']}, {'$set': {'is_admin': True, 'role': 'super_admin'}})
                    user['is_admin'] = True
                    user['role'] = 'super_admin'

                request.session['user_id'] = str(user['_id'])
                request.session['mobile'] = user.get('mobile', '')
                request.session['email'] = user.get('email', '')

                # Force session save to catch SQLite write permission errors early
                request.session.save()

                users.update_one(
                    {'_id': user['_id']},
                    {'$set': {'last_login': datetime.now()}}
                )

                messages.success(request, 'Staff Login successful!')
                return redirect('custom_admin_dashboard')

            if user:
                stored_password = user['password']
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')
                
                try:
                    is_valid = bcrypt.checkpw(password.encode('utf-8'), stored_password)
                except ValueError as e:
                    logger.error(f"Bcrypt error for user {email}: {str(e)}")
                    messages.error(request, 'System error verifying credentials. Please contact support.')
                    return render(request, 'auth/admin_login.html')

                if is_valid:
                    if not user.get('is_active', True):
                        messages.error(request, 'Your account has been deactivated.')
                        return render(request, 'auth/admin_login.html')

                    # --- Maintenance Mode Check ---
                    from core.utils import get_maintenance_status
                    maintenance = get_maintenance_status()
                    if maintenance and maintenance.get('is_active'):
                        is_admin = user.get('is_admin', False)
                        allowed_staff = maintenance.get('allowed_staff_ids', [])
                        if not is_admin and str(user['_id']) not in allowed_staff:
                            msg = maintenance.get('message', 'System is under maintenance. Please try again later.')
                            if maintenance.get('end_time'):
                                msg += f" Expected end time: {maintenance['end_time']}."
                            messages.error(request, msg)
                            return render(request, 'auth/admin_login.html')
                    # -----------------------------

                    # Ensure they actually have admin or tech_staff privileges
                    if not user.get('is_admin') and user.get('role') != 'tech_staff':
                        messages.error(request, 'You do not have staff permissions.')
                        return render(request, 'auth/admin_login.html')

                    # Set session
                    request.session['user_id'] = str(user['_id'])
                    request.session['mobile'] = user.get('mobile', '')
                    request.session['email'] = user.get('email', '')

                    # Force session save to catch SQLite write errors
                    request.session.save()

                    # Update last login
                    users.update_one(
                        {'_id': user['_id']},
                        {'$set': {'last_login': datetime.now()}}
                    )

                    messages.success(request, 'Staff Login successful!')
                    return redirect('custom_admin_dashboard' if user.get('is_admin') else 'staff_dashboard')
                else:
                    messages.error(request, 'Invalid email or password.')
            else:
                messages.error(request, 'Invalid email or password.')

        except Exception as e:
            logger.exception("Error during admin login process:")
            messages.error(request, f'An unexpected error occurred: {str(e)}')
            return render(request, 'auth/admin_login.html', status=500)

    return render(request, 'auth/admin_login.html')


def logout_view(request):
    """Handle user logout."""
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('landing_page')


@ratelimit(key='ip', rate='5/h', block=True)
def forgot_pin_view(request):
    """Handle verification for PIN reset."""
    if request.session.get('user_id'):
        return redirect('dashboard')

    if request.method == 'POST':
        mobile = request.POST.get('mobile', '').strip()
        full_name = request.POST.get('full_name', '').strip()

        users = get_collection('users')
        user = users.find_one({'mobile': mobile})

        if not user:
            messages.error(request, 'No user registered with this mobile number.')
            return render(request, 'auth/forgot_pin.html')

        profiles = get_collection('profiles')
        profile = profiles.find_one({'user_id': str(user['_id'])})

        # Match case-insensitively and trim
        if not profile or profile.get('full_name', '').strip().lower() != full_name.lower():
            messages.error(request, 'Mobile number and full name do not match.')
            return render(request, 'auth/forgot_pin.html')

        # If match, render the Step 2 form
        return render(request, 'auth/forgot_pin.html', {
            'step': 'reset',
            'target_user_id': str(user['_id'])
        })

    return render(request, 'auth/forgot_pin.html', {'step': 'verify'})


@ratelimit(key='ip', rate='5/h', block=True)
def reset_pin_submit(request):
    """Submit the new PIN."""
    from bson import ObjectId
    if request.method == 'POST':
        target_user_id = request.POST.get('user_id', '').strip()
        new_pin = request.POST.get('new_pin', '').strip()
        confirm_pin = request.POST.get('confirm_pin', '').strip()

        if not target_user_id or not new_pin or not confirm_pin:
            messages.error(request, 'Invalid request.')
            return redirect('forgot_pin')

        if len(new_pin) != 5 or not new_pin.isdigit():
            messages.error(request, 'PIN must be exactly 5 digits (numeric only).')
            return render(request, 'auth/forgot_pin.html', {
                'step': 'reset',
                'target_user_id': target_user_id
            })

        if new_pin != confirm_pin:
            messages.error(request, 'PINs do not match.')
            return render(request, 'auth/forgot_pin.html', {
                'step': 'reset',
                'target_user_id': target_user_id
            })

        # Hash new PIN
        hashed = bcrypt.hashpw(new_pin.encode('utf-8'), bcrypt.gensalt())

        users = get_collection('users')
        users.update_one(
            {'_id': ObjectId(target_user_id)},
            {'$set': {'password': hashed, 'updated_at': datetime.now()}}
        )

        messages.success(request, 'Your PIN has been successfully reset! Please login with your new PIN.')
        return redirect('login')

    return redirect('forgot_pin')


def auth_check_view(request):
    """Lightweight endpoint for Flutter to check if the user session is active.
    Returns JSON: {"authenticated": true} or {"authenticated": false}
    """
    from django.http import JsonResponse
    is_authenticated = bool(request.session.get('user_id'))
    return JsonResponse({'authenticated': is_authenticated})


def verify_pin_api(request):
    """API endpoint to verify PIN (used for app lock)."""
    from django.http import JsonResponse
    import json
    
    if not request.session.get('user_id'):
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pin = data.get('pin', '').strip()
            
            from bson import ObjectId
            users = get_collection('users')
            user = users.find_one({'_id': ObjectId(request.session['user_id'])})
            
            if user:
                stored_password = user['password']
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')
                if bcrypt.checkpw(pin.encode('utf-8'), stored_password):
                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({'success': False, 'error': 'Invalid PIN'})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid PIN'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
