from django.urls import path
from . import views

urlpatterns = [
    path('',views.home,name='home page'),
    path('register/owner/', views.register_owner, name='register_owner'),
    path('register/student/', views.register_student, name='register_student'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('student/profile/', views.student_profile_setup, name='student_profile_setup'),
    path('owner/profile/', views.owner_profile_setup, name='owner_profile_setup'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout, name='logout'),
    path('create-post/', views.create_post, name='create_post'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/edit/<int:post_id>/', views.edit_post, name='edit_post'),
    path('post/delete/<int:post_id>/', views.delete_post, name='delete_post'),
    path('post/assign-tenant/<int:post_id>/', views.assign_tenant, name='assign_tenant'),
    path('tenants/', views.tenant_list, name='tenant_list'),
    path('tenancy/end/<int:tenancy_id>/', views.end_tenancy, name='end_tenancy'),
    # Booking URLs
    path('post/<int:post_id>/book/', views.create_booking, name='create_booking'),
    path('my-bookings/', views.student_bookings, name='student_bookings'),
    path('booking/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('profile/<int:user_id>/', views.public_profile, name='public_profile'),
    path('my-tenancies/', views.student_tenancies, name='student_tenancies'),
    path('booking-requests/', views.owner_booking_requests, name='owner_booking_requests'),
    path('booking/action/<int:booking_id>/<str:action>/', views.handle_booking_action, name='handle_booking_action'),
    # Saved Posts URLs
    path('post/toggle-save/<int:post_id>/', views.toggle_save_post, name='toggle_save_post'),
    path('my-saved-posts/', views.saved_posts_list, name='saved_posts_list'),
    # Review URL
    path('post/<int:post_id>/add-review/', views.add_review, name='add_review'),
    # Messaging URLs
    path('messages/', views.inbox, name='inbox'),
    path('messages/start/<int:post_id>/', views.start_conversation, name='start_conversation'),
    path('messages/conversation/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    # API URL for notifications
    path('api/notifications/unread/', views.get_unread_notifications, name='get_unread_notifications'),
    # Rent Payment URLs
    path('rent-payments/', views.owner_rent_payments, name='owner_rent_payments'),
    path('rent-payments/mark-paid/<int:payment_id>/', views.mark_payment_paid, name='mark_payment_paid'),
    # Student Rent Payment URLs
    path('my-rent-payments/', views.student_rent_payments, name='student_rent_payments'),
    path('process-payment/<int:payment_id>/', views.process_payment, name='process_payment'),
    path('confirm-payment/<int:payment_id>/', views.confirm_payment, name='confirm_payment'),
    # Maintenance Request URLs
    path('tenancy/<int:tenancy_id>/report-issue/', views.report_issue, name='report_issue'),
    path('maintenance-requests/', views.owner_maintenance_list, name='owner_maintenance_list'),
    path('maintenance-requests/<int:request_id>/', views.maintenance_request_detail, name='maintenance_request_detail'),

]
