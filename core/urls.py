"""
URL configuration for GroupSathi core app.
"""

from django.urls import path
from core.views.auth_views import (
    register_view, login_view, admin_login_view, logout_view, 
    forgot_pin_view, reset_pin_submit, auth_check_view
)
from core.views.dashboard_views import dashboard_view
from core.views.landing_views import landing_page_view
from core.views.profile_views import profile_complete_view, profile_view, profile_edit_view
from core.views.group_views import (
    create_group_view, join_group_view, my_groups_view,
    group_detail_view, approve_join_request, reject_join_request, leave_group_view,
    approve_leave_request, reject_leave_request, promote_member_view,
    demote_member_view, remove_member_view,
    delete_group_view, waive_fine_request_view, approve_waive_request,
    reject_waive_request, send_emi_alert_view, edit_group_view,
    impose_fine_request_view, approve_impose_fine_view, reject_impose_fine_view,
    pay_imposed_fine_view, approve_fine_payment_view, reject_fine_payment_view,
    waive_imposed_fine_request_view, group_settlement_preview_view, execute_group_settlement_view
)
from core.views.loan_views import (
    loan_list_view, loan_request_view, loan_approve_view, loan_reject_view, loan_repay_view,
    emi_payment_view, approve_emi_request, reject_emi_request,
    approve_repayment_request, reject_repayment_request,
    extend_loan_request_view, approve_extend_loan_view, reject_extend_loan_view
)
from core.views.notification_views import (
    alerts_view, mark_read_view, mark_all_read_view,
    delete_notification_view, delete_all_notifications_view
)
from core.views.admin_views import (
    admin_dashboard_view, admin_users_view, admin_groups_view,
    admin_user_detail_view, admin_remove_user_view, admin_user_pdf_view,
    admin_add_staff_view, admin_broadcast_view, staff_dashboard_view, admin_edit_user_view,
    admin_hard_delete_user_view, admin_hard_delete_group_view, admin_edit_group_view,
    admin_chatbot_train_view, admin_db_explorer_view, admin_db_collection_view,
    admin_db_document_edit_view, admin_db_document_delete_view, admin_db_document_bulk_delete_view,
    admin_staff_list_view, admin_edit_staff_view, admin_delete_staff_view
)
from core.views.support_views import (
    my_tickets_view, create_ticket_view, ticket_chat_view, admin_tickets_view,
    staff_create_escalation_view
)
from core.views.search_views import search_member_view
from core.views.report_views import reports_view, generate_report_pdf, generate_settlement_pdf
from core.views.settings_views import settings_view, change_password_view
from core.views.help_views import help_view
from core.views.calculator_views import calculator_view
from core.views.download_views import download_apk_view
from core.views.chatbot_views import get_jwt_token_view, ChatbotAskView, ChatbotHistoryView, PublicChatbotAskView, ai_summarize_view, ai_generate_message_view, ai_generate_image_view

