# Models file - GroupSathi uses MongoDB directly via PyMongo.
# This file documents the collection schemas for reference.

"""
MongoDB Collection Schemas:

1. users:
   - _id: ObjectId
   - mobile: str (unique, 10 digits)
   - password: bytes (bcrypt hash)
   - is_active: bool
   - last_login: datetime
   - created_at: datetime
   - updated_at: datetime

2. profiles:
   - _id: ObjectId
   - user_id: str (ref to users._id)
   - mobile: str
   - full_name: str
   - gender: str
   - address: str
   - pin_code: str
   - profile_photo: str (file path)
   - member_id: str (unique 5-digit)
   - created_at: datetime
   - updated_at: datetime

3. groups:
   - _id: ObjectId
   - group_id: str (unique 6-digit)
   - name: str
   - logo: str (file path)
   - emi_amount: float
   - interest_rate: float
   - emi_date: int (day of month)
   - created_by: str (user_id)
   - is_active: bool
   - created_at: datetime
   - updated_at: datetime

4. group_members:
   - _id: ObjectId
   - group_id: str
   - user_id: str
   - role: str (leader, co-leader, member)
   - status: str (active, inactive)
   - joined_at: datetime

5. loans:
   - _id: ObjectId
   - group_id: str
   - user_id: str
   - amount: float
   - interest_rate: float
   - tenure_months: int
   - interest_amount: float
   - total_repayment: float
   - remaining_amount: float
   - mortgage_details: str
   - status: str (pending, approved, active, completed, rejected)
   - approved_by: str
   - approved_at: datetime
   - created_at: datetime
   - updated_at: datetime

6. transactions:
   - _id: ObjectId
   - group_id: str
   - user_id: str
   - type: str (emi_payment, interest_payment, loan_disbursement)
   - amount: float
   - description: str
   - created_at: datetime

7. notifications:
   - _id: ObjectId
   - user_id: str
   - title: str
   - message: str
   - type: str (info, success, warning, danger)
   - group_id: str (optional)
   - is_read: bool
   - created_at: datetime

8. emi_records:
   - _id: ObjectId
   - group_id: str
   - user_id: str
   - amount: float
   - payment_date: datetime
   - status: str

9. join_requests:
   - _id: ObjectId
   - group_id: str
   - user_id: str
   - member_name: str
   - status: str (pending, approved, rejected)
   - leader_approved: bool
   - co_leader_1_approved: bool
   - co_leader_2_approved: bool
   - created_at: datetime

10. leave_requests:
    - _id: ObjectId
    - group_id: str
    - user_id: str
    - status: str
    - leader_approved: bool
    - created_at: datetime

11. reminder_logs:
    - _id: ObjectId
    - group_id: str
    - reminder_type: str (e.g. '24h_before')
    - year: int
    - month: int
    - created_at: datetime
"""
