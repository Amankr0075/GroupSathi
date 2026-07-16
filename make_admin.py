import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupsathi.settings')
django.setup()

from core.db import get_collection

import bcrypt

def make_admin(mobile_number, email, password):
    users = get_collection('users')
    user = users.find_one({'mobile': mobile_number})
    
    if not user:
        print(f"Error: No user found with mobile number '{mobile_number}'")
        return
        
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    users.update_one({'_id': user['_id']}, {
        '$set': {
            'is_admin': True,
            'email': email,
            'password': hashed
        }
    })
    print(f"Success! The user with mobile {mobile_number} is now an Admin.")
    print(f"You can now log in at http://127.0.0.1:8000/auth/staff-login/ using Email: {email} and your new password.")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python make_admin.py <mobile_number> <admin_email> <admin_password>")
    else:
        make_admin(sys.argv[1], sys.argv[2], sys.argv[3])
