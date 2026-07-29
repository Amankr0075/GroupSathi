import os
import django
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def clean_database():
    uri = os.getenv('MONGODB_URI')
    db_name = os.getenv('MONGODB_NAME', 'groupsathi_db')
    
    if not uri:
        print("Error: MONGODB_URI not found in .env")
        return
        
    print(f"Connecting to MongoDB...")
    client = MongoClient(uri)
    db = client[db_name]
    
    # 1. Identify admin users
    print("Identifying admin users...")
    admin_users = list(db.users.find({
        '$or': [
            {'is_admin': True},
            {'role': 'super_admin'}
        ]
    }))
    
    admin_ids = [admin['_id'] for admin in admin_users]
    print(f"Found {len(admin_ids)} admin user(s).")
    
    # 2. Delete non-admin users
    user_result = db.users.delete_many({'_id': {'$nin': admin_ids}})
    print(f"Deleted {user_result.deleted_count} non-admin users.")
    
    # 3. Delete non-admin profiles
    # Profiles use user_id as a string (from auth_views.py: 'user_id': str(user_id))
    admin_ids_str = [str(aid) for aid in admin_ids]
    profile_result = db.profiles.delete_many({'user_id': {'$nin': admin_ids_str}})
    print(f"Deleted {profile_result.deleted_count} non-admin profiles.")
    
    # 4. Clear all other collections completely
    collections_to_clear = [
        'groups',
        'group_members',
        'loans',
        'notifications',
        'join_requests',
        'leave_requests',
        'emi_records',
        'transactions',
        'reminder_logs',
        'chat_histories',
        'tickets'
    ]
    
    for coll_name in collections_to_clear:
        result = db[coll_name].delete_many({})
        print(f"Deleted {result.deleted_count} documents from {coll_name}.")
        
    print("Database cleanup complete! All data except admin users has been removed.")

if __name__ == '__main__':
    clean_database()