urlpatterns = [
    # Home / Landing
    path('', landing_page_view, name='landing_page'),
    path('reset-pin/submit/', reset_pin_submit, name='reset_pin_submit'),
    path('dashboard/', dashboard_view, name='dashboard'),

    # Auth
    path('api/auth/check/', auth_check_view, name='auth_check'),
    path('api/auth/jwt-token/', get_jwt_token_view, name='jwt_token'),
    path('api/ai/summarize/', ai_summarize_view, name='ai_summarize'),
    path('api/ai/generate-message/', ai_generate_message_view, name='ai_generate_message'),
    path('api/ai/generate-image/', ai_generate_image_view, name='ai_generate_image'),
    # Chatbot Endpoints
    path('api/chatbot/ask/', ChatbotAskView.as_view(), name='chatbot_ask'),
    path('api/chatbot/public-ask/', PublicChatbotAskView.as_view(), name='chatbot_public_ask'),
    path('api/chatbot/history/', ChatbotHistoryView.as_view(), name='chatbot_history'),
    path('auth/register/', register_view, name='register'),
    path('auth/login/', login_view, name='login'),
    path('auth/staff-login/', admin_login_view, name='admin_login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/forgot-pin/', forgot_pin_view, name='forgot_pin'),
    path('auth/forgot-pin/reset/', reset_pin_submit, name='reset_pin_submit'),

    # Profile
    path('profile/complete/', profile_complete_view, name='profile_complete'),
    path('profile/', profile_view, name='profile_view'),
    path('profile/edit/', profile_edit_view, name='profile_edit'),

    # Groups
    path('groups/create/', create_group_view, name='create_group'),
    path('groups/join/', join_group_view, name='join_group'),
    path('groups/my/', my_groups_view, name='my_groups'),
    path('groups/<str:group_id>/', group_detail_view, name='group_detail'),
    path('groups/<str:group_id>/edit/', edit_group_view, name='edit_group'),
    path('groups/<str:group_id>/leave/', leave_group_view, name='leave_group'),
    path('groups/<str:group_id>/delete/', delete_group_view, name='delete_group'),
    path('groups/<str:group_id>/promote/<str:member_user_id>/', promote_member_view, name='promote_member'),
    path('groups/<str:group_id>/demote/<str:member_user_id>/', demote_member_view, name='demote_member'),
    path('groups/<str:group_id>/remove-member/<str:member_user_id>/', remove_member_view, name='remove_member'),
    path('groups/<str:group_id>/send-emi-alert/', send_emi_alert_view, name='send_emi_alert'),
    path('join-request/<str:request_id>/approve/', approve_join_request, name='approve_join_request'),
    path('join-request/<str:request_id>/reject/', reject_join_request, name='reject_join_request'),
    path('leave-request/<str:request_id>/approve/', approve_leave_request, name='approve_leave_request'),
    path('leave-request/<str:request_id>/reject/', reject_leave_request, name='reject_leave_request'),
    path('groups/<str:group_id>/waive-fine/', waive_fine_request_view, name='waive_fine_request'),
    path('groups/<str:group_id>/waive-imposed-fine/', waive_imposed_fine_request_view, name='waive_imposed_fine_request'),
    path('waive-request/<str:request_id>/approve/', approve_waive_request, name='approve_waive_request'),
    path('waive-request/<str:request_id>/reject/', reject_waive_request, name='reject_waive_request'),
    path('groups/<str:group_id>/settlement/', group_settlement_preview_view, name='group_settlement_preview'),
    path('groups/<str:group_id>/settlement/execute/', execute_group_settlement_view, name='execute_group_settlement'),
    path('groups/<str:group_id>/settlement/pdf/', generate_settlement_pdf, name='generate_settlement_pdf'),

    # General Fine Imposition Consensus Flow
    path('groups/<str:group_id>/impose-fine/<str:target_user_id>/', impose_fine_request_view, name='impose_fine_request'),
    path('fine-request/<str:request_id>/approve/', approve_impose_fine_view, name='approve_impose_fine'),
    path('fine-request/<str:request_id>/reject/', reject_impose_fine_view, name='reject_impose_fine'),
    path('fine/<str:fine_id>/pay/', pay_imposed_fine_view, name='pay_imposed_fine'),
    path('fine/<str:fine_id>/approve-payment/', approve_fine_payment_view, name='approve_fine_payment'),
    path('fine/<str:fine_id>/reject-payment/', reject_fine_payment_view, name='reject_fine_payment'),

    # Loans
    path('loans/', loan_list_view, name='loan_list'),
    path('loans/request/<str:group_id>/', loan_request_view, name='loan_request'),
    path('loans/<str:loan_id>/approve/', loan_approve_view, name='loan_approve'),
    path('loans/<str:loan_id>/reject/', loan_reject_view, name='loan_reject'),
    path('loans/<str:loan_id>/repay/', loan_repay_view, name='loan_repay'),
    path('loans/<str:loan_id>/extend/', extend_loan_request_view, name='extend_loan_request'),
    path('loans/extend-request/<str:request_id>/approve/', approve_extend_loan_view, name='approve_extend_loan'),
    path('loans/extend-request/<str:request_id>/reject/', reject_extend_loan_view, name='reject_extend_loan'),
    path('emi/<str:group_id>/pay/', emi_payment_view, name='emi_payment'),
    path('emi-request/<str:request_id>/approve/', approve_emi_request, name='approve_emi_request'),
    path('emi-request/<str:request_id>/reject/', reject_emi_request, name='reject_emi_request'),
    path('repayment-request/<str:request_id>/approve/', approve_repayment_request, name='approve_repayment_request'),
    path('repayment-request/<str:request_id>/reject/', reject_repayment_request, name='reject_repayment_request'),

    # Notifications
    path('alerts/', alerts_view, name='alerts'),
    path('alerts/<str:notif_id>/read/', mark_read_view, name='mark_read'),
    path('alerts/read-all/', mark_all_read_view, name='mark_all_read'),
    path('alerts/<str:notif_id>/delete/', delete_notification_view, name='delete_notification'),
    path('alerts/delete-all/', delete_all_notifications_view, name='delete_all_notifications'),

    # Search
    path('search/', search_member_view, name='search_member'),

    # Reports
    path('reports/', reports_view, name='reports'),
    path('reports/<str:group_id>/pdf/', generate_report_pdf, name='generate_report_pdf'),

    # Settings
    path('settings/', settings_view, name='settings'),
    path('settings/password/', change_password_view, name='change_password'),

    # Help
    path('help/', help_view, name='help'),

    # Calculator
    path('calculator/', calculator_view, name='calculator'),

    # APK Download
    path('download/app/', download_apk_view, name='download_apk'),

    # Custom Admin Dashboard
    path('custom-admin/', admin_dashboard_view, name='custom_admin_dashboard'),
    path('custom-admin/users/', admin_users_view, name='custom_admin_users'),
    path('custom-admin/users/<str:user_id>/', admin_user_detail_view, name='admin_user_detail'),
    path('custom-admin/users/<str:user_id>/edit/', admin_edit_user_view, name='admin_edit_user'),
    path('custom-admin/users/<str:user_id>/delete/', admin_remove_user_view, name='admin_remove_user'),
    path('custom-admin/users/<str:user_id>/pdf/', admin_user_pdf_view, name='admin_user_pdf'),
    path('custom-admin/users/<str:user_id>/hard-delete/', admin_hard_delete_user_view, name='admin_hard_delete_user'),
    path('custom-admin/groups/', admin_groups_view, name='custom_admin_groups'),
    path('custom-admin/groups/<str:group_id>/delete/', admin_hard_delete_group_view, name='admin_hard_delete_group'),
    path('custom-admin/groups/<str:group_id>/edit/', admin_edit_group_view, name='admin_edit_group'),
    path('custom-admin/staff/add/', admin_add_staff_view, name='admin_add_staff'),
    path('custom-admin/staff/list/', admin_staff_list_view, name='admin_staff_list'),
    path('custom-admin/staff/edit/<str:staff_id>/', admin_edit_staff_view, name='admin_edit_staff'),
    path('custom-admin/staff/delete/<str:staff_id>/', admin_delete_staff_view, name='admin_delete_staff'),
    path('custom-admin/broadcast/', admin_broadcast_view, name='admin_broadcast'),
    path('custom-admin/chatbot-train/', admin_chatbot_train_view, name='admin_chatbot_train'),
    path('custom-admin/db/', admin_db_explorer_view, name='admin_db_explorer'),
    path('custom-admin/db/<str:collection_name>/', admin_db_collection_view, name='admin_db_collection'),
    path('custom-admin/db/<str:collection_name>/edit/<str:doc_id>/', admin_db_document_edit_view, name='admin_db_document_edit'),
    path('custom-admin/db/<str:collection_name>/delete/<str:doc_id>/', admin_db_document_delete_view, name='admin_db_document_delete'),
    path('custom-admin/db/<str:collection_name>/bulk-delete/', admin_db_document_bulk_delete_view, name='admin_db_document_bulk_delete'),
    
    # Technical Staff Dashboard
    path('staff-dashboard/', staff_dashboard_view, name='staff_dashboard'),
    path('staff-dashboard/tickets/', admin_tickets_view, name='admin_tickets'),
    path('support/staff-escalate/', staff_create_escalation_view, name='staff_escalate'),
    
    # Customer Support
    path('support/', my_tickets_view, name='my_tickets'),
    path('support/create/', create_ticket_view, name='create_ticket'),
    path('support/<str:ticket_id>/', ticket_chat_view, name='ticket_chat'),
]
