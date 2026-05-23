"""
MongoDB connection module for GroupSathi.
Provides a singleton database connection used throughout the application.
"""

from pymongo import MongoClient
from django.conf import settings

_client = None
_db = None


def get_db():
    """Get MongoDB database connection (singleton pattern)."""
    global _client, _db
    if _db is None:
        _client = MongoClient(settings.MONGODB_URI)
        _db = _client[settings.MONGODB_NAME]
        _ensure_indexes()
    return _db


def _ensure_indexes():
    """Create necessary indexes for performance."""
    db = _db

    # Users collection
    db.users.create_index('mobile', unique=True)

    # Profiles collection
    db.profiles.create_index('user_id', unique=True)
    db.profiles.create_index('member_id', unique=True, sparse=True)

    # Groups collection
    db.groups.create_index('group_id', unique=True)

    # Group Members
    db.group_members.create_index([('group_id', 1), ('user_id', 1)], unique=True)

    # Loans
    db.loans.create_index('group_id')
    db.loans.create_index('user_id')

    # Notifications
    db.notifications.create_index('user_id')
    db.notifications.create_index([('user_id', 1), ('is_read', 1)])

    # Join Requests
    db.join_requests.create_index([('group_id', 1), ('user_id', 1)])

    # Leave Requests
    db.leave_requests.create_index([('group_id', 1), ('user_id', 1)])

    # EMI Records
    db.emi_records.create_index([('group_id', 1), ('user_id', 1)])

    # Transactions
    db.transactions.create_index('group_id')
    db.transactions.create_index('user_id')

    # Reminder Logs
    db.reminder_logs.create_index([('group_id', 1), ('reminder_type', 1), ('year', 1), ('month', 1)], unique=True)


def get_collection(name):
    """Get a specific MongoDB collection."""
    return get_db()[name]
