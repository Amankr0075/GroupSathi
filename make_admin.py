import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupsathi.settings')
django.setup()

from core.db import get_collection

def make_admin(mobile_number):
    users = get_collection('users')
    user = users.find_one({'mobile': mobile_number})
    
    if not user:
        print(f"Error: No user found with mobile number '{mobile_number}'")
        return
        
    users.update_one({'_id': user['_id']}, {'$set': {'is_admin': True}})
    print(f"Success! The user with mobile {mobile_number} is now an Admin.")
    print("You can now log in and access the Admin Dashboard from the profile dropdown menu, or go to http://127.0.0.1:8000/custom-admin/")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py <mobile_number>")
    else:
        make_admin(sys.argv[1])
